#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
simplify_china.py —— 把 DataV 中国省界 GeoJSON 简化成可内联进单文件 HTML 的精简版。

输入 : china_raw.json（DataV areas_v3 100000_full，约 580KB）
输出 : assets/map/china.json（目标 < 300KB）

处理：
1. shapely simplify 容差 0.04 度（1080p 大屏视觉无损）
2. properties 只留 name / adcode / centroid / center
3. 去掉非 Feature 顶层字段
4. 主图剔除三沙岛礁：海南省 MultiPolygon 中整体位于 MAIN_MIN_LAT 以南的岛环直接丢弃，
   避免主图 bbox 被拉成竖条（含三沙时横纵比仅 1.24，宽屏面板放不下）；
   九段线与三沙岛礁由「南海诸岛」feature 完整保留，大屏上以右下角插图呈现（国标画法，要素不丢）
"""
import json, os, sys
from shapely.geometry import shape, mapping

RAW = "D:/tmp/china_raw.json"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "map", "china.json")
TOL = 0.04
MAIN_MIN_LAT = 18.5   # 主图岛环保留下限：整体在该线以南的岛环（三沙）不进主图


def simplify_geom(geom, tol):
    """MultiPolygon/Polygon 逐部件 simplify；空几何原样返回"""
    g = shape(geom)
    if g.is_empty:
        return geom
    g = g.simplify(tol, preserve_topology=True)
    return mapping(g)


def trim_south_islands(geom, min_lat):
    """丢掉 MultiPolygon 中整体位于 min_lat 以南的岛环（海南省的三沙岛礁）。
    返回 (新几何, 是否有裁剪)。单 Polygon 与跨线部件不动。"""
    if geom.get("type") != "MultiPolygon":
        return geom, False
    polys = geom["coordinates"]
    keep = [p for p in polys if max(pt[1] for pt in p[0]) >= min_lat]
    if not keep:                              # 理论上不会发生：全被滤掉则保留最大部件
        keep = [max(polys, key=lambda p: len(p[0]))]
    if len(keep) == len(polys):
        return geom, False
    return {"type": "MultiPolygon", "coordinates": keep}, True


def main():
    with open(RAW, "r", encoding="utf-8") as f:
        data = json.load(f)
    feats = []
    for ft in data.get("features", []):
        p = ft.get("properties", {}) or {}
        name = p.get("name")
        if not name:
            # 100000_JD = 南海诸岛（国界线组成部分，合规必须保留，需命名否则 ECharts 注册后是空名分区）
            name = "南海诸岛" if str(p.get("adcode", "")).endswith("_JD") else "未命名"
        np_ = {
            "name": name,
            "adcode": p.get("adcode"),
            "centroid": p.get("centroid"),
            "center": p.get("center"),
        }
        geom = ft.get("geometry")
        if not geom:
            continue
        if str(p.get("adcode", "")).endswith("_JD"):
            # 九段线是细长弧线组，simplify 会把线段简化没——原样保留
            feats.append({"type": "Feature", "properties": np_, "geometry": geom})
            continue
        geom = simplify_geom(geom, TOL)
        geom, trimmed = trim_south_islands(geom, MAIN_MIN_LAT)
        if trimmed:
            # 主图不画三沙岛礁（海南的三沙小岛环）， centroid 改按最大部件（海南本岛）重算，
            # 否则 DataV 原始质心被岛礁拽到南海，端口/脉冲点定位会漂
            biggest = max(shape(geom).geoms, key=lambda x: x.area)
            c = biggest.centroid
            np_["centroid"] = [round(c.x, 4), round(c.y, 4)]
        feats.append({"type": "Feature", "properties": np_, "geometry": geom})
    out = {"type": "FeatureCollection", "features": feats}
    os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    sz = os.path.getsize(OUT)
    print("features: %d" % len(feats))
    print("输出: %s (%.1f KB)" % (os.path.abspath(OUT), sz / 1024.0))
    if sz > 320 * 1024:
        print("警告：仍偏大，建议容差调到 0.06")


if __name__ == "__main__":
    main()
