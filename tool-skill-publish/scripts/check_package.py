#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""技能上架包自检：结构 / frontmatter / 引用完整性 / 占位符 / 三方一致性 / 包内校验脚本

用法：
    python check_package.py <包.zip>
    python check_package.py <包.zip> --src <开发源目录> --dst <安装副本目录>
    python check_package.py <包.zip> --src <开发源目录> --skip-selfcheck

退出码：0 = 全部通过；1 = 有失败项（失败项会逐条列出）

要点：**必须验证 zip 解包后的结果**，不能只验证源目录 —— zip 会丢空目录、丢隐藏文件、路径可能错层。
"""
import argparse
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

# 常见占位符：出现在 frontmatter 里说明"忘了替换"
PLACEHOLDERS = ("个人开发者", "YOUR_NAME", "TODO", "TBD", "PLACEHOLDER", "待填", "xxx")
REQUIRED_FIELDS = ("description", "description_zh", "description_en", "version", "author")

# 包内可能存在的、用于跑业务校验的脚本候选
SELFCHECK_CANDIDATES = ("scripts/check_prototype.py", "scripts/check.py")

md5 = lambda b: hashlib.md5(b).hexdigest()

fail = []
warn = []


def ok(msg):
    print("  [OK]   %s" % msg)


def bad(msg):
    print("  [FAIL] %s" % msg)
    fail.append(msg)


def warn_(msg):
    print("  [WARN] %s" % msg)
    warn.append(msg)


def parse_frontmatter(text):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        return None
    try:
        import yaml
    except ImportError:
        sys.exit("需要 PyYAML：pip install pyyaml")
    return yaml.safe_load(m.group(1))


def load_zip(zip_path, tmp):
    with zipfile.ZipFile(zip_path) as z:
        names = sorted(n for n in z.namelist() if not n.endswith("/"))
        z.extractall(tmp)
    return names


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("zip_path")
    ap.add_argument("--src", help="开发源目录（用于三方一致性校验）")
    ap.add_argument("--dst", help="安装副本目录（用于三方一致性校验 + 多余文件检查）")
    ap.add_argument("--skip-selfcheck", action="store_true",
                    help="跳过包内业务校验脚本（默认会自动找 scripts/check_prototype.py 跑）")
    args = ap.parse_args()

    zip_path = os.path.abspath(args.zip_path)
    if not os.path.isfile(zip_path):
        sys.exit("找不到 zip：%s" % zip_path)

    print("=== 0) 包信息 ===")
    print("  %s   %d B" % (os.path.basename(zip_path), os.path.getsize(zip_path)))

    tmp = tempfile.mkdtemp(prefix="pkgcheck_")
    try:
        print("\n=== 1) 顶层结构 ===")
        with zipfile.ZipFile(zip_path) as z:
            all_names = z.namelist()
        names = sorted(n for n in all_names if not n.endswith("/"))
        tops = {n.split("/")[0] for n in all_names}
        skill = None
        if len(tops) != 1:
            bad("zip 顶层有多个条目：%s（应只有一个技能目录）" % sorted(tops))
        else:
            top = tops.pop()
            # 顶层是文件还是目录？目录的话必然有 "top/..." 形式的条目
            if not any(n.startswith(top + "/") for n in names):
                bad("zip 顶层直接是文件 `%s`，缺少技能目录 —— "
                    "正确形态是 `<技能目录>/SKILL.md`。"
                    "用 shutil.make_archive(out, 'zip', '.', '<技能目录>') 重打" % top)
            else:
                skill = top
                ok("顶层唯一目录：%s/" % skill)
        if skill and ("%s/SKILL.md" % skill) not in names:
            bad("SKILL.md 不在 %s/ 下（当前 zip 顶层若直接是 SKILL.md，平台解析会失败）" % skill)
        elif skill:
            ok("SKILL.md 位置正确：%s/SKILL.md" % skill)
        print("     包内文件 %d 个" % len(names))

        if not skill:
            return finish()

        load_zip(zip_path, tmp)
        root = os.path.join(tmp, skill)

        print("\n=== 2) frontmatter ===")
        skill_md = os.path.join(root, "SKILL.md")
        if not os.path.isfile(skill_md):
            bad("包内找不到 SKILL.md")
            return finish()
        t = io.open(skill_md, encoding="utf-8").read()
        fm = parse_frontmatter(t)
        if fm is None:
            bad("frontmatter 无法解析（检查 --- 分隔与缩进）")
        else:
            ok("YAML 可解析，字段 %d 个" % len(fm))
            missing = [k for k in REQUIRED_FIELDS if not fm.get(k)]
            if missing:
                bad("必填字段缺失：%s" % missing)
            else:
                ok("必填字段齐全：%s" % ", ".join(REQUIRED_FIELDS))
            print("     name=%s  version=%s  author=%s  category=%s"
                  % (fm.get("name"), fm.get("version"), fm.get("author"), fm.get("category")))
            # 占位符检测 —— 最容易漏的一步
            hits = [p for p in PLACEHOLDERS if p in str(fm.get("author", ""))]
            if hits:
                bad("author 仍是占位符 %s —— 提交前必须换成开放平台认证主体" % hits)
            elif fm.get("author"):
                ok("author 非占位符：%s" % fm["author"])
            v = str(fm.get("version", ""))
            if not re.match(r"^\d+\.\d+\.\d+", v):
                warn_("version 不是 semver 形式：%r（市场通常要求 x.y.z）" % v)

        print("\n=== 3) SKILL.md 引用的文件是否真在包里 ===")
        refs = sorted(set(re.findall(
            r"`((?:references|assets|scripts|templates|examples)/[^`]+?\.\w+)`", t)))
        if not refs:
            warn_("未发现 `` 内的相对路径引用（正常吗？）")
        missing = [r for r in refs if not os.path.isfile(os.path.join(root, r.replace("/", os.sep)))]
        if missing:
            bad("引用缺失 %d 个：%s" % (len(missing), missing))
        else:
            ok("%d 个引用文件全部存在" % len(refs))

        print("\n=== 4) 空目录 / 隐藏文件 ===")
        empty_dirs = []
        for dp, dn, fn in os.walk(root):
            if not dn and not fn:
                empty_dirs.append(os.path.relpath(dp, root))
        if empty_dirs:
            warn_("包内有空目录：%s（zip 不保留空目录，索引里别声称有内容）" % empty_dirs)
        else:
            ok("无空目录")
        junk = [os.path.relpath(os.path.join(dp, f), root)
                for dp, _, fn in os.walk(root) for f in fn
                if f.endswith((".pyc", ".tmp", ".bak", ".log", ".DS_Store")) or f.startswith("._")]
        if junk:
            bad("含垃圾文件：%s" % junk)
        else:
            ok("无 .pyc/.tmp/.bak 等垃圾文件")

        if not args.skip_selfcheck:
            print("\n=== 5) 跑包内自带校验脚本 ===")
            ran = False
            for cand in SELFCHECK_CANDIDATES:
                p = os.path.join(root, cand.replace("/", os.sep))
                if not os.path.isfile(p):
                    continue
                ran = True
                targets = []
                adir = os.path.join(root, "assets")
                if os.path.isdir(adir):
                    targets = [os.path.join(adir, x) for x in sorted(os.listdir(adir))
                               if x.endswith(".html")]
                r = subprocess.run([sys.executable, p] + targets,
                                   capture_output=True, text=True,
                                   encoding="utf-8", errors="replace")
                out = (r.stdout or "") + (r.stderr or "")
                tail = [l for l in out.splitlines() if "ERROR" in l or "WARN" in l]
                print("     %s -> returncode=%d  %s" % (cand, r.returncode, tail[-1:] or ""))
                if r.returncode != 0:
                    bad("包内脚本 %s 返回非 0" % cand)
                else:
                    ok("包内脚本 %s 通过" % cand)
            if not ran:
                print("     （未找到 %s，跳过）" % " / ".join(SELFCHECK_CANDIDATES))

        if args.src or args.dst:
            print("\n=== 6) 三方一致性 zip / 开发源 / 安装副本 ===")
            with zipfile.ZipFile(zip_path) as z:
                for n in names:
                    rel = n.split("/", 1)[1]
                    zb = z.read(n)
                    for base, label in ((args.src, "开发源"), (args.dst, "安装副本")):
                        if not base:
                            continue
                        fp = os.path.join(base, rel.replace("/", os.sep))
                        if not os.path.isfile(fp):
                            bad("%s 缺文件：%s" % (label, rel))
                        elif md5(open(fp, "rb").read()) != md5(zb):
                            bad("%s 与 zip 不一致：%s" % (label, rel))
            if not fail:
                ok("zip 内 %d 个文件与开发源、安装副本 md5 全一致" % len(names))
            if args.dst:
                packed = {n.split("/", 1)[1] for n in names}
                extra = [x for x in (os.path.relpath(os.path.join(dp, f), args.dst).replace(os.sep, "/")
                                     for dp, _, fn in os.walk(args.dst) for f in fn)
                         if x not in packed]
                if extra:
                    warn_("安装副本有包外多余文件：%s" % extra)
                else:
                    ok("安装副本无多余文件")

        return finish()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def finish():
    print("\n=== 结论 ===")
    if fail:
        print("  失败 %d 项：" % len(fail))
        for f in fail:
            print("    - %s" % f)
    else:
        print("  全部检查通过")
    if warn:
        print("  提醒 %d 项（不阻断）：" % len(warn))
        for w in warn:
            print("    - %s" % w)
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
