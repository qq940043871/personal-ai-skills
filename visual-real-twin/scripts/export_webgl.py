#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
export_webgl.py —— Blender 批处理导出 Web 优化 GLB（必须用 Blender 自带 Python 跑）

用法（系统 shell，不是 blender 内部）：
    blender --background --python export_webgl.py -- \
        --input scene.blend --out D:/tmp/out/tank.glb \
        [--collection ASSET_TANK-01] [--decimate 0.5] [--max-tex 2048]
        [--draco] [--ground] [--strip-tex]

参数：
  --input FILE      输入：.blend（打开）/ .glb/.gltf/.fbx/.obj（导入优化外部模型）
                    省略 = 操作当前场景（MCP 建模后由 MCP 侧保存的场景走此处时仍建议给 .blend）
  --out FILE        输出 GLB 路径（必填）
  --collection NAME 只导出该集合（建模规范：每个设备一个 ASSET_<id> 集合）
  --decimate R      DECIMATE 比例 0~1（0 或 1 = 不减面；hero 设备建议 0.6~1，bg 远景 0.3）
  --max-tex N       贴图最长边缩到 N 像素（0 = 不处理）
  --strip-tex       删除所有贴图（只留材质颜色，极限压体积用）
  --draco           导出时启用 Draco 网格压缩（Blender 官方构建自带）
  --ground          把导出内容整体落到 z=0（原点底部中心，与姊妹技能资产一致）

设计原则（继承 gen_models_blender.py 的实测坑位）：
- 绝不依赖选中态之外的全局状态；逐对象处理，处理前先应用变换
- 修改器先 apply 再统计/导出，保证面数统计 = 实际导出面数
"""
import bpy
import sys
import os

ARGS = None


def parse_args():
    argv = sys.argv
    if "--" not in argv:
        print("用法: blender --background --python export_webgl.py -- --out x.glb [--input s.blend] ...")
        raise SystemExit(2)
    a = argv[argv.index("--") + 1:]

    def val(flag, default=None):
        if flag in a:
            i = a.index(flag)
            return a[i + 1] if i + 1 < len(a) else default
        return default

    has = lambda flag: flag in a
    return {
        "input": val("--input"),
        "out": val("--out"),
        "collection": val("--collection"),
        "decimate": float(val("--decimate", "1") or 1),
        "max_tex": int(val("--max-tex", "0") or 0),
        "strip_tex": has("--strip-tex"),
        "draco": has("--draco"),
        "ground": has("--ground"),
    }


def load_input(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".blend":
        bpy.ops.wm.open_mainfile(filepath=path)
    elif ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=path)
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=path)
    elif ext == ".obj":
        try:
            bpy.ops.wm.obj_import(filepath=path)      # Blender 4.x
        except AttributeError:
            bpy.ops.import_scene.obj(filepath=path)   # Blender 3.x
    else:
        raise SystemExit("不认识的输入格式: %s" % ext)


def objects_to_export():
    if ARGS["collection"]:
        col = bpy.data.collections.get(ARGS["collection"])
        if not col:
            raise SystemExit("找不到集合: %s" % ARGS["collection"])
        objs = []
        stack = list(col.objects) + [o for c in col.children for o in c.objects]
        seen = set()
        for o in stack:
            if o.name not in seen:
                seen.add(o.name)
                objs.append(o)
        return [o for o in objs if o.type == "MESH"]
    return [o for o in bpy.data.objects if o.type == "MESH"]


def apply_transforms(obj):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)


def apply_decimate(obj, ratio):
    m = obj.modifiers.new("decimate", "DECIMATE")
    m.ratio = max(0.01, min(1.0, ratio))
    bpy.context.view_layer.objects.active = obj
    try:
        bpy.ops.object.modifier_apply(modifier=m.name)
    except Exception as e:
        print("  [warn] 减面失败 %s: %s" % (obj.name, e))


def scale_textures(max_dim):
    n = 0
    for img in bpy.data.images:
        if img.size[0] == 0 or img.source == "GENERATED":
            continue
        w, h = img.size
        longest = max(w, h)
        if longest > max_dim:
            s = max_dim / float(longest)
            try:
                img.scale(max(1, int(w * s)), max(1, int(h * s)))
                n += 1
            except Exception as e:
                print("  [warn] 贴图缩放失败 %s: %s" % (img.name, e))
    return n


def strip_textures():
    n = 0
    for m in bpy.data.materials:
        if not m.use_nodes:
            continue
        for node in list(m.node_tree.nodes):
            if node.type == "TEX_IMAGE":
                for link in list(m.node_tree.links):
                    if link.from_node == node:
                        m.node_tree.links.remove(link)
                m.node_tree.nodes.remove(node)
                n += 1
    return n


def ground_objects(objs):
    """整体落到 z=0，并把包围盒中心移到 x/y 原点（原点底部中心规范）"""
    zs, xs, ys = [], [], []
    for o in objs:
        for c in o.bound_box:
            w = o.matrix_world @ __import__("mathutils").Vector(c)
            xs.append(w.x); ys.append(w.y); zs.append(w.z)
    cx, cy, minz = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, min(zs)
    for o in objs:
        if o.parent is None:
            o.location.x -= cx
            o.location.y -= cy
            o.location.z -= minz
    return len(objs)


def main():
    global ARGS
    ARGS = parse_args()
    if not ARGS["out"]:
        raise SystemExit("--out 必填")
    os.makedirs(os.path.dirname(os.path.abspath(ARGS["out"])) or ".", exist_ok=True)

    if ARGS["input"]:
        load_input(ARGS["input"])

    if ARGS["strip_tex"]:
        print("删除贴图节点: %d" % strip_textures())
    elif ARGS["max_tex"]:
        print("贴图缩放(≤%dpx): %d 张" % (ARGS["max_tex"], scale_textures(ARGS["max_tex"])))

    objs = objects_to_export()
    if not objs:
        raise SystemExit("没有可导出的网格对象")
    for o in objs:
        apply_transforms(o)
        if 0 < ARGS["decimate"] < 1:
            apply_decimate(o, ARGS["decimate"])
    if ARGS["ground"]:
        ground_objects(objs)

    # 隐藏非导出对象（若指定了集合），避免把它们也导进去
    if ARGS["collection"]:
        export_names = {o.name for o in objs}
        for o in bpy.data.objects:
            o.hide_render = o.name not in export_names

    draco = ARGS["draco"]
    try:
        bpy.ops.export_scene.gltf(
            filepath=ARGS["out"], export_format="GLB",
            export_apply=True, export_yup=True, export_materials="EXPORT",
            export_draco_mesh_compression_enable=draco,
            export_draco_compression_level=6,
            use_selection=bool(ARGS["collection"]),
        )
    except TypeError:
        # 旧版 Blender 无 draco 参数 → 降级普通导出
        bpy.ops.export_scene.gltf(filepath=ARGS["out"], export_format="GLB",
                                  export_apply=True, export_yup=True,
                                  use_selection=bool(ARGS["collection"]))
        draco = False

    nv = sum(len(o.data.vertices) for o in objs)
    nf = sum(len(o.data.polygons) for o in objs)
    kb = os.path.getsize(ARGS["out"]) / 1024.0
    print("[OK] %s  对象=%d 面=%d 顶点=%d draco=%s  %.0fKB"
          % (ARGS["out"], len(objs), nf, nv, draco, kb))


if __name__ == "__main__":
    main()
