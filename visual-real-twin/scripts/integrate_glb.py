#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
integrate_glb.py —— 把体检通过的 GLB 集成进姊妹技能并生成 models[] 片段

用法：
    python integrate_glb.py tank.glb --target twin --name "1号储罐" \
        --position "[190,0,40]" [--id TANK-01] [--scale 1] [--rotation 30] \
        [--fallback box:4,26,4] [--config my.json]

行为：
1. 定位目标技能目录：--skill-dir 显式指定 > 已安装目录（~/.agents/skills/）
   > 工作区（脚本所在仓库根的 ../visual-digital-twin 等）
2. 拷贝 GLB 到 <目标技能>/assets/models/（twin）/ 用户指定目录（three）
3. 打印 models[] 配置片段；给了 --config 就把条目合并进该 JSON 的 models 数组
"""
import argparse
import glob
import json
import os
import shutil
import sys

TARGETS = {
    "twin":  {"skill": "visual-digital-twin",   "model_dir": os.path.join("assets", "models")},
    "three": {"skill": "visual-threejs-scene",  "model_dir": os.path.join("assets", "models")},
}


def locate_skill(target, override):
    if override:
        if not os.path.isdir(override):
            sys.exit("--skill-dir 不存在: %s" % override)
        return override
    name = TARGETS[target]["skill"]
    candidates = []
    home = os.path.expanduser("~")
    candidates += glob.glob(os.path.join(home, ".agents", "skills", name))
    candidates += glob.glob(os.path.join(home, ".workbuddy", "skills", name))
    # 脚本在 <repo>/visual-real-twin/scripts/，工作区兄弟技能在 <repo>/<skill>/
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    candidates.append(os.path.join(repo, name))
    for c in candidates:
        if os.path.isdir(c):
            return c
    sys.exit("找不到目标技能 %s（用 --skill-dir 显式指定）\n尝试过: %s" % (name, candidates))


def parse_vec(s, what, n):
    try:
        v = json.loads(s)
        if isinstance(v, list) and len(v) == n and all(isinstance(x, (int, float)) for x in v):
            return v
    except Exception:
        pass
    sys.exit("--%s 需要长度为 %d 的数字数组，收到: %s" % (what, n, s))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("glb")
    ap.add_argument("--target", choices=list(TARGETS), default="twin")
    ap.add_argument("--skill-dir", default=None)
    ap.add_argument("--id", default=None, help="唯一键，默认取文件名大写")
    ap.add_argument("--name", required=True, help="场景显示名")
    ap.add_argument("--position", default="[0,0,0]", help='世界坐标 "[x,y,z]"')
    ap.add_argument("--rotation", type=float, default=0, help="绕 Y 角度（度）")
    ap.add_argument("--scale", type=float, default=1)
    ap.add_argument("--fallback", default=None,
                    help='加载失败回退体，如 "box:4,26,4"')
    ap.add_argument("--config", default=None, help="把条目合并进该 JSON 配置的 models[]")
    args = ap.parse_args()

    if not os.path.isfile(args.glb):
        sys.exit("找不到 GLB: %s" % args.glb)

    tgt = TARGETS[args.target]
    skill_dir = locate_skill(args.target, args.skill_dir)
    dst_dir = os.path.join(skill_dir, *tgt["model_dir"].split(os.sep))
    os.makedirs(dst_dir, exist_ok=True)
    dst = os.path.join(dst_dir, os.path.basename(args.glb))
    shutil.copy2(args.glb, dst)

    asset_id = args.id or os.path.splitext(os.path.basename(args.glb))[0].upper()
    entry = {
        "id": asset_id,
        "name": args.name,
        "url": "models/%s" % os.path.basename(args.glb).replace(os.sep, "/"),
        "position": parse_vec(args.position, "position", 3),
    }
    if args.rotation:
        entry["rotation"] = args.rotation
    if args.scale != 1:
        entry["scale"] = args.scale
    if args.fallback:
        kind, _, dims = args.fallback.partition(":")
        try:
            size = [float(x) for x in dims.split(",") if x.strip()]
        except ValueError:
            size = []
        if len(size) != 3:
            sys.exit('--fallback 需要格式 "类型:长,高,深"，收到: %s' % args.fallback)
        entry["fallback"] = {"type": kind, "size": size}

    snippet = json.dumps({"models": [entry]}, ensure_ascii=False, indent=2)

    if args.config:
        with open(args.config, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        cfg.setdefault("models", [])
        cfg["models"] = [m for m in cfg["models"] if m.get("id") != asset_id] + [entry]
        with open(args.config, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        print("已合并进配置: %s（models 数组现有 %d 项，id=%s）" % (args.config, len(cfg["models"]), asset_id))

    print()
    print("GLB 已拷贝 -> %s" % dst)
    print("配置片段（--config 已自动合并时可忽略）:")
    print(snippet)
    print()
    print("下一步:")
    if args.target == "twin":
        print('  python3 <digital-twin>/scripts/build_twin.py --scene <city|factory|port> --config <配置> --out 大屏.html')
        print('  python3 <digital-twin>/scripts/verify_screen.py 大屏.html --shot check.png --expect-mode 写实三维')
    else:
        print('  在 visual-threejs-scene 的配置 JSON 顶层加 models 数组后跑 build_three_bundle.py')


if __name__ == "__main__":
    sys.exit(main())
