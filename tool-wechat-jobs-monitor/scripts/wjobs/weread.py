# -*- coding: utf-8 -*-
"""免 Docker 的采集源：直接调用微信读书的公众号接口。

为什么值得自己写这一层？
    we-mp-rss 本质上也只是「浏览器登录微信读书 → 调 weread 接口 → 转成 RSS」。
    如果你只盯一两个公众号，完全没必要为它跑一整套 FastAPI + Vue 前端服务。
    这个模块把最核心的 3 个接口抽出来，零服务、零 Docker，单文件就能跑。

前置条件（就两个）：
    1. 一个微信读书账号（建议小号），并在微信读书里「关注」目标公众号；
    2. 在 Chrome / Edge 里登录过 https://weread.qq.com —— cookie 自动读取，
       不用你手动去 F12 里复制粘贴那串 wr_skey。

合规声明：使用你自己登录态下的接口读取你自己能读到的内容，仅用于个人阅读与线索聚合。
"""
from __future__ import annotations

import os
import re
import sys
import time
from typing import Any, Dict, List, Optional

import requests

from .fetch import Article, html_to_text

BASE = "https://weread.qq.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36")


class WeReadError(RuntimeError):
    pass


def _pick(d: Dict[str, Any], *keys: str, default: Any = "") -> Any:
    for k in keys:
        v = d.get(k)
        if v:
            return v
    return default


def cookie_from_browser(browser: str = "chrome") -> str:
    """从本机浏览器里自动提取 weread.qq.com 的 cookie。

    Chrome/Edge 的 cookie 文件是加密的，browser-cookie3 会用 Windows DPAPI 解密，
    所以需要：① 该浏览器登录过 weread.qq.com；② 在同一台机器、同一个 Windows 账户下运行。
    """
    try:
        import browser_cookie3  # 可选依赖，没装就走手动 cookie
    except ImportError:
        raise WeReadError(
            "未安装 browser-cookie3，无法自动读 cookie。\n"
            "  pip install browser-cookie3\n"
            "或者改用手动方式：浏览器打开 weread.qq.com → F12 → Network → "
            "任选一个请求的 Cookie 请求头 → 粘到 config.yaml 的 source.weread.cookie"
        )

    loaders = {
        "chrome": "chrome", "edge": "edge", "brave": "brave",
        "firefox": "firefox", "safari": "safari",
    }
    name = loaders.get((browser or "chrome").lower())
    if name is None:
        raise WeReadError(f"不支持的浏览器: {browser}")
    try:
        jar = getattr(browser_cookie3, name)(domain_name="weread.qq.com")
    except Exception as exc:
        raise WeReadError(
            f"读取 {browser} 的 cookie 失败：{exc}\n"
            "常见原因：\n"
            "  ① 该浏览器没登录 weread.qq.com（先打开网页扫码登录）；\n"
            "  ② Chrome 正在运行并锁住 cookie 文件 —— 关掉浏览器或改用 Edge；\n"
            "  ③ Windows 下解密 cookie 有时需要管理员权限 —— 以管理员身份重跑，\n"
            "     或直接用手动 cookie（见下方 manual 方式）。"
        )
    cookie = "; ".join(f"{c.name}={c.value}" for c in jar)
    if "wr_skey" not in cookie:
        raise WeReadError(
            f"在 {browser} 里没找到 weread.qq.com 的登录 cookie（缺 wr_skey）。\n"
            "请先用该浏览器打开 https://weread.qq.com 扫码登录，再重跑。"
        )
    return cookie


