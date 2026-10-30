# -*- coding: utf-8 -*-
"""架构图 HTML → 2× 高清 PNG 导出器

用法：
    python export_png.py 输入.html                       # 输出 输入.png（同目录）
    python export_png.py 输入.html --out 成果图.png       # 指定输出文件
    python export_png.py a.html b.html --outdir out/      # 批量导出到目录
    python export_png.py 输入.html --width 1860 --scale 2 --wait 1200

输出路径规则（与 visual-diagram-suite 的 export_png.py 完全一致）：
  - 单文件 + --out     → 输出到 --out 指定的文件
  - 单文件无 --out     → 输出到输入文件同目录的同名 .png
  - 多文件 + --outdir  → 输出到该目录，文件名为 原名.png
  - 多文件无 --outdir  → 各自输出到自己所在目录
  - 多文件 + --out     → 报错（--out 只服务单文件）

为什么不用位置参数当输出名：
  argparse 里 `html nargs='+'` 后面再跟 `png nargs='?'` 时，贪婪匹配会把
  「输入.html 输出.png」里的 输出.png 当成第二个输入 HTML —— 位置参数 png
  永远拿不到值，是个死参数。故输出一律走 --out / --outdir。

设计要点：
  - channel='chrome'：本机 Chromium 常缺中文字体，Chrome 渲染最稳；失败自动回落 chromium
  - viewport.width=1860：= 1740 画布 + 左右 padding，保证不横向截断
  - device_scale_factor=2：得 3720px 宽，印刷/Word 缩放后仍清晰
  - full_page=True：整页截图，不受视口高度限制
  - 等 document.fonts.ready：否则可能截到 fallback 字体
退出码：0 全部成功 / 1 有失败。console 报错会打印出来但不影响退出码。
"""
import argparse
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description='架构图 HTML → 2× 高清 PNG')
    ap.add_argument('html', nargs='+', help='一个或多个输入 HTML')
    ap.add_argument('--out', help='输出 PNG 文件路径（仅单文件模式可用）')
    ap.add_argument('--outdir', help='批量输出目录（默认各输入文件同目录）')
    ap.add_argument('--width', type=int, default=1860, help='视口宽（默认 1860 = 1740 画布 + padding）')
    ap.add_argument('--scale', type=float, default=2.0, help='导出倍率（默认 2）')
    ap.add_argument('--wait', type=int, default=1200, help='额外等待毫秒（默认 1200）')
    args = ap.parse_args()

    # 先解决路径，别让浏览器白启动
    multi = len(args.html) > 1
    if multi and args.out:
        print('✗ --out 只用于单文件；批量导出请用 --outdir')
        return 1

    targets = []
    for h in args.html:
        hp = Path(h).resolve()
        if not hp.exists():
            print('✗ 找不到输入文件:', hp)
            return 1
        # 优先级：--out（显式文件）> --outdir（输出目录）> 输入同目录
        # 三个分支对单文件/批量一视同仁，避免「传了 --outdir 却静默输出到别处」
        if args.out:
            pp = Path(args.out).resolve()
        elif args.outdir:
            outdir = Path(args.outdir).resolve()
            outdir.mkdir(parents=True, exist_ok=True)
            pp = outdir / (hp.stem + '.png')
        else:
            pp = hp.with_suffix('.png')
        targets.append((hp, pp))
    # 同名输入去重，避免重复导出
    if multi and len({str(p) for _, p in targets}) != len(targets):
        print('✗ 批量模式下输出文件名冲突（两个输入同名），请用 --outdir 分开或改名')
        return 1

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

        failed = 0
        total = len(targets)
        for i, (hp, pp) in enumerate(targets, 1):
            old_size = None
            if pp.exists():
                try:
                    from PIL import Image
                    old_size = Image.open(pp).size
                except Exception:
                    pass

            del errs[:]
            page.goto(hp.as_uri())
            try:
                page.evaluate('() => document.fonts.ready')
            except Exception:
                pass
            page.wait_for_timeout(args.wait)
            page.screenshot(path=str(pp), full_page=True)

            tag = '[%d/%d] ' % (i, total) if total > 1 else ''
            print('%s%s' % (tag, hp.name))
            print('  console errors:', errs if errs else '[]  （空 = 正常）')
            try:
                from PIL import Image
                w, h = Image.open(pp).size
                print('  导出: %s → %s' % (pp.name, (w, h)))
                if old_size:
                    if tuple(old_size) == (w, h):
                        print('  尺寸与旧图一致 → 下游（Word 内嵌图 extent）无需改动')
                    else:
                        print('  ⚠️ 尺寸已变化: %s → %s' % (tuple(old_size), (w, h)))
                        print('     若该图已嵌入 Word，必须同步改 wp:extent 与 a:ext 两处的 cy')
            except ImportError:
                print('  （未安装 Pillow，跳过尺寸校验）')
        browser.close()

    if not multi:
        print('画布高度随文字行数变化；改动文案后请目视抽查改动区域。')
    else:
        print('完成：成功 %d / 失败 %d' % (len(targets) - failed, failed))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
