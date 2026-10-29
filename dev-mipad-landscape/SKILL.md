---
name: dev-mipad-landscape
version: 1.0.0
description: "小米平板横屏应用适配（uni-app Vue3）。当用户需要创建/适配小米平板横屏应用、平板三栏布局、uni-app 平板大屏适配、横屏锁定、rpx 大屏基准重定义时使用。提供 rpx 基准重定义、横屏锁定、全局居中约束、三栏布局、断点系统、屏幕旋转监听、安全区适配的完整端到端方案与可复制代码模板。首次使用时必须先确认需求（应用类型、目标设备、布局结构）与是否有原型图/设计稿，确认后再开始搭建。"
metadata:
  requires:
    files: []
---

# 小米平板横屏应用适配 Skill（uni-app Vue3）

## 概述

本 Skill 基于一个真实落地工程（全家签到 APP，适配小米平板 5 横屏）提炼而成，提供在 **uni-app (Vue3 + Vite)** 中创建「小米平板横屏应用」的完整端到端方案。

**适用场景**：
- 从零创建面向小米平板（横屏）的 uni-app 应用
- 给现有手机竖屏 uni-app 项目增加平板横屏专版
- 需要「手机竖屏 + 平板横屏三栏」自适应降级
- 需要 `layout-sw600dp-land` 等效断点的响应式布局

**核心思路**：不是简单放大手机界面，而是用「rpx 基准重定义 + 全局居中约束 + 横屏三栏布局」三管齐下，让同一套代码在手机上竖屏显示、在小米平板上自动切换为三栏横屏。

---

## 首次使用流程（先确认需求，再动手）

> **重要原则：首次被触发时，不要直接开始搭代码。必须先与用户确认需求，有原型图则先读懂原型，再进入实施步骤。** 否则容易因布局结构、配色、栏位分配与预期不符而返工。

### 第一步：确认基础需求

逐项向用户确认（推荐用提问卡片一次问清，避免多轮来回）：

| 需求项 | 选项 |
|--------|------|
| 应用类型 | 纯平板横屏专用 / 手机竖屏 + 平板横屏自适应 |
| 目标设备 | 小米平板 5（2560×1600）/ 其他尺寸平板 |
| 屏幕方向 | 仅横屏 / 横竖屏自适应 |
| 布局结构 | 三栏（左导航+中内容+右详情）/ 两栏（主从）/ 单栏 |
| 技术栈 | uni-app Vue3（默认）/ 是否需要 H5 + App 双端 |
| 导航形态 | 自定义左栏导航 / 底部 TabBar / 顶部导航 |

### 第二步：确认是否有原型图 / 设计稿

**必须主动询问**（这是本 Skill 的硬性前置条件）：

- 是否有原型图 / 设计稿？来源可能是 Figma、蓝湖、Axure、即时设计、截图、手绘稿，或指定参考某款 APP。
- **有原型图**：先读取 / 查看原型，从中提取——
  - 整体配色与主题（主色、背景色、强调色）
  - 布局结构（几栏、每栏放什么内容）
  - 关键页面清单与页面间的导航关系
  - 栏位宽度比例、间距、圆角、字体层级
  - 特殊交互（收起/展开、弹窗、Tab 切换）
  提取完成后向用户复述一遍设计要点，得到确认再继续。
- **无原型图**：基于功能描述设计默认方案，先输出「文字版布局说明」（每栏放什么、配色建议、页面清单）供用户确认，确认后再进入实施。

### 第三步：输出需求确认清单，得到确认后才执行

动手前，用一份清单向用户收口：

```
✅ 布局方案：三栏（左导航 220px + 中内容 + 右详情 220px + 底部通栏 70px）
✅ 配色主题：主色 ____ / 背景 ____ / 强调 ____
✅ 屏幕方向：仅横屏（锁 landscape）
✅ 关键页面：1.首页 2.xxx 3.xxx ...
✅ 降级策略：窄窗(<680px) 自动降级为单栏竖屏
```

用户确认（或明确说「就按这个来」）后，再进入下方「二、实施步骤」开始搭建。

> 补充：若用户已明确表达「不需要确认，直接做」，可以跳过提问直接实施；但只要需求存在任何歧义（布局结构、配色、是否有原型图未说明），都先问清楚再动手。

---

## 一、核心适配策略（6 大支柱）

