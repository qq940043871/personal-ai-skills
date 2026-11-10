---
name: visual-real-twin
display_name: 实景孪生资产管线（Blender）
display_name_en: Real-scene Digital Twin Asset Pipeline
description: "实景还原的 3D 数字孪生资产管线：当客户要求「按我们厂实际的样子来」（照片/CAD/实拍/设备清单）时，用 Blender MCP 半自动交互建模 → 命令行批处理导出优化（减面/贴图压缩/Draco GLB）→ GLB 体检（面数/体积/贴图预算）→ 一键集成到 visual-digital-twin / visual-threejs-scene 的 models[] 出最终大屏。无 Blender 环境自动降级程序化几何，不阻塞交付。触发词：实景还原、真实厂区、按实际建模、CAD、Blender、blender-mcp、GLB 优化、模型资产管线、实体孪生。"
description_zh: Blender MCP 实景建模 + CLI 导出优化 + GLB 体检 + 集成进孪生大屏 models[] 的编排技能；无 Blender 自动降级程序化几何。
description_en: Orchestration skill for real-scene digital-twin assets: Blender MCP modeling, CLI export optimization (decimate/texture/Draco), GLB validation, and integration into visual-digital-twin / visual-threejs-scene.
category: Design Tools
version: 0.1.0
author: hasWhere
tags: ["数字孪生", "Blender", "blender-mcp", "GLB", "实景还原", "资产管线", "Draco", "大屏"]
permissions:
  - file_read
  - file_write
  - command_exec
permission_notes_zh: 本 Skill 调用本机 Blender 可执行文件（--background 批处理）与 Python 脚本做模型导出与校验，读写用户指定目录；不联网、不上传数据。Blender MCP 需要用户自行安装 Blender 及其 MCP 插件。
---

# 实景孪生资产管线（Blender）

## 这个技能解决什么

三个姊妹技能（`visual-echarts-dashboard` / `visual-threejs-scene` / `visual-digital-twin`）的大屏生产链**已经闭环**，程序化几何能唬住 80% 的场景。缺的只有一小块：客户指着照片说"**我要按我们厂实际的样子来**"——这时候需要 Blender 出定制 GLB，然后喂回现有链路。

本技能就是这一小块的**编排层**：

```
[探测] probe_blender.py
   ├─ 有 Blender ──→ [路线 B：实景还原]
   │     ① Blender MCP 半自动建模（有照片/CAD/描述时，agent 经 MCP 操作）
   │     ② 保存 .blend
   │     ③ export_webgl.py（CLI 批处理：减面/贴图缩放/原点归底/Draco GLB）
   │     ④ validate_glb.py（面数/贴图/体积预算体检）
   │     ⑤ integrate_glb.py（拷入目标技能 assets/models/ + 生成 models[] 片段）
   │     ⑥ build_twin.py / build_three_bundle.py 出屏 + verify_screen.py 验证
   │
   └─ 无 Blender ──→ [路线 A：程序化降级]
         visual-threejs-scene 的 gen_models_blender.py？没有 Blender 也跑不了——
         直接用目标技能内置的程序化几何（rack/tank/pipeline/conveyor…）交付，
         并告知用户：装 Blender + blender-mcp 插件后可升级为实景还原。
```

### 与姊妹技能分工

| 你手上是什么 | 用哪个 |
|---|---|
| 程序化几何够用的孪生大屏（货架/储罐/管线…） | `visual-threejs-scene` / `visual-digital-twin` 直接干 |
| 纯 2D 图表大屏 | `visual-echarts-dashboard` |
| **客户要求按真实厂区/设备还原，需定制模型** | **本技能** → 产出 GLB → 交回上面两个 3D 技能出屏 |

**本技能不做大屏**。大屏生产链在姊妹技能里，这里只负责"把真实世界变成 GLB"这一段。

---

## 四条铁律

1. **MCP 只管建模创意环节，导出优化一律走 CLI 批处理**（`blender --background --python export_webgl.py`）。不要让 agent 经 MCP 一步步点导出设置——盲操作 Blender 每个截图回环好几秒，导出参数也让 agent 手调纯属浪费生命。
2. **米制真实尺寸、原点底部中心**。模型在 Blender 里按实物尺寸（米）建模，落地时 `position:[x,0,z]` 直接用，不猜缩放。原点在模型底部中心，与姊妹技能程序化资产一致。
3. **预算不过线不准进大屏**（见 `references/webgl-budget.md`）：单模型 ≤5 万面、GLB ≤1.5MB（内联）/ ≤5MB（外置）、贴图最长边 ≤2048。`validate_glb.py` 说 FAIL 就回炉，没有商量。
4. **建模前先 probe**。Blender 不在 → 直接走程序化几何交付，同时告诉用户升级路径。**不要在没探测的情况下空谈 MCP**。

