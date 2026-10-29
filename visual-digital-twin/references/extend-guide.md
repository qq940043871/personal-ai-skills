# 扩展指南：新增场景 / 组件 / 接真实数据（v2 写实引擎）

## 一、Scene 模块接口（assets/scenes/xxx.js）

### 写实引擎（v2 默认，three r160 ES module）

场景文件与 engine.js 在构建期拼接成一个 module（场景在前、引擎在后），
场景只负责声明 spec 对象，渲染器/天空/材质/相机全部由引擎提供：

```js
window.__DT_SCENE_SPEC__ = {
  id: 'city',                        // 与文件名、config.scene 一致
  name: '智慧城市 / 园区楼宇（写实）',
  camera: { pos: [190,150,230], target: [0,10,0] },
  textures: ['concrete','asphalt','ground','lawn','glass'],  // 声明用到的贴图（构建期按此内联）
  iso: function () { /* 2D 降级节点数组，格式同 classic */ },
  init: async function (E, ctx) { /* 返回 controller */ }
};
```

**贴图声明是硬契约**：`textures` 数组决定构建期把 `assets/img/tex-<name>*` 内联为
data URI；场景里 `E.texMat(name, …)` 用到的每个名字必须出现在数组里，漏了运行时
就是无贴图的纯白。

### init(E, ctx) → controller

- `E`（引擎 API）：`THREE / renderer / scene / camera / root / canvas / cfg / bus / toast /
  timeOfDay / setTimeOfDay / onTOD / mat / texMat / rbox / contactShadow / label /
  beaconPillar / flowLine / pulseRing / orbit / picker / loadModels / tuneShadow / refreshSky`
- `ctx`：`{ canvas, container, cfg, bus, toast }`（与 classic 相同，无 THREE——用 E.THREE）

controller 必须实现：

```js
{
  orbitRef,                // E.orbit() 的返回值（引擎主循环代为 update）
  update(dt, t),           // 每帧动画（车流/AGV/船摇…）
  setLayer(id, on),        // 图层开关（对应 config switches 的 id）
  focus(id),               // 相机聚焦（对应 entities/rank 的 dataId）
  dispose()                // 清理场景自有资源（引擎负责 raf/renderer）
}
```

写实场景固定套路（参考 scenes/city.js）：
1. 地面/道路用 `E.texMat(name, {repeatX, repeatY, color, roughness})`；**高空视角
   repeat 别超过 10 左右**，否则平铺出斑马纹
2. 建筑设备用 `E.rbox()`（圆角几何）+ `castShadow/receiveShadow = true`
3. 动效克制：车流/AGV/船摇等「真实运动」优先于流光光点；飞线/光柱低透明度
4. 昼夜双态用 `E.onTOD(t => …)`（如窗户 emissiveIntensity：day .05 / dusk 1.1）
5. 图层对象写 `userData.layer`；`bus.on('layer'/'focus'/'cmd'/'orbit')` 接运行时

### classic 引擎（assets/scenes-legacy/，v1 兼容）

接口与 v1.0.0 完全一致（`window.__DT_SCENE__` + 全局 THREE + DTH 工具箱），
用 `--engine classic` 构建时生效。

### iso() 降级节点格式（两引擎通用）

```js
[{ type:'block'|'belt'|'tank'|'yard', id, name, color, x, z, w, d, h }]
```

## 二、引擎 API 速查（写实，assets/core/engine.js）

| API | 用途 |
|---|---|
| `E.mat(opts)` | MeshStandardMaterial，自动注册材质级 envMap |
| `E.texMat(name, opts)` | PBR 三件套（albedo/normal/rough 自动挂载，color 调色） |
| `E.rbox(w,h,d,r,seg)` | RoundedBoxGeometry 圆角盒 |
| `E.contactShadow(w,d)` | 顶点色 alpha 接触阴影面片 |
| `E.label(text,opt)` | Sprite 文字标签 |
| `E.beaconPillar(r,h,color)` | 渐变光柱（分区/设备定位，支持 .update） |
| `E.flowLine(curve,opt)` | 沿曲线低饱和流动光点（航线） |
| `E.pulseRing(radius,color,opt)` | 扩散扫描环 |
| `E.orbit(camera,dom,opt)` | OrbitControls 封装（auto/flyTo/reset） |
| `E.picker(renderer,camera,dom)` | 射线拾取（读 userData.data/focusId） |
| `E.loadModels(list,onEach)` | config.models[] → GLB+Draco 加载，失败回退占位体 |
| `E.setTimeOfDay('day'/'dusk')` | 切换昼夜（太阳/天光/曝光/雾联动） |

## 三、自定义 GLB 模型

1. `.glb` 放 `assets/models/`（Draco 压缩可用，decoder 自动内联；三件套 .gltf+.bin 不支持，先转单文件）
2. config 加：
```json
"models": [{ "id":"M-01", "name":"堆垛机", "url":"models/xxx.glb",
             "position":[10,0,20], "rotation":30, "scale":1,
             "fallback":{ "type":"box", "size":[4,14,3] } }]
```
3. 构建：自动 base64 内联（>8MB 警告）、检测 Draco 并内联 decoder、加载失败回退占位体

## 四、新增面板组件

1. 在 `runtime.js` 的 `Comp` 对象加 `myType: function(box, def){ … return {tick} }`
2. 返回 `null` 表示静态组件；返回 `{tick(items)}` 参与 mock 脉冲
3. 样式加在 `layout.css`，遵守视觉规范 token

## 五、接真实数据（替换 mock）

mock 脉冲由 `runtime.js` 的 `pulse()` 驱动（config.pulse=false 可关闭）。接入真实
数据的标准做法：

```js
// 方式 A：轮询
setInterval(() => fetch('/api/kpi').then(r => r.json()).then(d => {
  window.DTBus.emit('kpi', d);
}), 5000);

// 方式 B：WebSocket
const ws = new WebSocket('wss://host/realtime');
ws.onmessage = e => window.DTBus.emit('realtime', JSON.parse(e.data));
```

**构建产物只做展示层，数据接入代码写在 config 驱动的自定义 script 或改造 runtime 后重新 build。**

## 六、注册新场景 checklist

- [ ] `assets/scenes/my.js` 实现 `__DT_SCENE_SPEC__`（textures 声明别漏）
- [ ] `templates/config/my.json` 默认面板配置（左右各 ≤4 面板）+ `env.timeOfDay`
- [ ] `build_twin.py` 的 `SCENE_ALIAS` 加中英文别名
- [ ] 语法检查 + `verify_screen.py` 冒烟（写实 3D 与 `--offline` 2D 各验一次）
- [ ] 徽标「写实三维」、pageerror/资源失败为空、面板数 = 配置数、截图非空白
