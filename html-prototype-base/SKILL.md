---
name: html-prototype-base
description: "企业管理系统 HTML 原型的单一技能：通用基座（用途选择器、六种菜单布局、通用页面模式、CDN 依赖规范）+ 四个业务象限的专化页面模式。01-design 生成架构设计文档页（系统设计、架构说明、业务场景、领域建模、状态机、表结构）；02-manage 生成运营后台页（增删改查、系统配置、流程向导、详情、报表，蓝色表格驱动）；03-client 生成企业门户/会员中心页（合同、履约、单据、结算、待办、企业资料，翠绿卡片式）；04-mobile 生成手机端触控页（底部 Tab、时间线、卡片列表，奶油暖色）。当用户说「做个管理后台」「运营后台增删改查」「系统配置页」「会员中心」「客户端门户」「手机端页面」「架构设计文档」「状态机文档」「表结构文档」「HTML 原型」时使用。触发词：HTML 原型、管理系统原型、运营后台、管理后台、增删改查、系统配置、报表页、会员中心、企业门户、客户端门户、客户前台、履约中心、单据中心、手机端页面、移动端页面、底部 Tab、架构设计文档、系统设计文档、架构图说明、状态机文档、表结构文档、领域建模。不适用于：B2B 产业互联网门户（走 html-b2b-portal）、需要构建工具或真实后端的项目。"
description_zh: 企业管理系统 HTML 原型单一技能：通用基座（用途、六种菜单布局、通用页面模式）+ 四象限（架构设计文档 / 运营后台 / 会员中心 / 手机端）。
description_en: "Enterprise HTML prototype skill: a generic shell base (purpose presets, six navigation layouts, shared page patterns) plus four quadrant playbooks — design docs, admin backend, member portal, and mobile pages."
version: 0.1.0
author: hasWhere
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# html-prototype-base — HTML 原型基座（含四象限）

> **定位**: 企业管理系统 HTML 原型的**单一技能**。基座给出不绑定业务的框架（用途、布局、CDN 依赖、通用页面模式），四个象限给出各自的专化页面模式。
> **核心链路**: 象限路由 → 用途/主题色 → 菜单布局 → 页面类型 → 生成自包含 HTML。
> **合并说明**: 原 `html-architecture-design`、`html-manage-pages`、`html-client-pages`、`html-mobile-pages` 已并入本技能，内容分别落在 `references/01-design-architecture.md`、`02-manage-pages.md`、`03-client-pages.md`、`04-mobile-pages.md`。不要再按旧名寻找或新建独立技能。

## 何时使用 / 不适用

| 场景 | 使用 |
|------|------|
| 运营后台、系统配置、CRM/合同/订单管理等管理端页面 | 本技能 → `02-manage-pages.md` |
| 企业会员中心、客户门户、个人中心、订单查询 | 本技能 → `03-client-pages.md` |
| 手机端 / 平板页面、底部 Tab、触控交互 | 本技能 → `04-mobile-pages.md` |
| 架构设计、系统设计、状态机、表结构、路线图等文档页 | 本技能 → `01-design-architecture.md` |
| 不属于以上任何象限的全新管理系统 | 本技能，只用基座（Layout A–F） |
| B2B 产业互联网门户、大宗商品交易平台 | `html-b2b-portal` |
| 需要 npm / 打包 / 真实接口的系统 | 不适用（本技能只产出静态原型） |

## Core Rules

1. **Zero build tools** — No package.json, no bundler, no npm. Everything loads from CDN.
2. **Chinese-first** — Always use `lang="zh-CN"`, Chinese labels and content.
3. **Static mock data** — All data is hardcoded in HTML. No API calls, no data files.
4. **Self-contained pages** — Every `.html` file is an independent, fully renderable page.
5. **iframe shell model** — `index.html` acts as the shell with nav and an `<iframe>` content area (手机端除外).

---

## Step 1: 确定象限与用途

先用「象限路由」落到 `references/`，再用用途预设定主题色。

### 象限路由

