# 设计系统：类 APP 工作台

三套主题 + 七类组件 + 布局骨架 + 交互规范。生成原型时**逐条对照本文执行**，不要自由发挥；所有颜色/圆角/阴影只引用 `:root` 变量。

## 设计原则

1. **iPad 优先**：竖屏 768–834px 宽为主场景，横屏兼容；内容列最大 720px 居中，避免横向拉伸稀疏。
2. **拇指可达**：高频操作放底部（tabbar、主按钮、sheet）；右上只放低频操作。
3. **大字大按钮**：正文 ≥16px，数字统计 32–40px；触控热区 ≥50px。
4. **数据即界面**：工作台首页先用统计卡回答「今天怎么样」，再给明细列表。

---

## 一、三套主题（Token）

使用方式：整套复制对应主题的 `:root` 块替换模板里的变量，组件样式不改。

### 1. ocean-dark（暗色炫酷，默认）

深海军蓝底 + 霓虹青紫渐变 + 玻璃拟态卡片。适合工具型、效率型、个人仪表盘。

```css
:root {
  --bg: #0B1220;
  --bg-soft: #101A2C;
  --surface: rgba(255, 255, 255, 0.06);      /* 玻璃卡 */
  --surface-solid: #131C2E;
  --border: rgba(255, 255, 255, 0.10);
  --text: #E6EDF7;
  --text-2: #94A3B8;
  --text-3: #64748B;
  --primary: #22D3EE;                         /* 霓虹青 */
  --secondary: #818CF8;                       /* 靛紫 */
  --accent: linear-gradient(135deg, #22D3EE 0%, #818CF8 100%);
  --success: #34D399;
  --warning: #FBBF24;
  --danger: #F87171;
  --glow: 0 0 24px rgba(34, 211, 238, 0.35);  /* 主按钮霓虹光晕 */
  --shadow: 0 8px 32px rgba(0, 0, 0, 0.45);
  --radius-s: 12px; --radius-m: 16px; --radius-l: 24px;
  --blur: saturate(160%) blur(18px);          /* backdrop-filter */
}
```

暗色专属规则：卡片用 `background: var(--surface)` + `backdrop-filter: var(--blur)` + `border: 1px solid var(--border)`；主按钮可用 `background: var(--accent)` + `box-shadow: var(--glow)`；正文避免纯白 `#FFFFFF`，用 `var(--text)`。

### 2. light-fresh（清爽明亮）

白底浅灰 + 品牌蓝 + 柔和投影。适合办公、清单、通用后台。

```css
:root {
  --bg: #F6F8FB;
  --bg-soft: #EDF1F7;
  --surface: #FFFFFF;
  --surface-solid: #FFFFFF;
  --border: #E2E8F0;
  --text: #0F172A;
  --text-2: #64748B;
  --text-3: #94A3B8;
  --primary: #2563EB;
  --secondary: #0EA5E9;
  --accent: linear-gradient(135deg, #2563EB 0%, #0EA5E9 100%);
  --success: #059669;
  --warning: #D97706;
  --danger: #DC2626;
  --glow: none;
  --shadow: 0 2px 8px rgba(15, 23, 42, 0.06);
  --shadow-lift: 0 8px 24px rgba(15, 23, 42, 0.10);
  --radius-s: 12px; --radius-m: 16px; --radius-l: 24px;
  --blur: none;
}
```

亮色专属规则：卡片用实色 `var(--surface)` + `box-shadow: var(--shadow)`；主按钮纯色 `var(--primary)` 即可，不用渐变光晕。

### 3. warm-family（暖色活泼·育儿版）

奶油底 + 橙珊瑚 + 大圆角 + 贴纸感描边。给孩子/家庭用：奖励打卡、习惯养成、家庭记事。

```css
:root {
  --bg: #FFF7ED;
  --bg-soft: #FFEDD5;
  --surface: #FFFFFF;
  --surface-solid: #FFFFFF;
  --border: #FED7AA;
  --text: #431407;
  --text-2: #9A3412;
  --text-3: #C2755A;
  --primary: #F97316;                          /* 橙 */
  --secondary: #FB7185;                        /* 珊瑚 */
  --accent: linear-gradient(135deg, #F97316 0%, #FB7185 100%);
  --success: #10B981;
  --warning: #F59E0B;
  --danger: #EF4444;
  --glow: none;
  --sticker: 0 4px 0 rgba(154, 52, 18, 0.18);  /* 贴纸硬阴影 */
  --shadow: 0 4px 0 rgba(154, 52, 18, 0.18);
  --radius-s: 16px; --radius-m: 20px; --radius-l: 28px;
  --blur: none;
}
```

