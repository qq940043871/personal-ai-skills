---
name: html-manage-pages
description: Patterns for management backend pages (运营后台). Use when creating admin CRUD pages, system config pages, contract/fulfillment management, reports, or any admin backend module in the 02-manage quadrant.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# 02-manage — 管理端页面技能

> **适用目录**: `02-manage/` 及其子目录
> **整体风格**: 蓝色主题 `#3B82F6`，专业后台，表格驱动，数据密集
> **Shell**: `02-manage/index.html` — Header(h-16) + Sidebar(w-64) + iframe

---

## 1. Shell 导航结构

### 侧边栏导航分组 (02-manage/index.html)

```
首页
  ├── 工作台 → portal/admin-portal.html
系统配置
  ├── 系统设置 → system/system-settings.html
  ├── 交收模式 → system/set-mode.html
  ├── 付款规则 → system/payment-rules.html
  ├── 合同模板 → system/template-management.html
  ├── 交收商品 → system/commodity-params-config.html
  └── 客户参数 → system/customer-params-config.html
业务管理
  ├── 合同管理 → contract/contract-list.html
  ├── 履约管理 → performance/performance.html
  ├── 违约记录 → contract/breach-list.html
  └── 纠纷管理 → contract/dispute-list.html
统计报表
  └── 合同报表 → report/reports.html
```

### 导航核心函数
```javascript
function loadPage(page) {
    document.getElementById('mainFrame').src = page;
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active-nav');
        const onclick = item.getAttribute('onclick') || '';
        if (onclick.includes(page)) item.classList.add('active-nav');
    });
}
function toggleGroup(header) {
    const content = header.nextElementSibling;
    const icon = header.querySelector('.collapse-icon');
    content.classList.toggle('collapsed');
    icon.classList.toggle('rotated');
    content.style.maxHeight = content.classList.contains('collapsed') ? '0px' : content.scrollHeight + 'px';
}
```

### 跨iframe导航通信
子页面使用 `postMessage` 与Shell通信：
```javascript
window.parent.postMessage({ type: 'navigate', to: 'relative/path.html', id: 'xxx' }, '*');
```
Shell监听：
```javascript
window.addEventListener('message', function(e) {
    if (e.data.type === 'navigate') loadPage(e.data.to);
});
```
- `to` 以 `http`/`https` 开头 → `window.open(e.data.to)` 新标签打开
- 否则 → 更新 iframe `src`

---

## 2. 管理端页面类型详解

### Type A: 列表/CRUD 页面 (最常见)

**典型文件**: `contract-list.html`, `breach-list.html`, `dispute-list.html`, `reports.html`

**完整结构**:
```
┌─ 页面标题栏 ──────────────────────────────────────┐
│  [标题]  [描述]                    [新建] [导出]   │
├─ 统计卡片行 ───────────────────────────────────────┤
│  [总数]  [待处理]  [已完成]  [异常]               │
├─ 筛选栏 ──────────────────────────────────────────┤
│  [搜索框]  [状态下拉]  [日期]  [搜索按钮]         │
├─ 数据表格 ────────────────────────────────────────┤
│  [表头]                                            │
│  [数据行 带状态标签和操作链接]                      │
│  [数据行] ...                                      │
├─ 分页栏 ──────────────────────────────────────────┤
│  '显示第 1 到 10 条，共 97 条'  [页码导航]        │
└───────────────────────────────────────────────────┘
```

**统计卡片模式**:
```html
<div class="bg-white rounded-lg shadow p-6">
    <div class="flex items-center">
        <div class="p-3 rounded-full bg-blue-100 text-blue-600">
            <i class="fas fa-file-alt text-xl"></i>
        </div>
        <div class="ml-4">
            <p class="text-gray-500 text-sm">标签</p>
            <h3 class="text-2xl font-bold">1,248</h3>
        </div>
    </div>
</div>
```

**筛选栏模式**:
```html
<div class="bg-white rounded-lg shadow mb-6 p-4">
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">字段</label>
            <input type="text" class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">
        </div>
        <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">状态下拉</label>
            <select class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">
                <option value="">全部状态</option>
                <option value="opt1">选项1</option>
            </select>
        </div>
        <div class="flex items-end space-x-2">
            <button class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">查询</button>
            <button class="px-4 py-2 bg-white border border-gray-300 rounded-md hover:bg-gray-50">重置</button>
        </div>
    </div>
</div>
```