| # | 支柱 | 作用 | 关键位置 |
|---|------|------|---------|
| 1 | rpx 基准重定义 | 让 `750rpx = 960px`，手机设计稿在平板上按比例适配、不溢出 | `pages.json` → `globalStyle` |
| 2 | 横屏锁定 | 只允许横屏，禁止旋转回竖屏 | `manifest.json` → `screenOrientation` |
| 3 | 全局居中约束 | body/#app 限制 `max-width:960px` 居中；三栏页全屏覆盖 | `uni.scss` |
| 4 | 横屏三栏布局 | 左导航 + 中内容 + 右详情 + 底部通栏 | `pages/landscape` + `components/layout` |
| 5 | 自动路由切换 | 启动/显示时检测横屏 → 自动 reLaunch 到三栏页 | `App.vue` |
| 6 | 断点 + 旋转监听 | 窗口变化实时判断断点、竖屏锁回横屏 | `utils/pad-layout-helper.js` |

---

## 二、实施步骤（Step by Step）

### Step 1 — 初始化项目（若从零开始）

```bash
# 使用 HBuilderX 或 CLI 创建 uni-app (Vue3) 项目
npx degit dcloudio/uni-preset-vue#vite my-pad-app
cd my-pad-app
npm install
```

依赖版本要点（参考已落地工程 `package.json`）：
- `@dcloudio/uni-app` / `uni-components` / `uni-h5` 同一版本（如 `3.0.0-alpha-*`）
- `vue ^3.4.0`、`vite ^5.2.0`、`sass ^1.77.0`、`cross-env`

`vite.config.js` 关键点（H5 构建产物目录）：
```js
import { defineConfig } from 'vite'
import uni from '@dcloudio/vite-plugin-uni'
export default defineConfig({
  plugins: [uni()],
  server: { host: '0.0.0.0', port: 5173 },
  build: { outDir: 'unpackage/dist/build/h5' }
})
```

### Step 2 — 配置 rpx 基准（pages.json）

在 `pages.json` 的 `globalStyle` 中加三行，把 rpx 的计算基准从默认 750px 改为 960px：

```json
"globalStyle": {
  "rpxCalcMaxDeviceWidth": 960,
  "rpxCalcBaseDeviceWidth": 960,
  "rpxCalcIncludeWidth": 750
}
```

**原理**：默认 `750rpx = 屏宽`。平板横屏逻辑宽约 960dp，若不重定义，`1rpx` 会变得很大导致界面被撑爆。设为 960 后 `750rpx` 恰好对应 960px，手机上的设计稿（750 设计稿）在平板上等比例适配，无需重写尺寸。

### Step 3 — 锁定横屏（manifest.json）

```json
"app-plus": {
  "screenOrientation": [ "landscape-primary", "landscape-secondary" ]
}
```

> 注意：`screenOrientation` 仅 App 端（真机/打包）生效；H5 预览不支持锁定，需靠下方 CSS + JS 兜底。

### Step 4 — 全局居中约束（uni.scss）

在 `uni.scss` 顶部追加以下平板适配样式：

```scss
/* 页面容器：居中于 960px（与 rpx 基准一致） */
html { display: flex; justify-content: center; }
body { max-width: 960px; width: 100%; min-height: 100vh; }
uni-app, #app { max-width: 960px; width: 100%; }

/* 三栏布局页面：全屏覆盖，不受 max-width 限制 */
.pad-land-page,
body.pad-land-page,
.pad-land-page #app {
  max-width: 100% !important;
  width: 100vw !important;
}

/* 顶部导航栏居中 */
uni-page-head, .uni-page-head {
  max-width: 960px !important;
  left: 50% !important;
  transform: translateX(-50%) !important;
}

/* 三栏布局页：隐藏导航栏与 TabBar */
.pad-land-page ~ uni-page-head,
.pad-land-page .uni-page-head { display: none !important; }
.pad-land-page ~ .uni-tabbar,
.pad-land-page .uni-tabbar { display: none !important; }

/* 三栏布局页本体：全屏固定、无滚动 */
.pad-land-page {
  width: 100vw; height: 100vh; height: 100dvh;
  overflow: hidden; position: fixed; inset: 0; z-index: 100;
}

/* 安全区适配 */
.safe-bottom {
  padding-bottom: constant(safe-area-inset-bottom);
  padding-bottom: env(safe-area-inset-bottom);
}

/* 触摸热区 ≥ 60dp（平板点击更舒适） */
.touch-target { min-width: 60px; min-height: 60px; display: flex; align-items: center; justify-content: center; }

/* sw600dp-land 等效断点：横屏且宽 >= 600px */
@media screen and (min-width: 600px) and (orientation: landscape) {
  .tablet-land-only { display: block !important; }
  .phone-only { display: none !important; }
}

/* 底部 TabBar：居中悬浮卡片（平板风格） */
.uni-tabbar-bottom .uni-tabbar {
  position: fixed !important;
  left: 50% !important; right: auto !important;
  transform: translateX(-50%) !important;
  max-width: 960px !important; width: 100% !important;
  border-radius: 24rpx 24rpx 0 0 !important;
  box-shadow: 0 -8rpx 32rpx rgba(0,0,0,0.08) !important;
}
```

