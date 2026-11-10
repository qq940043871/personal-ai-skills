# 扩展：加构件 / 接实时数据 / 内网部署

## 一、新增一种构件类型

骨架里的构件统一走 `BUILDERS` 分派表，加一种类型只动三处。

**1) 写工厂函数**（放在 `assets/sandbox-skeleton.html` 的「构件工厂」段）：

```js
/* 约定：返回一个 Group，几何以自身底心为原点（y=0 在地面），
   不要自己写 world position —— 装配阶段统一设置。 */
function makeTank(e, lc){
  var T = S.THREE, g = new T.Group();
  var r = num(e.radius, 8), h = num(e.height, 16);
  var body = new T.Mesh(
    new T.CylinderGeometry(r, r, h, 24),
    new T.MeshStandardMaterial({ color: C(e.color || 0x9aa8b4), roughness: 0.45, metalness: 0.6 })
  );
  body.position.y = h / 2;
  body.castShadow = true; body.receiveShadow = true;
  g.add(body);
  g.add(outline(new T.CylinderGeometry(r, r, h, 24), lc, 0.32));   // 描边必须过 outline()
  addGroundShadow(g, r*3.2, r*3.2);                                // 落地感
  return g;
}
```

**2) 注册到分派表**：

```js
var BUILDERS = { …, tank: makeTank };
```

**3) 如果是点实体，加入 `POINT_TYPES`**：

```js
var POINT_TYPES = { tower:1, plant:1, warehouse:1, block:1, tree:1, alarm:1, tank:1 };
```

否则装配阶段不会写 `position`，实体会全部堆在原点。

**4) 同步构建脚本的白名单**（否则配置校验会报「未知构件类型」）：
`scripts/build_sandbox.py` 顶部的 `POINT_TYPES` / `LINE_TYPES` / `KNOWN_TYPES`。

漏掉第 4 步是新手最常犯的错——页面能跑，但构建直接失败。

## 二、接实时数据

骨架刻意**不内置轮询**：接口契约因行业而异，塞一个假约定进去反而碍事。
运行时入口只有两个：

```js
sandbox.update(entityId, { status, metrics, name })   // 改单个实体
sandbox.updateAll([{ id:'P1', status:'alarm' }, …])   // 批量
```

最小可用接法（在产物 HTML 末尾追加一段经典 script 即可，不必动骨架）：

```html
<script>
(function(){
  var base = 'https://your-api.example/park';
  function pull(){
    fetch(base + '/snapshot').then(function(r){ return r.json(); }).then(function(d){
      if (!window.sandbox) return;
      // 期望结构：[{ id:'P1', status:'alarm', metrics:[{label,value,pct}] }]
      window.sandbox.updateAll(d.entities || []);
      (d.alarms || []).forEach(function(a){       /* 左上角时钟旁的告警列表按需自行渲染 */ });
    }).catch(function(e){ console.warn('[data] 拉取失败', e); });
  }
  var timer = setInterval(pull, 5000);
  pull();
  window.addEventListener('beforeunload', function(){ clearInterval(timer); });
})();
</script>
```

要点：

- `status` 变化会自动重建告警光柱与脉冲环，不用管 3D 层。
- `metrics` 传 `[]` 表示清空；字段名必须是 `label / value / pct`。
- 别把整份配置重新注入——重建场景会黑屏闪一下，更新走 `update` 就够。
- 若数据源是 WebSocket：把 `setInterval` 换成 `ws.onmessage`，其余一致。

## 三、内网 / 离线部署

页面只依赖 three 本体（一个 `three.min.js`），三条路径按需选：

| 场景 | 做法 |
|---|---|
| 内网有静态服务器 | 把 `three.min.js` 放到内网，配置 `"threeSources": ["http://内网/three.min.js"]` |
| 完全离线 | 同上但用 `file:///D:/lib/three.min.js`；注意浏览器需允许本地文件互引 |
| 允许降级 | 什么都不做，加载失败自动切等距二维，图层/时间轴/详情照常可用 |

`threeSources` 是**有序回退列表**，每个源 6 秒超时，全部失败才降级。
建议至少给两个源，别只写一个。

## 四、改主题 / 换品牌色

- 主色在 CSS 变量 `--cy`（`#35e0ff`），辅色 `--vi`（`#7c8cff`），告警 `--alarm`。
- 三维侧的图层色在配置里逐层给 `color`，它同时驱动**描边、管线流光、告警脉冲、标签高亮**。
- 三时段调色板在骨架的 `PALETTE`（`day` / `dusk` / `night`）：
  改 `sun`/`hemiSky`/`hemiGnd`/`win`/`exposure` 即可整体换氛围，别逐材质改。
- 换时段后**一定要重新截图确认曝光**：暮色与夜色的合适曝光差 0.1~0.15。

## 五、加一种 HUD 面板

HUD 是纯 DOM，不参与 three 渲染：

1. 在 `<body>` 里按 `.pane` 写一块面板（四角亮标由 `.pane::before/::after` 自动给）。
2. 在 `buildUI()` 里填充内容。
3. 位置用 `position:absolute` + 四角偏移；注意 ≥1240px 宽的媒体查询里已有布局收敛规则。

面板不要超过 4 块——沙盘靠留黑才有模型感。

## 六、导出静态图

`verify_sandbox.py --shot` 就是一条现成的截图流水线（swiftshader 无头）。要更高分辨率：

```bash
python scripts/verify_sandbox.py out.html --shot big.png --width 2560 --height 1440
```

相机固定用 `--shot-preset N` 选机位，便于多轮迭代对比同一构图。