def cookie_auto(order: Optional[List[str]] = None) -> tuple[str, str]:
    """依次尝试多个浏览器，返回 (cookie, 命中的浏览器名)。

    只在「真正可能成功」的浏览器上尝试：
      - 未安装的浏览器直接跳过（别再为一个不存在的 Chrome 白报错）
      - Edge/Chrome 现在对 cookie 库加了独占锁，读文件基本无望，
        这类错误会被归类为「锁死」，并在全失败时给出对症的替代方案。
    """
    chain = list(order or ["chrome", "edge", "brave", "firefox"])
    tried: List[str] = []
    locked: List[str] = []
    last: Optional[WeReadError] = None

    for b in chain:
        if b in ("edge", "chrome", "brave") and not _browser_installed(b):
            print(f"  [info] 跳过 {b}：未安装")
            continue
        try:
            return cookie_from_browser(b), b
        except WeReadError as exc:
            last = exc
            tried.append(b)
            if "requires admin" in str(exc).lower() or "共享冲突" in str(exc):
                locked.append(b)
            print(f"  [info] {b} 读取失败，换下一个")

    tips = []
    if locked:
        tips.append(
            f"{'、'.join(locked)} 的 cookie 数据库被浏览器独占锁定"
            "（这是 Edge/Chrome 新版防止 cookie 被第三方读取的机制，跟登录状态无关）"
        )
    tips.append("改用 CDP 方式自动获取（推荐，不用关浏览器）：\n"
                "      python scripts/get_cookie.py --browser edge")
    tips.append("或手动获取：浏览器打开 weread.qq.com → F12 → Network → 刷新 → "
                "复制请求头里的 Cookie 整行 → 填到 config.yaml 的 source.weread.cookie\n"
                "      （并把 cookie_from 改成 manual；也可跑 python scripts/get_cookie.py --manual 看指引）")

    raise WeReadError(
        "自动读取浏览器 cookie 失败。\n原因：" + "；".join(tips)
    )


def _browser_installed(browser: str) -> bool:
    local = os.environ.get("LOCALAPPDATA", "")
    mapping = {
        "edge": os.path.join(local, "Microsoft", "Edge", "User Data"),
        "chrome": os.path.join(local, "Google", "Chrome", "User Data"),
        "brave": os.path.join(local, "BraveSoftware", "Brave-Browser", "User Data"),
    }
    path = mapping.get(browser)
    if path is None:
        return True  # firefox 等交给 browser_cookie3 自己判断
    return os.path.isdir(path)


