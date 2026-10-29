# -*- coding: utf-8 -*-
"""架构图 HTML → 2× 高清 PNG 导出器

用法：
    python export_png.py 输入.html [输出.png] [--width 1860] [--scale 2] [--wait 1200]

设计要点：
  - channel='chrome'：本机 Chromium 常缺中文字体，Chrome 渲染最稳；失败自动回落 chromium
  - viewport.width=1860：= 1740 画布 + 左右 padding，保证不横向截断
  - device_scale_factor=2：得 3720px 宽，印刷/Word 缩放后仍清晰
  - full_page=True：整页截图，不受视口高度限制
  - 等 document.fonts.ready：否则可能截到 fallback 字体
退出码：0 成功 / 1 失败。console 报错会打印出来但不影响退出码。
"""
import argparse
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('html')
    ap.add_argument('png', nargs='?')
    ap.add_argument('--width', type=int, default=1860, help='视口宽（默认 1860 = 1740 画布 + padding）')
    ap.add_argument('--scale', type=float, default=2.0, help='导出倍率（默认 2）')
    ap.add_argument('--wait', type=int, default=1200, help='额外等待毫秒（默认 1200）')
    args = ap.parse_args()

    html = Path(args.html).resolve()
    if not html.exists():
        print('✗ 找不到输入文件:', html)
        return 1
    png = Path(args.png).resolve() if args.png else html.with_suffix('.png')

    old_size = None
    if png.exists():
        try:
            from PIL import Image
            old_size = Image.open(png).size
        except Exception:
            pass

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print('✗ 缺少 playwright：pip install playwright && playwright install chrome')
        return 1

    errs = []
    with sync_playwright() as pw:
        browser = None
        for channel in ('chrome', None):          # 优先真实 Chrome，失败回落 Chromium
            try:
                browser = pw.chromium.launch(channel=channel) if channel else pw.chromium.launch()
                break
            except Exception as e:
                print('  · 启动 %s 失败（%s），尝试下一个' % (channel or 'chromium', type(e).__name__))
        if browser is None:
            print('✗ 无法启动浏览器，请执行 playwright install chrome')
            return 1

        page = browser.new_page(
            viewport={'width': args.width, 'height': 1200},
            device_scale_factor=args.scale,
        )
        page.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
        page.goto(html.as_uri())
        try:
            page.evaluate('() => document.fonts.ready')
        except Exception:
            pass
        page.wait_for_timeout(args.wait)
        page.screenshot(path=str(png), full_page=True)
        browser.close()

    # ---- 校验输出 ----
    print('console errors:', errs if errs else '[]  （空 = 正常）')
    try:
        from PIL import Image
        w, h = Image.open(png).size
        print('导出:', png.name, '→', (w, h))
        if old_size:
            if tuple(old_size) == (w, h):
                print('尺寸与旧图一致 → 下游（Word 内嵌图 extent）无需改动')
            else:
                print('⚠️ 尺寸已变化: %s → %s' % (tuple(old_size), (w, h)))
                print('   若该图已嵌入 Word，必须同步改 wp:extent 与 a:ext 两处的 cy（见 skill docx-batch-revise）')
        print('画布高度随文字行数变化；改动文案后请目视抽查改动区域。')
    except ImportError:
        print('（未安装 Pillow，跳过尺寸校验）')

    return 0


if __name__ == '__main__':
    sys.exit(main())
