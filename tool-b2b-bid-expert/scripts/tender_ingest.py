#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tender_ingest.py — 招标文件摄入：PDF / DOCX / TXT → 分页文本 + 页码索引 + 关键条款候选定位。

为什么需要它：招标文件基本都是 PDF（很多还是扫描件），而标书应答、废标自检的全部价值
都建立在"能指着原文说第几页第几条"上。拿不到页码，输出就只能泛泛而谈。

用法:
    python tender_ingest.py 招标文件.pdf --out ./_tender
    python tender_ingest.py 招标文件.pdf --out ./_tender --no-ocr          # 只用文字层
    python tender_ingest.py 招标文件.pdf --out ./_tender --max-pages 40     # 先试跑前 40 页
    python tender_ingest.py 招标文件.docx --out ./_tender
    python tender_ingest.py 招标公告.txt --out ./_tender

输出（全部落在 --out 目录）:
    tender.md        带 [[P12]] 页码锚点的全文，供模型引用
    pages.json       逐页结构化：页码 / 字数 / 是否 OCR / 是否需视觉补看 / 文本
    hits.json        关键条款候选定位（评分办法/废标/★条款/最高限价/保证金/截止/资格/偏离表）
    hits_index.md    人读版条款索引，按类别分组，每条带页码
    manifest.json    文件信息、提取路线、统计

设计取舍:
- 页码一律用 **1-based 物理页序**（PDF 第 1 页 = P1），不猜"印刷页码"。
  招标文件正文常有扉页/目录偏移，猜错了引用就全错；宁可给物理页，让用户自己核对一次。
