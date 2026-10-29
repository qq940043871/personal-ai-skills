#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_site.py - 把 notes/ 下的章节笔记 Markdown 编译成单文件学习网站 HTML。

用法:
    # 最省事：只给书籍文件夹（init_book.py 建的），路径全推导
    python build_site.py --book D:/books/深入分析JavaWeb

    # 非技术书（无代码，概念/思想/管理类）：固定小节用「关键论断」替代「代码要点」
    python build_site.py --book D:/books/失控 --profile prose

    # 手动指定
    python build_site.py --notes <notes_dir> --out <site.html> [--map map.json]
                         [--title "书名"] [--subtitle "副标题"]

设计要点:
- 解析完全自研（不依赖 markdown 库），只认 references/notes-format.md 约定的层级。
- 产物是单文件 HTML：CSS/JS 全内联，零 CDN，双击即开、可离线、可随意拷走。
- 模板在 assets/site_template.html，改样式改模板即可，不必动本文件。
- map.json 中登记但 notes/ 里没有的章节，会渲染成"待补充"占位，站点结构保持完整。
- --book 会自动推导 notes/map/out；未显式给 --out 时输出 <书籍文件夹>/index.html。
- --profile 取代了历史做法「把本脚本复制进书内 _build.py 再 str.replace 打 5 处补丁」，
  现在无需复制、无需补丁、无需手动传 --template。

profile 差异（仅影响章末第 2 个固定小节的名称与统计条文案，其余解析逻辑完全一致）:
    tech（默认）  代码要点        统计条「代码片段」
    prose         关键论断        统计条「关键论断」
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TEMPLATE = os.path.join(HERE, "..", "assets", "site_template.html")

# --------------------------------------------------------------------------
# profile：书籍类型决定章末固定小节的措辞
# --------------------------------------------------------------------------
PROFILES = {
    "tech": {
        "code_section": "代码要点",
        "code_stat": "代码片段",
        "code_stat_visible": True,
        "hero_tag": "PDF 书籍要点学习站",
        "hero_chips": "✓ 打卡进度本地保存|⌕ 全文关键词检索|◐ 深/浅色主题|A± 字号与宽读排版|? 自测题点开看答案",
        "footer": "由 PDF 书籍要点整理流水线生成 · 单文件离线可用 · 内容忠于原书章节",
    },
    "prose": {
        "code_section": "关键论断",
        "code_stat": "关键论断",
        "code_stat_visible": True,
        "hero_tag": "书籍要点导读站",
        "hero_chips": "✓ 打卡进度本地保存|⌕ 全文关键词检索|◐ 深/浅色主题|A± 字号与宽读排版|? 自测题点开看答案",
        "footer": "由书籍要点整理流水线生成 · 单文件离线可用 · 内容忠于原书章节",
    },
    "prose-nocode": {
        # 无代码且统计条也不必显示该格（如《失控》当初的做法）
        "code_section": "关键论断",
        "code_stat": "关键论断",
        "code_stat_visible": False,
        "hero_tag": "书籍要点导读站",
        "hero_chips": "✓ 打卡进度本地保存|⌕ 全文关键词检索|◐ 深/浅色主题|A± 字号与宽读排版|? 自测题点开看答案",
        "footer": "由书籍要点整理流水线生成 · 单文件离线可用 · 内容忠于原书章节",
    },
}

# 当前生效的 profile（build() 入口设置；模块级读取避免把参数层层传下去）
ACTIVE = PROFILES["tech"]


def fixed_sections():
    """章末固定小节名 -> 内部 key。prose 类书籍第 2 项是「关键论断」。"""
    return {
        "核心概念": "concepts",
        ACTIVE["code_section"]: "code",
        "常见误区与深入理解": "pitfalls",
        "自测问题": "quiz",
        "本章收获": "takeaways",
    }


def panel_titles():
    return {
        "concepts": ("核心概念", "concepts"),
        "code": (ACTIVE["code_section"], "code"),
        "pitfalls": ("常见误区与深入理解", "pitfalls"),
        "quiz": ("自测问题", "quiz"),
        "takeaways": ("本章收获", "takeaways"),
    }


def resolve_template(explicit: str) -> str:
    """模板定位优先级：--template > 技能内 assets/ > 同目录 _template.html。

    历史坑：脚本被复制进书内 _extract/ 后，__file__ 变了，../assets/site_template.html 就找不到，
    当时靠打补丁改DEFAULT_TEMPLATE 解决。现在自动回退到同目录副本，省掉补丁。
    """
    if explicit:
        return explicit
    if os.path.isfile(DEFAULT_TEMPLATE):
        return DEFAULT_TEMPLATE
    local = os.path.join(HERE, "_template.html")
    if os.path.isfile(local):
        return local
    return DEFAULT_TEMPLATE  # 交由调用方报错，路径信息更明确


