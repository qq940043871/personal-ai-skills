---
name: html-client-pages
description: >-
  门户会员中心页面技能 — 生成企业客户端门户会员中心的各类页面。
  当需求涉及创建面向企业会员/客户的门户前台页面时触发，包括但不限于：
  会员工作台/首页看板、合同管理（列表/详情）、履约中心（计划/总览/详情）、
  单据中心（发货/收货/资金/发票/仓单）、结算中心、待办任务、
  异议管理、企业信息与账号设置等模块。
  也适用于：客户/会员登录后看到的门户首页、个人中心、订单查询、企业资料管理等面向终端企业用户的页面。
  触发关键词：门户、会员中心、客户端门户、客户前台、企业门户、member center、client portal、customer portal。
  不适用于：管理运营后台（走 html-manage-pages）、手机端（走 html-mobile-pages）、B2B 产业平台（走 html-b2b-portal）。
  目录：03-client/ 象限。
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# 03-client — 门户会员中心技能

> **定位**: 生成面向企业会员/客户的**门户会员中心**页面。区别于管理运营后台（02-manage），本象限所有页面以"会员视角"组织信息——"我的合同""我的待办""我的单据""我的企业"。
> **适用目录**: `03-client/` 及其子目录 `dashboard/`、`contract/`、`performance/`、`settlement/`、`document-center/`、`dispute/`、`tasks/`、`company/`
> **整体风格**: 翠绿色主题 `#059669`，品牌化（"履约宝"），卡片式UI，更注重视觉和用户体验
> **Shell**: `03-client/index.html` — Header(h-16) + Sidebar(w-60) + iframe

---

## 1. Shell 导航结构

### 侧边栏导航分组 (03-client/index.html)

```
工作台
  ├── 首页看板 → dashboard/index.html
  ├── 结算总览 → settlement/index.html
我的待办
  ├── 待办任务 → tasks/index.html (badge: 5)
  └── 已办任务 → tasks/history.html
合同管理
  ├── 合同管理 → contract/list.html
  ├── 履约管理 → performance/plan-list.html
  └── 异议管理 → dispute/index.html
我的单据
  ├── 单据中心 → document-center/index.html
  ├── 发货管理 → document-center/shipment.html
  ├── 收货结算 → document-center/receipt.html
  ├── 资金单管理 → document-center/payment.html
  ├── 发票管理 → document-center/invoice.html
  ├── 退款与扣罚单 → document-center/refund.html
  └── 我的仓单 → document-center/warehouse.html
企业中心
  ├── 企业信息 → company/profile.html
  └── 账号设置 → company/settings.html
```

### Shell 特色

- **Header品牌**: 翠绿色logo方块 + "履约宝"标题 + "企业客户端"标签(badge)
- **用户信息**: 带头像和部门信息（如"张经理 · 华北钢铁集团"）
- **侧边栏宽度**: `w-60`（比管理端的 w-64 略窄）
- **导航激活**: 左侧3px翠绿色边框

---

## 2. 客户端特有页面类型

### 2.1 首页看板 (`dashboard/index.html`)

与后台仪表盘不同，客户端看板更注重"我的"视角：

**布局结构**:
```
┌─ 欢迎区 ────────────────────────┐
│  "早上好，张经理" + 日期 + 通知   │
├─ 核心指标行 ─────────────────────┤
│  合同总额 | 待处理 | 履约中 | 单据  │
├─ 待办 + 快捷操作 ────────────────┤
│  [待办列表]        [快捷操作网格]  │
├─ 最近动态 ───────────────────────┤
│  活动时间线                         │
└───────────────────────────────────┘
```

**待办任务卡片**:
```html
<div class="bg-white rounded-lg shadow-sm border border-gray-100 p-4 hover:shadow-md transition-shadow">
    <div class="flex items-start">
        <div class="w-2 h-2 rounded-full bg-red-500 mt-2 mr-3 flex-shrink-0"></div>
        <div class="flex-1">
            <div class="flex justify-between">
                <h4 class="text-sm font-medium text-gray-800">待办标题</h4>
                <span class="text-xs text-gray-400">2小时前</span>
            </div>
            <p class="text-xs text-gray-500 mt-1">合同编号: CONT-2024-001</p>
            <div class="flex space-x-2 mt-2">
                <button class="px-2 py-1 text-xs bg-emerald-500 text-white rounded">处理</button>
                <button class="px-2 py-1 text-xs border rounded text-gray-600">稍后</button>
            </div>
        </div>
    </div>
</div>
```

