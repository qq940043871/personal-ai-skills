#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audit_notes.py - 章节笔记结构审计（build_site 契约的守门人）。

为什么需要它：子代理自报"结构校验通过"不可信。实测 18 章里查出 3 章共 21 个代码块缺 caption。
本脚本把历次项目里手搓的 audit.py / _audit.py / audit2.py / audit3.py 统一成一份。

用法:
    python audit_notes.py --book D:/books/深入分析JavaWeb
    python audit_notes.py --book D:/books/失控 --profile prose
    python audit_notes.py --book D:/books/x --expect-sections 4,6,3 --strict
    python audit_notes.py --book D:/books/x --json     # 机器可读，便于自动化

审计项:
  1.  H1 恰为 1（统计前先按 ``` 切块跳过代码内部，否则代码注释 # 会被当成标题）
  2.  围栏配平（未闭合的 ``` 会让后面所有内容解析错位）
  3.  五个固定小节齐全且顺序正确
  4.  每个代码块首行有 // caption:
  5.  Q / A 数量配对
  6.  无 "- **误区**：" 前缀（模板自带 ⚠ 图标，写了会重复）
  7.  章号可被 build_site 的 H1 正则识别（否则站点上章号不显示）
  8.  空代码块 / 空卡片 / 节内无卡片
  9.  可选：每章分节数与预期一致（--expect-sections）
  10. 占位符残留（__XXX__ / TODO / FIXME / 待补充）

退出码: 0 = 无ERROR（可能有 WARN）；1 = 有 ERROR；2 = 参数/环境错误
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

# build_site.py 的固定小节（--profile tech/prose/prose-nocode 的差别只在第 2 项）
PROFILE_CODE_SECTION = {
    "tech": "代码要点",
    "prose": "关键论断",
    "prose-nocode": "关键论断",
}

CHAP_NUM_RE = re.compile(r"^(第[^章篇部\s]*[章篇部][分]?)\s*(.*)$")
MISTAKE_PREFIX_RE = re.compile(r"^\s*[-*]\s*\*\*误区\*\*\s*[：:]")
DEEP_PREFIX_RE = re.compile(r"^\s*[-*]\s*\*\*深入\*\*\s*[：:]")
Q_RE = re.compile(r"\*\*Q\*\*\s*[：:]")
A_RE = re.compile(r"\*\*A\*\*\s*[：:]")
CAPTION_RE = re.compile(r"^\s*(?://|#|--|;|/\*)\s*caption:\s*\S", re.I)
CAPTION_XML_RE = re.compile(r"^\s*<!--\s*caption:\s*\S", re.I)
# 只抓"真的是占位"的写法：模板占位符、TODO/FIXME、整行「待补充」。
# 注意不要把正文里的省略号（……/...）当占位符——中文笔记里省略号极常见，
# 历史误报：工业AI ch11 一句正常的"…检查缺失签名、超限、时间顺序和程序…"被判成残留。
PLACEHOLDER_RE = re.compile(r"__[A-Z_]{2,}__|\bTODO\b|\bFIXME\b|\bXXX\b")
PLACEHOLDER_LINE_RE = re.compile(r"^\s*(?:[-*]\s*)?(?:待补充|待写|TODO|FIXME)\s*[:：]?\s*$", re.I)

# 模板里真正存在的占位符（读模板现算，避免手抄清单过期）
_FALLBACK_PLACEHOLDERS = {"__TITLE__", "__SUBTITLE__", "__META__", "__STATS__", "__NAV__",
                          "__CONTENT__", "__TOTAL_CARDS__", "__HERO_TAG__", "__HERO_CHIPS__",
                          "__FOOTER__", "__SLUG__"}


def template_placeholders():
    tpl = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "assets", "site_template.html")
    try:
        with open(tpl, encoding="utf-8") as f:
            found = set(re.findall(r"__[A-Z_]{2,}__", f.read()))
        return found or set(_FALLBACK_PLACEHOLDERS)
    except OSError:
        return set(_FALLBACK_PLACEHOLDERS)


