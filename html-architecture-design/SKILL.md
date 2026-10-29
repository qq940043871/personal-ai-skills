---
name: html-architecture-design
description: Patterns and conventions for architecture/design documentation pages. Use when creating system design docs, architecture diagrams, scenario analysis, or domain modeling pages in the 01-design quadrant.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# 01-design — 架构设计文档技能

> **适用目录**: `01-design/` 及其子目录 `architecture/`、`scenarios/`、`documents/`
> **整体风格**: 文档型页面，以内容可读性为核心，图文并茂

---

## 1. Shell 结构

`01-design/index.html` 是文档系统的 Shell，与管理端相同模式：
- **Header** (h-16): 白色背景，`fa-file-contract` 图标，标题"系统介绍"
- **侧边栏** (w-64): 可折叠分组（文档总览、架构设计、业务场景、发展路线）
- **主区域**: `<iframe id="mainFrame">` 加载各文档页面

**导航加载函数**:
```javascript
function loadPage(page) {
    document.getElementById('mainFrame').src = page;
    document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active-nav'));
    if (event && event.currentTarget) event.currentTarget.classList.add('active-nav');
}
```

---

## 2. 设计文档的页面模式

### 2.1 文档页通用布局

设计文档采用 **内容优先** 布局，与功能页面不同：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>文档标题</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        /* 文档页特有样式 */
        .doc-content { max-width: 1200px; margin: 0 auto; }
        .doc-section { margin-bottom: 2.5rem; }
        .doc-section h2 { font-size: 1.5rem; font-weight: 700; color: #1e293b; margin-bottom: 1rem; padding-bottom: 0.5rem; border-bottom: 2px solid #e2e8f0; }
        .doc-section h3 { font-size: 1.25rem; font-weight: 600; color: #334155; margin: 1.5rem 0 0.75rem; }
        .doc-section h4 { font-size: 1.05rem; font-weight: 600; color: #475569; margin: 1rem 0 0.5rem; }
        .doc-card { background: white; border-radius: 0.75rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); padding: 1.5rem; margin-bottom: 1.5rem; }
        .diagram-box { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 0.5rem; padding: 2rem; margin: 1rem 0; text-align: center; }
        .tag { display: inline-block; padding: 0.125rem 0.5rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; }
        .tag-blue { background: #dbeafe; color: #1d4ed8; }
        .tag-green { background: #d1fae5; color: #059669; }
        .tag-purple { background: #ede9fe; color: #7c3aed; }
        .tag-orange { background: #ffedd5; color: #c2410c; }
    </style>
</head>
<body class="bg-gray-50">
    <div class="p-6">
        <div class="doc-content">
            <!-- 页面标题 -->
            <div class="mb-8">
                <h1 class="text-2xl font-bold text-gray-900">文档主标题</h1>
                <p class="text-gray-500 mt-2">文档副标题/描述</p>
            </div>
            <!-- 内容章节 -->
            <div class="doc-section">
                <h2>1. 章节标题</h2>
                <div class="doc-card">
                    <!-- 内容 -->
                </div>
            </div>
        </div>
    </div>
</body>
</html>
```

### 2.2 图表和示意图

使用纯 HTML+CSS 绘制图表，不使用 Canvas/SVG 库：

**流程图**: 使用 `flex` + 箭头符号 (`→` / `➤`) + 卡片
```html
<div class="flex items-center justify-center gap-4 flex-wrap">
    <div class="bg-blue-100 text-blue-800 px-4 py-2 rounded-lg font-medium">状态A</div>
    <i class="fas fa-arrow-right text-gray-400"></i>
    <div class="bg-green-100 text-green-800 px-4 py-2 rounded-lg font-medium">状态B</div>
    <i class="fas fa-arrow-right text-gray-400"></i>
    <div class="bg-yellow-100 text-yellow-800 px-4 py-2 rounded-lg font-medium">状态C</div>
</div>
```

**分层架构图**: 使用堆叠卡片
```html
<div class="space-y-2 max-w-xl mx-auto">
    <div class="bg-blue-50 border-2 border-blue-200 rounded-lg p-4 text-center text-blue-800 font-medium">应用层</div>
    <div class="bg-green-50 border-2 border-green-200 rounded-lg p-4 text-center text-green-800 font-medium">领域层</div>
    <div class="bg-purple-50 border-2 border-purple-200 rounded-lg p-4 text-center text-purple-800 font-medium">基础设施层</div>
</div>
```

**表格式设计**: 设计文档中的表结构
```html
<div class="overflow-x-auto">
    <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
            <tr>
                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">字段名</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">类型</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">说明</th>
            </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
            <tr class="hover:bg-gray-50">
                <td class="px-4 py-3 text-sm font-mono text-blue-600">field_name</td>
                <td class="px-4 py-3 text-sm text-gray-600">varchar(100)</td>
                <td class="px-4 py-3 text-sm text-gray-500">字段说明</td>
            </tr>
        </tbody>
    </table>
</div>
```

### 2.3 状态机图

使用表格 + 状态标签表示状态迁移：
```html
<div class="doc-card">
    <h3 class="text-lg font-semibold mb-4">状态迁移表</h3>
    <table class="min-w-full">
        <thead>
            <tr class="border-b">
                <th class="text-left py-2 px-3 text-sm font-medium text-gray-500">当前状态</th>
                <th class="text-left py-2 px-3 text-sm font-medium text-gray-500">事件</th>
                <th class="text-left py-2 px-3 text-sm font-medium text-gray-500">下一状态</th>
                <th class="text-left py-2 px-3 text-sm font-medium text-gray-500">条件</th>
            </tr>
        </thead>
        <tbody>
            <tr class="border-b hover:bg-gray-50">
                <td class="py-2 px-3"><span class="tag tag-blue">待付款</span></td>
                <td class="py-2 px-3 text-gray-600">支付成功</td>
                <td class="py-2 px-3"><span class="tag tag-green">已付款</span></td>
                <td class="py-2 px-3 text-gray-500">金额匹配</td>
            </tr>
        </tbody>
    </table>
</div>
```

### 2.4 架构说明

使用 `grid` 布局排列架构组件卡片：
```html
<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
    <div class="doc-card border-l-4 border-blue-500">
        <h4 class="font-semibold text-gray-800"><i class="fas fa-cube text-blue-500 mr-2"></i>组件名称</h4>
        <p class="text-sm text-gray-600 mt-2">组件说明</p>
        <div class="mt-3 text-xs text-gray-400">职责: ...</div>
    </div>
    <!-- 更多组件卡片 -->
</div>
```

---

## 3. 典型文档内容类型

| 类型 | 特点 | 示例文件 |
|------|------|---------|
| **架构总览** | 四色架构图、分层说明、核心概念 | `overview.html` |
| **引擎设计** | 双轨对比、流程图、组件交互 | `dual-track-engine.html` |
| **状态机** | 状态迁移表、事件列表、伪代码 | `fulfillment-state-machine.html` |
| **资金核算** | 资金池模型、核销流程、会计分录 | `fund-accounting.html` |
| **场景分析** | 表格对比、优劣分析、适用条件 | `fulfillment-workflow-modes.html` |
| **表结构** | 字段定义表、ER关系、索引说明 | `system-design-with-tables.html` |
| **路线图** | 时间线、版本规划、里程碑 | `roadmap.html` |

---

## 4. 配色约定

设计文档使用扩展色系，与功能页面区分：

| 用途 | 色值 | Tailwind |
|------|------|----------|
| 架构层-蓝色 | `#dbeafe` / `#1d4ed8` | blue-100/blue-700 |
| 领域层-绿色 | `#d1fae5` / `#059669` | emerald-100/emerald-600 |
| 基础设施-紫色 | `#ede9fe` / `#7c3aed` | violet-100/violet-600 |
| 事件流-橙色 | `#ffedd5` / `#c2410c` | orange-100/orange-700 |
| 高亮边框 | 各组件主色的左4pxborder | `border-l-4 border-{color}-500` |

---

## 5. 新增文档页面步骤

1. 在 `01-design/architecture/` 或 `01-design/scenarios/` 下创建 `.html` 文件
2. 使用文档页通用布局
3. 编写内容章节（每个章节一个 `doc-section`）
4. 在 `01-design/index.html` 的侧边栏相应分组下添加导航项
5. 如果是关联文档，在页面内添加"相关文档"章节引用其他页面

---

## 6. 相关技能

- [[project-catalog]] — 项目总目录参考
- [[html-prototype-base]] — 通用基座：HTML原型框架底层技能