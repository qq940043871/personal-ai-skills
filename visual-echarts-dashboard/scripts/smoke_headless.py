#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
visual-echarts-dashboard / smoke_headless.py

无头浏览器冒烟：把大屏跑起来，检查 pageerror / console error / 面板数 / 图表 canvas，
可选模拟一次刷新与新告警，最后截图。**交付前必跑。**

用法：
  python smoke_headless.py ./dash.html
  python smoke_headless.py ./dash.html --shot ./preview.png --size 1920x1080
  python smoke_headless.py ./dash.html --size 3840x2160 --expect-panels 9

依赖：pip install playwright && playwright install chromium
"""
import argparse, asyncio, functools, http.server, os, re, socketserver, sys, threading


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve(root, port):
    handler = functools.partial(Quiet, directory=root)
    httpd = socketserver.TCPServer(("127.0.0.1", port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()


async def run(args):
    from playwright.async_api import async_playwright
    root = os.path.dirname(os.path.abspath(args.page)) or "."
    name = os.path.basename(args.page)
    serve(root, args.port)
    url = "http://127.0.0.1:%d/%s" % (args.port, name)
    w, h = [int(x) for x in args.size.lower().replace("*", "x").split("x")]

    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--use-gl=angle", "--use-angle=swiftshader",
                                         "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        pg = await b.new_page(viewport={"width": w, "height": h})
        errors, cerr = [], []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("console", lambda m: cerr.append(m.text) if m.type == "error" else None)
        await pg.goto(url, wait_until="load", timeout=60000)
        await pg.wait_for_timeout(args.wait)
        info = await pg.evaluate("""() => {
            const s = document.getElementById('screen');
            return {
              title: (document.getElementById('hd-title') || {}).textContent,
              panels: document.querySelectorAll('.panel').length,
              canvases: document.querySelectorAll('.chart canvas').length,
              kpis: document.querySelectorAll('.kpi').length,
              alarms: document.querySelectorAll('.alarm').length,
              rows: document.querySelectorAll('.tbl tbody tr').length,
              ticker: document.querySelectorAll('#tk-track span').length,
              scale: s ? s.style.transform : '',
              overflowX: document.documentElement.scrollWidth - window.innerWidth,
              overflowY: document.documentElement.scrollHeight - window.innerHeight
            };
        }""")
        # 刷新链路：走一遍 Mock tick + 新告警
        await pg.evaluate("() => { window.dash && window.dash.tick(); window.dash && window.dash.push(); }")
        await pg.wait_for_timeout(1000)
        after = await pg.evaluate("() => (document.querySelector('.alarm .tx') || {}).textContent")
        echarts_ok = await pg.evaluate("() => typeof window.echarts !== 'undefined'")
        if args.shot:
            await pg.screenshot(path=args.shot)
        await b.close()

    # 网络资源失败（CDN 抽风等）若已被兜底恢复（echarts 仍在、无 pageerror），降级为警告不算失败
    net_pat = re.compile(r"Failed to load resource|net::ERR", re.I)
    net_errs = [e for e in cerr if net_pat.search(e)]
    hard_errs = [e for e in cerr if not net_pat.search(e)]
    ok = (not errors) and (not hard_errs) and info["canvases"] > 0 and echarts_ok
    if args.expect_panels is not None and info["panels"] != args.expect_panels:
        ok = False
    print("URL        :", url)
    print("视口       :", "%dx%d" % (w, h), "| 缩放:", info["scale"])
    print("标题       :", info["title"])
    print("面板/图表  : %s / %s（可见 canvas）" % (info["panels"], info["canvases"]))
    print("KPI/告警/明细/播报: %s / %s / %s / %s" % (info["kpis"], info["alarms"], info["rows"], info["ticker"]))
    print("溢出       : X=%s Y=%s（都应为 0）" % (info["overflowX"], info["overflowY"]))
    print("刷新后首条告警:", after)
    print("pageerror  :", errors[:5] if errors else "无")
    print("console.err:", hard_errs[:5] if hard_errs else "无")
    if net_errs:
        print("网络警告   :", net_errs[:2], "（已由 CDN 兜底恢复则不影响判定）" if echarts_ok else "（兜底也未恢复！）")
    if args.shot:
        print("截图       :", os.path.abspath(args.shot))
    print("RESULT     :", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description="数据大屏无头冒烟")
    ap.add_argument("page", help="待测 HTML 路径")
    ap.add_argument("--shot", default=None, help="截图输出路径")
    ap.add_argument("--size", default="1920x1080", help="浏览器视口，如 1920x1080 / 3840x2160")
    ap.add_argument("--wait", type=int, default=6000, help="加载后等待毫秒（等 CDN 与首帧）")
    ap.add_argument("--expect-panels", type=int, default=None, help="期望面板数，用于校验布局配置是否生效")
    ap.add_argument("--port", type=int, default=8126)
    args = ap.parse_args()
    if not os.path.exists(args.page):
        sys.exit("找不到页面：%s" % args.page)
    try:
        sys.exit(asyncio.run(run(args)))
    except ImportError:
        sys.exit("缺少 playwright：pip install playwright && playwright install chromium")
    except Exception as e:
        sys.exit("冒烟失败：%r" % e)


if __name__ == "__main__":
    main()
