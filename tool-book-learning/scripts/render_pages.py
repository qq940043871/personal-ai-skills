#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_pages.py - 把 PDF 指定页渲染成带页码标签的 PNG（供视觉读取）。

用法:
    python render_pages.py --pdf book.pdf --start 24 --end 48 --out out_dir [--dpi 100]

说明:
- 页码为 0-based PDF 页索引（PyMuPDF 的 doc[i]）。
- 每张 PNG 左上角烧入 "PDFIDX=N" 红色标签：多图并行读取时返回顺序可能被打乱，
  靠标签可100%确认每张图对应哪一页。
- 书页号 = PDFIDX + page_offset（page_offset 见 map.json，符号约定：书页 = PDF 索引 + offset）。
  例：正文第一页在 PDFIDX=21 且印着"书页 1"，则 page_offset = -20。
"""
import argparse
import os
import sys


def main():
    ap = argparse.ArgumentParser(description="Render PDF pages to stamped PNGs")
    ap.add_argument("--pdf", required=True, help="PDF 文件路径")
    ap.add_argument("--start", type=int, required=True, help="起始 PDF 页索引（0-based，含）")
    ap.add_argument("--end", type=int, required=True, help="结束 PDF 页索引（0-based，含）")
    ap.add_argument("--out", required=True, help="输出目录")
    ap.add_argument("--dpi", type=int, default=100, help="渲染 DPI（默认 100，扫描件建议 95-110）")
    args = ap.parse_args()

    try:
        import fitz  # PyMuPDF
    except ImportError:
        sys.exit("需要 PyMuPDF：pip install PyMuPDF")
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        sys.exit("需要 Pillow：pip install Pillow")

    if not os.path.isfile(args.pdf):
        sys.exit(f"PDF 不存在: {args.pdf}")

    os.makedirs(args.out, exist_ok=True)
    doc = fitz.open(args.pdf)
    last = min(args.end, doc.page_count - 1)
    if args.start < 0 or args.start > last:
        sys.exit(f"页范围非法: {args.start}..{args.end}（共 {doc.page_count} 页）")

    for i in range(args.start, last + 1):
        pix = doc[i].get_pixmap(dpi=args.dpi)
        fp = os.path.join(args.out, f"p{i:04d}.png")
        pix.save(fp)
        im = Image.open(fp).convert("RGB")
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, 150, 30], fill=(255, 0, 0))
        d.text((10, 9), f"PDFIDX={i}", fill=(255, 255, 255))
        im.save(fp)
    doc.close()
    print(f"OK rendered PDFIDX {args.start}..{last} -> {args.out}")


if __name__ == "__main__":
    main()