### Step 5 — 复制工具函数

将本 Skill `assets/` 目录下的两个文件复制到项目 `utils/` 目录：

```bash
cp assets/pad-land-helper.js 项目/utils/pad-land-helper.js
cp assets/pad-layout-helper.js 项目/utils/pad-layout-helper.js
```

- `pad-land-helper.js`：横屏判断、安全区、旋转监听
- `pad-layout-helper.js`：断点常量、窗口状态 `useWindowState`、断点判断 `useBreakpoint`、三栏状态 `useLayoutState`

### Step 6 — 创建横屏三栏页面

**6.1 注册页面**（pages.json），设为自定义导航栏：

```json
{
  "path": "pages/landscape/landscape",
  "style": {
    "navigationBarTitleText": "应用名",
    "navigationStyle": "custom",
    "app-plus": { "titleNView": false }
  }
}
```

**6.2 页面容器** `pages/landscape/landscape.vue`：

```vue
<template>
  <view class="pad-land-page">
    <PadLandLayout />
  </view>
</template>

<script setup>
import { onMounted } from 'vue'
import PadLandLayout from '@/components/layout/PadLandLayout.vue'
onMounted(() => {
  try { uni.hideTabBar({ animation: false }) } catch {}
})
</script>

<style scoped>
.pad-land-page {
  width: 100vw; height: 100vh; height: 100dvh;
  overflow: hidden;
  padding-top: env(safe-area-inset-top, 0px);
  padding-bottom: env(safe-area-inset-bottom, 0px);
  box-sizing: border-box;
}
</style>
```

**6.3 三栏骨架** `components/layout/PadLandLayout.vue`：

```vue
<template>
  <view class="pad-land">
    <view class="pad-land-body">
      <!-- 左栏：常驻导航 -->
      <view class="left-nav" :style="{ width: leftWidth + 'px', minWidth: leftWidth + 'px' }">
        <LeftNav @toggle="toggleLeft" />
      </view>
      <!-- 中栏：核心内容区（flex:1，独立滚动） -->
      <view class="middle-col">
        <slot />
      </view>
      <!-- 右栏：详情面板（可收起） -->
      <view v-if="!rightCollapsed" class="right-panel" :style="{ width: rightWidth + 'px' }">
        <RightPanel />
      </view>
    </view>
    <!-- 底部通栏 -->
    <view class="bottom-bar" v-if="!rightCollapsed">
      <BottomBar />
    </view>
  </view>
</template>

<script setup>
import { useLayoutState } from '@/utils/pad-layout-helper'
import LeftNav from './LeftNav.vue'
import RightPanel from './RightPanel.vue'
import BottomBar from './BottomBar.vue'
const { leftCollapsed, rightCollapsed, leftWidth, rightWidth, toggleLeft, toggleRight } = useLayoutState()
</script>

<style scoped>
.pad-land { display: flex; flex-direction: column; width: 100%; height: 100vh; height: 100dvh; overflow: hidden; }
.pad-land-body { display: flex; flex: 1; overflow: hidden; }
.left-nav { flex-shrink: 0; height: 100%; transition: width 0.3s cubic-bezier(0.25,0.46,0.45,0.94); border-right: 1px solid #eee; }
.middle-col { flex: 1; min-width: 0; height: 100%; overflow-y: auto; overflow-x: hidden; }
.right-panel { flex-shrink: 0; height: 100%; overflow-y: auto; border-left: 1px solid #eee; transition: width 0.3s; }
.bottom-bar { flex-shrink: 0; height: 70px; border-top: 1px solid #eee; }

/* 窄窗降级：竖屏/窄窗单栏 */
@media screen and (max-width: 680px) {
  .pad-land-body { flex-direction: column; }
  .left-nav { width: 100% !important; min-width: 100% !important; height: auto !important; }
  .right-panel, .bottom-bar { display: none !important; }
}
</style>
```

### Step 7 — App.vue 自动路由切换