| 象限 | 目录 | 主题色 | 列表形态 | 导航 | 参考文件 |
|------|------|--------|----------|------|----------|
| `01-design` | `01-design/` | 蓝/绿/紫/橙四色分层 | 文档表格 | Layout A（可折叠分组） | `references/01-design-architecture.md` |
| `02-manage` | `02-manage/` | `#3B82F6` 蓝 | 数据表格 | Layout A / C | `references/02-manage-pages.md` |
| `03-client` | `03-client/` | `#059669` 翠绿 | 卡片网格 + Chips | Layout A(w-60) / D | `references/03-client-pages.md` |
| `04-mobile` | `04-mobile/` | `#d97706` 琥珀 + `#f8f6f2` 底色 | 触控卡片 | Layout F | `references/04-mobile-pages.md` |
| 无象限 | 自定义 | 按下方用途表 | 按页面类型 | Layout A–F | 本文件 + `references/layouts.md` |

### 用途预设表

| 用途 | 代号 | 主题色 | 导航推荐 | 组件密度 | 典型页面类型 | 典型场景 |
|------|------|--------|----------|----------|-------------|----------|
| 管理后台 | `admin` | `#3B82F6` 蓝 | Layout A / C | 高（表格密集） | List/CRUD, Dashboard, Settings | 运营管理、合同管理、系统配置 |
| 企业门户 | `portal` | `#1E3A5F` 深蓝 | Layout B / A | 中（卡片+图表） | Dashboard, Portal | 企业首页、工作台、数据概览 |
| 会员中心 | `member` | `#059669` 翠绿 | Layout A / D | 中（卡片+表单） | List, Process, Settings | 个人中心、订单查询、账号设置 |
| 客户端 | `client` | `#7C3AED` 紫 | Layout A / C | 中高（流程+表单） | List, Process, Detail | 客户工作台、履约跟踪、单据管理 |
| 手机端 | `mobile` | `#d97706` 琥珀 | Layout F | 低（大触控） | Mobile Cards, Mobile List | 移动办公、审批、查询 |
| 数据大屏 | `screen` | `#0F172A` 暗底 | 无导航（全屏） | 极高（图表密集） | Big Screen | 监控中心、数据驾驶舱 |

### 用途配置预设

生成 shell 时，按用途替换 tailwind.config 和 CSS 变量：

**admin**:
```js
tailwind.config = { theme: { extend: { colors: {
    primary: '#3B82F6', secondary: '#64748B', accent: '#10B981'
}}}}
```

**portal**:
```js
tailwind.config = { theme: { extend: { colors: {
    primary: '#1E3A5F', secondary: '#FF6A00', accent: '#10B981'
}}}}
```

**member**:
```js
tailwind.config = { theme: { extend: { colors: {
    primary: '#059669', secondary: '#0EA5E9', accent: '#F59E0B'
}}}}
```

**client**:
```js
tailwind.config = { theme: { extend: { colors: {
    primary: '#7C3AED', secondary: '#EC4899', accent: '#06B6D4'
}}}}
```

**mobile**:
```js
tailwind.config = { theme: { extend: { colors: {
    primary: '#d97706', secondary: '#059669', accent: '#3B82F6'
}}}}
```

**screen**:
```js
tailwind.config = { theme: { extend: { colors: {
    primary: '#0EA5E9', secondary: '#8B5CF6', accent: '#10B981',
    dark: { 50:'#F8FAFC', 900:'#0F172A', 950:'#020617' }
}}}}
```

---

## Step 2: 选择菜单布局

| 布局 | 形态 | 适用用途 | 信息层级 |
|------|------|----------|----------|
| A | 经典左侧边栏（最通用） | 管理后台、会员中心、客户端、文档系统 | 2 级（分组 + 菜单项） |
| B | 顶部水平导航 | 企业门户、营销型工作台 | 1 级（顶部菜单直达） |
| C | 侧边栏 + 顶部二级标签 | 复杂管理系统、客户端 | 3 级（模块 + 子页 + 页内） |
| D | 折叠图标侧边栏（hover 展开） | 会员中心、现代感后台 | 1-2 级 |
| E | 双栏树形导航 | 文件/分类/多层级设置 | 3 级+ |
| F | 手机底部 Tab 栏 | 手机端、平板 | 1 级（底部 Tab 直达） |

