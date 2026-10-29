#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_map.py - 给"书签不可信"的书造出可用的 map.json。

适用三类书（init_book.py 切出来的章表不能用）：
  A. 无书签：切出 0 章（网页打印稿、小册子）
  B. 书签层级混乱：L1 里混装篇/章/节，切出来碎成几百章，或某"章"独占 181 页
  C. 合集型书：本质是多篇长文/多册合订，章标题是「第N篇」「第N部分」「一、二、三」
     —— 这类书的 get_toc() 完全不可信，靠正则匹配「第N章」也匹配不出来

用法:
    # 1) 先看完整书签树，自己判断该不该按 L2/L3 重切
    python make_map.py --pdf book.pdf --dump-toc > toc.txt

    # 2) 按目录页列出的篇标题，在正文里定位"首次出现页"自动切章（合集型书首选）
    python make_map.py --pdf book.pdf --titles-file titles.txt --book D:/books/xxx \
        [--body-start 3] [--offset -1]

    # 3) 手工指定每章 PDF 页范围（终极兜底，什么都能干）
    python make_map.py --pdf book.pdf --book D:/books/xxx \
        --range "1:1-40" --range "2:41-96" --range "3:97-140"

    # 4) 切完渲染各章首页，人工核对边界与 page_offset
    python make_map.py --pdf book.pdf --book D:/books/xxx --render-homes

titles.txt 每行一个章标题（按顺序），空行与 # 开头的行忽略。
切完**必须**跑 --render-homes 核对：目录说"第2章在书页46"不等于 pdf=46+offset 就是章首页，
每个"部分"之间常插一张无页码扉页。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

_ILLEGAL = '<>:"/\\|?*'


def safe_dir_name(name):
    s = (name or "").replace("\u3000", " ").replace("\xa0", " ")
    for ch in _ILLEGAL:
        s = s.replace(ch, " ")
    s = re.sub(r"\s+", " ", s).strip().rstrip(". ")
    if re.match(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\..*)?$", s, re.I):
        s = "_" + s
    return (s[:80].rstrip(". ") if len(s) > 80 else s) or "book"


def norm(s):
    """归一化用于正文匹配：去所有空白、全角转半角、常见异体统一。

    合集型书切章靠字符串匹配正文，PDF 抽取的文本里标题常被拆成多行或夹着空格，
    不归一化就匹配不到。
    """
    s = (s or "").strip()
    out = []
    for ch in s:
        code = ord(ch)
        if code == 0x3000:
            code = 32
        elif 0xFF01 <= code <= 0xFF5E:# 全角 -> 半角
            code -= 0xFEE0
        out.append(chr(code))
    t = "".join(out).lower()
    return re.sub(r"\s+", "", t)


def load_page_texts(doc, body_start=0):
    """逐页抽文本并归一化，返回 [(idx, norm_text)]。"""
    pages = []
    for i in range(body_start, doc.page_count):
        pages.append((i, norm(doc[i].get_text())))
    return pages


def find_first(pages, title, from_idx=0):
    """在正文里定位标题首次出现的页。返回 (pdf_idx, 整行原文, 命中次数)。"""
    key = norm(title)
    if not key:
        return None, "", 0
    best = None
    hits = 0
    for idx, txt in pages:
        if idx < from_idx:
            continue
        pos = txt.find(key)
        if pos >= 0:
            hits += 1
            if best is None:
                # 取命中所在的原始行，便于人工确认是不是标题
                best = (idx, pos)
    return best, key, hits


def chapter_from_title(title, idx):
    m = re.match(r"^\s*第\s*([0-9一二三四五六七八九十百零]+\s*[章篇部][分]?)", title)
    if m:
        return "第%s" % re.sub(r"\s+", "", m.group(1))
    m2 = re.match(r"^\s*([0-9]{1,3})[\s\.、]", title)
    if m2:
        return "第%s章" % m2.group(1)
    return title.strip()


