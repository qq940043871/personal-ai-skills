#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ocr_extract.py - 扫描件混合路由：先用 OCR 拿文本，只把"图页"留给多模态读图。

用法:
    # 按章跑（读 map.json 的 pdf_start/pdf_end）
    python ocr_extract.py --pdf book.pdf --map <work>/_extract/map.json \
        --out <work>/_extract/pages_ocr [--chapters ch04,ch08]

    # 试跑任意页范围（忽略 map）
    python ocr_extract.py --pdf book.pdf --out ./tryout --start 112 --end 118

参数:
    --backend rapidocr|easyocr|paddleocr|auto   默认 auto（按可用顺序挑）
    --min-chars 300      OCR 字符数低于此值判定为"图页"，需多模态补看
    --dpi 200            OCR 渲染 DPI（文字清晰优先，比给模型看的 150 高）
    --no-render-vision  不额外渲染待补看页的 PNG
    --vision-pages 115,120   强制指定需要视觉补看的 PDF 页索引

输出:
    <out>/chNN.txt          该章 OCR 全文，按页分隔（含 PDFIDX / 书页号 / 是否需补看）
    <out>/chNN/pNNNN.txt    单页文本
    <out>/vision/chNN/pNNNN.png   需多模态补看的页（默认生成）
    <out>/manifest.json     每页字符数与 need_vision 判定汇总
