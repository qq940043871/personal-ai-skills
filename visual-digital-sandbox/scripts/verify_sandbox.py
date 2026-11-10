#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
visual-digital-sandbox / verify_sandbox.py

沙盘产物的交付前门禁：真跑一遍浏览器，验「加载 / 渲染 / 交互 / 画面」四件事。

  python verify_sandbox.py ./sandbox-park.html --shot ./preview.png
  python verify_sandbox.py ./s.html --expect-entities 22 --expect-layers 7 --strict-shot
  python verify_sandbox.py ./s.html --expect-mode 2d          # 无网/无 GPU 的降级态

依赖：pip install playwright pillow && playwright install chromium
无 GPU 环境必须带 swiftshader 参数（脚本已内置），否则会误报 WebGL 不可用。
退出码 0 = PASS。
"""
import argparse
import asyncio
import functools
import http.server
import os
import socketserver
import sys
import threading


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve(root, port):
    handler = functools.partial(QuietHandler, directory=root)
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("127.0.0.1", port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


CDN_HOSTS = ("unpkg.com", "cdn.jsdelivr.net", "cdn.staticfile.org")


def is_cdn_noise(text):
    return any(h in text for h in CDN_HOSTS)


PROBE = """() => {
  const sb = window.sandbox;
  const out = { ready: !!window.__SANDBOX_READY__, hasSandbox: !!sb };
  if (!sb) return out;
  out.mode = sb.mode();
  out.stats0 = sb.stats();
  out.canvas = !!document.querySelector('#stage canvas') || !!document.querySelector('#fb-canvas');
  out.layers = Object.keys(sb.state.layerMap || {});
  out.entIds = Object.keys(sb.state.entMap || {});
  out.dur = sb.state.dur;
  out.kpiCount = document.querySelectorAll('.kpi').length;
  out.rows = document.querySelectorAll('.layer').length;
  out.alarms = document.querySelectorAll('.al').length;
  out.presets = document.querySelectorAll('.pbtn').length;
  return out;
}"""

INTERACT = """() => {
  const sb = window.sandbox;
  const out = { errors: [] };
  try {
    const lid = Object.keys(sb.state.layerMap)[0];
    out.layerOff = sb.layer(lid, false);
    out.layerOn = sb.layer(lid, true);
    out.clipMid = sb.clip(0.5);
    out.clipOff = sb.clip(1);
    const ids = Object.keys(sb.state.entMap);
    if (ids.length) { sb.select(ids[0]); }
    out.selected = sb.state.selected;
    out.insOn = document.getElementById('ins-body').classList.contains('on');
    // 运行时更新（接实时数据的入口）：改状态 + 换指标
    if (ids.length && sb.update) {
      const origMetrics = sb.state.entMap[ids[0]].def.metrics;
      out.upd = sb.update(ids[0], { status: 'alarm', metrics: [{ label: '自检指标', value: '1', pct: 50 }] });
      out.updStatus = sb.state.entMap[ids[0]].def.status;
      out.updBack = sb.update(ids[0], { status: 'normal', metrics: origMetrics || [] });
    }
    out.preset = sb.preset(1);
    if (sb.state.dur) out.seek = sb.seek(sb.state.dur * 0.5);
    out.tagsOn = document.querySelectorAll('.sb-tag.on').length;
    out.stats1 = sb.stats();
  } catch (e) { out.errors.push(String(e && e.stack || e)); }
  return out;
}"""


def shot_health(path):
    """截图必须不是纯色/纯黑——WebGL 没画出东西时页面只剩底色。"""
    try:
        from PIL import Image
    except ImportError:
        return None, "未安装 Pillow，跳过画面健全检查"
    im = Image.open(path).convert("RGB")
    small = im.resize((160, 90))
    colors = small.getcolors(160 * 90) or []
    uniq = len(colors)
    px = list(small.getdata())
    avg = sum((r + g + b) for r, g, b in px) / (3.0 * len(px))
    ok = uniq >= 120 and avg >= 6
    return ok, "尺寸 %dx%d，唯一色 %d，平均亮度 %.1f" % (im.size[0], im.size[1], uniq, avg)


async def run(args):
    from playwright.async_api import async_playwright

    page_path = os.path.abspath(args.page)
    root = os.path.dirname(page_path) or "."
    name = os.path.basename(page_path)
    serve(root, args.port)
    url = "http://127.0.0.1:%d/%s" % (args.port, name)

    errors, console_err, req_fail = [], [], []
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=[
            "--use-gl=angle", "--use-angle=swiftshader",
            "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist",
        ])
        page = await browser.new_page(viewport={"width": args.width, "height": args.height})
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: console_err.append(m.text) if m.type == "error" else None)
        page.on("requestfailed", lambda r: req_fail.append(r.url) if not is_cdn_noise(r.url) else None)

        await page.goto(url, wait_until="load", timeout=60000)
        try:
            await page.wait_for_function("() => !!window.__SANDBOX_READY__", timeout=args.wait)
        except Exception:
            pass
        await page.wait_for_timeout(1200)
        probe = await page.evaluate(PROBE)

        interact = {"errors": ["未就绪，跳过交互"]}
        if probe.get("ready") and probe.get("hasSandbox") and not args.no_interact:
            interact = await page.evaluate(INTERACT)
            # 截图取全景机位：交互过程中切到近景，直接截会得到一张局部特写
            if args.shot:
                await page.evaluate("(i) => { try { window.sandbox.preset(i); } catch(e){} }",
                                    args.shot_preset)
            await page.wait_for_timeout(1800)          # 等机位补间与图层动画走完

        if args.shot:
            await page.screenshot(path=args.shot)
        await browser.close()

    fatal_console = [c for c in console_err
                     if not (c.startswith("Failed to load resource") and is_cdn_noise(c))]

    fails, warns = [], []
    if not probe.get("ready"):
        fails.append("沙盘未就绪：__SANDBOX_READY__ 未置位（three 拉取失败或脚本报错）")
    if not probe.get("canvas"):
        fails.append("找不到画布：#stage canvas 与 #fb-canvas 都不存在")
    if errors:
        fails.append("pageerror：%s" % errors[:3])
    if fatal_console:
        fails.append("console.error：%s" % fatal_console[:3])
    if req_fail:
        fails.append("资源加载失败：%s" % req_fail[:3])

    mode = probe.get("mode") or "unknown"
    expect_mode = args.expect_mode or "3d"
    if mode != expect_mode:
        (warns if expect_mode == "any" else fails).append(
            "渲染模式为 %r，期望 %r%s" % (mode, expect_mode,
                                       "（无网/无 GPU 时属预期，加 --expect-mode 2d）" if mode == "2d" else ""))

    stats = probe.get("stats0") or {}
    if stats.get("entities") is not None and args.expect_entities is not None \
            and stats["entities"] != args.expect_entities:
        fails.append("实体数 %d ≠ 期望 %d（配置没生效或被去重）"
                     % (stats["entities"], args.expect_entities))
    if args.expect_layers is not None and stats.get("layers") != args.expect_layers:
        fails.append("图层数 %s ≠ 期望 %d" % (stats.get("layers"), args.expect_layers))
    if mode == "3d":
        if (stats.get("triangles") or 0) <= 0:
            fails.append("三角面为 0：场景没渲染出来")
        if (stats.get("tags") or 0) <= 0:
            fails.append("场景标签为 0：标签投影没跑起来")
        if (stats.get("calls") or 0) <= 5:
            fails.append("draw call 过少（%s）：大概率只画了底座" % stats.get("calls"))

    if interact.get("errors"):
        fails.append("交互异常：%s" % interact["errors"][:2])
    else:
        if interact.get("layerOff") is not False:
            fails.append("图层关闭后状态仍为真：setLayer 无效")
        if interact.get("layerOn") is not True:
            fails.append("图层重新打开失败")
        if interact.get("insOn") is not True:
            fails.append("选中实体后详情卡未展开")
        if interact.get("preset") is not True:
            fails.append("机位预设切换失败")
        if interact.get("upd") is not None:
            if interact.get("upd") is not True:
                fails.append("sandbox.update 返回非预期值")
            if interact.get("updStatus") != "alarm":
                fails.append("sandbox.update 未能改变实体状态")

    shot_ok = None
    if args.shot:
        shot_ok, detail = shot_health(args.shot)
        if shot_ok is False:
            msg = "截图画面异常（%s）" % detail
            (fails if args.strict_shot else warns).append(msg)

    print("URL        :", url)
    print("就绪       :", probe.get("ready"))
    print("渲染模式   :", mode)
    if stats:
        print("图层/实体  : %s / %s" % (stats.get("layers"), stats.get("entities")))
        print("可拾取网格 :", stats.get("pickables"))
        print("场景标签   :", stats.get("tags"))
        print("绘制/三角面: %s / %s" % (stats.get("calls"), stats.get("triangles")))
    print("HUD        : KPI %s 组，图层 %s 行，告警 %s 条，机位 %s 个"
          % (probe.get("kpiCount"), probe.get("rows"), probe.get("alarms"), probe.get("presets")))
    if interact.get("stats1"):
        print("交互后三角 :", interact["stats1"].get("triangles"))
    print("pageerror  :", errors[:3] if errors else "无")
    print("console.err:", fatal_console[:3] if fatal_console else
          ("仅 CDN 噪声 %d 条（已忽略）" % len(console_err) if console_err else "无"))
    print("req.failed :", req_fail[:3] if req_fail else "无")
    if args.shot:
        print("截图       : %s（%s）" % (os.path.abspath(args.shot),
                                        "未检查" if shot_ok is None else ("健全" if shot_ok else "异常")))
    for w in warns:
        print("  [warn] " + w)
    for f in fails:
        print("  [FAIL] " + f)
    print("RESULT     :", "PASS" if not fails else "FAIL")
    return 0 if not fails else 1


def main():
    ap = argparse.ArgumentParser(description="数字沙盘无头验收")
    ap.add_argument("page", help="待测 HTML")
    ap.add_argument("--shot", default=None, help="截图输出路径")
    ap.add_argument("--shot-preset", type=int, default=0, help="截图前切到的机位序号（默认 0 = 全景）")
    ap.add_argument("--wait", type=int, default=25000, help="等待就绪的毫秒上限（含 CDN 回退重试）")
    ap.add_argument("--expect-mode", default="3d", choices=["3d", "2d", "any"],
                    help="期望渲染模式，无网环境用 2d")
    ap.add_argument("--expect-entities", type=int, default=None)
    ap.add_argument("--expect-layers", type=int, default=None)
    ap.add_argument("--strict-shot", action="store_true", help="画面异常也算失败")
    ap.add_argument("--no-interact", action="store_true", help="跳过交互冒烟")
    ap.add_argument("--port", type=int, default=8137)
    ap.add_argument("--width", type=int, default=1600)
    ap.add_argument("--height", type=int, default=900)
    args = ap.parse_args()
    if not os.path.exists(args.page):
        sys.exit("找不到页面：%s" % args.page)
    try:
        sys.exit(asyncio.run(run(args)))
    except ImportError as e:
        sys.exit("缺少依赖：%s（pip install playwright pillow && playwright install chromium）" % e)
    except Exception as e:                                            # noqa: BLE001
        sys.exit("验收失败：%r" % e)


if __name__ == "__main__":
    main()