def split_code(lines):
    """把行切成 (是否在代码块内, 行) —— 所有标题统计前必须先过这一关。

    历史坑：第一版审计没排除代码块内的 # 注释，ch01 报出 H1=51 的荒谬假警报。
    """
    out = []
    in_code = False
    for ln in lines:
        s = ln.strip()
        if s.startswith("```"):
            in_code = not in_code
            out.append((True, ln))     # 围栏行本身算"代码内"，避免 ````java` 被当标题
            continue
        out.append((in_code, ln))
    return out, in_code


def audit_file(path, code_section):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    lines = text.replace("\r\n", "\n").split("\n")
    tagged, unclosed = split_code(lines)

    res = {
        "path": path, "chars": len(text),
        "h1": [], "h2": [], "h3": 0,
        "fence_balance": not unclosed,
        "code_blocks": [],        # {lang, lines, has_caption, empty}
        "q": 0, "a": 0, "mistake_prefix": 0, "deep_prefix": 0,
        "placeholders": [],
    }

    # 代码块收集
    cur = None
    for in_code, ln in tagged:
        s = ln.strip()
        if s.startswith("```"):
            if cur is None:
                lang = s[3:].strip().split()[0] if len(s) > 3 else "text"
                cur = {"lang": lang or "text", "lines": []}
            else:
                body = cur["lines"]
                while body and not body[0].strip():
                    body.pop(0)
                while body and not body[-1].strip():
                    body.pop()
                blk = dict(cur)
                blk["has_caption"] = bool(
                    body and (CAPTION_RE.match(body[0]) or CAPTION_XML_RE.match(body[0])))
                blk["empty"] = len([x for x in body if x.strip()]) <= 1
                res["code_blocks"].append(blk)
                cur = None
            continue
        if in_code and cur is not None:
            cur["lines"].append(ln)

    # 标题 / 标记统计（只在代码块外）
    for in_code, ln in tagged:
        if in_code:
            continue
        s = ln.strip()
        if s.startswith("### "):
            res["h3"] += 1
        elif s.startswith("## "):
            res["h2"].append(s[3:].strip())
        elif s.startswith("# "):
            res["h1"].append(s[2:].strip())
        if MISTAKE_PREFIX_RE.match(ln):
            res["mistake_prefix"] += 1
        if DEEP_PREFIX_RE.match(ln):
            res["deep_prefix"] += 1
        if Q_RE.search(ln):
            res["q"] += 1
        if A_RE.search(ln):
            res["a"] += 1
        if PLACEHOLDER_RE.search(ln) or PLACEHOLDER_LINE_RE.match(ln):
            res["placeholders"].append(s[:80])

    fixed = ["核心概念", code_section, "常见误区与深入理解", "自测问题", "本章收获"]
    res["fixed_present"] = [k for k in fixed if k in res["h2"]]
    res["fixed_missing"] = [k for k in fixed if k not in res["h2"]]
    res["fixed_order_ok"] = (
        len(res["fixed_present"]) == len(fixed)
        and res["h2"].index(fixed[0]) < res["h2"].index(fixed[1])
        < res["h2"].index(fixed[2]) < res["h2"].index(fixed[3])
        < res["h2"].index(fixed[4])
    ) if not res["fixed_missing"] else False

    # 正节 = H2 总数 - 固定小节数
    res["sections"] = len(res["h2"]) - len(fixed)
    res["unknown_h2"] = [h for h in res["h2"] if h not in fixed]
    res["num_ok"] = bool(res["h1"]) and bool(CHAP_NUM_RE.match(res["h1"][0]))
    res["cards"] = res["h3"]
    return res


