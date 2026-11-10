# 通用页面模式 — Type 1–5

子页面的区块级模板。先按页面类型选型，再复制对应片段；配色随用途替换（见 `../SKILL.md`「Color Conventions」）。

| 类型 | 用途 | 主要区块 |
|------|------|----------|
| Type 1 | 列表 / 增删改查 | 标题栏、统计卡片、筛选栏、数据表格、分页 |
| Type 2 | 仪表盘 / 门户 | 问候区、统计卡片行、图表区、快捷操作 |
| Type 3 | 流程 / 向导 | 步骤条、指标卡片、详情区、操作按钮 |
| Type 4 | 设置 / 配置 | 左侧标签导航 + 右侧内容面板 |
| Type 5 | 数据大屏 | 暗底、发光卡片、动态数字、图表 |

---

## Type 1: List/CRUD Page

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

---

## Type 2: Dashboard/Portal Page

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

---

## Type 3: Process/Wizard Page

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

---

## Type 4: Settings/Config Page

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

---

## Type 5: Big Screen/Dashboard

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
