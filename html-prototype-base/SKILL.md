---
name: html-prototype-base
description: >-
  通用基座 skill — 企业管理系统 HTML 原型的底层框架、用途选择器、菜单布局选择器与通用页面模式。
  支持按用途（管理后台 / 企业门户 / 会员中心 / 客户端 / 手机端 / 数据大屏）选择预设主题色与组件密度，
  支持按场景选择菜单布局（经典侧边栏 / 顶部导航 / 侧边栏+二级标签 / 折叠图标栏 / 双栏树形 / 手机底部Tab）。
  当需求不属于 html-manage-pages / html-client-pages / html-mobile-pages / html-b2b-portal 任何一个具体象限时使用；
  已有象限 skill 是此基座的特化版本，当需求明确命中某个象限时，优先使用对应象限 skill。
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# html-prototype-base — 通用基座 Skill

> **定位**: 本 skill 是企业管理系统 HTML 原型的**通用基座**，提供不绑定具体业务象限的底层框架。
> **核心能力**: 用途选择 → 菜单布局选择 → 页面模式套用 → 生成自包含 HTML 文件。

## 何时使用本 skill vs 象限 skill

| 场景 | 使用 |
|------|------|
| 新建一个不属于任何已有象限的全新管理系统 | **本 skill** |
| 需要跨象限复用的 shell 模板、色彩规范、页面样板 | **本 skill** |
| 管理端后台（蓝主题、表格驱动） | html-manage-pages |
| 企业客户端门户（绿主题、卡片式） | html-client-pages |
| 手机端页面（暖色、触控） | html-mobile-pages |
| B2B 产业门户 | html-b2b-portal |
| 不确定属于哪个象限 | 先用本 skill 搭建，后续按业务方向迁移到对应象限 |

## Core Rules

1. **Zero build tools** — No package.json, no bundler, no npm. Everything loads from CDN.
2. **Chinese-first** — Always use `lang="zh-CN"`, Chinese labels and content.
3. **Static mock data** — All data is hardcoded in HTML. No API calls, no data files.
4. **Self-contained pages** — Every `.html` file is an independent, fully renderable page.
5. **iframe shell model** — `index.html` acts as the shell with nav and an `<iframe>` content area (手机端除外).

---

## Step 1: 选择用途类型

生成项目前，先确定用途类型。每种用途自带主题色、导航推荐、组件密度等预设。

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

根据用途和信息层级选择布局。以下是 6 种内置布局，每种含完整可复制的 shell 模板。

### Layout A: 经典左侧边栏（最通用）

```
┌─ Header (h-16) ────────────────────────────────┐
│  [Logo] 系统名称              [🔔] [👤 用户名]   │
├─ Sidebar (w-64) ──┬─ Main (flex-1) ──────────────┤
│  分组名称          │                              │
│  ▸ 菜单项1        │   <iframe> 内容区             │
│  ▸ 菜单项2        │                              │
│  分组名称          │                              │
│  ▸ 菜单项3        │                              │
└──────────────────┴──────────────────────────────┘
```