### 2.2 合同列表 (`contract/list.html`) — 卡片式网格

客户端合同列表使用 **卡片式网格** 而非表格，更直观：

```html
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
    <div class="bg-white rounded-lg border border-gray-200 hover:shadow-md transition-shadow p-5 cursor-pointer">
        <div class="flex justify-between items-start mb-3">
            <div>
                <h3 class="font-semibold text-gray-900">合同标题</h3>
                <p class="text-xs text-gray-500 mt-0.5">CONT-2024-001</p>
            </div>
            <span class="px-2 py-0.5 text-xs rounded-full bg-green-100 text-green-700 font-medium">履约中</span>
        </div>
        <div class="grid grid-cols-2 gap-3 text-sm">
            <div>
                <span class="text-gray-400 text-xs">买方</span>
                <p class="text-gray-700">华北钢铁</p>
            </div>
            <div>
                <span class="text-gray-400 text-xs">卖方</span>
                <p class="text-gray-700">澳洲矿业</p>
            </div>
            <div>
                <span class="text-gray-400 text-xs">数量</span>
                <p class="text-gray-700">50,000 吨</p>
            </div>
            <div>
                <span class="text-gray-400 text-xs">总金额</span>
                <p class="text-gray-700 font-medium">¥ 2,500万</p>
            </div>
        </div>
        <div class="mt-3 pt-3 border-t border-gray-100">
            <span class="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded">款到发货</span>
        </div>
    </div>
    <!-- 更多卡片 -->
</div>
```

**筛选条使用 Chips（标签）**:
```html
<div class="flex flex-wrap gap-2 mb-4">
    <button class="px-3 py-1.5 text-sm rounded-full bg-emerald-500 text-white">全部</button>
    <button class="px-3 py-1.5 text-sm rounded-full bg-white border text-gray-600 hover:bg-gray-50">进行中</button>
    <button class="px-3 py-1.5 text-sm rounded-full bg-white border text-gray-600 hover:bg-gray-50">已完成</button>
    <button class="px-3 py-1.5 text-sm rounded-full bg-white border text-gray-600 hover:bg-gray-50">待确认</button>
</div>
```

### 2.3 合同详情 (`contract/detail.html`)

布局：信息分组 + 交收模式标签 + 履约计划

**交收模式标签**:
```html
<span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium
    {mode === 'payment_first' ? 'bg-blue-100 text-blue-700' : ''}
    {mode === 'arrival_payment' ? 'bg-green-100 text-green-700' : ''}
    {mode === 'deposit_balance' ? 'bg-purple-100 text-purple-700' : ''}
    {mode === 'installment' ? 'bg-orange-100 text-orange-700' : ''}
    {mode === 'letter_credit' ? 'bg-red-100 text-red-700' : ''}">
    <i class="fas fa-tag mr-1"></i>模式名称
</span>
```

### 2.4 履约中心 — 核心页面

履约中心是客户端最复杂的页面集合，包含三个核心页面:

#### a) 创建履约计划 (`performance/plan.html`)
- **流程**: 选择合同 → 选择交收模式(5种) → 动态渲染节点时间线 → 选择结算渠道 → 保存
- **交收模式选择器**:
```html
<div class="grid grid-cols-1 md:grid-cols-5 gap-3">
    <div class="mode-card border-2 border-gray-200 rounded-lg p-4 cursor-pointer hover:border-emerald-300 text-center"
         onclick="selectMode(this, 'payment_first')">
        <i class="fas fa-credit-card text-2xl text-gray-400 mb-2"></i>
        <h4 class="font-medium text-sm">款到发货</h4>
        <p class="text-xs text-gray-500 mt-1">先付款后发货</p>
    </div>
    <!-- 其余4种模式类似 -->
</div>
```

