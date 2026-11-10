#!/usr/bin/env python3
"""知识库修复战役终验脚本（tool-kb-audit-repair 阶段3）。

机械检查：密码残留 / 存根 / 空目录 / XML与语雀标记残留 / 导出噪音 /
围栏平衡 / <title> 残留 / 疑似悬空数字（人工复核项）。

用法:
  python verify_kb.py --root library/技术
  python verify_kb.py --root library --archive-root library/_备份元数据
  python verify_kb.py --root library --json   # 机器可读输出

退出码: 0=全部PASS, 1=存在FAIL。疑似悬空数字只算 WARN 不影响退出码。
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

SKIP_DIRS = {"__pycache__", ".git", "node_modules"}

# (标签, 编译好的正则, 是否只在行内搜)
PASSWORD_PATTERNS = [
    ("疑似root密码(Root@)", re.compile(r"Root@(?=[^\s]*\d)")),
    ("密码明文值", re.compile(r"(?:密码|passwd|password|pwd)\s*[:：=]\s*([^\s<>]{4,})")),
]
# 明文值后过滤：占位/描述/教程常见示例值不算泄漏
PLACEHOLDER_RE = re.compile(
    r"已脱敏|见密码管理器|xxx+|<[^>]+>|\*\*\*|默认|示例|为空|可自行|改成|设置为|your|"
    r"^(123456|admin|password|test|demo|changeme|1234(56)?)$", re.I)
PLACEHOLDER_RE = re.compile(r"已脱敏|见密码管理器|xxx+|<[^>]+>|\*\*\*")
XML_PATTERNS = [
    ("飞书callout残留", re.compile(r"<callout")),
    ("sub-page-list残留", re.compile(r"<sub-page-list")),
    ("bookmark标签残留", re.compile(r"<bookmark")),
    ("whiteboard残留", re.compile(r"<whiteboard")),
]
TITLE_RE = re.compile(r"^<title>.+</title>\s*$")
FENCE_RE = re.compile(r"^```")
# 疑似悬空数字 —— 误报率高(取模%N、like '%abc'均合法)，仅 WARN 供人工复核
DANGLING_PATTERNS = [
    ("空格+%+的(悬空百分比)", re.compile(r"\s%\s*的")),
    ("中文+%+结尾(悬空百分比)", re.compile(r"[\u4e00-\u9fff]\s*%[，。;；\s]")),
    (">){(疑似代码被啃", re.compile(r"[><=!]=?\s*\)\s*\{\s*$")),
]
NOISE_PATTERNS = [("复制代码噪音", re.compile(r"复制代码"))]

FENCE_BLOCK = re.compile(r"```.*?```", re.S)  # 用于剥离围栏内容再搜标记


def strip_fenced(text: str) -> str:
    return FENCE_BLOCK.sub("", text)


def read_text(p: Path) -> str:
    for enc in ("utf-8", "utf-8-sig", "gbk"):
        try:
            return p.read_text(encoding=enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return p.read_text(encoding="utf-8", errors="replace")


def iter_md(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            if f.lower().endswith(".md"):
                yield Path(dirpath) / f


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="library", help="被检查的知识库根目录")
    ap.add_argument("--archive-root", default="library/_备份元数据",
                    help="归档区(从此根排除事故判定，密码原稿单独点名)")
    ap.add_argument("--json", action="store_true", help="输出JSON")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    archive = Path(args.archive_root).resolve()
    if not root.exists():
        print(f"[FAIL] 根目录不存在: {root}")
        return 1

    findings = {"password": [], "stub": [], "empty_dir": [], "xml": [],
                "noise": [], "fence": [], "title": [], "dangling": [], "nbsp": []}
    n_md = 0
    archive_pw_files = []

    for p in iter_md(root):
        n_md += 1
        in_archive = archive in p.parents
        text = read_text(p)
        stripped = strip_fenced(text)
        rel = p.relative_to(root).as_posix()

        # 密码扫描只在围栏外搜（教程配置示例在代码块里属正常内容）
        for label, pat in PASSWORD_PATTERNS:
            for i, line in enumerate(stripped.splitlines(), 1):
                m = pat.search(line)
                if m:
                    value = m.group(1) if m.groups() else m.group(0)
                    if value and not PLACEHOLDER_RE.search(value):
                        if in_archive:
                            archive_pw_files.append(rel)
                        else:
                            findings["password"].append(f"{rel}:{i} [{label}] {value[:20]}")
                        break  # 每文件每类报一次即可

        # <100B 存根；内容为纯图/纯链接引用的不算（语雀纯图笔记是预期保留形态）
        if p.stat().st_size < 100:
            if not re.search(r"!\[|<img|https?://", text):
                findings["stub"].append(f"{rel} ({p.stat().st_size}B)")

        for label, pat in XML_PATTERNS:
            if pat.search(stripped):
                findings["xml"].append(f"{rel} [{label}]")
                break
        if re.search(r"^:::", stripped, re.M):
            findings["xml"].append(f"{rel} [语雀:::残留]")
        for label, pat in NOISE_PATTERNS:
            if pat.search(stripped):
                findings["noise"].append(f"{rel} [{label}]")
                break

        fence_lines = [l for l in text.splitlines() if FENCE_RE.match(l)]
        if len(fence_lines) % 2 == 1:
            findings["fence"].append(f"{rel} (围栏行数奇数: {len(fence_lines)})")
        first = next((l for l in text.splitlines() if l.strip()), "")
        if TITLE_RE.match(first.strip()):
            findings["title"].append(rel)
        if "\xa0" in text:
            findings["nbsp"].append(f"{rel} (NBSP×{text.count(chr(160))})")

        if not in_archive:
            for label, pat in DANGLING_PATTERNS:
                for i, line in enumerate(stripped.splitlines(), 1):
                    if pat.search(line):
                        findings["dangling"].append(f"{rel}:{i} [{label}] {line.strip()[:60]}")
                        break  # 每文件每类报一例

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        if not dirnames and not filenames:
            findings["empty_dir"].append(Path(dirpath).relative_to(root).as_posix() or ".")

    def section(key, title, level="FAIL"):
        items = findings[key]
        if not items:
            print(f"[PASS] {title}: 0")
        else:
            print(f"[{level}] {title}: {len(items)}")
            for it in items[:20]:
                print(f"    - {it}")
            if len(items) > 20:
                print(f"    ... 另 {len(items)-20} 项")

    fails = sum(1 for k in ("password", "stub", "empty_dir", "xml",
                            "noise", "fence", "title", "nbsp") if findings[k])

    if not args.json:
        print(f"=== 知识库终验: {root} (扫描 {n_md} 个md) ===")
        for key, title in [("password", "密码残留(工作区)"), ("stub", "存根残留(<100B)"),
                           ("empty_dir", "空目录"), ("xml", "XML/语雀标记残留"),
                           ("noise", "导出噪音"), ("fence", "围栏未闭合"),
                           ("title", "<title>首行残留"), ("nbsp", "NBSP残留(U+00A0)")]:
            section(key, title)
        section("dangling", "疑似悬空数字(人工复核,不算FAIL)", level="WARN")

        if archive_pw_files:
            uniq = sorted(set(archive_pw_files))
            print(f"[INFO] 归档区含密码原稿 {len(uniq)} 份(预期内,轮换后删除):")
            for it in uniq[:10]:
                print(f"    - {it}")
        print(f"=== 结果: {'FAIL' if fails else 'ALL PASS'} ({fails} 类FAIL, {n_md} 个md) ===")

    if args.json:
        out = dict(findings, _archive_passwords=sorted(set(archive_pw_files)),
                   _scanned=n_md, _root=str(root))
        print(json.dumps(out, ensure_ascii=False, indent=2))

    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