- DOCX 没有可靠分页，改用「段落块」编号（page_mode=paragraph），并在输出里明确声明。
- OCR 是兜底：只在某页文字层近乎为空时启用，避免整本 OCR 的时间成本。
"""
import argparse
import json
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

# ---------------------------------------------------------------- 条款定位规则
# 每条规则：(类别, 风险等级, [正则...])
# 正则只做"候选定位"，不做判定——最终是否构成废标必须人工读原文确认。
#
# 顺序即优先级：一行只归入第一个命中的类别。
# ★ / ▲ 排最前，因为符号本身就是最可靠的实质性条款标记——
# 早先把它们排在"废标条款"之后，结果 ★4.2 那一行因为含"无效投标"被吞进废标类，
# 星号条款统计为 0，反而把最该盯的条款漏掉了。
HIT_RULES = [
    ("星号条款", "致命", [r"[★☆]"]),
    ("三角条款", "高", [r"[▲△]"]),
    ("废标条款", "致命", [r"废标", r"无效投标", r"投标无效", r"无效标", r"否决[^\n]{0,4}投标",
                       r"实质性响应", r"实质性要求", r"不予受理", r"按无效处理"]),
    ("评标办法", "高", [r"评标办法", r"评分办法", r"评审办法", r"综合评分法", r"最低评标价法",
                     r"经评审的?最低", r"评分细则"]),
    ("最高限价", "致命", [r"最高限价", r"招标控制价", r"预算金额", r"采购预算", r"拦标价"]),
    ("保证金", "高", [r"投标保证金", r"履约保证金", r"保证金金额", r"退还保证金"]),
    ("截止时间", "致命", [r"投标截止", r"递交[^\n]{0,6}截止", r"开标时间", r"提交[^\n]{0,6}截止",
                       r"报名截止", r"答疑[^\n]{0,6}截止"]),
    ("资格要求", "致命", [r"投标人资格", r"供应商资格", r"资格要求", r"资质要求", r"合格投标人",
                       r"特定资格"]),
    ("偏离表", "高", [r"偏离表", r"技术偏离", r"商务偏离", r"响应表", r"点对点"]),
    ("评分项", "中", [r"评分标准", r"评分表", r"分值", r"加分项", r"业绩要求"]),
    ("交付与验收", "中", [r"交货期", r"工期", r"验收标准", r"质保期", r"付款方式", r"结算方式"]),
]

OCR_MIN_CHARS = 20          # 文字层低于这个字数才认为"这页没文字层"
SNIPPET_MAX = 120           # 单条候选摘录长度上限
MAX_HITS_PER_KIND_PER_PAGE = 3
MAX_KINDS_PER_LINE = 2      # 一行最多归两类（如"最高限价…投标无效"同时是价格与废标信息）


# ---------------------------------------------------------------- 工具函数
def norm(s):
    return re.sub(r"\s", "", s or "")


def snippet(line):
    line = re.sub(r"[ \t\u3000]+", " ", line).strip()
    line = re.sub(r"\.{4,}|…{2,}|·{4,}", " … ", line)   # 折叠目录里的点线
    return line[:SNIPPET_MAX]


def split_lines(text):
    return [ln for ln in (text or "").splitlines() if ln.strip()]


# ---------------------------------------------------------------- OCR 兜底
def make_ocr():
    """返回 (name, fn)；不可用时返回 (None, None)，由调用方降级为"需视觉补看"。"""
    try:
        from rapidocr_onnxruntime import RapidOCR
        eng = RapidOCR()

        def run(page, dpi):
            import numpy as np
            pix = page.get_pixmap(dpi=dpi)
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            if pix.n == 4:
                img = img[:, :, :3]
            res, _ = eng(img)
            lines = []
            for r in res or []:
                box, txt = r[0], r[1]
                ys = [p[1] for p in box]
                xs = [p[0] for p in box]
                lines.append((round(min(ys) / 10), min(xs), txt))
            lines.sort(key=lambda x: (x[0], x[1]))
            return "\n".join(t for _, _, t in lines)
        return "rapidocr", run
    except Exception:
        pass
    try:
        import easyocr
        reader = easyocr.Reader(["ch_sim", "en"], gpu=False, verbose=False)

        def run(page, dpi):
            import numpy as np
            pix = page.get_pixmap(dpi=dpi)
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            if pix.n == 4:
                img = img[:, :, :3]
            res = reader.readtext(img, detail=1)
            res = sorted(res, key=lambda r: (min(p[1] for p in r[0]) // 10, min(p[0] for p in r[0])))
            return "\n".join(r[1] for r in res or [])
        return "easyocr", run
    except Exception:
        return None, None


# ---------------------------------------------------------------- PDF
def ingest_pdf(path, out, use_ocr, dpi, max_pages):
    try:
        import fitz
    except ImportError:
        sys.exit("需要 PyMuPDF：pip install PyMuPDF（或用 anaconda 解释器）")

    doc = fitz.open(path)
    total = doc.page_count
    limit = min(total, max_pages) if max_pages else total
    ocr_name, ocr_fn = (make_ocr() if use_ocr else (None, None))
    vision_dir = os.path.join(out, "vision")
    pages, ocr_pages, vision_pages = [], [], []
    layout_pages = []          # 含疑似表格/评分表的页，供视觉复核

    for i in range(limit):
        page = doc[i]
        text = page.get_text("text").strip()
        used_ocr = False
        if len(norm(text)) < OCR_MIN_CHARS and ocr_fn:
            try:
                got = ocr_fn(page, dpi)
                if got and len(norm(got)) > len(norm(text)):
                    text, used_ocr = got, True
                    ocr_pages.append(i + 1)
            except Exception as e:
                print("  ! P%d OCR 失败：%s" % (i + 1, e))

        chars = len(norm(text))
        need_vision = chars < OCR_MIN_CHARS
        if need_vision:
            vision_pages.append(i + 1)
            os.makedirs(vision_dir, exist_ok=True)
            try:
                page.get_pixmap(dpi=150).save(os.path.join(vision_dir, "P%04d.png" % (i + 1)))
            except Exception:
                pass

        # 评分表/报价表这类版面，文字层能抽到字但结构会丢，单列一份清单提醒复核
        if re.search(r"(评分|分值|报价|清单|偏离)[^\n]{0,8}(表|明细)", text):
            layout_pages.append(i + 1)

        pages.append({
            "page": i + 1,
            "chars": chars,
            "ocr": used_ocr,
            "need_vision": need_vision,
            "text": text,
        })
        flag = "OCR" if used_ocr else ("视觉" if need_vision else "")
        print("  P%-4d %6d字 %s" % (i + 1, chars, flag))

    doc.close()
    meta = {
        "file": os.path.basename(path),
        "format": "pdf",
        "page_mode": "physical",
        "page_mode_note": "页码为 PDF 物理页序（1-based），非文件内印刷页码",
        "total_pages": total,
        "parsed_pages": limit,
        "truncated": bool(max_pages and total > max_pages),
        "ocr_backend": ocr_name,
        "ocr_pages": ocr_pages,
        "vision_pages": vision_pages,
        "layout_review_pages": layout_pages,
    }
    return pages, meta


# ---------------------------------------------------------------- DOCX
def ingest_docx(path, max_pages):
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml")
    root = ET.fromstring(xml)

    paras = []
    for p in root.iter("{%s}p" % W_NS):
        txt = "".join(t.text or "" for t in p.iter("{%s}t" % W_NS)).strip()
        brk = any((br.get("{%s}type" % W_NS) or "") == "page"
                  for br in p.iter("{%s}br" % W_NS))
        if txt or brk:
            paras.append((txt, brk))

    # 优先用显式分页符；没有就按段数切块（DOCX 不存渲染页码）
    has_break = any(b for _, b in paras)
    if has_break:
        page_mode, note = "section", "按 DOCX 显式分页符切分，页码近似"
        blocks, cur = [], []
        for txt, brk in paras:
            if txt:
                cur.append(txt)
            if brk and cur:
                blocks.append(cur)
                cur = []
        if cur:
            blocks.append(cur)
    else:
        page_mode, note = "paragraph", "DOCX 无分页信息，按每 40 段切一块，引用请用章节标题+段落号"
        step = 40
        blocks = [ [t for t, _ in paras[i:i + step] if t] for i in range(0, len(paras), step) ]

    pages = []
    for idx, block in enumerate(blocks[:max_pages] if max_pages else blocks, start=1):
        text = "\n".join(block)
        pages.append({
            "page": idx,
            "chars": len(norm(text)),
            "ocr": False,
            "need_vision": False,
            "text": text,
        })
    meta = {
        "file": os.path.basename(path),
        "format": "docx",
        "page_mode": page_mode,
        "page_mode_note": note,
        "total_pages": len(blocks),
        "parsed_pages": len(pages),
        "truncated": bool(max_pages and len(blocks) > max_pages),
        "ocr_backend": None,
        "ocr_pages": [],
        "vision_pages": [],
        "layout_review_pages": [],
    }
    return pages, meta


# ---------------------------------------------------------------- 纯文本
def ingest_text(path, max_pages, chunk=3000):
    raw = open(path, "r", encoding="utf-8", errors="replace").read()
    blocks = raw.split("\f") if "\f" in raw else [raw[i:i + chunk] for i in range(0, len(raw), chunk)]
    pages = []
    for idx, b in enumerate(blocks[:max_pages] if max_pages else blocks, start=1):
        pages.append({
            "page": idx,
            "chars": len(norm(b)),
            "ocr": False,
            "need_vision": False,
            "text": b.strip(),
        })
    meta = {
        "file": os.path.basename(path),
        "format": "text",
        "page_mode": "chunk",
        "page_mode_note": "纯文本无页码，按 %d 字符或换页符切块" % chunk,
        "total_pages": len(blocks),
        "parsed_pages": len(pages),
        "truncated": bool(max_pages and len(blocks) > max_pages),
        "ocr_backend": None,
        "ocr_pages": [],
        "vision_pages": [],
        "layout_review_pages": [],
    }
    return pages, meta


# ---------------------------------------------------------------- 条款定位
def locate(pages):
    hits = []
    counter = {}
    for pg in pages:
        for line in split_lines(pg["text"]):
            # 一行可以同时命中多个类别：只留一个会把"最高限价…投标无效"这类
            # 双重信息句压缩掉，导致最高限价统计为 0（报价红线直接消失）。
            matched = []
            for kind, level, pats in HIT_RULES:
                if any(re.search(p, line) for p in pats):
                    matched.append((kind, level))
                    if len(matched) >= MAX_KINDS_PER_LINE:
                        break
            for kind, level in matched:
                key = (pg["page"], kind)
                if counter.get(key, 0) >= MAX_HITS_PER_KIND_PER_PAGE:
                    continue
                counter[key] = counter.get(key, 0) + 1
                hits.append({
                    "kind": kind,
                    "risk": level,
                    "page": pg["page"],
                    "text": snippet(line),
                })
    return hits


def write_md(pages, meta, out):
    lines = ["# 招标文件提取：%s" % meta["file"], ""]
    lines.append("> 提取路线：%s｜共 %d 页（已解析 %d 页）" % (
        meta["page_mode_note"], meta["total_pages"], meta["parsed_pages"]))
    if meta["vision_pages"]:
        lines.append("> 无文字层、需人工看图确认的页：P%s" %
                     "、P".join(str(p) for p in meta["vision_pages"]))
    if meta["ocr_pages"]:
        lines.append("> 经 OCR 还原的页：P%s" % "、P".join(str(p) for p in meta["ocr_pages"]))
    if meta["layout_review_pages"]:
        lines.append("> 疑似评分表/报价表（结构可能失真，建议看图核对）：P%s" %
                     "、P".join(str(p) for p in meta["layout_review_pages"]))
    lines.append("")
    for pg in pages:
        lines.append("[[P%d]]" % pg["page"])
        lines.append(pg["text"] or "（本页无文字层）")
        lines.append("")
    open(os.path.join(out, "tender.md"), "w", encoding="utf-8").write("\n".join(lines))


def write_hits_index(hits, meta, out):
    groups = {}
    for h in hits:
        groups.setdefault(h["kind"], []).append(h)
    order = [k for k, _, _ in HIT_RULES if k in groups]
    lines = ["# 条款索引：%s" % meta["file"], "",
             "> 以下是**候选定位**，不是结论。每一条都要回原文逐字确认后再写进应答表或废标清单。", ""]
    for kind in order:
        items = sorted(groups[kind], key=lambda x: x["page"])
        risk = items[0]["risk"]
        lines.append("## %s（风险：%s）｜%d 处" % (kind, risk, len(items)))
        lines.append("")
        for it in items:
            lines.append("- P%d：%s" % (it["page"], it["text"]))
        lines.append("")
    missing = [k for k, _, _ in HIT_RULES if k not in groups]
    if missing:
        lines.append("## 未定位到的类别")
        lines.append("")
        lines.append("以下类别在已解析页里没有命中，**不等于文件中不存在**（可能是扫描页或表格）："
                     " %s" % "、".join(missing))
        lines.append("")
    open(os.path.join(out, "hits_index.md"), "w", encoding="utf-8").write("\n".join(lines))


# ---------------------------------------------------------------- 主流程
def main():
    ap = argparse.ArgumentParser(description="招标文件摄入：PDF/DOCX/TXT → 分页文本 + 页码索引")
    ap.add_argument("file", help="招标文件路径（.pdf / .docx / .txt / .md）")
    ap.add_argument("--out", required=True, help="输出目录")
    ap.add_argument("--no-ocr", action="store_true", help="不做 OCR，只抽文字层")
    ap.add_argument("--dpi", type=int, default=200, help="OCR 渲染 DPI（默认 200）")
    ap.add_argument("--max-pages", type=int, default=0, help="只解析前 N 页（0=全部）")
    args = ap.parse_args()

    if not os.path.isfile(args.file):
        sys.exit("文件不存在: %s" % args.file)
    os.makedirs(args.out, exist_ok=True)

    ext = os.path.splitext(args.file)[1].lower()
    print("== 摄入 %s" % args.file)
    if ext == ".pdf":
        pages, meta = ingest_pdf(args.file, args.out, not args.no_ocr, args.dpi, args.max_pages)
    elif ext == ".docx":
        pages, meta = ingest_docx(args.file, args.max_pages)
    elif ext in (".txt", ".md"):
        pages, meta = ingest_text(args.file, args.max_pages)
    else:
        sys.exit("不支持的文件类型：%s（支持 .pdf / .docx / .txt / .md）" % ext)

    hits = locate(pages)
    meta["hits_total"] = len(hits)
    meta["hits_by_kind"] = {}
    for h in hits:
        meta["hits_by_kind"][h["kind"]] = meta["hits_by_kind"].get(h["kind"], 0) + 1

    json.dump(pages, open(os.path.join(args.out, "pages.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump(hits, open(os.path.join(args.out, "hits.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump(meta, open(os.path.join(args.out, "manifest.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    write_md(pages, meta, args.out)
    write_hits_index(hits, meta, args.out)

    print("\n== 完成")
    print("   页数 %d（解析 %d）｜条款候选 %d 处" % (meta["total_pages"], meta["parsed_pages"], len(hits)))
    for k, v in sorted(meta["hits_by_kind"].items(), key=lambda x: -x[1]):
        print("   %-10s %d" % (k, v))
    if meta["vision_pages"]:
        print("   ! 需人工看图：P%s" % "、P".join(str(p) for p in meta["vision_pages"]))
    print("   -> %s" % os.path.abspath(args.out))


if __name__ == "__main__":
    main()
