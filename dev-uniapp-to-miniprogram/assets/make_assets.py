"""重建小程序头像资源：裁到内圆 + 圆外补圆底色，输出干净的满圆头像。

为什么这么做：
- 原图是「方形底色 + 内圆」结构，直接缩放到圆形容器里，四角会露出方形底色，
  且当方底与内圆颜色接近时（如浅蓝方底 + 稍浅蓝内圆）会出现一圈看不清的接缝。
- 这里统一裁到内圆，并把圆外像素填成内圆底色（带羽化），
  于是无论容器怎么裁，都是干净的圆形头像，五张观感一致。

依赖：原项目 family-check-in/static/avatars/*.png（1024×1024 无损）
输出：images/avatars/*.jpg（200×200，baseline JPEG q88）
"""
import os
from PIL import Image, ImageDraw, ImageFilter

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(BASE, 'family-check-in', 'static', 'avatars')
DST = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'images', 'avatars')

OUT_SIZE = 200          # 最终边长（显示最大仅 96rpx≈48px，200 足够且体积很小）
SUPER = 600             # 中间超采样尺寸，保证圆形边缘平滑
QUALITY = 88

# (源文件, 目标文件)；内圆几何由 tools/measure_disc.py 实测得出
JOBS = [
    ('avatar-dad.png',     'avatar-dad.jpg',     (506, 506, 506, 506)),
    ('avatar-mom.png',     'avatar-mom.jpg',     (507, 506, 506, 506)),
    ('avatar-son.png',     'avatar-son.jpg',     (506, 506, 433, 436)),
    ('avatar-baby.png',    'avatar-baby.jpg',    (509, 507, 479, 479)),
    ('avatar-grandma.png', 'avatar-grandma.jpg', (524, 526, 488, 476)),
]

HAIRY = 4               # 羽化像素（超采样尺度下）


def disc_edge_color(im, cx, cy, r):
    """采样内圆边缘一圈的颜色，取中位数，作为圆外填充色。"""
    px = im.load()
    vals = []
    for i in range(180):
        import math
        a = i * 2 * math.pi / 180
        x = int(cx + r * 0.92 * math.cos(a))
        y = int(cy + r * 0.92 * math.sin(a))
        vals.append(px[x, y])
    vals.sort(key=lambda c: sum(c))
    return vals[len(vals) // 2]


os.makedirs(DST, exist_ok=True)
total = 0
for src_name, dst_name, (cx, cy, rx, ry) in JOBS:
    src_path = os.path.join(SRC, src_name)
    if not os.path.exists(src_path):
        print('MISSING', src_path)
        continue

    im = Image.open(src_path).convert('RGB')
    r = min(rx, ry)                                  # 内切圆，避免带入方底色

    # 1) 裁到内圆外接正方形
    box = (int(cx - r), int(cy - r), int(cx + r), int(cy + r))
    disc = im.crop(box).resize((SUPER, SUPER), Image.LANCZOS)

    # 2) 圆外区域填成圆底色（羽化边缘，避免硬接缝）
    bg = disc_edge_color(im, cx, cy, r)
    mask = Image.new('L', (SUPER + 2 * HAIRY, SUPER + 2 * HAIRY), 0)
    ImageDraw.Draw(mask).ellipse((HAIRY, HAIRY, SUPER + HAIRY - 1, SUPER + HAIRY - 1), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(HAIRY / 2.0)).crop(
        (HAIRY, HAIRY, HAIRY + SUPER, HAIRY + SUPER))
    canvas = Image.new('RGB', (SUPER, SUPER), bg)
    canvas.paste(disc, (0, 0), mask)

    # 3) 缩到目标尺寸输出
    out = os.path.join(DST, dst_name)
    canvas.resize((OUT_SIZE, OUT_SIZE), Image.LANCZOS).save(
        out, 'JPEG', quality=QUALITY, optimize=True, progressive=False)

    size = os.path.getsize(out)
    total += size
    print(f'{dst_name:<22}{size:>7} bytes   圆底色={bg}')

print(f'{"TOTAL":<22}{total:>7} bytes')
