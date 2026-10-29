---
name: visual-echarts-dashboard
display_name: 数据大屏原型（ECharts）
display_name_en: ECharts Data Dashboard Prototype
description: "用单文件 HTML + ECharts 快速搭出面向领导演示的可视化大屏：深色科技风布局、任意分辨率等比自适应、KPI 指标卡（数字滚动 + 环比涨红跌绿）、中国省界地图（含南海诸岛九段线）与物流流向、库存与出入库趋势、库区负荷进度条、交易与供应链桑基图、告警列表与底部滚动播报，Mock 数据 + 定时刷新，接口可一键替换。适用于大宗商品、仓储物流、政府监管等场景。当用户说「做个大屏」「数据大屏」「可视化驾驶舱」「领导汇报大屏」「监控看板」时使用。触发词：数据大屏、可视化大屏、驾驶舱、指挥中心、ECharts 大屏、KPI 看板、实时监控、滚动播报、大屏自适应、1920x1080 大屏。"
description_zh: 配置驱动生成深色科技风 ECharts 大屏：行业预设三套（大宗/仓储/监管）、11 类面板组件、Mock 数据引擎与定时刷新、接口可替换、任意分辨率等比缩放、含无头冒烟脚本。
description_en: Build dark-tech ECharts data dashboards (bulk commodity / warehouse logistics / government supervision) from a JSON config, with mock-data engine, auto-refresh, swappable HTTP endpoints and resolution-agnostic scaling.
category: Design Tools
version: 0.4.0
author: hasWhere
tags: ["数据大屏", "ECharts", "可视化", "驾驶舱", "单文件HTML", "配置驱动", "Mock数据", "自适应", "告警播报"]
permissions:
  - file_read
  - file_write
permission_notes_zh: 本 Skill 读取自带骨架 HTML 与用户配置 JSON，在用户指定目录写入大屏页面；不调用外部接口、不上传任何数据。页面运行时按需从 CDN 加载 ECharts（可离线本地化，见 SKILL.md）。
---

# 数据大屏原型（ECharts）

## 这个技能解决什么

**明天上午要看，今天下午才接到需求**的那种大屏——用一份 JSON 配置和一套跑通的骨架把它变出来，而不是从 `<div>` 开始排像素。

**一句话判断**：需要**二维图表 + 指标 + 地图 + 告警播报**的一屏总览 → 用本技能；需要**在三维空间里看位置关系与设备状态** → 用 `visual-threejs-scene`。两者可同屏组合（3D 视口嵌在大屏中间，见「扩展方式」）。

### 三条铁律

1. **设计稿固定一种分辨率**（默认 1920×1080），运行时整体 `scale()` 等比缩放。**绝不**写 `%`+媒体查询去凑响应式——大屏是演示设备，缩放比断点可靠得多。
2. **Mock 优先**：先让一屏数据动起来，再谈接口。接口挂了必须降级为 Mock 而不是白屏。
3. **面板 = 配置项**：加一块图 = 往 `layout` 里加一个对象，不改骨架。

---

## 输入参数

### 顶层配置

| 字段 | 必填 | 说明 |
|---|---|---|
| `meta.title` / `meta.subtitle` | ✅ | 顶栏主标题 / 副标题 |
| `meta.industry` | ✅ | `bulk` 大宗商品 / `warehouse` 仓储物流 / `gov` 政府监管，仅作语义标记 |
| `screen.designWidth` / `designHeight` | ✅ | 设计分辨率，如 1920×1080 / 3840×2160 |
| `screen.fit` | ⭕ | `contain`（留边不裁，推荐）/ `cover`（铺满裁边）/ `stretch`（拉伸填满） |
| `theme.palette` / `accent` | ⭕ | 主色板与强调色 |
| `theme.upColor` / `downColor` | ⭕ | 涨/跌色，**默认涨红跌绿**（国内习惯） |
| `kpis[]` | ✅ | `{label, value, unit, trend, level, fixed}`：`trend` 正数显示红 ▲，负数显示绿 ▼ |
| `layout.left[] / center[] / right[]` | ✅ | 三列面板数组，见下 |
| `map` | ⭕ | 地图分区、流向、底图模式 |
| `alarms[]` | ⭕ | 告警：`{level: crit/warn/info, text, time}` |
| `ticker[]` | ⭕ | 底部滚动播报文案（支持 `<b>` 高亮） |
| `dataSource` | ⭕ | `{mode:'mock'|'http', refreshMs, endpoints:{...}}` |
| `mock.seed` / `jitter` | ⭕ | 伪随机种子与每轮抖动幅度 |