#### b) 履约总览 (`performance/center.html`)
- **双模式切换**: "组织履约"（里程碑时间线） vs "自由交收"（三轨并行：资金/货物/发票）
- **切换标签**:
```html
<div class="flex bg-gray-100 rounded-lg p-1 mb-6">
    <button class="flex-1 px-4 py-2 text-sm rounded-md bg-white shadow-sm font-medium" onclick="switchView('org')">
        <i class="fas fa-sitemap mr-1"></i>组织履约
    </button>
    <button class="flex-1 px-4 py-2 text-sm rounded-md text-gray-600 hover:text-gray-800" onclick="switchView('free')">
        <i class="fas fa-random mr-1"></i>自由交收
    </button>
</div>
```

#### c) 履约详情 (`performance/detail.html`)
- 根据5种交收模式动态展示不同节点流程
- 线上/线下资金流转对比
- 结算渠道适配信息

### 2.5 单据中心 (`document-center/`)

客户端特有的功能模块，每个单据类型一个页面：

- `index.html` — 单据中心导航总览（9宫格/列表）
- 各单据页面统一风格：标题+状态+明细表格+操作

**装运单卡片示例**:
```html
<div class="bg-white rounded-lg border border-gray-200 p-4">
    <div class="flex justify-between items-start">
        <div>
            <span class="text-xs text-gray-400">SHIP-2024-001</span>
            <h4 class="font-medium">铁矿石 50,000吨 装运单</h4>
        </div>
        <span class="px-2 py-0.5 text-xs rounded-full bg-yellow-100 text-yellow-700">待确认</span>
    </div>
    <div class="grid grid-cols-3 gap-4 mt-3 text-sm">
        <div><span class="text-gray-400 text-xs">发货方</span><p class="text-gray-700">澳洲矿业</p></div>
        <div><span class="text-gray-400 text-xs">起运港</span><p class="text-gray-700">黑德兰港</p></div>
        <div><span class="text-gray-400 text-xs">预计到港</span><p class="text-gray-700">2024-03-15</p></div>
    </div>
</div>
```

### 2.6 结算中心 (`settlement/index.html`)

资金结算总览：
- 结算汇总统计卡片
- 结算单列表
- 资金池余额

---

## 3. 客户端与后台的风络差异

| 维度 | 管理端 (02-manage) | 客户端 (03-client) |
|------|-------------------|-------------------|
| 主色 | 蓝色 `#3B82F6` | 翠绿 `#059669` |
| 列表风格 | 数据表格 (table) | 卡片网格 (card grid) |
| 筛选方式 | 表单式筛选栏 | Chips标签 + 搜索框 |
| 用户视角 | 管理员/运营 | 企业用户/"我的" |
| 侧边栏宽度 | w-64 | w-60 |
| 品牌感 | 弱 (通用后台) | 强 ("履约宝") |
| 操作密度 | 高 (批量操作) | 低 (单条处理) |

---

## 4. 客户端配色约定

| 用途 | Tailwind类 |
|------|-----------|
| 主色 | `bg-emerald-500`, `text-emerald-600` |
| 主色浅色 | `bg-emerald-50`, `text-emerald-700` |
| Header图标 | `bg-emerald-500 text-white` |
| 导航激活 | 左侧3px `border-emerald-500` |
| 按钮主 | `bg-emerald-500 text-white hover:bg-emerald-600` |
| 品牌标签 | `bg-emerald-100 text-emerald-700` |

---

## 5. 新增客户端页面步骤

1. **确定功能归属目录**: `dashboard/`、`contract/`、`performance/`、`settlement/`、`document-center/`、`dispute/`、`tasks/`、`company/`
2. **选择页面风格**: 卡片网格(列表)、详情Tab、流程向导、或总览看板
3. **创建HTML**: 使用翠绿色主题，mock数据
4. **注册导航**: 在 `03-client/index.html` 侧边栏添加导航项
5. **确保iframe兼容**: 使用相对路径，支持 `postMessage` 导航

---

## 6. 相关技能

- [[project-catalog]] — 项目总目录，快速查找参考文件
- [[html-prototype-base]] — 通用基座：HTML原型框架底层
- [[html-manage-pages]] — 管理端后台页面（数据模型相同，UI风格不同）
- [[html-mobile-pages]] — 手机端页面（相同功能域的移动适配）
- [[html-architecture-design]] — 架构设计文档，用于了解领域模型