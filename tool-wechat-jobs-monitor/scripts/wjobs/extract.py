# -*- coding: utf-8 -*-
"""抽取层：把一篇招聘公告拆成结构化字段。

两种模式：
  rule —— 纯正则。离线、零成本、可解释。适合公告格式规范的政务号。
  llm  —— 调大模型。适合排版混乱、一篇文章含多个单位的场景。

任一路径失败都会自动回退到 rule，保证流水线绝不空手而归。
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

import requests

from .fetch import Article

# ---------------------------------------------------------------- 数据结构


@dataclass
class JobPost:
    article_title: str = ""
    url: str = ""
    published: str = ""
    account: str = ""

    unit: str = ""            # 招聘单位 / 主管部门
    category: str = ""        # 岗位类别
    headcount: str = ""       # 招聘人数
    education: str = ""       # 学历要求
    major: str = ""           # 专业要求
    age: str = ""             # 年龄要求
    location: str = ""        # 工作地点
    apply_start: str = ""     # 报名开始（YYYY-MM-DD）
    apply_end: str = ""       # 报名截止（YYYY-MM-DD）
    apply_method: str = ""    # 报名方式 / 入口
    exam: str = ""            # 笔试面试安排
    salary: str = ""          # 薪酬待遇
    contact: str = ""         # 联系方式
    highlights: str = ""      # 关键条件摘要
    extract_mode: str = "rule"
    seq: int = 0              # 同一篇文章内第几条（llm 模式可能一篇拆多条）

    @property
    def fingerprint(self) -> str:
        """去重指纹：只认**文章身份**（链接，退化用标题+发布日期）。

        曾经这里混入了 unit / category —— 那是抽取结果。后果很实际：
        只要修一次抽取逻辑（比如把单位名从「郑州节后」修成空），
        同一篇文章的指纹就变了，于是被当成新文章重新入库，
        邮件里同一条标题出现两遍。指纹必须与抽取质量解耦。
        """
        ident = (self.url or "").strip() or f"{self.article_title}|{self.published}"
        return hashlib.sha1(f"{ident}#{self.seq}".encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["fingerprint"] = self.fingerprint
        return d


# ---------------------------------------------------------------- 工具函数

_EDU_ORDER = [
    ("博士", r"博士(?:研究生|后)?"),
    ("硕士", r"硕士(?:研究生|学位)?"),
    ("研究生", r"研究生(?!学历|(?:及以上)?学历要求)"),
    ("本科", r"(?:全日制)?本科(?:及以上)?(?:学历)?"),
    ("大专", r"(?:全日制)?(?:大专|专科)(?:及以上)?"),
    # 「高中」必须带学历语境，否则会把「高中教师」「初中、高中」当成学历要求；
    # 中间不允许跨过标点，否则「本科及以上学历，初中、高中教师」会误命中
    ("高中", r"(?:学历|文化程度)[^。\n，、；：]{0,4}高中|高中(?:及以上)?(?:学历|文化程度)"),
]

_DATE_RE = re.compile(r"(20\d{2})\s*[年\-/.]\s*(\d{1,2})\s*[月\-/.]\s*(\d{1,2})\s*日?")
# 年份可省略，如「10月16日」——靠前文年份"继承"补全
_DATE_CARRY_RE = re.compile(r"(?:(\d{4})\s*[年\-/.])?\s*(\d{1,2})\s*[月\-/.]\s*(\d{1,2})\s*日?")
_PHONE_RE = re.compile(r"(?:Tel[:：]?\s*)?(0\d{2,3}[\s\-]?\d{7,8})")
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_URL_RE = re.compile(r"https?://[^\s，。；、）)】\"']+")

# 公众号运营方自己的投稿/合作邮箱（例如某号的「wanglinlin@xxx.com」），
# 每篇文末都有，但它不是「本次招聘」的联系人邮箱，不该出现在岗位联系方式里。
# 由 config.yaml -> extract.contact_email_deny 提供（按域名子串匹配）。
# 这里默认留空 —— 不同账号的运营邮箱不同，不该硬编码进通用 skill。
_CONTACT_EMAIL_DENY: List[str] = []


def _seg(text: str, *labels: str, span: int = 200) -> str:
    """截取「关键词：内容」到句末的片段。

    取**所有**命中里最长的那一段，而不是第一个。
    原因：政务公告的标题常写作「三、报名方式」，其后紧跟的却是报名时间段落，
    取第一个命中就会把「报名时间：…」当成报名方式。取最长可稳定命中正文实述。
    """
    best = ""
    for lb in labels:
        for m in re.finditer(rf"{lb}\s*[:：]?\s*([^。\n]{{2,{span}}})", text):
            val = m.group(1).strip(" ，；、")
            if len(val) > len(best):
                best = val
    return best


def _norm_date(y: str, m: str, d: str) -> str:
    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"


def _dates_in(text: str) -> List[str]:
    return [_norm_date(*g) for g in _DATE_RE.findall(text)]


def _dates_carry(text: str) -> List[str]:
    """按出现顺序抽日期，缺年份时继承上一个已知年份。

    「2026年10月12日9:00至10月16日17:00」→ ['2026-10-12','2026-10-16']
    政务公告里第二个日期几乎总是省略年份，不继承就会把起止判错。
    """
    out: List[str] = []
    year: int | None = None
    for y, m, d in _DATE_CARRY_RE.findall(text):
        if y:
            year = int(y)
        mm, dd = int(m), int(d)
        if not (1 <= mm <= 12 and 1 <= dd <= 31):
            continue
        if year is None:
            continue
        out.append(f"{year:04d}-{mm:02d}-{dd:02d}")
    return out


# 单位名的「机构后缀」——招聘标题里的实体几乎必然带其中之一。
# 优先按它抓实体，比按「招聘」二字切分可靠得多（切分法会被 别名/钩子/并列 带偏）。
_UNIT_SUFFIX = (r"(?:集团|公司|有限公司|有限责任公司|股份公司|银行|医院|卫生院|服务中心|"
                r"中心|学校|小学|中学|初中|高中|大学|学院|幼儿园|职业技术学院|"
                r"研究院|研究所|设计院|事务所|交易所|管委会|管理局|局|委员会|"
                r"办公室|研究院|支队|大队|出版社|车站|机场|电网|电厂|厂)")

_UNIT_RE = re.compile(
    r"([\u4e00-\u9fa5A-Za-z0-9]{2,24}" + _UNIT_SUFFIX + r")")

# 这些词一出现，说明切出来的压根不是机构名，而是活动名/时间副词/模糊数量词。
# 「郑州节后招聘会来了！」→ 切分法会给出「郑州节后」这个假单位，必须拦掉；
# 拦掉后宁可返回空（报告里显示"未识别单位"），也不能编一个错的单位名。
_UNIT_BAD = re.compile(
    r"(节前|节后|期间|本周|上周|近期|最新|一批|大批|多家|两家|三家|几家|数个|若干"
    r"|招聘会|直招|急招|好单位|这些|众多|大量|全部|部分)")


def guess_unit(title: str) -> str:
    """从标题猜招聘单位。

    策略（按可靠性排序，命中即返回）：
      A. 直接抓带机构后缀的实体名 —— 最可靠。
         「郑州比亚迪招聘10000人！操作工…」→ 郑州比亚迪（误）…这条反而抓不到后缀，
         所以 A 失败时走 B。
      B. 「招聘/招录」前的文字切分 —— 适用于「X局招聘」「X公司招聘」这类
         实体本身不以标准后缀结尾的情况。
      C. 兜底：整条标题。

    处理前先剥掉【】栏目名与营销钩子，否则会把「【郑州事业单位」当成单位名。
    """
    raw = title or ""
    t = re.sub(r"[（(][^)）]*[)）]", "", raw)

    # ① 剥【】里的「栏目名」（郑州事业单位招聘 / 郑州医院招聘 …）
    def _strip_bracket(m: "re.Match[str]") -> str:
        inner = m.group(1)
        if re.fullmatch(r"[\u4e00-\u9fa5A-Za-z0-9]{0,10}(?:招聘|招录|招考|校招|社招|兼职|岗位|公告)", inner):
            return ""
        return inner
    t = re.sub(r"[【\[]([^】\]]{1,20})[】\]]", _strip_bracket, t).strip()

    # ② 剥开头的营销钩子（部分月薪达1万！/ 年薪10万起！/ 六险一金！）
    def _strip_hook(m: "re.Match[str]") -> str:
        seg = m.group(1)
        if re.search(r"(月薪|年薪|日薪|时薪|起薪|福利|待遇|补贴|五险|六险|七险|八险|"
                     r"公积金|包吃|包住|双休|带薪|学历|可报名|可报|应届|经验|"
                     r"不限|年龄)", seg):
            return ""
        return seg + m.group(2)
    # 末尾的 (?=.) 很关键：只有当「！」后面还有内容时才算钩子。
    # 「郑州西门子、赛诺菲招聘，福利待遇好！」这类标题，钩子词在**结尾**，
    # 若无此保护会被整条剥空，最后回退成「整条标题当单位名」。
    t = re.sub(r"^([^！!]{1,18})([！!])(?=.)", _strip_hook, t, count=1).strip()

    body = re.sub(r"(公告|通知|简章|启事|公示|通告|来啦|来了)\s*$", "", t.strip())
    body = re.sub(r"^20\d{2}\s*年", "", body).strip()

    # A. 机构后缀优先：在「招聘」二字之前的部分里找实体，避免抓到后面的岗位描述
    head_zone = re.split(r"(?:招聘|招录|招考|校招|社招|引进|选聘|选调|补录)", body)[0]
    m = _UNIT_RE.search(head_zone)
    if m:
        cand = m.group(1).strip(" 　的")
        if not _UNIT_BAD.search(cand):
            return cand

    # A2. 若「招聘」前没有后缀实体，退一步在整条里找（如「郑州比亚迪招聘10000人」）
    m = _UNIT_RE.search(body)
    if m:
        cand = m.group(1)
        # 排除「培训学校」「服务中心」等太泛或紧邻「教师」的错误结果
        if len(cand) >= 3 and not re.search(r"^(?:劳务|人才|培训|服务)$", cand) \
                and not _UNIT_BAD.search(cand):
            return cand.strip(" 　的")

    # B. 文字切分
    parts = re.split(r"(?:面向|公开|社会|拟|计划|招聘|招录|招考|引进|选聘|选调|补录)", body)
    unit = parts[0].strip(" 　的")
    unit = re.sub(r"[，,、；;！!～~\s]+$", "", unit)
    # 「河南四方达2027校园招聘」→ 切分后去掉尾巴上的年份与招聘场景词
    unit = re.sub(r"20\d{2}\s*年?\s*(?:校园|社会|春季|秋季|校招|社招|专场|大型|网络)?\s*$", "", unit)
    unit = re.sub(r"(?:校园|社会|春季|秋季|校招|社招|专场|大型|网络)\s*$", "", unit).strip(" 　的")
    if _UNIT_BAD.search(unit):
        return ""      # 切出来的是活动名/模糊词，不是单位 —— 宁可留空

    # C. 兜底：地名太单薄时，用整条标题里最长的机构片段
    if unit in ("郑州", "河南", "郑", "河南省") or len(unit) < 3:
        return (body or raw).strip()
    return unit


def guess_category(title: str, text: str) -> str:
    """从标题猜岗位类别，猜不到再去正文里找「招聘岗位：…」这类显式描述。"""
    _GENERIC = {"人员", "人才", "公告", "通知", "简章", "启事", "公示", "通告"}
    m = re.search(r"(?:招聘|招录|引进|选聘|补录)([\u4e00-\u9fa5]{2,16}?)(?:公告|的通知|通知|简章|启事|$)", title or "")
    if m:
        cat = re.sub(r"^(?:若干|一批|一批次)", "", m.group(1).strip(" 　的"))
        if cat and cat not in _GENERIC:
            return cat
    # 「共设岗位 12 类」→ 12 类岗位
    m = re.search(r"(?:设|招聘)岗位\s*(\d{1,3})\s*类", text)
    if m:
        return f"{m.group(1)} 类岗位"
    # 只认带冒号的显式列举，避免抓到一整句碎碎念
    m = re.search(r"(?:招聘岗位|岗位类别|招聘计划)\s*[:：]\s*([^。\n，、；]{4,30})", text)
    if m:
        return m.group(1).strip(" ，；、")
    return ""


def _education(text: str) -> str:
    found: List[str] = []
    for label, pat in _EDU_ORDER:
        if re.search(pat, text):
            found.append(label)
    # 「硕士/博士」已覆盖「研究生」，去掉冗余项
    if ("硕士" in found or "博士" in found) and "研究生" in found:
        found.remove("研究生")
    return "、".join(dict.fromkeys(found))


def _headcount(text: str) -> str:
    """人数：优先抓「共/计划招聘 X 名」，再退回「X 名/人」，但必须排除误命中。

    兜底分支极易误伤，实测踩过的坑：
        郑州一单位劳务派遣   → 抓成「1 人」（其实「一单位」是量词）
        共设 2 个岗位        → 抓成「2 人」（其实说的是岗位数）
        「每人限报 1 个岗位」 → 抓成「1 人」
    所以兜底时要求：数字前不能是「一/两/两」等中文量词、后面紧跟的必须是
    「名/人」且不能是「个人/人员/人才/岗位/学科」这类复合词。
    """
    cands: List[int] = []
    for m in re.finditer(r"(?:共|计划|拟|合计|本次)?\s*(?:招聘|招录|招考|引进|选聘|补录)"
                         r"[^。；\n]{0,30}?(\d[\d,]{0,5})\s*[名个人]", text):
        cands.append(int(m.group(1).replace(",", "")))
    if not cands:
        for m in re.finditer(r"(?<![一二两三四五六七八九十])(\d[\d,]{0,5})\s*([名个人])"
                             r"(?!才|员|士|事|为|民|数|均|岗|学科|项目)", text):
            v = int(m.group(1).replace(",", ""))
            # 紧邻前文若是「设/共/岗位/学科/限报」等，说明这个数字指的不是人数
            pre = text[max(0, m.start() - 6):m.start()]
            if re.search(r"(?:设|共|岗位|学科|限报|每人|每个|第)\s*$", pre):
                continue
            cands.append(v)
    cands = [c for c in cands if 0 < c <= 100000]
    if not cands:
        if re.search(r"(若干|数名|不限|多名)", text):
            return "若干"
        return ""
    best = max(cands)
    return f"{best} 人"


def _apply_window(text: str) -> tuple[str, str, str]:
    """报名时间：返回 (起, 止, 原文片段)。

    策略：先按显式标签截句；截不到再找含「报名/截止」的句子。
    绝不做全文兜底扫描——那会把面试日期、笔试日期误当成报名截止，
    而给出错误的截止日期，比不给更坑人。
    """
    seg = _seg(text, "网上报名时间", "报名时间", "报名日期",
               "报名截止时间", "报名截止日期", span=160)
    if _is_noise(seg):
        seg = ""
    if not seg or not _dates_carry(seg):
        for m in re.finditer(r"[^。\n]{0,24}(?:报名|投递|截止)[^。\n]{0,140}", text):
            cand = m.group(0)
            if _is_noise(cand):  # 跳过文末菜单引导语
                continue
            seg = cand
            break
    ds = _dates_carry(seg)
    if not ds:
        return "", "", seg
    return ds[0], ds[-1], seg


def _apply_method(text: str) -> str:
    """报名方式：截显式标签段；若截到的是文末菜单引导语则丢弃。"""
    seg = _seg(text, "报名方式", "报名渠道", "报名入口", "投递方式", span=180)
    if seg and not _is_noise(seg):
        return seg
    # 退回：找含真实报名动作的句子
    for m in re.finditer(r"[^。\n]{4,180}", text):
        s = m.group(0).strip(" ，；、")
        if _is_noise(s):
            continue
        if re.search(r"(报名|投递|简历|发送至|发至|登录|登陆|提交)", s) and \
           re.search(r"(邮箱|官网|www\.|https?://|系统|平台|二维码|@)", s):
            return s
    return seg if not _is_noise(seg) else ""


def _money(text: str) -> str:
    m = re.search(r"(\d[\d,]{0,5}(?:\.\d+)?)\s*[—\-~至到]\s*(\d[\d,]{0,5}(?:\.\d+)?)\s*(万元|元|万元/年)", text)
    if m:
        return f"{m.group(1)}—{m.group(2)} {m.group(3)}"
    m = re.search(r"(\d[\d,]{0,5}(?:\.\d+)?)\s*(万元|元)", text)
    return f"{m.group(1)} {m.group(2)}" if m else ""


_SALARY_KW = ("薪酬", "薪资", "工资", "月薪", "年薪", "待遇", "补贴", "安家费", "福利", "五险", "公积金")
_MONEY_HINT = re.compile(r"\d[\d,]*\s*(?:万元|元)")
_FEE_KW = ("考务费", "报名费", "缴费", "费用", "服务费")

# 公众号文末的「求赞/求关注/小编」类运营文案，必须整体丢弃，
# 否则「点个赞，小编工资蹭蹭涨1毛」会被当成薪酬待遇混进招聘摘要。
_NOISE_KW = ("小编", "点个赞", "点赞", "在看", "转发", "涨1毛", "涨一毛",
             "关注我们", "扫码关注", "长按识别", "好运连连", "祝大家",
             "来源：", "声明：", "往期回顾", "推荐阅读", "更多资讯")

# 文末「回复【XX】获取…」是公众号的菜单引导语，不是本次招聘的报名方式。
_MENU_HINT = re.compile(r"回复\s*[【\[]?[^】\]]{1,8}[】\]]?\s*(?:获取|查看|即可)")


def _is_noise(seg: str) -> bool:
    """判断一句是否是公众号运营噪声（求赞、菜单引导、免责声明）。"""
    if any(k in seg for k in _NOISE_KW):
        return True
    # 「回复【地铁】获取郑州地铁招聘信息」这类：句子里没有真实的报名动作，
    # 只有菜单关键词引导，且不含"报名/投递/简历/邮箱/官网"等真报名信号。
    if _MENU_HINT.search(seg) and not re.search(
            r"(报名|投递|简历|邮箱|官网|www\.|https?://|发送至|发至|登录)", seg):
        return True
    return False


def _norm_key(s: str) -> str:
    """只留汉字/字母/数字，用于「这句是不是标题的复读」这类比对。"""
    return re.sub(r"[^\u4e00-\u9fa5A-Za-z0-9]", "", s or "")


def _salary(text: str, title: str = "") -> str:
    """薪酬待遇。

    单靠「薪酬待遇：」标签会漏掉大量只写「四、待遇」小标题的公告，
    所以改为按句扫描：命中待遇类关键词、或含金额且不是在讲报名费的句子，
    全部拼起来（去重、限长），信息最全。

    但正文首行通常是标题的复读。它会命中「待遇」这类关键词（标题里往往有
    「福利待遇好！」），于是「薪酬」字段里出现一整条标题原文——这是噪声，
    因为标题已经在卡片第一行显示过了。这里把与标题等价的句子剔掉。
    """
    tkey = _norm_key(title)
    picked: List[str] = []
    for seg in re.split(r"[。\n]", text):
        s = seg.strip(" ，；、")
        if len(s) < 8:
            continue
        if _is_noise(s):
            continue
        skey = _norm_key(s)
        if tkey and skey and (
                skey == tkey
                or skey in tkey
                or (tkey in skey and len(skey) - len(tkey) <= 4)):
            continue
        has_kw = any(k in s for k in _SALARY_KW)
        has_money = bool(_MONEY_HINT.search(s))
        if not (has_kw or has_money):
            continue
        if not has_kw and any(f in s for f in _FEE_KW):
            continue  # 这是在讲报名费，不是工资
        if any(s in p or p in s for p in picked):
            continue
        picked.append(s)
    return "；".join(picked)[:260]


def _exam(text: str) -> str:
    """考试安排。

    三个坑：
    ① 从关键词前一并截取会带出「00前完成网上缴费」这种半截垃圾 → 必须从关键词开始匹配；
    ② 关键词后不足 6 字的是残句（如「面试三个环节」）→ 直接丢弃；
    ③ 「本次引进不设笔试」若从「笔试」处切，会把否定语义切掉，读出相反的结论
       → 若关键词前紧邻否定词，一并保留。
    """
    found: List[str] = []
    for kw in ("笔试", "面试", "体能测试", "试讲", "专业测试"):
        hits: List[str] = []
        for m in re.finditer(rf"{kw}[^。\n]{{6,100}}", text):
            s = m.group(0)
            pre = text[max(0, m.start() - 4):m.start()]
            neg = re.search(r"(不设|无需|免于|免|无)$", pre)
            if neg:
                s = neg.group(1) + s
            hits.append(s.strip(" ，；、"))
        if hits:
            found.append(max(hits, key=len))
    found.sort(key=len, reverse=True)
    uniq: List[str] = []
    for s in found:
        if any(s in u for u in uniq):
            continue
        uniq.append(s)
    return " ｜ ".join(uniq)[:360]


def _highlights(pub: str, unit: str, cat: str, hc: str, edu: str, age: str, end: str) -> str:
    bits = []
    if unit:
        bits.append(f"单位：{unit}")
    if cat:
        bits.append(f"岗位：{cat}")
    if hc:
        bits.append(f"人数：{hc}")
    if edu:
        bits.append(f"学历：{edu}")
    if age:
        bits.append(f"年龄：{age}")
    if end:
        bits.append(f"截止：{end}")
    return "；".join(bits)


def _published_date(pub: str) -> str:
    """发布时间归一成 YYYY-MM-DD。

    微信读书接口给的是 Unix 秒级时间戳（"1791198096"），
    RSS 给的是 RFC822（"Mon, 06 Oct 2026 09:00:00 GMT"），
    手工填的可能是 "2026-10-06"。三种都要认，否则报告里会冒出裸时间戳。
    """
    s = (pub or "").strip()
    if not s:
        return ""
    # 纯数字 → Unix 时间戳（10 位秒 / 13 位毫秒）
    if re.fullmatch(r"\d{10}", s):
        try:
            import datetime as _dt
            return _dt.datetime.fromtimestamp(int(s)).strftime("%Y-%m-%d")
        except Exception:
            pass
    if re.fullmatch(r"\d{13}", s):
        try:
            import datetime as _dt
            return _dt.datetime.fromtimestamp(int(s) / 1000).strftime("%Y-%m-%d")
        except Exception:
            pass
    ds = _dates_in(s)
    if ds:
        return ds[0]
    m = re.search(r"(\d{1,2})\s+(\w{3})\s+(\d{4})", s)
    if m:
        months = {mm: i + 1 for i, mm in enumerate(
            ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}
        mo = months.get(m.group(2))
        if mo:
            return f"{int(m.group(3)):04d}-{mo:02d}-{int(m.group(1)):02d}"
    return s[:10]


# ---------------------------------------------------------------- rule 模式

def extract_rule(article: Article, account: str = "") -> JobPost:
    text = article.plain
    start, end, _seg_raw = _apply_window(text)

    units = re.findall(r"([\u4e00-\u9fa5]{2,18}(?:局|委员会|集团|医院|学校|中心|办公室|管委会|人民政府|组织部|公司))", text)
    unit = guess_unit(article.title)
    if not unit and units:
        unit = units[0]

    phones = list(dict.fromkeys(_PHONE_RE.findall(text)))
    emails = [e for e in dict.fromkeys(_EMAIL_RE.findall(text))
              if not any(d and d.lower() in e.lower() for d in _CONTACT_EMAIL_DENY)]
    contact = "；".join(phones[:3] + emails[:2])

    job = JobPost(
        article_title=article.title,
        url=article.link,
        published=_published_date(article.published),
        account=account,
        unit=unit,
        category=guess_category(article.title, text),
        headcount=_headcount(text),
        education=_education(text),
        major=_seg(text, "专业要求", "所学专业", "专业条件", span=120),
        age=_age(text),
        location=_seg(text, "工作地点", "工作地区", span=60),
        apply_start=start,
        apply_end=end,
        apply_method=_apply_method(text),
        exam=_exam(text),
        salary=_salary(text, article.title),
        contact=contact,
        extract_mode="rule",
    )
    if not job.apply_method:
        urls = _URL_RE.findall(text)
        if urls:
            job.apply_method = urls[0]
    job.highlights = _highlights(job.published, job.unit, job.category,
                                 job.headcount, job.education, job.age, job.apply_end)
    return job


def _age(text: str) -> str:
    ages: List[int] = []
    for m in re.finditer(r"(\d{2})\s*周岁", text):
        ages.append(int(m.group(1)))
    if not ages:
        return ""
    lo, hi = min(ages), max(ages)
    if lo == hi:
        return f"{lo} 周岁"
    # "18周岁以上、35周岁以下" → 18—35
    return f"{lo}—{hi} 周岁"


# ---------------------------------------------------------------- llm 模式

_LLM_SYSTEM = "你是政务公告信息抽取助手，只输出 JSON，不要任何解释文字。"

_LLM_SCHEMA = {
    "jobs": [{
        "unit": "招聘单位", "category": "岗位类别", "headcount": "招聘人数",
        "education": "学历要求", "major": "专业要求", "age": "年龄要求",
        "location": "工作地点", "apply_start": "YYYY-MM-DD", "apply_end": "YYYY-MM-DD",
        "apply_method": "报名方式与入口", "exam": "笔试面试安排",
        "salary": "薪酬待遇", "contact": "联系方式",
    }]
}


def extract_llm(article: Article, llm: Dict[str, Any], account: str = "") -> List[JobPost]:
    base = (llm.get("base_url") or "").rstrip("/")
    key = llm.get("api_key") or ""
    if not base or not key:
        raise RuntimeError("未配置 LLM base_url / api_key，回退到 rule 模式")

    prompt = (
        "从下面这篇公众号招聘公告中抽取结构化信息。\n"
        "要求：\n"
        "1) 一篇文章若涉及多个招聘单位或多个批次，输出多条记录；\n"
        "2) 找不到的字段留空字符串，不要编造；\n"
        "3) 日期统一转成 YYYY-MM-DD；\n"
        f"4) 严格按此 JSON 结构输出：{json.dumps(_LLM_SCHEMA, ensure_ascii=False)}\n\n"
        f"标题：{article.title}\n发布时间：{article.published}\n正文：\n{article.plain[:8000]}"
    )
    resp = requests.post(
        f"{base}/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": llm.get("model") or "gpt-4o-mini",
            "temperature": llm.get("temperature", 0),
            "messages": [
                {"role": "system", "content": _LLM_SYSTEM},
                {"role": "user", "content": prompt},
            ],
        },
        timeout=90,
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    m = re.search(r"\{[\s\S]*\}", content)
    if not m:
        raise RuntimeError("模型未返回可解析的 JSON")
    data = json.loads(m.group(0))

    jobs: List[JobPost] = []
    for idx, item in enumerate(data.get("jobs") or []):
        job = JobPost(
            article_title=article.title, url=article.link,
            published=_published_date(article.published), account=account,
            extract_mode="llm", seq=idx,
        )
        for k, v in item.items():
            if hasattr(job, k) and v:
                setattr(job, k, str(v).strip())
        job.highlights = _highlights(job.published, job.unit, job.category,
                                     job.headcount, job.education, job.age, job.apply_end)
        jobs.append(job)
    if not jobs:
        raise RuntimeError("模型返回 jobs 为空")
    return jobs


# ---------------------------------------------------------------- 对外入口

def extract_jobs(articles: List[Article], cfg: Dict[str, Any]) -> List[JobPost]:
    ecfg = cfg.get("extract", {})
    mode = (ecfg.get("mode") or "rule").lower()
    account = cfg["source"].get("account_name", "")
    jobs: List[JobPost] = []

    # 允许从 config.yaml 追加「运营方邮箱域名」，屏蔽公众号自己的投稿/合作邮箱
    extra = ecfg.get("contact_email_deny") or []
    global _CONTACT_EMAIL_DENY
    _CONTACT_EMAIL_DENY = list(dict.fromkeys(_CONTACT_EMAIL_DENY + [str(d) for d in extra]))

    for art in articles:
        if mode == "llm":
            try:
                jobs.extend(extract_llm(art, ecfg.get("llm", {}), account))
                continue
            except Exception as exc:  # 兜底，绝不让流水线断掉
                print(f"  [warn] LLM 抽取失败，回退 rule：{exc}")
        jobs.append(extract_rule(art, account))
    return jobs