**数据表格模式**:
```html
<div class="bg-white rounded-lg shadow overflow-hidden">
    <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
                <tr>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">列名</th>
                    <!-- ...更多列... -->
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">操作</th>
                </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
                <tr class="hover:bg-gray-50">
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">数据</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm">
                        <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">正常</span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        <a href="#" class="text-blue-600 hover:text-blue-900 mr-3">查看</a>
                        <a href="#" class="text-green-600 hover:text-green-900 mr-3">编辑</a>
                        <a href="#" class="text-red-600 hover:text-red-900">删除</a>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
    <!-- 分页 -->
    <div class="px-4 py-3 flex items-center justify-between border-t">
        <div class="text-sm text-gray-700">显示第 <span class="font-medium">1</span> 到 <span class="font-medium">10</span> 条，共 <span class="font-medium">97</span> 条</div>
        <nav class="relative z-0 inline-flex rounded-md shadow-sm -space-x-px">
            <a href="#" class="relative inline-flex items-center px-2 py-2 rounded-l-md border bg-white text-gray-500"><i class="fas fa-chevron-left"></i></a>
            <a href="#" class="relative inline-flex items-center px-4 py-2 border bg-blue-50 text-blue-600">1</a>
            <a href="#" class="relative inline-flex items-center px-4 py-2 border bg-white text-gray-700 hover:bg-gray-50">2</a>
            <a href="#" class="relative inline-flex items-center px-2 py-2 rounded-r-md border bg-white text-gray-500"><i class="fas fa-chevron-right"></i></a>
        </nav>
    </div>
</div>
```

### Type B: 系统配置页

**典型文件**: `system-settings.html`, `payment-rules.html`, `customer-params-config.html`

**左标签 + 右内容布局**:
```html
<div class="flex flex-col md:flex-row gap-6">
    <!-- 左侧标签导航 (w-1/4) -->
    <div class="md:w-1/4">
        <div class="bg-white rounded-lg shadow">
            <div class="p-4 border-b"><h2 class="font-bold">设置分类</h2></div>
            <nav class="p-2" id="settings-nav">
                <a href="#" class="nav-item flex items-center px-4 py-3 text-blue-600 bg-blue-50 rounded-lg mb-1" data-target="tab1">
                    <i class="fas fa-sliders-h mr-3 w-5"></i><span>基础参数</span>
                </a>
                <a href="#" class="nav-item flex items-center px-4 py-3 text-gray-700 hover:bg-gray-50 rounded-lg mb-1" data-target="tab2">
                    <i class="fas fa-cog mr-3 w-5"></i><span>高级设置</span>
                </a>
            </nav>
        </div>
    </div>
    <!-- 右侧内容 (w-3/4) -->
    <div class="md:w-3/4">
        <div class="bg-white rounded-lg shadow p-6 settings-content" id="tab1-content">
            <!-- 表单元素 -->
        </div>
        <div class="bg-white rounded-lg shadow p-6 settings-content" id="tab2-content" style="display:none">
            <!-- 表单元素 -->
        </div>
    </div>
</div>
<script>
    document.querySelectorAll('#settings-nav .nav-item').forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            document.querySelectorAll('#settings-nav .nav-item').forEach(n => { n.classList.remove('active','text-blue-600','bg-blue-50'); });
            this.classList.add('active','text-blue-600','bg-blue-50');
            document.querySelectorAll('.settings-content').forEach(c => c.style.display = 'none');
            document.getElementById(this.getAttribute('data-target') + '-content').style.display = 'block';
        });
    });
</script>
```

### Type C: 流程/向导页

**典型文件**: `payment.html`, `delivery.html`, `receipt.html`, `breach-process.html`

**关键组件 — 进度条**:
```html
<div class="relative mb-8">
    <div class="absolute top-1/2 left-0 right-0 h-0.5 bg-gray-200 -translate-y-1/2 z-0"></div>
    <div id="progress-bar" class="absolute top-1/2 left-0 w-0 h-0.5 bg-blue-500 -translate-y-1/2 z-10 transition-all duration-500"></div>
    <div class="flex justify-between relative z-20">
        <div class="step-item flex flex-col items-center" data-step="1">
            <div class="step-circle w-8 h-8 rounded-full border-2 flex items-center justify-center mb-2 text-sm">
                <i class="fas fa-check text-white"></i>
            </div>
            <span class="text-xs font-medium">步骤1</span>
        </div>
        <!-- step-item × N -->
    </div>
</div>
<style>
    .step-circle { transition: all 0.3s; }
    .step-item.completed .step-circle { @apply bg-green-500 border-green-500 text-white; }
    .step-item.active .step-circle { @apply bg-blue-500 border-blue-500 text-white; }
    .step-item.pending .step-circle { @apply border-gray-300 text-gray-400 bg-white; }
</style>
```

