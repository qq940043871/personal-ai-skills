# -*- coding: utf-8 -*-
"""架构图工具箱 · 通用 HTML → 2× 高清 PNG 导出器

用法：
    python export_png.py 输入.html [输出.png] [--width 1860] [--scale 2] [--wait 900]
    python export_png.py a.html b.html c.html --outdir ./png     # 批量导出
    python export_png.py 输入.html --strict                       # 连线数对不上即失败退出

设计要点（多图型通用，五张骨架全部适配）：
  - channel='chrome'：本机 Chromium 常缺中文字体，Chrome 渲染最稳；失败自动回落 chromium
  - 等「就绪标记」：骨架脚本画完连线的标志，不等就会截到「只有卡片没有线」的图
        · 本工具箱骨架（时序 / 组件 / 部署 / 状态机）→ window.__DIAGRAM_READY__
        · 管道流程图骨架 → 同时置 __DIAGRAM_READY__ 与旧名 __PIPE_READY__，两者通用
  - 读连线统计：优先 window.__DIAGRAM_STATS__，读不到则从 DOM 现场统计（兼容旧文件）
        核对 edges（声明）vs drawn（实际绘制）—— 少画一条线的图**照样能看**，
        肉眼极难发现，这是本类图最容易埋的雷
  - device_scale_factor=2：印刷 / Word 缩放后仍清晰
  - 比对新旧尺寸：尺寸变了则提示 Word 内嵌图的 extent 联动（见 skill docx-batch-revise）
退出码：0 成功 / 1 失败 / 2 连通线数都对不上（仅 --strict）
"""
import argparse
import sys
from pathlib import Path


def export_one(html, png, width, scale, wait, strict):
    """导出单张图。返回 (ok, size_or_None, msg)"""
    from playwright.sync_api import sync_playwright

    old_size = None
    if png.exists():
        try:
            from PIL import Image
            old_size = Image.open(png).size
        except Exception:
            pass

    errs = []
    stats = None
    with sync_playwright() as pw:
        browser = None
        for channel in ('chrome', None):
            try:
                browser = pw.chromium.launch(channel=channel) if channel else pw.chromium.launch()
                break
            except Exception as e:
                print('  · 启动 %s 失败（%s），尝试下一个' % (channel or 'chromium', type(e).__name__))
        if browser is None:
            return False, None, '无法启动浏览器，请执行 playwright install chrome'

        page = browser.new_page(
            viewport={'width': width, 'height': 1200},
            device_scale_factor=scale,
        )
        page.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
        page.goto(Path(html).resolve().as_uri())
        try:
            page.evaluate('() => document.fonts.ready')
        except Exception:
            pass
        # 等骨架脚本画完连线（最多 5s），再补一个短等待让过渡结束
        try:
            page.wait_for_function(
                '() => window.__DIAGRAM_READY__ === true || window.__PIPE_READY__ === true',
                timeout=5000)
        except Exception:
            print('  · 未等到就绪标记（骨架脚本可能报错，稍后看 console errors）')
        page.wait_for_timeout(wait)
        # 视口高必须贴合内容高。
        # full_page 截的是 max(视口高, 内容高) —— 视口写死 1200 而图只有 600 高时，
        # 下方会截出一大片 canvas 底色空白（实测占掉整图一大半）。
        # 注意不能用 scrollHeight 来量：它至少等于视口高，量不出真实内容高。
        content_h = page.evaluate('() => Math.ceil(document.body.getBoundingClientRect().height)')
        if content_h and content_h > 0:
            page.set_viewport_size({'width': width, 'height': max(content_h, 120)})
            page.wait_for_timeout(180)   # resize 可能触发骨架重绘连线
        stats = page.evaluate('''() => {
            if (window.__DIAGRAM_STATS__) return window.__DIAGRAM_STATS__;
            // 兼容旧版管道流程图骨架（只有 __PIPE_* 标记）
            const g = document.querySelector('#egrp') || document.querySelector('#paths');
            if (!g) return null;
            return {
                type: 'pipeline(legacy)',
                nodes: document.querySelectorAll('[data-node]').length,
                edges: window.__PIPE_EDGES__ != null ? window.__PIPE_EDGES__ : null,
                drawn: g.querySelectorAll('path').length
            };
        }''')
        page.screenshot(path=str(png), full_page=True)
        browser.close()

    bad = False
    print('  console errors:', errs if errs else '[]  （空 = 正常）')
    if stats:
        n, m, k = stats.get('nodes'), stats.get('edges'), stats.get('drawn')
        flag = '' if (m is None or k is None or m == k) else '  ← 对不上！检查 id 拼写'
        print('  图形类型: %s · 节点 %s · 声明连线 %s · 实际绘制 %s%s'
              % (stats.get('type'), n, m, k, flag))
        if m is not None and k is not None and m != k:
            bad = True
    else:
        print('  未读到连线统计（无连线画布，或骨架脚本未执行）')

    try:
        from PIL import Image
        w, h = Image.open(png).size
        print('  导出:', png.name, '→', (w, h))
        if old_size:
            if tuple(old_size) == (w, h):
                print('  尺寸与旧图一致 → 下游（Word 内嵌图 extent）无需改动')
            else:
                print('  ⚠️ 尺寸已变化: %s → %s' % (tuple(old_size), (w, h)))
                print('     若该图已嵌入 Word，必须同步改 wp:extent 与 a:ext 两处的 cy'
                      '（见 skill docx-batch-revise）')
    except ImportError:
        print('  （未安装 Pillow，跳过尺寸校验）')

    if bad and strict:
        return False, None, '连线数与声明不一致（--strict）'
    return True, None, 'ok'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('html', nargs='+', help='一个或多个输入 HTML')
    ap.add_argument('png', nargs='?', help='输出 PNG（单文件时可用）')
    ap.add_argument('--outdir', help='批量模式输出目录')
    ap.add_argument('--width', type=int, default=1860, help='视口宽（默认 1860 = 1740 画布 + padding）')
    ap.add_argument('--scale', type=float, default=2.0, help='导出倍率（默认 2）')
    ap.add_argument('--wait', type=int, default=900, help='额外等待毫秒（默认 900）')
    ap.add_argument('--strict', action='store_true', help='连线数对不上时以失败退出')
    args = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        print('✗ 缺少 playwright：pip install playwright && playwright install chrome')
        return 1

    batch = len(args.html) > 1 or args.outdir
    failed = 0
    for i, h in enumerate(args.html, 1):
        hp = Path(h).resolve()
        if not hp.exists():
            print('✗ 找不到输入文件:', hp)
            failed += 1
            continue
        if batch:
            outdir = Path(args.outdir).resolve() if args.outdir else hp.parent
            outdir.mkdir(parents=True, exist_ok=True)
            pp = outdir / (hp.stem + '.png')
        else:
            pp = Path(args.png).resolve() if args.png else hp.with_suffix('.png')

        print('[%d/%d] %s' % (i, len(args.html), hp.name))
        ok, _, msg = export_one(hp, pp, args.width, args.scale, args.wait, args.strict)
        if not ok:
            print('  ✗', msg)
            failed += 1

    print('完成：成功 %d / 失败 %d' % (len(args.html) - failed, failed))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
