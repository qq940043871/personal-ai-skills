---
name: visual-threejs-scene
display_name: Three.js 数字孪生原型
display_name_en: Three.js Digital Twin Prototype
description: "Three.js 场景开发工具箱（配置驱动）：自己搭或改造三维场景——程序化几何库（厂房/货架/堆场/储罐/管线/车辆）、GLTF/GLB 接入校验、标签弹窗、巡检漫游、设备高亮告警、拾取、离线打包。要开箱即用的成品孪生大屏（城市/工厂/港口模板）走 visual-digital-twin。触发词：Three.js、WebGL 场景、程序化几何、GLTF、GLB、巡检漫游、设备高亮、拾取交互、三维场景原型、离线 three。"
description_zh: Three.js 场景开发工具箱：程序化几何 + GLB 接入校验 + 标签/巡检/告警/拾取 + 离线打包，用于自己搭或改造三维场景；要成品孪生大屏走 visual-digital-twin。
description_en: Toolkit for authoring or customizing your own Three.js scene — procedural geometry, GLB loading, labels, patrol animation, alarm highlighting, picking, offline bundling. For a ready-made digital-twin dashboard, use visual-digital-twin.
category: Design Tools
version: 0.11.0
author: hasWhere
tags: ["数字孪生", "Three.js", "WebGL", "3D", "单文件HTML", "配置驱动", "Mock数据", "仓储", "厂区", "大屏"]
permissions:
  - file_read
  - file_write
permission_notes_zh: 本 Skill 读取自带骨架 HTML 与用户配置 JSON，在用户指定目录写入原型页面；不调用外部接口、不上传任何数据。页面运行时按需从 unpkg 加载 Three.js 运行时（可离线本地化，见「离线与内网部署」）。
---

# Three.js 数字孪生原型

## 这个技能解决什么

把「一个仓库 / 厂区 / 园区 / 港口长什么样、设备状态如何」变成**一个双击就能转起来的三维原型**，给领导看、给客户看、给评审看，而不是先做三个月建模。

**一句话判断要不要用它**：需要**在三维空间里看位置关系与状态**（层高、堆位、管线走向、车辆轨迹、告警落点）→ 用本技能。只是要一张**图表大屏** → 用 `visual-echarts-dashboard`。两者可叠加（大屏里嵌 3D 视口，见「扩展方式」）。

### 与姊妹技能分工

| 你手上是什么 | 用哪个 |
|---|---|
| 三维场景、设备状态、空间位置；要自己搭或改场景结构 | **本技能** |
| 开箱即用的成品孪生大屏（城市/工厂/港口模板、配置即交付、2D 降级） | `visual-digital-twin` |
| 二维图表大屏、KPI 卡、地图、告警播报 | `visual-echarts-dashboard` |
| 分层技术架构图 / 流程图 | `visual-arch-diagram` / `visual-diagram-suite` |

---

## 输入参数

> 全部通过 JSON 交给骨架。**配置只需写要改的片段**（深度合并），不写的走默认值。

### 顶层字段

| 字段 | 必填 | 说明 |
|---|---|---|
| `meta.title` / `meta.subtitle` | ✅ | 顶栏标题、副标题 |
| `sceneType` | ✅ | `warehouse`(仓储) / `plant`(厂区) / `park`(园区) / `bulk`(港口大宗) / `mine`(露天矿)，仅作语义标记与预设选择 |
| `env` | ⭕ | 天空模式（`sky`：shader/texture/gradient）、太阳方向强度、地面、网格、雾、曝光、`realism` 写实开关 |
| `camera` | ⭕ | `fov` / `position` / `target` / `autoFit`（装配后自动取景）/ 距离与俯仰限制 / 自动旋转 |
| `performance` | ⭕ | `maxPixelRatio` / `shadows` / `shadowMapSize` / `antialias` |
| `buildings[]` | ⭕ | 建筑：厂房、平库、车间、楼宇、泊位、船舶（`type` 见构件表） |
| `devices[]` | ⭕ | 设备设施：货架、堆场、储罐、筒仓、管线、输送廊道、车辆 |
| `models[]` | ⭕ | 外部 GLTF/GLB 模型（`url` 为空或加载失败自动回退程序化占位） |
| `labels` | ⭕ | 标签开关与是否显示状态色 |
| `patrol` | ⭕ | 漫游巡检路径点、时长、是否循环、是否自动播放 |
| `kpis[]` | ⭕ | 左侧指标卡：`{label, value, unit}` |
| `alerts[]` | ⭕ | 告警：`{deviceId, level: critical/warning, text, time}` |
| `dataSource` | ⭕ | `{mode:'mock'|'http', refreshMs, http:{assets, metrics, alerts}}` |

### 资产条目通用字段

```jsonc
{
  "id": "TANK-02",              // 必填，告警/接口/清单回挂的唯一键
  "type": "tank",               // 必填，决定程序化几何
  "name": "2号储罐",             // 场景标签与清单显示名
  "position": [190, 0, 40],     // 世界坐标（管线类用 points，不写 position）
  "status": "alarm",            // normal | warn | alarm | off → 决定发光色与标签
  "metrics": [                  // 信息弹窗里的指标条
    {"label": "液位", "value": "94%", "pct": 94}
  ],
  // 以下是各 type 专属参数
  "size": [长, 高, 宽],          // warehouse / rack / yard / box
  "roof": "arch|gable|flat",    // warehouse
  "seeThrough": true,           // warehouse：墙体半透明，能看到库内货架
  "bays": 10, "levels": 4, "fill": 0.78,   // rack：货位数/层数/占用率
  "stack": "cone|box", "rows": 3, "cols": 6,   // yard：垛型与阵列
  "radius": 16, "height": 26, "level": 0.86,   // tank / silo
  "points": [[x,y,z], ...],      // pipeline：管道路径（Catmull-Rom 平滑）
  "flow": true,                  // pipeline：管内流光动画
  "length": 120,                 // conveyor
  "path": [[x,y,z],[x,y,z]], "speed": 14   // vehicle：往复路径与速度
}
```

### 构件库（`type` 取值）

