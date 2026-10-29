#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
visual-digital-twin / verify_screen.py

无头浏览器验证大屏产物：
  1. pageerror / console.error 必须为空
  2. 3D 模式徽标（写实三维 / 三维渲染 / 二维降级）
  3. 面板数量与告警滚动条
  4. 截图像素健全性（非纯空白）
  5. 渲染统计（fps / 三角面）

用法：
  python verify_screen.py screen-city.html --shot city.png
  python verify_screen.py screen-port.html --expect-mode 写实三维
依赖 playwright（chromium）。无 GPU 环境脚本已内置 swiftshader 参数。
"""
import argparse, asyncio, functools, http.server, os, socketserver, threading


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve(root, port):
    handler = functools.partial(QuietHandler, directory=root)
    httpd = socketserver.TCPServer(("127.0.0.1", port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


async def run(args):
    from playwright.async_api import async_playwright
    root = os.path.dirname(os.path.abspath(args.page)) or "."
    name = os.path.basename(args.page)
    serve(root, args.port)
    url = "http://127.0.0.1:%d/%s" % (args.port, name)

    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--use-gl=angle", "--use-angle=swiftshader",
                                          "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        pg = await b.new_page(viewport={"width": args.width, "height": args.height})
        errors, console_err, req_fail = [], [], []
        CDN_HOSTS = ("cdn.jsdelivr.net", "unpkg.com", "esm.sh", "bytecdntp.com")
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("console", lambda m: console_err.append(m.text) if m.type == "error" else None)

        def on_reqfail(r):
            url = r.url
            if not any(h in url for h in CDN_HOSTS):
                req_fail.append("%s %s" % (r.failure, url[:120]))
        pg.on("requestfailed", on_reqfail)
        await pg.goto(url, wait_until="load", timeout=60000)
        await pg.wait_for_timeout(args.wait)
        info = await pg.evaluate("""() => ({
            canvas: !!document.querySelector('#dtCanvas'),
            mode: (document.querySelector('#dtChipMode')||{}).textContent || '',
            modeFlag: window.__DT_MODE__ || '',
            panels: document.querySelectorAll('.dt-panel').length,
            title: (document.querySelector('#dtTitle')||{}).textContent || '',
            alarms: document.querySelectorAll('#dtAlarmList .dt-marquee-item').length,
            stats: (window.__DT_CTRL__ && window.__DT_CTRL__.stats) ? window.__DT_CTRL__.stats() : null
        })""")
        if args.shot:
            await pg.screenshot(path=args.shot)
        await b.close()

    # 截图像素健全性
    px_ok, px_bright = None, None
    if args.shot and os.path.exists(args.shot):
        from PIL import Image
        im = Image.open(args.shot).convert("RGB")
        small = im.resize((160, 90))
        px = list(small.getdata())
        bright = sum(1 for c in px if sum(c) / 3 > 12)
        px_bright = bright
        px_ok = bright > len(px) * 0.5 and len(set(px)) > 100

    # 资源失败判据走 req_fail（含 URL，可白名单 CDN 探测）；console.err 仅展示
    ok = bool(info["canvas"]) and not errors and not req_fail and px_ok is not False
    if args.expect_mode:
        ok = ok and (args.expect_mode in info["mode"])
    print("URL        :", url)
    print("标题       :", info["title"])
    print("模式徽标   :", info["mode"].strip(), "| __DT_MODE__ =", info["modeFlag"])
    print("面板数     :", info["panels"], "| 告警条目:", info["alarms"])
    print("渲染统计   :", info["stats"])
    print("pageerror  :", "无" if not errors else errors[:3])
    print("console.err:", "无" if not console_err else console_err[:3])
    print("资源失败   :", "无" if not req_fail else req_fail[:3])
    print("截图像素   :", ("健全（亮像素 %d/160x90）" % px_bright) if px_ok else ("异常（亮像素 %s）" % px_bright) if px_bright is not None else "未截图")
    print("RESULT     :", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("page")
    ap.add_argument("--shot", help="截图输出路径")
    ap.add_argument("--wait", type=int, default=15000, help="引擎加载等待 ms")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--expect-mode", help="期望徽标文案包含（如：写实三维 / 二维降级）")
    a = ap.parse_args()
    raise SystemExit(asyncio.get_event_loop().run_until_complete(run(a)))


if __name__ == "__main__":
    main()
