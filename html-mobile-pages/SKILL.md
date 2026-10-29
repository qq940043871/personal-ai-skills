---
name: html-mobile-pages
description: Patterns for mobile client pages (手机端). Use when creating mobile-adapted pages, touch-friendly interfaces, bottom tab navigation, or any mobile preview of the contract fulfillment system in the 04-mobile quadrant.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# 04-mobile — 手机端页面技能

> **适用目录**: `04-mobile/` 及其子目录 `pages/`、`pages/profile/`
> **整体风格**: 温暖奶油色 `#f8f6f2`，琥珀色 `#d97706` 强调，衬线字体，卡片圆角，触控优化
> **Shell**: `04-mobile/index.html` — 状态栏 + Header + iframe + 底部Tab栏

---

## 1. Shell 结构

`04-mobile/index.html` 是一个手机模拟器 Shell：

```
┌─ 状态栏 (Status Bar) ────────────┐
│  9:41                      📶🔋  │
├─ 品牌Header ─────────────────────┤
│  [🏆] 大宗商品交易   [🔔][👤]     │
├─ iframe 内容区域 ─────────────────┤
│  (加载 pages/*.html)              │
├─ 底部Tab栏 ───────────────────────┤
│  首页  合同  履约  待办  我的     │
└───────────────────────────────────┘
```

### 设计变量
```css
:root {
    --bg-deep: #f8f6f2;          /* 页面背景 - 温暖奶油色 */
    --bg-surface: #ffffff;        /* 卡片背景 */
    --bg-card: #ffffff;           /* 卡片 */
    --bg-card-hover: #faf8f5;     /* 卡片悬停 */
    --text-primary: #1c1917;      /* 主文字 - 深棕 */
    --text-secondary: #78716c;    /* 次要文字 - 暖灰 */
    --text-muted: #a8a29e;        /* 更浅文字 */
    --accent-amber: #d97706;      /* 强调色 - 琥珀 */
    --accent-orange: #ea580c;     /* 强调色 - 橙 */
    --accent-gradient: linear-gradient(135deg, #d97706, #ea580c);
    --success: #16a34a;           /* 成功 */
    --warning: #d97706;           /* 警告 */
    --danger: #dc2626;            /* 危险 */
    --border: rgba(0,0,0,0.06);   /* 边框 */
    --shadow-card: 0 2px 16px rgba(0,0,0,0.06); /* 卡片阴影 */
    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 16px;
    --radius-xl: 20px;
}
```

### 字体方案
```css
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@500;600;700;900&family=Outfit:wght@400;500;600;700&display=swap');
font-family: 'Outfit', -apple-system, 'PingFang SC', 'Noto Serif SC', sans-serif;
```
- 标题使用 `Noto Serif SC`（衬线体，增加质感）
- 正文使用 `Outfit`（现代无衬线）

### 底部Tab栏
```html
<nav class="bottom-tabs">
    <button class="tab-item active" onclick="switchTab('dashboard')">
        <i class="fas fa-home"></i>
        <span>首页</span>
    </button>
    <button class="tab-item" onclick="switchTab('contracts')">
        <i class="fas fa-file-contract"></i>
        <span>合同</span>
    </button>
    <button class="tab-item" onclick="switchTab('fulfillment')">
        <i class="fas fa-exchange-alt"></i>
        <span>履约</span>
    </button>
    <button class="tab-item" onclick="switchTab('tasks')">
        <i class="fas fa-check-circle"></i>
        <span>待办</span>
    </button>
    <button class="tab-item" onclick="switchTab('profile')">
        <i class="fas fa-user"></i>
        <span>我的</span>
    </button>
</nav>
```

### Tab切换函数
```javascript
function switchTab(tab) {
    document.querySelectorAll('.tab-item').forEach(t => t.classList.remove('active'));
    event.currentTarget.classList.add('active');
    const pages = {
        dashboard: 'pages/dashboard.html',
        contracts: 'pages/contracts.html',
        fulfillment: 'pages/fulfillment.html',
        tasks: 'pages/tasks.html',
        profile: 'pages/profile.html',
    };
    document.getElementById('pageFrame').src = pages[tab];
}
```

---

## 2. 移动端页面设计原则

### 2.1 触控优化
- 所有可点击元素最小 `44px` 高度
- 卡片使用 `active:scale-98` 微缩放反馈
- 使用 `-webkit-tap-highlight-color: transparent` 移除默认高亮
- 禁用文本选择

### 2.2 布局适配
- 内容区域固定在手机模拟器尺寸内（max-width: 480px）
- 使用 `dvh` 单位（dynamic viewport height）处理浏览器栏
- 底部安全区域适配 `env(safe-area-inset-bottom)`
- 滚动条隐藏 `::-webkit-scrollbar { width: 0; height: 0; }`