**卡片+表单区域**:
```html
<div class="bg-white rounded-lg shadow p-6 mb-6">
    <h3 class="text-lg font-bold text-gray-800 mb-4">标题</h3>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">字段名</label>
            <input type="text" class="w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500" placeholder="请输入">
        </div>
        <!-- 更多表单字段 -->
    </div>
</div>
```

### Type D: 详情页

**典型文件**: `contract-detail.html`, `dispute-detail.html`, `performance-detail.html`

**Tab切换展示详情**:
```html
<div class="border-b border-gray-200 mb-6">
    <nav class="flex space-x-8">
        <button class="tab-btn py-4 px-1 border-b-2 border-blue-500 text-blue-600 font-medium" data-tab="basic">基本信息</button>
        <button class="tab-btn py-4 px-1 border-b-2 border-transparent text-gray-500 hover:text-gray-700" data-tab="items">条款明细</button>
        <button class="tab-btn py-4 px-1 border-b-2 border-transparent text-gray-500 hover:text-gray-700" data-tab="timeline">操作记录</button>
    </nav>
</div>
<div class="tab-content" id="basic">...</div>
<div class="tab-content" id="items" style="display:none">...</div>
<div class="tab-content" id="timeline" style="display:none">...</div>
<script>
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('border-blue-500', 'text-blue-600'));
            this.classList.add('border-blue-500', 'text-blue-600');
            document.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');
            document.getElementById(this.dataset.tab).style.display = 'block';
        });
    });
</script>
```

---

## 3. 管理端特有组件

### 确认弹窗
```html
<div id="confirmModal" class="fixed inset-0 bg-black bg-opacity-50 hidden items-center justify-center z-50">
    <div class="bg-white rounded-xl shadow-2xl p-6 max-w-md mx-4">
        <h3 class="text-lg font-bold text-gray-900 mb-2">确认操作</h3>
        <p class="text-gray-600 mb-6">确定要执行此操作吗？</p>
        <div class="flex justify-end space-x-3">
            <button onclick="closeModal()" class="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200">取消</button>
            <button onclick="confirmAction()" class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">确定</button>
        </div>
    </div>
</div>
```

### 操作按钮配色
| 类型 | 按钮类 | 图标 |
|------|--------|------|
| 查看 | `text-blue-600 hover:text-blue-900` | `fa-eye` |
| 编辑 | `text-green-600 hover:text-green-900` | `fa-edit` |
| 删除 | `text-red-600 hover:text-red-900` | `fa-trash` |
| 审核 | `text-yellow-600 hover:text-yellow-900` | `fa-check-circle` |
| 导出 | `bg-white border text-gray-700` | `fa-download` |
| 新建 | `bg-blue-600 text-white` | `fa-plus` |

---

## 4. 页面级配色

| 用途 | 类 |
|------|-----|
| 页面背景 | `bg-gray-50` |
| 卡片 | `bg-white rounded-lg shadow p-6` |
| 表头 | `bg-gray-50` |
| 输入框聚焦 | `focus:ring-2 focus:ring-blue-500` |
| 主按钮 | `bg-blue-600 text-white hover:bg-blue-700` |
| 次要按钮 | `bg-white border border-gray-300 hover:bg-gray-50` |
| 危险按钮 | `bg-red-600 text-white hover:bg-red-700` |

---

## 5. 新增管理页面步骤

1. **确定目录**: 在 `02-manage/` 下选择或创建子目录（`contract/`、`performance/`、`system/`、`report/`、`common/`）
2. **选择页面类型**: 根据需求选 Type A(列表)、B(配置)、C(流程)、D(详情)
3. **创建HTML**: 使用对应模板，硬编码 mock 数据
4. **注册导航**: 在 `02-manage/index.html` 侧边栏对应分组下添加 `<a>` 标签
5. **实现交互**: 添加筛选、分页、Tab切换、弹窗等 JS 逻辑
6. **postMessage通信**: 如果需跨iframe导航，在子页面添加 `window.parent.postMessage()`

---

## 6. 相关技能

- [[project-catalog]] — 项目总目录，快速查找参考文件
- [[html-prototype-base]] — 通用基座：HTML原型框架底层（Tailwind/Font Awesome等CDN配置）
- [[html-architecture-design]] — 架构设计文档，适合了解领域模型和表结构
- [[html-client-pages]] — 客户端门户页面模式
- [[html-mobile-pages]] — 手机端页面模式