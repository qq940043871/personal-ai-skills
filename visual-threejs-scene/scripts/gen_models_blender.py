#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
gen_models_blender.py —— 用 Blender 生成高精度工业设备 GLB（数字孪生 skill 资产工厂）

运行环境：Blender 自带的 Python（不是系统 python），必须这样调用：
    blender.exe --background --python gen_models_blender.py -- --out <目录> [--models tank,container]
                                                                    [--size tank:32,26]

设计原则
--------
1. **真实尺寸（米）**：模型按工业实物尺寸建模，场景里 scale=1 直接用，不用猜缩放。
2. **原点在底部中心**：与 skill 现有 ph-*.glb 一致，摆放时 position:[x, 0, z] 即落地。
3. **倒角优先**：工业设备的"真实感"第一来源是边缘高光。所有板件/壳体都加 BEVEL 修改器。
4. **人体工学细节不随主体缩放**：栏杆永远 1.1m、踏距永远 0.32m。罐子可以 Ø32m，
   栏杆不能跟着放大成 3m —— 直径控制"环向细节数量"，高度控制"纵向细节数量"。
5. **面数克制**：单模型 <5 万面，GLB <1.5MB（要 base64 内联进单文件 HTML）。

⚠️ Blender headless 陷阱（本次实测踩坑）
---------------------------------------
**bpy.ops.transform.rotate / scale 是对"所有选中物体"操作的**。headless 下
primitive_cylinder_add 创建后，旧物体仍处于选中态 —— 每转一次踏棍，
之前创建的罐壁/栏杆/平台全被跟着旋转（表现：细节"消失"，其实全转到别处了）。
所以本脚本的所有构件创建都走 cyl()/cub() 辅助函数：先 select_all(DESELECT)，
创建后用数学方式设 rotation_euler 并立即 transform_apply，绝不依赖选中态。
"""

import bpy
import sys
import os
import math
from math import sin, cos, pi, radians


# ============================================================================
# 基础设施
# ============================================================================

def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def mat(name, color, roughness=0.5, metalness=0.0, **kw):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        lin = [c ** 2.2 for c in color]          # sRGB → 线性
        bsdf.inputs["Base Color"].default_value = (lin[0], lin[1], lin[2], 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metalness
        for k, v in kw.items():
            key = k.replace("_", " ").title()
            if key in bsdf.inputs:
                bsdf.inputs[key].default_value = v
    return m


MATS = {}

def build_materials():
    # 钢漆面调深（v2）：0.62 的浅灰在强阳光下泛白像塑料；中灰蓝更接近真实防腐漆
    MATS["steel_paint"] = mat("steel_paint", (0.42, 0.46, 0.50), 0.42, 0.35)
    MATS["steel_raw"]   = mat("steel_raw",   (0.38, 0.39, 0.41), 0.55, 0.75)
    MATS["galvanized"]  = mat("galvanized",  (0.58, 0.60, 0.62), 0.38, 0.80)
    MATS["rubber"]      = mat("rubber",      (0.07, 0.07, 0.08), 0.90, 0.0)
    MATS["glass"]       = mat("glass",       (0.20, 0.30, 0.38), 0.06, 0.0)
    MATS["brass"]       = mat("brass",       (0.60, 0.46, 0.22), 0.38, 0.85)
    MATS["concrete"]    = mat("concrete",    (0.36, 0.36, 0.35), 0.92, 0.0)
    MATS["hub"]         = mat("hub",         (0.30, 0.31, 0.33), 0.45, 0.70)


def bevel(obj, width=0.02, segments=2):
    b = obj.modifiers.new("bevel", 'BEVEL')
    b.width = width
    b.segments = segments
    b.limit_method = 'ANGLE'
    b.angle_limit = radians(60)
    return b


def apply_modifiers(obj):
    bpy.context.view_layer.objects.active = obj
    for m in list(obj.modifiers):
        try:
            bpy.ops.object.modifier_apply(modifier=m.name)
        except Exception:
            pass
    return obj


def set_mat(obj, m):
    if obj.data.materials:
        obj.data.materials[0] = m
    else:
        obj.data.materials.append(m)
    return obj


def _deselect_all():
    bpy.ops.object.select_all(action='DESELECT')


def cyl(radius, depth, verts, loc, rot=None, m=None, bev=None):
    """安全创建圆柱。rot = (rx, ry, rz) 弧度，创建后立即应用（不依赖选中态）"""
    _deselect_all()
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, vertices=verts, location=loc)
    o = bpy.context.active_object
    if rot:
        o.rotation_euler = rot
        bpy.ops.object.transform_apply(rotation=True)
    if bev:
        bevel(o, bev[0], bev[1])
    if m:
        set_mat(o, m)
    return o


def cub(size, loc, rot=None, m=None, bev=None):
    """安全创建盒体。size = (sx, sy, sz)"""
    _deselect_all()
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    o = bpy.context.active_object
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    if rot:
        o.rotation_euler = rot
        bpy.ops.object.transform_apply(rotation=True)
    if bev:
        bevel(o, bev[0], bev[1])
    if m:
        set_mat(o, m)
    return o


def cone(r1, r2, depth, verts, loc, rot=None, m=None, bev=None):
    _deselect_all()
    bpy.ops.mesh.primitive_cone_add(radius1=r1, radius2=r2, depth=depth, vertices=verts, location=loc)
    o = bpy.context.active_object
    if rot:
        o.rotation_euler = rot
        bpy.ops.object.transform_apply(rotation=True)
    if bev:
        bevel(o, bev[0], bev[1])
    if m:
        set_mat(o, m)
    return o


def torus(R, r, major, minor, loc, m=None, rot=None):
    _deselect_all()
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r,
                                     major_segments=major, minor_segments=minor, location=loc)
    o = bpy.context.active_object
    if rot:
        o.rotation_euler = rot
        bpy.ops.object.transform_apply(rotation=True)
    if m:
        set_mat(o, m)
    return o


def move_origin_bottom(obj):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    minz = min((obj.matrix_world @ v.co).z for v in obj.data.vertices)
    obj.location.z -= minz
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj


def join_parts(parts, name):
    """合并前逐个应用修改器（先 join 再 apply 会让倒角作用于复杂网格：极慢且产生废面）"""
    for p in parts:
        if p.modifiers:
            apply_modifiers(p)
    _deselect_all()
    for p in parts:
        p.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    merged = bpy.context.active_object
    merged.name = name
    return merged


# ============================================================================
# 模型 1：立式储罐（tank）—— 化工/油品仓储核心资产
# ============================================================================

def build_tank(diameter=12.0, height=16.0):
    r = diameter / 2.0
    parts = []
    seg = max(40, min(72, int(diameter * 1.6)))

    # 罐壁
    parts.append(cyl(r, height, seg, (0, 0, height / 2), m=MATS["steel_paint"], bev=(0.015, 1)))

    # 抗风圈：每 ~7m 一道
    n_ring = max(2, int(height / 7.0))
    for i in range(n_ring):
        hz = height * (0.18 + 0.72 * i / max(1, n_ring - 1)) if n_ring > 1 else height * 0.5
        parts.append(cyl(r + 0.10, 0.34, seg, (0, 0, hz), m=MATS["steel_raw"], bev=(0.02, 2)))

    # 弱锥顶
    parts.append(cone(r + 0.12, r, 1.5, seg, (0, 0, height + 0.75), m=MATS["steel_paint"], bev=(0.02, 2)))

    # 顶部平台（环形走道，位于锥顶外缘之上，栏杆立在平台上）
    deck_r = r - 1.0
    parts.append(cyl(deck_r, 0.10, 48, (0, 0, height + 1.45), m=MATS["galvanized"]))

    # 顶部栏杆（立柱间距 ~2.2m；高度从平台面起算，确保在锥顶之上）
    rail_r = deck_r
    n_post = max(12, int(2 * pi * rail_r / 2.2))
    deck_z = height + 1.50
    for i in range(n_post):
        a = 2 * pi * i / n_post
        parts.append(cyl(0.045, 1.10, 8, (rail_r * cos(a), rail_r * sin(a), deck_z + 0.55),
                         m=MATS["galvanized"]))
    for hz_off in (0.55, 1.08):
        parts.append(torus(rail_r, 0.035, 64, 6, (0, 0, deck_z + hz_off), MATS["galvanized"]))

    # 笼式爬梯：两根竖杆 + 横踏棍 + 外笼弧杆（贴罐壁，贯穿全高）
    ladder_r = r + 0.42
    la = radians(35)
    lx, ly = ladder_r * cos(la), ladder_r * sin(la)
    ux, uy = -sin(la), cos(la)               # 切向单位向量
    for off in (-0.26, 0.26):
        parts.append(cyl(0.05, height + 2.6, 8, (lx + ux * off, ly + uy * off, (height + 2.6) / 2 - 0.2),
                         m=MATS["galvanized"]))
    n_rung = int(height / 0.32)
    for i in range(1, n_rung):
        parts.append(cyl(0.030, 0.52, 6, (lx, ly, i * 0.32), rot=(0, pi / 2, la), m=MATS["galvanized"]))
    # 外笼弧杆（每 3m 一道半圆护圈，简化为细环）
    for hz in range(3, int(height), 3):
        parts.append(torus(0.42, 0.028, 12, 5, (lx, ly, hz), MATS["galvanized"]))

    # 人孔（顶部）+ 侧面接管/法兰/阀组
    parts.append(cyl(0.45, 0.55, 20, (r * 0.45, r * 0.2, height + 2.0), m=MATS["steel_raw"], bev=(0.03, 2)))
    for ang in (radians(180), radians(250)):
        nx, ny = cos(ang), sin(ang)
        parts.append(cyl(0.22, 0.7, 16, ((r + 0.30) * nx, (r + 0.30) * ny, 1.5),
                         rot=(0, pi / 2, ang), m=MATS["steel_raw"]))
        parts.append(cyl(0.38, 0.12, 20, ((r + 0.68) * nx, (r + 0.68) * ny, 1.5),
                         rot=(0, pi / 2, ang), m=MATS["brass"]))
        parts.append(cub((0.55, 0.55, 0.55), ((r + 1.05) * nx, (r + 1.05) * ny, 1.5),
                         rot=(0, 0, -ang), m=MATS["brass"], bev=(0.04, 2)))

    # 混凝土基础
    parts.append(cyl(r + 0.9, 0.45, 48, (0, 0, 0.22), m=MATS["concrete"]))

    merged = join_parts(parts, "tank")
    move_origin_bottom(merged)
    return merged


# ============================================================================
# 模型 2：20ft 集装箱（container）—— 竖波纹侧板 + 角件 + 端门
# ============================================================================

def build_container():
    L, W, H = 6.058, 2.438, 2.591
    parts = []

    # 竖波纹侧板（两侧）
    corr_pitch = 0.28
    n_corr = int(L / corr_pitch)
    for side in (1, -1):
        for i in range(n_corr):
            x = -L / 2 + 0.14 + i * corr_pitch
            if abs(x) > L / 2 - 0.06:
                continue
            parts.append(cub((corr_pitch * 0.62, 0.055, H - 0.30),
                             (x, side * (W / 2 - 0.03), H / 2 + 0.15), m=MATS["steel_paint"]))

    # 端板
    for side in (1, -1):
        parts.append(cub((0.06, W - 0.1, H - 0.30), (side * (L / 2 - 0.03), 0, H / 2 + 0.15),
                         m=MATS["steel_paint"]))

    # 顶盖 & 底板
    parts.append(cub((L, W, 0.06), (0, 0, H - 0.03), m=MATS["steel_paint"]))
    parts.append(cub((L, W, 0.30), (0, 0, 0.15), m=MATS["steel_raw"]))

    # 角件 ×8（集装箱识别特征）
    for sx in (1, -1):
        for sy in (1, -1):
            for sz in (0, 1):
                parts.append(cub((0.18, 0.18, 0.18),
                                 (sx * (L / 2 - 0.09), sy * (W / 2 - 0.09),
                                  (H - 0.09) if sz else 0.09), m=MATS["steel_raw"], bev=(0.02, 1)))

    # 端门 + 门锁杆（后端）
    for sy in (1, -1):
        parts.append(cub((0.05, W / 2 - 0.08, H - 0.45), (-L / 2 + 0.04, sy * W / 4, H / 2 + 0.1),
                         m=MATS["steel_paint"]))
    for sy in (1, -1):
        parts.append(cyl(0.035, H - 0.6, 8, (-L / 2 + 0.12, sy * 0.12, H / 2 + 0.1), m=MATS["brass"]))

    merged = join_parts(parts, "container")
    move_origin_bottom(merged)
    return merged


# ============================================================================
# 模型 3：厢式货车（truck）—— 9.6m 载货车
# ============================================================================

def build_truck():
    L, W, H = 9.6, 2.5, 3.4
    parts = []

    # 厢体 / 驾驶室
    parts.append(cub((6.6, W, 2.4), (-1.2, 0, 1.55), m=MATS["steel_paint"], bev=(0.05, 2)))
    parts.append(cub((2.6, W * 0.96, 2.0), (4.0, 0, 1.35), m=MATS["steel_paint"], bev=(0.08, 2)))
    # 前脸倾斜段
    parts.append(cub((0.5, W * 0.9, 1.1), (5.35, 0, 1.10), rot=(0, radians(-18), 0),
                     m=MATS["steel_paint"], bev=(0.06, 2)))
    # 挡风玻璃（嵌在驾驶室前脸内，不是立在车顶上）
    parts.append(cub((0.10, W * 0.82, 0.75), (5.27, 0, 1.88), rot=(0, radians(-20), 0), m=MATS["glass"]))
    # 底盘 / 保险杠 / 后视镜
    parts.append(cub((L - 0.6, 0.9, 0.25), (0, 0, 0.55), m=MATS["steel_raw"], bev=(0.03, 1)))
    parts.append(cub((0.35, W * 0.98, 0.4), (5.5, 0, 0.62), m=MATS["steel_raw"], bev=(0.05, 2)))
    for sy in (1, -1):
        parts.append(cub((0.12, 0.3, 0.22), (4.85, sy * (W / 2 + 0.18), 1.95), m=MATS["steel_raw"], bev=(0.03, 1)))

    # 车轮：前 2 后 4（圆柱沿 X 轴：绕 Y 转 90°）
    for ax in (3.9, -2.2, -3.5):
        for sy in (1, -1):
            parts.append(cyl(0.52, 0.32, 24, (ax, sy * (W / 2 - 0.05), 0.52),
                             rot=(pi / 2, 0, 0), m=MATS["rubber"]))
            parts.append(cyl(0.26, 0.34, 16, (ax, sy * (W / 2 - 0.05), 0.52),
                             rot=(pi / 2, 0, 0), m=MATS["hub"]))

    # —— v0.8 精度补充：厢体竖向加强筋（货车厢侧最醒目的识别特征）——
    for i in range(9):
        x = -4.3 + i * 0.86
        for sy in (1, -1):
            parts.append(cub((0.09, 0.06, 2.28), (x, sy * (W / 2 + 0.02), 1.55),
                             m=MATS["steel_raw"]))
    # 厢体上下边梁
    for dz in (1.18, -1.18):
        parts.append(cub((6.62, W + 0.06, 0.10), (-1.2, 0, 1.55 + dz), m=MATS["steel_raw"]))
    # 车顶导流罩（驾驶室顶上的斜面整流罩）
    parts.append(cub((2.20, W * 0.94, 0.55), (3.55, 0, 3.05),
                     rot=(0, radians(-14), 0), m=MATS["steel_paint"], bev=(0.07, 2)))
    # 前照灯 ×2 + 保险杠拖钩
    for sy in (1, -1):
        parts.append(cub((0.14, 0.30, 0.22), (5.62, sy * 0.82, 0.88), m=MATS["brass"], bev=(0.03, 1)))
    # 车门（凹进的轮廓线）+ 门把手 + 登车踏板
    for sy in (1, -1):
        parts.append(cub((0.05, 0.90, 1.30), (3.70, sy * (W / 2 + 0.015), 1.42),
                         m=MATS["steel_raw"]))
        parts.append(cub((0.06, 0.22, 0.07), (4.28, sy * (W / 2 + 0.05), 1.50), m=MATS["brass"]))
        parts.append(cub((0.42, 0.26, 0.06), (4.10, sy * (W / 2 + 0.16), 0.72), m=MATS["steel_raw"]))
    # 侧面防护栏（厢体下方，法规件）
    for sy in (1, -1):
        parts.append(cub((5.60, 0.06, 0.42), (-1.4, sy * (W / 2 + 0.12), 0.72), m=MATS["steel_raw"]))
    # 尾部爬梯
    for sy in (1, -1):
        parts.append(cyl(0.035, 2.20, 6, (-4.52, sy * 0.30, 1.55), m=MATS["steel_raw"]))
    for i in range(6):
        parts.append(cyl(0.028, 0.62, 6, (-4.52, 0, 0.62 + i * 0.38),
                         rot=(0, 0, pi / 2), m=MATS["steel_raw"]))

    merged = join_parts(parts, "truck")
    move_origin_bottom(merged)
    return merged


# ============================================================================
# 模型 4：筒仓（silo）—— 锥底卸料 + 环箍 + 支撑腿
# ============================================================================

def build_silo(diameter=8.0, height=18.0):
    r = diameter / 2.0
    parts = []
    seg = max(32, min(56, int(diameter * 1.8)))

    # 筒体（从锥底之上开始）
    base_h = 3.0
    parts.append(cyl(r, height, seg, (0, 0, base_h + height / 2), m=MATS["galvanized"], bev=(0.015, 1)))
    # 锥底卸料斗
    parts.append(cone(r, 0.45, base_h, seg, (0, 0, base_h / 2), m=MATS["galvanized"]))
    # 卸料口
    parts.append(cyl(0.45, 0.6, 16, (0, 0, -0.1), m=MATS["steel_raw"]))
    # 顶盖
    parts.append(cone(r + 0.15, r, 1.2, seg, (0, 0, base_h + height + 0.6), m=MATS["steel_paint"], bev=(0.02, 2)))
    # 环箍（间距 ~4.5m）
    n_hoop = max(3, int(height / 4.5))
    for i in range(n_hoop):
        hz = base_h + height * (0.08 + 0.86 * i / max(1, n_hoop - 1))
        parts.append(torus(r + 0.03, 0.05, 40, 6, (0, 0, hz), MATS["galvanized"]))
    # 支撑腿
    n_leg = max(4, int(diameter / 3.0))
    for i in range(n_leg):
        a = 2 * pi * i / n_leg
        parts.append(cyl(0.14, base_h, 8, (r * 0.8 * cos(a), r * 0.8 * sin(a), base_h / 2),
                         m=MATS["steel_raw"]))

    merged = join_parts(parts, "silo")
    move_origin_bottom(merged)
    return merged


# ============================================================================
# 模型 5：叉车（forklift）—— 3.5t 内燃平衡重式
# 仓库/装卸区最有辨识度的移动设备，缺了它场景就"没有人干活"
# ============================================================================

def build_forklift():
    """坐标约定：+X 车头（货叉）/ -X 车尾（配重）；Y 车宽；Z 高度（原点在轮胎接地面）"""
    parts = []
    W = 1.28

    # 底盘 + 前桥凸起
    parts.append(cub((2.30, W, 0.34), (-0.25, 0, 0.62), m=MATS["steel_paint"], bev=(0.05, 2)))
    parts.append(cub((0.70, W * 0.96, 0.30), (0.62, 0, 0.82), m=MATS["steel_paint"], bev=(0.05, 2)))
    # 后配重：平衡重叉车最醒目的识别特征——车尾一整块厚重铸铁，大倒角
    parts.append(cub((0.86, W, 0.86), (-1.28, 0, 0.86), m=MATS["steel_raw"], bev=(0.12, 3)))
    # 发动机罩
    parts.append(cub((1.30, W * 0.92, 0.50), (-0.30, 0, 1.03), m=MATS["steel_paint"], bev=(0.06, 2)))
    # 座椅坐垫 + 靠背
    parts.append(cub((0.44, 0.48, 0.13), (-0.70, 0, 1.32), m=MATS["rubber"]))
    parts.append(cub((0.13, 0.48, 0.44), (-0.94, 0, 1.53), m=MATS["steel_raw"], bev=(0.03, 1)))
    # 转向柱 + 方向盘（盘面竖直略后倾）
    parts.append(cyl(0.035, 0.34, 10, (0.05, 0, 1.30), rot=(0, radians(-58), 0), m=MATS["steel_raw"]))
    parts.append(torus(0.16, 0.028, 22, 8, (0.24, 0, 1.52), MATS["rubber"],
                       rot=(radians(-18), radians(90), 0)))

    # 护顶架：4 立柱 + 顶框 + 栅格
    for sx in (0.95, -0.05):
        for sy in (1, -1):
            parts.append(cyl(0.045, 1.15, 8, (sx, sy * (W / 2 - 0.08), 1.85), m=MATS["steel_raw"]))
    for sy in (1, -1):
        parts.append(cub((1.15, 0.07, 0.07), (0.45, sy * (W / 2 - 0.06), 2.42), m=MATS["steel_raw"]))
    for sx in (1.02, -0.12):
        parts.append(cub((0.07, W - 0.10, 0.07), (sx, 0, 2.42), m=MATS["steel_raw"]))
    for i in range(3):
        parts.append(cub((0.05, W - 0.14, 0.04), (0.15 + i * 0.30, 0, 2.40), m=MATS["steel_raw"]))

    # 门架 mast：外立柱 + 内立柱 + 上下横梁 + 倾斜缸
    for sy in (1, -1):
        parts.append(cub((0.13, 0.11, 2.00), (1.06, sy * 0.44, 1.10), m=MATS["steel_raw"], bev=(0.02, 1)))
        parts.append(cub((0.09, 0.08, 1.70), (1.06, sy * 0.28, 0.95), m=MATS["galvanized"]))
    parts.append(cub((0.10, 1.00, 0.16), (1.06, 0, 2.05), m=MATS["steel_raw"]))
    parts.append(cub((0.08, 0.95, 0.12), (1.06, 0, 0.35), m=MATS["steel_raw"]))
    for sy in (1, -1):
        parts.append(cyl(0.05, 0.75, 8, (0.72, sy * 0.40, 0.95),
                         rot=(0, radians(28), 0), m=MATS["galvanized"]))

    # 挡货架 + 货叉（竖直段 + 水平段）
    parts.append(cub((0.06, 1.02, 0.60), (1.18, 0, 0.62), m=MATS["steel_raw"]))
    for sy in (1, -1):
        parts.append(cub((0.06, 0.14, 0.62), (1.22, sy * 0.32, 0.36), m=MATS["galvanized"]))
        parts.append(cub((1.10, 0.14, 0.05), (1.78, sy * 0.32, 0.08), m=MATS["galvanized"]))

    # 车轮：前轮大（驱动）/ 后轮小（转向）+ 轮毂
    for ax, rr, ww in ((0.62, 0.36, 0.24), (-1.05, 0.27, 0.18)):
        for sy in (1, -1):
            parts.append(cyl(rr, ww, 26, (ax, sy * (W / 2 - 0.06), rr),
                             rot=(pi / 2, 0, 0), m=MATS["rubber"]))
            parts.append(cyl(rr * 0.52, ww + 0.02, 14, (ax, sy * (W / 2 - 0.06), rr),
                             rot=(pi / 2, 0, 0), m=MATS["hub"]))

    merged = join_parts(parts, "forklift")
    move_origin_bottom(merged)
    return merged


# ============================================================================
# 模型 6：龙门吊（gantry）—— 轨道式门式起重机
# 堆场/装卸区体量最大的设备，撑起整个场景的"工业尺度感"
# ============================================================================

def build_gantry(span=26.0, height=14.0):
    """跨距沿 X（span），大车行走沿 Y；原点在轨道面"""
    parts = []
    half = span / 2.0
    leg_h = height - 1.6          # 支腿高（主梁中心以下）
    beam_z = height                # 主梁中心高

    # 主梁（双箱梁）
    for sy in (1, -1):
        parts.append(cub((span + 1.6, 0.85, 1.50), (0, sy * 2.30, beam_z),
                         m=MATS["steel_paint"], bev=(0.06, 2)))
    # 端梁（连接双主梁两端）
    for sx in (1, -1):
        parts.append(cub((1.10, 5.45, 1.20), (sx * half, 0, beam_z),
                         m=MATS["steel_paint"], bev=(0.05, 2)))
    # 主梁腹板竖筋（箱梁侧面的加劲肋，远景也能读出结构感）
    for i in range(16):
        x = -half + 0.8 + i * (span - 1.6) / 15.0
        for sy in (1, -1):
            parts.append(cub((0.10, 0.06, 1.42), (x, sy * (2.30 + 0.45), beam_z), m=MATS["steel_raw"]))

    # 走台 + 栏杆（主梁一侧）
    parts.append(cub((span - 1.0, 1.10, 0.08), (0, 3.60, beam_z + 0.80), m=MATS["steel_raw"]))
    for i in range(14):
        x = -half + 0.9 + i * (span - 1.8) / 13.0
        parts.append(cyl(0.035, 1.10, 6, (x, 4.08, beam_z + 1.32), m=MATS["steel_raw"]))
    for dz in (1.30, 0.80):
        parts.append(cub((span - 1.0, 0.05, 0.05), (0, 4.08, beam_z + dz), m=MATS["steel_raw"]))

    # 支腿：每侧两条，形成"门"
    for sx in (1, -1):
        for sy in (1, -1):
            parts.append(cub((0.90, 0.90, leg_h), (sx * half, sy * 2.30, leg_h / 2),
                             m=MATS["steel_paint"], bev=(0.05, 2)))
        # 支腿间联系梁
        parts.append(cub((0.70, 4.60, 0.70), (sx * half, 0, leg_h * 0.42),
                         m=MATS["steel_paint"], bev=(0.04, 2)))
        # 支腿斜撑（A 字感）
        parts.append(cub((0.55, 0.55, 6.6), (sx * half, 0, leg_h * 0.72),
                         rot=(radians(26), 0, 0), m=MATS["steel_raw"]))

    # 大车走行箱 + 走行轮（轴沿 X）
    for sx in (1, -1):
        for sy in (1, -1):
            parts.append(cub((1.60, 1.10, 0.90), (sx * half, sy * 2.30, 0.45),
                             m=MATS["steel_raw"], bev=(0.04, 1)))
            parts.append(cyl(0.45, 0.28, 18, (sx * half, sy * 2.30, 0.45),
                             rot=(0, pi / 2, 0), m=MATS["rubber"]))

    # 小车 + 司机室 + 窗
    parts.append(cub((3.20, 4.20, 0.90), (2.0, 0, beam_z + 1.05),
                     m=MATS["steel_paint"], bev=(0.05, 2)))
    parts.append(cub((1.40, 1.50, 1.90), (2.0, 2.10, beam_z - 0.20),
                     m=MATS["steel_paint"], bev=(0.06, 2)))
    parts.append(cub((0.10, 1.20, 1.00), (2.74, 2.10, beam_z - 0.10), m=MATS["glass"]))

    # 起升钢丝绳 ×4 + 吊具（伸缩式集装箱吊具）
    sp_z = beam_z - 4.6
    for dx in (1, -1):
        for dy in (1, -1):
            parts.append(cyl(0.03, 4.2, 6, (2.0 + dx * 1.30, dy * 1.60, sp_z + 2.30),
                             m=MATS["steel_raw"]))
    parts.append(cub((6.20, 0.55, 0.45), (2.0, 0, sp_z), m=MATS["galvanized"], bev=(0.03, 1)))
    parts.append(cub((0.70, 0.70, 0.60), (2.0, 0, sp_z + 0.45), m=MATS["steel_paint"]))
    for dx in (1, -1):
        parts.append(cub((0.20, 0.20, 0.30), (2.0 + dx * 2.95, 0, sp_z - 0.30), m=MATS["steel_raw"]))

    merged = join_parts(parts, "gantry")
    move_origin_bottom(merged)
    return merged


# ============================================================================
# 主流程
# ============================================================================

SPECS = {
    "tank":      {"diameter": 32.0, "height": 26.0},
    "silo":      {"diameter": 24.0, "height": 38.0},
    "container": {},
    "truck":     {},
    "forklift":  {},
    "gantry":    {"span": 26.0, "height": 14.0},
}

BUILDERS = {
    "tank":      lambda: build_tank(**SPECS["tank"]),
    "container": lambda: build_container(),
    "truck":     lambda: build_truck(),
    "silo":      lambda: build_silo(**SPECS["silo"]),
    "forklift":  lambda: build_forklift(),
    "gantry":    lambda: build_gantry(**SPECS["gantry"]),
}


def main():
    argv = sys.argv
    if "--" not in argv:
        print("用法: blender --background --python gen_models_blender.py -- --out <dir> [--models a,b] [--size tank:d,h]")
        return
    args = argv[argv.index("--") + 1:]

    out_dir = "D:/tmp/twin_models"
    models = list(BUILDERS.keys())
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--out" and i + 1 < len(args):
            out_dir = args[i + 1]; i += 1
        elif a == "--models" and i + 1 < len(args):
            models = [x.strip() for x in args[i + 1].split(",") if x.strip() in BUILDERS]; i += 1
        elif a == "--size" and i + 1 < len(args):
            nm, _, val = args[i + 1].partition(":")
            nm = nm.strip()
            if nm in SPECS:
                nums = [float(x) for x in val.split(",") if x.strip()]
                if nm in ("tank", "silo") and len(nums) >= 2:
                    SPECS[nm] = {"diameter": nums[0], "height": nums[1]}
                    print("  规格覆盖 %s -> Ø%.1f × H%.1f" % (nm, nums[0], nums[1]))
            i += 1
        i += 1

    os.makedirs(out_dir, exist_ok=True)
    print("=== gen_models_blender ===")
    print("输出目录:", out_dir)
    print("模型:", models)

    for name in models:
        reset_scene()
        build_materials()
        obj = BUILDERS[name]()
        apply_modifiers(obj)

        nv = len(obj.data.vertices)
        nf = len(obj.data.polygons)
        bbox = obj.bound_box
        xs = [v[0] for v in bbox]; ys = [v[1] for v in bbox]; zs = [v[2] for v in bbox]
        size = (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))

        path = os.path.join(out_dir, "bl-%s.glb" % name)
        bpy.ops.export_scene.gltf(filepath=path, export_format='GLB',
                                  export_apply=True, export_yup=True,
                                  export_materials='EXPORT')
        kb = os.path.getsize(path) / 1024.0
        print("[OK] %-10s 面=%-6d 顶点=%-6d 尺寸=%.2f×%.2f×%.2f  %.0fKB"
              % (name, nf, nv, size[0], size[1], size[2], kb))

    print("=== 完成 ===")


if __name__ == "__main__":
    main()