**适用**: 管理后台、会员中心、客户端 | **信息层级**: 2 级（分组 + 菜单项）

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>系统名称</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script>
        tailwind.config = { theme: { extend: { colors: {
            primary: '#3B82F6', secondary: '#64748B', accent: '#10B981'
        }}}}
    </script>
    <style>
        html, body { height: 100%; margin: 0; padding: 0; overflow: hidden; }
        .portal-container { height: calc(100vh - 64px); overflow: hidden; }
        .nav-item:hover { background-color: #EFF6FF; }
        .active-nav { background-color: #DBEAFE; border-left: 4px solid #3B82F6; }
        #mainFrame { width: 100%; height: 100%; border: 0; }
    </style>
</head>
<body class="bg-gray-50">
    <header class="bg-white shadow-sm h-16 flex items-center px-6">
        <div class="flex items-center">
            <i class="fas fa-cube text-primary text-2xl mr-3"></i>
            <h1 class="text-xl font-bold text-gray-800">系统名称</h1>
        </div>
        <div class="ml-auto flex items-center space-x-4">
            <button class="text-gray-600 hover:text-gray-900"><i class="fas fa-bell"></i></button>
            <div class="flex items-center">
                <div class="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-white mr-2">
                    <i class="fas fa-user"></i>
                </div>
                <span class="text-gray-700">用户名</span>
            </div>
        </div>
    </header>
    <div class="flex">
        <aside class="w-64 bg-white shadow-md h-screen sticky top-16 overflow-y-auto">
            <nav class="py-4" id="sidebar-nav">
                <div class="px-4 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">分组名称</div>
                <a href="#" onclick="loadPage('module/page.html')" class="nav-item active-nav flex items-center px-4 py-3 text-gray-700">
                    <i class="fas fa-home mr-3"></i><span>菜单项</span>
                </a>
            </nav>
        </aside>
        <main class="flex-1 p-6 portal-container">
            <iframe id="mainFrame" src="portal/dashboard.html" class="w-full h-full border-0 rounded-lg shadow"></iframe>
        </main>
    </div>
    <script>
        function loadPage(page) {
            document.getElementById('mainFrame').src = page;
            document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active-nav'));
            event.currentTarget.classList.add('active-nav');
        }
    </script>
</body>
</html>
```

### Layout B: 顶部水平导航

```
┌─ Header (h-16) ──────────────────────────────────┐
│  [Logo] 系统名称   [首页] [工作台] [报表] [设置]  │
├─ Main (full width) ──────────────────────────────┤
│                                                   │
│   <iframe> 内容区                                 │
│                                                   │
└───────────────────────────────────────────────────┘
```

**适用**: 企业门户、营销型工作台 | **信息层级**: 1 级（顶部菜单直达）

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>系统名称</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script>
        tailwind.config = { theme: { extend: { colors: {
            primary: '#1E3A5F', secondary: '#FF6A00', accent: '#10B981'
        }}}}
    </script>
    <style>
        html, body { height: 100%; margin: 0; padding: 0; overflow: hidden; }
        .portal-container { height: calc(100vh - 64px); overflow: hidden; }
        .nav-tab { position: relative; }
        .nav-tab.active { color: var(--primary, #1E3A5F); }
        .nav-tab.active::after {
            content: ''; position: absolute; bottom: -2px; left: 0; right: 0;
            height: 3px; background: #1E3A5F; border-radius: 2px;
        }
        #mainFrame { width: 100%; height: 100%; border: 0; }
    </style>
</head>
<body class="bg-gray-50">
    <header class="bg-white shadow-sm h-16 flex items-center px-6">
        <div class="flex items-center mr-8">
            <i class="fas fa-building text-primary text-2xl mr-3"></i>
            <h1 class="text-xl font-bold text-gray-800">系统名称</h1>
        </div>
        <nav class="flex items-center space-x-6">
            <a href="#" onclick="loadPage('portal/dashboard.html')" class="nav-tab active text-gray-700 hover:text-primary font-medium">
                <i class="fas fa-home mr-1"></i> 首页
            </a>
            <a href="#" onclick="loadPage('work/index.html')" class="nav-tab text-gray-700 hover:text-primary font-medium">
                <i class="fas fa-briefcase mr-1"></i> 工作台
            </a>
            <a href="#" onclick="loadPage('report/index.html')" class="nav-tab text-gray-700 hover:text-primary font-medium">
                <i class="fas fa-chart-bar mr-1"></i> 报表
            </a>
            <a href="#" onclick="loadPage('system/settings.html')" class="nav-tab text-gray-700 hover:text-primary font-medium">
                <i class="fas fa-cog mr-1"></i> 设置
            </a>
        </nav>
        <div class="ml-auto flex items-center space-x-4">
            <button class="text-gray-600 hover:text-gray-900"><i class="fas fa-bell"></i></button>
            <div class="flex items-center">
                <div class="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-white mr-2">
                    <i class="fas fa-user"></i>
                </div>
                <span class="text-gray-700">用户名</span>
            </div>
        </div>
    </header>
    <main class="portal-container">
        <iframe id="mainFrame" src="portal/dashboard.html" class="w-full h-full border-0"></iframe>
    </main>
    <script>
        function loadPage(page) {
            document.getElementById('mainFrame').src = page;
            document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
            event.currentTarget.classList.add('active');
        }
    </script>
</body>
</html>
```

### Layout C: 侧边栏 + 顶部二级标签

```
┌─ Header (h-16) ──────────────────────────────────┐
│  [Logo] 系统名称              [🔔] [👤 用户名]   │
├─ Sidebar ─┬─ Sub Nav (h-12) ──────────────────────┤
│ (w-64)    │  [子页1] [子页2] [子页3]              │
│           ├─ Main ─────────────────────────────────┤
│  ▸ 模块1  │                                        │
│  ▸ 模块2  │   <iframe> 内容区                     │
│  ▸ 模块3  │                                        │
└───────────┴────────────────────────────────────────┘
```

**适用**: 复杂管理系统、客户端 | **信息层级**: 3 级（模块 + 子页 + 页内）

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>系统名称</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script>
        tailwind.config = { theme: { extend: { colors: {
            primary: '#3B82F6', secondary: '#64748B', accent: '#10B981'
        }}}}
    </script>
    <style>
        html, body { height: 100%; margin: 0; padding: 0; overflow: hidden; }
        .nav-item:hover { background-color: #EFF6FF; }
        .active-nav { background-color: #DBEAFE; border-left: 4px solid #3B82F6; }
        .sub-tab { border-bottom: 2px solid transparent; }
        .sub-tab.active { color: #3B82F6; border-bottom-color: #3B82F6; }
        #mainFrame { width: 100%; height: 100%; border: 0; }
    </style>
</head>
<body class="bg-gray-50">
    <header class="bg-white shadow-sm h-16 flex items-center px-6">
        <div class="flex items-center">
            <i class="fas fa-cube text-primary text-2xl mr-3"></i>
            <h1 class="text-xl font-bold text-gray-800">系统名称</h1>
        </div>
        <div class="ml-auto flex items-center space-x-4">
            <button class="text-gray-600 hover:text-gray-900"><i class="fas fa-bell"></i></button>
            <div class="flex items-center">
                <div class="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-white mr-2">
                    <i class="fas fa-user"></i>
                </div>
                <span class="text-gray-700">用户名</span>
            </div>
        </div>
    </header>
    <div class="flex" style="height: calc(100vh - 64px);">
        <!-- 一级：模块侧边栏 -->
        <aside class="w-64 bg-white shadow-md overflow-y-auto">
            <nav class="py-4">
                <div class="px-4 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">业务管理</div>
                <a href="#" onclick="selectModule('contract', this)" class="nav-item active-nav flex items-center px-4 py-3 text-gray-700">
                    <i class="fas fa-file-contract mr-3"></i><span>合同管理</span>
                </a>
                <a href="#" onclick="selectModule('performance', this)" class="nav-item flex items-center px-4 py-3 text-gray-700">
                    <i class="fas fa-tasks mr-3"></i><span>履约管理</span>
                </a>
            </nav>
        </aside>
        <!-- 右侧：二级标签 + 内容 -->
        <div class="flex-1 flex flex-col overflow-hidden">
            <!-- 二级标签栏 -->
            <div class="bg-white border-b h-12 flex items-center px-4 gap-4" id="subNav">
                <a href="#" onclick="loadPage('contract/list.html')" class="sub-tab active px-3 py-2 text-sm font-medium text-gray-600">合同列表</a>
                <a href="#" onclick="loadPage('contract/free.html')" class="sub-tab px-3 py-2 text-sm font-medium text-gray-600">自由合同</a>
                <a href="#" onclick="loadPage('contract/breach.html')" class="sub-tab px-3 py-2 text-sm font-medium text-gray-600">违约记录</a>
            </div>
            <!-- 内容区 -->
            <div class="flex-1 p-4 overflow-hidden">
                <iframe id="mainFrame" src="contract/list.html" class="w-full h-full border-0 rounded-lg shadow"></iframe>
            </div>
        </div>
    </div>
    <script>
        function loadPage(page) {
            document.getElementById('mainFrame').src = page;
            document.querySelectorAll('.sub-tab').forEach(t => t.classList.remove('active'));
            event.currentTarget.classList.add('active');
        }
        function selectModule(module, el) {
            document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active-nav'));
            el.classList.add('active-nav');
            // 按模块切换二级标签内容（实际使用时替换 subNav 子元素）
            const subNavMap = {
                contract: [['合同列表','contract/list.html'],['自由合同','contract/free.html'],['违约记录','contract/breach.html']],
                performance: [['履约总览','performance/overview.html'],['付款管理','performance/payment.html'],['发货管理','performance/delivery.html']]
            };
            const subNav = document.getElementById('subNav');
            subNav.innerHTML = '';
            subNavMap[module].forEach((item, i) => {
                const a = document.createElement('a');
                a.href = '#'; a.className = 'sub-tab px-3 py-2 text-sm font-medium text-gray-600' + (i === 0 ? ' active' : '');
                a.textContent = item[0]; a.onclick = function(e) { e.preventDefault(); loadPage(item[1]); };
                subNav.appendChild(a);
            });
            loadPage(subNavMap[module][0][1]);
        }
    </script>
</body>
</html>
```

### Layout D: 折叠图标侧边栏

```
┌─ Header (h-16) ──────────────────────────────────┐
│  [≡] 系统名称               [🔔] [👤 用户名]    │
├─ Icon Bar ─┬─ Main ──────────────────────────────┤
│ (w-16)     │                                      │
│  [🏠]      │   <iframe> 内容区                    │
│  [📋]      │                                      │
│  [💰]      │   hover 时侧边栏展开到 w-64          │
│  [📊]      │                                      │
│  [⚙️]      │                                      │
└────────────┴──────────────────────────────────────┘
```

**适用**: 会员中心、现代感后台、内容优先场景 | **信息层级**: 1-2 级

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>系统名称</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script>
        tailwind.config = { theme: { extend: { colors: {
            primary: '#059669', secondary: '#0EA5E9', accent: '#F59E0B'
        }}}}
    </script>
    <style>
        html, body { height: 100%; margin: 0; padding: 0; overflow: hidden; }
        .sidebar { width: 64px; transition: width 0.2s ease; }
        .sidebar:hover { width: 256px; }
        .sidebar:hover .nav-label { display: inline; }
        .nav-label { display: none; white-space: nowrap; }
        .nav-icon-item { display: flex; align-items: center; padding: 12px; }
        .nav-icon-item:hover { background-color: #ECFDF5; }
        .active-icon { background-color: #D1FAE5; border-left: 3px solid #059669; }
        #mainFrame { width: 100%; height: 100%; border: 0; }
    </style>
</head>
<body class="bg-gray-50">
    <header class="bg-white shadow-sm h-16 flex items-center px-6">
        <div class="flex items-center">
            <i class="fas fa-leaf text-primary text-2xl mr-3"></i>
            <h1 class="text-xl font-bold text-gray-800">系统名称</h1>
        </div>
        <div class="ml-auto flex items-center space-x-4">
            <button class="text-gray-600 hover:text-gray-900"><i class="fas fa-bell"></i></button>
            <div class="flex items-center">
                <div class="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-white mr-2">
                    <i class="fas fa-user"></i>
                </div>
                <span class="text-gray-700">用户名</span>
            </div>
        </div>
    </header>
    <div class="flex" style="height: calc(100vh - 64px);">
        <aside class="sidebar bg-white shadow-md overflow-hidden">
            <nav class="py-4">
                <a href="#" onclick="loadPage('dashboard.html')" class="nav-icon-item active-icon text-gray-700">
                    <i class="fas fa-home text-lg w-6 text-center"></i><span class="nav-label ml-3">工作台</span>
                </a>
                <a href="#" onclick="loadPage('orders/list.html')" class="nav-icon-item text-gray-700">
                    <i class="fas fa-clipboard-list text-lg w-6 text-center"></i><span class="nav-label ml-3">我的订单</span>
                </a>
                <a href="#" onclick="loadPage('finance/index.html')" class="nav-icon-item text-gray-700">
                    <i class="fas fa-wallet text-lg w-6 text-center"></i><span class="nav-label ml-3">资金中心</span>
                </a>
                <a href="#" onclick="loadPage('docs/index.html')" class="nav-icon-item text-gray-700">
                    <i class="fas fa-folder-open text-lg w-6 text-center"></i><span class="nav-label ml-3">单据中心</span>
                </a>
                <a href="#" onclick="loadPage('profile/settings.html')" class="nav-icon-item text-gray-700">
                    <i class="fas fa-cog text-lg w-6 text-center"></i><span class="nav-label ml-3">账号设置</span>
                </a>
            </nav>
        </aside>
        <main class="flex-1 p-6 overflow-hidden">
            <iframe id="mainFrame" src="dashboard.html" class="w-full h-full border-0 rounded-lg shadow"></iframe>
        </main>
    </div>
    <script>
        function loadPage(page) {
            document.getElementById('mainFrame').src = page;
            document.querySelectorAll('.nav-icon-item').forEach(i => i.classList.remove('active-icon'));
            event.currentTarget.classList.add('active-icon');
        }
    </script>
</body>
</html>
```

### Layout E: 双栏树形导航

```
┌─ Header (h-16) ──────────────────────────────────┐
│  [Logo] 系统名称              [🔔] [👤 用户名]   │
├─ Tree Nav ────┬─ Content ────────────────────────┤
│ (w-72)        │                                    │
│  ▸ 分组1     │   <iframe> 内容区                  │
│    ▸ 子项1   │                                    │
│    ▸ 子项2   │                                    │
│  ▸ 分组2     │                                    │
│    ▸ 子项3   │                                    │
└──────────────┴────────────────────────────────────┘
```

**适用**: 文件管理、分类管理、多层级设置页 | **信息层级**: 3 级+（分组 + 子分组 + 叶子节点）

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>系统名称</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script>
        tailwind.config = { theme: { extend: { colors: {
            primary: '#3B82F6', secondary: '#64748B', accent: '#10B981'
        }}}}
    </script>
    <style>
        html, body { height: 100%; margin: 0; padding: 0; overflow: hidden; }
        .tree-group-btn { cursor: pointer; }
        .tree-children { display: none; }
        .tree-children.open { display: block; }
        .tree-item:hover { background-color: #EFF6FF; }
        .tree-item.active { background-color: #DBEAFE; color: #3B82F6; font-weight: 600; }
        #mainFrame { width: 100%; height: 100%; border: 0; }
    </style>
</head>
<body class="bg-gray-50">
    <header class="bg-white shadow-sm h-16 flex items-center px-6">
        <div class="flex items-center">
            <i class="fas fa-folder-tree text-primary text-2xl mr-3"></i>
            <h1 class="text-xl font-bold text-gray-800">系统名称</h1>
        </div>
        <div class="ml-auto flex items-center space-x-4">
            <button class="text-gray-600 hover:text-gray-900"><i class="fas fa-bell"></i></button>
            <span class="text-gray-700">用户名</span>
        </div>
    </header>
    <div class="flex" style="height: calc(100vh - 64px);">
        <aside class="w-72 bg-white shadow-md overflow-y-auto">
            <div class="p-4 border-b">
                <input type="text" placeholder="搜索..." class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
            </div>
            <nav class="p-2" id="treeNav">
                <!-- 分组1 -->
                <div class="tree-group-btn flex items-center px-3 py-2 text-gray-700" onclick="toggleGroup(this)">
                    <i class="fas fa-chevron-down text-xs mr-2 transition-transform"></i>
                    <span class="font-medium">分组名称1</span>
                </div>
                <div class="tree-children open ml-4">
                    <a href="#" onclick="loadPage('module/sub1.html')" class="tree-item active flex items-center px-3 py-2 text-sm text-gray-600 rounded">
                        <i class="fas fa-file mr-2 text-xs"></i> 子项1
                    </a>
                    <a href="#" onclick="loadPage('module/sub2.html')" class="tree-item flex items-center px-3 py-2 text-sm text-gray-600 rounded">
                        <i class="fas fa-file mr-2 text-xs"></i> 子项2
                    </a>
                </div>
                <!-- 分组2 -->
                <div class="tree-group-btn flex items-center px-3 py-2 text-gray-700" onclick="toggleGroup(this)">
                    <i class="fas fa-chevron-down text-xs mr-2 transition-transform"></i>
                    <span class="font-medium">分组名称2</span>
                </div>
                <div class="tree-children open ml-4">
                    <a href="#" onclick="loadPage('module2/sub1.html')" class="tree-item flex items-center px-3 py-2 text-sm text-gray-600 rounded">
                        <i class="fas fa-file mr-2 text-xs"></i> 子项3
                    </a>
                </div>
            </nav>
        </aside>
        <main class="flex-1 p-4 overflow-hidden">
            <iframe id="mainFrame" src="module/sub1.html" class="w-full h-full border-0 rounded-lg shadow"></iframe>
        </main>
    </div>
    <script>
        function loadPage(page) {
            document.getElementById('mainFrame').src = page;
            document.querySelectorAll('.tree-item').forEach(i => i.classList.remove('active'));
            event.currentTarget.classList.add('active');
        }
        function toggleGroup(el) {
            const children = el.nextElementSibling;
            const icon = el.querySelector('i');
            children.classList.toggle('open');
            icon.style.transform = children.classList.contains('open') ? 'rotate(0deg)' : 'rotate(-90deg)';
        }
    </script>
</body>
</html>
```

### Layout F: 手机底部 Tab 栏

```
┌─ 状态栏 (h-8) ──────────────────────────────────┐
│  9:41                              📶 🔋          │
├─ 品牌Header (h-14) ──────────────────────────────┤
│  [🏆] 系统名称              [🔔] [👤]            │
├─ iframe 内容区 ──────────────────────────────────┤
│                                                    │
│   (页面内容)                                       │
│                                                    │
├─ 底部Tab栏 (h-16) ────────────────────────────────┤
│  [🏠首页] [📋合同] [⚡履约] [✅待办] [👤我的]     │
└────────────────────────────────────────────────────┘
```

**适用**: 手机端、平板 | **信息层级**: 1 级（底部 Tab 直达）

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>系统名称</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script>
        tailwind.config = { theme: { extend: { colors: {
            primary: '#d97706', secondary: '#059669', accent: '#3B82F6'
        }}}}
    </script>
    <style>
        * { -webkit-tap-highlight-color: transparent; }
        html, body { height: 100%; margin: 0; padding: 0; overflow: hidden; font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; }
        body { max-width: 430px; margin: 0 auto; background: #f8f6f2; position: relative; box-shadow: 0 0 20px rgba(0,0,0,0.1); }
        .app-container { height: 100vh; display: flex; flex-direction: column; overflow: hidden; }
        .tab-item { -webkit-flex: 1; flex: 1; text-align: center; padding: 6px 0; color: #999; }
        .tab-item.active { color: #d97706; }
        .tab-item i { font-size: 20px; }
        .tab-item span { display: block; font-size: 11px; margin-top: 2px; }
        #appFrame { width: 100%; flex: 1; border: 0; background: #f8f6f2; }
    </style>
</head>
<body>
    <div class="app-container">
        <!-- 状态栏 -->
        <div class="bg-white flex items-center justify-between px-4 py-1 text-xs text-gray-800">
            <span>9:41</span>
            <span><i class="fas fa-wifi"></i> <i class="fas fa-signal"></i> <i class="fas fa-battery-three-quarters"></i></span>
        </div>
        <!-- 品牌Header -->
        <header class="bg-white shadow-sm flex items-center px-4 py-3">
            <div class="flex items-center">
                <i class="fas fa-trophy text-primary text-xl mr-2"></i>
                <h1 class="text-base font-bold text-gray-800">系统名称</h1>
            </div>
            <div class="ml-auto flex items-center space-x-3">
                <button class="text-gray-500"><i class="fas fa-bell"></i></button>
                <div class="w-7 h-7 rounded-full bg-primary flex items-center justify-center text-white text-xs">
                    <i class="fas fa-user"></i>
                </div>
            </div>
        </header>
        <!-- 内容区 -->
        <iframe id="appFrame" src="pages/dashboard.html"></iframe>
        <!-- 底部Tab栏 -->
        <nav class="bg-white border-t flex items-center" style="height: 56px;">
            <a href="#" onclick="loadPage('pages/dashboard.html', this)" class="tab-item active">
                <i class="fas fa-home"></i><span>首页</span>
            </a>
            <a href="#" onclick="loadPage('pages/contracts.html', this)" class="tab-item">
                <i class="fas fa-file-contract"></i><span>合同</span>
            </a>
            <a href="#" onclick="loadPage('pages/fulfillment.html', this)" class="tab-item">
                <i class="fas fa-bolt"></i><span>履约</span>
            </a>
            <a href="#" onclick="loadPage('pages/tasks.html', this)" class="tab-item">
                <i class="fas fa-check-circle"></i><span>待办</span>
            </a>
            <a href="#" onclick="loadPage('pages/profile.html', this)" class="tab-item">
                <i class="fas fa-user-circle"></i><span>我的</span>
            </a>
        </nav>
    </div>
    <script>
        function loadPage(page, el) {
            document.getElementById('appFrame').src = page;
            document.querySelectorAll('.tab-item').forEach(t => t.classList.remove('active'));
            el.classList.add('active');
        }
    </script>
</body>
</html>
```

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

## Page Type Patterns

### Type 1: List/CRUD Page

列表/增删改查页 — 最常用模式。包含: 标题栏、统计卡片、筛选栏、数据表格、分页。

**区块顺序:**
1. **标题栏** — `flex justify-between items-center mb-6`，h1 标题 + 操作按钮
2. **统计卡片** — `grid grid-cols-1 md:grid-cols-4 gap-6`
3. **筛选栏** — `bg-white rounded-lg shadow p-4`，4列网格
4. **数据表格** — `bg-white rounded-lg shadow overflow-hidden`
5. **分页** — 表格底部 footer

**统计卡片:**
```html
<div class="bg-white rounded-lg shadow p-6">
    <div class="flex items-center">
        <div class="p-3 rounded-full bg-blue-100 text-blue-600">
            <i class="fas fa-icon text-xl"></i>
        </div>
        <div class="ml-4">
            <p class="text-gray-500 text-sm">标签</p>
            <h3 class="text-2xl font-bold">1,248</h3>
        </div>
    </div>
</div>
```

**状态标签配色:**
| 状态 | Badge classes |
|------|--------------|
| 履约中/合规/正常/完成 | `bg-green-100 text-green-800` |
| 待履约/待处理 | `bg-yellow-100 text-yellow-800` |
| 已作废/不合规/驳回 | `bg-red-100 text-red-800` |
| 已归档/已解决 | `bg-gray-100 text-gray-800` |

**筛选栏:**
```html
<div class="bg-white rounded-lg shadow mb-6 p-4">
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">字段名</label>
            <input type="text" class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="请输入...">
        </div>
        <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">状态下拉</label>
            <select class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">
                <option value="">全部状态</option>
                <option value="opt1">选项1</option>
            </select>
        </div>
        <div class="flex items-end">
            <button class="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">搜索</button>
        </div>
    </div>
</div>
```

**数据表格:**
```html
<div class="bg-white rounded-lg shadow overflow-hidden">
    <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
                <tr>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">列名</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">操作</th>
                </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
                <tr class="hover:bg-gray-50">
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">数据</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        <a href="#" class="text-blue-600 hover:text-blue-900 mr-3">查看</a>
                        <a href="#" class="text-green-600 hover:text-green-900 mr-3">编辑</a>
                        <a href="#" class="text-red-600 hover:text-red-900">删除</a>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
    <div class="bg-white px-4 py-3 flex items-center justify-between border-t border-gray-200">
        <div class="text-sm text-gray-700">显示第 <span class="font-medium">1</span> 到 <span class="font-medium">10</span> 条，共 <span class="font-medium">97</span> 条</div>
        <nav class="inline-flex rounded-md shadow-sm -space-x-px">
            <a href="#" class="px-2 py-2 rounded-l-md border border-gray-300 bg-white text-gray-500 hover:bg-gray-50"><i class="fas fa-chevron-left"></i></a>
            <a href="#" class="px-4 py-2 border bg-blue-50 text-blue-600">1</a>
            <a href="#" class="px-4 py-2 border border-gray-300 bg-white text-gray-700 hover:bg-gray-50">2</a>
            <a href="#" class="px-2 py-2 rounded-r-md border border-gray-300 bg-white text-gray-500 hover:bg-gray-50"><i class="fas fa-chevron-right"></i></a>
        </nav>
    </div>
</div>
```

### Type 2: Dashboard/Portal Page

仪表盘/门户页 — 包含: 问候区、统计卡片行、图表区、快捷操作网格。

**关键区块:**
1. **问候** — h1 + 日期/描述
2. **统计卡片** — `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6`，含趋势箭头
3. **图表 + 最近活动** — `grid grid-cols-1 lg:grid-cols-3 gap-6`，图表 col-span-2
4. **快捷操作** — `grid grid-cols-2 md:grid-cols-4 gap-4`

**图表容器:**
```html
<div class="bg-white rounded-lg shadow p-6">
    <div class="flex justify-between items-center mb-6">
        <h2 class="text-lg font-bold text-gray-800">图表标题</h2>
        <div class="flex space-x-2">
            <button class="px-3 py-1 text-sm bg-blue-100 text-blue-600 rounded">月度</button>
            <button class="px-3 py-1 text-sm text-gray-600 hover:bg-gray-100 rounded">季度</button>
        </div>
    </div>
    <div class="h-64 pt-8 border-t">
        <canvas id="myChart"></canvas>
    </div>
</div>
```

**Chart.js 用法:**
```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
<script>
    const ctx = document.getElementById('myChart').getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: { labels: ['1月', '2月', '3月'], datasets: [{ /* data */ }] },
        options: { responsive: true, maintainAspectRatio: false }
    });
</script>
```

### Type 3: Process/Wizard Page

流程/向导页 — 包含: 步骤条、关键指标卡片、详细信息区、操作按钮。

**步骤条:**
```html
<div class="relative mb-8">
    <div class="absolute top-1/2 left-0 right-0 h-0.5 bg-neutral-200 -translate-y-1/2 z-0"></div>
    <div class="absolute top-1/2 left-0 w-2/5 h-0.5 bg-primary -translate-y-1/2 z-10"></div>
    <div class="flex justify-between relative z-20">
        <div class="flex flex-col items-center">
            <div class="w-8 h-8 rounded-full border-2 step-completed flex items-center justify-center mb-2">
                <i class="fa fa-check text-sm"></i>
            </div>
            <span class="text-xs font-medium">已完成步骤</span>
        </div>
        <div class="flex flex-col items-center">
            <div class="w-8 h-8 rounded-full border-2 step-active flex items-center justify-center mb-2">
                <i class="fa fa-icon text-sm"></i>
            </div>
            <span class="text-xs font-medium text-primary">当前步骤</span>
        </div>
        <div class="flex flex-col items-center">
            <div class="w-8 h-8 rounded-full border-2 border-neutral-200 text-neutral-400 flex items-center justify-center mb-2">
                <i class="fa fa-icon text-sm"></i>
            </div>
            <span class="text-xs font-medium text-neutral-500">待处理</span>
        </div>
    </div>
</div>
```

### Type 4: Settings/Config Page

设置/配置页 — 左标签导航 + 右内容面板。

```html
<div class="flex flex-col md:flex-row gap-6">
    <div class="md:w-1/4">
        <div class="bg-white rounded-lg shadow">
            <div class="p-4 border-b"><h2>设置分类</h2></div>
            <nav class="p-2">
                <a href="#" class="flex items-center px-4 py-3 text-blue-600 bg-blue-50 rounded-lg mb-1" data-target="tab1">
                    <i class="fas fa-icon mr-3"></i><span>标签1</span>
                </a>
                <a href="#" class="flex items-center px-4 py-3 text-gray-700 hover:bg-gray-50 rounded-lg mb-1" data-target="tab2">
                    <i class="fas fa-icon mr-3"></i><span>标签2</span>
                </a>
            </nav>
        </div>
    </div>
    <div class="md:w-3/4">
        <div class="bg-white rounded-lg shadow settings-content" id="tab1-content"></div>
        <div class="bg-white rounded-lg shadow settings-content" id="tab2-content" style="display: none;"></div>
    </div>
</div>
<script>
    document.querySelectorAll('[data-target]').forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            document.querySelectorAll('[data-target]').forEach(n => n.classList.remove('text-blue-600', 'bg-blue-50'));
            this.classList.add('text-blue-600', 'bg-blue-50');
            document.querySelectorAll('.settings-content').forEach(c => c.style.display = 'none');
            document.getElementById(this.dataset.target + '-content').style.display = 'block';
        });
    });
</script>
```

### Type 5: Big Screen/Dashboard

数据大屏 — 暗色背景、发光卡片、动态数字、地图图表。使用 Chart.js，紧凑网格，小字号。

```html
<body class="bg-slate-950 text-white">
    <div class="p-4 grid grid-cols-12 gap-4">
        <div class="col-span-3 bg-slate-900 rounded-lg border border-slate-800 p-4 shadow-lg">
            <p class="text-slate-400 text-sm">关键指标</p>
            <h2 class="text-3xl font-bold text-cyan-400">1,248</h2>
        </div>
        <!-- 更多卡片... -->
    </div>
</body>
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
├── index.html              # Shell (按选定 Layout 生成)
├── portal/                 # 仪表盘/概览页
├── module-name/            # 功能模块
│   ├── list.html           # 列表页
│   ├── detail.html         # 详情页
│   └── form.html           # 表单页
├── common/                 # 跨模块共用页面
├── system/                 # 配置/管理页
├── report/                 # 报表/图表页
└── screen/                 # 大屏页（可选）
```

---

## Key Dependencies (CDN)

| Library | CDN URL | When to Use |
|---------|---------|-------------|
| Tailwind CSS | `https://cdn.tailwindcss.com` | Always required |
| Font Awesome 6.4 | `https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css` | Always required |
| Chart.js 3.9.1 | `https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js` | Charts/dashboards |

---

## Development Instructions

### 生成新项目流程

1. **选择用途** — 从「Step 1 用途预设表」确定用途代号和主题色
2. **选择布局** — 从「Step 2 菜单布局」选择 Layout A-F，复制对应 shell 模板
3. **创建 index.html** — 粘贴选定 Layout 模板，替换主题色、系统名称、菜单项
4. **创建模块目录** — 按菜单结构建子目录
5. **生成子页面** — 用 Page Boilerplate 生成各页面，套用 Page Type Pattern

### 生成新页面流程

1. 确定页面类型（List / Dashboard / Process / Settings / Big Screen）
2. 复制 Page Boilerplate 作为骨架
3. 套用对应 Page Type Pattern 的区块代码
4. 替换主题色（与 shell 保持一致）
5. 如需在已有 shell 中加入口，在 sidebar/nav 中添加菜单项
