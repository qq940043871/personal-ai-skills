#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
visual-threejs-scene / gen_textures.py

程序化生成 PBR 三件套贴图（albedo + normal + roughness），写入 skill 的 assets/img/。
原则：
  - 纯本地生成（numpy + PIL），无外部素材、无版权风险
  - 命名约定：tex-<name>.jpg（已有则只补 normal/rough，除非 --force）
              tex-<name>-normal.png（法线，PNG 保真）
              tex-<name>-rough.jpg（粗糙度，灰度走 G 通道）
  - 骨架按命名约定自动挂载，改图不改代码

用法：
  python gen_textures.py                # 生成全部（已存在同名文件默认跳过 albedo，强制重生成加 --force）
  python gen_textures.py --only lawn asphalt
  python gen_textures.py --size 768
"""
import argparse
import os

import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.normpath(os.path.join(HERE, "..", "assets", "img"))


# --------------------------------------------------------------------------- 噪声工具箱
def _grid_noise(size, gw, gh, rng):
    """低频随机网格 → 双三次放大到 size×size，值域 [0,1]"""
    g = rng.random((gh, gw)).astype(np.float32)
    im = Image.fromarray((g * 255).astype(np.uint8), mode="L")
    im = im.resize((size, size), Image.BICUBIC)
    return np.asarray(im, dtype=np.float32) / 255.0


def fbm(size, octaves=5, gw=4, rng=None, persistence=0.55):
    """分形值噪声：低频网格逐层加密叠加"""
    rng = rng or np.random.default_rng(7)
    out = np.zeros((size, size), dtype=np.float32)
    amp, total, g = 1.0, 0.0, gw
    for _ in range(octaves):
        out += amp * _grid_noise(size, max(2, g), max(2, int(g * size / max(size, 1)) or 2), rng)
        total += amp
        amp *= persistence
        g *= 2
    out /= total
    return np.clip(out, 0, 1)


def ridged(size, gw=6, rng=None, sharpness=2.2):
    """脊状噪声：1-|2n-1| 的幂，产生山脊/裂纹质感"""
    rng = rng or np.random.default_rng(11)
    n = fbm(size, octaves=4, gw=gw, rng=rng)
    r = np.power(1.0 - np.abs(2.0 * n - 1.0), sharpness)
    return np.clip(r, 0, 1)


def to_normal(height, strength=2.0):
    """高度图 → 切线空间法线贴图（three.js OpenGL 约定：G 通道向上）

    图像坐标 y 向下；切空间 v 向上 → dh/dv = -dh/dy
    n = normalize(-dh/du, -dh/dv, 1) = normalize(-dh/dx, +dh/dy, 1)
    """
    gx = np.gradient(height, axis=1).astype(np.float32)
    gy = np.gradient(height, axis=0).astype(np.float32)
    n = np.dstack([-gx * strength, gy * strength, np.ones_like(height)])
    n /= np.maximum(np.linalg.norm(n, axis=2, keepdims=True), 1e-8)
    rgb = np.clip(n * 0.5 + 0.5, 0, 1)
    return (rgb * 255).astype(np.uint8)


def speckle(size, n_dots, rng, lo=0.0, hi=1.0, blur=1):
    """随机斑点（骨料/钉帽/颗粒）"""
    layer = np.zeros((size, size), dtype=np.float32)
    ys = rng.integers(0, size, n_dots)
    xs = rng.integers(0, size, n_dots)
    vals = rng.uniform(lo, hi, n_dots).astype(np.float32)
    layer[ys, xs] = vals
    im = Image.fromarray((layer * 255).astype(np.uint8), mode="L")
    if blur > 0:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    return np.asarray(im, dtype=np.float32) / 255.0


def save_jpg(arr_u8, path, quality=87):
    Image.fromarray(arr_u8, mode="RGB").save(path, "JPEG", quality=quality, optimize=True)


def save_normal(height, strength, path):
    Image.fromarray(to_normal(height, strength), mode="RGB").save(path, "PNG", optimize=True)


def save_rough(r01, path, quality=85):
    g = np.clip(r01, 0, 1)
    arr = np.dstack([g, g, g])
    Image.fromarray((arr * 255).astype(np.uint8), mode="RGB").save(path, "JPEG", quality=quality, optimize=True)


# --------------------------------------------------------------------------- 各材质定义
def gen_lawn(size, rng):
    """草地：多频绿噪声 + 草叶簇竖纹 + 干草斑"""
    base = fbm(size, octaves=5, gw=5, rng=rng)                       # 大块明暗
    fine = fbm(size, octaves=3, gw=48, rng=rng)                      # 细密草叶
    dry = fbm(size, octaves=3, gw=7, rng=rng)                        # 干草/秃斑
    blades = np.zeros((size, size), dtype=np.float32)                # 草叶簇：竖向短条纹
    bw = max(2, size // 190)
    for _ in range(int(size * 1.6)):
        x = rng.integers(0, size - bw)
        y = rng.integers(0, size - size // 5)
        ln = rng.integers(size // 40, size // 9)
        blades[y:y + ln, x:x + bw] = rng.uniform(0.35, 1.0)
    blades = np.asarray(Image.fromarray((blades * 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(0.7)), dtype=np.float32) / 255.0

    h = base * 0.55 + fine * 0.25 + blades * 0.45 + dry * 0.15
    h = np.clip(h, 0, 1)

    green_lo = np.array([0.16, 0.30, 0.10], dtype=np.float32)
    green_hi = np.array([0.42, 0.58, 0.20], dtype=np.float32)
    dry_col = np.array([0.48, 0.46, 0.22], dtype=np.float32)
    lum = np.clip(base * 0.6 + fine * 0.4, 0, 1)[..., None]
    albedo = green_lo + (green_hi - green_lo) * lum
    albedo = albedo * (1 - dry[..., None] * 0.45) + dry_col * (dry[..., None] * 0.45)
    albedo = np.clip(albedo * (0.82 + 0.36 * fine[..., None]), 0, 1)

    rough = np.clip(0.88 + fine * 0.10 - dry * 0.06, 0, 1)
    return (albedo * 255).astype(np.uint8), h, rough


def gen_ground(size, rng):
    """场地硬化地坪（老化）：深灰基底 + 收缩裂缝 + 水渍 + 大块色斑。
    v0.3：albedo 从 0.52~0.68 压到 0.30~0.45 —— 旧亮灰版在强阳光+高空俯视下
    整片泛白（"雪原"观感），是写实感的最大杀手；真实户外地坪经积灰车辙就是深灰。"""
    pore = fbm(size, octaves=4, gw=6, rng=rng)
    fine = fbm(size, octaves=3, gw=60, rng=rng)
    pits = speckle(size, int(size * 3.2), rng, lo=0.55, hi=1.0, blur=1)   # 麻面孔洞
    crack = ridged(size, gw=4, rng=rng)                                    # 裂纹网
    crack = np.where(crack > 0.82, crack, 0.0)
    stain = fbm(size, octaves=3, gw=3, rng=rng)                            # 大块水渍
    patch = fbm(size, octaves=2, gw=2, rng=rng)                            # 修补/积水色斑

    h = pore * 0.5 + fine * 0.2 + pits * 0.35 - crack * 0.9
    h = np.clip(h, 0, 1)
    albedo_lo = np.array([0.30, 0.31, 0.30], dtype=np.float32)
    albedo_hi = np.array([0.44, 0.445, 0.435], dtype=np.float32)
    lum = np.clip(pore * 0.55 + fine * 0.45, 0, 1)[..., None]
    albedo = albedo_lo + (albedo_hi - albedo_lo) * lum
    albedo *= (1 - crack[..., None] * 0.7)                                 # 裂缝发暗
    albedo *= (0.82 + 0.26 * (1 - stain)[..., None])                       # 污渍更深
    albedo = np.clip(albedo * (1 - patch[..., None] * 0.22), 0, 1)         # 大块色斑
    albedo = np.clip(albedo * (0.9 + 0.2 * pits[..., None]), 0, 1)
    rough = np.clip(0.86 + fine * 0.10 - pits * 0.06, 0, 1)
    return (albedo * 255).astype(np.uint8), h, rough


def gen_asphalt(size, rng):
    """沥青：深灰基底 + 骨料颗粒 + 修补条带 + 轮胎磨光带"""
    agg = speckle(size, int(size * 14), rng, lo=0.5, hi=1.0, blur=1)       # 骨料
    fine = fbm(size, octaves=3, gw=54, rng=rng)
    patch = fbm(size, octaves=3, gw=3, rng=rng)                            # 修补区
    wear = fbm(size, octaves=2, gw=8, rng=rng)                             # 车轮磨光带
    h = fine * 0.35 + agg * 0.55 + patch * 0.2
    h = np.clip(h, 0, 1)
    albedo_lo = np.array([0.075, 0.078, 0.082], dtype=np.float32)
    albedo_hi = np.array([0.20, 0.20, 0.21], dtype=np.float32)
    lum = np.clip(agg * 0.7 + fine * 0.3, 0, 1)[..., None]
    albedo = albedo_lo + (albedo_hi - albedo_lo) * lum
    albedo *= (1 - patch[..., None] * 0.25)
    albedo = np.clip(albedo * (1 + wear[..., None] * 0.25), 0, 1)          # 磨光带稍亮
    rough = np.clip(0.9 - agg * 0.18 - wear * 0.1, 0, 1)
    return (albedo * 255).astype(np.uint8), h, rough


def gen_wall_steel(size, rng):
    """彩钢板：压型波纹（清晰正弦波，峰脊受光）+ 螺钉点阵 + 轻微积灰"""
    x = np.arange(size, dtype=np.float32)
    period = max(8.0, size / 14.0)
    wave = 0.5 + 0.5 * np.sin(2 * np.pi * x / period)
    wave = np.tile(wave[None, :], (size, 1))
    seam = np.exp(-((x % period) ** 2) / (2 * (period * 0.06) ** 2))       # 波谷压缝线
    seam = np.tile(seam[None, :], (size, 1))
    dust = fbm(size, octaves=3, gw=6, rng=rng)
    rust = np.clip(ridged(size, gw=5, rng=rng) - 0.86, 0, 1) * 0.8         # 零星锈迹
    screws = np.zeros((size, size), dtype=np.float32)
    for gy in range(0, size, max(24, size // 16)):
        for gx in range(0, size, max(24, size // 16)):
            yy, xx = gy + rng.integers(0, 8), gx + rng.integers(0, 8)
            screws[yy % size, xx % size] = 1.0
    screws = np.asarray(Image.fromarray((screws * 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(1.2)), dtype=np.float32) / 255.0

    h = wave * 0.75 + screws * 0.3 + dust * 0.12 - seam * 0.25
    h = np.clip(h, 0, 1)
    albedo_lo = np.array([0.62, 0.66, 0.70], dtype=np.float32)             # 浅灰蓝涂装
    albedo_hi = np.array([0.86, 0.88, 0.90], dtype=np.float32)
    lum = np.clip(wave * 0.75 + dust * 0.25, 0, 1)[..., None]
    albedo = albedo_lo + (albedo_hi - albedo_lo) * lum
    albedo *= (0.94 + 0.06 * dust[..., None])
    albedo = np.clip(albedo * (1 - rust[..., None] * 0.9) + np.array([0.45, 0.22, 0.08]) * rust[..., None], 0, 1)
    rough = np.clip(0.42 + dust * 0.16 + rust * 0.35, 0, 1)                # 涂装较光，锈处糙
    return (albedo * 255).astype(np.uint8), h, rough


def gen_concrete(size, rng):
    """墙板混凝土：麻面 + 浇筑接缝 + 气孔"""
    pore = fbm(size, octaves=4, gw=6, rng=rng)
    fine = fbm(size, octaves=3, gw=64, rng=rng)
    pits = speckle(size, int(size * 2.2), rng, lo=0.5, hi=1.0, blur=1)
    joint = np.zeros((size, size), dtype=np.float32)                       # 模板接缝（横向两道）
    for jy in [int(size * 0.5), int(size * 0.96)]:
        joint[max(0, jy - 2):jy + 2, :] = 1.0
    joint = np.asarray(Image.fromarray((joint * 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(1.0)), dtype=np.float32) / 255.0
    h = pore * 0.5 + fine * 0.22 + pits * 0.3 - joint * 0.6
    h = np.clip(h, 0, 1)
    albedo_lo = np.array([0.55, 0.55, 0.53], dtype=np.float32)
    albedo_hi = np.array([0.72, 0.71, 0.68], dtype=np.float32)
    lum = np.clip(pore * 0.6 + fine * 0.4, 0, 1)[..., None]
    albedo = albedo_lo + (albedo_hi - albedo_lo) * lum
    albedo *= (1 - joint[..., None] * 0.5)
    albedo = np.clip(albedo * (0.92 + 0.16 * pits[..., None]), 0, 1)
    rough = np.clip(0.82 + fine * 0.1 - pits * 0.1, 0, 1)
    return (albedo * 255).astype(np.uint8), h, rough


def gen_crate_normal(size, rng):
    """木箱：albedo 沿用已有图案，只补 normal + rough（从亮度导凹凸 + 木纹）"""
    src = os.path.join(IMG_DIR, "tex-crate.jpg")
    im = Image.open(src).convert("L").resize((size, size), Image.BICUBIC)
    lum = np.asarray(im, dtype=np.float32) / 255.0
    grain = fbm(size, octaves=4, gw=40, rng=rng)                           # 木纹
    plank = np.exp(-((np.arange(size) % max(10, size // 6)) ** 2) / 40.0)  # 板缝
    plank = np.tile(plank[None, :], (size, 1))
    h = lum * 0.45 + grain * 0.3 + plank * 0.25
    h = np.clip(h, 0, 1)
    rough = np.clip(0.72 + grain * 0.22 - lum * 0.1, 0, 1)
    return None, h, rough


def gen_ore(size, rng):
    """矿石堆：碎石颗粒堆 + 深浅矿粉"""
    gravel = speckle(size, int(size * 22), rng, lo=0.4, hi=1.0, blur=1)
    fine = fbm(size, octaves=4, gw=36, rng=rng)
    big = fbm(size, octaves=3, gw=5, rng=rng)
    h = gravel * 0.55 + fine * 0.3 + big * 0.15
    h = np.clip(h, 0, 1)
    albedo_lo = np.array([0.23, 0.19, 0.15], dtype=np.float32)
    albedo_hi = np.array([0.46, 0.40, 0.33], dtype=np.float32)
    lum = np.clip(gravel * 0.6 + fine * 0.4, 0, 1)[..., None]
    albedo = albedo_lo + (albedo_hi - albedo_lo) * lum
    albedo *= (0.85 + 0.3 * big[..., None])
    albedo = np.clip(albedo, 0, 1)
    rough = np.clip(0.9 - gravel * 0.2, 0, 1)
    return (albedo * 255).astype(np.uint8), h, rough


def gen_bench(size, rng):
    """露天矿台阶岩石：水平沉积层理条带 + 红褐铁矿 + 碎石颗粒 + 黑色矿脉"""
    big = fbm(size, octaves=3, gw=4, rng=rng)                            # 大块岩性分区
    yline = fbm(size, octaves=3, gw=3, rng=rng).mean(axis=1)             # 每行亮度（扰动层理边界）
    band = 0.5 + 0.5 * np.sin(2 * np.pi * (np.arange(size) / max(4.0, size / 8.0)) + yline * 9.0)
    band = np.tile(band[:, None].astype(np.float32), (1, size))          # 横向条带铺满（层理）
    gravel = speckle(size, int(size * 10), rng, lo=0.35, hi=1.0, blur=1) # 碎石颗粒
    fine = fbm(size, octaves=4, gw=40, rng=rng)
    vein = np.clip(ridged(size, gw=6, rng=rng) - 0.90, 0, 1) * 0.8       # 零星黑色矿脉
    h = band * 0.38 + gravel * 0.42 + fine * 0.2 - vein * 0.3
    h = np.clip(h, 0, 1)
    rock_lo = np.array([0.27, 0.17, 0.12], dtype=np.float32)             # 暗红褐岩
    rock_hi = np.array([0.62, 0.40, 0.26], dtype=np.float32)             # 亮锈红矿层
    lum = np.clip(band * 0.55 + big * 0.45, 0, 1)[..., None]
    albedo = rock_lo + (rock_hi - rock_lo) * lum
    albedo *= (0.85 + 0.3 * gravel[..., None])
    albedo = np.clip(albedo * (1 - vein[..., None] * 0.85), 0, 1)        # 矿脉发黑
    rough = np.clip(0.92 - gravel * 0.15 - fine * 0.05, 0, 1)
    return (albedo * 255).astype(np.uint8), h, rough


def gen_track(size, rng):
    """履带板：深色金属 + 横向板节线 + 销轴耳 + 泥污（电铲/矿卡/推土机履带）"""
    x = np.arange(size, dtype=np.float32)
    period = max(6.0, size / 10.0)                                       # 板节距
    shoe = 0.5 + 0.5 * np.sin(2 * np.pi * x / period)
    shoe = np.tile(shoe[None, :], (size, 1))
    pin = np.exp(-((x % period) ** 2) / (2 * (period * 0.08) ** 2))      # 销轴亮点
    pin = np.tile(pin[None, :], (size, 1))
    fine = fbm(size, octaves=3, gw=48, rng=rng)
    mud = fbm(size, octaves=4, gw=6, rng=rng)
    h = shoe * 0.55 + pin * 0.25 + fine * 0.2
    h = np.clip(h, 0, 1)
    lo = np.array([0.055, 0.06, 0.065], dtype=np.float32)
    hi = np.array([0.16, 0.17, 0.18], dtype=np.float32)
    lum = np.clip(shoe * 0.7 + fine * 0.3, 0, 1)[..., None]
    albedo = lo + (hi - lo) * lum
    albedo *= (1 - mud[..., None] * 0.35)                                # 泥污变暗
    albedo = np.clip(albedo, 0, 1)
    rough = np.clip(0.75 - shoe * 0.1 + mud * 0.2, 0, 1)
    return (albedo * 255).astype(np.uint8), h, rough


def gen_tank(size, rng):
    """罐体：环向焊缝 + 竖向接缝 + 底部锈蚀 + 涂装灰白"""
    y = np.arange(size, dtype=np.float32)
    weld_y = [int(size * f) for f in (0.18, 0.52, 0.86)]
    weld = np.zeros((size, size), dtype=np.float32)
    for wy in weld_y:
        weld[max(0, wy - 2):wy + 2, :] = 1.0
    weld = np.asarray(Image.fromarray((weld * 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(1.5)), dtype=np.float32) / 255.0
    vseam = np.exp(-((np.arange(size) % max(10, size // 5)) ** 2) / 30.0)
    vseam = np.tile(vseam[None, :], (size, 1))
    dirt = fbm(size, octaves=4, gw=5, rng=rng)
    rust_zone = np.clip((y / size - 0.7) * 4.0, 0, 1)                      # 底部锈蚀带
    rust = np.clip(ridged(size, gw=8, rng=rng) - 0.55, 0, 1) * rust_zone

    h = weld * 0.5 + vseam * 0.25 + dirt * 0.25 + rust * 0.3
    h = np.clip(h, 0, 1)
    albedo_lo = np.array([0.70, 0.71, 0.72], dtype=np.float32)
    albedo_hi = np.array([0.88, 0.88, 0.87], dtype=np.float32)
    lum = np.clip(dirt * 0.7, 0, 1)[..., None]
    albedo = albedo_lo + (albedo_hi - albedo_lo) * lum
    albedo *= (1 - weld[..., None] * 0.12)
    albedo = np.clip(albedo * (1 - rust[..., None] * 0.85) + np.array([0.42, 0.20, 0.09]) * rust[..., None], 0, 1)
    rough = np.clip(0.45 + dirt * 0.2 + rust * 0.4, 0, 1)
    return (albedo * 255).astype(np.uint8), h, rough


# --------------------------------------------------------------------------- 主流程
BUILDERS = {
    "lawn":     (gen_lawn,      2.6, True),
    "ground":   (gen_ground,    2.8, True),
    "asphalt":  (gen_asphalt,   2.6, True),
    "wallsteel": (gen_wall_steel, 3.2, True),
    "concrete": (gen_concrete,  2.6, True),
    "crate":    (gen_crate_normal, 2.4, False),
    "ore":      (gen_ore,       2.4, True),
    "tank":     (gen_tank,      2.2, True),
    "bench":    (gen_bench,     2.0, True),
    "track":    (gen_track,     2.8, True),
}


SEEDS = {"lawn": 101, "ground": 202, "asphalt": 303, "wallsteel": 404,
         "concrete": 505, "crate": 606, "ore": 707, "tank": 808,
         "bench": 909, "track": 1011}


def main():
    ap = argparse.ArgumentParser(description="生成 PBR 三件套贴图")
    ap.add_argument("--only", nargs="*", default=None, help="只生成指定材质（空格分隔）")
    ap.add_argument("--size", type=int, default=768, help="贴图边长（默认 768）")
    ap.add_argument("--force", action="store_true", help="重生成已存在的 albedo")
    args = ap.parse_args()

    os.makedirs(IMG_DIR, exist_ok=True)
    names = args.only or sorted(BUILDERS)
    total = 0
    for name in names:
        if name not in BUILDERS:
            print("跳过未知材质：%s（可选：%s）" % (name, ", ".join(sorted(BUILDERS))))
            continue
        fn, n_strength, want_albedo = BUILDERS[name]
        rng = np.random.default_rng(SEEDS[name])   # 固定种子：同参数每次生成结果一致
        albedo, height, rough = fn(args.size, rng)
        albedo_path = os.path.join(IMG_DIR, "tex-%s.jpg" % name)
        normal_path = os.path.join(IMG_DIR, "tex-%s-normal.png" % name)
        rough_path = os.path.join(IMG_DIR, "tex-%s-rough.jpg" % name)
        if want_albedo and (args.force or not os.path.exists(albedo_path)):
            save_jpg(albedo, albedo_path)
            total += 1
            print("albedo  : tex-%s.jpg" % name)
        save_normal(height, n_strength, normal_path)
        save_rough(rough, rough_path)
        total += 2
        print("normal  : tex-%s-normal.png   rough: tex-%s-rough.jpg" % (name, name))
    print("完成：%d 个文件写入 %s" % (total, IMG_DIR))


if __name__ == "__main__":
    main()
