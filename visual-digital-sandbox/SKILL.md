---
name: visual-digital-sandbox
display_name: 数字沙盘（真三维可漫游）
display_name_en: Digital Sandbox (Interactive 3D)
description: >
  把一块园区/厂区「做成一台能被环视、拉近、点亮、剖开的实体沙盘」，产出可双击打开的单文件 HTML：
  带厚度的沙盘台体与地层剖面、程序化楼宇厂房道路管线车流、图层点亮、X/Z 向剖切、点选查指标、
  机位巡游与时间轴推演，three 三源回退失败自动降级等距二维。
  要开箱即用的孪生大屏（城市/工厂/港口模板 + KPI 面板）走 visual-digital-twin；
  要 GLB 实景模型、Blender 资产管线走 visual-threejs-scene。
  触发词：数字沙盘、三维沙盘、沙盘推演、园区沙盘、厂区沙盘、物理沙盘、沙盘台、可漫游沙盘、地块沙盘、规划沙盘。
description_zh: 配置驱动的真三维数字沙盘：沙盘台体 + 地层剖面 + 程序化园区/厂区构件 + 图层点亮 / 剖切 / 点选 / 机位巡游 / 时间轴推演，单文件 HTML 双击即开，无 WebGL 自动降级等距二维。
description_en: Config-driven interactive 3D digital sandbox as a single self-contained HTML — a raised terrain slab with strata section, procedural park/plant assets, layer toggles, section clipping, entity picking, camera presets and a timeline; degrades to an isometric 2D board without WebGL.
category: Design Tools
version: 0.1.0
author: hasWhere
tags: ["数字沙盘", "Three.js", "WebGL", "园区", "厂区", "规划", "剖切", "图层", "单文件HTML", "推演"]
permissions:
  - file_read
  - file_write
  - command_exec
permission_notes_zh: 本 Skill 读取自带骨架与用户配置 JSON，在用户指定目录写入单个 HTML 产物；不调用外部接口、不上传数据。页面运行时从 jsDelivr / unpkg / staticfile 三源之一加载 three r149（可改 cfg.threeSources 指向内网地址），全部失败则降级为等距二维，功能不丢。
---

# 数字沙盘 · 真三维可漫游

> 产出物：**自包含单文件 HTML**，双击即开。
> 一句话判断用不用它：需要**把一块地「托起来当模型看」**——能环视、能俯视、能一层层点亮、能剖开看内部 → 用它。
> 只是要一张图表大屏 → `visual-echarts-dashboard`；要城市/工厂/港口的成品孪生大屏 → `visual-digital-twin`。

## 与姊妹技能的分工（先看这张表）

| 你手上是什么 | 用哪个 |
|---|---|
| 一块园区/厂区的**实体沙盘**：台体、地层、图层点亮、剖切、推演 | **本技能** |
| 成品孪生大屏：城市/工厂/港口模板、左右 KPI 面板、配置即交付 | `visual-digital-twin` |
| 自己搭/深度改三维场景、GLB 实景模型、Blender 建模管线 | `visual-threejs-scene` |
| 二维图表大屏、地图、告警播报 | `visual-echarts-dashboard` |
| 分层技术架构图、流程图 | `visual-arch-diagram` / `visual-diagram-suite` |

**沙盘 vs 孪生大屏的关键差别**：沙盘的主角是**那块地**（有厚度、有剖面、悬在深色空间里，像摆在桌上的模型），HUD 克制地围在四角；孪生大屏的主角是**数据面板**，三维视口只是背景板。

## 快速开始

```bash
# 1) 看有哪些内置场景
python scripts/build_sandbox.py --list

# 2) 直接出一个园区沙盘（22 个实体，开箱即用）
python scripts/build_sandbox.py --scene park --out ./园区沙盘.html

# 3) 用自定义配置覆盖模板（深度合并，只写要改的片段）
python scripts/build_sandbox.py --scene park --config my.json --title "XX 智造园 数字沙盘" --out ./out.html

# 4) 交付前必跑的门禁
python scripts/verify_sandbox.py ./out.html --shot ./preview.png
```