| type | 几何 | 适用 |
|---|---|---|
| `warehouse` | **v0.9 起含门式刚架**：底板 + 四面墙（可选半透明）+ 屋面（拱/坡/平）+ 钢柱/斜梁或拱肋 + 檩条 + 屋脊通风器 + 采光带 + 卷帘门（门洞/门框/卷帘箱/门板横纹/挑雨棚/吊杆）+ 落水管 + 窗带 + 青色描边。结构件实体、墙板半透明——真实仓库本就是「钢骨架 + 彩钢板围护」，骨架可见才像建筑 | 立体库、平库、车间、楼宇 |
| `rack` | **v0.10 重写**：立柱片（立柱+地脚板+柱顶封盖+横撑）+ Y-Z 平面 Z 字斜撑合并为钢构 Mesh；**橙色**承载横梁 Mesh（RAL2004 是真实货架横梁标配色，全灰会死板）；**黄色**端部防撞护栏 Mesh；货物 = 托盘 + 货箱两个 InstancedMesh，货位再切 `COLS×ROWS` 子位各自随机高度/朝向/缺货 | 货架、备件架、立体库 |
| `yard` | 作业平台 + 垛堆 InstancedMesh（锥形/箱形） | 露天堆场、煤堆、集装箱区、停车场 |
| `tank` | 罐身 + 压扁罐顶 + 裙座 + 液位环 + 爬梯 | 液体储罐、罐区 |
| `silo` | 锥斗 + 罐身 + 顶盖 + 支腿 | 筒仓、粮食仓、料仓 |
| `pipeline` | TubeGeometry 管线 + 流光彩壳 + 支撑立柱 | 管廊、输送管线 |
| `conveyor` | 皮带 + 支架 + 动画带面 | 输送廊道、装船皮带 |
| `vehicle` | 车头 + 货箱 + 车轮，按 `path` 往复行驶并自动转向 | 运输车、集卡、摆渡车 |
| `box` | 带描边长方体（GLTF 失败时的占位体） | 泊位、船舶、闸口、任意临时占位 |
| `office` | 幕墙贴图层 + 裙房 + 屋面板 + 屋顶机组 + 电梯机房 + 玻璃门厅 + 雨棚立柱 | 综合楼、研发楼、门诊楼、办公楼 |
| `tree` | 树干 + 3 个二十面体树冠（确定性随机，刷新不变化） | 单棵景观树 |
| `grove` | 区域内批量种树，树干/树冠各合并成 1 个 Mesh（共 2 个 draw call） | 行道树、绿化带 |
| `road` | 沥青贴图平面 + 中心虚线 + 路缘石，可 `rotation` 转向 | 园区主路、次通道、消防通道 |
| `lawn` | 草地贴图平面 | 中央绿地、宅间绿地 |
| `parking` | 沥青底 + 白色车位线 + 停放车辆（`occupied` 控制占用数） | 停车场、回车场 |
| `lamp` / `lampRow` | 灯杆 + 横臂 + 灯头 + 发光面；`lampRow` 沿曲线布灯并合并 | 路灯、庭院灯、周界灯 |
| `dock` | 混凝土月台 + 卷帘门阵列（`bays`）+ 门框 + 8m 出挑雨棚 + 登车桥 + 防撞块 + 黄色警示带 | 装卸月台、站台、冷库月台 |
| `gate` | 门卫室（玻璃带 + 屋面板）+ 双立柱 + 双向道闸 + Canvas 文字标识牌（`sign`/`signSub`）+ 减速带 | 园区大门、闸口、卡口 |
| `fence` | 沿 `points` 折线布立柱 + 半透明栅栏板 + 顶栏，各合并成 1 个 Mesh（2~3 draw call） | 围墙、周界、隔离栏 |
| `solar` | 斜面板 InstancedMesh + 支架，`rows`/`cols`/`tilt` 可调 | 屋顶光伏、光伏车棚 |
| `pit` | 椭圆开口逐层收缩：层间坡面 + 安全平台 + 台阶运输道路（环带+双黄线+轮胎痕）+ 黄色安全护栏（横杆+立柱）+ crest 矮堤；岩石面用 `tex-bench` 层理贴图 + tint 三档岩层色带 | 露天采场、矿坑（需配 `env.pitHole` 在地面挖洞） |
| `ramp` | 沿三维折线生成条带路面 + 双黄边线 + 两侧轮胎磨痕（可爬坡） | 露天矿螺旋/排土运输干线 |
| `excavator` | 履带底盘（`tex-track` 深色履带板）+ 回转体 + 起重臂 + 斗杆 + 铲斗 + 液压杆，带回转/挖掘动画 | 电铲、单斗挖掘机 |
| `drill` | 履带底盘（`tex-track`）+ 钻架 + 钻杆钻头，带穿孔高频微振动 | 牙轮钻机、穿孔设备 |
| `haulTruck` | 六轮矿卡（前小后大双轴）+ 自卸车厢 + 两级矿石堆（`loaded`），按 `path` 行驶 | 矿用自卸卡车 |
| `crusher` | 混凝土基础 + 受料漏斗 + 破碎腔 + 出料皮带 + 单梁吊车 + 爬梯；受料口/皮带端自动挂扬尘粒子（`dust:false` 可关） | 半移动破碎站 |
| `dump` | 多层截锥台阶（`tex-bench` 层理岩面 + tint 分层）+ 顶部排土线；排土线自动挂扬尘粒子 | 排土场、废石场 |
| `lightTower` | 高杆 + 四联自发光灯头 | 矿坑/场地夜间高杆照明 |
| `dozer` | 履带（`tex-track`）+ 车体 + 驾驶室 + 直推铲（可调倾角）+ 刀齿 + 推臂 | 推土机、平整设备 |
| `pond` | 围堰 + 半透明水面 + 底泥 | 沉淀池、蓄水池 |
| `monitor` | 立杆 + 设备箱 + 太阳能板 + 天线 + 告警 Beacon | 边坡 GNSS 监测桩、监测点 |

### 环境配景（`ambient: true`）

写实场景里八成观感来自配景，但配景不该污染业务数据。给条目加 `ambient: true` 即可：

- 不进 `pickables`（点不中，不干扰设备拾取与悬浮高亮）
- 不进左侧设备清单、不计入顶栏「资产：N」（`countAssets()` 只数业务资产）
- 不参与 `fitView()` 的包围盒（视野不会被外围绿化带撑大）
- 仍然正常渲染、投影、参与时段光照变化

推荐铺设顺序：**草坪 → 道路 → 行道树 → 停车场 → 路灯带**。`campus` 预设就是这套的完整示例。

---

## 输出结构

```text
<输出目录>/
├── <项目名>-twin.html          # 唯一交付物：单文件原型页（骨架 + 注入的 CONFIG）
└── <项目名>-config.json        # 可选：配置留档，方便二次生成
```

页面本体结构（一份 HTML，三块）：

| 区块 | 组成 |
|---|---|
| 3D 视口 | `#stage`（canvas）+ `#labels`（CSS2D 标签层，与三维坐标同步投影） |
| HUD | 顶栏（标题/场景/数据模式/资产数）、左栏（KPI 卡 + 设备清单）、右栏（对象详情 + 指标条 + 告警）、底栏（巡检/重置/取景/速度/标签/告警/线框 + 图例 + FPS 与绘制统计） |
| 配置块 | 页面里唯一的 `<script id="twin-config">window.__TWIN_CONFIG__ = {...}</script>`，改它即改场景 |

调试入口（F12 控制台）：`tw.CONFIG`、`tw.selectAsset('TANK-01', true)`、`tw.applyStatus('TANK-01','alarm')`、`tw.applyWeather('night')`、`tw.fitView()`、`tw.assets`。**注意方法名是 `selectAsset` / `applyStatus`，不是 `select` / `status`。**

---

## 使用步骤

```bash
S=~/.workbuddy/skills/visual-threejs-scene

# 1) 看有哪些场景预设
python $S/scripts/scaffold.py --list

# 1b) （可选）重新生成 PBR 三件套贴图（albedo + normal + roughness）
python $S/scripts/gen_textures.py            # 已存在的 albedo 跳过，只补 normal/rough
python $S/scripts/gen_textures.py --force    # 全部重生成

# 2) 直接出页面（五个预设任选，改标题）
python $S/scripts/scaffold.py --scene warehouse --title "华东智能仓数字孪生" --out ./twin.html
python $S/scripts/scaffold.py --scene campus --title "智慧园区数字孪生" --out ./campus.html
# 完整仓储园区（多库房 + 月台 + 堆场 + 闸口 + 围墙 + 屋顶光伏 + 集卡动线，约 30 个业务资产）
python $S/scripts/scaffold.py --scene logisticspark --title "华东智能仓储园区" --offline-three --out ./park.html
# 完整露天铁矿（台阶采场 + 螺旋运输干线 + 电铲/钻机/矿卡 + 破碎输送 + 排土场 + 高杆灯塔，35 个业务资产）
python $S/scripts/scaffold.py --scene mine --title "青山露天铁矿" --offline-three --out ./mine.html

#   默认把 13 张贴图内联成 data URI（产出的 HTML 单文件可带走、双击即开）
#   想外置贴图就用 --no-inline（记得把骨架同目录的 img/ 一起复制）
python $S/scripts/scaffold.py --scene campus --no-inline --out ./campus.html

#   CDN 不可达 / 内网环境必加 --offline-three：three.js r160 + 引擎全部内联，
#   页面零外网请求。优先用 assets/three-r160-bundle.js（esbuild 单脚本，CSP 兼容，
#   资料库在线预览等 script-src 'self' 'unsafe-inline' 严格环境唯一可行形态；
#   引擎/模块变更后重跑 scripts/build_three_bundle.py 重建），缺失则回退
#   assets/three-r160/ importmap data URI 方案（宽松环境可用）。
python $S/scripts/scaffold.py --scene warehouse --offline-three --out ./twin-offline.html

#   集成显卡 / 笔记本 / 远程桌面：--lite 一键降配（= quality low + 贴图≤1024 + HDR≤512）
#   体积能砍 60~70%，运行时还带掉帧自动降分辨率/降档；不传 --lite 默认 auto 按 GPU 挑档
python $S/scripts/scaffold.py --scene warehouse --offline-three --lite --out ./twin-igpu.html
#   也可以逐项点：--quality low|medium|high|ultra|potato / --tex-max 768 / --hdri-max 512

# 3) 要精调：先导出配置，改完回填
python $S/scripts/scaffold.py --scene plant --dump-config ./plant.json
#   编辑 plant.json（加建筑、改设备坐标、换告警、配接口）
python $S/scripts/scaffold.py --config ./plant.json --out ./plant-twin.html

# 4) 打开（本地起个静态服务，避免个别浏览器对 file:// 模块的限制）
python -m http.server 8000     # 然后访问 http://127.0.0.1:8000/twin.html
```

