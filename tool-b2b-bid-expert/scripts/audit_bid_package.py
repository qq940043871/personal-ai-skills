#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audit_bid_package.py — 标书交付物质检。

为什么需要它：标书的价值全在"每句话都能对应到招标文件某页某条"。
模型很容易写出漂亮但悬空的应答表（"我方完全满足"），人工很难逐行查。
本脚本把这件事变成可执行的门禁。

用法:
    python audit_bid_package.py 应答表.md
    python audit_bid_package.py 应答表.md --tender ./_tender      # 额外校验★条款页码覆盖
    python audit_bid_package.py ./out --tender ./_tender          # 目录模式，扫全部 .md

检查项:
    E1 占位符残留（＿＿ / TODO / XXX / 待填 / 示例）
    E2 表格行缺少页码引用（表头含 位置/页码/出处/条款 时，每行须有 P12 或「待核对」）
    E3 空表（只有表头没有数据行）
    E4 无附件支撑的资质声称（"我司具备…资质"但同段无 附件/见/详见）
    E5 ★条款页码覆盖不足（需 --tender，未覆盖的★页逐页列出）
    E6 空泛响应（★条款行只写"满足/响应/无偏离"而无实现说明）

退出码：0 全部通过；1 存在【高】及以上问题。
"""
import argparse
import json
import os
import re
import sys

CITE_RE = re.compile(r"[Pp]\s?\d{1,4}|第\s?\d+\s?页|待核对|需核对")
PLACEHOLDER_RE = re.compile(r"[＿_]{3,}|\bTODO\b|\bTBD\b|\bXXX\b|待填|【待补充】|示例内容")
CLAIM_RE = re.compile(
    r"(我司|我方|本公司|投标人)[^。\n]{0,12}"
    r"(具备|拥有|已获|取得|通过)[^。\n]{0,24}"
    r"(资质|证书|认证|业绩|许可|专利|体系)"
)
SUPPORT_RE = re.compile(r"附件|见第|详见|附后|编号[:：]|扫描件|证书编号|据第")
WEAK_CELLS = {"满足", "完全满足", "响应", "完全响应", "无偏离", "符合", "符合要求", "同意"}


def iter_files(target):
    if os.path.isfile(target):
        return [target]
    out = []
    for dp, _, fns in os.walk(target):
        for f in fns:
            if f.lower().endswith(".md"):
                out.append(os.path.join(dp, f))
    return sorted(out)


def split_tables(text):
    """返回 [(header_cells, [row_cells...], start_line)]"""
    tables, cur, start = [], [], 0
    for i, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if s.startswith("|") and s.endswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if not cur:
                start = i
            cur.append(cells)
        else:
            if cur:
                tables.append((cur[0], cur[1:], start))
                cur = []
    if cur:
        tables.append((cur[0], cur[1:], start))
    return tables


def audit_file(path, tender_hits=None):
    text = open(path, "r", encoding="utf-8", errors="replace").read()
    name = os.path.basename(path)
    issues = []

    # E1 占位符
    for m in PLACEHOLDER_RE.finditer(text):
        ln = text[:m.start()].count("\n") + 1
        issues.append({"code": "E1", "level": "高", "line": ln,
                       "msg": "占位符残留：%s" % m.group(0)})

    # E2/E3 表格
    tables = split_tables(text)
    cited_pages = set()
    if not tables:
        issues.append({"code": "E3", "level": "高", "line": 0,
                       "msg": "全文没有任何 Markdown 表格——应答表/偏离表/清单交付物不应缺表"})
    for header, rows, start in tables:
        cite_idx = None
        for i, h in enumerate(header):
            if re.search(r"位置|页码|出处|条款(位置|号)", h):
                cite_idx = i
                break
        data_rows = [r for r in rows if not re.match(r"^[-:\s|]+$", "|".join(r))]
        if not data_rows:
            issues.append({"code": "E3", "level": "高", "line": start,
                           "msg": "空表（只有表头）：%s" % " | ".join(header[:4])})
            continue
        if cite_idx is not None:
            for k, r in enumerate(data_rows, 1):
                val = r[cite_idx] if cite_idx < len(r) else ""
                if not CITE_RE.search(val):
                    issues.append({"code": "E2", "level": "高", "line": start,
                                   "msg": "第 %d 行缺页码引用（列「%s」为空或无效）：%s"
                                          % (k, header[cite_idx], (val or "—")[:24])})
    for m in re.finditer(r"[Pp]\s?(\d{1,4})", text):
        cited_pages.add(int(m.group(1)))

    # E4 无附件支撑的资质声称
    for line in text.splitlines():
        if CLAIM_RE.search(line) and not SUPPORT_RE.search(line):
            ln = text[:text.find(line)].count("\n") + 1
            issues.append({"code": "E4", "level": "致命", "line": ln,
                           "msg": "资质声称无附件/出处支撑（严禁编造）：%s" % line.strip()[:60]})

    # E6 空泛响应：★ 条款所在行里出现"整格只有满足/无偏离"的单元格。
    # 评标专家对 ★ 条款只看"实现方式或参数值"，只写"满足"等于没响应。
    for header, rows, start in tables:
        for r in rows:
            if not any("★" in c for c in r):
                continue
            for c in r:
                if c.replace("★", "").replace("☆", "").strip() in WEAK_CELLS:
                    issues.append({"code": "E6", "level": "高", "line": start,
                                   "msg": "★条款响应空泛（单元格只有「%s」，须给出实现方式/参数值）"
                                          % c.strip()})
                    break

    # E5 ★条款页码覆盖
    if tender_hits is not None:
        star_pages = {h["page"] for h in tender_hits if h["kind"] == "星号条款"}
        if star_pages:
            missing = sorted(star_pages - cited_pages)
            if missing:
                issues.append({"code": "E5", "level": "致命", "line": 0,
                               "msg": "★条款所在页未被引用：P%s（共 %d/%d 页未覆盖）"
                                      % ("、P".join(str(p) for p in missing),
                                         len(missing), len(star_pages))})
    return name, issues


def main():
    ap = argparse.ArgumentParser(description="标书交付物质检")
    ap.add_argument("target", help="交付物 .md 文件或目录")
    ap.add_argument("--tender", default="", help="tender_ingest 输出目录（启用★条款覆盖校验）")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    args = ap.parse_args()

    if not os.path.exists(args.target):
        sys.exit("路径不存在: %s" % args.target)

    hits = None
    if args.tender:
        hp = os.path.join(args.tender, "hits.json")
        if not os.path.isfile(hp):
            sys.exit("找不到 %s，先跑 tender_ingest.py" % hp)
        hits = json.load(open(hp, encoding="utf-8"))

    files = iter_files(args.target)
    if not files:
        sys.exit("没有找到 .md 文件")

    all_results, total_fatal, total_high = [], 0, 0
    for f in files:
        name, issues = audit_file(f, hits)
        all_results.append({"file": name, "issues": issues})
        total_fatal += sum(1 for i in issues if i["level"] == "致命")
        total_high += sum(1 for i in issues if i["level"] == "高")

    if args.json:
        print(json.dumps({"results": all_results,
                          "fatal": total_fatal, "high": total_high}, ensure_ascii=False, indent=2))
    else:
        for r in all_results:
            print("\n== %s" % r["file"])
            if not r["issues"]:
                print("   PASS 无问题")
                continue
            for i in sorted(r["issues"], key=lambda x: (x["level"] != "致命", x["line"])):
                loc = "L%-4d" % i["line"] if i["line"] else "   - "
                print("   [%s][%s] %s %s" % (i["level"], i["code"], loc, i["msg"]))
        print("\n== 合计：致命 %d 项，高风险 %d 项" % (total_fatal, total_high))
        if total_fatal == 0 and total_high == 0:
            print("   PASS 可以交付")
        else:
            print("   FAIL 修完再交（致命项尤其不能留）")

    sys.exit(1 if (total_fatal or total_high) else 0)


if __name__ == "__main__":
    main()