class WeReadClient:
    def __init__(self, cookie: str, timeout: int = 15):
        if not cookie:
            raise WeReadError("cookie 为空")
        self.timeout = timeout
        self.s = requests.Session()
        self.s.headers.update({
            "User-Agent": UA,
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://weread.qq.com/",
            "Cookie": cookie,
        })

    # ---------------------------------------------------------------- 基础请求

    def _get(self, path: str, **params: Any) -> Any:
        r = self.s.get(f"{BASE}{path}", params=params, timeout=self.timeout)
        try:
            data = r.json()
        except Exception:
            raise WeReadError(f"{path} 返回非 JSON（HTTP {r.status_code}）：{r.text[:160]}")
        if isinstance(data, dict) and data.get("errCode") not in (0, None):
            raise WeReadError(f"{path} -> errCode={data.get('errCode')} "
                              f"{data.get('errMsg')}（多半是 cookie 过期，重新扫码登录）")
        return data

    # ---------------------------------------------------------------- 接口封装

    def list_articles(self, book_id: str, offset: int = 0, count: int = 20) -> List[Dict[str, Any]]:
        """文章列表。

        实测返回结构（2026-10）：
            {"reviews": [{"createTime":…, "subReviews": [
                {"reviewId": "MP_WXS_xxx_token",
                 "review": {"createTime":…, "mpInfo": {
                     "title":…, "content":…(摘要), "time":…,
                     "originalId":…, "mp_name":…, "readNum":…}}}]}]}
        早期版本是扁平的 articles 数组，所以下面两种都兼容。
        """
        data = self._get("/web/mp/articles", bookId=book_id, offset=offset, count=count)
        if not isinstance(data, dict):
            return []

        # 结构 A：reviews[].subReviews[].review.mpInfo
        reviews = data.get("reviews")
        if isinstance(reviews, list) and reviews:
            out: List[Dict[str, Any]] = []
            for grp in reviews:
                subs = (grp or {}).get("subReviews") or []
                for sub in subs:
                    inner = (sub or {}).get("review") or {}
                    mp = inner.get("mpInfo") or {}
                    rid = sub.get("reviewId") or inner.get("reviewId") or ""
                    out.append({
                        "reviewId": rid,
                        "title": mp.get("title") or "",
                        "summary": mp.get("content") or "",
                        "publishTime": mp.get("time") or inner.get("createTime") or 0,
                        "mp_name": mp.get("mp_name") or "",
                        "readNum": mp.get("readNum") or 0,
                    })
            return out

        # 结构 B：扁平数组（老版本）
        for key in ("articles", "mpArticles", "items", "data", "list"):
            v = data.get(key)
            if isinstance(v, list) and v:
                return v
        return []

    def account_name(self, book_id: str) -> str:
        """从接口响应里顺手带出公众号名称，用于校验 book_id 是不是想要的那个号。"""
        try:
            items = self.list_articles(book_id, offset=0, count=1)
            if items:
                return items[0].get("mp_name") or ""
        except WeReadError:
            pass
        return ""

    def article_content(self, review_id: str) -> str:
        """文章正文 HTML。

        注意：/web/mp/content 返回的是**整个微信读书阅读页的 HTML**（约 4 MB），
        不是 JSON。所以这里绝不能走 _get()（它强制 r.json()，会直接抛错）。
        实测（2026-10）：参数名就是 reviewId，且必须传完整的
        「MP_WXS_xxxx_token」形式；只传 token 段会返回空字符串。
        """
        if not review_id:
            return ""
        r = self.s.get(f"{BASE}/web/mp/content",
                       params={"reviewId": review_id}, timeout=self.timeout)
        if r.status_code != 200:
            raise WeReadError(f"/web/mp/content HTTP {r.status_code}")
        html = r.text or ""
        if not html:
            raise WeReadError("/web/mp/content 返回空内容（reviewId 可能不完整）")
        # 页面里正文在 <div id="js_content"> 内；优先剥出正文，
        # 拿不到就整页交给下游 html_to_text 兜底。
        m = re.search(r'<div[^>]+id="js_content"[^>]*>(.*?)</div>\s*</div>',
                      html, re.S)
        if m:
            return m.group(1)
        m = re.search(r'<div[^>]+id="js_content"[^>]*>(.*?)(?=<div[^>]+id="js_)',
                      html, re.S)
        if m:
            return m.group(1)
        return html

    def subscriptions(self) -> List[Dict[str, Any]]:
        """已订阅（加过书架）的公众号列表，用来找目标号的 bookId。"""
        try:
            data = self._get("/web/shelf/bookIds")
        except WeReadError:
            return []
        for key in ("bookIds", "books", "data", "list"):
            v = data.get(key) if isinstance(data, dict) else None
            if isinstance(v, list) and v:
                return v
        return []

    # ---------------------------------------------------------------- 组装 Article

    def fetch(self, book_id: str, limit: int = 30, with_content: bool = True) -> List[Article]:
        raw: List[Dict[str, Any]] = []
        offset = 0
        while len(raw) < limit:
            batch = self.list_articles(book_id, offset=offset, count=20)
            if not batch:
                break
            raw.extend(batch)
            if len(batch) < 20:
                break
            offset += len(batch)
        raw = raw[:limit]

        arts: List[Article] = []
        for it in raw:
            review = str(_pick(it, "reviewId", "review_id", "id"))
            arts.append(Article(
                title=str(_pick(it, "title", "name")),
                link=review_to_url(review),
                published=str(_pick(it, "publishTime", "publish_time", "published",
                                    "createTime", "updateTime")),
                summary=str(_pick(it, "summary", "abstract", "intro", "desc")),
            ))
            # 把完整 reviewId 挂到对象上：正文接口要求「MP_WXS_xxxx_token」全量，
            # 不能从短链里反推（短链只有 token 段，必空）。_review_of 兜底只对
            # 那些 link 里恰好藏着全量 id 的情况有效。
            setattr(arts[-1], "_review_id", review)

        if with_content:
            for a in arts:  # 频率克制：串行 + 小间隔，别把接口惹毛
                rid = getattr(a, "_review_id", "") or _review_of(a)
                if rid:
                    try:
                        a.content = self.article_content(rid)
                    except WeReadError as exc:
                        print(f"  [warn] 正文拉取失败，保留摘要：{exc}")
                time.sleep(0.4)
        return arts


