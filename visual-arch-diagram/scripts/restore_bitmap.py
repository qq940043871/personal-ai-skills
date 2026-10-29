# -*- coding: utf-8 -*-
"""位图架构图 → 还原辅助（层带定界 + 分栏放大切片）

用法：
    python restore_bitmap.py 架构图.png [--out 输出目录] [--zoom 3]
                            [--rule-ratio 0.75] [--min-band 20]

做两件事：
  1) 用「双信号」扫出层带边界——
     a. 长横线：某行存在超过 rule_ratio × 图宽 的连续非白像素 → 这是层带的上下边框（最可靠）
     b. 空白行：非白像素占比低于阈值的连续行 → 层间空隙
     层带边框信号（a）在主，空隙信号（b）为辅。**只用空白行会把紧贴的层带合并成一大块**。
  2) 按层带边界分左右半幅放大切片，用于逐字辨认小字（原图 10–12px 直接看必糊）。

产出：layers.txt（层带坐标）+ band_XX_L/R.png（放大切片）
"""
import argparse
from pathlib import Path


def max_run_of_true(row):
    """一行布尔数组里 True 的最大连续长度——用来找层带的长横线边框"""
    import numpy as np
    if not row.any():
        return 0
    padded = np.concatenate(([False], row, [False]))
    idx = np.flatnonzero(np.diff(padded))
    return int((idx[1::2] - idx[0::2]).max()) if len(idx) >= 2 else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('--out', default=None, help='输出目录（默认源文件同级 _crop）')
    ap.add_argument('--zoom', type=float, default=3.0, help='放大倍率（默认 3；小字可到 5）')
    ap.add_argument('--rule-ratio', type=float, default=0.75,
                    help='多长的连续非白像素算"层带横线"（占图宽比例，默认 0.75）')
    ap.add_argument('--gap-threshold', type=float, default=0.01,
                    help='判断空白行的非白像素占比阈值（默认 0.01）')
    ap.add_argument('--min-band', type=int, default=20, help='最小层带高度，过滤噪声（默认 20）')
    ap.add_argument('--max-thickness', type=int, default=8,
                    help='横线的最大厚度（行）；超过此厚度的连续非白块是实心色块而非边框（默认 8）')
    args = ap.parse_args()

    import numpy as np
    from PIL import Image

    src = Path(args.src).resolve()
    if not src.exists():
        print('✗ 找不到图片:', src)
        return 1
    out = Path(args.out).resolve() if args.out else src.parent / '_crop'
    out.mkdir(parents=True, exist_ok=True)

    im = Image.open(src)
    W, H = im.size
    print('源图:', src.name, (W, H))

    a = np.array(im.convert('L'))
    dark = a < 245
    nonwhite = dark.mean(axis=1)
    min_run = int(W * args.rule_ratio)
    runs = np.array([max_run_of_true(dark[i]) for i in range(H)])
    rules = runs >= min_run          # 层带横线所在行
    gaps = nonwhite < args.gap_threshold   # 空白行

    # ---- 以「横线」为主切分层带：一对横线（上边框 / 下边框）= 一条层带 ----
    rule_rows = np.flatnonzero(rules)
    lines = ['# 检测结果', '',
             '图宽 %d → 判定为横线需连续非白 ≥ %d px' % (W, min_run),
             '命中横线行 %d 行；空白行 %d 行' % (len(rule_rows), int(gaps.sum())), '']

    bands = []
    if len(rule_rows) >= 2:
        # 把相邻横线行归组（同一条边框占若干像素）
        groups, cur = [], [rule_rows[0]]
        for r in rule_rows[1:]:
            if r - cur[-1] <= 2:
                cur.append(r)
            else:
                groups.append((cur[0], cur[-1]))
                cur = [r]
        groups.append((cur[0], cur[-1]))
        lines.append('横线分组（%d 条）: %s' % (len(groups), groups))
        # 排除「实心色块」：连续非白过厚的是数据层大色块，不是层带边框
        thick = [g for g in groups if g[1] - g[0] + 1 > args.max_thickness]
        groups = [g for g in groups if g[1] - g[0] + 1 <= args.max_thickness]
        if thick:
            lines.append('排除实心色块（厚 > %d 行，非边框）: %s' % (args.max_thickness, thick))
        lines.append('→ 采用其中 %d 条作为层带边框' % len(groups))
        lines.append('')
        # 相邻两条边框之间 = 一条层带
        for k in range(len(groups) - 1):
            y0, y1 = groups[k][1] + 1, groups[k + 1][0] - 1
            if y1 - y0 >= args.min_band:
                bands.append((y0, y1))
        lines.append('按横线切出 %d 条层带' % len(bands))
    else:
        lines.append('⚠️ 未检测到足够横线（图可能无边框），回退到「空白行」切分')

    if not bands:
        # 回退：按空白行切分
        i = 0
        while i < H:
            if gaps[i]:
                i += 1
                continue
            j = i
            while j < H and not gaps[j]:
                j += 1
            if j - i >= args.min_band:
                bands.append((i, j))
            i = j
        lines.append('回退切出 %d 条层带' % len(bands))

    lines += ['', '# 层带坐标（y0, y1, 高度）', '']
    for k, (y0, y1) in enumerate(bands, 1):
        lines.append('band_%02d: y %-5d → %-5d  (h=%d)' % (k, y0, y1, y1 - y0))

    # 自动告警：高度远超中位数的层带，多半是把两层并成了一条
    if len(bands) >= 3:
        hs = sorted(b[1] - b[0] for b in bands)
        med = hs[len(hs) // 2]
        big = [(i + 1, b[0], b[1]) for i, b in enumerate(bands) if b[1] - b[0] > med * 2]
        if big:
            lines += ['', '⚠️ 以下层带高度 > 中位数(%d) 的 2 倍，可能合并了多层，务必人工核对：' % med]
            for idx, y0, y1 in big:
                lines.append('   band_%02d  (y %d–%d, h=%d)' % (idx, y0, y1, y1 - y0))
            lines.append('   → 多为层内有大面积实心色块（被 --max-thickness 排除）。')

    lines += ['', '提示：若层带数明显少于实际层数，调小 --rule-ratio（如 0.5）；',
              '      若把一行文字误判成层带，调大 --rule-ratio（如 0.9）。']

    (out / 'layers.txt').write_text('\n'.join(lines), encoding='utf-8')
    print('\n'.join(lines))
    print('→ 写入', out / 'layers.txt')

    # ---- 分栏放大切片 ----
    made = 0
    for k, (y0, y1) in enumerate(bands, 1):
        y0 = max(0, y0 - 4)
        y1 = min(H, y1 + 4)
        for tag, x0, x1 in (('L', 0, W // 2), ('R', W // 2, W)):
            c = im.crop((x0, y0, x1, y1))
            w, h = c.size
            c = c.resize((int(w * args.zoom), int(h * args.zoom)), Image.LANCZOS)
            c.save(out / ('band_%02d_%s.png' % (k, tag)))
            made += 1
    print('→ 生成 %d 张放大切片（%g×）于 %s' % (made, args.zoom, out))
    print('\n下一步：逐张读取切片转录文案。凡不可辨的字段，交付时必须标注为"推断"。')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
