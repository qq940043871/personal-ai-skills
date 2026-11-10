# Shell 布局模板 — Layout A–F

按用途与信息层级选择布局，直接复制对应模板到 `<项目根>/index.html`，再替换主题色、系统名称与菜单项。

| 布局 | 形态 | 适用用途 | 信息层级 |
|------|------|----------|----------|
| A | 经典左侧边栏 | admin / member / client / design | 2 级（分组 + 菜单项） |
| B | 顶部水平导航 | portal / 营销型工作台 | 1 级（顶部菜单直达） |
| C | 侧边栏 + 顶部二级标签 | 复杂管理系统 / client | 3 级（模块 + 子页 + 页内） |
| D | 折叠图标侧边栏 | member / 现代感后台 | 1-2 级 |
| E | 双栏树形导航 | 文件/分类/多层级设置 | 3 级+ |
| F | 手机底部 Tab 栏 | mobile / 平板 | 1 级（底部 Tab 直达） |

> 模板中的配色为对应默认用途，实际生成时按 `../SKILL.md` 的「用途配置预设」替换。

---

## Layout A: 经典左侧边栏（最通用）

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

**适用**: 管理后台、会员中心、客户端、文档系统 | **信息层级**: 2 级（分组 + 菜单项）

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

---

## Layout B: 顶部水平导航

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

---

## Layout C: 侧边栏 + 顶部二级标签

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

---

## Layout D: 折叠图标侧边栏

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

---

## Layout E: 双栏树形导航

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

---

## Layout F: 手机底部 Tab 栏

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