def review_to_url(review_id: str) -> str:
    """reviewId → mp.weixin.qq.com 原文直链。

    reviewId 形如 `MP_WXS_3925849039_<token>`，token 段就是 /s/ 后的短链。

    ⚠️ **token 里的 `~` 必须还原成 `_`**（2026-10-07 实测）。

    微信短链 token 是 Base64 URL-safe 编码，字符集为 `A-Za-z0-9-_`，
    **不含 `~`**。微信读书在 reviewId 里把 `_` 写成了 `~`——
    因为 `_` 正是它自己的前缀分隔符（`MP_WXS_xxx_token`），直接放会歧义。

    不做这层还原的后果：`/s/<含~的token>` 一律返回一个 31KB 的
    「参数错误」页（HTTP 仍是 200，所以静默失败）。实测：
        sR1t5~EWOZANzk3oLfz1Zg  → 参数错误（31613 字节）
        sR1t5_EWOZANzk3oLfz1Zg  → 正常文章（3879458 字节）
    用户点邮件里的「查看原文」打不开，就是这个原因。

    格式不确定时返回空串，宁可不给链接，也不给错链接。
    """
    if not review_id:
        return ""
    if "_" in review_id:
        token = review_id.rsplit("_", 1)[-1]
    else:
        token = review_id
    token = token.replace("~", "_")      # 还原微信读书的转义
    if not token or len(token) < 8 or "/" in token or " " in token:
        return ""
    return f"https://mp.weixin.qq.com/s/{token}"


# ---------------------------------------------------------------- bookId 识别

# 公众号 bookId 的明文前缀，其十六进制形式为 4d505f5758535f
_BOOKID_PREFIX = "MP_WXS_"


def parse_book_id(text: str) -> str:
    """从各种输入里认出 bookId。

    支持四种写法，用户粘什么都能认：
        1. 已是干净 bookId：MP_WXS_3222425727
        2. 阅读页完整链接：https://weread.qq.com/web/mp/reader/647423d224d505...
        3. 纯十六进制编码串：647423d224d505f5758535f33323232343235373237d5e
        4. 半截编码串（前缀部分被截掉）

    原理：微信读书把 bookId 按 ASCII 逐字节转十六进制，拼在固定前缀 647423d2 后面。
    所以只要在串里定位到 'MP_WXS_' 的十六进制 4d505f5758535f，
    从该处起按两位一组解 ASCII，直到遇到解不出可见字符或格式不合法为止。
    """
    text = (text or "").strip()
    if not text:
        return ""

    # 情况 1：已经是 bookId
    m = re.search(r"MP_WXS_\d+", text)
    if m:
        return m.group(0)

    # 提取候选编码串（去掉 URL 与查询参数，只留十六进制）
    cand = text
    if "://" in cand:
        cand = cand.split("?")[0].rstrip("/").split("/")[-1]
    cand = re.sub(r"[^0-9a-fA-F]", "", cand)
    if not cand:
        return ""

    # 情况 2/3/4：在串里找 'MP_WXS_' 的十六进制位置
    hex_prefix = _BOOKID_PREFIX.encode("ascii").hex()  # 4d505f5758535f
    idx = cand.find(hex_prefix)
    if idx < 0:
        return ""

    body = cand[idx:]
    # 从前缀开始每两位一解；末尾奇数字符直接丢弃（补位用）
    if len(body) % 2:
        body = body[:-1]

    out = []
    for i in range(0, len(body), 2):
        try:
            ch = chr(int(body[i:i + 2], 16))
        except ValueError:
            break
        # 必须用 ASCII 白名单判断：Python 的 str.isalnum() 对 'Õ' 这类
        # 拉丁字母也返回 True，会把尾部的补位字节一起吃进来，导致正则失配。
        if not (ch.isascii() and (ch.isdigit() or "A" <= ch <= "Z" or ch == "_")):
            break
        out.append(ch)

    decoded = "".join(out)
    m = re.fullmatch(r"(MP_WXS_\d+)", decoded)
    return m.group(1) if m else ""


