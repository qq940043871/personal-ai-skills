# 配置契约（完整字段）

配置文件是一份 JSON，交给 `scripts/build_sandbox.py` 后与内置模板**深度合并**
（对象递归合并、数组整体替换），所以只需写要改的片段。

## 坐标系

```
        +Z（南，默认相机所在侧）
         │
  ───────┼───────  +X（东）
         │
        -Z（北）
```

- 台面中心为原点，`y = 0` 是台面顶面（建筑底标高）。
- 台面范围：`x ∈ [-size[0]/2, +size[0]/2]`，`z ∈ [-size[2]/2, +size[2]/2]`。
- `base.terrain` > 0 时，地表在**台面四周**隆起（中心保持平坦），所以建筑不会浮空；
  但地形幅度别超过 6，否则边缘坡会把靠边的实体包进去。
- 台体厚度向下延伸 `size[1]`，侧面是程序化地层剖面。

**定位规则**（最容易搞错的一条）：

| 实体类别 | 定位方式 | 备注 |
|---|---|---|
| 点实体 `tower` `plant` `warehouse` `block` `tree` `alarm` | `position: [x,y,z]` | 几何以自身底心为原点，`y` 一般填 0 |
| 线实体 `road` `pipe` `vehicle` | `points` / `path`（世界坐标） | 实体自身 `position` 被忽略 |
| 面实体 `zone` | `polygon: [[x,z], …]`（世界坐标） | 顶点顺序决定填充，闭合由程序补 |

## 顶层字段

```jsonc
{
  "meta":   { "title": "…", "subtitle": "…", "badge": "智慧园区" },
  "base":   { "size": [420, 26, 320], "terrain": 5, "terrainSeed": 12, "surface": "park" },
  "env":    { "timeOfDay": "dusk", "fog": 0, "exposure": 0.95, "shadow": true },
  "camera": { … },
  "presets": [ … ],
  "layers": [ … ],
  "kpis":   [ … ],
  "alarms": [ … ],
  "timeline": { … },
  "clip":   { … },
  "threeSources": [ "…" ]
}
```

### base

| 字段 | 默认 | 说明 |
|---|---|---|
| `size` | `[420,26,320]` | 宽 / 台体厚度 / 深。园区常用 360~480，厂区 320~400 |
| `terrain` | `3.2` | 边缘地形起伏幅度；0 = 纯平板，> 6 会盖住靠边实体 |
| `terrainSeed` | `12` | 地形种子；同一份配置每次刷新地形一致 |
| `surface` | `park` | `park` 草绿 / `concrete` 混凝土 / `asphalt` 沥青 |

### env

| 字段 | 默认 | 说明 |
|---|---|---|
| `timeOfDay` | `dusk` | `day` 白天 / `dusk` 黄昏 / `night` 夜间（联动太阳色温、天光、窗光强度、曝光） |
| `fog` | `0` | 指数雾密度。**默认关**；真要加别超过 0.0008，见 `04-pitfalls.md` |
| `exposure` | 随时段 | 覆盖色调映射曝光，一般 0.9~1.1 |
| `shadow` | `true` | 动态阴影开关；软件渲染环境可关掉换性能 |

### camera

| 字段 | 默认 | 说明 |
|---|---|---|
| `fov` | `42` | 视角。沙盘建议 34~38，画面更紧凑饱满 |
| `position` | 按台面自动 | 相机世界坐标 |
| `target` | `[0,0,0]` | 注视点；沙盘略偏向实体密集侧更耐看 |
| `minPolar` / `maxPolar` | `12` / `82` | 俯仰限制（度）；`minPolar` 太小会变成正俯视，看不出台体厚度 |
| `minRadius` / `maxRadius` | 台面对角 ×0.22 / ×2.4 | 缩放范围 |
| `autoRotate` | `false` | 缓慢环绕，`autoRotateSpeed` 建议 0.08~0.16 |
| `near` / `far` | `1` / `4000` | 裁剪面 |

### presets

```jsonc
{ "id": "overview", "label": "全景", "position": [313, 252, 353], "target": [22, 0, 6] }
```

`position`/`target` 会被换算成球坐标做 900ms 缓动飞行。**第一个 preset 建议与 `camera` 完全一致**，
否则首屏与点「全景」的视角不一致，观感很怪。

### timeline

```jsonc
"timeline": {
  "enabled": true, "durationSec": 32, "autoplay": true,
  "frames": [ { "t": 0, "activity": 0.3, "label": "班前" }, … ]
}
```

- `t` 单位是**秒**，必须 ≤ `durationSec`。
- `activity ∈ [0,1]`：相邻两帧之间线性插值，作为车辆速度的**倍率**（下限 0.05，不会完全停住）。
- `label` 显示在时间轴刻度与右侧进度文字上；拖动进度条会实时生效。
- 少于 2 帧时构建脚本会告警——一帧的时间轴没有推进意义。

### clip

```jsonc
"clip": { "enabled": true, "axis": "x", "value": 1 }
```

- `axis: "x"` 沿 X 方向切（从 +X 侧切进去），`"z"` 沿 Z 方向切。
- `value ∈ [0,1]` 表示**保留比例**：1 = 不切（平面退到台面外），0.5 = 切掉一半，0 = 全切掉。
- 开启时所有材质临时切到 `DoubleSide`，关闭时按缓存的原始 `side` 还原——别在业务代码里手动改 `side`。

