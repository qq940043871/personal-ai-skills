#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
visual-threejs-scene / scaffold.py

把一个场景预设 + JSON 配置，落成一份可直接打开的数字孪生原型页面。

用法：
  python scaffold.py --scene warehouse --out ./twin.html
  python scaffold.py --scene plant --title "华东炼化厂区" --out ./plant.html
  python scaffold.py --config my-config.json --out ./twin.html
  python scaffold.py --scene bulk --dump-config bulk.json      # 先导出配置去改，再回填
  python scaffold.py --list                                    # 看有哪些预设

参数说明见 SKILL.md「输入参数」章节。
"""
import argparse, io, json, os, re, struct, sys, copy, base64

HERE = os.path.dirname(os.path.abspath(__file__))
SKELETON = os.path.normpath(os.path.join(HERE, "..", "assets", "twin-skeleton.html"))
INJECT_MARK = '<script id="twin-boot">'
THREE_VENDOR_DIRNAME = "three-r160"   # assets/three-r160/ 下的离线引擎模块

# 骨架引擎依赖的全部模块（相对路径导入已改写为裸说明符，见 GLTFLoader.js 注释）
THREE_MODULES = [
    ("three", "three.module.js"),
    ("three/addons/controls/OrbitControls.js", "OrbitControls.js"),
    ("three/addons/environments/RoomEnvironment.js", "RoomEnvironment.js"),
    ("three/addons/geometries/RoundedBoxGeometry.js", "RoundedBoxGeometry.js"),
    ("three/addons/loaders/DRACOLoader.js", "DRACOLoader.js"),
    ("three/addons/loaders/GLTFLoader.js", "GLTFLoader.js"),
    ("three/addons/loaders/RGBELoader.js", "RGBELoader.js"),
    ("three/addons/objects/Sky.js", "Sky.js"),
    ("three/addons/postprocessing/SSRPass.js", "SSRPass.js"),
    ("three/addons/renderers/CSS2DRenderer.js", "CSS2DRenderer.js"),
    ("three/addons/shaders/SSRShader.js", "SSRShader.js"),
    ("three/addons/utils/BufferGeometryUtils.js", "BufferGeometryUtils.js"),
]

BOOT_OFFLINE = '''<script id="twin-boot">
/* --- 完全离线引导：three.js 已全量内联为 importmap data URI，无需 CDN --- */
(function () {
  function fail(msg) {
    var box = document.querySelector('#loading .box');
    if (!box) { alert('三维引擎初始化失败: ' + msg); return; }
    box.innerHTML = '<div class="t" style="color:#ff8585">三维引擎初始化失败</div>' +
      '<div style="color:#9fb4c8;font:12px/1.7 system-ui;margin:12px 0 14px">' + msg + '</div>';
  }
  function go() {
    try {
      var slot = document.getElementById('twinEngineSrc');
      if (!slot) { fail('engine slot missing'); return; }
      var blob = new Blob([slot.textContent], { type: 'text/javascript' });
      import(URL.createObjectURL(blob)).catch(function (e) { fail(e && e.message || e); });
    } catch (e) { fail(e && e.message || e); }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', go);
  else go();
})();
</script>'''


def inline_three(html, skeleton_path):
    """--offline-three：页面零外网请求。两条路径：
    1) 首选 assets/three-r160-bundle.js（build_three_bundle.py 产物）——
       three.js+引擎 esbuild 打包成单一内联经典脚本，CSP 兼容
       （script-src 'self' 'unsafe-inline' 的严格环境如资料库在线预览也能跑，
       importmap 的 data:/blob: 脚本源会被这类 CSP 整体拦截）。
    2) 回退 assets/three-r160/ importmap data URI 方案（宽松环境可用）。"""
    assets_dir = os.path.join(os.path.dirname(os.path.abspath(skeleton_path)))
    bundle = os.path.join(assets_dir, "three-r160-bundle.js")
    if os.path.exists(bundle):
        js = io.open(bundle, "r", encoding="utf-8").read()
        if "</script" in js:
            sys.exit("bundle 含 </script 危险序列，请重跑 build_three_bundle.py")
        boot_new = ('<script id="twin-boot">\n'
                    '/* 完全离线 + CSP 兼容：three.js r160 与孪生引擎已 esbuild 打包为'
                    '单一内联脚本（模型走 data: 直解析旁路），无 importmap / blob / 外网请求 */\n'
                    + js + "\n</script>")
        m = re.search(r'<script id="twin-boot">.*?</script>', html, re.S)
        if not m:
            sys.exit("骨架结构异常：未找到 twin-boot 引导脚本")
        return html[:m.start()] + boot_new + html[m.end():]

    vendor = os.path.join(assets_dir, THREE_VENDOR_DIRNAME)
    if not os.path.isdir(vendor):
        sys.exit("找不到离线引擎目录：%s" % vendor)
    entries = []
    for spec, fname in THREE_MODULES:
        p = os.path.join(vendor, fname)
        if not os.path.exists(p):
            sys.exit("离线引擎缺模块：%s" % p)
        raw = open(p, "rb").read()
        entries.append('"%s": "data:text/javascript;base64,%s"' % (spec, base64.b64encode(raw).decode()))
    importmap = '<script type="importmap">{"imports":{%s}}</script>' % ",\n".join(entries)
    m = re.search(r'<script id="twin-boot">.*?</script>', html, re.S)
    if not m:
        sys.exit("骨架结构异常：未找到 twin-boot 引导脚本")
    return html[:m.start()] + importmap + "\n" + BOOT_OFFLINE + html[m.end():]
IMG_DIRNAME = "img"
_MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}

# 骨架里的默认贴图路径。显式写进 CONFIG 后，--offline-three 把引擎 bundle 内联进页面时，
# 运行时读的是 CONFIG.textures（已替换为 data URI），不会再去请求 img/ 目录（file:// 下必失败）。
# 天图不放进来：默认 env.sky='shader' 走物理天空，省 3 张无用贴图。
DEFAULT_TEXTURES = {
    "lawn": "img/tex-lawn.jpg", "concrete": "img/tex-ground.jpg", "asphalt": "img/tex-asphalt.jpg",
    "wallSteel": "img/tex-wall-steel.jpg", "glass": "img/tex-glass.jpg",
    "wallConcrete": "img/tex-concrete.jpg", "tank": "img/tex-tank.jpg",
    "ore": "img/tex-ore.jpg", "crate": "img/tex-crate.jpg", "tree": "img/sprite-tree.png",
    "bench": "img/tex-bench.jpg", "track": "img/tex-track.jpg"
}


def _shrink_image(path, max_side):
    """把贴图缩到 max_side 以内并重编码 —— v0.11 集显版的体积 / 显存双降手段

    返回 (bytes, mime)；PIL 不可用或无需处理时返回 None（调用方回退原始文件）。

    ⚠️ 法线贴图千万别留 PNG：1024² 的无损 PNG 法线单张就近 1MB，13 张直接把页面顶到 17MB。
    转 WebP q88 后体积降 6~8 倍，而精度完全够 —— 游戏行业做法线贴图本来就是 BC5 有损压缩。
    albedo / rough 走 JPEG q82（1024² 与原图观感无差）。
    """
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        im = Image.open(path)
    except Exception:
        return None
    w, h = im.size
    big = max(w, h)
    changed = big > max_side
    if not changed and os.path.getsize(path) < 200 * 1024:
        return None                                     # 小图重编码反而可能变大，不动
    if changed:
        s = max_side / float(big)
        im = im.resize((max(1, int(round(w * s))), max(1, int(round(h * s)))), Image.LANCZOS)
    buf = io.BytesIO()
    ext = os.path.splitext(path)[1].lower()
    if ext == ".png":
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGBA" if "A" in im.getbands() else "RGB")
        try:
            im.save(buf, "WEBP", quality=88, method=6)
            return buf.getvalue(), "image/webp"
        except Exception:
            buf = io.BytesIO()
            im.save(buf, "PNG", optimize=True)
            return buf.getvalue(), "image/png"
    if im.mode != "RGB":
        im = im.convert("RGB")
    im.save(buf, "JPEG", quality=82, optimize=True, progressive=True)
    return buf.getvalue(), "image/jpeg"


def _hdr_rows(data, pos, w, h):
    """解析 Radiance .hdr 的扫描线（RLE 与 legacy flat 都吃），返回每行「交错」RGBE

    ⚠️ 大坑：HDR 的 RLE 是**通道平面布局**（R[0..w] G[0..w] B[0..w] E[0..w]），
    不是交错像素。直接当交错用会让 E 通道错位到别的通道上 —— 表现是 27% 的像素
    指数 >150（radiance 1e34），PMREM 一算，整个场景白成雪原。
    这里解码到平面缓冲后显式重排成交错 RGBE，下游（下采样 / 重编码）才能按 r,g,b,e 处理。
    """
    rows = []
    for _ in range(h):
        if pos + 4 > len(data):
            break
        # RLE 扫描线固定以 2,2,hi,lo 开头，hi<<8|lo == 宽度
        if data[pos] == 2 and data[pos + 1] == 2 and w >= 8 and ((data[pos + 2] << 8) | data[pos + 3]) == w:
            pos += 4
            plane = bytearray(w * 4)
            ptr = 0
            ptr_end = w * 4
            while ptr < ptr_end:
                if pos >= len(data):
                    return rows
                cnt = data[pos]; pos += 1
                if cnt > 128:                            # run：同一通道值重复 cnt-128 次
                    cnt -= 128
                    if ptr + cnt > ptr_end:
                        break
                    val = data[pos]; pos += 1
                    plane[ptr:ptr + cnt] = bytes([val]) * cnt
                    ptr += cnt
                else:                                    # raw：cnt 个连续通道字节
                    if cnt == 0 or ptr + cnt > ptr_end:
                        break
                    plane[ptr:ptr + cnt] = data[pos:pos + cnt]
                    pos += cnt
                    ptr += cnt
            row = bytearray(w * 4)
            for i in range(w):                           # 平面 → 交错
                row[i * 4]     = plane[i]
                row[i * 4 + 1] = plane[i + w]
                row[i * 4 + 2] = plane[i + 2 * w]
                row[i * 4 + 3] = plane[i + 3 * w]
            rows.append(bytes(row))
        else:                                            # legacy：整数行直接是 w*4 字节（已是交错）
            n = w * 4
            rows.append(bytes(data[pos:pos + n]))
            pos += n
    return rows


def _hdr_rle_row(row, w):
    """把一行 RGBE 编成标准 RLE 扫描线（每通道 128 字节 raw 段，不做 run 压缩）"""
    out = bytearray((2, 2, (w >> 8) & 0xff, w & 0xff))
    for c in range(4):
        ch = row[c::4]
        for k in range(0, w, 128):
            seg = ch[k:k + 128]
            out.append(len(seg))
            out += seg
    return bytes(out)


def _hdr_downscale(path, max_w):
    """Radiance .hdr 最近邻 2× 下采样，返回 (bytes, w, h) 或 None

    HDRI 只用来做 PMREM 环境反射（本来就低频），2048 宽降成 1024 完全看不出，
    但 base64 体积直接砍 4 倍 —— 集显版 25MB 的 HTML 里这两张占了 4MB。
    """
    try:
        with open(path, "rb") as f:
            data = f.read()
        if not data.startswith(b"#?"):
            return None
        head_end = data.find(b"\n\n")
        if head_end < 0:
            return None
        pos = head_end + 2
        nl = data.find(b"\n", pos)
        res = data[pos:nl].decode("ascii", "ignore")
        pos = nl + 1
        m = re.match(r"\s*([+-])Y\s+(\d+)\s+([+-])X\s+(\d+)", res)
        if not m:
            return None
        w, h = int(m.group(4)), int(m.group(2))
        if w <= max_w:
            return None
        rows = _hdr_rows(data, pos, w, h)
        if len(rows) < h:
            return None
        while w > max_w and w >= 2 and h >= 2:
            nr = []
            for y in range(0, h - 1, 2):
                src = rows[y]
                nr.append(b"".join(src[i:i + 4] for i in range(0, w * 4, 8)))
            rows = nr
            w //= 2; h //= 2
        out = bytearray(b"#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n")
        out += ("-Y %d +X %d\n" % (h, w)).encode("ascii")
        # ⚠️ 绝对不能写 flat：RGBELoader 用「首 4 字节是不是 2,2,hi,lo」判断是否 RLE，
        # 而暗部像素正好是 RGBE=(2,2,<128,*) 时会命中这个魔数，然后抛 "wrong scanline width"。
        # 所以统一写标准 RLE 扫描线头 + 128 字节 raw 段（不做 run 压缩，体积只多 0.8%，但零误判风险）
        for r in rows:
            out += _hdr_rle_row(r, w)
        return bytes(out), w, h
    except Exception:
        return None


def inline_images(html, img_dir, max_tex=0):
    """把 img/xxx.jpg 替换成 data URI —— 保证产出的 HTML 单文件可带走、双击即开

    同时把运行时按命名约定推导的补充贴图（xxx-normal.png / xxx-rough.jpg）注入
    window.__TWIN_TEX_URI__ 映射（这些路径不在 HTML 文本里出现，正则抓不到）。
    """
    import base64, re
    used = []
    uri_map = {}
    saved = [0, 0]                                      # [省下的字节, 处理张数]

    def b64_of(rel_name):
        p = os.path.join(img_dir, rel_name)
        if not os.path.exists(p):
            return None
        ext = os.path.splitext(p)[1].lower()
        mime = _MIME.get(ext, "application/octet-stream")
        if max_tex:
            r = _shrink_image(p, max_tex)
            if r is not None:
                raw, mime = r
                saved[0] += os.path.getsize(p) - len(raw)
                saved[1] += 1
                return "data:%s;base64,%s" % (mime, base64.b64encode(raw).decode("ascii"))
        with open(p, "rb") as f:
            return "data:%s;base64,%s" % (mime, base64.b64encode(f.read()).decode("ascii"))

    def sub(m):
        rel = m.group(0)
        uri = b64_of(os.path.basename(rel))
        if uri is None:
            return rel                                   # 找不到就保持原样，页面自动回退纯色
        used.append(os.path.basename(rel))
        # 派生贴图（存在才注入）：albedo -> -normal.png / -rough.jpg
        stem = os.path.splitext(os.path.basename(rel))[0]
        for suffix in ("-normal.png", "-rough.jpg"):
            dname = stem + suffix
            duri = b64_of(dname)
            if duri:
                uri_map["img/" + dname] = duri
        return uri

    html = re.sub(r"img/[A-Za-z0-9._-]+", sub, html)
    if saved[1]:
        print("贴图降采样 %d 张（上限 %dpx，JPEG q82）：原始体积省 %.1f MB"
              % (saved[1], max_tex, saved[0] / 1048576.0))
    if uri_map:
        inject = ('<script>window.__TWIN_TEX_URI__ = ' +
                  json.dumps(uri_map, ensure_ascii=False) + ';</script>\n')
        html = html.replace("<head>", "<head>\n" + inject, 1)
    return html, used


def inline_hdri(html, assets_dir, max_w=0):
    """把 hdri/xxx.hdr 替换成 data URI —— 实拍 HDR 天空（Poly Haven CC0 .hdr）

    RGBELoader 走 FileLoader（fetch 支持 data: URI），故 HDR 也可内联为单文件；
    只有 env.sky='hdri' 的场景才会在 CONFIG.textures 里注入 hdri/ 路径，其余场景零体积浪费。
    max_w：集显版把 2k HDR 降到 1k（只服务 PMREM 环境反射，低频到看不出差别，体积砍 4×）。
    """
    import base64, re
    hdri_dir = os.path.join(assets_dir, "hdri")
    used = []

    def sub(m):
        rel = m.group(0)
        p = os.path.join(hdri_dir, os.path.basename(rel))
        if not os.path.exists(p):
            return rel                                   # 找不到保持原样，页面回退物理天空
        raw = None
        if max_w:
            r = _hdr_downscale(p, max_w)
            if r is not None:
                raw, nw, nh = r
                print("  HDR 降采样：%s → %dx%d" % (os.path.basename(rel), nw, nh))
        if raw is None:
            with open(p, "rb") as f:
                raw = f.read()
        used.append((os.path.basename(rel), len(raw)))
        return "data:application/octet-stream;base64," + base64.b64encode(raw).decode("ascii")

    html = re.sub(r"hdri/[A-Za-z0-9._-]+\.hdr", sub, html)
    return html, used


def glb_uses_draco(path):
    """GLB 的 JSON chunk 里出现 KHR_draco_mesh_compression → 该模型需要 DRACO decoder"""
    try:
        with open(path, "rb") as f:
            head = f.read(20)
        if len(head) < 20 or head[:4] != b"glTF" or head[16:20] != b"JSON":
            return False
        with open(path, "rb") as f:
            f.seek(20)
            blob = f.read(struct.unpack("<I", head[12:16])[0])
        return b"KHR_draco_mesh_compression" in blob
    except Exception:
        return False


def inline_models(html, models_dir):
    """把 models/xxx.glb 内联成 data URI —— 与贴图同理，保证单文件可带走

    ⚠️ v0.11 改为「查表注入」而不是正文替换：同一个 GLB 常被引用多次
    （集装箱 ×14、叉车 ×3），正文替换会在 HTML 里存 14 份一模一样的 base64
    —— 仓库场景实测因此多出 2.5 MB。现在只注入一份 window.__TWIN_MODEL_URI__，
    骨架加载前查表还原，配置里的路径保持可读。

    返回 (html, used, draco_models)；used 是 (文件名, 字节数) 列表，已去重。
    只支持 .glb（二进制自包含）；.gltf + .bin 多文件格式无法内联，需先转换。
    """
    import base64, re
    used, draco_models = [], []
    uri_map = {}

    for name in sorted(set(re.findall(r"models/([A-Za-z0-9._-]+\.glb)", html))):
        p = os.path.join(models_dir, name)
        if not os.path.exists(p):
            continue                                     # 找不到保持原样，页面回退程序化占位
        with open(p, "rb") as f:
            raw = f.read()
        used.append((name, len(raw)))
        if glb_uses_draco(p):
            draco_models.append(name)
        uri_map["models/" + name] = ("data:application/octet-stream;base64," +
                                     base64.b64encode(raw).decode("ascii"))

    if uri_map:
        inject = ('<script>window.__TWIN_MODEL_URI__ = ' +
                  json.dumps(uri_map, ensure_ascii=False) + ';</script>\n')
        html = html.replace("<head>", "<head>\n" + inject, 1)
    return html, used, draco_models


def inject_draco(html, assets_dir):
    """把 draco decoder（wrapper js + wasm）base64 注入 window.__TWIN_DRACO__

    骨架的 DRACOLoader 检测到该变量时，用 LoadingManager.setURLModifier 把
    decoder 请求改写为 data URI，彻底摆脱 unpkg CDN 依赖（离线可用）。
    decoder 缺失时返回 False，骨架自动回退 CDN。
    """
    import base64
    draco_dir = os.path.join(assets_dir, "draco")
    files = {"wrapper": os.path.join(draco_dir, "draco_wasm_wrapper.js"),
             "wasm":    os.path.join(draco_dir, "draco_decoder.wasm")}
    if not all(os.path.exists(p) for p in files.values()):
        return html, False

    def b64(p, mime):
        with open(p, "rb") as f:
            return "data:%s;base64,%s" % (mime, base64.b64encode(f.read()).decode("ascii"))

    payload = {"wrapper": b64(files["wrapper"], "text/javascript"),
               "wasm":    b64(files["wasm"], "application/octet-stream")}
    inject = ('<script>window.__TWIN_DRACO__ = ' +
              json.dumps(payload, ensure_ascii=False) + ';</script>\n')
    html = html.replace("<head>", "<head>\n" + inject, 1)
    return html, True


# ----------------------------------------------------------------------------- 场景预设
def _common(title, subtitle):
    return {
        "meta": {"title": title, "subtitle": subtitle, "dataMode": "mock"},
        # preset 默认 day（物理天空 shader + 写实日光）；想要深色科技风改用 cyber
        "env": {"preset": "day", "sky": "shader", "realism": True,
                "bgTop": "#0b2545", "bgBottom": "#03080f",
                "ground": "#0e1c2c", "gridColor": "#123049", "gridSize": 600, "gridDivisions": 60,
                "gridOpacity": 0.05,          # 科技网格线强度（写实风 <=0.2；shader 天空下建议接近 0）
                "groundTex": "concrete",      # lawn | concrete | asphalt | none
                "groundTexRepeat": 8,     # 高空俯视 repeat>10 出斑马纹，写实铁律
                "haze": [0x081422, 320, 1100], "exposure": 1.05,
                "sunDirection": [120, 160, 80], "sunIntensity": 2.2},
        "camera": {"fov": 45, "position": [150, 105, 175], "target": [0, 8, 0], "autoFit": True},
        "labels": {"show": True, "showStatus": True},
        "dataSource": {"mode": "mock", "refreshMs": 8000,
                       "http": {"assets": "", "metrics": "", "alerts": ""}},
        "alerts": [], "buildings": [], "devices": [], "models": []
    }


def preset_warehouse(title):
    c = _common(title, "立体库 + 平库 + 露天堆场 · 仓储物流")
    c["sceneType"] = "warehouse"
    c["kpis"] = [{"label": "在库总量", "value": "12,480", "unit": "吨"},
                 {"label": "今日入库", "value": "1,286", "unit": "吨"},
                 {"label": "今日出库", "value": "964", "unit": "吨"},
                 {"label": "作业设备", "value": "23", "unit": "台"},
                 {"label": "在线率", "value": "96.4", "unit": "%"},
                 {"label": "未处理告警", "value": "2", "unit": "条"}]
    c["buildings"] = [
        {"id": "WH-01", "type": "warehouse", "name": "1号立体库", "position": [0, 0, -40],
         "size": [130, 20, 58], "roof": "arch", "seeThrough": True, "status": "normal",
         "metrics": [{"label": "库容利用率", "value": "82%", "pct": 82},
                     {"label": "在库吨位", "value": "12,480 吨"}]},
        {"id": "WH-02", "type": "warehouse", "name": "2号平库", "position": [0, 0, 95],
         "size": [130, 14, 44], "roof": "gable", "seeThrough": True, "status": "normal",
         "metrics": [{"label": "库容利用率", "value": "61%", "pct": 61}]}]
    c["devices"] = [
        {"id": "RACK-A", "type": "rack", "name": "A区货架", "position": [-31, 0, -45],
         "size": [56, 15, 24], "bays": 10, "levels": 4, "fill": 0.78, "status": "normal"},
        {"id": "RACK-B", "type": "rack", "name": "B区货架", "position": [31, 0, -45],
         "size": [56, 15, 24], "bays": 10, "levels": 4, "fill": 0.91, "status": "warn",
         "metrics": [{"label": "货位占用", "value": "91%", "pct": 91}]},
        {"id": "YARD-01", "type": "yard", "name": "露天堆场", "position": [-150, 0, 150],
         "size": [150, 70], "stack": "cone", "rows": 3, "cols": 6, "status": "normal"},
        # 注：TANK-01/02 已改用 Blender 高精度 GLB（见下方 c["models"]）。
        # 程序化圆柱版本在此移除 —— 倒角高光 / 抗风圈分层 / 笼式爬梯 / 顶部栏杆 / 法兰阀组
        # 这些细节是 CylinderGeometry 永远给不了的，而这批细节正是"一眼假"的根源。
        {"id": "PIPE-01", "type": "pipeline", "name": "主工艺管线", "radius": 0.9, "flow": True,
         "status": "normal", "points": [[150, 1.2, 16], [150, 1.2, -80], [60, 1.2, -80],
                                        [60, 1.2, 72], [0, 1.2, 72]]},
        # SILO-01 同样改用 Blender GLB（见下方 c["models"]）：锥底卸料斗 + 环箍 + 支撑腿
        {"id": "BELT-01", "type": "conveyor", "name": "输送廊道", "position": [-60, 10, 40],
         "length": 120, "status": "normal"},
        {"id": "CAR-01", "type": "vehicle", "name": "运输车 A", "position": [-120, 0, -8],
         "speed": 14, "path": [[-120, 0, -8], [140, 0, -8]], "status": "normal"},
        {"id": "CAR-02", "type": "vehicle", "name": "运输车 B", "position": [100, 0, -120],
         "speed": 11, "path": [[100, 0, -120], [-140, 0, -120]], "status": "normal"}]
    c["env"].update({"gridSize": 800, "gridDivisions": 80, "haze": [0x081422, 400, 1200],
                     "sky": "hdri"})   # v0.5：实拍 HDR 天空（Poly Haven CC0），比 Preetham shader 更逼真
    c["camera"].update({"position": [190, 120, 210], "target": [0, 6, 0]})
    c["devices"] += [
        # —— 环境配景：ambient:true → 不拾取 / 不进清单 / 不参与取景 ——
        {"id": "LN-01", "type": "lawn", "ambient": True, "name": "南侧绿地",
         "position": [-120, 0, 240], "size": [260, 80]},
        {"id": "LN-02", "type": "lawn", "ambient": True, "name": "东南绿地",
         "position": [200, 0, 250], "size": [160, 70]},
        {"id": "RD-01", "type": "road", "ambient": True, "name": "园区主通道",
         "position": [0, 0, 20], "size": [18, 460]},
        {"id": "RD-02", "type": "road", "ambient": True, "name": "横向次通道",
         "position": [-110, 0, 20], "size": [14, 330], "rotation": 90},
        {"id": "GR-01", "type": "grove", "ambient": True, "name": "西绿化带",
         "position": [-250, 0, -40], "size": [60, 200], "count": 30, "seed": 3},
        {"id": "GR-02", "type": "grove", "ambient": True, "name": "南绿化带",
         "position": [-40, 0, 280], "size": [320, 26], "count": 26, "seed": 9},
        {"id": "GR-03", "type": "grove", "ambient": True, "name": "东北绿化带",
         "position": [230, 0, -210], "size": [80, 110], "count": 18, "seed": 17},
        {"id": "PK-01", "type": "parking", "ambient": True, "name": "访客停车场",
         "position": [150, 0, 250], "cols": 8, "rows": 1, "seed": 5},
        {"id": "LP-01", "type": "lampRow", "ambient": True, "name": "主通道路灯", "height": 9,
         "points": [[11, 0, -215], [11, 0, 235]]},
        {"id": "LP-02", "type": "lampRow", "ambient": True, "name": "次通道路灯", "height": 9,
         "points": [[-110, 0, -150], [-110, 0, 180]]},
        # —— 装卸区散货托盘（v0.6 生活痕迹）：平库门口待入库/待出库托盘堆 ——
        {"id": "PL-01", "type": "pallet", "ambient": True, "name": "待入库托盘", "position": [-26, 0, 122], "size": [2.6, 2.6], "layers": 2, "rotation": 12, "seed": 3},
        {"id": "PL-02", "type": "pallet", "ambient": True, "name": "待入库托盘", "position": [-18, 0, 126], "size": [2.4, 2.4], "layers": 3, "rotation": -8, "seed": 11},
        {"id": "PL-03", "type": "pallet", "ambient": True, "name": "待出库托盘", "position": [18, 0, 120], "size": [2.6, 2.6], "layers": 2, "rotation": 24, "seed": 7},
        {"id": "PL-04", "type": "pallet", "ambient": True, "name": "待出库托盘", "position": [26, 0, 125], "size": [2.4, 2.4], "layers": 3, "rotation": -18, "seed": 19}
    ]
    c["alerts"] = [{"deviceId": "TANK-02", "level": "critical", "text": "液位超上限 94%", "time": "10:24"},
                   {"deviceId": "RACK-B", "level": "warning", "text": "货位占用率 91%", "time": "10:11"}]
    c["patrol"] = {"enabled": True, "duration": 48, "loop": True, "autoStart": False, "height": 46,
                   "waypoints": [[210, 46, 210], [210, 46, -190], [-190, 46, -190], [-190, 46, 210]]}
    # —— 外部 GLB：Blender 高精度工业设备（scripts/gen_models_blender.py 可复跑重生成）——
    # scale 一律由「模型实际外廓 ÷ 目标实物尺寸」反算：罐体外廓含基础环 34.22m，
    # 目标 Ø32m → 0.94。不要用 scale 去"凑大小"——缩放会连倒角一起放大，等于白做细节。
    c["models"] = [
        {"id": "TANK-01", "name": "1号储罐", "url": "models/bl-tank.glb",
         "position": [150, 0, 40], "rotation": 0, "scale": 0.94, "status": "normal",
         "fallback": {"type": "tank", "radius": 16, "height": 26},
         "metrics": [{"label": "液位", "value": "86%", "pct": 86}, {"label": "介质", "value": "乙二醇"}]},
        {"id": "TANK-02", "name": "2号储罐", "url": "models/bl-tank.glb",
         "position": [190, 0, 40], "rotation": 150, "scale": 0.94, "status": "alarm",
         "fallback": {"type": "tank", "radius": 16, "height": 26},
         "metrics": [{"label": "液位", "value": "94%", "pct": 94}, {"label": "温度", "value": "51 ℃"}]},
        {"id": "SILO-01", "name": "中转筒仓", "url": "models/bl-silo.glb",
         "position": [-195, 0, -30], "rotation": 0, "scale": 0.99, "status": "normal",
         "fallback": {"type": "silo", "radius": 12, "height": 38}},
    ]
    # 集装箱堆场：20ft 标准箱 6.06×2.44×2.59，按 6.3 / 3.5 间距码放，含二层堆垛
    # v0.8：堆场加密到 14 箱（三排 + 二层），否则 26m 跨距的龙门吊下面空得像停车场
    for _i, (_cx, _cy, _cz) in enumerate(((265, 0, 112), (271.3, 0, 112), (277.6, 0, 112),
                                          (265, 0, 115.5), (271.3, 0, 115.5), (277.6, 0, 115.5),
                                          (265, 2.62, 112), (271.3, 2.62, 112),
                                          (277.6, 2.62, 112), (265, 2.62, 115.5),
                                          (271.3, 2.62, 115.5), (277.6, 2.62, 115.5),
                                          (265, 0, 119), (271.3, 0, 119))):
        c["models"].append({
            "id": "CN-%02d" % (_i + 1), "name": "集装箱 %02d" % (_i + 1),
            "url": "models/bl-container.glb", "position": [_cx, _cy, _cz],
            "rotation": 0, "scale": 1, "ambient": True,
            "fallback": {"type": "box", "size": [6.06, 2.59, 2.44]}})
    # 待卸货车：停在 2 号平库前装卸位，车头朝主通道
    for _i, _tz in enumerate((134, 138.2)):
        c["models"].append({
            "id": "TRK-%02d" % (_i + 1), "name": "待卸货车 %02d" % (_i + 1),
            "url": "models/bl-truck.glb", "position": [-32, 0, _tz], "rotation": 0,
            "scale": 1, "ambient": True,
            "fallback": {"type": "box", "size": [9.6, 3.4, 2.5]}})
    # —— v0.8 高精度设备：叉车（3.5t 平衡重式）——
    # 场景里"有人干活"的关键证物：没有搬运设备的仓库 = 没有生命感的空盒子。
    # 摆放逻辑：平库装卸区 2 台（对向作业）+ 立体库门口 1 台（待命）
    for _i, (_fx, _fz, _fr) in enumerate(((-14, 128, 25), (14, 121, -160), (72, -22, 200))):
        c["models"].append({
            "id": "FLK-%02d" % (_i + 1), "name": "叉车 %02d" % (_i + 1),
            "url": "models/bl-forklift.glb", "position": [_fx, 0, _fz], "rotation": _fr,
            "scale": 1, "ambient": True,
            "fallback": {"type": "box", "size": [3.7, 2.4, 1.3]}})
    # —— v0.8 高精度设备：轨道式龙门吊（堆场跨距 26m）——
    # scale 由「模型外廓跨距 27.60m ÷ 目标跨距 26m」反算 = 0.94，勿用 scale 凑大小
    c["models"].append({
        "id": "GC-01", "name": "堆场龙门吊", "url": "models/bl-gantry.glb",
        "position": [271.3, 0, 114], "rotation": 0, "scale": 0.94, "status": "normal",
        "fallback": {"type": "box", "size": [27.6, 15.9, 9.8]},
        "metrics": [{"label": "今日吊次", "value": "186", "pct": 62},
                    {"label": "作业效率", "value": "92%", "pct": 92}]})
    return c


def preset_plant(title):
    c = _common(title, "主车间 + 罐区 + 管廊 · 厂区数字孪生")
    c["sceneType"] = "plant"
    c["env"].update({"bgTop": "#122033", "bgBottom": "#05080d", "sunIntensity": 2.0})
    c["kpis"] = [{"label": "装置负荷", "value": "92.6", "unit": "%"},
                 {"label": "今日产量", "value": "1,840", "unit": "吨"},
                 {"label": "能耗单耗", "value": "86.4", "unit": "kg/t"},
                 {"label": "在线设备", "value": "312", "unit": "台"},
                 {"label": "报警数", "value": "5", "unit": "条"},
                 {"label": "安全天数", "value": "127", "unit": "天"}]
    c["buildings"] = [
        {"id": "MB-01", "type": "warehouse", "name": "主车间", "position": [-80, 0, 0],
         "size": [120, 24, 70], "roof": "arch", "seeThrough": True, "status": "normal",
         "metrics": [{"label": "装置负荷", "value": "92.6%", "pct": 93}]},
        {"id": "MB-02", "type": "warehouse", "name": "成品库", "position": [95, 0, -95],
         "size": [90, 16, 50], "roof": "gable", "seeThrough": True, "status": "normal"}]
    devs = []
    for i, (x, z) in enumerate([(-40, 120), (20, 120), (-40, 180), (20, 180)]):
        devs.append({"id": "T-0%d" % (i + 1), "type": "tank", "name": "%d号储罐" % (i + 1),
                     "position": [x, 0, z], "radius": 13, "height": 24,
                     "level": 0.5 + i * 0.12, "status": "normal" if i < 3 else "warn",
                     "metrics": [{"label": "液位", "value": "%d%%" % int((0.5 + i * 0.12) * 100)},
                                 {"label": "温度", "value": "%d ℃" % (32 + i * 4)}]})
    devs += [
        {"id": "PIPE-A", "type": "pipeline", "name": "罐区管廊", "radius": 0.8, "flow": True,
         "status": "normal", "points": [[-40, 12, 120], [20, 12, 120], [20, 12, 180], [-40, 12, 180]]},
        {"id": "SILO-A", "type": "silo", "name": "原料筒仓", "position": [130, 0, 60],
         "radius": 11, "height": 34, "status": "normal"},
        {"id": "BELT-A", "type": "conveyor", "name": "成品输送廊道", "position": [95, 12, -40],
         "length": 110, "status": "normal"},
        {"id": "RACK-P", "type": "rack", "name": "备件货架", "position": [95, 0, -95],
         "size": [50, 12, 20], "bays": 8, "levels": 3, "fill": 0.6, "status": "normal"},
        {"id": "CAR-P1", "type": "vehicle", "name": "厂内运输车", "position": [-160, 0, -120],
         "speed": 12, "path": [[-160, 0, -120], [160, 0, -120]], "status": "normal"}]
    c["devices"] = devs
    c["alerts"] = [{"deviceId": "T-04", "level": "warning", "text": "液位偏高 86%", "time": "09:52"}]
    c["patrol"] = {"enabled": True, "duration": 56, "loop": True, "autoStart": False, "height": 60,
                   "waypoints": [[230, 60, 250], [-230, 60, 250], [-230, 60, -200], [230, 60, -200]]}
    return c


def preset_park(title):
    c = _common(title, "多业态园区 · 楼宇 + 道路 + 停车场")
    c["sceneType"] = "park"
    c["env"].update({"bgTop": "#14243a", "bgBottom": "#05080f"})
    c["kpis"] = [{"label": "入驻企业", "value": "86", "unit": "家"},
                 {"label": "今日人流", "value": "4,628", "unit": "人"},
                 {"label": "车位占用", "value": "72", "unit": "%"},
                 {"label": "能耗总量", "value": "18.4", "unit": "万kWh"},
                 {"label": "告警数", "value": "1", "unit": "条"},
                 {"label": "在线率", "value": "99.2", "unit": "%"}]
    b, d = [], []
    blocks = [("A座 研发楼", -120, -60, [40, 46, 30]), ("B座 办公楼", -40, -60, [46, 38, 30]),
              ("C座 孵化器", 40, -60, [42, 52, 30]), ("D座 配套商业", 120, -60, [36, 22, 26]),
              ("E座 员工宿舍", -100, 60, [54, 30, 30]), ("F座 交流中心", 60, 60, [40, 18, 34])]
    for name, x, z, size in blocks:
        b.append({"id": "B-" + name.split()[0], "type": "warehouse", "name": name,
                  "position": [x, 0, z], "size": size, "roof": "flat", "seeThrough": False,
                  "status": "normal",
                  "metrics": [{"label": "入驻率", "value": "%d%%" % (60 + (x % 40))},
                              {"label": "能耗", "value": "%d kWh" % (200 + abs(x))}]})
    d.append({"id": "PARK-P", "type": "yard", "name": "地面停车场", "position": [-30, 0, 150],
              "size": [120, 46], "stack": "box", "rows": 3, "cols": 8, "status": "normal"})
    for i, (x, z) in enumerate([(-160, 150), (110, 150), (-160, -150)]):
        d.append({"id": "GATE-%d" % (i + 1), "type": "box", "name": "%d号闸口" % (i + 1),
                  "position": [x, 0, z], "size": [16, 8, 6], "status": "normal"})
    for i, path in enumerate([[[-200, 0, 0], [200, 0, 0]], [[0, 0, -200], [0, 0, 200]]]):
        d.append({"id": "BUS-%d" % (i + 1), "type": "vehicle", "name": "园区摆渡车 %d" % (i + 1),
                  "position": path[0], "speed": 9, "path": path, "status": "normal"})
    c["buildings"], c["devices"] = b, d
    c["alerts"] = [{"deviceId": "B-F", "level": "warning", "text": "交流中心空调超负荷", "time": "08:31"}]
    c["patrol"] = {"enabled": True, "duration": 62, "loop": True, "autoStart": False, "height": 78,
                   "waypoints": [[280, 78, 300], [-280, 78, 300], [-280, 78, -280], [280, 78, -280]]}
    return c


def preset_bulk(title):
    c = _common(title, "港口堆场 + 筒仓 + 装船作业 · 大宗贸易")
    c["sceneType"] = "bulk"
    c["env"].update({"bgTop": "#0d2036", "bgBottom": "#03080e"})
    c["kpis"] = [{"label": "今日到港", "value": "6", "unit": "船"},
                 {"label": "堆存总量", "value": "486,200", "unit": "吨"},
                 {"label": "今日吞吐", "value": "72,400", "unit": "吨"},
                 {"label": "作业机械", "value": "38", "unit": "台"},
                 {"label": "在途货值", "value": "3.26", "unit": "亿"},
                 {"label": "告警数", "value": "2", "unit": "条"}]
    b, d = [], []
    b.append({"id": "BERTH-1", "type": "box", "name": "1号泊位", "position": [-40, 0, 220],
              "size": [220, 3, 26], "status": "normal",
              "metrics": [{"label": "泊位利用率", "value": "78%", "pct": 78}]})
    for i, (x, z, st_, kind) in enumerate([(-160, -40, "normal", "cone"), (-160, 80, "normal", "box"),
                                           (60, -40, "warn", "cone"), (60, 80, "normal", "box")]):
        d.append({"id": "BASIN-%d" % (i + 1), "type": "yard", "name": "%d号堆场" % (i + 1),
                  "position": [x, 0, z], "size": [140, 90], "stack": kind,
                  "rows": 3, "cols": 7, "status": st_,
                  "metrics": [{"label": "堆存量", "value": "%d,%03d 吨" % (60 + i * 11, 200 + i * 137),
                               "pct": 55 + i * 9}]})
    d += [
        {"id": "SHIP-1", "type": "box", "name": "在港船舶「远海 8」", "position": [10, 0, 260],
         "size": [96, 12, 26], "status": "normal",
         "metrics": [{"label": "装载进度", "value": "64%", "pct": 64}, {"label": "货种", "value": "铁矿石"}]},
        {"id": "QL-1", "type": "conveyor", "name": "装船皮带机", "position": [10, 16, 180],
         "length": 140, "status": "normal"},
        {"id": "SILO-B1", "type": "silo", "name": "粮食筒仓群 1", "position": [230, 0, -60],
         "radius": 12, "height": 40, "status": "normal"},
        {"id": "SILO-B2", "type": "silo", "name": "粮食筒仓群 2", "position": [230, 0, 20],
         "radius": 12, "height": 40, "status": "normal"},
        {"id": "TANK-B1", "type": "tank", "name": "液体化工罐", "position": [-260, 0, 220],
         "radius": 15, "height": 26, "level": 0.72, "status": "normal"},
        {"id": "PIPE-B", "type": "pipeline", "name": "罐区输送管线", "radius": 0.9, "flow": True,
         "status": "normal", "points": [[-260, 1.2, 200], [-140, 1.2, 200], [-140, 1.2, 120]]},
        {"id": "TRK-B1", "type": "vehicle", "name": "集卡 1", "position": [-200, 0, 160],
         "speed": 13, "path": [[-200, 0, 160], [200, 0, 160]], "status": "normal"},
        {"id": "TRK-B2", "type": "vehicle", "name": "集卡 2", "position": [160, 0, 160],
         "speed": 11, "path": [[160, 0, 160], [-160, 0, 160]], "status": "normal"}]
    c["buildings"], c["devices"] = b, d
    c["alerts"] = [{"deviceId": "BASIN-3", "level": "warning", "text": "堆场作业饱和度偏高", "time": "11:02"}]
    c["patrol"] = {"enabled": True, "duration": 60, "loop": True, "autoStart": False, "height": 90,
                   "waypoints": [[330, 90, 340], [-330, 90, 340], [-330, 90, -220], [330, 90, -220]]}
    return c




def preset_campus(title):
    """园区 / 院区：多栋幕墙楼 + 中央绿地 + 主路行道树 + 停车场（写实日光基调）"""
    c = _common(title or "智慧园区 · 数字孪生", "写实日光 · 多楼宇 · Mock 数据")
    c["sceneType"] = "campus"
    c["env"].update({"preset": "day", "gridOpacity": 0.10, "groundTex": "lawn",
                     # lawn 低对比贴图：repeat 32 细腻且低于摩尔阈值；高对比裂缝贴图（concrete）才需 ≤10
                     "groundTexRepeat": 32, "gridSize": 900, "gridDivisions": 90})
    c["camera"].update({"position": [260, 150, 300], "target": [0, 20, 0]})
    c["buildings"] = [
        {"id": "B-01", "type": "office", "name": "研发主楼", "position": [-90, 0, -60],
         "size": [54, 44, 32], "floors": 10, "podium": 2, "roofUnits": 4, "status": "normal",
         "metrics": [{"label": "入驻企业", "value": "24 家"}, {"label": "今日访客", "value": "318 人"},
                     {"label": "能耗", "value": "正常"}]},
        {"id": "B-02", "type": "office", "name": "综合服务楼", "position": [70, 0, -90],
         "size": [46, 30, 28], "floors": 7, "podium": 1, "roofUnits": 3, "status": "normal",
         "metrics": [{"label": "在岗人数", "value": "186 人"}, {"label": "空调负荷", "value": "62%", "pct": 62}]},
        {"id": "B-03", "type": "warehouse", "name": "物资仓库", "position": [120, 0, 110],
         "size": [90, 16, 44], "roof": "flat", "seeThrough": False, "status": "warn",
         "metrics": [{"label": "库容利用率", "value": "88%", "pct": 88}]}
    ]
    c["devices"] = [
        # —— 环境配景：ambient:true → 不拾取 / 不进清单 / 不参与取景 ——
        {"id": "RD-01", "type": "road", "ambient": True, "name": "园区主路",
         "position": [0, 0, 20], "size": [20, 520]},
        {"id": "RD-02", "type": "road", "ambient": True, "name": "横向环路",
         "position": [-140, 0, 60], "size": [14, 340], "rotation": 90},
        {"id": "LN-01", "type": "lawn", "ambient": True, "name": "中央绿地",
         "position": [0, 0, 180], "size": [260, 90]},
        {"id": "GR-01", "type": "grove", "ambient": True, "name": "主路行道树",
         "position": [-16, 0, 0], "size": [26, 420], "count": 40, "seed": 3},
        {"id": "GR-02", "type": "grove", "ambient": True, "name": "南侧绿化",
         "position": [0, 0, 215], "size": [280, 30], "count": 28, "seed": 9},
        {"id": "GR-03", "type": "grove", "ambient": True, "name": "西北绿化",
         "position": [-230, 0, -150], "size": [90, 110], "count": 22, "seed": 17},
        {"id": "PK-01", "type": "parking", "ambient": True, "name": "访客停车场",
         "position": [170, 0, 200], "cols": 10, "rows": 1, "seed": 5},
        {"id": "LP-01", "type": "lampRow", "ambient": True, "name": "主路路灯", "height": 9,
         "points": [[11, 0, -240], [11, 0, 240]]},
        # —— 业务设备 ——
        {"id": "CAM-01", "type": "box", "name": "周界监控", "position": [-180, 0, -60],
         "size": [3, 10, 3], "status": "normal"},
        {"id": "CAR-01", "type": "vehicle", "name": "巡逻车", "position": [-200, 0, -8], "speed": 16,
         "path": [[-200, 0, -8], [220, 0, -8]], "status": "normal",
         "metrics": [{"label": "车牌", "value": "鄂A·7701"}, {"label": "任务", "value": "园区巡更"}]}
    ]
    c["kpis"] = [
        {"label": "入驻企业", "value": "24", "unit": "家"},
        {"label": "今日访客", "value": "318", "unit": "人"},
        {"label": "在岗人数", "value": "186", "unit": "人"},
        {"label": "能耗强度", "value": "42.6", "unit": "kWh/㎡"},
        {"label": "设备在线", "value": "98.2", "unit": "%"},
        {"label": "未处理告警", "value": "1", "unit": "条"}
    ]
    c["alerts"] = [{"deviceId": "B-03", "level": "warning", "text": "物资仓库库容 88%", "time": "09:42"}]
    return c

def preset_logisticspark(title):
    """完整仓储园区：多栋库房 + 装卸月台 + 集卡动线 + 堆场 + 办公楼 + 门卫闸口 + 围墙 + 屋顶光伏"""
    c = _common(title, "多栋库房 · 装卸月台 · 堆场 · 闸口 · 全要素仓储园区")
    c["sceneType"] = "park"
    # 场地用深灰蓝素色（不挂混凝土贴图）：大面积混凝土在强光下会整片泛白，
    # 深色场地 + 浅色库房墙面的明暗对比才是园区该有的层次；道路靠浅色路缘石区分。
    c["env"].update({"gridSize": 900, "gridDivisions": 90, "haze": [0x081422, 700, 2200],
                     "exposure": 0.95, "groundTex": "none", "ground": "#263340",
                     "gridOpacity": 0.07})
    c["camera"].update({"position": [300, 150, 340], "target": [0, 14, 40]})
    c["kpis"] = [
        {"label": "园区占地", "value": "38.4", "unit": "万㎡"},
        {"label": "在库总量", "value": "86,400", "unit": "吨"},
        {"label": "今日入库", "value": "3,860", "unit": "吨"},
        {"label": "今日出库", "value": "3,240", "unit": "吨"},
        {"label": "月台作业", "value": "128", "unit": "车次"},
        {"label": "库容利用率", "value": "78.6", "unit": "%"},
        {"label": "设备在线", "value": "97.2", "unit": "%"},
        {"label": "未处理告警", "value": "3", "unit": "条"}
    ]
    c["buildings"] = [
        {"id": "WH-01", "type": "warehouse", "name": "1号立体库", "position": [-95, 0, -215],
         "size": [150, 26, 58], "roof": "arch", "seeThrough": True, "status": "normal",
         "metrics": [{"label": "库容利用率", "value": "82%", "pct": 82},
                     {"label": "在库吨位", "value": "24,600 吨"},
                     {"label": "货架层高", "value": "12.5 m"}]},
        {"id": "WH-02", "type": "warehouse", "name": "2号立体库", "position": [95, 0, -215],
         "size": [150, 26, 58], "roof": "arch", "seeThrough": True, "status": "normal",
         "metrics": [{"label": "库容利用率", "value": "88%", "pct": 88},
                     {"label": "在库吨位", "value": "26,100 吨"}]},
        {"id": "WH-03", "type": "warehouse", "name": "3号平库", "position": [-95, 0, -95],
         "size": [150, 16, 44], "roof": "gable", "seeThrough": True, "status": "normal",
         "metrics": [{"label": "库容利用率", "value": "61%", "pct": 61},
                     {"label": "在库吨位", "value": "11,900 吨"}]},
        {"id": "WH-04", "type": "warehouse", "name": "4号冷链库", "position": [95, 0, -95],
         "size": [150, 18, 44], "roof": "flat", "seeThrough": True, "status": "warn",
         "metrics": [{"label": "库温", "value": "-16.2 ℃"}, {"label": "设定温度", "value": "-18.0 ℃"},
                     {"label": "库容利用率", "value": "74%", "pct": 74}]},
        {"id": "OFF-01", "type": "office", "name": "园区综合楼", "position": [235, 0, 235],
         "size": [56, 52, 36], "podium": 2, "roofUnits": 4, "rotation": 180, "status": "normal",
         "metrics": [{"label": "入驻部门", "value": "7 个"}, {"label": "在岗", "value": "96 人"}]},
        {"id": "WS-01", "type": "warehouse", "name": "维修车间", "position": [235, 0, -35],
         "size": [56, 12, 30], "roof": "flat", "status": "normal",
         "metrics": [{"label": "在修设备", "value": "3 台"}]}
    ]
    c["devices"] = [
        # —— 装卸月台：每栋库房南侧一组 ——
        {"id": "DOCK-A", "type": "dock", "name": "1号库月台", "position": [-95, 0, -172],
         "size": [150, 22], "bays": 6, "wallHeight": 13, "status": "normal",
         "metrics": [{"label": "今日作业", "value": "32 车次"}, {"label": "在位车辆", "value": "4"}]},
        {"id": "DOCK-B", "type": "dock", "name": "2号库月台", "position": [95, 0, -172],
         "size": [150, 22], "bays": 6, "wallHeight": 13, "status": "normal",
         "metrics": [{"label": "今日作业", "value": "28 车次"}, {"label": "在位车辆", "value": "3"}]},
        {"id": "DOCK-C", "type": "dock", "name": "3号库月台", "position": [-95, 0, -52],
         "size": [150, 20], "bays": 5, "wallHeight": 10, "status": "normal",
         "metrics": [{"label": "今日作业", "value": "21 车次"}]},
        {"id": "DOCK-D", "type": "dock", "name": "4号库月台（冷链）", "position": [95, 0, -52],
         "size": [150, 20], "bays": 5, "wallHeight": 11, "status": "warn",
         "metrics": [{"label": "今日作业", "value": "17 车次"}, {"label": "月台温度", "value": "-9.4 ℃"}]},
        # —— 库内货架 ——
        {"id": "RACK-A", "type": "rack", "name": "1号库 A 区货架", "position": [-118, 0, -215],
         "size": [56, 20, 24], "bays": 12, "levels": 5, "fill": 0.82, "status": "normal",
         "metrics": [{"label": "货位占用", "value": "82%", "pct": 82}]},
        {"id": "RACK-B", "type": "rack", "name": "1号库 B 区货架", "position": [-72, 0, -215],
         "size": [56, 20, 24], "bays": 12, "levels": 5, "fill": 0.68, "status": "normal"},
        {"id": "RACK-C", "type": "rack", "name": "2号库 A 区货架", "position": [72, 0, -215],
         "size": [56, 20, 24], "bays": 12, "levels": 5, "fill": 0.88, "status": "warn"},
        {"id": "RACK-D", "type": "rack", "name": "2号库 B 区货架", "position": [118, 0, -215],
         "size": [56, 20, 24], "bays": 12, "levels": 5, "fill": 0.93, "status": "alarm",
         "metrics": [{"label": "货位占用", "value": "93%", "pct": 93}, {"label": "可用货位", "value": "42"}]},
        {"id": "RACK-E", "type": "rack", "name": "3号库贯通货架", "position": [-95, 0, -95],
         "size": [110, 11, 22], "bays": 16, "levels": 3, "fill": 0.61, "status": "normal"},
        # —— 堆场 / 筒仓 / 水罐 ——
        {"id": "YARD-01", "type": "yard", "name": "集装箱堆场", "position": [-195, 0, 232],
         "size": [190, 78], "stack": "box", "rows": 3, "cols": 8, "status": "alarm",
         "metrics": [{"label": "堆存箱量", "value": "486 TEU"}, {"label": "堆场利用率", "value": "94%", "pct": 94}]},
        {"id": "YARD-02", "type": "yard", "name": "散货堆场", "position": [95, 0, 232],
         "size": [150, 66], "stack": "cone", "rows": 3, "cols": 6, "status": "normal",
         "metrics": [{"label": "在堆吨位", "value": "18,700 吨"}]},
        {"id": "SILO-01", "type": "silo", "name": "散货筒仓 A", "position": [-272, 0, -30],
         "radius": 12, "height": 38, "status": "normal"},
        {"id": "SILO-02", "type": "silo", "name": "散货筒仓 B", "position": [-272, 0, 20],
         "radius": 12, "height": 38, "status": "normal"},
        {"id": "TANK-01", "type": "tank", "name": "消防水罐 A", "position": [255, 0, -175],
         "radius": 10, "height": 16, "level": 0.92, "status": "normal",
         "metrics": [{"label": "液位", "value": "92%", "pct": 92}]},
        {"id": "TANK-02", "type": "tank", "name": "消防水罐 B", "position": [285, 0, -175],
         "radius": 10, "height": 16, "level": 0.9, "status": "normal"},
        {"id": "PIPE-01", "type": "pipeline", "name": "消防管网", "radius": 0.8, "flow": True,
         "status": "normal",
         "points": [[268, 1.2, -160], [268, 1.2, -30], [150, 1.2, -30], [150, 1.2, -160], [-60, 1.2, -160]]},
        {"id": "BELT-01", "type": "conveyor", "name": "散货输送廊道", "position": [-200, 9, 60],
         "length": 130, "status": "normal"},
        # —— 园区出入口 ——
        {"id": "GATE-01", "type": "gate", "name": "园区主大门", "position": [0, 0, 305],
         "width": 34, "sign": "华东智能仓储园区", "signSub": "EAST CHINA SMART LOGISTICS PARK",
         "status": "warn",
         "metrics": [{"label": "今日进出", "value": "426 车次"}, {"label": "排队车辆", "value": "8"},
                     {"label": "平均通行", "value": "48 s"}]},
        # 围墙在南侧大门处断开 34m（closed=false 才不会横穿门洞）
        {"id": "FENCE-01", "type": "fence", "name": "园区围墙", "height": 2.6, "closed": False,
         "points": [[17, 0, 305], [330, 0, 305], [330, 0, -305], [-330, 0, -305],
                    [-330, 0, 305], [-17, 0, 305]],
         "status": "normal"},
        # —— 屋顶光伏 ——
        {"id": "PV-01", "type": "solar", "name": "4号库屋顶光伏", "position": [95, 18.6, -95],
         "size": [140, 40], "rows": 3, "cols": 14, "tilt": 20, "status": "normal",
         "metrics": [{"label": "装机容量", "value": "1.8 MW"}, {"label": "今日发电", "value": "9,640 kWh"}]},
        {"id": "PV-03", "type": "solar", "name": "综合楼屋顶光伏", "position": [235, 52.6, 235],
         "size": [50, 30], "rows": 2, "cols": 6, "tilt": 18, "status": "normal",
         "metrics": [{"label": "装机容量", "value": "0.3 MW"}]},
        # —— 车辆动线 ——
        {"id": "TRK-01", "type": "vehicle", "name": "集卡 A", "position": [-6, 0, -260], "speed": 16,
         "path": [[-6, 0, -255], [-6, 0, 285]], "status": "normal",
         "metrics": [{"label": "车牌", "value": "沪B·7H92"}, {"label": "任务", "value": "1号库卸货"}]},
        {"id": "TRK-02", "type": "vehicle", "name": "集卡 B", "position": [7, 0, 285], "speed": 14,
         "path": [[7, 0, 285], [7, 0, -255]], "status": "normal",
         "metrics": [{"label": "车牌", "value": "苏E·3K18"}, {"label": "任务", "value": "4号库提货"}]},
        {"id": "TRK-03", "type": "vehicle", "name": "园区摆渡车", "position": [-290, 0, 45], "speed": 12,
         "path": [[-290, 0, 45], [290, 0, 45]], "status": "normal"},
        {"id": "TRK-04", "type": "vehicle", "name": "AGV 搬运车", "position": [-280, 0, -115], "speed": 8,
         "path": [[-280, 0, -115], [-40, 0, -115]], "status": "normal"},
        {"id": "TRK-05", "type": "vehicle", "name": "堆场正面吊", "position": [290, 0, 180], "speed": 9,
         "path": [[290, 0, 180], [-110, 0, 180]], "status": "normal"}
    ]
    # —— 环境配景：草坪 / 道路 / 绿化 / 停车 / 路灯 ——
    c["devices"] += [
        {"id": "LN-01", "type": "lawn", "ambient": True, "name": "中央绿地西",
         "position": [-45, 0, 15], "size": [52, 56]},
        {"id": "LN-02", "type": "lawn", "ambient": True, "name": "中央绿地东",
         "position": [45, 0, 15], "size": [52, 56]},
        {"id": "LN-03", "type": "lawn", "ambient": True, "name": "入口景观绿地",
         "position": [-120, 0, 250], "size": [150, 60]},
        {"id": "LN-04", "type": "lawn", "ambient": True, "name": "综合楼景观绿地",
         "position": [235, 0, 190], "size": [110, 50]},
        {"id": "LN-05", "type": "lawn", "ambient": True, "name": "北侧生态绿带",
         "position": [-95, 0, -274], "size": [440, 52]},
        {"id": "LN-06", "type": "lawn", "ambient": True, "name": "东侧生态绿带",
         "position": [268, 0, 90], "size": [104, 130]},
        {"id": "LN-07", "type": "lawn", "ambient": True, "name": "西侧生态绿带",
         "position": [-262, 0, 155], "size": [110, 110]},
        {"id": "LN-08", "type": "lawn", "ambient": True, "name": "西北绿地",
         "position": [-260, 0, -240], "size": [120, 90]},
        {"id": "RD-01", "type": "road", "ambient": True, "name": "园区主大道",
         "position": [0, 0, 15], "size": [20, 580]},
        {"id": "RD-02", "type": "road", "ambient": True, "name": "北横通道",
         "position": [0, 0, -115], "size": [16, 640], "rotation": 90},
        {"id": "RD-03", "type": "road", "ambient": True, "name": "中横通道",
         "position": [0, 0, 45], "size": [14, 640], "rotation": 90},
        {"id": "RD-04", "type": "road", "ambient": True, "name": "南横通道",
         "position": [0, 0, 180], "size": [14, 640], "rotation": 90},
        {"id": "RD-05", "type": "road", "ambient": True, "name": "西纵通道",
         "position": [-170, 0, 20], "size": [12, 560]},
        {"id": "RD-06", "type": "road", "ambient": True, "name": "东纵通道",
         "position": [170, 0, 20], "size": [12, 560]},
        {"id": "GR-01", "type": "grove", "ambient": True, "name": "主大道行道树",
         "position": [-16, 0, 20], "size": [14, 520], "count": 44, "seed": 5},
        {"id": "GR-02", "type": "grove", "ambient": True, "name": "南围墙绿化带（东段）",
         "position": [190, 0, 288], "size": [290, 22], "count": 24, "seed": 11},
        {"id": "GR-02W", "type": "grove", "ambient": True, "name": "南围墙绿化带（西段）",
         "position": [-190, 0, 288], "size": [290, 22], "count": 24, "seed": 19},
        {"id": "GR-08", "type": "grove", "ambient": True, "name": "主大道东侧行道树",
         "position": [17, 0, 30], "size": [12, 460], "count": 34, "seed": 23},
        {"id": "GR-03", "type": "grove", "ambient": True, "name": "北围墙绿化带",
         "position": [-40, 0, -288], "size": [560, 22], "count": 42, "seed": 21},
        {"id": "GR-04", "type": "grove", "ambient": True, "name": "西绿化带",
         "position": [-300, 0, 30], "size": [30, 480], "count": 30, "seed": 7},
        {"id": "GR-05", "type": "grove", "ambient": True, "name": "东绿化带",
         "position": [300, 0, 30], "size": [30, 480], "count": 30, "seed": 13},
        {"id": "PK-01", "type": "parking", "ambient": True, "name": "货车待卸停车场",
         "position": [-40, 0, 250], "cols": 10, "rows": 2, "occupied": 13, "seed": 9},
        {"id": "PK-02", "type": "parking", "ambient": True, "name": "综合楼停车场",
         "position": [235, 0, 205], "cols": 9, "rows": 2, "occupied": 11, "seed": 4},
        {"id": "GR-06", "type": "grove", "ambient": True, "name": "北侧绿带树林",
         "position": [-95, 0, -274], "size": [430, 46], "count": 46, "seed": 31},
        {"id": "GR-07", "type": "grove", "ambient": True, "name": "东侧绿带树林",
         "position": [268, 0, 90], "size": [96, 120], "count": 22, "seed": 41},
        {"id": "LP-01", "type": "lampRow", "ambient": True, "name": "主大道照明", "height": 10,
         "points": [[12, 0, -275], [12, 0, 295]]},
        {"id": "LP-02", "type": "lampRow", "ambient": True, "name": "北横照明", "height": 9,
         "points": [[-300, 0, -107], [300, 0, -107]]},
        {"id": "LP-03", "type": "lampRow", "ambient": True, "name": "南横照明", "height": 9,
         "points": [[-300, 0, 188], [300, 0, 188]]}
    ]
    # —— 外部 GLB：AI 生成的智慧仓库（贴图已压至 1K，单文件内联） ——
    c["models"] = [
        {"id": "WH-05", "name": "5号智能仓", "url": "models/ai-warehouse.glb",
         "position": [-95, 0, 118], "rotation": 0, "scale": 1, "status": "normal",
         "fallback": {"type": "warehouse", "size": [110, 29.5, 82], "roof": "flat", "seeThrough": True},
         "metrics": [{"label": "AGV 在岗", "value": "18 台"},
                     {"label": "库容利用率", "value": "69%", "pct": 69},
                     {"label": "屋顶光伏", "value": "220 kWp"}]}
    ]
    c["alerts"] = [
        {"deviceId": "YARD-01", "level": "critical", "text": "集装箱堆存超限 94%", "time": "10:31"},
        {"deviceId": "RACK-D", "level": "critical", "text": "2号库 B 区货位占用 93%", "time": "10:12"},
        {"deviceId": "WH-04", "level": "warning", "text": "冷链库温偏高 -16.2℃", "time": "09:58"},
        {"deviceId": "GATE-01", "level": "warning", "text": "闸口排队 8 辆，通行超时", "time": "10:26"}
    ]
    c["patrol"] = {"enabled": True, "duration": 72, "loop": True, "autoStart": False, "height": 58,
                   "waypoints": [[300, 58, 290], [300, 58, -260], [-300, 58, -260], [-300, 58, 60],
                                 [-40, 58, 120], [300, 58, 180]]}
    return c


def preset_mine(title):
    """露天铁矿数字孪生：台阶式采场 + 螺旋运输干线 + 电铲/钻机/矿卡 + 破碎输送 + 排土场"""
    import math
    c = _common(title or "青山露天铁矿 · 数字孪生",
                "台阶式露天采场 · 电铲钻机矿卡 · 破碎输送 · 排土场 · Mock 数据")
    c["sceneType"] = "mine"
    # 场地：tex-ground 土石地面贴图（低对比可用高 repeat）+ 粉尘 haze + 物理白天天空
    c["env"].update({"preset": "day", "sky": "shader", "realism": True,
                     "ground": "#3a3428", "groundTex": "concrete", "groundTexRepeat": 28,
                     "gridOpacity": 0,
                     "gridSize": 3400, "gridDivisions": 68,
                     "haze": [0xa89a82, 800, 3400], "exposure": 1.02,
                     "sunDirection": [-150, 230, 280], "sunIntensity": 3.0})
    c["camera"].update({"fov": 45, "position": [760, 580, 900], "target": [0, -40, 0],
                        "autoFit": False, "minDistance": 60, "maxDistance": 4200,
                        "maxPolarAngle": 1.45})
    # 阴影图：骨架 realism 模式下自动取 4096，无需在此覆盖

    # ---- 采场几何（与骨架 buildPit 同一公式；半径按圆算，group 整体压扁成椭圆） ----
    RX, RZ, BH, N, BERM = 330.0, 268.0, 12.0, 13, 7.0
    SETBACK = BH / math.tan(math.radians(65))
    r_out = [RX]
    for i in range(1, N + 1):
        r_out.append(r_out[i - 1] - (0 if i == 1 else BERM) - SETBACK)
    floor_r = r_out[N] - BERM

    def ptx(th, radius, y):
        t = math.radians(th)
        return [round(radius * math.cos(t), 1), round(y, 1), round(radius * math.sin(t), 1)]

    def bench_road_r(i):
        return r_out[i] - BERM / 2.0

    def face_center(th):                       # 电铲/钻机车头（+Z）朝向坑心
        t = math.radians(th)
        return round(math.degrees(math.atan2(-math.cos(t), -math.sin(t))), 1)

    b, d = [], []
    b.append({"id": "PIT-01", "type": "pit", "name": "露天采场", "position": [0, 0, 0],
              "rx": RX, "rz": RZ, "depth": N * BH, "benchHeight": BH, "slope": 65, "berm": BERM,
              "status": "normal", "tagHeight": 120,
              "metrics": [{"label": "采场深度", "value": "156 m"},
                          {"label": "台阶数", "value": "13 个"},
                          {"label": "当前推进", "value": "-108 m 平台"},
                          {"label": "境界尺寸", "value": "660 × 536 m"},
                          {"label": "边坡角", "value": "65°"}]})
    # 地面在采场开口处挖椭圆洞（略小于境界，坑壁从洞口中"长出"不露缝）
    c["env"]["pitHole"] = {"x": 0, "z": 0, "rx": RX - 2, "rz": RZ - 2}

    # ---- 螺旋运输干线：坑底 → 地表（坡度 8%，贴帮盘旋） ----
    RUN = BH / 0.08
    TH0 = 134.0
    ramp = [ptx(TH0 + 30, floor_r * 0.5, -N * BH)]
    th = TH0
    for i in range(N, 0, -1):
        r_i = bench_road_r(i) - 9.0
        dth = math.degrees(RUN / max(80.0, r_i))
        th += dth
        if i < N:                              # 坡面中点（上下两级平台之间）
            r_wall = (r_out[i] + r_out[i + 1] - BERM) / 2.0
            ramp.append(ptx(th - dth / 2, r_wall - 13.0, -(i + 0.5) * BH))
        ramp.append(ptx(th, r_i, -i * BH))
    ramp.append(ptx(th + 16, (RX + r_out[1]) / 2.0 - 6, -BH / 2))
    ramp.append(ptx(th + 28, RX + 8, 0.8))
    ramp.append(ptx(th + 40, RX + 70, 1.3))
    exit_th = th + 40
    d.append({"id": "DRMP-01", "type": "ramp", "name": "采场螺旋运输干线", "width": 26,
              "points": ramp, "status": "normal", "tagHeight": 70,
              "metrics": [{"label": "干线长度", "value": "≈ 3.1 km"},
                          {"label": "最大坡度", "value": "8 %"},
                          {"label": "路面宽度", "value": "26 m"},
                          {"label": "日均车次", "value": "1,860"}]})

    # ---- 地表环线（八边形 R=460，避开采场） ----
    OCT_R = 460.0
    oct_v = [ptx(a, OCT_R, 1.5) for a in (270, 315, 0, 45, 90, 135, 180, 225)]
    # 坑内环线：坑底 → 螺旋干线 → 出坑口 → 沿环线北缘 → 破碎站卸载 → 原路返回（闭合）
    exit_th = math.degrees(math.atan2(ramp[-1][2], ramp[-1][0]))
    up_surface = [ptx(315, OCT_R, 1.5), (163, 1.5, -393), (0, 1.5, -460), (-30, 1.5, -515), (8, 1.5, -540)]
    back_surface = [(95, 1.5, -542), (230, 1.5, -520), (330, 1.5, -470), ptx(exit_th + 3, 385, 1.3)]
    haul_loop = list(ramp) + up_surface + back_surface + list(reversed(ramp))

    # ---- 排土场动线 ----
    dump_ramp = [(700, 1.2, -100), (672, 8, -140), (645, 15, -175), (620, 22, -205),
                 (598, 28, -230), (580, 33, -252), (562, 37, -268), (540, 40, -278), (525, 40.3, -284)]
    dump_tip = (512, 40.5, -290)
    dump_loop = ([(8, 1.5, -540), (95, 1.5, -542), (240, 1.5, -520), (420, 1.5, -430), (560, 1.5, -380),
                  (640, 1.5, -300), (688, 1.5, -210)] + dump_ramp + [dump_tip] +
                 list(reversed(dump_ramp)) + [(640, 1.5, -300), (420, 1.5, -430), (240, 1.5, -520), (8, 1.5, -540)])
    d.append({"id": "DRMP-02", "type": "ramp", "name": "排土场斜坡道", "width": 22,
              "points": dump_ramp, "status": "normal",
              "metrics": [{"label": "台阶高度", "value": "40 m"},
                          {"label": "排土线", "value": "2 条"}]})

    # ---- 外运环线（堆场 → 大门）沿八边形环线 ----
    gate_loop = ([(250, 1.5, -620), (0, 1.5, -645), (0, 1.5, -478)] + oct_v[:5] +
                 [(0, 1.5, 560), (-45, 1.5, 585), (-45, 1.5, 420)] + oct_v[5:] +
                 [(0, 1.5, -478), (0, 1.5, -645), (85, 1.5, -632), (250, 1.5, -620)])

    # ---- 采场设备：电铲 / 钻机（坐在对应台阶道路上） ----
    d += [
        {"id": "EXC-01", "type": "excavator", "name": "1号电铲", "phase": 0.0, "scale": 1.0,
         "position": ptx(140, bench_road_r(3) + 0.1, -3 * BH + 0.08), "rotation": face_center(140),
         "status": "normal",
         "metrics": [{"label": "斗容", "value": "13 m³"}, {"label": "今日铲装", "value": "8,640 m³"},
                     {"label": "作业台阶", "value": "-36 m"}]},
        {"id": "EXC-02", "type": "excavator", "name": "2号电铲", "phase": 0.4, "scale": 1.12,
         "position": ptx(320, bench_road_r(7) + 0.1, -7 * BH + 0.08), "rotation": face_center(320),
         "status": "normal",
         "metrics": [{"label": "斗容", "value": "16 m³"}, {"label": "今日铲装", "value": "9,210 m³"},
                     {"label": "作业台阶", "value": "-84 m"}]},
        {"id": "EXC-03", "type": "excavator", "name": "3号电铲", "phase": 0.8, "scale": 1.0,
         "position": ptx(95, bench_road_r(11) + 0.1, -11 * BH + 0.08), "rotation": face_center(95),
         "status": "normal",
         "metrics": [{"label": "斗容", "value": "10 m³"}, {"label": "今日铲装", "value": "6,480 m³"},
                     {"label": "作业台阶", "value": "-132 m"}]},
        {"id": "DRL-01", "type": "drill", "name": "1号牙轮钻机", "phase": 0.0,
         "position": ptx(40, bench_road_r(2) + 0.1, -2 * BH + 0.08), "rotation": face_center(40),
         "status": "normal",
         "metrics": [{"label": "孔径", "value": "250 mm"}, {"label": "今日穿孔", "value": "412 m"},
                     {"label": "钻速", "value": "0.8 m/min"}]},
        {"id": "DRL-02", "type": "drill", "name": "2号牙轮钻机", "phase": 2.5,
         "position": ptx(225, bench_road_r(5) + 0.1, -5 * BH + 0.08), "rotation": face_center(225),
         "status": "warn",
         "metrics": [{"label": "孔径", "value": "250 mm"}, {"label": "今日穿孔", "value": "268 m"},
                     {"label": "液压油温", "value": "78 ℃"}]}]

    # ---- 矿卡动线 ----
    TRK_METRICS = [{"label": "载重", "value": "130 吨"}, {"label": "燃油", "value": "62 %"},
                   {"label": "车速", "value": "28 km/h"}]
    d += [
        {"id": "TRK-01", "type": "haulTruck", "name": "矿卡 01（重车）", "loaded": True, "phase": 0.0,
         "position": haul_loop[0], "speed": 11, "path": haul_loop, "status": "normal",
         "metrics": TRK_METRICS + [{"label": "车牌", "value": "蒙B·88021"}, {"label": "任务", "value": "采场 → 破碎站"}]},
        {"id": "TRK-02", "type": "haulTruck", "name": "矿卡 02（空车）", "loaded": False, "phase": 0.45,
         "position": haul_loop[0], "speed": 11, "path": haul_loop, "status": "normal",
         "metrics": TRK_METRICS + [{"label": "车牌", "value": "蒙B·88026"}, {"label": "任务", "value": "破碎站 → 采场"}]},
        {"id": "TRK-03", "type": "haulTruck", "name": "矿卡 03（排土）", "loaded": True, "phase": 0.2,
         "position": dump_loop[0], "speed": 10, "path": dump_loop, "status": "warn",
         "metrics": TRK_METRICS + [{"label": "车牌", "value": "蒙B·88113"}, {"label": "任务", "value": "破碎站 → 排土场"}]},
        {"id": "TRK-04", "type": "haulTruck", "name": "矿卡 04（外运）", "loaded": True, "phase": 0.6,
         "position": gate_loop[0], "speed": 10, "path": gate_loop, "status": "normal",
         "metrics": TRK_METRICS + [{"label": "车牌", "value": "蒙B·88137"}, {"label": "任务", "value": "堆场 → 大门外运"}]},
        {"id": "TRK-05", "type": "haulTruck", "name": "矿卡 05（台阶倒运）", "loaded": True, "phase": 0.0,
         "position": ptx(300, bench_road_r(7) + 0.08, -7 * BH + 0.08), "speed": 7,
         "path": [ptx(a, bench_road_r(7) + 0.08, -7 * BH + 0.08) for a in (300, 340, 20, 60, 300)],
         "status": "normal",
         "metrics": [{"label": "载重", "value": "130 吨"}, {"label": "任务", "value": "电铲 ↔ 干线路口"}]},
        {"id": "WTR-01", "type": "vehicle", "name": "洒水车", "body": "tank", "size": 1.15, "phase": 0.0,
         "position": oct_v[0], "speed": 7, "path": oct_v + [oct_v[0]], "status": "normal",
         "metrics": [{"label": "水箱", "value": "32 m³"}, {"label": "今日洒水", "value": "14 车次"},
                     {"label": "任务", "value": "环线道路降尘"}]},
        {"id": "SVC-01", "type": "vehicle", "name": "指挥车", "body": "pickup", "size": 0.62, "phase": 0.0,
         "position": (-500, 1.5, 430), "speed": 9,
         "path": [(-500, 1.5, 430), (-320, 1.5, 470), (-280, 1.5, 340), (-460, 1.5, 330), (-500, 1.5, 430)],
         "status": "normal",
         "metrics": [{"label": "车牌", "value": "蒙B·5T021"}, {"label": "任务", "value": "生产指挥巡查"}]}]

    # ---- 工业场地：破碎站 / 输送廊道 / 堆场 / 排土场 ----
    d += [
        {"id": "CRU-01", "type": "crusher", "name": "半移动破碎站", "position": [0, 0, -560],
         "status": "normal", "tagHeight": 40,
         "metrics": [{"label": "处理能力", "value": "6,000 t/h"}, {"label": "今日破碎", "value": "4.28 万吨"},
                     {"label": "给料粒度", "value": "≤ 1,200 mm"}, {"label": "排料口", "value": "250 mm"}]},
        {"id": "BELT-01", "type": "conveyor", "name": "至堆场皮带廊", "position": [75, 9, -545],
         "rotation": -12, "length": 120, "status": "normal",
         "metrics": [{"label": "带速", "value": "2.5 m/s"}, {"label": "今日输送", "value": "4.28 万吨"},
                     {"label": "运距", "value": "120 m"}]},
        {"id": "YARD-01", "type": "yard", "name": "原矿堆场", "position": [220, 0, -600],
         "size": [170, 80], "stack": "cone", "rows": 3, "cols": 7, "status": "normal",
         "metrics": [{"label": "堆存量", "value": "18.6 万吨"}, {"label": "堆高", "value": "14 m"},
                     {"label": "堆位利用率", "value": "71 %", "pct": 71}]},
        {"id": "YARD-02", "type": "yard", "name": "块矿堆场", "position": [360, 0, -480],
         "size": [130, 70], "stack": "box", "rows": 2, "cols": 6, "status": "normal",
         "metrics": [{"label": "堆存量", "value": "7.2 万吨"}, {"label": "堆高", "value": "11 m"}]},
        {"id": "DUMP-01", "type": "dump", "name": "排土场", "position": [470, 0, -260],
         "radius": 150, "height": 40, "steps": 4, "status": "normal", "tagHeight": 60,
         "metrics": [{"label": "已排容量", "value": "2,860 万m³"}, {"label": "剩余容量", "value": "4,120 万m³"},
                     {"label": "台阶数", "value": "4 个"}, {"label": "日排土量", "value": "17.3 万m³"}]},
        {"id": "DZR-01", "type": "dozer", "name": "排土场推土机", "blade": 78,
         "position": [442, 40.3, -250], "rotation": 200, "status": "normal",
         "metrics": [{"label": "型号", "value": "SD32"}, {"label": "今日推土", "value": "3,400 m³"},
                     {"label": "任务", "value": "排土线整理"}]},
        {"id": "DZR-02", "type": "dozer", "name": "破碎站推土机", "blade": 62,
         "position": [-55, 0, -505], "rotation": 25, "status": "normal",
         "metrics": [{"label": "型号", "value": "SD22"}, {"label": "任务", "value": "受料坑清理"}]},
        {"id": "MON-01", "type": "monitor", "name": "北帮边坡监测点", "position": [0, 0, -288],
         "status": "alarm",
         "metrics": [{"label": "累计位移", "value": "32 mm"}, {"label": "位移速率", "value": "2.1 mm/天"},
                     {"label": "阈值", "value": "25 mm"}, {"label": "监测频率", "value": "1 次/小时"}]}]

    # ---- 高杆灯塔 ----
    for i, (x, z) in enumerate([(-22, -470), (450, 22), (22, 470), (-450, -22), (-130, -610), (690, -410)]):
        d.append({"id": "LT-0%d" % (i + 1), "type": "lightTower", "name": "高杆灯塔 %d" % (i + 1),
                  "position": [x, 0, z], "height": 28, "status": "normal",
                  "metrics": [{"label": "灯杆高度", "value": "28 m"}, {"label": "照明范围", "value": "≈ 180 m"},
                              {"label": "功率", "value": "4 × 400 W"}]})

    # ---- 辅助设施：办公楼 / 维修车间 / 油库 / 沉淀池 / 大门 ----
    b += [
        {"id": "OFF-01", "type": "office", "name": "矿综合办公楼", "position": [-480, 0, 400],
         "size": [46, 30, 28], "floors": 7, "podium": 2, "roofUnits": 3, "status": "normal",
         "metrics": [{"label": "在岗", "value": "126 人"}, {"label": "今日来访", "value": "23 人"}]},
        {"id": "WH-01", "type": "warehouse", "name": "机修车间", "position": [-320, 0, 450],
         "size": [80, 14, 36], "roof": "flat", "status": "normal",
         "metrics": [{"label": "在修设备", "value": "5 台"}, {"label": "今日保养", "value": "9 台"}]}]
    d += [
        {"id": "TANK-01", "type": "tank", "name": "1号柴油罐", "position": [-640, 0, 280],
         "radius": 10, "height": 16, "level": 0.62, "status": "normal",
         "metrics": [{"label": "液位", "value": "62 %", "pct": 62}, {"label": "储量", "value": "486 m³"}]},
        {"id": "TANK-02", "type": "tank", "name": "2号柴油罐", "position": [-640, 0, 230],
         "radius": 10, "height": 16, "level": 0.41, "status": "warn",
         "metrics": [{"label": "液位", "value": "41 %", "pct": 41}, {"label": "储量", "value": "322 m³"}]},
        {"id": "POND-01", "type": "pond", "name": "矿井水沉淀池", "position": [-600, 0, 120],
         "radius": 45, "status": "normal",
         "metrics": [{"label": "处理能力", "value": "3,600 m³/天"}, {"label": "悬浮物", "value": "38 mg/L"},
                     {"label": "回用率", "value": "86 %", "pct": 86}]},
        {"id": "GATE-01", "type": "gate", "name": "矿区主大门", "position": [0, 0, 620],
         "width": 36, "sign": "青山露天铁矿", "signSub": "QINGSHAN OPEN-PIT IRON MINE", "status": "warn",
         "metrics": [{"label": "今日进出", "value": "1,264 车次"}, {"label": "排队车辆", "value": "6"},
                     {"label": "平均通行", "value": "52 s"}]}]

    # ---- 环境配景（ambient：不拾取 / 不进清单 / 不参与取景） ----
    d += [
        {"id": "FENCE-01", "type": "fence", "ambient": True, "name": "矿区围墙", "height": 2.6,
         "closed": False,
         "points": [[25, 0, 700], [800, 0, 700], [800, 0, -700], [-800, 0, -700], [-800, 0, 700], [-25, 0, 700]]},
        # 八边形地表环线（每边一段直路）
        *([{"id": "RD-O%d" % i, "type": "road", "ambient": True, "name": "地表环线",
            "position": [round((oct_v[i][0] + oct_v[(i + 1) % 8][0]) / 2, 1), 0,
                         round((oct_v[i][2] + oct_v[(i + 1) % 8][2]) / 2, 1)],
            "size": [16, round(2 * OCT_R * math.sin(math.radians(22.5)), 1)],
            "rotation": round(math.degrees(math.atan2(oct_v[(i + 1) % 8][0] - oct_v[i][0],
                                                      oct_v[(i + 1) % 8][2] - oct_v[i][2])), 1)}
           for i in range(8)]),
        # 放射性道路：北（破碎站）/ 东北（排土场）/ 西南（办公区）/ 南（大门）/ 西（油库）
        {"id": "RD-N", "type": "road", "ambient": True, "name": "至破碎站道路",
         "position": [0, 0, -550], "size": [16, 180]},
        {"id": "RD-DUMP", "type": "road", "ambient": True, "name": "至排土场道路",
         "position": [503, 0, -233], "size": [14, 400], "rotation": 62},
        {"id": "RD-SW", "type": "road", "ambient": True, "name": "至办公区道路",
         "position": [-398, 0, 358], "size": [14, 159], "rotation": -66},
        {"id": "RD-S", "type": "road", "ambient": True, "name": "大门道路",
         "position": [0, 0, 550], "size": [18, 180]},
        {"id": "RD-W", "type": "road", "ambient": True, "name": "至油库道路",
         "position": [-550, 0, 60], "size": [12, 216], "rotation": -56},
        # 办公区绿化
        {"id": "LN-01", "type": "lawn", "ambient": True, "name": "办公区绿地",
         "position": [-540, 0, 420], "size": [170, 90]},
        {"id": "GR-01", "type": "grove", "ambient": True, "name": "西侧防风林",
         "position": [-620, 0, 430], "size": [36, 110], "count": 20, "seed": 5},
        {"id": "GR-02", "type": "grove", "ambient": True, "name": "办公区绿化带",
         "position": [-480, 0, 510], "size": [150, 26], "count": 16, "seed": 9},
        # 停车场
        {"id": "PK-01", "type": "parking", "ambient": True, "name": "办公区停车场",
         "position": [-400, 0, 300], "cols": 8, "rows": 2, "seed": 5},
        {"id": "PK-02", "type": "parking", "ambient": True, "name": "设备停车场",
         "position": [-280, 0, -560], "cols": 6, "rows": 2, "seed": 9},
        {"id": "PK-03", "type": "parking", "ambient": True, "name": "大门待检停车场",
         "position": [-90, 0, 560], "cols": 4, "rows": 1, "seed": 13},
        # 路灯带
        {"id": "LP-01", "type": "lampRow", "ambient": True, "name": "破碎站路照明", "height": 10,
         "points": [[-11, 0, -470], [-11, 0, -630]]},
        {"id": "LP-02", "type": "lampRow", "ambient": True, "name": "排土场路照明", "height": 10,
         "points": [[340, 0, -330], [672, 0, -148]]},
        {"id": "LP-03", "type": "lampRow", "ambient": True, "name": "大门路照明", "height": 9,
         "points": [[-12, 0, 470], [-12, 0, 615]]},
        {"id": "LP-04", "type": "lampRow", "ambient": True, "name": "环线东照明", "height": 10,
         "points": [[326, 0, -300], [326, 0, 300]]},
        {"id": "LP-05", "type": "lampRow", "ambient": True, "name": "环线西照明", "height": 10,
         "points": [[-326, 0, -300], [-326, 0, 300]]},
        {"id": "LP-06", "type": "lampRow", "ambient": True, "name": "办公区路照明", "height": 9,
         "points": [[-335, 0, 315], [-462, 0, 386]]},
        {"id": "LP-07", "type": "lampRow", "ambient": True, "name": "油库路照明", "height": 9,
         "points": [[-470, 0, 10], [-628, 0, 112]]}]

    c["buildings"], c["devices"] = b, d
    c["kpis"] = [
        {"label": "原矿日产", "value": "4.28", "unit": "万吨"},
        {"label": "采剥总量", "value": "21.6", "unit": "万m³"},
        {"label": "剥采比", "value": "4.8", "unit": "t/t"},
        {"label": "设备出动率", "value": "92.6", "unit": "%"},
        {"label": "平均运距", "value": "3.6", "unit": "km"},
        {"label": "日柴油消耗", "value": "86", "unit": "t"},
        {"label": "边坡监测点", "value": "42", "unit": "个"},
        {"label": "未处理告警", "value": "4", "unit": "条"}]
    c["alerts"] = [
        {"deviceId": "MON-01", "level": "critical", "text": "北帮边坡累计位移 32mm，超阈值 25mm", "time": "11:26"},
        {"deviceId": "TRK-03", "level": "warning", "text": "矿卡超速报警 38km/h（限速 30）", "time": "11:15"},
        {"deviceId": "BELT-01", "level": "warning", "text": "皮带机运行跑偏 12mm", "time": "10:58"},
        {"deviceId": "DRL-02", "level": "warning", "text": "钻机液压油温偏高 78℃", "time": "10:41"}]
    c["patrol"] = {"enabled": True, "duration": 96, "loop": True, "autoStart": False,
                   "waypoints": [[round(820 * math.cos(math.radians(a)), 1), 430,
                                  round(680 * math.sin(math.radians(a)), 1)] for a in range(0, 360, 45)]}
    return c


PRESETS = {"warehouse": preset_warehouse, "plant": preset_plant,
           "park": preset_park, "bulk": preset_bulk, "campus": preset_campus,
           "logisticspark": preset_logisticspark, "mine": preset_mine}


# ----------------------------------------------------------------------------- 主流程
def build_config(args):
    if args.config:
        with io.open(args.config, "r", encoding="utf-8") as f:
            return json.load(f)
    fn = PRESETS.get(args.scene or "warehouse")
    if not fn:
        sys.exit("未知场景 preset：%s（可选：%s）" % (args.scene, ", ".join(PRESETS)))
    cfg = fn(args.title)
    if args.auto_fit is False:
        cfg["camera"] = dict(cfg.get("camera", {}), autoFit=False)
    if args.refresh_ms:
        cfg["dataSource"] = dict(cfg.get("dataSource", {}), refreshMs=args.refresh_ms)
    return cfg


def main():
    ap = argparse.ArgumentParser(description="生成 Three.js 数字孪生原型页面")
    ap.add_argument("--scene", default="warehouse", help="场景预设 warehouse|plant|park|bulk|campus（campus=写实园区）")
    ap.add_argument("--title", default=None, help="页面标题（不传则用预设默认标题）")
    ap.add_argument("--config", default=None, help="外部 JSON 配置（覆盖 --scene 预设）")
    ap.add_argument("--out", default=None, help="输出 HTML 路径")
    ap.add_argument("--dump-config", default=None, help="只导出配置 JSON 到指定路径，不生成页面")
    ap.add_argument("--refresh-ms", type=int, default=None, help="数据刷新间隔毫秒")
    ap.add_argument("--no-auto-fit", dest="auto_fit", action="store_false", help="禁用装配后自动取景")
    ap.add_argument("--list", action="store_true", help="列出可用场景预设")
    ap.add_argument("--skeleton", default=SKELETON, help="骨架 HTML 路径（默认用技能自带骨架）")
    ap.add_argument("--no-inline", action="store_true",
                    help="不把贴图内联成 data URI（需把骨架同目录的 img/ 一起复制，否则回退纯色）")
    ap.add_argument("--offline-three", action="store_true",
                    help="内联 three.js r160 全模块为 importmap data URI，页面零 CDN 依赖（CDN 不可达/内网环境必开）")
    ap.add_argument("--quality", default=None,
                    help="画质档位 potato|low|medium|high|ultra（默认 auto：按 GPU 型号自动挑，运行时还会掉帧降档）")
    ap.add_argument("--tex-max", type=int, default=0,
                    help="贴图降采样上限（像素，如 1024）：内联前缩小并重编码，体积/显存双降")
    ap.add_argument("--hdri-max", type=int, default=0,
                    help="HDR 天空降采样宽度上限（如 1024）：只服务 PMREM 反射，降一半看不出")
    ap.add_argument("--lite", action="store_true",
                    help="集显构建预设 = --quality low + --tex-max 1024 + --hdri-max 1024")
    args = ap.parse_args()

    if args.lite:                                     # 集显一键档：性能与体积同时降
        args.quality = args.quality or "low"
        args.tex_max = args.tex_max or 1024
        args.hdri_max = args.hdri_max or 512          # HDR 只服务 PMREM 反射，512 宽足够
        print("集显构建模式：quality=%s / 贴图≤%dpx / HDR≤%dpx"
              % (args.quality, args.tex_max, args.hdri_max))

    if args.list:
        print("\n".join("%-10s %s" % (k, (v("示例").get("meta", {}).get("subtitle") or ""))
                        for k, v in PRESETS.items()))
        return

    default_title = PRESETS[args.scene or "warehouse"]("示例")["meta"]["title"]
    args.title = args.title or default_title
    cfg = build_config(args)
    # v0.11：画质档位 / 贴图上限写进 CONFIG.performance（骨架在 new WebGLRenderer 之前读取）
    if args.quality or args.tex_max:
        perf = dict(cfg.get("performance") or {})
        if args.quality:
            perf["quality"] = args.quality
        if args.tex_max:
            perf["texMaxSize"] = args.tex_max
        cfg["performance"] = perf
    # 显式落 CONFIG.textures：离线引擎内联后，运行时据此读已内联的 data URI
    if isinstance(cfg.get("textures"), dict):
        cfg["textures"] = dict(DEFAULT_TEXTURES, **cfg["textures"])
    else:
        cfg["textures"] = dict(DEFAULT_TEXTURES)
    # 只有贴图天空（env.sky='texture'）才需要三张全景图；shader 物理天空不用
    if (cfg.get("env") or {}).get("sky") == "texture":
        cfg["textures"].update({"skyDay": "img/sky-day.jpg", "skySunset": "img/sky-sunset.jpg",
                                "skyNight": "img/sky-night.jpg"})
    # HDRI 实拍天空（env.sky='hdri'）：day/sunset 两张 HDR（Poly Haven CC0）
    if (cfg.get("env") or {}).get("sky") == "hdri":
        cfg["textures"].update({"hdriDay": "hdri/sky-day.hdr",
                                "hdriSunset": "hdri/sky-sunset.hdr"})

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
    if INJECT_MARK not in html:
        sys.exit("骨架结构异常：未找到 <script type=\"module\"> 注入点")

    inject = ('<script id="twin-config">\nwindow.__TWIN_CONFIG__ = ' +
              json.dumps(cfg, ensure_ascii=False, indent=2) + ';\n</script>\n')
    html = html.replace(INJECT_MARK, inject + INJECT_MARK, 1)

    if not args.no_inline:
        html, used = inline_images(html, os.path.join(os.path.dirname(args.skeleton), IMG_DIRNAME),
                                   max_tex=args.tex_max)
        print("已内联贴图 %d 张：%s" % (len(used), ", ".join(used) if used else "（未找到 img/ 目录）"))

        # HDRI 实拍天空（hdri/sky-*.hdr → data URI），env.sky='hdri' 时才存在
        html, hdri_used = inline_hdri(html, os.path.dirname(args.skeleton), max_w=args.hdri_max)
        if hdri_used:
            total = sum(s for _, s in hdri_used)
            print("已内联 HDRI 天空 %d 张：%s（共 %.1f MB）" %
                  (len(hdri_used), ", ".join(n for n, _ in hdri_used), total / 1048576.0))

        # 外部模型（models/xxx.glb → data URI）；DRACO 压缩模型附带内联 decoder
        models_dir = os.path.join(os.path.dirname(args.skeleton), "models")
        html, models_used, draco_models = inline_models(html, models_dir)
        if models_used:
            total = sum(s for _, s in models_used)
            print("已内联模型 %d 个：%s（共 %.1f MB）" %
                  (len(models_used), ", ".join(n for n, _ in models_used), total / 1048576.0))
            if total > 8 * 1024 * 1024:
                print("警告：模型总体积 %.1f MB，data URI 会让 HTML 显著变大，建议减面或拆分场景"
                      % (total / 1048576.0))
        else:
            print("未内联模型：models/ 目录为空（外部 GLB 放 assets/models/，配置里声明 models[] 即可）")
        for bad in re.findall(r"models/[A-Za-z0-9._-]+\.(?:gltf|bin)", html):
            print("警告：%s 是多文件 glTF 资源，无法内联——请先在 Blender 导出 glTF Binary 或用 "
                  "gltf-pipeline 转成 .glb" % bad)
        if draco_models:
            html, ok = inject_draco(html, os.path.dirname(args.skeleton))
            print("Draco 压缩模型：%s → decoder %s" %
                  (", ".join(draco_models), "已内联（离线可用）" if ok else "缺失，回退 CDN"))
    else:
        print("未内联贴图/模型：请把骨架同目录的 img/ 与 models/ 一并复制，否则回退纯色/占位体")

    if args.offline_three:
        size_before = len(html)
        html = inline_three(html, args.skeleton)
        print("离线引擎：three.js r160 + 引擎已内联（+%.1f MB），页面零外网请求"
              % ((len(html) - size_before) / 1048576.0))

    out = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with io.open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print("原型已生成：%s" % out)
    print("资产：建筑 %d / 设备 %d / KPI %d / 告警 %d" %
          (len(cfg.get("buildings", [])), len(cfg.get("devices", [])),
           len(cfg.get("kpis", [])), len(cfg.get("alerts", []))))
    print("下一步：直接双击打开，或在目录内 python -m http.server 8000 后访问")


if __name__ == "__main__":
    main()
