#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
visual-digital-sandbox / build_sandbox.py

把一份配置 JSON 编译成**自包含单文件 HTML 沙盘**：骨架内联、配置注入、
占位符全替换。产出物双击即开（three 走 CDN 三源回退，失败自动降级等距二维）。

用法：
  python build_sandbox.py --scene park --out ./沙盘.html
  python build_sandbox.py --scene plant --config my.json --out ./厂区沙盘.html
  python build_sandbox.py --scene park --config my.json --strict --out out.html
  python build_sandbox.py --list

退出码：0 构建成功（--strict 时无告警）；1 校验失败；2 输入错误。
"""
import argparse
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = os.path.join(ROOT, "assets", "sandbox-skeleton.html")
CFG_DIR = os.path.join(ROOT, "templates", "config")

POINT_TYPES = {"tower", "plant", "warehouse", "block", "tree", "alarm"}
LINE_TYPES = {"road", "pipe", "vehicle"}
KNOWN_TYPES = POINT_TYPES | LINE_TYPES | {"zone"}

PLACEHOLDERS = ("__SANDBOX_CONFIG__", "__TITLE__", "__SUBTITLE__", "__BADGE__")


# ── 配置装载 ────────────────────────────────────────────────
def read_json(path):
    with io.open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def scenes():
    if not os.path.isdir(CFG_DIR):
        return []
    return sorted(n[:-5] for n in os.listdir(CFG_DIR) if n.endswith(".json"))


def deep_merge(base, over):
    """dict 递归合并，list 整体替换（图层/实体顺序是作者意图，不该被拼接）。"""
    if not isinstance(base, dict) or not isinstance(over, dict):
        return over
    out = dict(base)
    for k, v in over.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


# ── 校验：沙盘最常见的错是坐标写到台面外面去 ────────────────
def validate(cfg):
    errors, warns = [], []
    base = cfg.get("base") or {}
    size = base.get("size") or [420, 22, 320]
    try:
        hw, hd = float(size[0]) / 2.0, float(size[2]) / 2.0
    except (TypeError, ValueError, IndexError):
        errors.append("base.size 必须是 [宽, 厚, 深] 三个数字")
        hw, hd = 210.0, 160.0

    layers = cfg.get("layers")
    if not isinstance(layers, list) or not layers:
        errors.append("layers 缺失或为空：沙盘至少要有一个图层")
        return errors, warns

    seen_layer, seen_ent = set(), set()
    total = 0
    for li, layer in enumerate(layers):
        if not isinstance(layer, dict):
            errors.append("layers[%d] 不是对象" % li)
            continue
        lid = layer.get("id")
        if not lid:
            errors.append("layers[%d] 缺少 id" % li)
            lid = "layer%d" % li
        if lid in seen_layer:
            errors.append("图层 id 重复：%s" % lid)
        seen_layer.add(lid)

        ents = layer.get("entities")
        if ents is None:
            warns.append("图层 %s 没有 entities（会渲染成空图层）" % lid)
            continue
        if not isinstance(ents, list):
            errors.append("图层 %s 的 entities 不是数组" % lid)
            continue

        for ei, e in enumerate(ents):
            total += 1
            where = "%s[%d]" % (lid, ei)
            if not isinstance(e, dict):
                errors.append("%s 不是对象" % where)
                continue
            eid = e.get("id")
            if not eid:
                errors.append("%s 缺少 id（告警与拾取都靠它回挂）" % where)
            elif eid in seen_ent:
                errors.append("实体 id 重复：%s" % eid)
            else:
                seen_ent.add(eid)

            et = e.get("type")
            if et not in KNOWN_TYPES:
                errors.append("%s 未知构件类型 %r（可用：%s）"
                              % (where, et, ", ".join(sorted(KNOWN_TYPES))))
                continue

            if et in POINT_TYPES:
                pos = e.get("position")
                if not pos:
                    errors.append("%s 点实体缺少 position" % where)
                else:
                    try:
                        x, z = float(pos[0]), float(pos[2])
                        if abs(x) > hw or abs(z) > hd:
                            warns.append("%s 的 position 超出台面（x=%.0f/±%.0f, z=%.0f/±%.0f）"
                                         % (where, x, hw, z, hd))
                    except (TypeError, ValueError, IndexError):
                        errors.append("%s 的 position 必须是 [x,y,z]" % where)

            if et in LINE_TYPES:
                pts = e.get("path") if et == "vehicle" else e.get("points")
                if not pts or len(pts) < 2:
                    errors.append("%s 的 %s 至少需要 2 个点"
                                  % (where, "path" if et == "vehicle" else "points"))
                elif len(pts) == 2 and et != "vehicle":
                    warns.append("%s 只有 2 个点：曲线会退化成直线，建议给 3 个以上控制点" % where)
                else:
                    for p in pts:
                        try:
                            if abs(float(p[0])) > hw * 1.05 or abs(float(p[2])) > hd * 1.05:
                                warns.append("%s 的路径点超出台面边界，会被切在沙盘外" % where)
                                break
                        except (TypeError, ValueError, IndexError):
                            errors.append("%s 的路径点必须是 [x,y,z]" % where)
                            break

            if et == "zone":
                poly = e.get("polygon")
                if not poly or len(poly) < 3:
                    errors.append("%s 的 polygon 至少需要 3 个点" % where)
                else:
                    for p in poly:
                        try:
                            if abs(float(p[0])) > hw or abs(float(p[1])) > hd:
                                warns.append("%s 的地块顶点超出台面，会被裁掉" % where)
                                break
                        except (TypeError, ValueError, IndexError):
                            errors.append("%s 的 polygon 点必须是 [x,z]" % where)
                            break

    if total == 0:
        errors.append("所有图层都是空的：沙盘没东西可看")

    # 告警回挂
    for ai, a in enumerate(cfg.get("alarms") or []):
        eid = (a or {}).get("entityId")
        if eid and eid not in seen_ent:
            warns.append("alarms[%d] 指向不存在的实体 %s" % (ai, eid))

    # 时间轴
    tl = cfg.get("timeline") or {}
    if tl.get("enabled"):
        frames = tl.get("frames") or []
        if len(frames) < 2:
            warns.append("timeline 已启用但 frames 少于 2 帧，时间轴不会推进")
        dur = tl.get("durationSec")
        if not dur:
            warns.append("timeline 缺少 durationSec，默认按 30 秒")
        else:
            for fi, f in enumerate(frames):
                if (f or {}).get("t") is not None and float(f["t"]) > float(dur):
                    warns.append("timeline.frames[%d].t 超出 durationSec" % fi)

    return errors, warns


# ── 渲染 ────────────────────────────────────────────────────
def dump_config(cfg):
    """内联进 <script type="application/json">：必须挡住 </script> 与 <!-- 截断。"""
    s = json.dumps(cfg, ensure_ascii=False, separators=(",", ":"))
    s = s.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return s


def render(cfg, tpl_html):
    meta = cfg.get("meta") or {}
    html = tpl_html
    html = html.replace("__SANDBOX_CONFIG__", dump_config(cfg))
    html = html.replace("__TITLE__", str(meta.get("title") or "数字沙盘"))
    html = html.replace("__SUBTITLE__", str(meta.get("subtitle") or "DIGITAL SANDBOX"))
    html = html.replace("__BADGE__", str(meta.get("badge") or "沙盘"))

    left = [p for p in PLACEHOLDERS if p in html]
    if left:
        raise SystemExit("骨架里还有未替换的占位符：%s" % ", ".join(left))
    # 骨架里 __PART_* 分区必须都已被填掉（防止有人拿半成品骨架发布）
    parts = re.findall(r"//__PART_[A-Z]+__", html)
    if parts:
        raise SystemExit("骨架存在未实现的分区：%s" % ", ".join(sorted(set(parts))))
    return html


def stat(cfg):
    layers = cfg.get("layers") or []
    total = sum(len((l or {}).get("entities") or []) for l in layers)
    types = {}
    for l in layers:
        for e in (l or {}).get("entities") or []:
            t = (e or {}).get("type", "?")
            types[t] = types.get(t, 0) + 1
    return layers, total, types


def main():
    ap = argparse.ArgumentParser(description="数字沙盘单文件构建器")
    ap.add_argument("--scene", default="park", help="场景模板名（见 --list），默认 park")
    ap.add_argument("--config", default=None, help="自定义配置 JSON，与模板深度合并")
    ap.add_argument("--out", default=None, help="输出 HTML 路径")
    ap.add_argument("--title", default=None, help="覆盖标题")
    ap.add_argument("--subtitle", default=None, help="覆盖副标题")
    ap.add_argument("--badge", default=None, help="覆盖角标文案")
    ap.add_argument("--strict", action="store_true", help="有告警即视为失败")
    ap.add_argument("--list", action="store_true", help="列出内置场景模板")
    args = ap.parse_args()

    if args.list:
        for s in scenes():
            p = os.path.join(CFG_DIR, s + ".json")
            try:
                c = read_json(p)
                _, n, _ = stat(c)
                print("  %-8s %3d 个实体  %s" % (s, n, (c.get("meta") or {}).get("title", "")))
            except Exception as e:                                   # noqa: BLE001
                print("  %-8s 读取失败：%s" % (s, e))
        return 0

    tpl_path = TPL
    if not os.path.exists(tpl_path):
        sys.exit("找不到骨架：%s" % tpl_path)
    with io.open(tpl_path, "r", encoding="utf-8") as f:
        tpl = f.read()

    scene_file = os.path.join(CFG_DIR, args.scene + ".json")
    if not os.path.exists(scene_file):
        sys.exit("未知场景 %r，可用：%s" % (args.scene, ", ".join(scenes())))
    cfg = read_json(scene_file)

    if args.config:
        if not os.path.exists(args.config):
            sys.exit("找不到配置：%s" % args.config)
        cfg = deep_merge(cfg, read_json(args.config))

    meta = cfg.setdefault("meta", {})
    if args.title:
        meta["title"] = args.title
    if args.subtitle:
        meta["subtitle"] = args.subtitle
    if args.badge:
        meta["badge"] = args.badge

    errors, warns = validate(cfg)
    for w in warns:
        print("  [warn ] " + w)
    if errors:
        for e in errors:
            print("  [ERROR] " + e)
        print("RESULT     : FAIL（%d 处错误）" % len(errors))
        return 1
    if warns and args.strict:
        print("RESULT     : FAIL（--strict：%d 处告警）" % len(warns))
        return 1

    html = render(cfg, tpl)
    out = args.out or os.path.join(os.getcwd(), "sandbox-%s.html" % args.scene)
    out = os.path.abspath(out)
    d = os.path.dirname(out)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with io.open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)

    layers, total, types = stat(cfg)
    print("场景       :", args.scene, "|", (cfg.get("meta") or {}).get("title", ""))
    print("图层       :", len(layers), "个 ——", "，".join(
        "%s(%d)" % ((l or {}).get("label", (l or {}).get("id", "?")),
                    len((l or {}).get("entities") or [])) for l in layers))
    print("实体       :", total, "个 ——", "，".join("%s×%d" % (k, v) for k, v in sorted(types.items())))
    print("体积       : %.1f KB" % (os.path.getsize(out) / 1024.0))
    print("输出       :", out)
    print("RESULT     : PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
