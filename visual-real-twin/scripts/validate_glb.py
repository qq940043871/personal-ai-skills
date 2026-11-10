#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
validate_glb.py —— GLB 体检（纯标准库，解析二进制，任意 python 可跑）

检查项：
1. GLB 头与 chunk 结构合法（magic/version/length，JSON+BIN chunk）
2. extensionsRequired 是否含 KHR_draco_mesh_compression（内联链路要求 Draco）
3. 面数预算（默认 ≤100,000；程序化单模型规范 ≤50,000）
4. 贴图预算（单张贴图 bufferView ≤ 上限；最长边无法从二进制直接读，按字节数近似把关）
5. 体积预算：内联模式默认 ≤2MB（base64 后 ~2.7MB，进单文件 HTML）；
   --standalone 外置模式 ≤5MB
6. POSITION accessor 的 min/max → 模型包围盒尺寸（米，Y-up），用于验证米制尺度

exit 0 = PASS，exit 1 = FAIL。
"""
import json
import struct
import sys
import argparse
import os

MAGIC = 0x46546C67  # 'glTF'
CHUNK_JSON = 0x4E4F534A
CHUNK_BIN = 0x004E4942


def parse_glb(path):
    with open(path, "rb") as f:
        data = f.read()
    if len(data) < 12:
        raise ValueError("文件太小，不是 GLB")
    magic, version, length = struct.unpack_from("<III", data, 0)
    if magic != MAGIC:
        raise ValueError("magic 不是 glTF（可能是 .gltf 文本文件，先转单文件 GLB）")
    if version != 2:
        raise ValueError("glTF 版本 %d 不支持（需 2）" % version)
    if length != len(data):
        raise ValueError("header.length=%d 与实际 %d 不符（文件损坏）" % (length, len(data)))

    off, chunks = 12, {}
    while off + 8 <= len(data):
        clen, ctype = struct.unpack_from("<II", data, off)
        chunks[ctype] = data[off + 8: off + 8 + clen]
        off += 8 + clen
    if CHUNK_JSON not in chunks:
        raise ValueError("缺 JSON chunk")
    gltf = json.loads(chunks[CHUNK_JSON].decode("utf-8"))
    return gltf, chunks.get(CHUNK_BIN, b""), len(data)


def face_count(gltf):
    total = 0
    for mesh in gltf.get("meshes", []):
        for prim in mesh.get("primitives", []):
            mode = prim.get("mode", 4)
            if mode != 4:  # 只统计三角形
                continue
            idx = prim.get("indices")
            if idx is not None:
                total += gltf["accessors"][idx].get("count", 0) // 3
            else:
                pos = prim.get("attributes", {}).get("POSITION")
                if pos is not None:
                    total += gltf["accessors"][pos].get("count", 0) // 3
    return total


def bbox_meters(gltf):
    """用 POSITION accessor 的 min/max 求包围盒（glTF 是 Y-up，米）"""
    lo = [1e9] * 3
    hi = [-1e9] * 3
    for mesh in gltf.get("meshes", []):
        for prim in mesh.get("primitives", []):
            pos = prim.get("attributes", {}).get("POSITION")
            if pos is None:
                continue
            acc = gltf["accessors"][pos]
            mn, mx = acc.get("min"), acc.get("max")
            if mn and mx:
                for i in range(3):
                    lo[i] = min(lo[i], mn[i])
                    hi[i] = max(hi[i], mx[i])
    if lo[0] > 1e8:
        return None
    return [round(hi[i] - lo[i], 2) for i in range(3)]  # glTF Y-up: [宽, 高, 深]


def texture_stats(gltf, bin_chunk):
    out = []
    for img in gltf.get("images", []):
        bv = img.get("bufferView")
        size = gltf["bufferViews"][bv].get("byteLength", 0) if bv is not None else 0
        out.append({"name": img.get("name", "?"), "mime": img.get("mimeType", "?"),
                    "bytes": size})
    return out


def main():
    ap = argparse.ArgumentParser(description="GLB 体检")
    ap.add_argument("glb")
    ap.add_argument("--max-faces", type=int, default=100000)
    ap.add_argument("--max-mb", type=float, default=None,
                    help="体积上限 MB；默认内联 2.0，--standalone 时 5.0")
    ap.add_argument("--standalone", action="store_true",
                    help="外置服务模式（阈值放宽到 5MB）")
    ap.add_argument("--require-draco", action="store_true", default=True)
    args = ap.parse_args()
    if not os.path.exists(args.glb):
        sys.exit("找不到文件: %s" % args.glb)
    max_mb = args.max_mb or (5.0 if args.standalone else 2.0)

    problems, notes = [], []
    try:
        gltf, bin_chunk, total = parse_glb(args.glb)
    except ValueError as e:
        print("RESULT: FAIL —— %s" % e)
        return 1

    faces = face_count(gltf)
    req = gltf.get("extensionsRequired", [])
    has_draco = "KHR_draco_mesh_compression" in req
    texs = texture_stats(gltf, bin_chunk)
    size_mb = total / 1024.0 / 1024.0
    bbox = bbox_meters(gltf)

    if args.require_draco and not has_draco:
        problems.append("未启用 Draco（KHR_draco_mesh_compression 不在 extensionsRequired）——重新导出加 --draco")
    if faces > args.max_faces:
        problems.append("面数 %d > 预算 %d（调 export_webgl.py --decimate）" % (faces, args.max_faces))
    if size_mb > max_mb:
        problems.append("体积 %.2fMB > 预算 %.1fMB%s" % (
            size_mb, max_mb, "（外置模式）" if args.standalone else "（内联模式）"))
    big_tex = [t for t in texs if t["bytes"] > 4 * 1024 * 1024]
    if big_tex:
        problems.append("贴图过大: %s（调 --max-tex）"
                        % ", ".join("%s(%dKB)" % (t["name"], t["bytes"] // 1024) for t in big_tex))
    if bbox:
        w, h, d = bbox
        longest = max(w, h, d)
        if longest > 500:
            problems.append("包围盒 %.0fm 疑似单位错了（m→mm？），米制实物不该超过 500m" % longest)
        elif longest < 0.1:
            problems.append("包围盒 %.2fm 疑似单位错了（m→km？）或模型过小" % longest)

    print("文件        :", args.glb)
    print("体积        : %.2f MB（预算 %.1f）" % (size_mb, max_mb))
    print("面数        : %d（预算 %d）" % (faces, args.max_faces))
    print("Draco       : %s" % ("是" if has_draco else "否"))
    print("贴图        : %d 张%s" % (len(texs), ("，共 %dKB" % (sum(t['bytes'] for t in texs) // 1024)) if texs else "（无贴图，材质色）"))
    print("包围盒(W,H,D): %s 米（glTF Y-up，落地时视觉高度=H）" % bbox)
    print("扩展要求    : %s" % (req or "无"))
    for n in notes:
        print("note        :", n)
    if problems:
        print()
        for p in problems:
            print("FAIL: %s" % p)
        print("RESULT: FAIL")
        return 1
    print()
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
