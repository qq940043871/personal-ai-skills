"""测量 5 张原始头像的「内圆」几何（圆心/半径）与「人头」尺寸占比。

原图是无损 PNG，可直接做边界检测。
输出用于决定：裁到内圆 + 是否需要统一人头的构图尺度。
"""
import os
from PIL import Image

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(BASE, 'family-check-in', 'static', 'avatars')

FILES = ['avatar-dad.png', 'avatar-mom.png', 'avatar-son.png',
         'avatar-baby.png', 'avatar-grandma.png']


def diff(c1, c2):
    return sum(abs(a - b) for a, b in zip(c1, c2))


def find_disc(im):
    """沿过圆心的横竖两条中线找内圆边界。返回 (cx, cy, r)。"""
    w, h = im.size
    px = im.load()
    ref = px[3, 3]                      # 方底颜色（左上角）
    TH = 6                              # 颜色差阈值（无损图可放小）
    RUN = 6                             # 需连续 N 像素确认，抗噪

    def scan(seq, start, step, limit):
        """从 start 出发按 step 前进，找到第一个持续变化的坐标。"""
        hit = 0
        i = start
        while 0 <= i < limit:
            c = seq(i)
            if diff(c, ref) > TH:
                hit += 1
                if hit >= RUN:
                    return i - RUN + 1
            else:
                hit = 0
            i += step
        return None

    row = h // 2
    col = w // 2
    left = scan(lambda x: px[x, row], 0, 1, w)
    right = scan(lambda x: px[x, row], w - 1, -1, w)
    top = scan(lambda y: px[col, y], 0, 1, h)
    bottom = scan(lambda y: px[col, y], h - 1, -1, h)
    vals = [left, right, top, bottom]
    if any(v is None for v in vals):
        return None, (left, right, top, bottom)

    cx = (left + right) / 2.0
    cy = (top + bottom) / 2.0
    rx = (right - left) / 2.0
    ry = (bottom - top) / 2.0
    return (cx, cy, rx, ry), (left, right, top, bottom)


def head_bbox(im, disc):
    """以内圆边缘采样色为参考，测人头包围盒（近似）。"""
    w, h = im.size
    px = im.load()
    cx, cy, rx, ry = disc
    # 在圆内左右边缘取样作为「圆底色」参考
    ref = px[int(cx - rx * 0.85), int(cy)]
    TH = 40

    minx, miny, maxx, maxy = w, h, 0, 0
    for y in range(int(cy - ry), int(cy + ry) + 1, 2):
        for x in range(int(cx - rx), int(cx + rx) + 1, 2):
            dx = (x - cx) / rx
            dy = (y - cy) / ry
            if dx * dx + dy * dy > 1.0:
                continue                       # 只看圆内
            if diff(px[x, y], ref) > TH:
                minx = min(minx, x); maxx = max(maxx, x)
                miny = min(miny, y); maxy = max(maxy, y)
    if maxx <= minx:
        return None
    return minx, miny, maxx, maxy


print(f'{"文件":<20}{"圆心":<18}{"半径":<16}{"人头高/圆直径":<16}{"人头宽/圆直径"}')
print('-' * 88)
for f in FILES:
    im = Image.open(os.path.join(SRC, f)).convert('RGB')
    disc, edges = find_disc(im)
    if disc is None:
        print(f'{f:<20} 内圆检测失败 edges={edges}')
        continue
    cx, cy, rx, ry = disc
    hb = head_bbox(im, disc)
    if hb:
        hw = hb[2] - hb[0]
        hh = hb[3] - hb[1]
        hr = f'{hh / (2 * ry):.3f}'.ljust(14) + f'{hw / (2 * rx):.3f}'
    else:
        hr = 'n/a'
    print(f'{f:<20}({cx:6.0f},{cy:6.0f})  ({rx:5.0f},{ry:5.0f})  {hr}')