### 2.3 设计风格
- **大圆角**: `--radius-lg: 16px` 到 `--radius-xl: 20px`
- **轻阴影**: `--shadow-card: 0 2px 16px rgba(0,0,0,0.06)`
- **暖色背景**: 不使用纯白，使用 `#f8f6f2` 奶油色
- **琥珀强调**: 所有交互元素使用 `#d97706` 琥珀色
- **衬线标题**: 品牌标题使用 Noto Serif SC 衬线字体

---

## 3. 移动端页面类型详解

### 3.1 首页仪表盘 (`pages/dashboard.html`)

**紧凑指标卡片**:
```html
<div class="grid grid-cols-3 gap-3">
    <div class="stat-card">
        <div class="stat-label">合同总额</div>
        <div class="stat-value">¥12.8亿</div>
        <div class="stat-trend up">+12.5%</div>
    </div>
    <!-- 更多指标 -->
</div>
```

**快捷操作网格**:
```html
<div class="grid grid-cols-4 gap-3">
    <div class="quick-action" onclick="navigateTo('contracts')">
        <div class="icon-wrap"><i class="fas fa-file-contract"></i></div>
        <span>合同</span>
    </div>
    <div class="quick-action" onclick="navigateTo('payment')">
        <div class="icon-wrap"><i class="fas fa-credit-card"></i></div>
        <span>付款</span>
    </div>
    <!-- 更多 -->
</div>
```

### 3.2 合同列表 (`pages/contracts.html`)

**搜索+筛选组合**:
```html
<div class="search-bar">
    <i class="fas fa-search"></i>
    <input type="text" placeholder="搜索合同编号/名称..." class="search-input">
    <i class="fas fa-sliders-h filter-icon"></i>
</div>
<div class="filter-chips">
    <span class="chip active">全部</span>
    <span class="chip">进行中</span>
    <span class="chip">已完成</span>
    <span class="chip">待确认</span>
</div>
```

**合同卡片**:
```html
<div class="contract-card" onclick="openDetail('CONT-001')">
    <div class="card-header">
        <div class="contract-title">铁矿石采购合同</div>
        <span class="status-badge active">履约中</span>
    </div>
    <div class="contract-meta">
        <div class="meta-row">
            <span class="label">合同编号</span>
            <span class="value">CONT-2024-001</span>
        </div>
        <div class="meta-row">
            <span class="label">总金额</span>
            <span class="value highlight">¥ 2,500万</span>
        </div>
    </div>
    <div class="card-footer">
        <span class="mode-tag">款到发货</span>
        <span class="progress">履约进度 60%</span>
    </div>
    <div class="progress-bar"><div class="progress-fill" style="width:60%"></div></div>
</div>
```

### 3.3 履约中心 (`pages/fulfillment.html`)

**模式切换 + 动态内容**:
```html
<div class="mode-switch">
    <button class="mode-btn active" onclick="switchMode('sequential')">顺序交收</button>
    <button class="mode-btn" onclick="switchMode('free')">自由交收</button>
</div>
<div id="sequential-view">
    <!-- 顺序交收的节点时间线 -->
    <div class="timeline">
        <div class="timeline-item completed">
            <div class="timeline-dot"><i class="fas fa-check"></i></div>
            <div class="timeline-content">
                <h4>定金支付</h4>
                <p>¥ 500万 · 2024-01-15</p>
            </div>
        </div>
        <div class="timeline-item active">
            <div class="timeline-dot"></div>
            <div class="timeline-content">
                <h4>发货</h4>
                <p>待处理</p>
            </div>
        </div>
        <div class="timeline-item pending">
            <div class="timeline-dot"></div>
            <div class="timeline-content">
                <h4>收货验收</h4>
                <p>待发货完成后</p>
            </div>
        </div>
    </div>
</div>
<div id="free-view" style="display:none">
    <!-- 自由交收的三轨并行视图 -->
</div>
```

### 3.4 待办任务 (`pages/tasks.html`)

**待办卡片+滑动操作**:
```html
<div class="task-card">
    <div class="task-left">
        <div class="task-icon priority-high"><i class="fas fa-exclamation"></i></div>
        <div class="task-info">
            <h4>待办标题</h4>
            <p class="task-desc">合同 CONT-2024-001 待确认收货</p>
            <span class="task-time">2小时前</span>
        </div>
    </div>
    <div class="task-right">
        <span class="task-badge">紧急</span>
        <i class="fas fa-chevron-right"></i>
    </div>
</div>
```

