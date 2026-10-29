#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
visual-threejs-scene / smoke_headless.py

无头浏览器冒烟：把原型页跑起来，检查 pageerror / console error / canvas / 资产数，
并可选截图。**这是交付前的最后一道门，别跳过。**

用法：
  python smoke_headless.py ./twin.html
  python smoke_headless.py ./twin.html --shot ./preview.png --wait 7000 --expect-assets 13

依赖：pip install playwright && playwright install chromium
无 GPU 环境必须带 swiftshader 参数（脚本已内置），否则会误报 WebGL 上下文创建失败。
"""
import argparse, asyncio, os, sys, threading, functools, http.server, socketserver


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):        # 静音访问日志，别污染校验输出
        pass


def serve(root, port):
    handler = functools.partial(QuietHandler, directory=root)
    httpd = socketserver.TCPServer(("127.0.0.1", port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


CDN_HOSTS = ("unpkg.com", "cdn.jsdelivr.net", "esm.sh")   # CDN 抖动属良性，不计 FAIL


def _is_cdn_noise(text):
    """console 资源加载失败 / 网络请求失败里，指向 CDN 域名的算良性噪声。"""
    return any(h in text for h in CDN_HOSTS)


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
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("console", lambda m: console_err.append(m.text) if m.type == "error" else None)
        pg.on("requestfailed", lambda r: req_fail.append(r.url) if not _is_cdn_noise(r.url) else None)
        await pg.goto(url, wait_until="load", timeout=60000)
        await pg.wait_for_timeout(args.wait)
        info = await pg.evaluate("""() => ({
            canvas: !!document.querySelector('#stage canvas'),
            assets: document.querySelectorAll('#ui-devs .dev').length,
            tags: document.querySelectorAll('.tag').length,
            perf: (document.getElementById('ui-perf') || {}).textContent || '',
            // v0.3：后处理链是否真的建起来了（软件渲染器上可能整体回退，属预期）
            postfx: (window.tw && window.tw.postfx) ? window.tw.postfx() : null,
            draws: (window.tw && window.tw.renderer) ? window.tw.renderer.info.render.calls : -1,
            tris:  (window.tw && window.tw.renderer) ? window.tw.renderer.info.render.triangles : -1
        })""")
        if args.shot:
            await pg.screenshot(path=args.shot)
        await b.close()

    fatal_console = [c for c in console_err
                     if not (c.startswith("Failed to load resource") and _is_cdn_noise(c))]
    ok = info["canvas"] and not errors and not fatal_console and not req_fail
    if args.expect_assets is not None and info["assets"] != args.expect_assets:
        ok = False
    print("URL        :", url)
    print("canvas     :", info["canvas"])
    print("资产数     :", info["assets"], "（预期 %s）" % args.expect_assets if args.expect_assets else "")
    print("场景标签数 :", info["tags"])
    print("渲染统计   :", info["perf"].strip())
    print("绘制/三角面:", "%d / %.0fk" % (info["draws"], info["tris"] / 1000.0))
    pf = info.get("postfx")
    if pf is None:
        print("后处理链   : 未暴露 tw.postfx（旧版本页面？）")
    elif pf.get("on"):
        print("后处理链   : 已启用  AO=%s Bloom=%s SMAA=%s" % (pf["ao"], pf["bloom"], pf["smaa"]))
    else:
        print("后处理链   : 未启用（软件渲染器回退 / postfx:false 均可导致，非缺陷）")
    print("pageerror  :", errors[:5] if errors else "无")
    print("console.err:", fatal_console[:5] if fatal_console else
          ("仅 CDN 噪声 %d 条（已忽略）" % len(console_err) if console_err else "无"))
    print("req.failed :", req_fail[:3] if req_fail else "无")
    if args.shot:
        print("截图       :", os.path.abspath(args.shot))
    print("RESULT     :", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description="数字孪生原型无头冒烟")
    ap.add_argument("page", help="待测 HTML 路径（相对或绝对）")
    ap.add_argument("--shot", default=None, help="截图输出路径")
    ap.add_argument("--wait", type=int, default=7000, help="加载后等待毫秒（等 CDN 与首帧）")
    ap.add_argument("--expect-assets", type=int, default=None, help="期望资产数（建筑+设备），用于校验配置是否真的生效")
    ap.add_argument("--port", type=int, default=8123)
    ap.add_argument("--width", type=int, default=1600)
    ap.add_argument("--height", type=int, default=900)
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