### 场景改造清单（按顺序，不要跳）

1. **换 `meta` 与 `sceneType`** —— 标题、副标题先对。
2. **改 `buildings` 与 `devices` 的 `position`/`size`** —— 先把平面布局摆对，别急细节。平面坐标建议以场地中心为原点，1 单位 = 1 米。
3. **配 `env` 与 `camera`** —— `env.preset` 选 `day/sunset/night/cyber`，`env.sky` 选 `shader`（物理天空，默认）/ `texture`（sky-*.jpg）/ `gradient`（纯渐变）；写实风把 `gridOpacity` 压到 ≤0.2；`camera.autoFit=true` 时装配后自动框住全部资产，改完尺寸不必手调机位。
4. **铺环境配景** —— 往 `devices[]` 塞 `ambient:true` 的 `lawn / road / grove / parking / lampRow`，先把「地面—道路—绿化—停车」铺满，观感立刻从原型变成实景。
5. **灌业务数据** —— `kpis` 换成真实口径，`devices[].metrics` 换成真实指标，`alerts` 换成真实告警源。
6. **开巡检路径** —— `patrol.waypoints` 沿着动线取 4~8 个点（默认为闭合环），`height` 即巡视高度。
7. **接外部模型** —— 有 GLB 就往 `models[]` 里塞；没有就用程序化几何顶着，别为了模型拖进度。
8. **切接口** —— 见下节。

---

## 实现要点（骨架里已落地的做法，改代码前先读）

### 场景与相机
- 渲染器固定 `outputColorSpace = SRGBColorSpace` + `ACESFilmicToneMapping`，曝光走 `env.exposure`；否则夜景会灰。
- 相机默认 **装配完成后按资产包围盒自动取景**（`camera.autoFit`），避免「配置一改，场景跑出画布」。
- OrbitControls 开阻尼，限制 `maxPolarAngle` 防止钻到地面以下。

### 光照天空与环境（写实基调的关键）
- **天空默认走物理天空 shader**（Preetham 模型，`env.sky:'shader'`）：太阳方向 = `env.sunDirection`，天空亮度、色温、环境反射三者物理一致，比等距柱状贴图强一个量级。Sky mesh 只存在于专用 `skyScene`，由 CubeCamera 渲成 cube render target 后赋给 `scene.background` —— **Sky mesh 绝不能直接进主场景**（见「已知坑」5）。想要贴图天空设 `env.sky:'texture'`（回退 `sky-*.jpg`），纯深色科技风设 `gradient`。
- **HDRI 实拍天空（v0.5，`env.sky:'hdri'`，最逼真）**：从 Poly Haven 下 CC0 .hdr（`assets/hdri/sky-day.hdr` 2k + `sky-sunset.hdr` 1k），RGBELoader 解码 → PMREM 预滤波为**材质级 envMap**（罐体/集装箱倒映真实天空云层亮度层次，比 Preetham 平滑天空更接近实拍）。**背景仍用 Preetham skyDome**：数字孪生多为俯视视角，equirect 全景的地平线以下（植被/地面）会顶进背景（看起来像灰雾地面），Preetham 任意朝向都是天空。scaffold 只在 `env.sky:'hdri'` 时内联 HDR（其余场景零体积），`inline_hdri()` 负责 data URI 化。
- **四时段一键切换**：底部工具条「白天 / 黄昏 / 夜晚 / 科技」，或控制台 `tw.applyWeather('sunset')`。切换会同步主光强度与色温、半球光天地色、环境光、补光、雾色、曝光、天空 cube 与环境贴图 —— 不是只换个背景图。
- **曝光校准铁律（v0.3，v0.6 微调）**：进入 ACES 的线性亮度尺度 ≈ `sun强度 × toneMappingExposure`，须落在 **1.2~2.2**。旧版 day 6.5×0.72=4.7 过曝成"雪原"。v0.6 day 调成 2.4×0.95=2.28（微超上限，靠 ACES 压高光），同时把环境光 hemi 0.12→0.40、amb 0.03→0.16——真实白天天空漫反射占总光 20~40%，v0.3 环境光只有 3% 导致暗部死黑。动光照先算 sun×exposure 乘积，再看 hemi+amb 环境光占比。
- **环境反射默认值按天空模式自适应（v0.6）**：`IBL_DEFAULT = sky==='hdri' ? 0.40 : 0.15`。v0.3 的 0.15 是 Preetham 程序天空时代的防过曝值（Sky shader 太阳周边 radiance 极高，超 0.2 就贡献 40%+ 亮度、把中灰材质洗白）；但 HDRI 实拍天空 radiance 是真实有限动态范围，0.15 会把天空漫反射 + 金属镜面反射一起掐死（暗部死灰、罐体哑光塑料感）。金属/玻璃类构件用 `opts.envMapIntensity` 显式调高（HDRI 下 0.5~0.8）。**注意 `MeshStandardMaterial.envMapIntensity` 默认是 1 不是 null**，`== null` 判断永远不命中——默认值必须在材质工厂（mat/texMat）里显式给。
- **夜晚要把"天空里的太阳"沉到地平线以下**（v0.3，`applySkyPreset` 已处理）：Preetham 天空没有夜晚概念，只要太阳在天上，rayleigh 再低夜空也是白的（实测夜景全屏泛白的根因）。夜间照明交给月光（低强度 DirectionalLight）与人工光源。
- **环境反射挂材质级 `envMap`，不设 `scene.environment`**：PMREM 预滤波贴图按材质登记（`PBR_MATS`），时段切换统一刷新。`scene.environment` 是全局 uniform，在部分软件渲染器上会让其他物体整批消失（见「已知坑」6）。
- **雾色别用亮色（v0.3）**：day 雾色旧版是 0xc6daec（亮蓝白），600m 场地远端整片"白纱"；现默认 0x8fa5b8（中性灰蓝）。

### 写实后处理链（v0.3，默认开启）

`EffectComposer` 串联四段，`performance.postfx:false` 一键退回直出管线：

| Pass | 作用 | 关键参数（`performance.*`） |
|---|---|---|
| `RenderPass` | 常规渲染（输出线性 HDR 到 HalfFloat RT） | — |
| `GTAOPass` | **屏幕空间环境光遮蔽**：墙角、设备落地处、货箱缝隙、台阶交接的暗角——这是"塑料感"和"实景感"的分水岭，权重高于任何贴图升级 | `ao` / `aoRadius`(米，大场地 3~4) / `aoIntensity`(1.25) / `aoThickness` |
| `UnrealBloomPass` | 辉光：夜景路灯、告警光柱、自发光面板 | `bloom` / `bloomStrength` / `bloomThreshold` / `bloomRadius` |
| `SMAAPass` | 抗锯齿（走 composer 后 MSAA 失效，靠它补几何边缘） | `smaa` |
| `SSRPass` | **屏幕空间反射（v0.5）**：罐体/集装箱倒映彼此与天空，金属玻璃质感关键。独立 try/catch（依赖 float RT + depth 采样，软件渲染器下大概率失败则只跳过 SSR） | `ssr` / `ssrIntensity`(0.55) / `ssrMaxDistance`(120) / `ssrThickness` |
| `ShaderPass` | **电影调色（v0.7）**：链尾 OutputPass 后做对比度/饱和度/暗角（sRGB 显示空间），把"直出感"拉成"拍摄感"。默认 contrast 1.05 / saturation 1.03 / vignette 0.18（暗角别超 0.25，否则边缘糊成暗色） | `grade`(false 关闭) / `gradeContrast` / `gradeSaturation` / `gradeVignette` |
| `OutputPass` | 链尾统一 tone mapping + sRGB（必须在最后） | — |

**Bloom threshold 作用在 tone mapping 前的 HDR 线性域**——0.9 的旧默认连亮天空都在辉光（黄昏整幅白雾），现默认 1.6：只让灯光/高光发光，夜景灯光 intensity>2 依然有效。

调试入口（F12）：`tw.postfx()` 查看各 pass 状态；`tw.setPostFX(false)` 一键对比开/关 AO 的真实感差距；`tw.setAO(radius, intensity)`、`tw.setBloom(strength, threshold)` 实时调参。