### 面板配置（`layout` 里的每一项）

```jsonc
{
  "id": "trend",                 // 唯一标识
  "type": "line",                // kpi|line|bar|pie|radar|gauge|map|sankey|alarm|table
  "title": "库存与出入库趋势",     // 面板标题
  "en": "IN / OUT TREND",        // 英文副标（科技风必备的装饰性文字）
  "weight": 1.30,                // 同列内的伸缩比（左/右列生效；中列由 CSS 行比例控制）
  "unit": "吨",                  // 右上角单位角标（可选）
  "option": { /* 可选 */ },      // 直接覆盖 ECharts option 片段，做面板级微调
  "value": 86, "metric": "饱和度"  // 仅 gauge 用到
}
```

### 组件能力

| type | 渲染 | 默认数据口径 |
|---|---|---|
| `kpi` | DOM 网格：图标 chip + 大数字滚动 + 环比色（涨红跌绿），发丝线分隔无盒 | `CONFIG.kpis` |
| `line` | 双 Y 轴折线：入库 / 出库 / 在库库存（虚线） | `MOCK.hours` 等 |
| `bar` | 横向排名条，渐变填充 + 右端数值标签 | `MOCK.rank` |
| `pie` | 环形图，**中心富文本合计** | `MOCK.mix` |
| `radar` | 本企业 vs 行业均值双系列 | `MOCK.radar` |
| `gauge` | 半环仪表盘（进度条 + 中心大数） | `cfg.value` |
| `map` | 省界分区着色（重点省坡度 + 标签防重叠）+ 港口脉冲与标签 + 干线流向（渐变 + 匀速光点）+ 南海诸岛插图 + 右上角数据胶囊 | `CONFIG.map` + `MOCK.mapData` + `MOCK.portData` |
| `sankey` | 上游 → 品类 → 分区 → 去向 四级流向 | 自动生成 |
| `alarm` | 告警列表，新条目闪红，最多 `max` 条 | `CONFIG.alarms` |
| `table` | 作业明细表，状态胶囊 | `MOCK.ops` |
| `progress` | 进度条面板：大数字 + 渐变轨道，>85% 烫金 | `cfg.items`，缺省用园区饱和度 |

### 地图 `map`

```jsonc
{
  "mode": "china",               // china：内置中国省界（默认，零外部数据，含南海诸岛九段线）
                                 // schematic：骨架自生成园区矩形栅格（无真实地理需求时用）
                                 // geo：自定义地理底图，必须给 geoJSONUrl
  "hot": ["河北省", "山东省", "江苏省", "上海市"],  // china：重点省（有数据+标签常显），其余省暗底
  "ports": {                     // china：港口/枢纽坐标（流向起止点优先用这里，线形比省质心干净）
    "青岛港": [120.32, 36.06], "天津港": [117.70, 38.98], "上海港": [121.49, 31.23]
  },
  "geoJSONUrl": "",              // geo 模式：本地 .json 或接口，features[].properties.name 为分区名
  "cols": 4,                     // schematic：分区排几列（影响底图宽高比）
  "zones": ["1号堆场", "液体罐区", "散粮筒仓", "装船作业区"],   // schematic：分区名 = 地图标签 = 流向端点
  "sites": [],                   // geo 模式：{name, coord:[lng,lat], value, level}
  "flows": [                     // 流向：from/to 用 ports 名（或省名/分区名），value 决定线宽
    { "from": "青岛港", "to": "天津港", "value": 820 }
  ]
}
```

> **china 模式**内置 `assets/map/china.json`（35 个省级单位，约 157KB，DataV 数据经 Douglas-Peucker 简化、九段线原样保留）。scaffold 生成页面时把它**内联成 `window.__CHINA_GEO__`**，产物仍是单文件；直接打开骨架则异步 fetch `map/china.json`，两者都没有才回退 schematic——**任何路径都不会白屏**。
>
> 渲染时拆成两张底图：**主图**（大陆 + 台湾 + 海南本岛，剔除三沙岛礁）等比投影撑满面板；**南海诸岛**（九段线 + 岛礁）按国标画法收进**右下角小插图**，金描边、永不省略。

---

## 输出结构

```text
<输出目录>/
├── <项目名>-dash.html          # 唯一交付物：单文件大屏（骨架 + 注入的 CONFIG）
└── <项目名>-config.json        # 可选：配置留档，便于二次生成 / 交接
```