**六套完整可复制模板（含 ASCII 结构图）见 `references/layouts.md`**，复制后替换主题色、系统名称、菜单项即可。

---

## Step 3: 读取象限专化文档

只读当前任务需要的那个文件，不要一次全读。

| 何时读取 | 文件 | 内容 |
|----------|------|------|
| 做架构/设计/状态机/表结构文档页，或需要先定领域模型 | `references/01-design-architecture.md` | 文档页布局、纯 CSS 图表（流程图/分层图/状态迁移表）、文档类型清单、四色配色、新增步骤 |
| 做运营后台增删改查、系统配置、流程、详情、报表 | `references/02-manage-pages.md` | Shell 导航分组、Type A–D 模板、确认弹窗、按钮配色、postMessage 导航 |
| 做会员中心/客户门户，卡片式列表与履约单据 | `references/03-client-pages.md` | Shell 品牌化、看板、卡片网格、Chips 筛选、履约中心三页、单据中心、与后台差异表 |
| 做手机端/平板页面 | `references/04-mobile-pages.md` | 设计变量、字体、底部 Tab、触控原则、页面类型、样式模块、子页清单 |
| 需要 Layout A–F 完整 HTML | `references/layouts.md` | 六套 shell 模板 |
| 需要列表/看板/流程/设置/大屏的区块代码 | `references/page-patterns.md` | Type 1–5 完整片段 |

---

## Page Boilerplate（子页模板）

每个子页面遵循此结构（mobile 布局去掉外层 padding）：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>页面标题</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script>
        tailwind.config = { theme: { extend: { colors: {
            primary: '#3B82F6', secondary: '#64748B', accent: '#10B981'
        }}}}
    </script>
    <style>
        /* Page-specific styles */
    </style>
</head>
<body class="bg-gray-50">
    <div class="p-6">
        <!-- Page content -->
    </div>
    <script>
        // Page-specific JavaScript
    </script>
</body>
</html>
```

---

## 页面类型速查

| 类型 | 用途 | 区块 |
|------|------|------|
| List/CRUD | 列表、增删改查 | 标题栏 → 统计卡片 → 筛选栏 → 表格 → 分页 |
| Dashboard/Portal | 仪表盘、门户首页 | 问候 → 统计卡片行 → 图表 + 活动 → 快捷操作 |
| Process/Wizard | 流程、向导 | 步骤条 → 指标卡 → 详情区 → 操作按钮 |
| Settings | 设置、配置 | 左标签导航 + 右内容面板 |
| Big Screen | 数据大屏 | 暗底 + 发光卡片 + 图表 |

完整代码见 `references/page-patterns.md`。

**状态标签配色（跨象限通用）:**

| 状态 | Badge classes |
|------|--------------|
| 履约中/合规/正常/完成 | `bg-green-100 text-green-800` |
| 待履约/待处理 | `bg-yellow-100 text-yellow-800` |
| 已作废/不合规/驳回 | `bg-red-100 text-red-800` |
| 已归档/已解决 | `bg-gray-100 text-gray-800` |

---

## Shell 契约（跨象限通用）

### 1. 主内容导航
```javascript
function loadPage(page) {
    document.getElementById('mainFrame').src = page;
    document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active-nav'));
    event.currentTarget.classList.add('active-nav');
}
```

### 2. 子页面 → Shell 通信
子页面通过 `postMessage` 请求 Shell 导航；Shell 侧统一监听：
```javascript
window.parent.postMessage({ type: 'navigate', to: 'relative/path.html', id: 'xxx' }, '*');

