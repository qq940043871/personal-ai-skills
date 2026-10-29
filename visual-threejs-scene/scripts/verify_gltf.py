#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""verify_gltf.py —— 外部 GLB 内联链路的端到端验证

三重判据（缺一不可）：
1. 红色像素：测试模型是纯红三角形，占位回退体是灰色系，截图做像素级红色检测
2. 零 draco 网络请求：route 阻断 **/draco/**，若 decoder 走了 CDN 必被抓包
3. 零 pageerror / console.error，且 DOM 资产数符合预期

用法：python verify_gltf.py ./gltf-test.html --expect-assets 24 --shot out.png
"""
import argparse, asyncio, os, sys, threading, functools, http.server, socketserver


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve(root, port):
    handler = functools.partial(QuietHandler, directory=root)
    httpd = socketserver.TCPServer(("127.0.0.1", port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def count_red(shot_path, step=2):
    from PIL import Image
    im = Image.open(shot_path).convert("RGB")
    w, h = im.size
    px = im.load()
    red = 0
    for y in range(0, h, step):
        for x in range(0, w, step):
            r, g, b = px[x, y]
            if r > 200 and g < 90 and b < 90:
                red += 1
    return red * step * step   # 折算回全图像素


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
        errors, console_err, draco_hits = [], [], []

        # 判据 2：阻断 draco CDN 并抓包——decoder 若走网络必现形
        await pg.route("**/draco/**", lambda route: (draco_hits.append(route.request.url),
                                                     route.abort()))
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("console", lambda m: console_err.append(m.text) if m.type == "error" else None)

        await pg.goto(url, wait_until="load", timeout=60000)
        await pg.wait_for_timeout(args.wait)
        info = await pg.evaluate("""() => ({
            canvas: !!document.querySelector('#stage canvas'),
            assets: document.querySelectorAll('#ui-devs .dev').length,
            dracoEmbedded: !!window.__TWIN_DRACO__,
            texEmbedded: !!window.__TWIN_TEX_URI__
        })""")
        if args.shot:
            await pg.screenshot(path=args.shot)
        await b.close()

    red_px = count_red(args.shot) if args.shot and os.path.exists(args.shot) else -1
    ok = (info["canvas"] and not errors and not console_err and not draco_hits
          and red_px >= args.min_red)
    if args.expect_assets is not None and info["assets"] != args.expect_assets:
        ok = False

    print("URL          :", url)
    print("canvas       :", info["canvas"])
    print("资产数       :", info["assets"], "（预期 %s）" % args.expect_assets)
    print("draco 内联   :", info["dracoEmbedded"], "| 贴图内联:", info["texEmbedded"])
    print("draco 网络请求:", draco_hits if draco_hits else "无（decoder 走内联）")
    print("红色像素     :", red_px, "（阈值 %d）" % args.min_red)
    print("pageerror    :", errors[:5] if errors else "无")
    print("console.err  :", console_err[:5] if console_err else "无")
    print("RESULT       :", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description="GLB 内联链路端到端验证")
    ap.add_argument("page")
    ap.add_argument("--shot", default=None)
    ap.add_argument("--wait", type=int, default=9000)
    ap.add_argument("--expect-assets", type=int, default=None)
    ap.add_argument("--min-red", type=int, default=300,
                    help="红色像素阈值（单个 10m 红三角在 1600x900 下实测约 400；占位场景必为 0）")
    ap.add_argument("--port", type=int, default=8137)
    ap.add_argument("--width", type=int, default=1600)
    ap.add_argument("--height", type=int, default=900)
    args = ap.parse_args()
    if not os.path.exists(args.page):
        sys.exit("找不到页面：%s" % args.page)
    sys.exit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()