页面结构：`#screen`（固定设计尺寸的画布）→ 顶栏（标题 + 行业/数据模式标签 + 时钟 + 全屏/暂停）→ 三列主体 → 底部滚动播报。全部尺寸按设计稿写死，靠 `transform: scale()` 适配任意屏幕。

调试入口（F12 控制台）：`dash.CONFIG`、`dash.tick()`（手动推一轮数据）、`dash.push()`（手动加一条告警）、`dash.refresh()`、`dash.fit()`。

---

## 使用步骤

```bash
S=~/.workbuddy/skills/visual-echarts-dashboard

# 1) 看行业预设
python $S/scripts/scaffold.py --list

# 2) 直接出页面
python $S/scripts/scaffold.py --industry bulk --title "XX港务生产运营驾驶舱" --out ./dash.html
python $S/scripts/scaffold.py --industry gov  --resolution 3840x2160 --out ./gov-dash.html

#   默认把 3 张底图内联成 data URI（产出的 HTML 单文件可带走、双击即开）
#   想外置底图就用 --no-inline（记得把骨架同目录的 img/ 一起复制）
python $S/scripts/scaffold.py --industry gov --no-inline --out ./gov-dash.html

# 3) 精调：导出配置 → 改 → 回填
python $S/scripts/scaffold.py --industry warehouse --dump-config ./wh.json
#    编辑 wh.json（KPI 口径、分区名、告警文案、面板增删）
python $S/scripts/scaffold.py --config ./wh.json --out ./wh-dash.html

# 4) 打开演示：双击即可；要全屏就用页面右上角「全屏」或 F11
```

### 交付改造顺序（别跳步）

1. **定分辨率**：先问清演示屏（1920×1080 / 2560×1440 / 3840×2160）。分辨率定错，字体全废。
2. **换标题与行业**：`meta`。
3. **换 KPI 口径**：`kpis` 六张卡是领导第一眼看的，单位与同比口径必须真。
4. **换重点省与流向**：china 模式改 `map.hot`（重点省名必须与省界数据一致，如"河北省""上海市"）+ `map.ports`（港口坐标）+ `map.flows`（起止点用港口名，线沿海岸走比省质心干净）；用园区示意则改 `map.zones`，名字要和业务叫法一致（"1号堆场"而不是"Zone1"）。
5. **加删面板**：`layout` 三个数组里增删对象，`weight` 调高度；不够用的图表类型用 `option` 覆盖。
6. **换告警与播报**：`alarms` + `ticker`，这两处最容易被领导追问，文案要像人话。
7. **接真数据**：见下节。

---

## 实现要点（骨架已落地，改代码前先读）

### 分辨率自适应
- `#screen` 固定 `designWidth × designHeight`，`fitScreen()` 用 `scale(k)` + 居中偏移；`k = min(w/dw, h/dh)`（contain）。
- 设计尺寸以**配置为准**：`fitScreen()` 会同步写回 CSS 变量 `--dw/--dh`，避免 CSS 与配置各说各话。
- `resize` 防抖 120ms，缩放后**必须**对所有 ECharts 实例调 `resize()`，否则图表停在旧尺寸。

### 底图与氛围

| 用途 | 引用位置 | 文件 |
|---|---|---|
| 大屏底图 | `#screen` 的 `background` | `img/bg.jpg` 1920×1080 —— 深蓝紫渐变 + 点阵世界地图水印 + 三处径向光晕 + 底部透视网格地板 + 上下暗角 |

- 底图之上叠 `#screen::before`：**上下暗化渐变**，保证标题与数字对比度不被底图光晕吃掉。
- 地图面板另叠 `.p-bd-map::after` 一层青色径向光晕，把中心地图衬成"英雄位"。
- 底图走 CSS `background`：加载失败就是纯深色，**不会破图、不会布局塌陷**。
- 底图由 `scripts/gen_bg.py` 程序化生成（可复现、无版权风险）：改渐变/光晕/水印浓度就改脚本顶部署量，重跑即可。

### 图表工厂
- 所有字号、颜色、网格来自 `axisBase()/legendBase()/tipBase()/baseGrid()` 四个基线函数——改一次全屏统一，这是"看起来专业"的关键。
- `hexA()/mixHex()/areaGrad()/barGrad()` 负责所有渐变与透明度，**不要在 option 里手写 rgba 魔法值**。
- `glow()` 给折线/柱体加同色柔光（shadowBlur）——深底上"发亮"而不是"贴"上去，这是参考级大屏与"能看"之间的分界线。
- 面板级微调走 `cfg.option`，骨架 `deepMerge` 合并——业务定制不要动骨架。