"""
import argparse
import json
import os
import re
import sys

BACKENDS = ["rapidocr", "easyocr", "paddleocr"]
INSTALL_HINT = {
    "rapidocr": "pip install rapidocr-onnxruntime",
    "easyocr": "pip install easyocr",
    "paddleocr": "pip install paddleocr",
}


# --------------------------------------------------------------------------
# OCR 后端：统一返回 [(box, text, score), ...]，box 用于按阅读顺序排序
# --------------------------------------------------------------------------
def build_engine(backend="auto"):
    order = BACKENDS if backend == "auto" else [backend]
    errs = []
    for b in order:
        try:
            if b == "rapidocr":
                from rapidocr_onnxruntime import RapidOCR
                eng = RapidOCR()

                def run(img, eng=eng):
                    res, _ = eng(img)          # res: [[box, text, score], ...]
                    return [(r[0], r[1], float(r[2])) for r in (res or [])]
                return b, run

            if b == "easyocr":
                import easyocr
                reader = easyocr.Reader(["ch_sim", "en"], gpu=False, verbose=False)

                def run(img, reader=reader):
                    res = reader.readtext(img, detail=1)   # [[box, text, score], ...]
                    return [(r[0], r[1], float(r[2])) for r in (res or [])]
                return b, run

            if b == "paddleocr":
                from paddleocr import PaddleOCR
                ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)

                def run(img, ocr=ocr):
                    res = ocr.ocr(img, cls=True)   # [[[box, (text, score)], ...], ...]
                    out = []
                    for line in (res or []):
                        for w in line or []:
                            out.append((w[0], w[1][0], float(w[1][1])))
                    return out
                return b, run
        except Exception as e:  # noqa: BLE001 - 后端不可用时换下一个
            errs.append("%s: %s" % (b, e))
    sys.exit("没有可用的 OCR 后端。安装其一：\n  %s\n尝试记录：\n  %s"
             % ("\n  ".join(INSTALL_HINT[b] for b in order), "\n  ".join(errs)))


def sort_lines(items):
    """按阅读顺序排序：行按 y（容差 10px 归为同一行）聚拢，行内按 x 从左到右。"""
    def key(it):
        box = it[0]
        ys = [p[1] for p in box]
        xs = [p[0] for p in box]
        return (round(min(ys) / 10), min(xs))
    return sorted(items, key=key)


# --------------------------------------------------------------------------
# 页渲染 -> ndarray
# --------------------------------------------------------------------------
def page_image(page, dpi):
    import numpy as np
    pix = page.get_pixmap(dpi=dpi)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    if pix.n == 4:
        img = img[:, :, :3]
    return img


FIG_RE = re.compile(r"图\s*[0-9]{1,2}[-．.][0-9]{1,2}")
TBL_RE = re.compile(r"表\s*[0-9]{1,2}[-．.][0-9]{1,2}")


def need_vision(lines, text, chars, min_chars, force):
    """判定该页是否需要多模态补看。

    三条判据，命中任一即交给视觉：
    1) 字太少 —— 整页就是一张图；
    2) 文字碎片化 —— 行数不少但平均每行很短，典型症状是插图里的散落标签被 OCR 抓出来、
       顺序还被搅乱（实测图页能"抓到"500+ 字，但全是碎片，毫无阅读价值）；
    3) 含"图 N-N"/"表 N-N"标记且文字偏少 —— 图/表的语义 OCR 抓不到。
    """
    if force:
        return True, "手动指定"
    if chars < min_chars:
        return True, "文字过少（%d 字 < %d），疑似整页插图" % (chars, min_chars)
    if len(lines) >= 8 and chars / len(lines) < 10:
        return True, "文字碎片化（平均每行 %.1f 字），疑似插图标签" % (chars / len(lines))
    if (FIG_RE.search(text) or TBL_RE.search(text)) and chars < min_chars * 2:
        return True, "含图/表标记且文字偏少，插图信息 OCR 抓不到"
    return False, ""


# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="扫描件 OCR 混合路由提取")
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--map", default="", help="map.json（按章提取时用）")
    ap.add_argument("--out", required=True)
    ap.add_argument("--chapters", default="", help="只跑这些章，逗号分隔，如 ch04,ch08")
    ap.add_argument("--start", type=int, default=None, help="试跑：起始 PDF 页索引（0-based）")
    ap.add_argument("--end", type=int, default=None, help="试跑：结束 PDF 页索引（0-based，含）")
    ap.add_argument("--backend", default="auto", choices=["auto"] + BACKENDS)
    ap.add_argument("--min-chars", type=int, default=300)
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--no-render-vision", action="store_true")
    ap.add_argument("--vision-pages", default="", help="强制视觉补看的 PDF 页索引，逗号分隔")
    args = ap.parse_args()

    try:
        import fitz
    except ImportError:
        sys.exit("需要 PyMuPDF：pip install PyMuPDF")

    if not os.path.isfile(args.pdf):
        sys.exit("PDF 不存在: %s" % args.pdf)

    os.makedirs(args.out, exist_ok=True)
    backend, run_ocr = build_engine(args.backend)
    print("OCR 后端: %s · dpi=%d · min_chars=%d" % (backend, args.dpi, args.min_chars))

    force_pages = set()
    for x in args.vision_pages.split(","):
        x = x.strip()
        if x:
            force_pages.add(int(x))

    offset = 0
    jobs = []  # [(cid, start, end)]
    if args.start is not None and args.end is not None:
        jobs.append(("pages", args.start, args.end))
    else:
        if not args.map:
            sys.exit("按章提取需要 --map，或直接用 --start/--end 试跑")
        with open(args.map, "r", encoding="utf-8") as f:
            book = json.load(f)
        offset = int(book.get("meta", {}).get("page_offset") or 0)
        want = [c.strip() for c in args.chapters.split(",") if c.strip()]
        for c in book.get("chapters", []):
            if want and c["id"] not in want:
                continue
            s, e = c.get("pdf_start"), c.get("pdf_end")
            if s in (None, "") or e in (None, ""):
                print("跳过 %s（map 里没有完整页范围）" % c["id"])
                continue
            jobs.append((c["id"], int(s), int(e)))

    doc = fitz.open(args.pdf)
    n = doc.page_count
    manifest = {"backend": backend, "pdf": os.path.basename(args.pdf), "chapters": {}}

    for cid, s, e in jobs:
        s, e = max(0, s), min(e, n - 1)
        if s > e:
            continue
        ch_dir = os.path.join(args.out, cid)
        os.makedirs(ch_dir, exist_ok=True)
        vision_dir = os.path.join(args.out, "vision", cid)

        all_text = []
        pages_meta = []
        for i in range(s, e + 1):
            img = page_image(doc[i], args.dpi)
            items = sort_lines(run_ocr(img))              # [(box, text, score)]
            lines = [it[1].strip() for it in items if it[1].strip()]
            text = "\n".join(lines)
            chars = len(re.sub(r"\s", "", text))
            nv, why = need_vision(lines, text, chars, args.min_chars, i in force_pages)
            if nv and not args.no_render_vision:
                os.makedirs(vision_dir, exist_ok=True)
                doc[i].get_pixmap(dpi=150).save(os.path.join(vision_dir, "p%04d.png" % i))
            with open(os.path.join(ch_dir, "p%04d.txt" % i), "w", encoding="utf-8") as f:
                f.write(text)
            book_page = i + offset
            all_text.append(
                "\n----- [PDFIDX=%d / 书页 %s / %s] -----\n%s\n"
                % (i, book_page, "需视觉补看" if nv else "OCR 完成", text)
            )
            pages_meta.append({
                "pdfidx": i, "book_page": book_page, "chars": chars,
                "need_vision": nv, "reason": why,
            })
            print("  p%-4d 书页%-4s %5d字 %s" % (i, book_page, chars, ("需补看 · " + why) if nv else ""))

        with open(os.path.join(args.out, cid + ".txt"), "w", encoding="utf-8") as f:
            f.write("".join(all_text))

        vision_pages = [p["pdfidx"] for p in pages_meta if p["need_vision"]]
        manifest["chapters"][cid] = {
            "range": [s, e],
            "pages": pages_meta,
            "need_vision_pages": vision_pages,
            "text_file": "%s.txt" % cid,
        }
        print("%s 完成：%d 页，%d 页需视觉补看 -> %s"
              % (cid, len(pages_meta), len(vision_pages), os.path.join(args.out, cid + ".txt")))

    with open(os.path.join(args.out, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print("OK -> %s （manifest.json）" % os.path.abspath(args.out))
    doc.close()


if __name__ == "__main__":
    main()
