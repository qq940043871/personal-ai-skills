#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_twin.py — 数字孪生大屏单文件构建器（v2.0 写实引擎版）

把 assets 中的样式 / 运行时 / 场景模块与业务配置组装成一个独立 .html。
两种引擎：
  realistic（默认）— three r160 ES module 写实管线（物理天空/PBR/接触阴影/Draco GLB），
                      构建期把场景声明的贴图与模型内联为 data URI，运行时探测 CDN 并注入 importmap；
  classic          — v1 经典 UMD 科技风（assets/scenes-legacy/），行为与 v1.0.0 完全一致。
两者都保留 Canvas 2D 等距降级。

用法：
  python3 build_twin.py --scene city --out /workspace/city.html
  python3 build_twin.py --config ../templates/config/factory.json --out f.html
  python3 build_twin.py --scene port --offline --out port-offline.html
  python3 build_twin.py --scene city --engine classic --out city-v1-style.html
"""
import argparse
import base64
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CORE = os.path.join(ROOT, "assets", "core")
SCENES = os.path.join(ROOT, "assets", "scenes")
LEGACY = os.path.join(ROOT, "assets", "scenes-legacy")
FALLBACK = os.path.join(ROOT, "assets", "fallback")
IMG = os.path.join(ROOT, "assets", "img")
MODELS = os.path.join(ROOT, "assets", "models")
DRACO = os.path.join(ROOT, "assets", "draco")
TPL_CONFIG = os.path.join(ROOT, "templates", "config")

SCENE_ALIAS = {"city": "city", "城市": "city", "智慧城市": "city", "园区": "city", "楼宇": "city",
               "factory": "factory", "工厂": "factory", "产线": "factory", "车间": "factory",
               "port": "port", "港口": "port", "物流": "port", "枢纽": "port"}

MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
        ".glb": "application/octet-stream", ".js": "application/javascript",
        ".wasm": "application/wasm"}


def read(p):
    with open(p, "r", encoding="utf-8") as f:
        return f.read()


def data_uri(path):
    ext = os.path.splitext(path)[1].lower()
    mime = MIME.get(ext, "application/octet-stream")
    with open(path, "rb") as f:
        return "data:%s;base64,%s" % (mime, base64.b64encode(f.read()).decode("ascii"))


def load_config(scene, cfg_path, title=None, subtitle=None):
    if cfg_path:
        if not os.path.exists(cfg_path):
            sys.exit("配置文件不存在：%s" % cfg_path)
        cfg = json.loads(read(cfg_path))
    else:
        p = os.path.join(TPL_CONFIG, "%s.json" % scene)
        if not os.path.exists(p):
            sys.exit("未找到场景默认配置：%s" % p)
        cfg = json.loads(read(p))
    if title:
        cfg["title"] = title
    if subtitle:
        cfg["subtitle"] = subtitle
    return cfg


def scene_texture_names(scene_js):
    """从写实场景源码提取 textures: [...] 声明（贴图选择性内联的依据）"""
    m = re.search(r"textures:\s*\[([^\]]*)\]", scene_js)
    if not m:
        return None
    return [x.strip().strip("'\"") for x in m.group(1).split(",") if x.strip()]


def build_tex_json(scene_js):
    """场景声明贴图名 → {name: albedoURI, name-normal: URI, name-rough: URI}"""
    names = scene_texture_names(scene_js)
    tex = {}
    if names is None:  # 未声明 → 全量
        names = [f[4:-4] for f in os.listdir(IMG)
                 if f.startswith("tex-") and f.endswith(".jpg") and "-rough" not in f and "-normal" not in f]
    for n in names:
        for suffix, ext in [("", ".jpg"), ("-normal", ".png"), ("-rough", ".jpg")]:
            p = os.path.join(IMG, "tex-%s%s%s" % (n, suffix, ext))
            if os.path.exists(p):
                tex[n + suffix] = data_uri(p)
    return tex, names


def glb_uses_draco(path):
    """读 GLB JSON chunk，检查是否启用 KHR_draco_mesh_compression"""
    try:
        with open(path, "rb") as f:
            head = f.read(20)
            if head[:4] != b"glTF":
                return False
            jlen = struct.unpack("<I", head[12:16])[0]
            js = json.loads(f.read(jlen).decode("utf-8", "ignore"))
        exts = set(js.get("extensionsUsed") or [])
        if "KHR_draco_mesh_compression" in exts:
            return True
        for ext in js.get("extensionsRequired") or []:
            if "draco" in ext.lower():
                return True
    except Exception:
        pass
    return False


def build_models_json(cfg):
    """config.models[] → {url: dataURI}；返回 (dict, draco_json_str)"""
    out, need_draco = {}, False
    for m in cfg.get("models") or []:
        url = m.get("url") or ""
        if not url.startswith("models/"):
            continue  # http(s) 直链交给运行时
        p = os.path.join(MODELS, os.path.basename(url))
        if not os.path.exists(p):
            print("   ⚠️ 模型缺失：%s（运行时将回退占位体）" % p)
            continue
        size_mb = os.path.getsize(p) / 1048576.0
        if size_mb > 8:
            print("   ⚠️ 模型较大 %.1fMB：%s（单文件产物会显著膨胀）" % (size_mb, p))
        out[url] = data_uri(p)
        if glb_uses_draco(p):
            need_draco = True
    draco = "null"
    if need_draco:
        wp, sp = os.path.join(DRACO, "draco_wasm_wrapper.js"), os.path.join(DRACO, "draco_decoder.wasm")
        if os.path.exists(wp) and os.path.exists(sp):
            draco = json.dumps({"wrapper": data_uri(wp), "wasm": data_uri(sp)})
            print("   Draco 模型已内联 decoder（wrapper+wasm，离线可解压）")
        else:
            print("   ⚠️ 检测到 Draco 模型但 assets/draco/ 缺文件，运行时将无法解码")
    return out, draco


def build(scene, cfg_path, out, title=None, subtitle=None, offline=False, engine="realistic"):
    scene_dir = SCENES if engine == "realistic" else LEGACY
    scene_file = os.path.join(scene_dir, "%s.js" % scene)
    if not os.path.exists(scene_file):
        sys.exit("未找到场景模块：%s（engine=%s 可选：city / factory / port）" % (scene_file, engine))

    cfg = load_config(scene, cfg_path, title, subtitle)
    cfg.setdefault("scene", scene)
    cfg["engineMode"] = engine  # 运行时分派依据（写实源码在 text/plain 槽内，无法用全局变量探测）
    if offline:
        cfg["forceMode"] = "2d"
    cfg.setdefault("env", {})
    cfg["env"].setdefault("timeOfDay", "dusk" if scene == "port" else "day")

    scene_js = read(scene_file)

    if engine == "realistic":
        if offline:
            tex_json, models_json, draco_json = {}, {}, "null"  # 2D 降级用不到，省 2-3MB
            engine_js = scene_js + "\n\n/* ---- engine.js（写实内核，构建期拼接）---- */\n" + read(os.path.join(CORE, "engine.js")) + "\n"
            scene_classic_js = ""
            print("   离线 2D 模式：跳过贴图/模型内联")
        else:
            tex_json, tex_names = build_tex_json(scene_js)
            models_json, draco_json = build_models_json(cfg)
            engine_js = scene_js + "\n\n/* ---- engine.js（写实内核，构建期拼接）---- */\n" + read(os.path.join(CORE, "engine.js")) + "\n"
            scene_classic_js = ""
            size_tex = sum(len(v) for v in tex_json.values()) / 1048576.0
            print("   写实贴图内联 %d 组（%.1f MB）：%s" % (len(tex_names), size_tex, ", ".join(tex_names)))
    else:
        tex_json, models_json, draco_json = {}, {}, "null"
        engine_js = ""
        scene_classic_js = scene_js

    html = read(os.path.join(CORE, "shell.html"))
    parts = {
        "__LAYOUT_CSS__": read(os.path.join(CORE, "layout.css")),
        "__CHARTS_JS__": read(os.path.join(CORE, "charts.js")),
        "__HELPERS_JS__": read(os.path.join(CORE, "helpers.js")),
        "__SCENE_JS__": scene_classic_js,
        "__FALLBACK_JS__": read(os.path.join(FALLBACK, "iso2d.js")),
        "__RUNTIME_JS__": read(os.path.join(CORE, "runtime.js")),
        "__ENGINE_JS__": engine_js,
        "__TEX_JSON__": json.dumps(tex_json, ensure_ascii=False),
        "__MODELS_JSON__": json.dumps(models_json, ensure_ascii=False),
        "__DRACO_JSON__": draco_json,
        "__CONFIG_JSON__": json.dumps(cfg, ensure_ascii=False, indent=2),
    }
    for k, v in parts.items():
        html = html.replace(k, v)
    html = html.replace("__TITLE__", cfg.get("title", "数字孪生可视化平台"))

    # 自检：只检查构建期占位符（运行时全局变量名 __DT_*__ 需排除）
    expected = set(list(parts.keys()) + ["__TITLE__"])
    left = [x for x in set(re.findall(r"__[A-Z_]+__", html)) if x in expected]
    if left:
        sys.exit("构建失败：残留占位符 %s" % left)
    if html.count("<script") != html.count("</scr" + "ipt>"):
        sys.exit("构建失败：script 标签不平衡")

    d = os.path.dirname(os.path.abspath(out))
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)

    size = os.path.getsize(out) / 1024.0
    print("✅ 生成完成：%s" % os.path.abspath(out))
    print("   场景：%s | 引擎：%s | 模式：%s | 体积：%.1f KB" % (
        scene, engine,
        "离线 2D 降级" if offline else ("写实 3D + 2D 自动降级" if engine == "realistic" else "Three.js + 2D 自动降级"),
        size))
    return out


def main():
    ap = argparse.ArgumentParser(description="构建数字孪生可视化大屏单文件 HTML（v2 写实引擎）")
    ap.add_argument("--scene", default="city", help="city / factory / port（或中文本名）")
    ap.add_argument("--config", help="自定义业务配置 JSON 路径")
    ap.add_argument("--out", required=True, help="输出 HTML 路径")
    ap.add_argument("--title", help="覆盖大屏主标题")
    ap.add_argument("--subtitle", help="覆盖英文副标题")
    ap.add_argument("--offline", action="store_true", help="强制离线 2D 降级模式")
    ap.add_argument("--engine", default="realistic", choices=["realistic", "classic"],
                    help="realistic=写实管线（默认）；classic=v1 经典 UMD 科技风")
    a = ap.parse_args()

    scene = SCENE_ALIAS.get(a.scene, a.scene)
    build(scene, a.config, a.out, a.title, a.subtitle, a.offline, a.engine)


if __name__ == "__main__":
    main()