### Mock 数据引擎
- `mulberry(seed)` 确定性伪随机：**同一 seed 每次刷新数据连续**，不会出现"数字乱跳像坏了"。
- `mockTick()` 推进时间序列（shift + push）、抖动排名、生成新作业单、按概率生成新告警；`CONFIG.mock.jitter` 控制抖动幅度。
- 数字动效 `rollTo()` 用 `requestAnimationFrame` + easeOutCubic，900ms 滚到位，避免数字闪变。

### 地图（三模式，默认 china 真地图）
- **china**：`assets/map/china.json`（35 省级单位，含台湾/海南/南海诸岛九段线）→ `buildChinaGeo()` 拆主图与南海诸岛 → `registerMap('dashmap' / 'dashmap_jd')` → `geo` 数组渲染。重点省填「深蓝 → 亮青」坡度、>85% 补贴金描边；无数据省暗底，hover 显示"暂无数据"。
- **schematic**：`buildParkGeo()` 自生成边界 + 分区矩形栅格，零外部数据的兜底方案。
- **geo**：自定义 GeoJSON，站点坐标由 `map.sites` 显式给。
- 港口脉冲用 `effectScatter`（`coordinateSystem:'geo'`，标签 `position:'top'` + `labelLayout.hideOverlap`）；流向用 `lines`：起端暗末端的**渐变线**（按线段包围盒方向）+ 线上匀速光点（`effect.symbol:'circle'` + 短 trail），端口坐标取 `map.ports`，缺省回退省质心。
- `geo` 与 `series.map` 不要同时用来画同一张底图，会渲染两层；本骨架统一用 `geo` + `regions` 着色。
- **省形不能压扁**：`aspectScale` 语义是 `y px/度 = x px/度 ÷ a`，**a=1 才是等比投影**（1°经度 = 1°纬度），>1 就是纵向压扁（v0.3 用 1.3 被用户点名"压扁"，已回 1）。主图剔除三沙后 bbox 61.6°×35.4°（1.74），与宽屏地图面板比例接近。
- **`layoutSize` 实测语义**：`X%` → 地图外接正方形边长 = `X% × 0.953 × min(面板宽, 高)`，再对地图 bbox 做 contain 适配。992×604 的地图面板下 **172% ≈ 宽 100% / 高 95% 撑满**；改面板比例（如中列行高、设计分辨率）需按此公式重算，别凭感觉拍。
- 南海诸岛插图用 `left/right/top/bottom` 百分比定位（`left:'86%' right:'1.5%' top:'71%' bottom:'4%'`），实测内容会比盒子略向左上偏移约 2%，已按避开台湾（最东 124.6°E）留足净距；`silent:true` 不响应 hover。
- `labelLayout: { hideOverlap: true }` 让 ECharts 自动隐藏被遮挡的省标签——京津冀鲁苏沪挤在一处，没有它标签糊成一团。
- 地图面板右上角有数据胶囊（省级单位数/重点省数/主干流向/平均饱和度），由 `buildMapStats()` 生成、`updateMapStats()` 随刷新更新。

### 告警与播报
- 告警列表 DOM 渲染，新条目加 `.flash` 动画类（一次性），超长自动截断，`max` 控制条数。
- 滚动播报用 CSS 动画 `translateX(-50%)` + **内容复制两份**实现无缝循环；时长按文本宽度除以 62px/s 计算，**长短文案速度一致**。
- 点「暂停刷新」同时冻结数据定时器与播报动画（`animationPlayState`），演示时能定格讲解。

### 性能
- 所有图表 `renderer:'canvas'`；面板容器没高度时不初始化（否则 ECharts 会以 0 高度建实例，整块空白），骨架里用 `clientHeight < 20 → 等一帧重试` 兜住。
- `document.hidden` 时跳过刷新；定时器统一由 `startTimer()` 管理，重复调用先清旧的。

---

## 数据接口（Mock → 真实）

```jsonc
"dataSource": {
  "mode": "http",
  "refreshMs": 6000,
  "endpoints": {
    "kpis":    "/api/dash/kpis",     // { kpis:    [{label,value,unit,trend,level}] }
    "series":  "/api/dash/series",   // { hours, inbound, outbound, stock, days, inboundD, outboundD, rank, mix }
    "alarms":  "/api/dash/alarms",   // { alarms:  [{level,text,time}] }  ← 只回增量，前端自己 prepend
    "map":     "/api/dash/map",      // { zones:   [{name,value}] }
    "ticker":  "/api/dash/ticker"    // { ticker:  ["...", "..."] }
  }
}
```