### 3.5 个人中心 (`pages/profile.html`)

**用户信息 + 统计 + 功能入口**:
```html
<div class="profile-header">
    <div class="avatar">张</div>
    <div class="user-info">
        <h3>张经理</h3>
        <p>华北钢铁集团</p>
    </div>
    <i class="fas fa-qrcode"></i>
</div>
<div class="stats-row">
    <div class="stat">合同<span>28</span></div>
    <div class="stat">待办<span>5</span></div>
    <div class="stat">单据<span>142</span></div>
</div>
<div class="menu-list">
    <a href="pages/profile/payment_order.html" class="menu-item">
        <i class="fas fa-credit-card"></i><span>资金单</span><i class="fas fa-chevron-right"></i>
    </a>
    <a href="pages/profile/delivery_auth.html" class="menu-item">
        <i class="fas fa-shipping-fast"></i><span>发货授权</span><i class="fas fa-chevron-right"></i>
    </a>
    <!-- 更多菜单项 -->
</div>
```

---

## 4. 移动端核心样式模块

### 4.1 通用卡片样式
```css
.card {
    background: var(--bg-card);
    border-radius: var(--radius-lg);
    padding: 16px;
    box-shadow: var(--shadow-card);
    margin-bottom: 12px;
}
```

### 4.2 状态标签
```css
.status-badge {
    padding: 2px 10px; border-radius: 999px; font-size: 11px; font-weight: 600;
}
.status-badge.active { background: #dcfce7; color: #16a34a; }    /* 进行中 */
.status-badge.pending { background: #fef3c7; color: #d97706; }   /* 待处理 */
.status-badge.completed { background: #e0e7ff; color: #6366f1; } /* 已完成 */
.status-badge.draft { background: #f5f5f4; color: #78716c; }     /* 草稿 */
```

### 4.3 渐变按钮
```css
.btn-primary {
    background: var(--accent-gradient);
    border-radius: var(--radius-md);
    padding: 12px 24px;
    color: white;
    font-weight: 600;
    box-shadow: 0 4px 16px var(--accent-glow);
}
```

---

## 5. 个人中心子页面 (pages/profile/)

每个子页面采用统一风格：
- 顶部导航栏（返回按钮 + 标题）
- 内容区域（单据列表/详情）
- 底部操作按钮（如有）

| 文件 | 说明 | 用途 |
|------|------|------|
| `payment_order.html` | 资金单查询 | 查看资金流水 |
| `delivery_auth.html` | 发货授权 | 授权发货操作 |
| `invoice_order.html` | 发票单查询 | 查看发票状态 |
| `warehouse_receipt.html` | 仓单查询 | 查看仓单信息 |
| `refund_penalty.html` | 退款与扣罚 | 退款扣罚明细 |
| `dispute_ticket.html` | 争议工单 | 争议处理记录 |

---

## 6. 移动端特定行为

### 6.1 页面导航
```javascript
function navigateTo(page) {
    // 通过postMessage通知Shell切换Tab
    const tabMap = {
        contracts: 'contracts',
        payment: 'fulfillment',
        tasks: 'tasks',
        profile: 'profile',
    };
    if (tabMap[page]) {
        window.parent.postMessage({ type: 'switchTab', tab: tabMap[page] }, '*');
    }
}
```

### 6.2 详情页打开
```javascript
function openDetail(id) {
    window.parent.postMessage({ type: 'navigate', to: 'pages/contract-detail.html?id=' + id }, '*');
}
```

### 6.3 触控反馈
```css
.btn:active { transform: scale(0.96); transition: transform 0.1s; }
.card:active { background: var(--bg-card-hover); }
```

---

## 7. 新增移动端页面步骤

1. **创建页面文件**: 在 `04-mobile/pages/` 下创建 `.html` 文件
2. **使用设计变量**: 引用 `:root` CSS 变量保持风格一致
3. **适配Shell**: 页面在 iframe 中显示，无需额外布局
4. **注册Tab**: 如需新Tab，在 `04-mobile/index.html` 底部Tab栏添加
5. **postMessage通信**: 子页面通过 `window.parent.postMessage()` 与Shell通信
6. **触控优化**: 确保点击区域 ≥ 44px，添加 `active` 状态反馈

---

## 8. 相关技能

- [[project-catalog]] — 项目总目录，快速查找参考文件
- [[html-prototype-base]] — 通用基座：HTML原型框架底层
- [[html-client-pages]] — 客户端的桌面版本（内容对应，布局适配）
- [[html-manage-pages]] — 管理端后台页面（管理相关的功能入口）
- [[html-architecture-design]] — 架构设计文档