```vue
<script setup>
import { onLaunch, onShow } from '@dcloudio/uni-app'
import { onMounted } from 'vue'
import { onRotateWatch } from '@/utils/pad-land-helper'

onLaunch(() => tryRedirectToLandscape(true))
onShow(() => tryRedirectToLandscape(false))

onMounted(() => {
  onRotateWatch((res) => {
    // 旋转为竖屏时，锁回横屏（仅真机生效）
    if (!res.landscape) {
      try { plus.screen.lockOrientation('landscape-primary') } catch {}
    }
    // 进入横屏时切到三栏
    if (res.landscape && res.w >= 680) tryRedirectToLandscape(false)
  })
})

function tryRedirectToLandscape(force = false) {
  try {
    const info = uni.getWindowInfo()
    if (info.windowWidth >= 680 && info.windowWidth > info.windowHeight) {
      if (!force) {
        const pages = getCurrentPages()
        const cur = pages[pages.length - 1]
        if (cur && cur.route === 'pages/landscape/landscape') return
      }
      uni.reLaunch({ url: '/pages/landscape/landscape' })
    }
  } catch {}
}
</script>
```

### Step 8 — index.html viewport

确保 `viewport-fit=cover` 以支持安全区：

```html
<meta name="viewport" content="width=device-width, user-scalable=no, initial-scale=1.0, maximum-scale=1.0, minimum-scale=1.0, viewport-fit=cover" />
```

---

## 三、关键数值速查表

| 项目 | 数值 | 说明 |
|------|------|------|
| 小米平板5 物理分辨率 | 2560×1600 | 16:10 横屏 |
| 逻辑宽度（横屏） | 约 853~960dp | 用于断点 |
| rpx 基准 | 960px | `750rpx = 960px` |
| 三栏布局断点 | ≥ 853dp | `tablet-land` |
| 自动跳转阈值 | 宽 ≥ 680dp 且横屏 | App.vue 判断 |
| 左栏宽度 | 220px | 收起后 72px |
| 右栏宽度 | 220px | 可收起为 0 |
| 底部通栏高度 | 70px | — |
| 触摸热区 | ≥ 60px (60dp) | 平板友好 |

---

## 四、注意事项 / 踩坑清单

1. **rpx 三兄弟必须同时设**：`rpxCalcBaseDeviceWidth` / `rpxCalcMaxDeviceWidth` / `rpxCalcIncludeWidth`，缺一个会导致尺寸错乱。
2. **`screenOrientation` 仅 App 生效**：H5 预览靠 CSS `max-width` + JS 锁屏兜底，不能强锁。
3. **三栏页必须 `navigationStyle: custom`**，否则顶部会留一条原生导航栏。
4. **三栏页要主动 `uni.hideTabBar`**：自定义导航接管后，原生 TabBar 会遮挡底部通栏。
5. **`100dvh` 优先于 `100vh`**：`dvh` 能正确处理移动端地址栏/手势条引起的视口变化，`vh` 作为回退。
6. **中栏必须 `min-width: 0`**：flex 子项默认 `min-width:auto`，内容过宽会撑破三栏，务必归零。
7. **安全区用 `env()` 而非写死**：小米平板底部手势横条、顶部状态栏都需要 `env(safe-area-inset-*)` 避让。
8. **`getWindowInfo` 需 try/catch**：H5 低版本或非 App 环境可能抛错。
9. **路由跳转用 `reLaunch` 而非 `navigateTo`**：三栏页是根级布局，避免页面栈堆积。
10. **断点要同时判断宽度和方向**：`windowWidth > windowHeight` 才算横屏，单纯看宽度会误判分屏/竖屏。

---

## 五、验证清单

完成后逐项验证：

- [ ] 手机竖屏：正常单栏，`body` 居中不溢出
- [ ] 小米平板横屏：自动进入三栏布局
- [ ] 旋转到竖屏：自动锁回横屏（真机）
- [ ] 左栏收起/展开：宽度过渡平滑（72px ↔ 220px）
- [ ] 右栏收起：中栏自动占满
- [ ] 中栏独立滚动，左右栏不联动
- [ ] 底部手势条区域内容不被遮挡（安全区）
- [ ] 所有可点击元素热区 ≥ 60px
- [ ] 窄窗（<680px）降级为单栏竖屏
- [ ] 750rpx 元素在平板上约 960px，不畸形放大

---

## 六、模板文件

| 文件 | 用途 |
|------|------|
| `assets/pad-land-helper.js` | 横屏判断、安全区、旋转监听工具 |
| `assets/pad-layout-helper.js` | 断点常量、窗口状态、三栏布局状态工具 |

按需调整断点数值与 `LAYOUT` 尺寸后直接复制到项目 `utils/` 目录使用。