约定与边界：

- **接口只回数据，不回样式**；字段名不一致就改 `pullRemote()` 里的映射，别动图表工厂。
- 任一接口失败 → `console.warn` + 保持 Mock 继续跑（演示现场不能白屏）。
- 告警接口若回全量，记得在前端去重（骨架当前按"增量 prepend"设计）。
- 实时性要求高（秒级）时把 `refreshMs` 调到 2000 以内，或改用 WebSocket：在 `startTimer()` 旁挂 WS，收到消息后更新 data + `refreshAll(true)`，**不要**为每帧数据重建 ECharts 实例（`setOption(opt, true)` 全量替换即可）。

---

## 离线与内网部署

骨架从 jsDelivr 加载 `echarts@5.5.0`，并带 unpkg 自动兜底（主源被墙/限流时切第二源，不会白屏）。内网环境把 `echarts.min.js` 下载到页面同级 `vendor/`，把两个 `<script src=...>` 都改成相对路径即可（ECharts 单文件、无子资源依赖，比 Three.js 好处理）。**改完必须重跑冒烟。**

---

## 质量校验（交付前必做）

```bash
python <skill>/scripts/smoke_headless.py ./dash.html --size 1920x1080 --expect-panels 10 --shot ./preview.png
```

硬指标：**pageerror 为空、console.error 为空、可见 canvas 数 > 0、`#screen` 溢出为 0、面板数 = 配置条数**。再顺手切一次目标分辨率（`--size 3840x2160`）确认缩放不裁不糊。

已知易踩的坑（骨架里已规避，改代码时别改回去）：
1. **容器没高度就 `echarts.init`** → 图表空白且不报错；必须先确认有高度。
2. **忘了 `chart.resize()`** → 换分辨率/全屏后图表还是旧尺寸，看着像"卡住了"。
3. **`geo` 与 `series.map` 同时渲染同一张底图** → 两层叠在一起，颜色对不上。
4. **满饱和色铺满分区** → 一屏荧光蓝，领导看着累；分区用暗色坡度，只让**数值高**的分区发亮。
5. **滚动播报不复制两份内容** → 每轮结尾闪一下再跳回开头。
6. **涨跌配色反了** —— 国内业务语境下涨用红、跌用绿，别照搬欧美绿涨红跌。
7. **`aspectScale` 调大去"填满"宽面板** —— 那是纵向压扁省形（海南含三沙时更糟）；正确做法是主图剔三沙走插图 + `aspectScale:1` + 按 `layoutSize` 公式算填充。

## 扩展方式

| 想加什么 | 怎么加 |
|---|---|
| **新图表面板** | `layout` 里加 `{id,type,title,en,weight}`；若要**新图表类型**，在 `OPT_BUILDERS` 加一个 `optXxx()` 并注册 |
| **换底图** | 替换 `assets/img/bg.jpg`（1920×1080，cover）即可，骨架按文件名引用，改图不改代码；或改 `scripts/gen_bg.py` 顶部署量重跑生成 |
| **新行业预设** | `scripts/scaffold.py` 加 `preset_xxx(title)` 并注册进 `PRESETS`，与骨架零耦合 |
| **多屏轮播 / 页面切换** | 配多份 `layout` 当"页"，加一个按钮切换 `layout` 后重建面板（`boot()` 已可重复调用） |
| **地图换成真实辖区/园区** | 全国图改 `map.hot` + `map.flows`（省名精确匹配）；园区/自定义辖区用 `map.mode='schematic'|'geo'` + `zones`/`geoJSONUrl` |
| **换中国地图数据** | 重跑 `scripts/simplify_china.py`（改容差/数据源见脚本头）；注意：**九段线（100000_JD）绝不能 simplify**，细长弧线会被简化没；脚本还会把海南省的三沙岛环（lat<18.5）从主图剔除（`MAIN_MIN_LAT`），否则主图 bbox 被拉成 1.24 竖条、宽屏面板放不下 |
| **嵌三维数字孪生** | 在中间列把 `map` 面板换成 `<iframe src="twin.html">`（并隐藏 3D 页顶栏/底栏），或同页引入双技能产物 |
| **点击下钻** | 在 `renderChart` 后监听 `chart.on('click', p => ...)`，弹层或跳详情页；数据源侧预留 drilldown 接口 |
| **大屏截图归档** | 用本技能的 `smoke_headless.py --shot` 即可定时出图，无需人工截屏 |
