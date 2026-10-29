#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""extract_text.py - 文字层快路：按章节页范围直接抽取 PDF 文本。

用法:
    python extract_text.py --pdf book.pdf --map map.json --out <pages_text_dir>

适用:
    pdf_probe.py 判定 text_layer=true 的 PDF。每章输出 <out>/chNN.txt。
    扫描件（text_layer=false）没有文字层，此脚本无用，走 render_pages.py 视觉路。
"""
import argparse
import json
import os
import sys


def main():
    ap = argparse.ArgumentParser(description="按章抽取 PDF 文字层文本")
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--map", required=True, help="map.json")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    try:
        import fitz
    except ImportError:
        sys.exit("需要 PyMuPDF：pip install PyMuPDF")

    if not os.path.isfile(args.pdf):
        sys.exit("PDF 不存在: %s" % args.pdf)
    with open(args.map, "r", encoding="utf-8") as f:
        book = json.load(f)

    os.makedirs(args.out, exist_ok=True)
    doc = fitz.open(args.pdf)
    n = doc.page_count

    for c in book.get("chapters", []):
        s, e = c.get("pdf_start"), c.get("pdf_end")
        if s is None or s == "" or e is None or e == "":
            continue
        s, e = max(0, int(s)), min(int(e), n - 1)
        if s > e:
            continue
        parts = []
        for i in range(s, e + 1):
            parts.append("\n----- [PDFIDX=%d / 书页 %s] -----\n" % (i, i + int(book.get("meta", {}).get("page_offset") or 0)))
            parts.append(doc[i].get_text())
        fp = os.path.join(args.out, c["id"] + ".txt")
        with open(fp, "w", encoding="utf-8") as f:
            f.write("".join(parts))
        chars = sum(len(p) for p in parts)
        print("%s  p%d-%d  %d chars" % (c["id"], s, e, chars))
    doc.close()
    print("OK -> %s" % os.path.abspath(args.out))


if __name__ == "__main__":
    main()