window.addEventListener('message', function (e) {
    if (!e.data || !e.data.type) return;
    if (e.data.type === 'navigate') {
        // 外链新开标签，内链换 iframe
        if (/^https?:/.test(e.data.to)) window.open(e.data.to);
        else loadPage(e.data.to);
    }
    if (e.data.type === 'switchTab') switchTab(e.data.tab);   // 仅手机端 shell
});
```

### 3. 分组折叠
```javascript
function toggleGroup(header) {
    const content = header.nextElementSibling;
    content.classList.toggle('collapsed');
    header.querySelector('.collapse-icon')?.classList.toggle('rotated');
}
```

---

## Color Conventions

**默认语义色（跨用途通用）:**

| 角色 | Tailwind Class | Hex |
|------|---------------|-----|
| 主按钮/链接 | `bg-blue-600`, `text-blue-600` | #2563EB |
| 成功标签 | `bg-green-100`, `text-green-800` | - |
| 警告标签 | `bg-yellow-100`, `text-yellow-800` | - |
| 危险标签 | `bg-red-100`, `text-red-800` | - |
| 中性标签 | `bg-gray-100`, `text-gray-800` | - |

**扩展调色板（自定义主题色页面）:**
```js
tailwind.config = {
    theme: { extend: { colors: {
        primary: '#165DFF', success: '#00B42A',
        warning: '#FF7D00', danger: '#F53F3F',
        neutral: { 100:'#F2F3F5', 200:'#E5E6EB', 300:'#C9CDD4', 400:'#86909C', 500:'#4E5969', 600:'#1D2129' }
    }}}
}
```

---

## Module Directory Structure

```
project/
├── index.html              # Shell（优先：按象限分目录后每个象限各有 index.html）
├── 01-design/              # 架构设计文档（architecture/ scenarios/ documents/）
├── 02-manage/              # 运营后台（portal/ contract/ performance/ system/ report/）
├── 03-client/              # 会员中心（dashboard/ contract/ performance/ settlement/ document-center/ tasks/ company/）
├── 04-mobile/              # 手机端（pages/ pages/profile/）
├── module-name/            # 无象限时的通用功能模块
│   ├── list.html
│   ├── detail.html
│   └── form.html
├── common/                 # 跨模块共用页面
├── system/                 # 配置/管理页
├── report/                 # 报表/图表页
└── screen/                 # 大屏页（可选）
```

单象限工程可只用对应目录；多象限工程由总 `index.html` 或各象限 `index.html` 分别承载 Shell。

---

## Key Dependencies (CDN)

| Library | CDN URL | When to Use |
|---------|---------|-------------|
| Tailwind CSS | `https://cdn.tailwindcss.com` | Always required |
| Font Awesome 6.4 | `https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css` | Always required |
| Chart.js 3.9.1 | `https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js` | Charts/dashboards |
| Google Fonts（手机端） | `https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@500;600;700;900&family=Outfit:wght@400;500;600;700&display=swap` | 04-mobile 衬线标题 |

---

## Development Instructions

### 生成新项目流程

1. **选象限** — 查「象限路由」定目录与参考文件；无匹配则只用基座
2. **选用途** — 从「用途预设表」确定代号与主题色，替换 tailwind.config
3. **选布局** — 从 `references/layouts.md` 取 Layout A–F 对应模板，生成 `index.html`
4. **建目录** — 按菜单结构建子目录（见 Module Directory Structure）
5. **生成子页面** — 用 Page Boilerplate 起稿，套用页面类型片段，填 mock 数据
6. **连通导航** — 侧边栏/ Tab 注册入口，需要跨页跳转时用 postMessage 契约

### 生成新页面流程

1. 确定页面类型（List / Dashboard / Process / Settings / Big Screen）
2. 复制 Page Boilerplate 作为骨架
3. 套用 `references/page-patterns.md` 或象限文档中的区块代码
4. 替换主题色（与 shell 保持一致）
5. 如需在已有 shell 中加入口，在 sidebar/nav 中添加菜单项

### 自检清单

- [ ] `lang="zh-CN"`，全部文案中文
- [ ] 直接双击 `index.html` 可渲染，无构建步骤
- [ ] 每个子页可独立打开（不依赖父页状态）
- [ ] 主题色与象限/用途一致，状态标签配色统一
- [ ] 菜单项与文件路径一一对应，无 404
- [ ] 手机端点击区域 ≥ 44px，底部安全区已适配
