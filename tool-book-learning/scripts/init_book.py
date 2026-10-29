#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""init_book.py - 为一本 PDF 书初始化提取工作区（默认按书名建文件夹）。

用法:
    # 最省事：只给 PDF，自动在 PDF 所在目录下建 "<书名>/" 工作区
    python init_book.py --pdf book.pdf [--title "..."] [--subtitle "..."]

    # 指定书籍库根目录（推荐：一本一文件夹，统一收纳）
    python init_book.py --pdf book.pdf --root D:/books

    # 完全自定义工作目录（覆盖自动推导）
    python init_book.py --pdf book.pdf --work D:/somewhere/xxx

生成:
    <book_dir>/_extract/notes/       章节笔记目录（chNN.md）
    <book_dir>/_extract/pages/       渲染页 PNG 目录
    <book_dir>/_extract/pages_text/  文字层快路的按章文本（如有文字层）
    <book_dir>/_extract/map.json     章节映射表

stdout 额外打印可直接喂给后续脚本的机器可读变量:
    BOOK_DIR=...  ROOT_DIR=...  MAP_JSON=...  NOTES_DIR=...

map.json 规则:
- PDF 自带书签目录时自动填 chapters（只取最浅层级，剔除页码型条目）。
- 扫描件无书签 / 书签层级不可靠时输出空骨架，由 agent 渲染目录页人工读取后填写。
- page_offset 需人工校准：书页 N = PDF 0-based 索引 N + page_offset。
"""
import argparse
import json
import os
import re
import sys

# Windows 文件名非法字符 + 控制字符
_ILLEGAL = '<>:"/\\|?*'


def safe_dir_name(name):
    """把书名转成安全的文件夹名：去非法字符、压空白、去尾点/空格、避保留设备名。"""
    s = (name or "").replace("\u3000", " ").replace("\xa0", " ")
    for ch in _ILLEGAL:
        s = s.replace(ch, " ")
    s = re.sub(r"\s+", " ", s).strip()
    s = s.rstrip(". ")
    if re.match(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\..*)?$", s, re.I):
        s = "_" + s
    if len(s) > 80:
        s = s[:80].rstrip(". ")
    return s or "book"


def is_page_like(title):
    """判断书签标题是否是"页码型"条目——扫描件 OCR 书签的典型垃圾。"""
    t = re.sub(r"\s+", "", title or "")
    if not t:
        return True
    if re.match(r"^[0-9]{1,4}$", t):          # 12 / 037 / 1-234
        return True
    if re.match(r"^[0-9]{1,4}[-–—.]{1,2}[0-9]{1,4}$", t):  # 1-234
        return True
    if re.match(r"^第?[0-9]{1,4}页?$", t):
        return True
    return False


def resolve_dirs(args, pdf, title):
    """推导 root / book_dir。优先级：--work > --root+书名 > PDF 所在目录+书名。"""
    if args.work:
        book_dir = os.path.abspath(args.work)
        root = os.path.dirname(book_dir)
    else:
        root = os.path.abspath(args.root) if args.root else os.path.dirname(pdf)
        book_dir = os.path.join(root, safe_dir_name(title))
    return root, book_dir


def main():
    ap = argparse.ArgumentParser(description="初始化 PDF 书籍提取工作区（按书名建文件夹）")
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--work", default="", help="自定义工作目录（默认按书名自动建文件夹）")
    ap.add_argument("--root", default="", help="书籍库根目录，默认取 PDF 所在目录")
    ap.add_argument("--title", default="", help="书名（默认取 PDF 文件名）")
    ap.add_argument("--subtitle", default="")
    ap.add_argument("--max-chapters", type=int, default=60,
                    help="章数上限，超过则截断并在 map.json 标注警告（默认 60）")
    args = ap.parse_args()

    try:
        import fitz
    except ImportError:
        sys.exit("需要 PyMuPDF：pip install PyMuPDF")

    pdf = os.path.abspath(args.pdf)
    if not os.path.isfile(pdf):
        sys.exit("PDF 不存在: %s" % pdf)

    title = args.title or os.path.splitext(os.path.basename(pdf))[0]
    root, work = resolve_dirs(args, pdf, title)

    extract = os.path.join(work, "_extract")
    for d in ("notes", "pages", "pages_text"):
        os.makedirs(os.path.join(extract, d), exist_ok=True)

    doc = fitz.open(pdf)
    n = doc.page_count
    toc = doc.get_toc()

    chapters = []
    tops = []
    if toc:
        # 只取 TOC 里最浅的那一层当"章"：扫描件常见 lv0=部分、lv1=小节，
        # 若把 lv<=1 全收会炸出几百个碎片条目。
        top_lv = min(x[0] for x in toc)
        tops = [x for x in toc if x[0] == top_lv]
        src = "自动提取自 PDF 书签（最浅层级 lv=%d，共 %d 条），请核对 page_offset 与 book_pages" % (
            top_lv, len(tops))
        # 防呆：扫描件书签常是 OCR 出来的页级条目（标题纯页码、每条一页），当章会炸出几百个碎片
        page_like = [x for x in tops if is_page_like(x[1])]
        if page_like:
            tops = [x for x in tops if not is_page_like(x[1])]
            src += "；已剔除 %d 条页码型书签（疑似扫描件页级条目）" % len(page_like)
    else:
        src = "扫描件无书签：请渲染目录页（约前 10-25 页）人工读取章节表后填写 chapters"

    for idx, (lv, t, pg) in enumerate(tops, 1):
        m = re.search(r"第\s*([0-9一二三四五六七八九十百]+)\s*章", t)
        num = ("第%s章" % m.group(1)) if m else ("第%d章" % idx)
        start0 = max(0, pg - 1)  # 书签页码 1-based -> 0-based
        chapters.append({
            "id": "ch%02d" % idx,
            "num": num,
            "title": re.sub(r"^\s*第[^章\s]*章\s*", "", t).strip() or t.strip(),
            "book_pages": "",
            "pdf_start": start0,
            "pdf_end": "",
        })

    # 用下一章起点补 pdf_end
    for i, c in enumerate(chapters):
        if c["pdf_end"] == "" and i + 1 < len(chapters):
            c["pdf_end"] = chapters[i + 1]["pdf_start"] - 1
    if chapters and chapters[-1]["pdf_end"] == "":
        chapters[-1]["pdf_end"] = n - 1

    # 章数上限：超了说明书签层级不可靠，提示人工重填，而不是默默生成几百章
    if len(chapters) > args.max_chapters:
        dropped = len(chapters) - args.max_chapters
        chapters = chapters[: args.max_chapters]
        chapters[-1]["pdf_end"] = n - 1
        src += "；警告：共切出 %d 章，其中 %d 条超过 --max-chapters=%d 被截断；" \
               "书签层级多半不对，请渲染目录页人工重填 chapters" % (
                   len(chapters) + dropped, dropped, args.max_chapters)

    book = {
        "title": title,
        "subtitle": args.subtitle,
        "meta": {
            "source_pdf": os.path.basename(pdf),
            "source_pdf_path": pdf,
            "book_dir": work,
            "root_dir": root,
            "pages": n,
            "page_offset": "",
            "note": src,
        },
        "chapters": chapters,
    }
    map_path = os.path.join(extract, "map.json")
    with open(map_path, "w", encoding="utf-8") as f:
        json.dump(book, f, ensure_ascii=False, indent=2)

    print("OK 书名: %s" % title)
    print("   PDF %d 页 · 书签 %d 条 · 切出 %d 章" % (n, len(toc), len(chapters)))
    if not chapters:
        print("   ! 无可用章节，需人工校准 map.json（见下方 BOOK_DIR）")
    print("   map.json: %s" % map_path)
    print("")
    print("BOOK_DIR=%s" % work)
    print("ROOT_DIR=%s" % root)
    print("MAP_JSON=%s" % map_path)
    print("NOTES_DIR=%s" % os.path.join(extract, "notes"))
    doc.close()


if __name__ == "__main__":
    main()