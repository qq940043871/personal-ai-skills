#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
visual-echarts-dashboard / scaffold.py

把行业预设 + JSON 配置，落成一份可直接打开的大屏原型页面。

用法：
  python scaffold.py --list
  python scaffold.py --industry bulk  --title "XX港务驾驶舱" --out ./dash.html
  python scaffold.py --industry gov   --resolution 3840x2160 --out ./gov.html
  python scaffold.py --industry warehouse --dump-config wh.json   # 导出配置去改
  python scaffold.py --config wh.json  --out ./wh.html            # 回填生成

配置是「片段覆盖」：只写要改的字段，其余走骨架默认值（骨架内做深度合并）。
"""
import argparse, io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKELETON = os.path.normpath(os.path.join(HERE, "..", "assets", "dashboard-skeleton.html"))
ANCHOR = "<!-- __DASH_CONFIG__"
IMG_DIRNAME = "img"
CHINA_GEO = os.path.normpath(os.path.join(HERE, "..", "assets", "map", "china.json"))
_MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


def inline_images(html, img_dir):
    """把 img/xxx.jpg 替换成 data URI —— 保证产出的 HTML 单文件可带走、双击即开"""
    import base64, re
    used = []

    def sub(m):
        rel = m.group(0)
        p = os.path.join(img_dir, os.path.basename(rel))
        if not os.path.exists(p):
            return rel                                   # 找不到就保持原样，页面自动回退纯色
        ext = os.path.splitext(p)[1].lower()
        with open(p, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        used.append(os.path.basename(rel))
        return "data:%s;base64,%s" % (_MIME.get(ext, "application/octet-stream"), b64)

    return re.sub(r"img/[A-Za-z0-9._-]+", sub, html), used


def inline_china_geo(html):
    """china 地图模式：把内置省界 GeoJSON 内联成 window.__CHINA_GEO__ —— 保持单文件可带走"""
    if not os.path.exists(CHINA_GEO):
        return html, 0
    with io.open(CHINA_GEO, "r", encoding="utf-8") as f:
        geo = f.read()
    inj = '<script id="china-geo">\nwindow.__CHINA_GEO__ = ' + geo + ';\n</script>\n'
    return html.replace(ANCHOR, inj + ANCHOR, 1), os.path.getsize(CHINA_GEO)


def screen(w, h, fit="contain"):
    return {"screen": {"designWidth": w, "designHeight": h, "fit": fit}}


def preset_bulk(title):
    """大宗商品交易场所 / 港口：堆场、罐区、筒仓、装船作业"""
    c = {"meta": {"title": title, "subtitle": "仓储 · 物流 · 交易 · 结算 一体化监控",
                  "industry": "bulk", "dataMode": "mock"}}
    c.update(screen(1920, 1080))
    c["kpis"] = [
        {"label": "在库总量", "value": 486200, "unit": "吨", "trend": 3.2, "level": "normal"},
        {"label": "今日出入库", "value": 72400, "unit": "吨", "trend": -1.8, "level": "normal"},
        {"label": "今日成交额", "value": 3.26, "unit": "亿元", "trend": 5.6, "level": "normal", "fixed": 2},
        {"label": "待处理告警", "value": 7, "unit": "条", "trend": 16.7, "level": "warn"},
        {"label": "车辆在场", "value": 138, "unit": "辆", "trend": 2.1, "level": "normal"},
        {"label": "库存周转率", "value": 4.8, "unit": "次/月", "trend": -0.6, "level": "normal", "fixed": 1}]
    c["map"] = {"mode": "china",
                "hot": ["河北省", "山东省", "江苏省", "上海市", "浙江省", "广东省",
                        "天津市", "辽宁省", "广西壮族自治区", "海南省"],
                "ports": {"天津港": [117.70, 38.98], "青岛港": [120.32, 36.06],
                          "日照港": [119.55, 35.42], "连云港": [119.19, 34.72],
                          "上海港": [121.49, 31.23], "宁波舟山港": [121.90, 29.93],
                          "广州港": [113.55, 23.10], "北部湾港": [108.35, 21.62]},
                "flows": [{"from": "青岛港", "to": "天津港", "value": 820},
                          {"from": "日照港", "to": "青岛港", "value": 430},
                          {"from": "宁波舟山港", "to": "上海港", "value": 640},
                          {"from": "连云港", "to": "上海港", "value": 380},
                          {"from": "北部湾港", "to": "广州港", "value": 260}]}
    c["alarms"] = [
        {"level": "crit", "text": "2号堆场 堆取料机过载停机", "time": "10:24"},
        {"level": "warn", "text": "液体罐区 T-04 液位 86% 接近上限", "time": "10:11"},
        {"level": "warn", "text": "散粮筒仓 3号 温度 38.5℃ 超阈值", "time": "09:58"},
        {"level": "info", "text": "保税库 出入口闸机离线 5 分钟", "time": "09:36"}]
    c["ticker"] = ["今日到港船舶 <b>6</b> 艘，其中已完船 2 艘",
                   "堆场作业饱和度 <b>78%</b>，建议关注 2 号堆场",
                   "铁矿石现货均价 <b>826</b> 元/吨，环比 +0.8%",
                   "在途货值 <b>3.26</b> 亿元，涉及 41 家会员企业"]
    return c


def preset_warehouse(title):
    """仓储物流企业：多库区、月台、分拣线"""
    c = {"meta": {"title": title, "subtitle": "库区 · 作业 · 订单 · 时效 全链路监控",
                  "industry": "warehouse", "dataMode": "mock"}}
    c.update(screen(1920, 1080))
    c["kpis"] = [
        {"label": "在库件数", "value": 1286400, "unit": "件", "trend": 1.4, "level": "normal"},
        {"label": "今日入库", "value": 86200, "unit": "件", "trend": 4.1, "level": "normal"},
        {"label": "今日出库", "value": 94100, "unit": "件", "trend": 6.8, "level": "normal"},
        {"label": "出库及时率", "value": 97.6, "unit": "%", "trend": -0.5, "level": "normal", "fixed": 1},
        {"label": "异常单量", "value": 12, "unit": "单", "trend": 20.0, "level": "warn"},
        {"label": "库位利用率", "value": 84.2, "unit": "%", "trend": 2.3, "level": "normal", "fixed": 1}]
    c["map"] = {"mode": "china",
                "hot": ["广东省", "浙江省", "江苏省", "山东省", "河南省", "四川省",
                        "湖北省", "上海市", "北京市", "福建省"],
                "ports": {"北京": [116.41, 39.90], "天津": [117.20, 39.13],
                          "郑州": [113.62, 34.75], "西安": [108.95, 34.34],
                          "成都": [104.07, 30.57], "重庆": [106.55, 29.56],
                          "武汉": [114.30, 30.60], "长沙": [112.94, 28.23],
                          "上海": [121.47, 31.23], "广州": [113.26, 23.13]},
                "flows": [{"from": "成都", "to": "重庆", "value": 880},
                          {"from": "武汉", "to": "上海", "value": 720},
                          {"from": "郑州", "to": "北京", "value": 540},
                          {"from": "长沙", "to": "广州", "value": 410}]}
    c["alarms"] = [
        {"level": "crit", "text": "自动分拣线 2号滑道 卡件停机", "time": "10:31"},
        {"level": "warn", "text": "C区 冷藏库 温度 -16.2℃ 接近上限", "time": "10:18"},
        {"level": "warn", "text": "D区 危品库 温湿度采集器离线", "time": "09:47"},
        {"level": "info", "text": "1号月台 排队车辆 9 辆，建议增开道口", "time": "09:22"}]
    c["ticker"] = ["今日订单 <b>18,420</b> 单，已发货 15,860 单",
                   "自动分拣线效率 <b>2,400</b> 件/小时",
                   "出库及时率 <b>97.6%</b>，低于目标 0.4 个百分点",
                   "在途运单 <b>1,286</b> 票，涉及 32 条线路"]
    return c


def preset_gov(title):
    """政府监管：辖区、企业、交易合规线索"""
    c = {"meta": {"title": title, "subtitle": "企业监管 · 交易合规 · 风险线索 一屏统览",
                  "industry": "gov", "dataMode": "mock"}}
    c.update(screen(1920, 1080))
    c["kpis"] = [
        {"label": "在册企业", "value": 2860, "unit": "家", "trend": 0.8, "level": "normal"},
        {"label": "今日交易额", "value": 9.84, "unit": "亿元", "trend": 2.6, "level": "normal", "fixed": 2},
        {"label": "异常线索", "value": 23, "unit": "条", "trend": 15.0, "level": "warn"},
        {"label": "待核查事项", "value": 9, "unit": "项", "trend": -10.0, "level": "normal"},
        {"label": "在线监测点位", "value": 742, "unit": "个", "trend": 1.2, "level": "normal"},
        {"label": "合规率", "value": 98.4, "unit": "%", "trend": 0.3, "level": "normal", "fixed": 1}]
    c["map"] = {"mode": "china",
                "hot": ["北京市", "上海市", "广东省", "江苏省", "浙江省", "山东省",
                        "四川省", "湖北省", "福建省", "辽宁省"],
                "ports": {"北京": [116.41, 39.90], "上海": [121.47, 31.23],
                          "广州": [113.26, 23.13], "深圳": [114.06, 22.55],
                          "成都": [104.07, 30.57], "武汉": [114.30, 30.60],
                          "西安": [108.95, 34.34], "沈阳": [123.43, 41.80]},
                "flows": [{"from": "深圳", "to": "北京", "value": 760},
                          {"from": "上海", "to": "北京", "value": 640},
                          {"from": "成都", "to": "西安", "value": 520},
                          {"from": "广州", "to": "武汉", "value": 430}]}
    c["alarms"] = [
        {"level": "crit", "text": "某企业 关联方交易占比 82%，触发异常线索", "time": "10:26"},
        {"level": "warn", "text": "西部辖区 某仓库 未按规上传库存台账", "time": "10:05"},
        {"level": "warn", "text": "口岸查验区 视频监测点位 3 个离线", "time": "09:44"},
        {"level": "info", "text": "今日新增备案合同 126 份", "time": "09:10"}]
    c["ticker"] = ["今日新增备案企业 <b>12</b> 家",
                   "异常线索核查完成率 <b>86%</b>，剩余 9 项",
                   "重点监控品类：<b>铁矿石 / 乙二醇 / 玉米</b>",
                   "本周双随机抽查 <b>48</b> 家，已覆盖 82%"]
    return c


PRESETS = {"bulk": preset_bulk, "warehouse": preset_warehouse, "gov": preset_gov}


def main():
    ap = argparse.ArgumentParser(description="生成 ECharts 数据大屏原型页面")
    ap.add_argument("--industry", default="bulk", help="行业预设 bulk|warehouse|gov")
    ap.add_argument("--title", default=None, help="大屏标题")
    ap.add_argument("--config", default=None, help="外部 JSON 配置（覆盖行业预设）")
    ap.add_argument("--resolution", default=None, help="设计分辨率，如 1920x1080 / 2560x1440 / 3840x2160")
    ap.add_argument("--fit", default=None, help="缩放策略 contain|cover|stretch")
    ap.add_argument("--out", default=None, help="输出 HTML 路径")
    ap.add_argument("--dump-config", default=None, help="只导出配置 JSON，不生成页面")
    ap.add_argument("--list", action="store_true", help="列出行业预设")
    ap.add_argument("--skeleton", default=SKELETON, help="骨架 HTML 路径")
    ap.add_argument("--no-inline", action="store_true",
                    help="不把底图/纹理内联成 data URI（需把骨架同目录的 img/ 一起复制，否则回退纯色）")
    args = ap.parse_args()

    if args.list:
        for k, v in PRESETS.items():
            print("%-11s %s" % (k, v("示例").get("meta", {}).get("subtitle", "")))
        return

    if args.config:
        with io.open(args.config, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    else:
        fn = PRESETS.get(args.industry)
        if not fn:
            sys.exit("未知行业预设：%s（可选：%s）" % (args.industry, ", ".join(PRESETS)))
        cfg = fn(args.title or fn("示例")["meta"]["title"])

    if args.title:
        cfg.setdefault("meta", {})["title"] = args.title
    if args.resolution:
        try:
            w, h = [int(x) for x in args.resolution.lower().replace("*", "x").split("x")]
            cfg.setdefault("screen", {}).update({"designWidth": w, "designHeight": h})
        except Exception:
            sys.exit("--resolution 格式应为 1920x1080")
    if args.fit:
        cfg.setdefault("screen", {})["fit"] = args.fit

    if args.dump_config:
        with io.open(args.dump_config, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        print("配置已导出：%s（改完用 --config 回填）" % args.dump_config)
        return

    if not args.out:
        sys.exit("缺少 --out（或改用 --dump-config）")
    if not os.path.exists(args.skeleton):
        sys.exit("找不到骨架文件：%s" % args.skeleton)

    with io.open(args.skeleton, "r", encoding="utf-8") as f:
        html = f.read()
    if ANCHOR not in html:
        sys.exit("骨架结构异常：未找到配置注入点 __DASH_CONFIG__")

    script = ('<script id="dash-config">\nwindow.__DASH_CONFIG__ = ' +
              json.dumps(cfg, ensure_ascii=False, indent=2) + ';\n</script>\n')
    html = html.replace(ANCHOR, script + ANCHOR, 1)

    if not args.no_inline:
        html, used = inline_images(html, os.path.join(os.path.dirname(args.skeleton), IMG_DIRNAME))
        print("已内联底图 %d 张：%s" % (len(used), ", ".join(used) if used else "（未找到 img/ 目录）"))
        html, geo_sz = inline_china_geo(html)
        if geo_sz:
            print("已内联中国省界底图：%.1f KB（35 省级单位含南海诸岛）" % (geo_sz / 1024.0))
    else:
        print("未内联底图：请把骨架同目录的 img/ 一并复制，否则页面回退到纯色背景")
        html, geo_sz = inline_china_geo(html)
        if geo_sz:
            print("已内联中国省界底图：%.1f KB" % (geo_sz / 1024.0))

    out = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with io.open(out, "w", encoding="utf-8") as f:
        f.write(html)
    panels = sum(len(cfg.get(k, [])) for k in ("left", "center", "right")) if "layout" in cfg else -1
    print("大屏已生成：%s" % out)
    print("行业：%s | 设计分辨率：%sx%s | KPI：%d | 地图：%s" % (
        cfg.get("meta", {}).get("industry"), cfg.get("screen", {}).get("designWidth"),
        cfg.get("screen", {}).get("designHeight"), len(cfg.get("kpis", [])),
        ("china（重点省 %d 个）" % len(cfg.get("map", {}).get("hot", []))) if cfg.get("map", {}).get("mode") == "china"
        else cfg.get("map", {}).get("mode", "schematic")))
    print("下一步：双击打开（或 python -m http.server 8000），按 F11 进全屏演示")


if __name__ == "__main__":
    main()
