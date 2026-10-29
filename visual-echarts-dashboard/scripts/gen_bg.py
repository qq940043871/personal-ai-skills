#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
visual-echarts-dashboard / gen_bg.py

程序化生成大屏氛围底图 assets/img/bg.jpg（1920x1080）：
  1) 深蓝紫垂直渐变（顶 #0c1e4a → 底 #07102b，右下一点紫）
  2) 点阵世界地图水印（低透明度，居中偏上，供内容压图不抢戏）
  3) 三处径向光晕（左青、右蓝、下紫）
  4) 底部透视网格地板 + 全屏细网格
  5) 上下暗角渐变 + 微噪声（防色带）

用法：
  python gen_bg.py                     # 写回 ../assets/img/bg.jpg
  python gen_bg.py --out xxx.jpg --w 1920 --h 1080
"""
import argparse, math, os, random

from PIL import Image, ImageDraw, ImageFilter

# ---------- 粗略世界地图（lon/lat 多边形，仅作水印，不求精确） ----------
CONTINENTS = {
    "north_america": [(-168,65),(-160,71),(-140,70),(-125,49),(-118,48),(-105,49),(-95,47),
                      (-83,42),(-80,35),(-81,25),(-90,29),(-97,26),(-105,20),(-95,15),(-88,15),
                      (-84,10),(-79,9),(-83,15),(-90,20),(-97,22),(-105,25),(-114,30),(-120,34),
                      (-124,40),(-125,48),(-131,54),(-140,60),(-150,60),(-165,60)],
    "greenland":     [(-55,60),(-45,60),(-25,70),(-20,75),(-30,82),(-45,83),(-58,78),(-60,68)],
    "south_america": [(-78,8),(-72,11),(-62,10),(-52,5),(-50,0),(-44,-3),(-35,-6),(-38,-13),
                      (-42,-20),(-48,-25),(-53,-32),(-58,-38),(-62,-40),(-65,-45),(-68,-52),
                      (-71,-54),(-75,-48),(-73,-40),(-71,-30),(-70,-20),(-75,-14),(-79,-6),(-81,0)],
    "africa":        [(-17,14),(-10,15),(0,12),(8,4),(12,-2),(9,-8),(13,-17),(15,-25),(20,-34),
                      (27,-34),(32,-29),(35,-22),(40,-15),(41,-8),(43,-2),(48,2),(51,11),(44,11),
                      (40,15),(37,20),(34,28),(32,31),(25,32),(18,30),(10,34),(3,36),(-6,35),
                      (-12,28),(-17,21)],
    "eurasia":       [(-10,36),(-9,43),(-2,43),(0,47),(4,52),(8,55),(10,58),(15,66),(22,70),
                      (30,70),(40,68),(55,70),(70,72),(80,74),(95,78),(110,76),(125,73),(140,72),
                      (155,70),(165,67),(170,66),(162,60),(150,59),(142,54),(140,48),(135,44),
                      (130,42),(126,38),(122,32),(120,25),(112,20),(105,18),(100,13),(98,8),
                      (95,15),(90,22),(85,20),(80,8),(77,8),(73,20),(68,23),(62,25),(57,27),
                      (50,30),(48,38),(43,42),(40,44),(37,40),(30,40),(28,36),(24,36),(20,38),
                      (15,37),(12,38),(8,36)],
    "australia":     [(114,-22),(113,-26),(115,-34),(120,-34),(129,-32),(135,-35),(140,-38),
                      (146,-39),(150,-37),(153,-30),(153,-25),(146,-19),(142,-11),(136,-12),
                      (130,-11),(125,-14),(122,-18)],
}
# 零星岛屿（小椭圆：cx, cy, rx, ry，单位度）
ISLANDS = [
    (131,32,3.5,7),      # 日本
    (120,0,4,4),         # 婆罗洲
    (100,-2,3,5),        # 苏门答腊
    (47,-19,2.5,6),      # 马达加斯加
    (174,-41,3,5),       # 新西兰
    (-8,53,2,2.5),       # 英国
    (113,2,3,4),         # 菲律宾
]

TOP    = (12, 30, 74)     # #0c1e4a
MID    = (10, 22, 54)     # #0a1636
BOTTOM = (7, 16, 43)      # #07102b


def lerp(a, b, k):
    return tuple(round(a[i] + (b[i] - a[i]) * k) for i in range(3))


def base_gradient(w, h):
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        k = y / max(1, h - 1)
        c = lerp(TOP, MID, min(1, k / 0.55)) if k < 0.55 else lerp(MID, BOTTOM, (k - 0.55) / 0.45)
        for x in range(w):
            px[x, y] = c
    return img


def add_radial_glow(img, cx, cy, radius, color, alpha):
    """叠加一层径向光晕（屏幕混合感）"""
    w, h = img.size
    layer = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(layer)
    steps = 48
    for i in range(steps, 0, -1):
        r = radius * i / steps
        a = round(alpha * (1 - i / steps) ** 1.6)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=a)
    layer = layer.filter(ImageFilter.GaussianBlur(60))
    tint = Image.new("RGB", (w, h), color)
    img.paste(tint, (0, 0), layer)


def lonlat_to_px(lon, lat, w, h, scale, ox, oy):
    x = (lon + 180) / 360 * w * scale + ox
    y = (90 - lat) / 180 * h * scale + oy
    return x, y


def draw_world_map(img, w, h):
    """点阵世界地图水印：先铺极淡大陆填充，再叠点阵"""
    scale, ox, oy = 1.28, -w * 0.14, -h * 0.10
    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    for pts in CONTINENTS.values():
        md.polygon([lonlat_to_px(x, y, w, h, scale, ox, oy) for x, y in pts], fill=110)
    for cx, cy, rx, ry in ISLANDS:
        x, y = lonlat_to_px(cx, cy, w, h, scale, ox, oy)
        rxp = rx / 360 * w * scale
        ryp = ry / 180 * h * scale
        md.ellipse([x - rxp, y - ryp, x + rxp, y + ryp], fill=110)
    # 大陆填充（极淡）
    fill = Image.new("RGB", (w, h), (38, 84, 148))
    img.paste(fill, (0, 0), mask.point(lambda v: round(v * 0.16)))
    # 点阵：只落在 mask 内
    spacing, r = 9, 1.7
    dot = Image.new("L", (w, h), 0)
    dd = ImageDraw.Draw(dot)
    y = spacing
    while y < h:
        x = spacing
        while x < w:
            if mask.getpixel((min(w - 1, round(x)), min(h - 1, round(y)))) > 40:
                dd.ellipse([x - r, y - r, x + r, y + r], fill=46)
            x += spacing
        y += spacing
    dot = dot.filter(ImageFilter.GaussianBlur(0.6))
    tint = Image.new("RGB", (w, h), (122, 172, 236))
    img.paste(tint, (0, 0), dot)


def draw_perspective_floor(img, w, h):
    """底部透视网格地板"""
    layer = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(layer)
    horizon = round(h * 0.80)
    vpx = w / 2
    for i in range(-26, 27):
        x_bottom = vpx + i * (w / 16)
        d.line([(vpx, horizon), (x_bottom, h)], fill=26, width=1)
    y = horizon
    step = 6
    while y < h:
        d.line([(0, y), (w, y)], fill=26, width=1)
        step *= 1.32
        y += round(step)
    layer = layer.filter(ImageFilter.GaussianBlur(0.8))
    tint = Image.new("RGB", (w, h), (96, 158, 226))
    img.paste(tint, (0, 0), layer)


def draw_fine_grid(img, w, h):
    layer = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(layer)
    cell = 64
    for x in range(0, w, cell):
        d.line([(x, 0), (x, h)], fill=12, width=1)
    for y in range(0, h, cell):
        d.line([(0, y), (w, y)], fill=12, width=1)
    tint = Image.new("RGB", (w, h), (90, 150, 220))
    img.paste(tint, (0, 0), layer)


def add_vignette(img, w, h):
    layer = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(layer)
    d.rectangle([0, 0, w, round(h * 0.16)], fill=120)      # 顶部压暗（保标题对比）
    d.rectangle([0, h - round(h * 0.10), w, h], fill=110)  # 底部压暗（保播报对比）
    for x in range(round(w * 0.06)):                       # 左右轻压
        a = round(60 * (1 - x / (w * 0.06)))
        d.line([(x, 0), (x, h)], fill=a)
        d.line([(w - 1 - x, 0), (w - 1 - x, h)], fill=a)
    layer = layer.filter(ImageFilter.GaussianBlur(40))
    img.paste(Image.new("RGB", (w, h), (3, 7, 18)), (0, 0), layer)


def add_noise(img, sigma=2.0):
    random.seed(20261017)
    w, h = img.size
    noise = Image.effect_noise((w, h), sigma)
    img.paste(Image.merge("RGB", (noise, noise, noise)), (0, 0),
              noise.point(lambda v: 10))  # 10/255 强度，只去色带


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description="生成大屏氛围底图")
    ap.add_argument("--out", default=os.path.join(here, "..", "assets", "img", "bg.jpg"))
    ap.add_argument("--w", type=int, default=1920)
    ap.add_argument("--h", type=int, default=1080)
    ap.add_argument("--q", type=int, default=88)
    args = ap.parse_args()

    w, h = args.w, args.h
    img = base_gradient(w, h)
    add_radial_glow(img, w * 0.16, h * 0.30, w * 0.30, (36, 120, 220), 90)   # 左青光
    add_radial_glow(img, w * 0.86, h * 0.72, w * 0.34, (28, 84, 200), 80)    # 右蓝光
    add_radial_glow(img, w * 0.50, h * 1.02, w * 0.45, (64, 32, 128), 70)    # 下紫光
    draw_world_map(img, w, h)
    draw_fine_grid(img, w, h)
    draw_perspective_floor(img, w, h)
    add_vignette(img, w, h)
    add_noise(img)

    out = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    img.save(out, "JPEG", quality=args.q)
    print("底图已生成：%s（%dx%d，%d KB）" % (out, w, h, os.path.getsize(out) // 1024))


if __name__ == "__main__":
    main()
