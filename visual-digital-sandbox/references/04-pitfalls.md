# 坑位记录（全部真实踩过）

按「症状 → 原因 → 修法」写，出问题时按症状查。

---

## 1. 画面整体发灰发白，像未上色的白模

**原因 A：色彩管线。** three r149 没有 ColorManagement，`new THREE.Color(0x2a3a48)` 被当作**线性反射率**采样，
输出到 sRGB 屏幕变成 `#8a97a3`。

**修法**：全部颜色过 `C(hex)`（`convertSRGBToLinear()`），纹理设 `encoding = sRGBEncoding`。

**原因 B：窗格密度。** 幕墙用 `repeat.set(round(w/11), round(h/9))`，50 米高的楼会出现 130 行窗，
远处必然混叠成均匀亮色。

**修法**：`repeat.set(bays/8, floors/22)`，`floors = h/4`、`bays = w/2.6`。

---

## 2. 转换色彩管线后画面全黑

**原因**：颜色转成线性后亮度整体下降约 2~3 档，而光照强度还是按"直出"配的。

**修法**：三步重配——① 光线强度提到 1.5~2.5；② 材质基色提到 sRGB 0.35~0.55；
③ 曝光 0.9~1.1。**别继续压 albedo**，否则会一路滑进剪影。

---

## 3. 沙盘消失成一片黑，只看得到一小块草地

**原因**：`FogExp2` 的衰减是 `exp(-(distance × density)²)`，不是线性的。
`density = 0.0024` 在 700 单位处 `exp(-2.82) ≈ 0.06`，94% 被雾吃掉。

**修法**：沙盘是模型展示，**默认关雾**（`env.fog = 0`）。真要加不超过 0.0008。

---

## 4. 地面上一块块"脏斑"

**原因**：不是贴图，是**动态阴影**。太阳高度只有台面对角的 0.85 倍，阴影拖得很长。

**修法**：太阳高度提到 1.45 倍，`shadow.radius = 2.4` 柔化边缘。
排查时可以先关 `env.shadow` 截图对比，别一头钻进贴图里找。

---

## 5. 建筑像浮在半空 / 没有落地感

**原因**：沙盘是加厚台体，地面本身没有承接阴影。

**修法**：两套并用——动态阴影 + 贴地投影贴片（径向渐变 canvas，贴在脚下，取占地 1.5 倍）。
软件渲染环境下动态阴影不可靠，贴片是保底方案。

---

## 6. 剖切关掉后，双面材质变成了单面

**原因**：`applyClip()` 把 `material.side` 改成 `DoubleSide`，关闭时统一改回 `FrontSide`。
但材质是**共享**的，屋顶、地块、光柱原本就是双面，被永久改坏。

**修法**：首次改之前把原始 `side` 缓存到 `material.userData.__side`，还原时按缓存回填。

---

## 7. 关掉某个图层后，其他图层的材质跟着变透明

**原因**：想做淡出就把材质的 `opacity` 往下插值，但 `stdMat()` 是**共享材质缓存**，
一个材质被多个图层/多个实体复用。

**修法**：不要碰材质。图层显隐用「从台面升起/落下」（`scale.y` + `position.y` 补间 260ms），
既避开共享材质，又比淡入更符合"沙盘插片"的物理直觉。

---

## 8. 三个源都加载失败但页面没有任何降级

**原因**：`scene.background = new Color(...)` 的 `alpha:false` 渲染器 + 初始化异常，
在 `initScene()` 中间抛错时既没 3D 也没 2D。

**修法**：`initScene()` 整段包 try/catch，失败时把 `S.mode` 复位再走 `fallback2D()`；
降级路径要**独立**重建 `layerMap` / `entMap`（3D 的装配没跑过），否则图层面板是空的。

---

## 9. 状态标记的脉冲不动 / 改状态后光柱不消失

**原因**：状态标记原本由构件工厂内部创建，没有引用，运行时无法增删；
且每帧 `scene.traverse` 找 `pulse` 会拖慢主循环。

**修法**：构件工厂**不管状态**，由装配阶段统一 `attachMarker()` 挂载，
并把带 `pulse` 的对象收集进 `S.pulsers` 数组；`updateEntity()` 改状态时 `detachMarker()` 再重建。

---

## 10. 构建报「未知构件类型」但页面里明明能跑

**原因**：骨架的 `BUILDERS` 加了新类型，但 `scripts/build_sandbox.py` 的
`POINT_TYPES / LINE_TYPES / KNOWN_TYPES` 白名单没同步。

**修法**：两处都要改。加构件类型是**四处联动**：工厂函数、`BUILDERS`、`POINT_TYPES`、构建脚本白名单。

---

## 11. 全屏截图里 `file://` 双击打开是白屏

**原因**：用了 `<script type="module">` + importmap。file:// 下 origin 为 `null`，
模块脚本会被 CORS 拦掉。

**修法**：three 走**经典 script**（`three.min.js` UMD，r149），三源回退，不用 importmap、不用 module。
代价是不能用 three 的 addons（OrbitControls/CSS2DRenderer 等）——所以相机控制和标签投影都是手写的。
