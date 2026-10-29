#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""build_three_bundle.py —— 预构建「three.js r160 + 孪生引擎」单一 IIFE bundle

产物: assets/three-r160-bundle.js
供 scaffold.py --offline-three 内联进页面（CSP 兼容：无 importmap/blob/data: 脚本源）。

为什么不用 importmap 方案：严格 CSP（script-src 'self' 'unsafe-inline'，如
WorkBuddy 资料库在线预览）会拦截 data:/blob: 脚本源，importmap 的 data URI
模块全部加载失败。单一内联经典脚本是唯一通吃形态。

前置：esbuild 已装在 node 托管工作区（npm install esbuild）。
依赖引擎变更时重跑本脚本即可。

用法：python build_three_bundle.py [--esbuild <path>]
"""
import argparse, os, re, shutil, subprocess, sys, tempfile

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKELETON = os.path.join(SKILL, "assets", "twin-skeleton.html")
VENDOR = os.path.join(SKILL, "assets", "three-r160")
OUT = os.path.join(SKILL, "assets", "three-r160-bundle.js")

# 候选 esbuild 位置
def find_esbuild():
    cands = []
    arg = None
    for a in sys.argv:
        if a == "--esbuild":
            arg = "next"
        elif arg == "next":
            cands.append(a)
    ws = r"C:/Users/qq940/.workbuddy/binaries/node/workspace/node_modules/esbuild/bin/esbuild"
    cands.append(ws)
    for c in cands:
        if os.path.exists(c):
            return c
    return "esbuild"  # PATH 兜底

def find_node():
    for c in (r"C:/Users/qq940/.workbuddy/binaries/node/versions/22.22.2-6/node.exe", "node"):
        if shutil.which(c) or os.path.exists(c):
            return c
    return "node"

def rewrite(text):
    text = re.sub(r"from\s*'three'\s*;", "from './three.module.js';", text)
    text = re.sub(r"from\s*'three/addons/[A-Za-z0-9_]+/[A-Za-z0-9_]+\.js'",
                  lambda m: "from './%s'" % re.search(r"/([A-Za-z0-9_]+\.js)", m.group(0)).group(1),
                  text)
    # 后处理模块（postprocessing/*）对 shaders/ math/ 的上级相对引用，扁平化后需拉平
    text = re.sub(r"from\s*'\.\./(?:shaders|math|utils)/([A-Za-z0-9_]+\.js)'",
                  r"from './\1'", text)
    return text

def main():
    if not os.path.exists(SKELETON):
        sys.exit("找不到骨架：%s" % SKELETON)
    t = open(SKELETON, encoding="utf-8").read()
    m = re.search(r'<script type="text/plain" id="twinEngineSrc">(.*?)</script>', t, re.S)
    if not m:
        sys.exit("骨架中未找到 twinEngineSrc 引擎槽")
    engine = rewrite(m.group(1))

    stage = tempfile.mkdtemp(prefix="twinbundle_")
    open(os.path.join(stage, "engine-src.js"), "w", encoding="utf-8").write(engine)
    for f in os.listdir(VENDOR):
        if f.endswith(".js"):
            raw = open(os.path.join(VENDOR, f), encoding="utf-8").read()
            open(os.path.join(stage, f), "w", encoding="utf-8").write(rewrite(raw))

    node, esb = find_node(), find_esbuild()
    r = subprocess.run([node, esb, os.path.join(stage, "engine-src.js"),
                        "--bundle", "--format=iife", "--target=es2018",
                        "--outfile=" + OUT, "--log-level=warning"],
                       capture_output=True, text=True)
    if not os.path.exists(OUT):
        sys.stderr.write(r.stderr[-3000:])
        sys.exit("esbuild 打包失败")
    js = open(OUT, encoding="utf-8").read()
    assert "</script" not in js, "bundle 含 </script 危险序列，禁止内联"
    shutil.rmtree(stage, ignore_errors=True)
    print("bundle 已构建：%s（%.1f MB）" % (OUT, os.path.getsize(OUT) / 1048576.0))

if __name__ == "__main__":
    main()