def check_site_vs_dom(site_path, code_section):
    """核对已编译站点的统计条与 DOM 实际数量是否一致。

    为什么必须查：build_site 的统计曾经只扫一层块、且漏扫固定小节，
    Phoenix 一书统计条报 536 卡片 / 115 代码块，DOM 实际 537 / 144 —— 站点自己骗自己。
    这个函数把"统计口径 == 渲染口径"变成可自动验证的断言。
    """
    problems = []
    if not os.path.isfile(site_path):
        return ["--check-site 指定的站点不存在: %s" % site_path]
    with open(site_path, "r", encoding="utf-8") as f:
        t = f.read()

    stats = {}
    for m in re.finditer(r'<div class="stat"><b>(\d+)</b><span>([^<]+)</span></div>', t):
        stats[m.group(2)] = int(m.group(1))

    dom = {
        "知识点卡片": len(re.findall(r'<article class="card"', t)),
        code_section: len(re.findall(r'<div class="code-block">', t)),
        "自测题": len(re.findall(r'<div class="qa" data-id=', t)),
    }
    for label, claimed in stats.items():
        if label not in dom:
            continue
        actual = dom[label]
        if claimed != actual:
            problems.append("统计条「%s」= %d，但 DOM 实际 %d（统计口径与渲染口径不一致）"
                            % (label, claimed, actual))
    # ⚠ 只报"模板里真的存在过的占位符"。裸扫 __X__ 会把技术书正文里的 C 宏当残留
    # （《操作系统真象还原》的 `#define PANIC(...) panic_spin(__FILE__, __LINE__, __VA_ARGS__)`
    # 曾报 3 个假 ERROR）。
    tpl_ph = template_placeholders()
    for ph in sorted(set(re.findall(r"__[A-Z_]{2,}__", t)) & tpl_ph):
        problems.append("站点残留未替换占位符 %s" % ph)
    # ⚠ 脏值同理不能裸判：NaN 只在后面跟尺寸单位时才算渲染坏掉（正文里的合法字面量放过）
    if re.search(r"\bundefined\b", t):
        problems.append("站点正文含脏值 undefined")
    if re.search(r"(?<![\w.])NaN\s*(px|%|em|rem|vh|vw|s)\b", t):
        problems.append("站点正文含脏值 NaN<尺寸>")
    if "[object Object]" in t:
        problems.append("站点正文含脏值 [object Object]")
    return problems