任何一环在软件渲染器（SwiftShader）上不可用时整链 try/catch 回退直出，页面照常可用——`tw.postfx().on` 为 false 即回退态，非缺陷。

### 贴图体系

| 配置键 | 文件 | 用途 |
|---|---|---|
| `env.groundTex` | `lawn` / `concrete` / `asphalt` | 地面材质（对应 `textures.lawn/concrete/asphalt`） |
| `textures.skyDay/Sunset/Night` | `sky-*.jpg` 1280×853 | 三时段天空全景（`env.sky:'texture'` 模式用） |
| `textures.glass` | `tex-glass.jpg` | 办公楼幕墙（带层间线与竖向分格） |
| `textures.wallConcrete` | `tex-concrete.jpg` | 浅灰墙板、裙房 |
| `textures.wallSteel` | `tex-wall-steel.jpg` | 厂房彩钢板墙与屋面 |
| `textures.tank / ore / crate / bench / track` | `tex-*.jpg` | 储罐壳体 / 矿石料堆 / 货架货箱 / 露天矿台阶岩石（水平沉积层理）/ 深色履带板 |
| `textures.lawn / asphalt / concrete` | `tex-*.jpg` | 草地 / 道路 / 场地 |

**PBR 三件套（v0.2 起）**：以上每个 `tex-xxx.jpg` 均可配同名衍生贴图，`texMat()` 按命名约定自动挂载：

| 衍生文件 | 通道 | 作用 |
|---|---|---|
| `tex-xxx-normal.png` | RGB 切线空间法线 | 微观几何：混凝土麻面 / 钢板波纹 / 草地起伏 / 焊缝锈迹 |
| `tex-xxx-rough.jpg` | G 粗糙度 | 乘区：锈迹更糙、磨光带更光、脏污变化 |

重新生成整套贴图（纯本地 numpy+PIL 程序化生成，无版权风险，固定种子结果可复现）：

```bash
python <skill>/scripts/gen_textures.py              # 生成全部（已存在的 albedo 跳过）
python <skill>/scripts/gen_textures.py --force      # 连 albedo 一起重生成
python <skill>/scripts/gen_textures.py --only lawn asphalt --size 768
# 大场景主贴图提分辨率（台阶岩石 bench 用 2048，小物件 768 即可）
python <skill>/scripts/gen_textures.py --only bench --size 2048
```

**扫描贴图替换（v0.5，越逼真越用这个）**：程序化贴图是"一眼假"的第二来源（第一是天空）。
从 Poly Haven（CC0）下载真实扫描 PBR 贴图替换同名文件即可，diff/nor_gl/rough 三通道一一对应：

| 场景用途 | Poly Haven slug | 替换的 `assets/img/` 文件 |
|---|---|---|
| 混凝土地面 | `concrete_floor_worn_001` | `tex-ground.jpg` / `-normal.png` / `-rough.jpg` |
| 沥青道路 | `asphalt_02` | `tex-asphalt.jpg` / `-normal.png` / `-rough.jpg` |
| 波纹彩钢板 | `box_profile_metal_sheet` | `tex-wall-steel.jpg` / `tex-wallsteel-normal.png` / `tex-wallsteel-rough.jpg` |

下载：`https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/{slug}/{slug}_{ch}_1k.jpg`（`ch` = diff/nor_gl/rough）。
`nor_gl` 是 JPG，需转 PNG 再放 `-normal.png`（法线通道对压缩伪影敏感）。**墙钢命名有坑**：albedo 是
`tex-wall-steel.jpg`（带连字符）而 normal/rough 历史文件名是 `tex-wallsteel-*`（无连字符），`texMat` 按
命名约定找带连字符的会落空——v0.5 已补齐两份命名，新增材质时保持一致性。

**全部走 `loadTex()` 带缓存 + 静默失败**：断网、图丢了、路径写错，都只会回退到程序化纯色，不会白屏也不会刷 console 错误。想彻底离线就把图换成本地同名的即可。scaffold 会把 HTML 里引用的贴图连同 `-normal.png` / `-rough.jpg` 衍生件一起内联成 data URI（注入 `window.__TWIN_TEX_URI__` 映射）。

**`texMat(url, rx, ry, opts)` 两个进阶选项（v0.2.4）**：
- `opts.tint` —— 贴图挂载后把材质基色设为该色（乘性），同一张贴图派生多档色相（台阶岩层色带 / 排土场分层）；不传则复位为白色
- `opts.envMapIntensity` —— 显式设置则不覆盖默认（HDRI 0.40 / shader 0.15，v0.6）。**深色非金属（履带/泥污履带板）必须显式压低（0.1~0.15）+ metalness ≤0.25**，否则 PMREM 环境反射会把深色 albedo「洗」成发亮灰蓝金属（典型误判：以为是贴图没挂）

**扬尘粒子（v0.2.4）**：`makeDust(origin, {count, spread, rise, size, opacity})` 生成 canvas 径向渐变贴图的 Points 粒子团（上浮+漂移+寿命循环，夜间自动降透明度）；`buildCrusher` / `buildDump` 内置破碎站受料口/皮带端、排土线尘源，构件配 `dust:false` 可关。

### 程序化几何与模型
- 重复构件全部走 **InstancedMesh**（货箱、垛堆、车轮），单场景 draw call 稳定在百级；立柱横梁用 `mergeGeometries` 合成单 Mesh。
- **写实模式（`env.realism:true`，默认）**下：① 青色描边透明度从 0.35 降到 `env.edgeOpacity`（默认 0.12）② 科技网格线默认 0.05 ③ 关键构件（墙体、货箱、车头货箱、楼体裙房）用 `RoundedBoxGeometry` 圆角 —— 尖角盒的高光是一条尖线，圆角才有「实物感」。
- **接触阴影**：每个业务资产底部自动生成一片顶点色 alpha 渐变的暗斑（`contactShadow()`），补足「落在地上」的落地感。细长构件（管线/廊道）由 builder 标记 `noCS` 排除；车辆作为子对象自动跟随。**用顶点色 alpha 而非黑色 alpha 贴图** —— 部分软件渲染环境下 canvas 贴图的 alpha 通道会丢失，整片暗斑不可见（实测踩坑）。
- GLTF 走 `GLTFLoader` + `DRACOLoader`（压缩模型可用），`LoadingManager.onProgress` 驱动加载条；**任何失败都回退程序化占位体并 `console.warn`**，不白屏。

#### 外部 GLB 接入（models[]）

**模型从哪来**（按工业数字孪生适配度排序）：
1. **设备厂商/设计院要 CAD**——筒仓、皮带机、装车塔等主设备的正统来源；STEP/IGES 用 FreeCAD（免费）或 Fusion 360 转 STL，再进 Blender 减面
2. **GrabCAD / McMaster-Carr**——标准机械件（轴承、螺栓、管件），McMaster 是 CAD 精度
3. **Sketchfab / TurboSquid**——卡车、叉车等通用设备，挑 <50k 面的免费款，看清许可；**下载默认带 Draco 压缩**（见下）
4. **Blender 自建低模**——货架、月台、围墙类「几何简单 + 吃程序化贴图」的构件，几千面封顶
5. **照片建模（Meshroom/RealityScan）/ AI 生成（Tripo/Meshy）**——前者适合形态不规则老设备（反光不锈钢表面会瞎），后者只配景观杂物，**禁用于主设备**

**接入三步**：
1. `.glb` 放进 skill 的 `assets/models/`。**多文件 `.gltf + .bin` 不支持内联**——先在 Blender 导出 glTF Binary，或用 `gltf-pipeline -i x.gltf -o x.glb` 转换
2. 配置声明：
```jsonc
"models": [
  { "id": "GLTF-STACKER", "name": "堆垛机", "url": "models/stacker.glb",
    "position": [0, 0, -40], "rotation": 0, "scale": 1,
    "fallback": { "type": "box", "size": [4, 14, 3] }, "status": "normal" }
]
```
3. `scaffold.py` 生成时**自动把 .glb 内联成 data URI**（单文件可带走），总体积 >8MB 会警告