def main():
    ap = argparse.ArgumentParser(description="给书签不可信的书造 map.json")
    ap.add_argument("--pdf", default="", help="PDF 路径（dump-toc / titles / render-homes 需要）")
    ap.add_argument("--book", default="", help="书籍文件夹（写入 <book>/_extract/map.json）")
    ap.add_argument("--dump-toc", action="store_true", help="打印完整书签树后退出")
    ap.add_argument("--titles-file", default="", help="每行一个章标题的文件")
    ap.add_argument("--body-start", type=int, default=0, help="正文起始 PDF 索引（跳过封面/版权/目录）")
    ap.add_argument("--offset", type=int, default=None, help="page_offset：书页 = PDF索引 + offset")
    ap.add_argument("--range", action="append", default=[],
                    help="手工范围 id:start-end，0-based，可重复")
    ap.add_argument("--render-homes", action="store_true", help="渲染各章首页供人工核对")
    ap.add_argument("--subtitle", default="", help="副标题")
    ap.add_argument("--dpi", type=int, default=100)
    args = ap.parse_args()

    try:
        import fitz
    except ImportError:
        sys.exit("需要 PyMuPDF：pip install PyMuPDF")

    # ---------- dump-toc ----------
    if args.dump_toc:
        if not args.pdf:
            sys.exit("--dump-toc 需要 --pdf")
        doc = fitz.open(args.pdf)
        toc = doc.get_toc()
        if not toc:
            print("(该 PDF 无书签)")
        for lv, title, page in toc:
            print("lv%d\t%s\t%d" % (lv, title, page))
        print("\n共 %d 条书签· %d 页" % (len(toc), doc.page_count))
        doc.close()
        return

    if not args.book:
        sys.exit("需要 --book（写入 map.json 的书籍文件夹）")
    book_dir = os.path.abspath(args.book)
    extract = os.path.join(book_dir, "_extract")
    os.makedirs(extract, exist_ok=True)

    existing = os.path.join(extract, "map.json")
    book = {"title": os.path.basename(book_dir), "subtitle": args.subtitle,
            "meta": {"book_dir": book_dir, "note": ""}, "chapters": []}
    if os.path.isfile(existing):
        try:
            with open(existing, "r", encoding="utf-8") as f:
                book = json.load(f)
        except Exception as e:
            print("! 现有 map.json 读不出来（%s），将新建" % e)
            book = {"title": os.path.basename(book_dir), "subtitle": args.subtitle,
                    "meta": {"book_dir": book_dir}, "chapters": []}

    # ---------- render-homes ----------
    if args.render_homes:
        if not args.pdf:
            sys.exit("--render-homes 需要 --pdf")
        doc = fitz.open(args.pdf)
        outdir = os.path.join(extract, "pages_homes")
        os.makedirs(outdir, exist_ok=True)
        try:
            from PIL import Image, ImageDraw
        except ImportError:
            sys.exit("需要 Pillow")
        for c in book.get("chapters", []):
            s = c.get("pdf_start")
            if s in (None, ""):
                continue
            i = int(s)
            fp = os.path.join(outdir, "%s_p%04d.png" % (c["id"], i))
            doc[i].get_pixmap(dpi=args.dpi).save(fp)
            im = Image.open(fp).convert("RGB")
            d = ImageDraw.Draw(im)
            d.rectangle([0, 0, 260, 30], fill=(255, 0, 0))
            d.text((8, 9), "%s  PDFIDX=%d" % (c["id"], i), fill=(255, 255, 255))
            im.save(fp)
            print("  %s 首页 PDFIDX=%d -> %s" % (c["id"], i, os.path.basename(fp)))
        print("\n逐张 Read 这些图，确认首行确实是本章标题；不对就手工改 map.json 的 pdf_start。")
        print("重点核对：各『部分』之间的扉页会让 offset 不均匀，出现错位就要逐章修正。")
        doc.close()
        return

    # ---------- 手工范围 ----------
    if args.range:
        for spec in args.range:
            cid, _, rng = spec.partition(":")
            a, _, b = rng.partition("-")
            book.setdefault("chapters", []).append({
                "id": cid.strip(), "num": "", "title": cid.strip(),
                "book_pages": "", "pdf_start": int(a), "pdf_end": int(b)})
        book["meta"]["note"] = "由 make_map.py --range 手工指定"

    # ---------- 按标题自动定位 ----------
    elif args.titles_file:
        if not args.pdf:
            sys.exit("--titles-file 需要 --pdf")
        titles = []
        with open(args.titles_file, "r", encoding="utf-8") as f:
            for ln in f:
                t = ln.strip()
                if t and not t.startswith("#"):
                    titles.append(t)
        if not titles:
            sys.exit("titles 文件里没有有效标题")

        doc = fitz.open(args.pdf)
        pages = load_page_texts(doc, args.body_start)
        print("扫了 %d 页，开始定位 %d 个标题……" % (len(pages), len(titles)))
        chapters = []
        cursor = args.body_start
        ambiguous = []
        for i, t in enumerate(titles, 1):
            (hit, key, hits), = (find_first(pages, t, cursor),)
            if hit is None:
                print("  [MISS] %s  —— 标题未在正文找到，跳过" % t)
                continue
            idx = hit[0]
            chapters.append({
                "id": "ch%02d" % i,
                "num": chapter_from_title(t, idx),
                "title": re.sub(r"^\s*第\s*[0-9一二三四五六七八九十百零]+\s*[章篇部][分]?\s*", "", t).strip() or t,
                "book_pages": "", "pdf_start": idx, "pdf_end": "",
                "_source_title": t, "_hits": hits})
            flag = "  <- 全文出现 %d 次，取首次" % hits if hits > 1 else ""
            print("  ch%02d  PDFIDX=%-5d %s%s" % (i, idx, t, flag))
            if hits > 1:
                ambiguous.append((i, t, hits))
            cursor = idx + 1
        for i, c in enumerate(chapters):
            if c["pdf_end"] == "" and i + 1 < len(chapters):
                c["pdf_end"] = chapters[i + 1]["pdf_start"] - 1
        if chapters:
            chapters[-1]["pdf_end"] = doc.page_count - 1
            book["chapters"] = chapters
        book["meta"]["note"] = ("由 make_map.py --titles-file 按标题在正文中首次出现页定位；"
                                "**必须用 --render-homes 逐章核对首页**")
        if ambiguous:
            book["meta"]["note"] += "；%d 个标题全文多处出现，已取首次" % len(ambiguous)
        doc.close()

    else:
        ap.print_help()
        sys.exit("没指定任何操作：用 --dump-toc / --titles-file / --range / --render-homes")

    with open(existing, "w", encoding="utf-8") as f:
        json.dump(book, f, ensure_ascii=False, indent=2)
    print("\nOK -> %s（%d 章）" % (existing, len(book.get("chapters", []))))
    print("下一步：python make_map.py --pdf <pdf> --book %s --render-homes" % book_dir)


if __name__ == "__main__":
    main()