---

## 工作流

### 第 0 步：探测环境

```bash
python scripts/probe_blender.py          # 任意 python 都行（纯标准库）
```

输出 JSON 报告：Blender 路径/版本、blender-mcp addon 是否安装、uvx 是否可用（MCP server 依赖）。**exit 0 = 有 Blender**，按路线 B；否则路线 A 并提示用户升级。

### 第 1 步：建模（路线 B）

经 Blender MCP（`execute_blender_code` 工具，一次一轮 Python，效率最高）交互建模。建模规范见 `references/blender-mcp.md`，核心：

- 参考照片/CAD/设备清单先给用户确认建模清单（哪些设备、什么精度级别）
- 全部走"创建原语 + 数学设变换 + BEVEL 倒角"路线，**绝不依赖选中态**（headless/远程操作经典坑：旧物体仍选中，一转全跟着转）
- 每个设备一个独立 Collection，命名 `ASSET_<id>`，方便逐个导出
- 栏杆 1.1m、踏距 0.32m 等人体工学尺寸**不随主体缩放**
- 完成后 `bpy.ops.wm.save_as_mainfile()` 存 .blend（这是后续 CLI 导出的输入）

### 第 2 步：导出优化（CLI，不是 MCP）

```bash
blender --background --python scripts/export_webgl.py -- \
    --input scene.blend --out D:/tmp/out/tank.glb \
    --collection "ASSET_TANK-01" --decimate 0.5 --max-tex 2048 --draco --ground
```

支持输入 `.blend`（打开）或 `.glb/.gltf/.fbx/.obj`（导入，用于优化外部给的模型）。参数见脚本头部注释。

### 第 3 步：体检

```bash
python scripts/validate_glb.py D:/tmp/out/tank.glb           # 内联预算（默认 ≤2MB）
python scripts/validate_glb.py tank.glb --standalone          # 外置预算（≤5MB）
```

纯标准库解析 GLB 二进制：面数、Draco、贴图尺寸、模型包围盒尺寸（顺带验证米制尺度是否合理）。FAIL 必须回炉（调 decimate / max-tex）。

### 第 4 步：集成

```bash
python scripts/integrate_glb.py tank.glb --target twin \
    --name "1号储罐" --position "[190,0,40]" [--id TANK-01] [--config my.json]
```

自动定位目标技能目录（先找已安装的 `C:\Users\qq940\.agents\skills\`，再找工作区），拷贝 GLB 到其 `assets/models/`，打印 `models[]` 配置片段；给了 `--config` 就直接把条目合并进配置 JSON。之后照常：

```bash
python3 <digital-twin>/scripts/build_twin.py --scene factory --config my.json --out 孪生大屏.html
python3 <digital-twin>/scripts/verify_screen.py 孪生大屏.html --shot check.png --expect-mode 写实三维
```

---

## 输入参数（建模清单，交给第 1 步）

```jsonc
{
  "assets": [
    {
      "id": "TANK-01",            // 唯一键，告警/清单/聚焦回挂
      "name": "1号储罐",
      "refs": ["厂区照片.jpg", "储罐剖面.dwg"],   // 参考素材（可空 = 按描述建）
      "dims": {"diameter": 32, "height": 26},     // 实测/估算尺寸（米）
      "lod": "hero",              // hero 主角设备（细节拉满）| mid 常规 | bg 远景（减面优先）
      "materials": {"壁板": "防腐漆中灰蓝", "栏杆": "镀锌"}
    }
  ],
  "target": {"skill": "twin", "scene": "factory"}   // 集成目标
}
```

---

## 环境（《用户环境》已确认的坑）

- 脚本用系统 python 跑没问题（全部纯标准库，不依赖第三方库）
- `export_webgl.py` 必须**用 Blender 自带的 Python 解释器跑**（`blender --background --python` 自动用它），不要用系统 python 直接 import bpy
- Windows 下 Blender 通常在 `C:\Program Files\Blender Foundation\Blender <ver>\blender.exe`，probe 脚本会自动找
- blender-mcp addon 装在 `%APPDATA%\Blender Foundation\Blender\<ver>\`（4.2+ 在 `extensions/blender_org/`，旧版在 `scripts/addons/`），MCP server 用 `uvx blender-mcp` 启动