**Draco 压缩自动处理**：scaffold 检测到 `KHR_draco_mesh_compression` 扩展时，把 `assets/draco/` 的 decoder（wrapper js + wasm 共约 340KB）base64 注入 `window.__TWIN_DRACO__`，骨架经 `LoadingManager.setURLModifier`（公开 API，FileLoader 走 `manager.resolveURL`）把 decoder 请求改写为 data URI——**离线可用、零 CDN 请求**。未检测到 draco 模型时不注入（零体积浪费），decoder 走 unpkg CDN。
**已知坑**：`gltf-pipeline` 4.3.1 处理 `.glb` 二进制输入必报 "Binary glTF scene format is not JSON"（BIN chunk 类型常量 `0x004e4942` 少了高位 `0x20`，是它的 bug）——**绕过法：喂 `.gltf` JSON 输入**。
**测试样例**：`assets/models/tri.glb`（未压缩）与 `tri-draco.glb`（Draco 压缩）是最小合法 GLB，各含一片 10m 纯红三角形，专用于验证内联链路（配 `verify_gltf.py`）。

**内置示例库（Poly Haven，CC0，1k 档，米制真实尺寸）**：

| 文件 | 名称 | 尺寸（长×高×宽 m） | 体积 | 注意 |
|---|---|---|---|---|
| `ph-overhead_crane.glb` | 桥式起重机 | 12.5×4.6×4.7 | 7.0M | **原点在腹部**（底部 -3.35m），摆放要 `position:[x, 3.35, z]` |
| `ph-hand_truck.glb` | 液压搬运车（地牛） | 0.59×1.4×0.69 | 3.1M | 原点在底部 |
| `ph-plastic_crate_02.glb` | 塑料周转箱 | 0.51×0.25×0.41 | 1.8M | 原点在底部 |
| `ph-cardboard_box_01.glb` | 纸箱 | 0.39×0.34×0.52 | 2.1M | 原点在底部 |
| `ph-barrel_03.glb` | 工业油桶 | 0.63×0.93×0.64 | 0.5M | 原点在底部 |
| `ph-steel_frame_shelves_02.glb` | 钢制货架 | 0.59×2.14×0.5 | 0.5M | 仅 0.6m 宽，是陈列架不是库区大货架 |

**大场景放小模型的取景坑**：autoFit 按全场景包围盒拉相机，±100m 场地里 1m 级小物件只剩几十像素（实测 6 模型 showcase 截图上小件几乎看不清）。对策：小物件要么 `scale` 适度放大（展示用途可接受），要么把 `camera.position/target` 显式写到模型群附近并关 autoFit。

**从 Poly Haven 增补模型的流程**（2026-10-17 实测）：
1. API `https://api.polyhaven.com/files/{slug}` 拿文件树——**注意 api.polyhaven.com 有 Cloudflare 限流，连续请求会间歇 522，且沙箱里 python 子进程的网络出口与 bash 不同（python subprocess 更易被拒），下载一律用 bash curl、每次间隔 1-3s**
2. 也可绕过 API 直连文件服务器（URL 有强规律，实测未被限流）：
   `https://dl.polyhaven.org/file/ph-assets/Models/gltf/1k/{slug}/{slug}_1k.gltf`
3. glTF 包是**三件套**：`.gltf` + 同名 `.bin`（几何，同目录）+ `textures/*`（贴图在 `Models/jpg/1k/{slug}/`）。只下 gltf 会 ENOENT，只下贴图会缺几何——三样都要
4. 转自包含单文件：`gltf-pipeline -i x.gltf -o ph-x.glb`（**喂 .gltf JSON 输入**，绕开 4.3.1 的 .glb 输入 bug；贴图会自动内嵌）
5. 输出放 `assets/models/ph-{slug}.glb`，CC0 许可无署名要求

**Blender 工业设备模型工厂（v0.4.0 新增，`bl-*.glb` 系列）**：
程序化 BoxGeometry 拼的储罐/筒仓是"一眼假"的重灾区（锐利边缘无高光、无结构细节）。本地 Blender
（`D:\tools\blender-4.5.14-windows-x64\blender.exe`，便携版）可以产出**倒角高光 + 法兰阀组 +
笼式爬梯 + 顶部栏杆 + 集装箱波纹板**这类 CylinderGeometry 永远给不了的细节，面数/体积可控。

- 生成命令：`blender.exe --background --python scripts/gen_models_blender.py -- --out <目录> [--models tank,container,truck,silo,forklift,gantry] [--size tank:32,26]`
- 出厂规格匹配 warehouse 主场景（TANK-01/02 = Ø32×H26，SILO-01 = Ø24×H38），其他规格 `--size` 覆盖
- 内置模型：`bl-tank`（罐壁+抗风圈+锥顶+平台栏杆+笼梯+人孔+法兰阀组+基础）、`bl-silo`（锥底卸料+环箍+支撑腿）、`bl-container`（竖波纹+角件+端门）、`bl-truck`（厢式货车六轮，v0.8 补厢体竖筋/导流罩/车门/前照灯/侧护栏/尾部爬梯）、**`bl-forklift`（v0.8，3.5t 平衡重叉车：后配重+护顶架栅格+两级门架+倾斜缸+货叉+前后异径轮）**、**`bl-gantry`（v0.8，跨距 26m 轨道式龙门吊：双箱梁+端梁+走台栏杆+门形支腿+斜撑+走行箱轮+小车司机室+吊具旋锁）**
- **模型精度 vs 体积**：Blender 程序化 GLB 极便宜——叉车 864 面 / 134KB，龙门吊 1248 面 / 181KB。
  "更精准的模型"几乎不增加体积，真正的体积大头是 HDRI 和扫描贴图，别搞错优化对象
- **尺寸参数化铁律**：罐体按参数缩放，**人体工学细节保持真实尺寸**——栏杆 1.1m、踏距 0.32m 不变，
  直径只控制"环向细节数量"（栏杆立柱按周长 ~2.2m 一根）。罐子 Ø32m 栏杆跟着变 3m = 一眼假
- **scale 反算**：预设里 `scale = 目标尺寸 ÷ 模型实际外廓`（罐体外廓含基础环，32/34.22≈0.94）。
  千万别用 scale 把 Ø13 的模型"放大"成 Ø32 用——倒角宽度也跟着放大 2.4 倍，细节全糊

**Blender headless 头号陷阱（实测，2026-10-28）**：`bpy.ops.transform.rotate/scale` 作用于
**所有选中物体**。headless 下 `primitive_cylinder_add` 创建后旧物体仍处于选中态——每转一根
踏棍，之前创建的罐壁/栏杆/平台全被跟着旋转，表现就是"细节神秘消失"（面数对但几何位置全歪）。
`gen_models_blender.py` 里所有构件都走 `cyl()/cub()/cone()/torus()` 辅助函数：先
`select_all(DESELECT)`，创建后数学方式设 `rotation_euler` 并立即 `transform_apply`，
**绝不依赖选中态**。复核方法：看导出面数是否符合"构件清单 × 单件面数"的估算，差太多就是丢了。

**GLB 材质与场景光照的一致性**：GLTFLoader 自建材质默认**不在 PBR_MATS 登记表里**，拿不到
skyEnvMap —— 真实模型在白天场景会比程序化资产暗一截（实测储罐黑成一坨）。骨架已在模型加载后
把 GLB 材质并入登记表（v0.4.0）；`applyEnvMaps` 会把 envMapIntensity=1 的默认值压到 IBL_DEFAULT（HDRI 0.40 / shader 0.15）与
全场统一。Blender 侧材质给中灰蓝（0.42~0.50）而非浅灰（0.62+），浅灰钢漆在强阳光下泛白如塑料。

**验证 GLB 世界尺寸：量数据，别信截图目测（2026-10-28 实测）**。远景 + 透视下，视觉判断
会离谱到"把 14.9m 高的龙门吊说成比 5.2m 箱堆略高"。可靠做法：Playwright 里遍历 scene，
**沿父链找 `userData.id`**（id 挂在父 Group，几何体在子 Mesh，只查自身会漏），再用
`matrixWorld` 变换 geometry boundingBox 的 8 个角点求世界 AABB。参考 `_measure.py` 模式。
注意旋转物体拿到的是 AABB（会比实际外廓大），判断长宽时要考虑 rotation 角度。

**HDRI 分辨率：1k 就够，2k 是纯浪费（2026-10-28）**。PMREM 预滤波 envMap 最高只用到 256px
envMap，源图 1k 与 2k 在反射上肉眼无差；但 2k 的 `kloofendal` 是 6.5MB、1k 只有 1.56MB ——
单文件产物直接省 5MB（v07 29.9MB → v08 25.2MB，还多装了 4 台设备）。
背景不用 HDRI（见上：俯视会采样到地平线以下的植被），所以 HDRI 只服务于反射，1k 完全够。