`--scene` 内置两个模板：`park`（园区：研发楼/总部/孵化器/厂房/仓储/管廊/车流/绿化/告警）、
`plant`（厂区：主车间/机加车间/成品库/动力辅管/叉车）。

## 标准工作流

1. **澄清场景**：园区还是厂区？沙盘尺寸（`base.size`）、要突出什么（楼宇 / 产线 / 地块规划）。
2. **挑模板改配置**：复制 `templates/config/park.json` 到工作区，改 `meta`、`layers[].entities[]`。
   实体坐标是**沙盘台面世界坐标**，台面中心为原点，X 向右、Z 向前。
3. **构建**：`build_sandbox.py` 会做一遍校验（未知类型、缺 position、坐标越界、id 重复），
   有问题直接报出来并退出码 1，不会产出一个畸形沙盘。
4. **验证（必做）**：`verify_sandbox.py` 真开浏览器跑——就绪、渲染模式、实体/图层数、
   图层开关、剖切、选中详情、机位切换、截图画面健全。`RESULT: PASS` 才算交付。
5. **交付**：给 HTML 路径 + 截图。联网出写实三维，断网/无 WebGL 自动降级等距二维。

## 配置契约（顶层）

| 字段 | 必填 | 说明 |
|---|---|---|
| `meta` | ✅ | `title` / `subtitle` / `badge`（顶栏角标） |
| `base` | ✅ | `size:[宽,厚,深]`、`terrain`（地形起伏幅度，建议 ≤6）、`terrainSeed`、`surface:park\|concrete\|asphalt` |
| `layers[]` | ✅ | 图层：`{id,label,color,on,entities[]}`，左侧面板一行一个，可点亮/熄灭 |
| `env` | ⭕ | `timeOfDay:day\|dusk\|night`、`fog`（0 = 关，见坑位）、`exposure`、`shadow` |
| `camera` | ⭕ | `fov`、`position`、`target`、`minPolar/maxPolar`、`minRadius/maxRadius`、`autoRotate`、`autoRotateSpeed` |
| `presets[]` | ⭕ | 机位：`{id,label,position,target}`，右下面板一键切 |
| `kpis[]` | ⭕ | 概览区指标卡 `{label,value,unit,trend}`（最多 4 个） |
| `alarms[]` | ⭕ | 告警 `{entityId,level:critical\|warning,text,time}`，点击跳转该实体 |
| `timeline` | ⭕ | `{enabled,durationSec,autoplay,frames:[{t,activity,label}]}`，activity 驱动车流速度 |
| `clip` | ⭕ | `{enabled,axis:x\|z,value:0~1}`，value=1 全显示 |
| `threeSources[]` | ⭕ | 覆盖 three 的 CDN 源（内网部署时指向本地 URL） |

## 构件库（`entities[].type`）

| type | 关键参数 | 用途 |
|---|---|---|
| `tower` | `size:[宽,高,深]` | 高层楼宇：幕墙窗格 + 裙房 + 女儿墙 + 屋顶机组 |
| `plant` | `size:[宽,高,深]`、`roofColor` | 厂房：双坡金属屋面 + 天窗带 + 竖墙肋 + 勒脚 + 卷帘门 |
| `warehouse` | `size:[宽,高,深]` | 仓储：低矮大跨 + 拱形屋面 + 墙肋 + 勒脚 |
| `block` | `size` | 通用体块（辅房、占位） |
| `road` | `points:[[x,y,z]…]`、`width` | 贴地路面 + 中心虚线；至少 3 个控制点 |
| `pipe` | `points`、`radius`、`flow` | 架空管廊：Tube + 沿管流光 + 支墩 |
| `vehicle` | `path`、`speed`、`phase`、`kind:car` | 沿路径往复行驶，速度受时间轴 activity 调制 |
| `zone` | `polygon:[[x,z]…]`、`color`、`opacity` | 地块分区：半透明填充 + 描边 |
| `tree` | `position`、`count`、`spread:[x,z]`、`seed` | 实例化成片种植 |
| `alarm` | `position`、`level`、`scale` | 告警光柱 + 双层脉冲环 |

