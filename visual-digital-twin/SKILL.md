---
name: visual-digital-twin
description: >
  生成写实的数字孪生三维可视化大屏（单文件 HTML），内置智慧城市 / 智慧工厂 / 港口物流三大场景模板：
  物理天空 + PBR 材质 + 接触阴影 + 昼夜光照，配置即交付，含 2D 等距降级与 v1 经典科技风（--engine classic）。
  要自己搭或深度改造三维场景（程序化几何、GLB、巡检漫游、离线打包）走 visual-threejs-scene。
  触发词：数字孪生、可视化大屏、3D 大屏、三维大屏、数据驾驶舱、智慧城市大屏、工厂大屏、港口大屏、孪生平台。
version: 2.0.0
---

# Digital Twin Screen — 数字孪生可视化大屏生成器（写实引擎版）

> 产出物：**自包含单文件 HTML**，双击即开。
> 三层渲染：**写实 3D**（默认，three r160 module + 物理天空/PBR/接触阴影）→
> **经典 3D**（v1 UMD 科技风，`--engine classic`）→ **2D 等距降级**（断网/无 WebGL，面板功能完整）。

## 快速开始

```bash
python3 scripts/build_twin.py --scene city    --out /workspace/twin-city.html
python3 scripts/build_twin.py --scene factory --out /workspace/twin-factory.html
python3 scripts/build_twin.py --scene port    --out /workspace/twin-port.html
python3 scripts/build_twin.py --scene port    --offline --out twin-port.html     # 强制离线 2D
python3 scripts/build_twin.py --scene city    --engine classic --out city-v1.html  # v1 科技风
python3 scripts/build_twin.py --scene city --config my.json --title "XX园区孪生中枢" --out out.html
```

场景别名支持中文：`城市/园区/楼宇 → city`，`工厂/产线/车间 → factory`，`港口/物流/枢纽 → port`。

## 标准工作流

1. **澄清场景**：用户说"数字孪生大屏"时，先确认行业场景与关键指标。没有明确行业 → 默认 `city`。
2. **选模板 + 定制配置**：三大场景开箱即用；复制 `templates/config/*.json` 修改
   （标题、KPI、图表数据、图层开关、告警文案、`env.timeOfDay`）。
3. **构建**：跑 build_twin.py；有自定义需求就改 config，不要手改产物 HTML。
4. **验证（必做）**：`python3 scripts/verify_screen.py 产物.html --shot x.png --expect-mode 写实三维`
   —— 检查 pageerror/资源失败为空、徽标「写实三维」、面板数、截图像素健全。
5. **交付**：HTML 路径给用户；联网自动写实 3D，断网自动 2D 降级。

## 写实渲染内核（v2 新增，assets/core/engine.js）

- **物理天空**：Preetham Sky → CubeCamera → `scene.background`；PMREM 环境贴图走
  **材质级 envMap**（不设 scene.environment——全局环境 uniform 令透明面片整批不渲染）
- **PBR 三件套**：`assets/img/tex-*.jpg/-normal.png/-rough.jpg` 按场景 `textures` 声明
  选择性内联为 data URI；`E.texMat()` 自动挂载
- **昼夜双态**：`env.timeOfDay: "day" | "dusk"`（太阳/天光/曝光/雾/窗户灯光联动）；
  阳光:天空光 ≈ 5:1，**两头都高 = 过曝发白 = 一眼假**
- **接触阴影 + 圆角几何 + 收紧的阴影相机**；场景声明贴图遗漏 → 纯白无贴图
- **GLB 支持**：`config.models[]` + `assets/models/*.glb`，Draco 自动检测、decoder 内联、失败回退占位体

### 加载链（产物内运行时自动完成）

```
探测 CDN（jsdelivr → unpkg，各 6s 超时）→ 注入 importmap
→ Blob URL 动态 import 内联引擎源码（text/plain 槽位 dtEngineSrc）
→ 引擎构建 → window.__DT_ENGINE_READY__ → 徽标「写实三维」
任一失败/20s 超时 → 2D 等距降级
```

**坑位记录**：importmap 必须在任何模块加载触发前注册——引擎源码必须放
`<script type="text/plain">`，运行时分派靠 `cfg.engineMode`（构建期写入），
不能用全局变量探测（text/plain 不执行）。

## 面板组件速查（config.panels.left/right 数组项）

| type | 数据字段 | 说明 |
|---|---|---|
| `kpi` | `items:[{label,value,unit,trend}]` | 2×2 指标卡，trend 为百分比 |
| `lineChart` | `series:[{name,color,data:[…]}], labels:[…]` | 折线/面积，末端脉冲点 |
| `bars` | `items:[{name,value,color}]` | 横向条形（默认）或 `opt:{horizontal:false}` |
| `rank` | `items:[{name,value,unit,dataId}]` | 排行榜，dataId 绑定 3D 聚焦 |
| `ringGroup` | `items:[{label,value,max,color}]` | 多环形仪表 |
| `donut` | `items:[{name,value,color}]` | 环形占比 |
| `entities` | `items:[{id,name,status,value,unit}]` | 设备列表，点击相机聚焦 3D |
| `switches` | `items:[{id,label,on}]` | 图层开关，id 对应场景图层 |
| `alarms` | `{items:[]}` | 告警列表（由 pulse 填充或 config.alarms） |

顶层字段：`title / subtitle / scene / engineMode(构建期) / env{timeOfDay} / pulse /
pulseInterval / alarms / forceMode / threeSources / threeModuleSources / models[]`。

## 双模式降级机制

- **写实路径**：见上方加载链；引擎/场景代码全部内联，仅 three 本体走 CDN。
- **classic 路径**（`--engine classic`）：jsDelivr → unpkg → 字节 CDN（three r149 UMD），
  任一源加载成功且 WebGL 可用 → 3D；失败/超时（每源 6s）→ 自动 2D 等距。
- **2D 等距**：零依赖 Canvas 手写 30° 投影，数据面板功能完整；场景 `iso()` 提供降级节点。
- 沙箱/无 GPU 验证用 verify_screen.py（内置 swiftshader 参数）。
- **SwiftShader 已知限制**：无头截图看不到动态阴影（depth texture 采样不完整），
  落地感以接触阴影为准；真实 GPU 浏览器正常。

## 新增场景 / 深度定制

阅读 `references/extend-guide.md`：写实场景 spec 契约（textures 声明是硬契约）、
引擎 API 速查、GLB 模型接入、classic/DTH 工具箱、新面板组件、真实数据接入。

## 视觉规范

大屏壳遵守 `references/visual-language.md`（暗色底 #030711、玻璃拟态面板、四角亮标、
动画 ≤300ms、禁 bounce）。**3D 写实层另守三条**：光照高对比（阳光:天空光≈5:1）、
动效克制（真实运动 > 流光光点）、高空贴图 repeat ≤10（防斑马纹）。

## 常见问题

- **file:// 打开白屏？** 不会——全部经典 script 内联；写实引擎源码也内联，仅 three 走 CDN，断网自动 2D。
- **想换 three 版本？** config 传 `threeModuleSources`（写实）/ `threeSources`（classic）。
- **面板显示不全？** 左右栏各建议 ≤4 个面板；低于 1100px 宽会自动堆叠。
- **性能差？** 楼宇/集装箱用 InstancedMesh；写实场景参考值：city 6.5 万 / port 4.6 万 / factory 1.1 万三角面。
- **场景发白？** 检查是否漏声明 textures、或贴图 repeat 过高。