def main():
    ap = argparse.ArgumentParser(description="章节笔记结构审计")
    ap.add_argument("--book", default="", help="书籍文件夹（含 _extract/notes）")
    ap.add_argument("--notes", default="", help="直接指定 notes 目录")
    ap.add_argument("--profile", default="tech", choices=list(PROFILE_CODE_SECTION))
    ap.add_argument("--expect-sections", default="",
                    help="每章正节数预期，逗号分隔按章序，如 4,6,3")
    ap.add_argument("--min-cards", type=int, default=3, help="每章最少卡片数（默认 3）")
    ap.add_argument("--strict", action="store_true", help="把 WARN 也算失败")
    ap.add_argument("--check-site", default="", help="同时核对已编译站点的统计条与 DOM 是否一致")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    args = ap.parse_args()

    notes_dir = args.notes
    if not notes_dir and args.book:
        notes_dir = os.path.join(os.path.abspath(args.book), "_extract", "notes")
    if not notes_dir or not os.path.isdir(notes_dir):
        sys.exit("笔记目录不存在: %s" % (notes_dir or "(未指定)"))

    files = sorted(f for f in os.listdir(notes_dir)
                   if f.startswith("ch") and f.endswith(".md"))
    if not files:
        sys.exit("目录里没有 chNN.md: %s" % notes_dir)

    expect = [int(x) for x in args.expect_sections.split(",") if x.strip()] \
        if args.expect_sections else []
    code_section = PROFILE_CODE_SECTION[args.profile]

    errors, warns, rows = [], [], []
    for i, fn in enumerate(files):
        r = audit_file(os.path.join(notes_dir, fn), code_section)
        cid = fn[:-3]
        tag = cid

        if len(r["h1"]) != 1:
            errors.append("%s H1 数量 = %d（应为 1）：%s" % (tag, len(r["h1"]), r["h1"][:3]))
        if not r["fence_balance"]:
            errors.append("%s 代码围栏未闭合（``` 数为奇数）" % tag)
        if r["fixed_missing"]:
            errors.append("%s 缺固定小节: %s" % (tag, "、".join(r["fixed_missing"])))
        elif not r["fixed_order_ok"]:
            errors.append("%s 固定小节顺序错误，应为：核心概念/%s/常见误区/自测/收获，实际：%s"
                          % (tag, code_section, "、".join(r["fixed_present"])))
        if r["q"] != r["a"]:
            errors.append("%s Q/A 不配对：Q=%d A=%d" % (tag, r["q"], r["a"]))
        if r["q"] == 0:
            warns.append("%s 没有自测题（每章建议 3-6 道）" % tag)
        if r["mistake_prefix"]:
            errors.append("%s 有 %d 处 '- **误区**：' 前缀，模板自带 ⚠ 图标，应删掉前缀"
                          % (tag, r["mistake_prefix"]))
        if not r["num_ok"]:
            warns.append("%s H1 未匹配「第N章/篇/部/部分」，站点上章号会不显示：%s"
                         % (tag, r["h1"][0][:40] if r["h1"] else "(无)"))
        nocap = [j for j, b in enumerate(r["code_blocks"]) if not b["has_caption"]]
        if nocap:
            errors.append("%s 有 %d 个代码块缺 // caption:（块序号 %s）"
                          % (tag, len(nocap), nocap[:8]))
        empt = [j for j, b in enumerate(r["code_blocks"]) if b["empty"]]
        if empt:
            errors.append("%s 有 %d 个空代码块（块序号 %s）" % (tag, len(empt), empt[:8]))
        if r["cards"] < args.min_cards:
            warns.append("%s 卡片数 %d < %d" % (tag, r["cards"], args.min_cards))
        if r["sections"] <= 0:
            warns.append("%s 没有正节（只有固定小节）" % tag)
        if r["placeholders"]:
            errors.append("%s 有占位符/TODO 残留：%s" % (tag, r["placeholders"][:3]))
        if expect and i < len(expect) and r["sections"] != expect[i]:
            warns.append("%s 正节数 %d，预期 %d" % (tag, r["sections"], expect[i]))

        rows.append({"cid": cid, "h1": r["h1"][:1], "sections": r["sections"],
                     "cards": r["cards"], "code": len(r["code_blocks"]),
                     "quiz": r["q"]})

    if args.check_site:
        errors.extend(check_site_vs_dom(args.check_site, code_section))

    if args.json:
        print(json.dumps({"notes_dir": notes_dir, "profile": args.profile,
                          "chapters": len(rows), "errors": errors, "warns": warns,
                          "rows": rows}, ensure_ascii=False, indent=2))
        sys.exit(1 if (errors or (args.strict and warns)) else 0)

    tot = {"sections": sum(r["sections"] for r in rows), "cards": sum(r["cards"] for r in rows),
           "code": sum(r["code"] for r in rows), "quiz": sum(r["quiz"] for r in rows)}
    print("审计 %s（%d 章 · profile=%s）" % (notes_dir, len(rows), args.profile))
    print("  合计：%d 节 · %d 卡片 · %d 代码块 · %d 自测题"
          % (tot["sections"], tot["cards"], tot["code"], tot["quiz"]))
    if errors:
        print("\nERROR %d：" % len(errors))
        for e in errors:
            print("  x " + e)
    if warns:
        print("\nWARN %d：" % len(warns))
        for w in warns:
            print("  ! " + w)
    if not errors and not warns:
        print("\n全部通过，0 问题。")
    sys.exit(1 if (errors or (args.strict and warns)) else 0)


if __name__ == "__main__":
    main()