### 标签与信息弹窗
- 标签用 `CSS2DRenderer`：**DOM 标签随三维坐标投影**，可直接绑 `click`，比 sprite 清晰、可换行、可加状态胶囊。
- 管线这类世界坐标构件通过 `userData.tagAt` 指定标签落点，不硬编码在原点。
- 右栏详情 = `cfg.metrics` 渲染指标条 + 命中告警列表；`BoxHelper` 描出选中包围盒。

### 漫游巡检
- 路径点 → `CatmullRomCurve3` → 按 `t += dt*speed/duration` 取点；相机朝向 = 前方点与场景中心做 `lerp(0.55)` 混合，避免「转头甩镜头」。
- 播放中禁用 OrbitControls，停止后把 target 拉回场景中心，否则下一次拖拽会瞬移。

### 状态高亮与告警
- 状态四态 `normal/warn/alarm/off` 映射统一色板；改状态走 `applyStatus(id, status)`，**同时更新三维材质 emissive、场景标签、左侧清单**，三处永不脱节。
- 告警 = 地面扩散环（`RingGeometry` 缩放+淡出）+ 竖直光柱 + 闪烁标签；告警呼吸在 `alarm` 态材质上按 `sin(t*3)` 调制。
- 告警落点由 `deviceId` 反查资产包围盒中心计算，**资产一改坐标，告警自动跟着走**。

### 交互拾取
- `Raycaster` + 资产级 `userData.assetId` 回挂：命中的是子 Mesh，但拿到的是资产 id，弹窗永远对着「设备」而不是「某块面」。
- 悬浮高亮保存原 `emissiveIntensity` 再还原，不会把告警态刷丢。
- 点击列表项 = 点击三维对象（同一份 `selectAsset`），附带 `flyTo` 缓动推镜。

### 性能与自适应
- `pixelRatio` 上限由 `performance.maxPixelRatio` 约束（默认 2），4K 屏不炸显存。
- `document.hidden` 时直接 return，切后台不烧显卡。
- 底栏实时显示 **FPS / draw call / 三角面**；`ResizeObserver` + 防抖响应容器尺寸变化（嵌 iframe 也不糊）。

#### 集成显卡适配（v0.11）：画质档位 + 自动调速

集显（Intel UHD/HD、Iris Xe、移动端 GPU）跑数字孪生，瓶颈**不是三角面，是填充率**：
1080p 全屏连跑 SSR+GTAO+Bloom+SMAA+调色 5 个 pass ≈ 每帧一亿像素着色，EU 数量直接跪。

五档 `QUALITY_TIERS`（`CONFIG.performance.quality` = `auto|potato|low|medium|high|ultra`）：

| 档位 | 目标设备 | pixelRatio | SSR | AO | Bloom | SMAA | 阴影图 | 贴图上限 | detail |
|---|---|---|---|---|---|---|---|---|---|
| `potato` | 软渲染/老集显 | 0.75 | ✕ | ✕ | ✕ | ✕ | 关 | 512 | 0.30 |
| `low` | HD 4000~620 / UHD 6xx | 1.0 | ✕ | 0.4× | ✕ | ✓ | 1024 | 1024 | 0.85 |
| `medium` | Iris Xe / UHD 7xx / Apple | 1.25 | ✕ | 0.5× | 0.5× | ✓ | 2048 | 1024 | 0.85 |
| `high` | 入门独显 MX/GTX1650 | 1.5 | ✕ | ✓ | 0.75× | ✓ | 2048 | 2048 | 1.0 |
| `ultra` | RTX/RX | 2 | ✓ | ✓ | ✓ | ✓ | 4096 | 2048 | 1.0 |

- **自动选档**：`detectGPU()` 用临时 canvas 读 `WEBGL_debug_renderer_info` → 正则判 Intel/Apple/移动/软渲染（SwiftShader/llvmpipe）→ 给档位；`hardwareConcurrency<=4` 再降一档。**必须在 `new WebGLRenderer` 之前跑**（`antialias` 只能在构造时决定）。
- **运行时切档**：点击底栏「画质」chip 循环 / `P` 键 / `tw.setQuality('low')`；右键 chip 回 `auto`。除贴图分辨率外全部即时生效。
- **自动调速器**：启动 5 秒后开始采样（PMREM/贴图解码期必然卡，别误判），滚动 90 帧均值 < 26fps →
  **先降渲染分辨率**（每次 −0.15，下限 0.6×），降到底才降一档。顺序是有意的：直接降档画面会"啪"地掉一档（AO 没了/货箱变少），比轻微变糊难看得多。
- **生成时**：`--lite` = `--quality low --tex-max 1024 --hdri-max 512`，同时把贴图/HDRI 内联前降采样，体积能砍 60~70%。

三项低配专属优化（默认开，`performance.staticShadows` 可关）：

1. **静态阴影图**：`renderer.shadowMap.autoUpdate=false`。光影 99% 时间不变，却每帧重画百万面深度图 —— 改为「相机移动中每帧刷 / 停稳后补一张就停手」。
2. **半分辨率 AO/Bloom**：`aoScale`/`bloomScale` 把 GTAOPass、UnrealBloomPass 的内部 RT 缩到 0.4~0.75 倍。
3. **小物件距离剔除**：包围球半径 <2.6m 的 Mesh 按尺寸分档（90/170/240m×detail）隐藏。**GLB 子树必须豁免**（见坑 30）。

实测（仓库场景 1600×900）：26.4MB / 2142 draw / 1767k 三角面 → **8.7MB / 409 draw / 422k 三角面**。

---

## 数据接口（Mock 优先，接口可替换）

```jsonc
"dataSource": {
  "mode": "mock",                 // mock：本地按时抖动；http：按 refreshMs 拉接口
  "refreshMs": 8000,
  "http": {
    "assets": "/api/twin/assets",   // 可选：资产清单（含 position/status/metrics）
    "metrics": "/api/twin/metrics", // { kpis: [{label,value,unit}] }
    "alerts":  "/api/twin/alerts"   // { alerts: [{deviceId,level,text,time}] }
  }
}
```

约定：**接口不可用时自动降级为 Mock 并只 `console.warn`**，演示现场不白屏。后端字段名如不同，只改 `pullRemote()` 里的映射，别改骨架其余部分。

---

## 离线与内网部署

骨架通过 `importmap` 从 unpkg 加载 Three.js（`three@0.160.0`）。内网/离线要改成：

```bash
# 在能联网的机器上取依赖
npm pack three@0.160.0    # 或直接下载 build/three.module.js 与 examples/jsm/
```

把 `three.module.js` + `examples/jsm/**` 放到页面同级 `vendor/three/`，然后改骨架 **boot 脚本**（`<script id="twin-boot">`）里的 `CDNS` 数组，把本地路径 `./vendor/three/` 放到首位（`three/addons/` 一定要映射到 `examples/jsm/` 目录本身，尾部斜杠不能少）。改完**必须重新冒烟**（见下）。

**Draco decoder 已内联化**：配置含 Draco 压缩模型时，scaffold 会把 `assets/draco/` 的 decoder 一并 base64 进产物，不依赖 unpkg；只有 Three.js 本体仍走 CDN（要彻底离线，走上面的 vendor 化流程）。

---

## 质量校验（交付前必做）

```bash
# 语法层：把 <script type="module"> 抽出来过一遍解析器
python <skill>/scripts/scaffold.py --scene warehouse --out /tmp/p.html   # 生成
# 运行层：无头浏览器跑一遍，看 console / pageerror 是否为空
python <skill>/scripts/smoke_headless.py /tmp/p.html                     # 见「配套脚本」
```

硬指标：**pageerror 为空、console 无 error、`canvas` 存在、资产数 = 配置里的建筑+设备数**。脚本已内置 CDN 域名白名单（unpkg/jsdelivr/esm.sh 的资源加载失败属网络抖动，不计 FAIL），自己写校验时别把 CDN 抖动误判成页面缺陷。
若用了无头核实，务必用 `--use-angle=swiftshader --enable-unsafe-swiftshader`，否则无 GPU 环境会直接报 WebGL 上下文创建失败，误判成代码问题。

