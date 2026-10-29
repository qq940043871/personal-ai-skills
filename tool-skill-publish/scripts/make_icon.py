# -*- coding: utf-8 -*-
"""SVG 图标 → 512×512 PNG（Chrome 4× 超采样 + LANCZOS 降采样）

用法：
    python make_icon.py <输入.svg> <输出.png> [目标尺寸=512] [超采样倍率=4]

为什么必须超采样：直接渲 512 会让 1px 描边与 3px 圆角落在像素边界上，产生锯齿。
本机无 cairosvg / svglib，走 Playwright + 真实 Chrome。
（注意：Playwright 只装在 anaconda python，必须用 C:\\Users\\qq940\\anaconda3\\python.exe 跑）
"""
import io
import os
import re
import sys
import tempfile

from PIL import Image


def render_svg(svg_path, render_px):
    """把 SVG 渲成 render_px × render_px 的 RGBA PNG 字节流"""
    src = io.open(svg_path, encoding="utf-8").read()
    # 把根标签的 width/height 换成渲染尺寸，viewBox 保持原始整数坐标不动
    src = re.sub(r'(<svg\b[^>]*?)\swidth="[^"]*"', r'\1', src, count=1)
    src = re.sub(r'(<svg\b[^>]*?)\sheight="[^"]*"', r'\1', src, count=1)
    if re.search(r'<svg\b[^>]*?\sviewBox=', src):
        src = src.replace("<svg ", '<svg width="%d" height="%d" ' % (render_px, render_px), 1)
    else:
        raise SystemExit("SVG 缺少 viewBox，无法等比缩放")

    html = (
        '<!doctype html><html><head><meta charset="utf-8"><style>'
        'html,body{margin:0;padding:0;background:transparent;overflow:hidden}'
        'svg{display:block}'
        '</style></head><body>' + src + '</body></html>'
    )

    from playwright.sync_api import sync_playwright

    tmp_html = os.path.join(tempfile.mkdtemp(prefix="icon_"), "icon.html")
    io.open(tmp_html, "w", encoding="utf-8", newline="").write(html)
    out = os.path.join(os.path.dirname(tmp_html), "render.png")

    with sync_playwright() as pw:
        browser = None
        for channel in ("chrome", None):
            try:
                browser = pw.chromium.launch(
                    channel=channel,
                    args=["--default-background-color=00000000"],
                ) if channel else pw.chromium.launch(
                    args=["--default-background-color=00000000"])
                break
            except Exception as e:
                print("  · 启动 %s 失败（%s），尝试下一个" % (channel or "chromium", type(e).__name__))
        if browser is None:
            raise SystemExit("✗ 无法启动浏览器，请执行 playwright install chrome")
        page = browser.new_page(viewport={"width": render_px, "height": render_px},
                                device_scale_factor=1)
        page.goto("file:///" + tmp_html.replace(os.sep, "/"))
        page.wait_for_timeout(400)
        page.screenshot(path=out, omit_background=True)
        browser.close()
    return out


def verify(im, target):
    """硬核验：尺寸 / 四角透明 / 中心不透明"""
    fails = []
    if im.size != (target, target):
        fails.append("尺寸 %s ≠ (%d, %d)" % (im.size, target, target))
    if im.mode != "RGBA":
        im = im.convert("RGBA")
    w, h = im.size
    corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
    bad = [(p, im.getpixel(p)) for p in corners if im.getpixel(p)[3] != 0]
    if bad:
        fails.append("四角不透明：%s" % bad)
    c = im.getpixel((w // 2, h // 2))
    if c[3] != 255:
        fails.append("中心 alpha=%d（应为 255）" % c[3])
    return fails


def contact_sheet(im, path):
    """多尺寸核验图：深浅底对照，确认 32px 下仍可辨"""
    sizes = [512, 256, 128, 96, 64, 48, 32]
    pad = 16
    total_w = sum(sizes) + pad * (len(sizes) + 1)
    cell_h = max(sizes) + pad * 2
    sheet = Image.new("RGBA", (total_w, cell_h * 2), (255, 255, 255, 255))
    x = pad
    for i, s in enumerate(sizes):
        t = im.resize((s, s), Image.LANCZOS)
        sheet.paste(t, (x, pad + (max(sizes) - s) // 2), t)
        sheet.paste(t, (x, cell_h + pad + (max(sizes) - s) // 2), t)
        x += s + pad
    # 下半部分铺深色底，检验亮色图形在深色列表里是否还能看清
    dark = Image.new("RGBA", (total_w, cell_h), (24, 26, 34, 255))
    sheet.paste(dark, (0, cell_h))
    x = pad
    for s in sizes:
        t = im.resize((s, s), Image.LANCZOS)
        sheet.paste(t, (x, cell_h + pad + (max(sizes) - s) // 2), t)
        x += s + pad
    sheet.convert("RGB").save(path)
    return path


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    svg, out = sys.argv[1], sys.argv[2]
    target = int(sys.argv[3]) if len(sys.argv) > 3 else 512
    ss = int(sys.argv[4]) if len(sys.argv) > 4 else 4

    render_px = target * ss
    print("渲染 %s → %dpx（%d× 超采样）" % (os.path.basename(svg), render_px, ss))
    tmp_png = render_svg(svg, render_px)

    im = Image.open(tmp_png).convert("RGBA")
    print("  原始渲染尺寸:", im.size)
    if im.size != (render_px, render_px):
        print("  ! 渲染尺寸与预期不符，按实际尺寸等比缩放")
    im = im.resize((target, target), Image.LANCZOS)
    im.save(out)
    print("  降采样输出:", out, im.size, im.mode)

    fails = verify(im, target)
    if fails:
        print("✗ 核验失败:")
        for f in fails:
            print("   -", f)
        return 1
    print("✓ 核验通过: 尺寸 %s / 模式 %s / 四角 alpha=0 / 中心 alpha=255" % (im.size, im.mode))

    base = os.path.splitext(out)[0]
    sheet = contact_sheet(im, base + "_sizes.png")
    print("✓ 多尺寸核验图:", sheet)
    return 0


if __name__ == "__main__":
    sys.exit(main())