育儿版专属规则：圆角整体加大一档；主按钮高度 ≥56px、字号 ≥18px；统计卡可加 2px 实色描边（`border: 2px solid var(--border)`）+ 贴纸阴影 `var(--sticker)` 制造手绘感；成功反馈用大号 SVG 对勾 + 轻微弹跳动画（`transform: scale` 关键帧，200ms）。

---

## 二、布局骨架

结构（模板 assets/templates/ipad-meta.html 已实现，直接用）：

```
.app            flex column, height 100dvh, 全屏固定
├── .app-header 高 56px：页面标题（左）+ 图标按钮（右，≥50px 热区）
├── .app-main   flex 1, overflow-y auto, 内容列 max-width 720px 居中,
│               padding-bottom = env(safe-area-inset-bottom) + tabbar 高 + 20px
└── .tabbar     fixed 底部：3–5 个 tab（内联 SVG 图标 24px + 11–12px 标签），
                高 64px + 安全区，active 用 var(--primary)
```

- 安全区：`.app` 四周 `padding: env(safe-area-inset-*)`；tabbar `padding-bottom: env(safe-area-inset-bottom)`。刘海屏/底部横条不遮挡。
- 多页面 = 单文件内「页面段」切换：每个 tab 对应一个 `<section class="page">`，切换时改 `display`，配 150ms 透明度过渡。不引入路由库。
- 横屏（iPad Landscape）：内容列仍限 720px；tabbar 可保持底部（简化，不强制迁侧栏）。

## 三、七类组件规格

所有组件高度、热区均已按触控调好，单位 px。颜色只许用 token。

### 1. 导航（tabbar / 头部）

- tabbar：见布局骨架；tab 热区 ≥64×64（图标+标签整体可点），active 图标和文字 `var(--primary)`，未激活 `var(--text-2)`。
- 头部图标按钮：44×44 视觉 + padding 撑到 50×50 热区；危险入口（清空数据）不放头部，放进设置页。

### 2. 卡片（统计卡 / 内容卡）

```css
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-m);
  padding: 16px;
  margin-bottom: 12px;
  box-shadow: var(--shadow);
}
.stat-card .stat-value { font-size: 36px; font-weight: 700; line-height: 1.1; }
.stat-card .stat-label { font-size: 13px; color: var(--text-2); }
```

- 统计卡网格：`display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px;`
- 首页统计卡内容：大数字（今日次数/完成率）+ 小标签 + 趋势箭头（内联 SVG，涨 `--success` 跌 `--danger`）。

### 3. 列表行

```css
.row {
  display: flex; align-items: center; gap: 12px;
  min-height: 64px; padding: 10px 14px;
  background: var(--surface); border-bottom: 1px solid var(--border);
}
.row-icon { width: 40px; height: 40px; flex: none; }       /* 圆底 + 内联 SVG */
.row-title { font-size: 16px; color: var(--text); }
.row-sub { font-size: 13px; color: var(--text-2); }
```

- 行整体可点（热区即 64px 高整行）；行内操作按钮（完成/删除）≥50px 热区右对齐。
- 删除入口不做滑动（触屏滑动易误触），用行内按钮 + 确认弹层。
- 空状态：居中一个大号内联 SVG（80px）+ 一句话 + 「添加第一条」主按钮。

### 4. 按钮

```css
.btn {
  min-height: 52px; min-width: 52px; padding: 0 24px;
  border-radius: var(--radius-m); border: none;
  font-size: 17px; font-weight: 600;
  display: inline-flex; align-items: center; justify-content: center; gap: 8px;
}
.btn-primary { background: var(--primary); color: #fff; box-shadow: var(--glow); }
/* ocean-dark 可用 background: var(--accent) 渐变 */
.btn-secondary { background: transparent; color: var(--primary); border: 1.5px solid var(--primary); }
.btn-danger { background: var(--danger); color: #fff; }
.btn-ghost { background: transparent; color: var(--text-2); }
```

- 主操作每屏只出现一个主按钮；表单提交用固定底部主按钮（宽 = 内容列宽）。
- warm-family 主题：`min-height: 56px; font-size: 18px; box-shadow: var(--sticker)`，按下时 `transform: translateY(2px)`（贴纸按压感）。