**外部模型专项**（配置含 `models[]` 时必做）：`verify_gltf.py` 会 route 阻断 `**/draco/**` 抓包 + 对测试模型的纯红表面做像素检测，三重判据确认「模型真渲染 + decoder 真内联」：

```bash
python <skill>/scripts/verify_gltf.py /tmp/p.html --expect-assets 14 --min-red 300
```

判据：draco 网络请求为无（decoder 走内联）、红色像素 ≥ 阈值（占位回退体是灰色系，绝不可能红）、零 pageerror/console.error。draw call 数可交叉验证：无模型 239 → 单模型 +2~3 → 双模型叠加。

### 阴影与相机
- 阴影相机**按场景实际包围盒收紧**（`tuneShadowCamera()`，装配后与 GLTF 到位各跑一次）：固定 ±300m/2048 对 600m 场地 = 0.29m/像素，边缘全糊；收紧后 4096 贴图约 0.14m/像素。`normalBias=0.03` 防曲面 shadow acne。
- 相机默认 **装配完成后按资产包围盒自动取景**（`camera.autoFit`），避免「配置一改，场景跑出画布」。
- OrbitControls 开阻尼，限制 `maxPolarAngle` 防止钻到地面以下。

已知易踩的坑（都已在骨架里规避，改代码时别改回去）：
1. **装配阶段读取的状态量必须提前声明** —— `applyStatus → renderDeviceList` 在场景装配期就会跑，`let selected` 若声明在后面会命中 TDZ 直接白屏。
2. **半透明墙体要 `depthWrite:false` + `renderOrder`**，否则库内货架被剔除或闪烁。
3. **只能命中「有材质的 Mesh」** —— 用 `visible:false` 的对象做拾取代理会被 Raycaster 跳过。
4. **`CSS2DObject` 的标签要有 `pointer-events:auto`**，父层 `pointer-events:none` 不影响子节点点击。
5. **Sky mesh 不能进主场景** —— 它的全屏 fragment 在部分软件渲染器（SwiftShader）上会把同帧其他不透明物体盖掉（症状：接触阴影整片消失，逐项二分定位）。正确架构：Sky 只在专用 `skyScene`，CubeCamera 渲成 cube RT 赋 `scene.background`（three 内部 background box 是 depthTest:false 且最先画，与场景零交互）。
6. **不要设 `scene.environment`** —— 全局环境 uniform 在 SwiftShader 上同样会让接触阴影等透明面片整批不渲染。环境反射走材质级 `envMap`（PBR_MATS 登记 + `applyEnvMaps()` 刷新）。
7. **实例化颜色的哈希别用 `Math.random()`** —— 刷新一次货位就跳一次，看起来像数据在抖。骨架用确定性正弦哈希。
8. 车辆朝向：`lookAt` 会把 **+Z** 对齐行进方向，模型车头在 +X 时要补 `rotation.y += Math.PI/2`。
9. **软件渲染环境（SwiftShader 无头）测不出动态阴影** —— three 的 shadow map 依赖 depth texture 采样，SwiftShader 的 ANGLE 实现不完整，最小复现（一箱一平面）也无阴影。这是环境限制不是代码 bug，真实 GPU 浏览器正常；无头截图里应以接触阴影判断落地感。
10. **内联贴图含运行时推导路径** —— normal/rough 按命名约定在运行时推导，HTML 文本里不存在这些字符串，scaffold 用 `window.__TWIN_TEX_URI__` 映射注入；手动维护页面时别删这段。
11. **地面贴图 repeat 按对比度定，别一刀切** —— 高对比裂缝类贴图（concrete/asphalt）高空俯视 repeat >10 会出斑马纹/摩尔纹，默认 8；低对比贴图（lawn）repeat 8 反而糊成大色斑，用 24~40（campus 预设 32）。改 `groundTexRepeat` 前先想清楚用的是哪种贴图。
12. **改过 `twin-skeleton.html` 必须重跑 `build_three_bundle.py`**（2026-10-19 踩）——`--offline-three` 内联的是预构建的 `three-r160-bundle.js`，骨架源码改了不重建，页面跑的仍是旧引擎：新加的 `type` 会走未知构件兜底（症状：`RoundedBoxGeometry` 计算包围盒报 NaN、新构件不出现），而源码里加的断言/日志也不会打印。改骨架 → `python scripts/build_three_bundle.py` → 再 scaffold。
13. **贴图路径必须由 scaffold 显式注入 `CONFIG.textures`** —— 骨架的默认 textures 是 `{}`。若在骨架里写死 `img/tex-*.jpg`，`--offline-three` 下这份硬编码会随 bundle 进入页面且不经过 `inline_images` 替换，`file://` 打开时整批贴图 CORS 失败、地面建筑全变素色（真库排查极易误判成"曝光问题"）。`scaffold.py` 的 `DEFAULT_TEXTURES` 是唯一来源；`env.sky:'texture'` 时才补三张天图。
14. **大面积地面贴图必须是暗色调**（v0.3 已修）—— `tex-ground.jpg` 旧版 albedo 0.52~0.68 亮灰，900m 场地在强阳光+高空俯视下整片泛白如"雪原"（`gen_textures.py` 的 `gen_ground` 已压到 0.30~0.44 深灰 + 大块色斑）。自己换地面贴图时记住：户外地坪经积灰车辙就是深灰的，亮色贴图 = 一眼假。
15. **CDN 是单点，骨架已内置探测回退链** —— 引擎源码放在 `text/plain` 槽（惰性），boot 脚本依次探测 unpkg → jsdelivr（fetch `package.json`，6s 超时），成功才注入 importmap 并以 Blob URL 动态 import 唤醒；全部失败在加载框里给「重新加载」按钮。**importmap 每文档只允许一份**，所以导入期失败不做换源重试；Draco else 分支经 `window.__TWIN_CDN__` 跟随所选 CDN。scaffold 的 `INJECT_MARK` 指向 boot 标签，改骨架结构时别弄丢。
16. **`envMapIntensity` 的默认是 1 不是 null**（v0.3 踩）—— `MeshStandardMaterial` 自带 `envMapIntensity=1`，所以 `if (m.envMapIntensity == null)` 永远不命中，写在 `applyEnvMaps` 里的默认值是死代码；IBL 默认强度必须在材质工厂（mat/texMat）构造参数里显式给。排查时用消融实验（`envMapIntensity=0` 看亮度变化）而不是看代码"觉得改了"。
17. **Bloom 的 threshold 作用在 tone mapping 前的 HDR 线性域**（v0.3 踩）—— 0.9 的"看起来合理"默认会让亮天空/亮地面整片进入辉光（黄昏白雾、白天发糊）。HDR 域中直射表面亮度 1~10、灯光更高，threshold 1.5~2.0 才只让"真高光"发光。
18. **Preetham 物理天空没有夜晚**（v0.3 踩）—— night 预设只降 rayleigh 没用，只要 `sunPosition` 在天上，夜空就被照成白天（背景 + PMREM + Bloom 全跟着白）。夜晚必须把 skyDome 的太阳沉到地平线以下（`applySkyPreset` 已处理）。
19. **后处理模式下 `renderer.info` 统计失真**（v0.3 踩）—— EffectComposer 每帧多个 pass，`info.autoReset` 默认每次 render 清零，底栏永远显示"绘制 1 / 三角面 0"。骨架已设 `autoReset=false` + 每帧手动 `reset()`；冒烟脚本的绘制数判据依赖这一点。
20. **vendor 加后处理模块后 `build_three_bundle.py` 的 rewrite 要认得上级相对引用** —— 官方 postprocessing 模块里有 `from '../shaders/X.js'`，扁平化进 vendor 目录后必须拉平成 `./X.js`（build 脚本已处理 shaders/math/utils 三个前缀）。新增其他目录层级的 addons 时记得扩这条规则。
21. **外立面构件必须落在墙外表面之外（v0.9 踩，最蠢但最隐蔽）** —— `buildWarehouse` 的墙厚 `t=0.8`，墙中心在 `±d/2`，所以**外表面在 `d/2 + 0.4`**。首版把卷帘门设 `d/2+0.12`、落水管 `+0.18`、窗带 `+0.06`，全部埋进墙里：钢柱在室内透过半透明墙能看见（看起来"有结构"），门和雨棚却一个不剩，极易误判成"代码没生效"。外挂件一律 `d/2 + 0.4 以上`（门 0.45 / 落水管 0.52 / 窗带 0.44）。
22. **调试相机必须显式 `camera.lookAt()`（v0.9 踩）** —— `tw.controls` 是 OrbitControls 且 `enableDamping=true`，只设 `controls.target` + `update()` 不保证朝向（截图会跑到建筑内部，表现为"看到远处货架"）。稳的写法：`controls.target.set(...)` → `controls.update()` → **再 `camera.lookAt(...)`** → `updateProjectionMatrix()`，等 2.5s 后截图。
23. **验证细部要拍 12m 近景 + 裁掉左右 UI 面板（v0.9 踩）** —— 数字孪生页面左右各有约 280px 指标/详情面板，1280 视口下有效画面只剩中间 700px；再加 SwiftShader 把远景细节糊平，30m 外拍立面会"什么都没有"（实测 25m 看不出门，13m + `clip` 裁 UI 后门框/卷帘箱/门板横纹/雨棚斜撑全部清晰）。**看不到 ≠ 没建**，先拉近再下结论；配合量世界 AABB 双保险。
24. **`mergeGeometries` 要求 index「全有或全无」（v0.10 踩）** —— `RoundedBoxGeometry` 在 `segments>1` 时内部 `toNonIndexed()`（`index=null`），而 `CylinderGeometry`/`BoxGeometry` 原生 indexed。两者混在一次 merge 里直接抛 `All geometries must have compatible attributes`。**统一用 `mergeSafe(list)`**（已加进骨架）：merge 前把所有带 `index` 的转 non-indexed。报错信息里的 "geometry at index N" 指的是**数组下标**，按 push 顺序数即可定位。
25. **InstancedMesh 的货位不能太深（v0.10 踩）** —— `rack` 的货位是 `step×d`，warehouse 预设 `size=[56,15,24]` 意味着单货位 5.6m 宽 × **14.9m 深**；一个货位塞一个大货箱，渲染出来是块"地板砖"（视觉模型实测判定为"扁平黄褐色板状、基本平齐"）。解法：**货位内部再切 `COLS×ROWS` 子位**，每子位 1 托盘+1 货箱独立随机高度/朝向/缺货 —— 视觉上才是一摞摞箱子。面数上，托盘改用 `BoxGeometry`（12 tris）而非 `rbox`（108 tris），子位数翻 6 倍也不炸。
26. **`userData` 的资产标识键是 `assetId`，不是 `id`（v0.10 踩）** —— 调试脚本里沿父链找 `userData.id` 会**全部落空**（表现为"场景里查无此资产"）。同理对象 `name` 也常为空，别靠中文名过滤。正确写法：`o.userData && o.userData.assetId`，且 id 挂在父 Group（几何体在子 Mesh），必须沿父链找。
27. **软件渲染下截图会 30s 超时（v0.10 踩）** —— 三角面涨到 1.7M 后，SwiftShader 单帧耗时超过 Playwright 默认截图超时。调试截图前先 `tw.setPostFX(false)` 关后处理链（SSR 会多渲 normal/depth pass，面数与耗时直接翻倍），并把 `screenshot(timeout=120000)`。
28. **改了骨架不重跑 `build_three_bundle.py`，等于没改（v0.11 踩得最惨）** —— `--offline-three` 用的不是 importmap，是 **esbuild 预打好的 IIFE bundle（three + 孪生引擎一起）**，骨架代码已经在 bundle 里。只改 `assets/twin-skeleton.html` 生成的页面跑的还是**旧引擎**，而且**不报任何错**：表现为新加的 `tw.xxx` 是 `undefined`、`CONFIG.performance` 新字段读不到、档位完全不生效。判别法：`grep -c 你的新函数名 产物.html` 有值 ≠ 生效（槽里那份模板不执行），必须 `tw.quality()` 之类实测。**改骨架 → 必跑 bundle → 再 scaffold**，写进流程。
29. **Radiance .hdr 的 RLE 是「通道平面」布局，不是交错像素（v0.11 踩）** —— 解码后缓冲是 `R[0..w] G[0..w] B[0..w] E[0..w]`。当成交错用会让 E 通道错位到 RGB 上，表现是 27% 像素指数 >150（radiance 1e34），PMREM 一算整个场景白成雪原。若自己写 HDR 降采样：解码到平面缓冲 → **显式重排成交错** → 再降采样 → 重编码（每行写 `2,2,w>>8,w&0xff` + 每通道 128 字节 raw 段）。**千万别写 flat**：`RGBELoader` 用首 4 字节是否 `2,2,hi,lo` 判断 RLE，暗部像素恰好命中就会被误判并抛 "wrong scanline width"。
30. **GLB 子树绝不能被距离剔除（v0.11 踩）** —— 储罐/筒仓/货车在 GLB 里拆成罐壳/法兰/爬梯十几个 mesh，每个包围球半径都不到 2m，按「小零件」规则会被整批隐藏：**罐体凭空消失，地上只剩接触阴影圈**。加载时给根节点打 `userData.glbRoot=true`，剔除前沿父链判断豁免。
31. **`composer.setSize()` 会把 GTAOPass/Bloom 的 RT 拉回全分辨率（v0.11 踩）** —— 半分辨率 AO 建好之后，只要触发一次 resize（或 `syncPixelRatio`），`setSize(w,h)` 传的是全尺寸，内部 RT 全部重建回全分辨率，省下的开销静默归零。解法：构造后把 `pass.setSize` 包一层固定缩放再挂进 composer。
32. **法线贴图不要留 PNG（v0.11 踩）** —— 1024² 的无损 PNG 法线单张近 1MB，13 张直接把页面顶到 17MB。转 **WebP q88** 体积降 6~8 倍，精度完全够（游戏里法线本来就是 BC5 有损）。albedo/rough 走 JPEG q82。仓库场景实测：PNG 9.87MB → WebP 1.02MB。
33. **模型内联必须「查表注入」，不能正文替换（v0.11 踩）** —— 同一 GLB 常被引用多次（集装箱 ×14、叉车 ×3），正文替换会在 HTML 里存 14 份相同 base64，白扔 2.5MB。改成注入一份 `window.__TWIN_MODEL_URI__`，骨架加载前查表还原（无映射时保持原路径，`--no-inline` 照常工作）。
34. **集显瓶颈是填充率，不是三角面（v0.11 实测）** —— 所以 `detail` 砍几何是次要手段；真正有效的顺序是：关 SSR > 关 Bloom > AO 降分辨率 > 阴影图降分辨率+静态化 > 贴图降采样 > pixelRatio > 小物件剔除。反过来先砍几何，画面会先"空掉"而不是先"变快"。

