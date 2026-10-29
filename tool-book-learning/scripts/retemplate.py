#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""retemplate.py — 把已有的 index.html 重套为当前技能模板（外壳换新，内容 DOM 原样搬运）。

适用路线（SKILL.md 路线 D）：
  本书没有 _extract/notes/chNN.md，或站点是手工装配的（自制 CSS / 自制图解），
  不能走 build_site.py 重建——一重建就会把手工内容冲掉。
  此时只替换“外壳”（CSS + JS + hero + footer），
  <div class="content" id="content"> 与 <nav class="nav" id="nav"> 内部原样搬运。

与旧的手写 retemplate.py 的差别：
  * 书名/副标题/统计全部自动推导，不再硬编码在脚本里
  * --extra-css auto（默认）：自动把旧站 CSS 里“新模板没有的选择器”追加进新模板，
    避免《人工智能》这类书的自制 SVG 图解（.figbox/.figcap/.fig .tx …）丢样式
  * --dry-run 先看会搬什么，再决定是否落盘
  * 落盘前自动备份

用法：
    python retemplate.py --book D:/books/失控
    python retemplate.py --book D:/books/人工智能（第2版） --profile tech --dry-run
    python retemplate.py --html D:/books/x/index.html --extra-css none
"""
import argparse
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TEMPLATE = os.path.join(HERE, "..", "assets", "site_template.html")

CHIPS = {
    "tech": ["✓ 打卡进度本地保存", "⌕ 全文关键词检索", "◐ 深/浅色主题",
             "A± 字号与宽读排版", "? 自测题点开看答案"],
    "prose": ["✓ 小节打卡进度本地保存", "⌕ 全文关键词检索", "◐ 深/浅色主题",
              "? 自测题点开看答案", "⇔ 限宽 / 宽读切换"],
}
FOOTER = "由 PDF 书籍要点整理流水线生成 · 单文件离线可用 · 内容忠于原书章节"
HERO_TAG = "PDF 书籍要点学习站"

CONTENT_OPEN = '<div class="content" id="content">'
NAV_OPEN = '<nav class="nav" id="nav">'
EMPTY_TIP = '<div class="empty-tip"'


# --------------------------------------------------------------------------- #
# CSS 工具：把旧站里“新模板不认识的选择器”挑出来，追加到新模板后面
# --------------------------------------------------------------------------- #
def strip_comments(css):
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def split_rules(css):
    """拆成 [(prelude, body)]，body 内可能还有嵌套规则（@media）。"""
    rules, i, n = [], 0, len(css)
    while i < n:
        j = css.find("{", i)
        if j < 0:
            break
        prelude = css[i:j].strip()
        depth, k = 0, j
        while k < n:
            if css[k] == "{":
                depth += 1
            elif css[k] == "}":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        rules.append((prelude, css[j + 1:k].strip()))
        i = k + 1
    return rules


def is_orphan_selector(sel, new_css):
    """选择器在新模板里完全没出现过 -> 属于本书自定义样式，需要保留。"""
    sel = sel.strip()
    if not sel:
        return False
    classes = re.findall(r"\.([A-Za-z0-9_\-]+)", sel)
    if classes:
        tail = classes[-1]
        return re.search(r"\." + re.escape(tail) + r"\b", new_css) is None
    # 元素/属性选择器：整串比对
    return sel not in new_css


def orphan_css(old_css, new_css):
    """返回需要保留的旧 CSS 片段列表（@media 会连同条件一起保留）。"""
    def walk(css):
        kept = []
        for prelude, body in split_rules(css):
            p = prelude.strip()
            if p.startswith("@media"):
                # 递归时必须整块回传，不能把内层规则漏到外层——
                # 否则窄屏专用的规则会在桌面宽度下也生效（.backtop 位置错乱就是这么来的）
                sub = walk(body)
                if sub:
                    kept.append("%s{%s}" % (p, "\n".join(sub)))
                continue
            if p.startswith("@keyframes"):
                name = p.split()[1] if len(p.split()) > 1 else ""
                if name and name not in new_css:
                    kept.append("%s{%s}" % (p, body))
                continue
            if p.startswith("@"):
                continue  # @font-face / @import 等一律丢弃
            # 普通规则：按逗号拆分，只留下“孤儿”选择器
            orphan_sels = [s for s in p.split(",") if is_orphan_selector(s, new_css)]
            if orphan_sels:
                kept.append("%s{%s}" % (",".join(s.strip() for s in orphan_sels), body))
        return kept

    return walk(old_css)


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
def first_group(pattern, text, default=""):
    m = re.search(pattern, text, re.S)
    return m.group(1).strip() if m else default


def main():
    ap = argparse.ArgumentParser(description="把已有学习站重套为当前技能模板")
    ap.add_argument("--book", default="", help="书籍文件夹（含 _extract/）")
    ap.add_argument("--html", default="", help="站点 HTML（默认 <book>/index.html）")
    ap.add_argument("--out", default="", help="输出路径（默认原地覆盖）")
    ap.add_argument("--template", default="", help="模板（默认技能内 assets/site_template.html）")
    ap.add_argument("--profile", default="tech", choices=["tech", "prose"], help="影响 hero chips 文案")
    ap.add_argument("--title", default="", help="书名（默认取站点 <h1>）")
    ap.add_argument("--subtitle", default="", help="副标题（默认取站点 <p class=\"sub\"> 或留空）")
    ap.add_argument("--extra-css", default="auto", choices=["auto", "none"],
                    help="auto=自动保留旧站自定义 CSS（推荐）")
    ap.add_argument("--no-backup", action="store_true", help="不备份（默认会备份）")
    ap.add_argument("--dry-run", action="store_true", help="只统计不落盘")
    args = ap.parse_args()

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    book = os.path.abspath(args.book) if args.book else ""
    html = os.path.abspath(args.html) if args.html else os.path.join(book, "index.html")
    if not os.path.isfile(html):
        sys.exit("站点不存在: %s" % html)
    if not book:
        book = os.path.dirname(html)

    tpl_path = args.template or DEFAULT_TEMPLATE
    if not os.path.isfile(tpl_path):
        sys.exit("模板不存在: %s" % tpl_path)

    src = io.open(html, encoding="utf-8").read()
    tpl = io.open(tpl_path, encoding="utf-8").read()

    # ---- 1) 内容区 ----
    if CONTENT_OPEN not in src:
        sys.exit("内容区标记缺失: %s（本脚本只适用于模板结构一致的站点）" % CONTENT_OPEN)
    ci = src.index(CONTENT_OPEN) + len(CONTENT_OPEN)
    if EMPTY_TIP not in src[ci:]:
        sys.exit("empty-tip 标记缺失，无法定位内容区结尾")
    ei = src.index(EMPTY_TIP, ci)
    close_idx = src.rindex("</div>", ci, ei)
    content_inner = src[ci:close_idx]

    # ---- 2) 目录 ----
    if NAV_OPEN not in src:
        sys.exit("目录标记缺失: %s" % NAV_OPEN)
    ni = src.index(NAV_OPEN) + len(NAV_OPEN)
    nav_inner = src[ni:src.index("</nav>", ni)]

    # ---- 3) 统计（按内容区真实 DOM 数，不信任旧 hero 的硬编码数字） ----
    n_ch = len(re.findall(r'<section class="chapter"', content_inner))
    n_card = len(re.findall(r'<article class="card"', content_inner))
    n_code = len(re.findall(r'class="code-block"', content_inner))
    n_quiz = len(re.findall(r'class="qa"', content_inner))
    # 注意：<figure class="figbox"> 会被两条规则同时命中，必须用单次交替匹配避免重复计数
    n_fig = len(re.findall(r'<figure[^>]*class="figbox"|<figure|class="figbox"', content_inner))

    # ---- 4) 文案 ----
    title = args.title or first_group(r"<h1[^>]*>(.*?)</h1>", src) or \
        first_group(r"<title>(.*?)</title>", src) or os.path.basename(book)
    title = re.sub(r"<[^>]+>", "", title).strip()
    # 副标题：模板类名是 hero-sub，早期站点可能写作 sub，两者都要认
    subtitle = args.subtitle or first_group(r'<p class="(?:hero-)?sub"[^>]*>(.*?)</p>', src)
    subtitle = re.sub(r"<[^>]+>", "", subtitle).strip()

    # 源 PDF 名：① 书籍目录里的 .pdf ② 旧站 hero 的 meta 行（无 PDF 的书靠这条抢救）
    pdf_name = ""
    for f in os.listdir(book):
        if f.lower().endswith(".pdf"):
            pdf_name = f
            break
    if not pdf_name:
        old_meta = re.sub(r"<[^>]+>", "", first_group(r'<div class="meta"[^>]*>(.*?)</div>', src))
        m = re.search(r"([\w\u4e00-\u9fff（）()\- ]+\.pdf)", old_meta, re.I)
        if m:
            pdf_name = m.group(1).strip()
    meta = ("%s · 共 %d 章" % (pdf_name, n_ch)) if pdf_name else ("共 %d 章" % n_ch)

    stats = ['<div class="stat"><b>%d</b><span>章已整理 / 共 %d 章</span></div>' % (n_ch, n_ch),
             '<div class="stat"><b>%d</b><span>知识点小节</span></div>' % n_card,
             '<div class="stat"><b>%d</b><span>%s</span></div>'
             % (n_code, "代码片段" if args.profile == "tech" else "关键论断"),
             '<div class="stat"><b>%d</b><span>自测题</span></div>' % n_quiz]
    if n_fig:
        stats.append('<div class="stat"><b>%d</b><span>图解</span></div>' % n_fig)

    chips = "".join('<span class="chip">%s</span>' % c for c in CHIPS[args.profile])
    slug = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "-", title).strip("-").lower() or "book"

    out = (tpl
           .replace("__TITLE__", title)
           .replace("__SUBTITLE__", subtitle)
           .replace("__META__", meta)
           .replace("__STATS__", "".join(stats))
           .replace("__NAV__", nav_inner)
           .replace("__CONTENT__", content_inner)
           .replace("__TOTAL_CARDS__", str(n_card))
           .replace("__HERO_TAG__", HERO_TAG)
           .replace("__HERO_CHIPS__", chips)
           .replace("__FOOTER__", FOOTER)
           .replace("__SLUG__", slug))
    left = [p for p in ("__TITLE__", "__NAV__", "__CONTENT__", "__STATS__", "__SLUG__") if p in out]
    if left:
        sys.exit("占位符未替换干净: %s" % left)

    # ---- 5) 旧站自定义 CSS 兜底 ----
    extra = []
    if args.extra_css == "auto":
        old_styles = re.findall(r"<style[^>]*>(.*?)</style>", src, re.S)
        new_css = strip_comments(re.findall(r"<style[^>]*>(.*?)</style>", tpl, re.S)[0])
        for st in old_styles:
            extra += orphan_css(strip_comments(st), new_css)
        if extra:
            block = ("\n/* ---- 本书自定义样式（重套模板时自动保留） ---- */\n"
                     + "\n".join(extra) + "\n")
            out = out.replace("</style>", block + "</style>", 1) if "</style>" in out else out + block

    print("书: %s" % os.path.basename(book))
    print("  标题=%s | 副标题=%s | meta=%s" % (title, subtitle or "(空)", meta))
    print("  章=%d  卡片=%d  代码=%d  自测=%d  图解=%d" % (n_ch, n_card, n_code, n_quiz, n_fig))
    print("  保留自定义 CSS 规则: %d 条" % len(extra))
    print("  体积: %d -> %d 字节" % (len(src.encode("utf-8")), len(out.encode("utf-8"))))

    if args.dry_run:
        print("  [dry-run] 未落盘")
        return

    out_path = args.out or html
    if not args.no_backup and out_path == html:
        bak_dir = os.path.join(book, "_extract") if os.path.isdir(os.path.join(book, "_extract")) else book
        bak = os.path.join(bak_dir, "index.bak-before-retemplate.html")
        if os.path.isfile(bak):
            bak = bak.replace(".html", "-%s.html" % os.path.basename(book))
        io.open(bak, "w", encoding="utf-8").write(src)
        print("  备份: %s" % bak)
    io.open(out_path, "w", encoding="utf-8").write(out)
    print("  已写入: %s" % out_path)


if __name__ == "__main__":
    main()