### 5. 表单输入

```css
.field { margin-bottom: 16px; }
.field-label { display: block; font-size: 14px; color: var(--text-2); margin-bottom: 6px; }
.field-input, .field-select {
  width: 100%; min-height: 48px; padding: 10px 14px;
  font-size: 16px; color: var(--text);
  background: var(--bg-soft); border: 1.5px solid var(--border);
  border-radius: var(--radius-s);
}
.field-input:focus { outline: none; border-color: var(--primary); }
```

- 类型：文本（`type="text"`）、数字（`type="number"`，配 stepper ±按钮各 ≥50px）、日期（`type="date"`，系统控件）、枚举（分段选择 segmented：横向按钮组，每段 ≥48px 高）、开关（自定义 toggle，轨道 52×32，可点区整体）。
- 校验失败：输入框 `border-color: var(--danger)` + 下方 13px 错误文案，不用 alert。
- 录入入口：右上「+」或底部主按钮 → bottom-sheet 弹出表单，不跳页。

### 6. 弹层与反馈（modal / sheet / toast）

```css
.sheet {
  position: fixed; left: 0; right: 0; bottom: 0;
  padding: 20px 20px calc(env(safe-area-inset-bottom) + 20px);
  background: var(--surface-solid); border-radius: var(--radius-l) var(--radius-l) 0 0;
  transform: translateY(100%); transition: transform 220ms ease;
}
.sheet.open { transform: translateY(0); }
.sheet-mask { position: fixed; inset: 0; background: rgba(0,0,0,0.45); opacity: 0; transition: opacity 220ms; }
.modal-center { position: fixed; left: 50%; top: 50%; transform: translate(-50%,-50%); width: min(340px, 86vw);
  background: var(--surface-solid); border-radius: var(--radius-l); padding: 24px; }
.toast {
  position: fixed; top: calc(env(safe-area-inset-top) + 16px); left: 50%; transform: translateX(-50%);
  background: var(--surface-solid); color: var(--text); border: 1px solid var(--border);
  border-radius: 999px; padding: 10px 22px; font-size: 14px;
  opacity: 0; transition: opacity 200ms; z-index: 60;
}
.toast.show { opacity: 1; }
```

- **破坏性操作（删除/清空）必须走确认 modal**：标题 + 影响说明 + 「取消」ghost + 「确认」danger。
- toast 只用于结果提示（已保存/已删除），2s 自动消失，不堆叠。
- sheet 打开时 `touchmove` 穿透要阻止（mask 上 `preventDefault`）。

### 7. 数据可视化（纯 SVG/CSS，无图表库）

- **进度环**：内联 SVG `circle` r=45、`stroke-dasharray = 周长`、`stroke-dashoffset = 周长 × (1 - 比例)`，中心放百分比文字；颜色按语义（完成率用 `--success`）。
- **柱状条**：`div` 高度百分比 + `border-radius` 顶端圆角，7 列（近 7 天），当前列用 `var(--primary)` 其余 `var(--text-3)` 40% 透明度。
- **趋势折线**：SVG `polyline`，点坐标按数据线性映射，宽 100% 高 120px；不确定的美化就不做，先保证数据正确。
- 所有图表下配图例行（13px、`--text-2`），数字标签 ≥12px。

---

## 四、交互规范

1. **按压反馈**：可点元素统一 `:active { transform: scale(0.96); opacity: 0.85; }`，过渡 150ms；按钮加 `transition: transform .15s, opacity .15s`。
2. **防抖**：输入类自动保存 debounce 300ms；统计重算随保存一起做。
3. **确认**：删除、清空、重置必须确认；普通编辑直接保存 + toast。
4. **加载**：数据量小（<500 条）同步渲染即可；渲染前先清空容器，避免叠加。
5. **无障碍**：图标按钮带 `aria-label`；文字与背景对比度 ≥4.5:1（三套主题的 token 组合已达标，不要改着改着把 `--text-3` 用到正文上）。
6. **禁用缩放**：viewport `user-scalable=no` + CSS `touch-action: manipulation`（已在模板里）；双击放大和长按选择都要关（`-webkit-user-select: none; -webkit-touch-callout: none`，输入框除外）。
7. **字体栈**：`-apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif`（模板已带），不引入网络字体。
