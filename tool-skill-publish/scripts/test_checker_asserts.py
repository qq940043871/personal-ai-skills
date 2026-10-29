#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_package.py 的回归测试：反向验证每条断言真的会触发。

「从不报错的检查等于没有检查」—— 这个脚本故意构造已知缺陷的包，
断言 check_package.py 必须报错。任何一条不再报错，说明该检查项失效了。

用法：
    python test_checker_asserts.py
退出码：0 = 全部断言按预期触发；1 = 有检查项失效（回归）
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKER = os.path.join(HERE, "check_package.py")
SKILL_NAME = "demo-skill"

GOOD_FM = """---
name: demo-skill
display_name: Demo
description: "demo"
description_zh: demo
description_en: demo
version: 1.0.0
author: hasWhere
---

正文。引用 `references/guide.md`。
"""


def build(tmp, dirname, skill_md, extra=None, flat=False):
    """flat=True 模拟打包层级错误（不建技能顶层目录）"""
    base = os.path.join(tmp, dirname)
    inner = base if flat else os.path.join(base, SKILL_NAME)
    os.makedirs(inner, exist_ok=True)
    io.open(os.path.join(inner, "SKILL.md"), "w", encoding="utf-8", newline="").write(skill_md)
    for rel, content in (extra or {}).items():
        p = os.path.join(inner, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        io.open(p, "w", encoding="utf-8", newline="").write(content)
    z = os.path.join(tmp, dirname + ".zip")
    with zipfile.ZipFile(z, "w") as f:
        for dp, _, fn in os.walk(base):
            for x in fn:
                fp = os.path.join(dp, x)
                arc = os.path.relpath(fp, base) if flat else os.path.join(SKILL_NAME, os.path.relpath(fp, inner))
                f.write(fp, arc)
    return z


def main():
    tmp = tempfile.mkdtemp(prefix="checker_test_")
    cases = [
        ("占位符 author + 引用缺失",
         build(tmp, "A", GOOD_FM.replace("author: hasWhere", "author: 个人开发者")),
         ["占位符", "引用缺失"]),
        ("打包层级错误（顶层是文件）",
         build(tmp, "B", GOOD_FM, flat=True),
         ["缺少技能目录"]),
        ("frontmatter 必填缺失",
         build(tmp, "C", GOOD_FM.replace("description_en: demo\n", ""),
               extra={"references/guide.md": "x"}),
         ["必填字段缺失"]),
        ("垃圾文件",
         build(tmp, "D", GOOD_FM,
               extra={"references/guide.md": "x", "scripts/__pycache__/a.pyc": "junk"}),
         ["垃圾文件"]),
    ]

    failures = []
    try:
        for label, z, expect_keywords in cases:
            print("\n" + "-" * 62)
            print("用例：%s" % label)
            r = subprocess.run([sys.executable, CHECKER, z, "--skip-selfcheck"],
                               capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
            out = (r.stdout or "") + (r.stderr or "")
            fails = [l.strip() for l in out.splitlines() if "[FAIL]" in l]
            for l in fails:
                print("   " + l)
            if r.returncode != 1:
                failures.append("%s：退出码 %d（预期 1）" % (label, r.returncode))
                print("   !! 未被捕获 —— 该检查失效")
            elif not any(k in out for k in expect_keywords):
                failures.append("%s：退出码对但没报出预期关键字 %s" % (label, expect_keywords))
                print("   !! 报错了但不是预期的原因：%s" % expect_keywords)
            else:
                print("   -> 已捕获，符合预期")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n" + "=" * 62)
    if failures:
        print("回归失败 %d 项：" % len(failures))
        for f in failures:
            print("  - %s" % f)
        return 1
    print("全部 %d 个反向用例均按预期触发" % len(cases))
    return 0


if __name__ == "__main__":
    sys.exit(main())