def extract_book_id_from_url(url: str) -> str:
    """从阅读页/分享链接里取出 bookId；取不到返回空串。"""
    return parse_book_id(url)


def _review_of(a: Article) -> str:
    """从已生成的原文链接里把 token 取回来当 reviewId 用（兜底路径）。

    注意：a.link 里的 token 已被 review_to_url 还原过 `~`→`_`，
    而正文接口要的是**原始 reviewId**。这里只补回前缀，
    token 段保持链接里的样子 —— 正常路径（fetch 里挂的 _review_id）
    比这条兜底可靠得多，只有在链接里恰好藏着全量 id 时才用得上。
    """
    if not a.link or "/s/" not in a.link:
        return ""
    return a.link.rsplit("/s/", 1)[-1]


# ---------------------------------------------------------------- CLI 自测

def _client_from_args(cookie: str, browser: str, use_browser: bool) -> WeReadClient:
    if not cookie and use_browser:
        preferred = (browser or "chrome").lower()
        order = [preferred] + [b for b in ("chrome", "edge", "brave", "firefox")
                               if b != preferred]
        cookie, used = cookie_auto(order)
        print(f"[ok] 已从 {used} 读到 weread cookie（长度 {len(cookie)}）")
    return WeReadClient(cookie)


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    p = argparse.ArgumentParser(description="微信读书公众号接口直连（免 Docker 采集源）")
    p.add_argument("cmd", choices=["subs", "list", "probe", "parse"],
                   help="subs=列出已订阅；list=列出某号文章；probe=检查登录态；parse=从链接解析 bookId")
    p.add_argument("book_id", nargs="?", default="",
                   help="公众号 bookId，或直接粘阅读页链接/编码串（会自动识别）")
    p.add_argument("--cookie", default="", help="手动 cookie（不填则自动从浏览器读）")
    p.add_argument("--browser", default="chrome", help="chrome/edge/brave/firefox")
    p.add_argument("--limit", type=int, default=10)
    a = p.parse_args(argv)

    if a.cmd == "parse":
        got = parse_book_id(a.book_id)
        if got:
            print(f"bookId = {got}")
            print("\n写进 config.yaml：")
            print("source:")
            print("  type: weread")
            print("  weread:")
            print(f'    book_id: "{got}"')
            return 0
        print("[error] 没能从输入里认出 bookId。请粘贴微信读书阅读页链接或 MP_WXS_ 开头的 ID。",
              file=sys.stderr)
        return 1

    # list 模式允许直接粘链接
    book_id = parse_book_id(a.book_id) or a.book_id

    try:
        c = _client_from_args(a.cookie, a.browser, not a.cookie)
        if a.cmd == "probe":
            items = c.list_articles(book_id or "MP_WXS_1", offset=0, count=1)
            print("登录态正常，接口可访问。条目数：", len(items))
        elif a.cmd == "subs":
            subs = c.subscriptions()
            print("已订阅：" if subs else "没读到订阅列表（接口可能已变更，改用浏览器地址栏手动取 bookId）")
            for s in subs[:50]:
                print("  ", s if not isinstance(s, dict) else
                      f"{_pick(s,'title','name','bookId')}  |  {_pick(s,'bookId','id')}")
        else:
            if not book_id:
                print("需要 bookId，可直接粘链接：\n"
                      "  python -m src.weread list \"https://weread.qq.com/web/mp/reader/647423d2...\"")
                return 1
            for art in c.fetch(book_id, limit=a.limit, with_content=False):
                print(f"  {art.published[:10]}  {art.title[:44]:46s} {art.link}")
    except WeReadError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