## 图层与实体

```jsonc
"layers": [
  {
    "id": "building",
    "label": "建筑",
    "color": "#35e0ff",      // 图层色：作用于描边、流光、告警脉冲
    "on": true,
    "entities": [ … ]
  }
]
```

- 图层是**点亮/熄灭的最小单位**，左侧面板一行一个，行尾显示实体数。
- 点亮/熄灭用「从台面升起/落下」表达（缩放 + 位移 260ms），不触碰材质（材质是共享的）。
- 建议分组：`zone` 地块 / `road` 路网 / `building` 建筑 / `pipe` 管廊 / `vehicle` 车辆 / `green` 绿化 / `alarm` 告警点。
  超过 8 个图层左侧面板会开始拥挤。

### 实体通用字段

| 字段 | 说明 |
|---|---|
| `id` | **必填且全局唯一**。告警 `entityId`、拾取、`sandbox.select()` 都靠它 |
| `name` | 场景标签文案；不写则用 `id`，`label:false` 可强制不显示 |
| `status` | `normal` / `warn` / `alarm` / `off`，决定描边与标签配色，`warn/alarm` 会加光柱脉冲 |
| `metrics` | `[{label,value,pct}]`，点选后右侧详情卡的指标条；`pct` 给 0~100 会画进度条 |
| `color` | 覆盖构件默认色（会走 sRGB→linear 转换） |
| `rotation` | 绕 Y 轴旋转（弧度），仅点实体有效 |

### 各构件专属参数

**tower**（高层楼宇）

```jsonc
{ "id":"HQ", "type":"tower", "position":[-95,0,-105], "size":[32,72,28], "emissive":"#a8d8ff" }
```

`size[1]` 是楼高；窗格密度由宽高自动推导（一层 ≈ 4、一开间 ≈ 2.6）。
自带裙房（占地 1.5 倍、高 12%）与屋顶机组，不需要额外配。

**plant**（厂房）

```jsonc
{ "id":"P1", "type":"plant", "position":[120,0,-95], "size":[88,15,42], "roofColor":"#4d5d6b" }
```

双坡金属屋面 + 天窗带 + 竖墙肋 + 1.8 高勒脚 + 卷帘门。屋面坡高按 `size[1] * 0.22` 自动算。

**warehouse**（仓储）：同 `plant` 但为拱形屋面、无天窗带。

**road**（道路）

```jsonc
{ "id":"R1", "type":"road", "width":16, "points":[[-195,0.5,-2],[-60,0.5,0],[60,0.5,0],[195,0.5,2]] }
```

- 至少 3 个控制点（2 个点会退化成直线，构建脚本会告警）。
- `points` 里的 `y` 建议恒为 0.5，路面会自动抬到 0.09、虚线到 0.13，避免与地表 z-fighting。

**pipe**（管廊）

```jsonc
{ "id":"PL1", "type":"pipe", "radius":0.9, "flow":true, "points":[[10,9,54],[10,9,20],[76,9,20]] }
```

`points.y` 就是架空高度，中心线高于 1.5 的段落会自动生成支墩。`flow:false` 关掉流光。

**vehicle**（车辆）

```jsonc
{ "id":"V1", "type":"vehicle", "speed":26, "phase":0.2, "kind":"car", "path":[[-185,0,3],[0,0,0],[185,0,-2]] }
```

- 沿路径**往复**行驶（前半程正向、后半程反向），不会凭空瞬移。
- `speed` 是单位/秒的名义速度，实际速度 = `speed × activity`。
- `phase ∈ [0,1]` 错开多辆车的起始位置。
- `kind:"car"` 去掉货箱，变成小车。

**zone**（地块）

```jsonc
{ "id":"Z1", "type":"zone", "color":"#35e0ff", "opacity":0.07, "polygon":[[68,-158],[203,-158],[203,-22],[68,-22]] }
```

填充透明度建议 0.05~0.1，再高会把地面压成一块色斑。描边自动加在同色 0.75 透明度。

**tree**（绿化）

```jsonc
{ "id":"G1", "type":"tree", "position":[-170,0,135], "count":22, "spread":[42,34], "seed":21, "label":false }
```

`count` 棵实例化树散布在 `position ± spread/2` 的矩形内，`seed` 决定每棵的位置与大小（可复现）。

**alarm**（告警点）

```jsonc
{ "id":"AL1", "type":"alarm", "position":[120,0,-95], "level":"critical", "scale":1 }
```

`critical` 红 / `warning` 琥珀。光柱高 26×scale，双层脉冲环。

## kpis / alarms

```jsonc
"kpis": [ { "label":"入驻企业", "value":42, "unit":" 家", "trend":5.0 } ]
```

`value` 是数字时会自动千分位/取整；`trend` 为负数会标红并显示负号。最多展示 4 个，多了自动丢弃。

```jsonc
"alarms": [ { "entityId":"P1", "level":"critical", "text":"3 号产线温度超限", "time":"14:22" } ]
```

`entityId` 指向不存在的实体时构建脚本会告警（点了不会跳转）。点击告警会选中并飞向该实体。