# --------------------------------------------------------------------------
# 行内 Markdown -> HTML
# --------------------------------------------------------------------------
def inline_md(s: str) -> str:
    """转义 + 行内代码 + 加粗 + 斜体 + 链接。"""
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # 行内代码先用占位符保护，避免被加粗规则误伤
    codes = []

    def _code(m):
        codes.append(m.group(1))
        return "\x00%d\x00" % (len(codes) - 1)

    s = re.sub(r"`([^`]+)`", _code, s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', s)
    for i, c in enumerate(codes):
        s = s.replace("\x00%d\x00" % i, "<code>%s</code>" % c)
    return s


def plain_text(s: str) -> str:
    """去掉 Markdown 标记，供搜索索引使用。"""
    t = re.sub(r"`([^`]+)`", r"\1", s)
    t = re.sub(r"\*\*([^*]+)\*\*", r"\1", t)
    t = re.sub(r"^\s*[-\d.]+[.、)]?\s*", "", t)
    return t.strip()


# --------------------------------------------------------------------------
# 行序列 -> 块列表
# --------------------------------------------------------------------------
CAPTION_RE = re.compile(r"^\s*(?://|#|--|;|/\*)\s*caption:\s*(.+?)\s*(?:\*/|-->)?\s*$", re.I)
CAPTION_XML_RE = re.compile(r"^\s*<!--\s*caption:\s*(.+?)\s*-->\s*$", re.I)
TABLE_CAP_RE = re.compile(r"^\*\*(表[^**]*)\*\*$")
LIST_RE = re.compile(r"^(\s*)(?:[-*+]\s+|\d+[.)]\s+)(.*)$")
# 「**标签**：…」要点边界（标签长度限制在 24 字内，避免把正文里的强调当标签）
POINT_LABEL_RE = re.compile(r"\*\*([^*\n]{1,24})\*\*\s*[：:]")
_BR_OPEN = "【「（《〔"
_BR_CLOSE = "】」）》〕"
# 要点自带的序号标记：第X / 其X / 路径X / ①…⑫。只认这几种，避免把正文里的普通数字
# 当序号（"1." "2)" 这类本来就由 Markdown 列表语法承载，不走本规则）。
_ORD_BODY = (r"(?:第\s*[0-9〇零一二三四五六七八九十百]+"
             r"|其[一二三四五六七八九十]+"
             r"|路径\s*[一二三四五六七八九十]+"
             r"|[①②③④⑤⑥⑦⑧⑨⑩⑪⑫])")
_ORD_TAIL_RE = re.compile(_ORD_BODY + r"\s*[，,、·.．:：]?\s*\Z")
_ORD_HEAD_RE = re.compile(r"^\s*" + _ORD_BODY + r"\s*[，,、·.．:：]?")
_ORD_HEAD_SPLIT_RE = re.compile(r"^(" + _ORD_BODY + r"\s*[，,、·.．:：]?)\s*")
# 「其一，**标签**——…」：序号已明示是枚举，标签后接冒号或破折号都算要点边界。
# 不能单凭破折号判定——笔记里的 —— 多数是句中强调 + 解释（实测 72 段会被误拆）。
ORD_LABEL_RE = re.compile(r"(" + _ORD_BODY + r")\s*[，,、·.．:：]?\s*\*\*([^*\n]{1,24})\*\*")
# 允许出现在序号标记之前的字符（句末标点/逗号顿号/换行）。用来确认它确实是列表序号而非正文。
_ORD_SAFE_PREV = "。！？；!?;\n，,、"


def point_starts(text: str):
    """找出一段文本里所有可作「要点边界」的位置（升序、去重）。

    两类边界：
      1) 「**标签**：…」——标签后紧跟冒号；
      2) 「其一，**标签**——…」——序号在前，标签后接冒号/破折号都算。
         第 2 类不能只看破折号：笔记里的 —— 多数是句中强调 + 解释，
         单按破折号拆会把叙述句误伤（实测《工业AI学习笔记》有 72 段会被拆错）。
    只认括号深度 0 处的边界，避免把套在【（内的并列说明误拆成两个要点。
    """
    cands = []
    for m in POINT_LABEL_RE.finditer(text):
        cands.append((m.start(), True))      # True：需向前吸收紧邻的序号
    for m in ORD_LABEL_RE.finditer(text):
        cands.append((m.start(1), False))    # 序号本身就在起点里
    cands.sort()

    out, depth, pos = [], 0, 0
    for st, absorb in cands:
        if absorb:
            j = st
            while j > 0 and text[j - 1] in " \t":
                j -= 1
            mm = _ORD_TAIL_RE.search(text[:j]) if j > 0 else None
            if mm:
                # 序号之前必须是句末标点/逗号顿号/行首，才认它是枚举序号（而非“第 3 组”这类正文）
                prev = text[:mm.start()].rstrip()
                if not prev or prev[-1] in _ORD_SAFE_PREV:
                    st = mm.start()
        for c in text[pos:st]:
            if c in _BR_OPEN:
                depth += 1
            elif c in _BR_CLOSE and depth > 0:
                depth -= 1
        pos = st
        if depth == 0 and (not out or st > out[-1]):
            out.append(st)
    return out


def items_carry_ordinal(items) -> bool:
    """要点自带序号（第一，/ ① / 路径二·）时改用无项目符号列表，免得「• 第二，」双重计数。"""
    if len(items) < 2:
        return False
    n = sum(1 for it in items if _ORD_HEAD_RE.match(it["text"]))
    return n >= 2 and n * 2 >= len(items)


# 只有标签没有内容的条目，例如单独一条 `**A**：`、`第二，**判定**：`。
_BARE_LABEL_RE = re.compile(
    r"^\s*(?:" + _ORD_BODY + r"\s*[，,、·.．:：]?\s*)?\*\*[^*\n]{1,24}\*\*\s*[：:]\s*$")


def para_or_points(text: str):
    """一段普通文本 -> 块列表。

    笔记里常见「**资产内涵**：…**旧计价**：…**判定**：…」这种多个要点挤在一行、
    全靠加粗标签分隔的写法；直接当一整段渲染就是一堵墙，所以在构建期按标签拆成
    要点列表（标签留在行首，前面若有引导语则单独成段；引导语很短则并入首条）。不足 2 个要点就保持原样。
    """
    starts = point_starts(text)
    if len(starts) < 2:
        return [{"type": "para", "text": text}]

    items = []
    for k, st in enumerate(starts):
        end = starts[k + 1] if k + 1 < len(starts) else len(text)
        seg = text[st:end].strip()
        if seg:
            items.append({"level": 0, "text": seg})

    # 「只有标签、没有内容」的条目必须并回下一条。
    # 触发场景：「**A**：**Cookie-Session 的缺点…**：…」，标签后面紧跟另一个标签，
    # 拆出来就是一条孤零零的 `**A**：`；下游按前缀识别语义的消费者（parse_quiz 找
    # `**A**：`）会因此拿到**空答案**，把真正的答案并进题干（《凤凰架构》ch06-q3/ch09-q5 实测）。
    merged = []
    for it in items:
        if merged and _BARE_LABEL_RE.match(merged[-1]["text"]):
            merged[-1]["text"] = (merged[-1]["text"] + it["text"]).strip()
        else:
            merged.append(it)
    items = [it for it in merged if not _BARE_LABEL_RE.match(it["text"])]
    if len(items) < 2:
        return [{"type": "para", "text": text}]

    out = []
    lead = text[:starts[0]].strip()
    # 引导语若是短小的“列表头”（「第一，」「第 0–30 天·」「三条原则」），且不以句末标点
    # 收尾，就直接并入首条要点，避免它被孤立成一段；否则作为独立引导段保留。
    if lead and len(lead) <= 30 and lead[-1] not in "。！？；：":
        items[0]["text"] = lead + items[0]["text"]
        lead = ""
    if lead:
        out.append({"type": "para", "text": lead})
    ord_mode = items_carry_ordinal(items)
    if ord_mode:
        # 无项目符号后序号是唯一的条目标记，拆出来单独上色，扫读时好定位
        for it in items:
            mm = _ORD_HEAD_SPLIT_RE.match(it["text"])
            if mm:
                it["ord"] = mm.group(1)
                it["text"] = it["text"][mm.end():]
    out.append({"type": "list", "items": items, "ord": ord_mode})
    return out


def is_table_sep(line: str) -> bool:
    t = line.strip()
    if not t.startswith("|"):
        return False
    return bool(re.match(r"^\|[\s:\-\|]+\|$", t))


def split_cells(row: str):
    t = row.strip()
    if t.startswith("|"):
        t = t[1:]
    if t.endswith("|"):
        t = t[:-1]
    return [c.strip() for c in t.split("|")]


def split_blocks(lines):
    """把一段连续的行切成块：[{type: para|table|code|list|quote}, ...]"""
    blocks = []
    i = 0
    n = len(lines)
    pending_caption = None

    while i < n:
        raw = lines[i]
        line = raw.rstrip()
        s = line.strip()

        if not s:
            i += 1
            continue

        # 代码块
        if s.startswith("```"):
            lang = s[3:].strip().split()[0] if len(s) > 3 else "text"
            i += 1
            body = []
            while i < n and not lines[i].strip().startswith("```"):
                body.append(lines[i])
                i += 1
            i += 1  # 跳过收尾 ```
            caption = None
            if body:
                m = CAPTION_RE.match(body[0]) or CAPTION_XML_RE.match(body[0])
                if m:
                    caption = m.group(1)
                    body = body[1:]
            blocks.append({
                "type": "code",
                "lang": lang or "text",
                "caption": caption,
                "code": "\n".join(body).strip("\n"),
            })
            continue

        # 表格
        if s.startswith("|"):
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                if not is_table_sep(lines[i]):
                    rows.append(split_cells(lines[i]))
                i += 1
            if rows:
                blocks.append({
                    "type": "table",
                    "caption": pending_caption,
                    "header": rows[0],
                    "rows": rows[1:],
                })
            pending_caption = None
            continue

        # 独立的表标题行： **表 1-1 xxx**
        m = TABLE_CAP_RE.match(s)
        if m:
            pending_caption = m.group(1)
            i += 1
            continue

        # 列表
        if LIST_RE.match(line):
            items = []
            while i < n:
                m2 = LIST_RE.match(lines[i])
                if not m2:
                    if not lines[i].strip():
                        # 空行：若下一行还是列表项则继续（markdown 允许松散列表）
                        j = i + 1
                        while j < n and not lines[j].strip():
                            j += 1
                        if j < n and LIST_RE.match(lines[j]):
                            i = j
                            continue
                    break
                indent = len(m2.group(1)) // 2
                items.append({"level": min(indent, 2), "text": m2.group(2).strip()})
                i += 1
            blocks.append({"type": "list", "items": items})
            continue

        # 引用块 >text：去掉标记后按段落处理
        if s.startswith(">"):
            txt = re.sub(r"^\s*>\s?", "", line).strip()
            if txt:
                blocks.append({"type": "para", "text": txt})
            i += 1
            continue

        # 段落：连续非空、非特殊起始的行合并
        para = []
        while i < n:
            t = lines[i].strip()
            if not t or t.startswith("|") or t.startswith("```") or LIST_RE.match(lines[i]) \
                    or t.startswith("#") or t.startswith(">"):
                break
            para.append(t)
            i += 1
        if para:
            blocks.extend(para_or_points(" ".join(para)))
        elif i < n:
            # 安全网：任何未被上面分支消费的行走到这里，必须推进 i，否则死循环
            i += 1

    return blocks


# --------------------------------------------------------------------------
# 笔记文件 -> 章节结构
# --------------------------------------------------------------------------
def parse_note(text: str) -> dict:
    lines = text.replace("\r\n", "\n").split("\n")
    ch = {
        "num": "", "title": "", "subtitle": "",
        "pre_blocks": [],         # H1 之后、首个 ## 之前的内容（如无节的小引言）
        "sections": [],          # [{title, blocks:[...], cards:[...]}]
        "special": {},           # key -> blocks
        "order": [],             # 渲染顺序
    }
    buf = []
    target = None               # 当前块归属（list of blocks）
    FIXED = fixed_sections()    # 随 profile 变化，函数内取一次避免每行重建 dict

    def flush():
        nonlocal buf
        if buf and target is not None:
            target.extend(split_blocks(buf))
        buf = []

    cur_sec = None
    cur_mode = None             # "section" or fixed key
    for line in lines:
        s = line.strip()

        if s.startswith("# ") and not s.startswith("##"):
            flush()
            t = s[2:].strip()
            # 章号前缀覆盖 章/篇/部/部分 —— 合集类书（多篇长文汇编）标题是「第N篇」，
            # 早期版本只认「章」，导致这类书 H1 的 num 为空、章号不显示。
            m = re.match(r"^(第[^章篇部\s]*[章篇部][分]?)\s*(.*)$", t)
            if m:
                ch["num"], ch["title"] = m.group(1), m.group(2).strip()
            else:
                ch["title"] = t
            continue

        if s.startswith("> "):
            flush()
            # 只认紧跟 H1 之后的第一个引用块作为本章概括（subtitle）。
            # 正文里的后续引用块必须当作普通内容渲染，否则会覆盖概括、
            # 造成"第N章标题下显示第N+1章内容"的错配。
            if not ch["subtitle"] and not ch["sections"] and not ch["special"]:
                ch["subtitle"] = s[2:].strip()
            else:
                target = ch["sections"][-1]["blocks"] if ch["sections"] else None
                if target is None:
                    ch["pre_blocks"] = ch.get("pre_blocks", []) + [s]
                else:
                    target.extend(split_blocks([line]))
            continue

        if s.startswith("## "):
            flush()
            title = s[3:].strip()
            if title in FIXED:
                cur_mode = FIXED[title]
                ch["special"].setdefault(cur_mode, [])
                ch["order"].append({"kind": "special", "key": cur_mode})
                target = ch["special"][cur_mode]
                cur_sec = None
            else:
                cur_mode = "section"
                cur_sec = {"title": title, "blocks": []}
                ch["sections"].append(cur_sec)
                ch["order"].append({"kind": "section", "index": len(ch["sections"]) - 1})
                target = cur_sec["blocks"]
            continue

        if s.startswith("### "):
            flush()
            title = s[4:].strip()
            blk = {"type": "card", "title": title, "blocks": []}
            if cur_sec is None:
                # 固定小节里出现了 ###，就给它造一个匿名节承载
                cur_sec = {"title": "", "blocks": []}
                ch["sections"].append(cur_sec)
                ch["order"].append({"kind": "section", "index": len(ch["sections"]) - 1})
            # 卡片要挂到「当前容器」下：正文节挂 cur_sec["blocks"]，固定小节挂 special 的 blocks。
            # 注意不能挂 blk["blocks"]（那是卡片自己的正文，会造成自我嵌套）。
            (cur_sec["blocks"] if cur_mode == "section" else target).append(blk)
            target = blk["blocks"]
            continue

        buf.append(line)

    flush()
    return ch


# --------------------------------------------------------------------------
# 块 -> HTML
# --------------------------------------------------------------------------
def render_blocks(blocks, cls_prefix=""):
    if not blocks:
        return ""
    out = []
    # 连续的 card 打成网格，其余块全宽，尽量保持原文顺序
    grid = []
    def close_grid():
        if grid:
            out.append('<div class="cards">%s</div>' % "".join(grid))
            grid.clear()

    for b in blocks:
        if b["type"] == "card":
            grid.append(render_card(b))
        else:
            close_grid()
            out.append(render_block(b))
    close_grid()
    return "".join(out)


def render_block(b):
    t = b["type"]
    if t == "para":
        return '<p class="para">%s</p>' % inline_md(b["text"])
    if t == "table":
        cap = '<div class="tbl-cap">%s</div>' % inline_md(b["caption"]) if b.get("caption") else ""
        head = "".join("<th>%s</th>" % inline_md(c) for c in b["header"])
        rows = "".join(
            "<tr>%s</tr>" % "".join("<td>%s</td>" % inline_md(c) for c in r)
            for r in b["rows"]
        )
        return '<div class="tbl-wrap">%s<table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (cap, head, rows)
    if t == "list":
        return render_list(b["items"], "lst ord" if b.get("ord") else "lst")
    if t == "code":
        return render_code(b)
    return ""


def render_list(items, cls="lst"):
    if not items:
        return ""
    out = ['<ul class="%s">' % cls]
    for it in items:
        extra = " sub" if it["level"] >= 1 else ""
        pre = '<span class="ordn">%s</span>' % html.escape(it["ord"]) if it.get("ord") else ""
        out.append('<li class="li%s">%s%s</li>' % (extra, pre, inline_md(it["text"])))
    out.append("</ul>")
    return "".join(out)


def render_code(b):
    cap = '<div class="code-cap">%s</div>' % inline_md(b["caption"]) if b.get("caption") else ""
    return (
        '<div class="code-block">'
        '<div class="code-head"><span class="lang">%s</span>'
        '<button class="copy-btn" type="button">复制</button></div>'
        '%s<pre><code>%s</code></pre></div>'
    ) % (html.escape(b.get("lang", "text")), cap, html.escape(b.get("code", "")))


def card_search_text(b):
    parts = [b.get("title", "")]
    for blk in b.get("blocks", []):
        if blk["type"] == "para":
            parts.append(blk["text"])
        elif blk["type"] == "list":
            parts.extend(i["text"] for i in blk["items"])
        elif blk["type"] == "code":
            parts.append(blk.get("caption") or "")
            parts.append(blk.get("code", "")[:300])
        elif blk["type"] == "table":
            parts.append(blk.get("caption") or "")
            parts.extend(blk["header"])
            parts.extend(c for r in blk["rows"] for c in r)
    return " ".join(plain_text(p) for p in parts if p)


def render_card(b, cid=""):
    search = card_search_text(b).lower().replace('"', "&quot;")
    return (
        '<article class="card" data-id="%s" data-search="%s">'
        '<div class="card-top"><h4>%s</h4>'
        '<button class="done-btn" type="button" aria-label="标记已掌握">✓</button></div>'
        '<div class="card-body">%s</div></article>'
    ) % (cid, search, inline_md(b.get("title", "")), render_blocks(b.get("blocks", [])))


# --------------------------------------------------------------------------
# 自测问答解析
# --------------------------------------------------------------------------
Q_RE = re.compile(r"^\*\*Q\*\*\s*[：:]\s*(.*)$", re.I)
A_RE = re.compile(r"^\*\*A\*\*\s*[：:]\s*(.*)$", re.I)


def parse_quiz(blocks):
    qa = []
    flat = []
    for b in blocks:
        if b["type"] == "list":
            flat.extend(b["items"])
        elif b["type"] == "para":
            flat.append({"level": 0, "text": b["text"]})
    cur = None
    for it in flat:
        text = it["text"]
        mq = Q_RE.match(text)
        ma = A_RE.match(text)
        if mq:
            cur = {"q": mq.group(1).strip(), "a": ""}
            qa.append(cur)
        elif ma:
            if cur is None:
                cur = {"q": "", "a": ""}
                qa.append(cur)
            cur["a"] = (cur["a"] + " " + ma.group(1).strip()).strip()
        else:
            if cur is None:
                cur = {"q": text, "a": ""}
                qa.append(cur)
            elif cur["a"]:
                cur["a"] += " " + text
            else:
                cur["q"] = (cur["q"] + " " + text).strip()
    return qa


def render_quiz(qa, cid):
    if not qa:
        return ""
    items = []
    for i, q in enumerate(qa, 1):
        items.append(
            '<div class="qa" data-id="%s-q%d">'
            '<div class="q"><span class="qb">Q</span><div class="qt">%s</div></div>'
            '<button class="ans-btn" type="button">查看答案</button>'
            '<div class="a"><span class="ab">A</span><div class="at">%s</div></div>'
            '</div>' % (cid, i, inline_md(q["q"]), inline_md(q["a"]))
        )
    return '<div class="qa-list">%s</div>' % "".join(items)


# --------------------------------------------------------------------------
# 章节 -> HTML
# --------------------------------------------------------------------------
# ⚠ 不要在模块级把 panel_titles() 赋给常量：模块级求值发生在 build() 设置 ACTIVE 之前，
# 会把快照永远锁在默认 tech 上（表现为 --profile prose 生效了、面板标题却仍是「代码要点」）。
# 历史 bug：改profile 时踩过一次，24 章各渲染一个错名空面板。
PANEL_TITLES = None  # 由 render_chapter 首次调用时惰性初始化


def get_panel_titles():
    global PANEL_TITLES
    if PANEL_TITLES is None:
        PANEL_TITLES = panel_titles()
    return PANEL_TITLES


def render_chapter(ch, meta, cid):
    num = meta.get("num") or ch.get("num") or ""
    title = meta.get("title") or ch.get("title") or cid
    sub = ch.get("subtitle", "")
    pages = meta.get("book_pages", "")

    if not ch.get("sections") and not ch.get("special") and not ch.get("pre_blocks"):
        return (
            '<section class="chapter pending" id="%s" data-ch="%s">'
            '<div class="ch-pending"><span class="ch-num">%s</span>'
            '<h2>%s</h2><p class="pending-tip">本章要点尚未提取 · 书页 %s</p></div>'
            '</section>' % (cid, cid, html.escape(num), html.escape(title), html.escape(str(pages)))
        )

    # 章头「N 个知识点」同样要递归 + 含固定小节，否则和顶部统计条对不上
    def count_cards(blocks):
        n = 0
        for b in blocks or []:
            if b["type"] == "card":
                n += 1 + count_cards(b.get("blocks", []))
        return n

    n_cards = sum(count_cards(s["blocks"]) for s in ch["sections"])
    n_cards += sum(count_cards(b) for b in ch["special"].values())

    body = []
    if ch.get("pre_blocks"):
        body.append('<div class="sec">%s</div>' % render_blocks(ch["pre_blocks"]))
    for item in ch["order"]:
        if item["kind"] == "section":
            sec = ch["sections"][item["index"]]
            h = '<h3 class="sec-title">%s</h3>' % inline_md(sec["title"]) if sec["title"] else ""
            body.append('<div class="sec">%s%s</div>' % (h, render_blocks(sec["blocks"])))
        else:
            key = item["key"]
            blocks = ch["special"].get(key, [])
            if not blocks:
                continue
            label, cls = get_panel_titles()[key]
            if key == "quiz":
                inner = render_quiz(parse_quiz(blocks), cid)
            else:
                inner = render_blocks(blocks)
            body.append(
                '<div class="panel %s"><h3 class="panel-title">%s</h3><div class="panel-body">%s</div></div>'
                % (cls, label, inner)
            )

    meta_bits = []
    if pages:
        meta_bits.append("书页 %s" % pages)
    meta_bits.append("%d 个知识点" % n_cards)

    return (
        '<section class="chapter" id="%s" data-ch="%s">'
        '<header class="ch-head"><span class="ch-num">%s</span>'
        '<h2>%s</h2><p class="ch-sub">%s</p>'
        '<div class="ch-meta">%s</div></header>'
        '%s</section>'
    ) % (cid, cid, html.escape(num), html.escape(title), inline_md(sub),
         html.escape(" · ".join(meta_bits)), "".join(body))


# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------
def load_map(path):
    if not path or not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build(args):
    global ACTIVE
    if args.profile not in PROFILES:
        sys.exit("未知 profile: %s（可选 %s）" % (args.profile, "/".join(PROFILES)))
    ACTIVE = PROFILES[args.profile]

    # --book 模式：路径全从书籍文件夹推导
    if args.book:
        book_dir = os.path.abspath(args.book)
        if not args.map:
            cand = os.path.join(book_dir, "_extract", "map.json")
            args.map = cand if os.path.isfile(cand) else ""
        if not args.notes:
            args.notes = os.path.join(book_dir, "_extract", "notes")
        if not args.out:
            args.out = os.path.join(book_dir, "index.html")

    notes_dir = args.notes
    if not notes_dir or not os.path.isdir(notes_dir):
        sys.exit("笔记目录不存在: %s" % (notes_dir or "(未指定)"))

    book = load_map(args.map)
    chapters_meta = {}
    title = args.title
    subtitle = args.subtitle
    source_pdf = ""
    if book:
        title = title or book.get("title", "")
        subtitle = subtitle or book.get("subtitle", "")
        source_pdf = book.get("meta", {}).get("source_pdf", "")
        for c in book.get("chapters", []):
            chapters_meta[c["id"]] = c

    ids = sorted(chapters_meta.keys()) if chapters_meta else []
    # notes 目录里出现但 map 没登记的章节，也要带上
    for fn in sorted(os.listdir(notes_dir)):
        if fn.startswith("ch") and fn.endswith(".md"):
            cid = fn[:-3]
            if cid not in ids:
                ids.append(cid)
    if not ids:
        sys.exit("没有找到任何章节（检查 --notes 与 --map）")

    chapters_html = []
    nav_items = []
    stats = {"cards": 0, "code": 0, "quiz": 0, "done_ch": 0}

    def walk(blocks):
        """递归遍历块树，返回 (卡片数, 代码块数)。

        两个必须递归的理由（都是实测踩出来的）：
        1. 卡片内部还能再挂卡片（### 出现在卡片里），代码块也能出现在卡片正文里；
        2. ### 可以出现在**固定小节**里（如「核心概念」下再分卡片），所以要扫全部 special，
           不能只扫 sections + special['code']。
        历史 bug：Phoenix 统计报 536 卡片 / 115 代码块，DOM 实际 537 / 144。
        """
        cards = code = 0
        for b in blocks or []:
            if b["type"] == "card":
                cards += 1
                c2, k2 = walk(b.get("blocks", []))
                cards += c2
                code += k2
            elif b["type"] == "code":
                code += 1
        return cards, code

    for cid in ids:
        meta = chapters_meta.get(cid, {"num": "", "title": cid, "book_pages": ""})
        path = os.path.join(notes_dir, cid + ".md")
        ch = None
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                ch = parse_note(f.read())
            stats["done_ch"] += 1
            ch_cards = ch_code = 0
            for s in ch["sections"]:
                c2, k2 = walk(s["blocks"])
                ch_cards += c2
                ch_code += k2
            # 必须遍历**全部** special：### 允许出现在固定小节里（实测 ch04 的「核心概念」有 1 张）
            for _key, _blocks in ch["special"].items():
                c3, k3 = walk(_blocks)
                ch_cards += c3
                ch_code += k3
            stats["cards"] += ch_cards
            stats["code"] += ch_code
            stats["quiz"] += len(parse_quiz(ch["special"].get("quiz", [])))
        html_piece = render_chapter(ch or {"sections": [], "special": {}, "pre_blocks": [],
                                           "subtitle": "", "num": "", "title": ""}, meta, cid)
        # 给卡片编唯一 id（进度打卡用）：ch01-1、ch01-2 ...
        seq = [0]

        def _assign_id(m):
            seq[0] += 1
            return 'data-id="%s-%d"' % (cid, seq[0])

        html_piece = re.sub(r'data-id=""', _assign_id, html_piece)
        chapters_html.append(html_piece)
        nav_items.append(
            '<a class="nav-item%s" href="#%s"><span class="nav-num">%s</span>'
            '<span class="nav-title">%s</span></a>'
            % (" done" if ch else "", cid, html.escape(meta.get("num", "") or cid),
               html.escape(meta.get("title", "") or cid))
        )

    template_path = resolve_template(args.template)
    if not os.path.isfile(template_path):
        sys.exit("模板不存在: %s（可显式传 --template，或把模板放到脚本同目录的 _template.html）"
                 % template_path)
    with open(template_path, "r", encoding="utf-8") as f:
        tpl = f.read()

    total = len(ids)
    stat_cells = [
        '<div class="stat"><b>%d</b><span>章已整理 / 共 %d 章</span></div>' % (stats["done_ch"], total),
        '<div class="stat"><b>%d</b><span>知识点小节</span></div>' % stats["cards"],
    ]
    if ACTIVE["code_stat_visible"]:
        stat_cells.append('<div class="stat"><b>%d</b><span>%s</span></div>'
                          % (stats["code"], ACTIVE["code_stat"]))
    stat_cells.append('<div class="stat"><b>%d</b><span>自测题</span></div>' % stats["quiz"])
    stat_html = "".join(stat_cells)

    meta_html = " · ".join(x for x in [source_pdf, "共 %d 章" % total] if x)

    slug = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "-", (title or "book")).strip("-").lower() or "book"

    out_html = (tpl
                .replace("__TITLE__", html.escape(title or "技术书籍学习站"))
                .replace("__SUBTITLE__", inline_md(subtitle or ""))
                .replace("__META__", html.escape(meta_html))
                .replace("__STATS__", stat_html)
                .replace("__NAV__", "".join(nav_items))
                .replace("__CONTENT__", "".join(chapters_html))
                .replace("__TOTAL_CARDS__", str(stats["cards"]))
                .replace("__HERO_TAG__", html.escape(ACTIVE["hero_tag"]))
                .replace("__HERO_CHIPS__", "".join(
                    '<span class="chip">%s</span>' % html.escape(c)
                    for c in ACTIVE["hero_chips"].split("|")))
                .replace("__FOOTER__", html.escape(ACTIVE["footer"]))
                .replace("__SLUG__", slug))

    out_dir = os.path.dirname(os.path.abspath(args.out))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(out_html)

    # 编译期自检：占位符必须全部替换干净。残留 = 模板新增了 __XXX__ 但忘了在 build() 里接线，
    # 或者模板里写了别的占位符。这类问题肉眼极难发现，直接拦在编译阶段。
    leftover = sorted(set(re.findall(r"__[A-Z_]{2,}__", out_html)))
    if leftover:
        print("! 警告：产物仍有未替换占位符 %s" % leftover)

    print("OK -> %s" % os.path.abspath(args.out))
    print("   profile=%s · 章节 %d（已整理 %d）· 卡片 %d · %s %d · 自测 %d"
          % (args.profile, total, stats["done_ch"], stats["cards"],
             ACTIVE["code_stat"], stats["code"], stats["quiz"]))


def main():
    ap = argparse.ArgumentParser(description="把章节笔记编译成单文件学习网站")
    ap.add_argument("--book", default="", help="书籍文件夹（含 _extract/），自动推导 notes/map/out")
    ap.add_argument("--notes", default="", help="笔记目录（含 chNN.md）")
    ap.add_argument("--out", default="", help="输出 HTML 路径（默认 <书籍文件夹>/index.html）")
    ap.add_argument("--map", default="", help="map.json（章节登记表）")
    ap.add_argument("--title", default="", help="书名（默认取 map.json）")
    ap.add_argument("--subtitle", default="", help="副标题（默认取 map.json）")
    ap.add_argument("--template", default="", help="自定义模板 HTML")
    ap.add_argument("--profile", default="tech", choices=list(PROFILES),
                    help="书籍类型：tech=技术书（代码要点/代码片段，默认）；"
                         "prose=非技术书（关键论断）；prose-nocode=非技术书且统计条不显示该格")
    build(ap.parse_args())


if __name__ == "__main__":
    main()
