#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pdf_probe.py - 探测 PDF 书籍：页数 / 文字层 / 书签目录 / 扫描页占比。

用法:
    python pdf_probe.py book.pdf [--sample 20]

输出 JSON 概要，决定走哪条提取路线：
- text_layer=True  -> 文字层快路（PyMuPDF 直接抽文本）
- text_layer=False -> 扫描件视觉路（render_pages.py + 多模态读图）
"""
import argparse
import json
import os
import sys


def main():
    ap = argparse.ArgumentParser(description="Probe a PDF book")
    ap.add_argument("pdf", help="PDF 文件路径")
    ap.add_argument("--sample", type=int, default=20, help="抽样探测的页数（默认 20）")
    args = ap.parse_args()

    try:
        import fitz
    except ImportError:
        sys.exit("需要 PyMuPDF：pip install PyMuPDF")

    if not os.path.isfile(args.pdf):
        sys.exit(f"PDF 不存在: {args.pdf}")

    doc = fitz.open(args.pdf)
    n = doc.page_count
    step = max(1, n // max(1, args.sample))

    text_pages = 0
    image_pages = 0
    total_chars = 0
    for i in range(0, n, step):
        p = doc[i]
        t = p.get_text().strip()
        total_chars += len(t)
        if len(t) > 20:
            text_pages += 1
        if p.get_images():
            image_pages += 1
    sampled = len(range(0, n, step))

    toc = doc.get_toc()
    toc_preview = [{"level": lv, "title": t, "page": pg} for lv, t, pg in toc[:20]]

    result = {
        "file": os.path.basename(args.pdf),
        "pages": n,
        "sampled_pages": sampled,
        "text_pages_in_sample": text_pages,
        "image_pages_in_sample": image_pages,
        "avg_chars_per_sampled_page": round(total_chars / max(1, sampled), 1),
        "text_layer": text_pages >= max(1, sampled // 2),
        "toc_entries": len(toc),
        "toc_preview": toc_preview,
        "route": None,
    }
    result["route"] = "text-extract" if result["text_layer"] else "vision-extract"
    print(json.dumps(result, ensure_ascii=False, indent=2))
    doc.close()


if __name__ == "__main__":
    main()