## 扩展方式

| 想加什么 | 怎么加 |
|---|---|
| **新构件类型**（皮带机、龙门吊、门禁…） | 在 `BUILDERS` 里加一个 `buildXxx(cfg)` 返回 Group，把 `type` 注册进表即可；`attachAsset` 会自动接管标签、拾取、状态着色 |
| **新场景预设** | 在 `scripts/scaffold.py` 加 `preset_xxx(title)` 并注册进 `PRESETS`，与骨架零耦合 |
| **换贴图** | 直接替换 `assets/img/` 下同名文件即可（天空 1280×853、材质 768×768 平铺），骨架按文件名引用，改图不改代码；想新增材质就在 `CONFIG.textures` 加键 + 构件里用 `texMat(T('键名'), rx, ry)` |
| **加环境配景** | 往 `devices[]` 塞 `ambient:true` 的 `lawn/road/grove/parking/lampRow`，不进清单不计资产数 |
| **真实模型替换占位** | `models[]` 填 `url`；模型坐标系不对就在 `rotation/scale/position` 里纠，不要改加载器 |
| **告警从 WebSocket 推** | 在 `startTimer()` 旁边加 WS 连接，收到消息后调 `applyStatus(id,'alarm')` + 更新 `CONFIG.alerts` + `refreshAlerts()` |
| **嵌进大屏** | 用 `<iframe src="twin.html">` 或直接同页引入；大屏侧关掉顶栏/底栏（给 `#topbar/#bottom` 加 `display:none`）即可当纯视口用，`ResizeObserver` 会自适应 |
| **联动图表** | `window.tw.selectAsset(id)` 与 `tw.status()` 已挂到全局，外部图表点选可直接驱动三维高亮 |
| **做点击下钻** | 在 `selectAsset()` 末尾派发自定义事件 `window.dispatchEvent(new CustomEvent('twin:select',{detail:{id}}))`，外层页面监听即可 |