实体通用字段：`id`（必填，告警/拾取回挂键）、`name`（场景标签）、`status:normal\|warn\|alarm\|off`、
`metrics:[{label,value,pct}]`（点选后的指标条）、`label:false`（不显示标签）、`color`、`rotation`。
**点实体**用 `position`；**线/面实体**（road/pipe/vehicle/zone）用 `points`/`path`/`polygon`，忽略 `position`。

## 运行时可编程接口（接真实数据 / 自动化）

页面就绪后暴露 `window.sandbox`：

```js
sandbox.stats()                 // {mode,layers,entities,pickables,tags,calls,triangles}
sandbox.select('HQ')            // 选中实体并聚焦
sandbox.layer('pipe', false)    // 点亮/熄灭图层（带升起动画）
sandbox.clip(0.5)               // 剖切到 50%
sandbox.preset(2)               // 切机位
sandbox.seek(12) / play(false)  // 时间轴
sandbox.cfg                     // 完整配置
```

`window.__SANDBOX_READY__ === true` 表示场景已就跑绪，轮询它做就绪判断最稳。

## 视觉规范（三条硬约束）

1. **色彩管线必须走 sRGB→linear**。three r149 没有 ColorManagement，材质色字面量会被当线性值采样——
   `0x2a3a48` 会变成屏幕上的 `#8a97a3` 浅灰。骨架里所有颜色都过 `C()` 转换，自己加构件时也必须过。
2. **反射率要在中调**。线性管线下 albedo 0.03 的地面等于黑体，画面会塌成剪影；用 sRGB 0.35~0.55 的基色，
   夜色交给雾、背景与曝光，别靠压暗 albedo。
3. **窗格密度按真实楼层算**。一层 ≈ 4 单位、一开间 ≈ 2.6 单位；写死 `round(h/9)` 会让 50 米高的楼出现
   130 行窗，远处混叠成一片灰白——整栋楼变"白模"。

其余：暗底 `#04080f`、玻璃面板、四角亮标、动画 ≤300ms、禁 bounce。详见 `references/02-visual-system.md`。

## 常见问题

- **双击打开白屏？** three 走经典 script（不是 ES module），file:// 可直接加载 CDN；
  全断网时会降级等距二维，界面与图层仍可用。
- **画面一片黑？** 99% 是雾。`FogExp2` 的衰减是 `exp(-(d·density)²)`，density 0.0024 在 700 单位处只剩 6% 可见。
  沙盘是模型展示，`env.fog` 默认 0。
- **楼体像白模？** 见视觉规范第 3 条（窗格密度）+ 第 2 条（albedo 过高会整片泛白）。
- **没有动态阴影？** 无头截图（SwiftShader）里阴影表现不可靠，真实 GPU 正常；
  骨架另有一套贴地投影贴片兜底，低端设备也有落地感。
- **剖切后看到背面穿帮？** 剖切开启时材质切到 `DoubleSide`，关闭时按缓存的原始 side 还原，别手改 side。
- **要接真实数据？** 见 `references/03-extend.md`，改 `updateEntity()` 一处分派即可，不必动断言逻辑。

## 文档索引

| 文件 | 什么时候读 |
|---|---|
| `references/01-config-contract.md` | 写配置：完整字段、坐标系统、实体参数、时间轴与剖切语义 |
| `references/02-visual-system.md` | 调视觉：光照配比、材质配方、HUD 规范、镜头构图 |
| `references/03-extend.md` | 加构件类型、接实时数据、内网离线部署 |
| `references/04-pitfalls.md` | 出问题时先查这里（真实踩过的 9 个坑） |

## 目录结构

```
visual-digital-sandbox/
├── SKILL.md
├── assets/sandbox-skeleton.html      # 运行时骨架（构建时内联配置进去）
├── scripts/build_sandbox.py          # 配置 → 单文件 HTML（含校验）
├── scripts/verify_sandbox.py         # 无头门禁（渲染 + 交互 + 截图）
├── templates/config/{park,plant}.json
└── references/*.md
```

产物写到用户指定目录，**不要写回 skill 目录**。
