# HTML 原型工程规范（Prototype Engineering Spec）

> 用法：Step 4 写代码前必读。目标：单文件、零构建、双击即开、跨行业可复用。

## 目录

1. 技术栈选型与权衡
2. Design Token（CSS 变量系统）
3. 编码规范
4. Mock 数据 Schema
5. 交互模式与动效规范
6. 无障碍（a11y）
7. 性能预算
8. 浏览器兼容与降级
9. 反模式（禁止项）
10. 交付物结构

---

## 1. 技术栈选型与权衡

### 1.1 选型

| 能力 | 方案 | 版本锁定 |
|------|------|----------|
| 样式 | Tailwind CSS CDN | `cdn.tailwindcss.com`（原型专用 JIT） |
| 图标 | Font Awesome | `6.4.0`，all.min.css |
| 图表 | Chart.js | `3.9.1`，chart.min.js |
| 字体 | 系统字体栈 | 不引外部中文字体 |
| 其他 | 原生 ES5/ES6 | 不引 jQuery / Vue / React |

### 1.2 权衡说明（架构师视角）

| 维度 | 评估 |
|------|------|
| 适用场景 | 需求验证、客户演示、静态原型；**不适合直接上生产**（Tailwind CDN 在浏览器内编译，生产体积与延迟不可接受） |
| 优点 | 零安装零构建、单文件可分发、工具类产出快、样式一致性好 |
| 成本 | 强依赖外网 CDN；离线环境需把三个资源下载本地化 |
| 风险 | CDN 不可用时页面裸奔；Tailwind CDN 控制台有 production 警告（原型可忽略） |
| 替代方案 | ① 离线：下载三资源放 `assets/vendor/` 改相对路径；② 生产化：Vite + Tailwind 构建，组件迁移为 Vue/React；③ 客户禁外网：内联关键 CSS，仅保留本地资源 |

### 1.3 引用写法（放 `<head>`，顺序不可乱）

```html
<script src="https://cdn.tailwindcss.com"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
```

### 1.4 断点体系（唯一权威，不得自行发明）

**以 Tailwind Play CDN 的默认断点为准**——原型零构建，不写 `tailwind.config`，因此 `sm/md/lg/xl:` 的实际生效值就是下面这张表。文档、门禁、模板三处必须与此一致。

| 档位 | 视口宽度 | Tailwind 前缀 | 布局策略 |
|------|----------|---------------|----------|
| 手机（默认） | < 640px | 无前缀 | 单列；底部分类/筛选走抽屉；`#mobileBar` 出现 |
| 平板竖屏 | 640 – 767px | `sm:` | 两列网格；通栏次项渐次出现 |
| 平板横屏 | 768 – 1023px | `md:` | 主导航"全部分类"按钮出现；筛选行内展开 |
| PC | ≥ 1024px | `lg:` | 完整多列：Hero 三栏、产品 4–5 列、桌面筛选栏 |
| 宽屏 | ≥ 1280px | `xl:` | 仅放宽留白，容器仍以 `--container`（1200px）封顶 |

手写媒体查询只有两处，必须与上表对齐，**不要另设 576 / 992 / 1200 这类数值**（旧版曾误用，导致门禁无法验证）：

```css
/* 手机端收窄容器内边距（= 低于 sm 的区间） */
@media (max-width:639px){ .container-x{padding:0 12px;} }
/* 移动端底部操作条（= 低于 md 的区间） */
@media (max-width:767px){ body{padding-bottom:60px;} #mobileBar{display:flex;} }
@media (max-width:767px) 之外的基础规则必须写在这两条媒体查询之前（见 §3.2 响应式覆盖铁律）。
```

> **例外**：若客户强制要求 992 / 1200 断点，必须在 CDN 之后**立即**插入配置，且三个模板同步；漏插会静默回退到默认值，比不改更危险。
> ```html
> <script src="https://cdn.tailwindcss.com"></script>
> <script>tailwind.config={theme:{screens:{sm:'576px',md:'768px',lg:'992px',xl:'1200px','2xl':'1440px'}}}</script>
> ```

## 2. Design Token（CSS 变量系统）

完整变量复制到 `<style>`，**行业切换只改前 4 行 + 强调色**：

```css
:root{
  /* 品牌（按行业画像替换） */
  --primary:#1E3A5F;
  --primary-light:#E8EEF4;
  --primary-dark:#0F1D2F;
  --secondary:#FF6A00;

  /* 强调色的可读变体（由 applyTheme 依 secondary 自动计算，禁止省略） */
  --secondary-text:#A64500;      /* 白底上的小字 / 配白字的底色 */
  --secondary-on-dark:#FF9447;   /* 深色底上的小字 */

  /* 行情语义色（固定，不随主题变） */
  --price-up:#E53E3E;
  --price-down:#38A169;
  --price-flat:#999999;

  /* 功能色：组件（表单错误态）与 Toast 依赖，禁止省略 */
  --success:#52C41A; --warning:#FAAD14; --error:#F5222D;

  /* 文字 */
  --text-primary:#333333; --text-secondary:#666666;
  --text-tertiary:#999999; --text-price:#FF6600;

  /* 背景/边框 */
  --background:#F8F8F8; --border:#E8E8E8; --border-light:#F0F0F0;

  /* 阴影/圆角 */
  --shadow-sm:0 1px 3px rgba(0,0,0,.08);
  --shadow-md:0 4px 12px rgba(0,0,0,.08);
  --shadow-lg:0 8px 24px rgba(0,0,0,.12);
  --radius-sm:4px; --radius:8px;

  /* 间距 */
  --space-sm:8px; --space-md:16px; --space-lg:24px;
  --space-xl:32px; --space-2xl:48px;

  --container:1200px;
}
```

基础元素：

```css
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei","Helvetica Neue",Arial,sans-serif;background:var(--background);color:var(--text-primary);}
.container-x{max-width:var(--container);margin:0 auto;padding:0 16px;}
.card{background:#fff;border-radius:var(--radius);box-shadow:var(--shadow-sm);transition:all .2s ease;}
.card:hover{transform:translateY(-2px);box-shadow:var(--shadow-lg);}
.spec-tag{background:var(--primary-light);color:var(--primary);border-radius:var(--radius-sm);padding:2px 8px;font-size:12px;}
.t-up{color:var(--price-up);} .t-down{color:var(--price-down);} .t-flat{color:var(--price-flat);}
```

## 3. 编码规范

### 3.1 HTML

- `lang="zh-CN"`，必须有 `<title>`、viewport、charset。
- 语义化：`header / nav / main / section / aside / footer`；纯装饰才用 `div`。
- 区块注释 `<!-- 区块名 -->`，每个 section 一行注释。
- 不写废弃标签；表格仅用于规格参数表。
- **可点击元素必须是原生 `<button type="button">`**：禁止给 `span/div/i` 绑 onclick。Tailwind Preflight 已重置按钮默认样式；这样键盘可聚焦/可回车，且自动化工具能通过无障碍树定位（span 点击点在交互快照中不可见）。
- **占位导航的 `<a>` 必须带 `href`**：无 `href` 的 `<a>` 不可聚焦、Tab 不可达、无障碍树里也不是 link 角色——恰好违反上一条的理由。原型中没有真实去向的占位项按语义二选一：
  - 有明确去向但暂无页面 → 写 `href="#"`（保留可聚焦与 link 角色），点击时 `return false` 不跳转；
  - 本质是动作而非跳转（"查看更多"、"切换视图"、"清空筛选"）→ 用 `<button type="button">`。
  ⚠️ 不要只写 `<a class="cursor-pointer">` 就算完——它看起来可点，键盘与读屏都够不到。

### 3.2 CSS

- 布局用 Tailwind 工具类；主题色一律走 `var(--*)`，禁止内联写死行业色（透明黑/白除外）。
- 自定义样式集中在一个 `<style>`，按"变量 → 基础 → 组件 → 动效"顺序。
- **响应式覆盖铁律**：同一选择器的基础规则必须写在媒体查询**之前**——同优先级时后写生效，写反会导致媒体查询被基础规则覆盖（如 `#mobileBar` 移动端不显示）。
- 动效只做 transform / opacity，不做引起重排的属性动画。

### 3.3 JavaScript

- 脚本集中在 `</body>` 前；先数据（const 数组）→ 渲染函数 → 初始化调用。
- 全部列表**数据驱动渲染**，禁止复制粘贴卡片 HTML。
- 用函数声明 + `var/const`，不依赖构建；事件内联 `onclick` 可接受（原型），但同名函数全局唯一。
- 数值计算注意单位；价格展示统一 `toLocaleString()`。
- 每个交互函数必须真实有效，禁止 `onclick="javascript:;"` 空绑定。
- 命名：数据集合名词复数（products）、渲染 `renderXxx`、卡片 `xxxCard`。

## 4. Mock 数据 Schema

### 4.1 主题与平台信息

```javascript
// THEME：改这 4 个值即换行业主题（camelCase，运行时写入 CSS 变量）
var THEME = { primary:'#1E3A5F', primaryLight:'#E8EEF4', primaryDark:'#0F1D2F', secondary:'#FF6A00' };

// PLATFORM：搜索占位是「单个字符串」而非数组；字段名必须与模板一致，否则文案渲染不出来
var PLATFORM = {
  name:'钢信汇', slogan:'钢铁一站式交易平台', topSlogan:'钢厂采购 · 一手价格',
  searchBtn:'搜钢',
  placeholder:'搜索钢材牌号、规格、供应商，如 HRB400 / Φ20 / 沙钢',
  hotwords:['HRB400','镀锌板','无缝管','冷轧卷']
};
```

### 4.2 类目（导航面板 + Hero 分类）

```javascript
const categories = [
  { name:'建筑钢材', children:['螺纹钢','盘螺','高线','圆钢'] },
  { name:'板材', children:['热轧板卷','冷轧板卷','镀锌板','中厚板'] }
];
const heroCats = categories.slice(0,8).map(function(c){return c.name;});
```

### 4.3 Banner

```javascript
const banners = [
  { kicker:'钢厂直发 · 当日可提', title:'螺纹钢现货 直供', desc:'HRB400E Φ16-25mm · 理重计价', cta:'立即询价' }
];
```

### 4.4 行情

```javascript
const ticker = [
  { name:'螺纹钢 HRB400', price:4500, chg:2.0, dir:'up' },
  { name:'热卷 Q235B', price:4620, chg:-1.0, dir:'down' }
];
```
约束：`dir` ∈ up/down/flat；price 与 chg 方向必须自洽。

### 4.5 专区

```javascript
const boards = {
  purchase:[
    { type:'采购螺纹钢', spec:'HRB400E Φ20', qty:'500 吨', city:'江苏南京', note:'钢厂直提', time:'11小时前' }
  ],
  supply:[ /* 同结构 */ ]
};
```

### 4.6 产品

**首页 / 通用产品卡（短 Schema，模板 `portal-home` 用）**

```javascript
const products = [
  { icon:'fa-layer-group', title:'螺纹钢 HRB400E Φ20',
    price:'¥3,650 ~ 3,720 /吨',
    specs:['HRB400','Φ20','9m'],
    supplier:'沙钢 · 已成交 1200 笔',
    tags:['认证','直供'] }
];
```

**列表页产品（长 Schema，模板 `product-list` 用）**

排序与筛选函数**直接读下列字段**，缺一个则对应功能静默失效（排序不动 / 一点筛选就空结果）：

```javascript
const products = [
  { icon:'fa-layer-group', title:'螺纹钢 HRB400E Φ20×9m',
    category:'建筑钢材', brand:'沙钢', grade:'HRB400E', city:'上海',
    priceNum:3680,                    // 必需 · 数值：价格升降序与价格区间筛选的比较依据
    priceText:'¥3,650 ~ 3,720 /吨',   // 必需 · 字符串：展示用，含千分位
    specs:['HRB400','Φ20','理计'],
    supplier:'沙钢 · 成交1200笔',
    tags:['认证','直供'],
    sales:1200,                       // 必需 · 数值：供「成交量」排序
    daysAgo:1                         // 必需 · 数值：供「最新发布」排序
  }
];
```

硬约束：

- `category / brand / grade / city` 的取值必须与 `filterGroups[].options` **逐字一致**，否则该筛选项一点就是空结果。
- `priceNum` 必须落在 `priceText` 所写区间内，否则排序后眼见价格顺序错乱。
- 长 Schema 比短 Schema 多了 8 个字段，**从首页复制数据到列表页时必须补齐**。

字段随行业替换：矿石 specs=['TFe 61.5%','-10mm','日照港']；工业品加 `moq:'12 副'`、`contract:true`（协议价标）。

### 4.7 供应商

```javascript
const suppliers = [
  { name:'虚构集团 · 华东直营', cert:'金牌供应商', year:'成立于1990年',
    auth:'ISO9001 · 深度验厂', main:'螺纹钢 / 线材', deal:'已成交 3000 笔 · 好评 98%' }
];
```

### 4.8 全球货源网络（3D 全息地球的数据源）

```javascript
const TRADE = {
  kpi:[ { label:'在途运力', value:42.8, dec:1, unit:'万吨' } ],
  hubs:[ { name:'黑德兰港', lat:-20.3, lng:118.6, size:1.0 } ],   // size 1.0 为基准，枢纽可到 1.5
  routes:[ { from:'黑德兰港', to:'唐山港', cargo:'铁矿石 TFe61.5%',
             qty:'12.4 万吨', eta:'在途 6 天', tone:'run' } ]
};
```

- `lat / lng` 必须填**真实经纬度**，球面投影靠它定位；`size` 控制枢纽光点半径（1.0 基准，主枢纽 1.3–1.5）。
- `routes.from / to` 用 `hubs[].name` 引用；引用了不存在的 name 时该航线**静默丢弃**（画不出来且不报错），交付前核对一遍。
- `tone`：`run` 在途（强调色）/ `done` 已到港（绿）/ `wait` 待装船（灰）。**不要**用涨跌红绿语义——那是价格色，物流状态混用会误读。
- 航线沿**大圆**绘制（球面线性插值），不穿球体。产地→销地、矿口→口岸、养殖场→加工厂都适用。

### 4.9 图表

```javascript
const chartData = { labels:['09-01',/*…*/], spot:[4400,/*…*/], future:[4380,/*…*/] };
```

### 4.10 数据红线

- 公司名、人名、电话、邮箱、备案号**全部虚构**，不映射真实企业全称。
- 不出现真实账号、密钥、内部系统地址。
- 数值保持行业合理量级，不为"好看"写出 0.1 元一吨这类穿帮价。

## 5. 交互模式规范

| 模式 | 规范 |
|------|------|
| 搜索 | 回车 + 按钮双触发；空值 toast 警告；有值 toast 演示（单页原型） |
| 分类面板 | 点击"全部分类"展开/收起；再点或选其他导航收起；移动端走左侧抽屉 |
| Banner | 自动 4s 轮播 + 指示点同步；悬停不暂停（简化）；淡入淡出 500ms |
| 行情条 | 无缝循环（数据渲染两份）；位移到一半归零；纯 transform |
| Tabs | 真切换内容面板；当前项主色 + 3px 下边框 |
| 筛选 | 标签选中态 + 真过滤数组 + 已选 chip 可删；空结果有空状态 |
| 排序 | 至少价格升降真实生效 |
| 数量步进 | 步进值符合行业（钢材吨、工业品 MOQ）；不允许 0 / 负 |
| 表单 | 必填校验、错误字段红框 + 文案；成功 toast 后切状态页 |
| 弹窗 | 遮罩 / X / ESC 三种关闭方式；打开时遮罩可点击关闭 |
| Toast | 顶部居中，2.5s 自动消失；四类语义色，底色与前景色成对（见 §6 对比度表，勿用统一白字） |

### 5.1 动效层（3D / 视差 / 光效）

动效是**渐进增强层**，不是结构层。写之前先接受这条：**动效全部失效时，页面信息必须一条不少地可读。**

| 约束 | 要求 |
|------|------|
| 内容不依赖动效 | 禁止用 CSS 直接写 `opacity:0` 做进场初始态——JS 崩了就永远不显现。隐藏态由 JS 加类（`.fx-stagger` 模式），无 JS 时保持默认可见 |
| 首屏状态不依赖 CDN | 任何决定首屏正确性的状态类（轮播显隐、指示点）必须定义在**本文件自己的 `<style>`** 里。若写成 Tailwind 工具类而它只出现在 JS 字符串中，靠 CDN 版 JIT 运行时生成——一旦漏生成（已实际发生过），三张轮播会同时可见、文字叠成重影 |
| 尊重系统偏好 | 必须有 `@media (prefers-reduced-motion:reduce)` 全量降级：动画/过渡压到 0.01ms，进场元素 `opacity:1`、`transform:none`，粒子与地球画布 `display:none` |
| 离屏即暂停 | canvas 动画由 IntersectionObserver 托管，滚出视口立刻停 rAF。禁止让不可见区域持续烧 CPU |
| DPR 封顶 | canvas 后备缓冲按 `min(devicePixelRatio, 2)` 设置，不要直接乘原值 |
| 指针效果限设备 | 3D 倾斜 / 磁吸 / 区域聚光只在 `(hover: hover) and (pointer: fine)` 下启用；触屏一律跳过 |
| 只动 transform / opacity | 动画与过渡只改这两个属性，不动 `width / height / top / left` |
| 不用 `filter:blur` 做大光斑 | 这个尺寸的模糊会把合成开销推高一个量级。柔边径向渐变 + 动画 `transform` 是等效且更省的写法 |
| 不引 3D 库 | 需要 3D 时用 canvas 2D 手写投影（球面网格 + 大圆航线约 40 行三角函数），不引 three.js——与「单文件、零构建、CDN 最小化」直接冲突 |
| 强度可调 | 倾角等强度写进 data 属性：`data-tilt="6"` = 该卡最大倾角 6°（小卡 5–7，大面板 3–4） |

**推荐组合（首页已落地，密码见 component-library.md §F）**

1. **底层动效**：粒子网络（节点 + 就近连线，指针轻微斥力）+ 极光光斑（3 个不同色相、慢速漂移）+ 雷达扫描线。
2. **视差**：背景网格按 `data-parallax="-.16"` 位移，位移量按容器高度 18% 封顶，避免露边。承载视差的层要比容器外扩（`inset:-22%`）留余量。
3. **3D**：卡片指针倾斜（CSS 变量驱动，与 `.card-lift` 共存）；深色区放一颗全息地球作为视觉高潮。
4. **光效**：深色面板掠光、`conic-gradient` 流光边框（`@property` 驱动角度，不支持时退化为静态描边）、区域聚光跟随指针、滚动进度条。
5. **数字与图表**：数值 count-up 收尾带一次光晕脉冲；迷你趋势线用 `pathLength="100"` + `stroke-dashoffset` 做绘制入场。

**性能红线**：单页 canvas ≤ 2 个、常驻 rAF 循环 ≤ 2 个、滚动监听必须 `{passive:true}` 且用 rAF 节流。

## 6. 无障碍（a11y，原型也要守底线）

- 所有图标按钮必须带文字或 `title`；纯图标按钮加 `aria-label`。
- 表单控件与 `<label>` 关联（`for/id`），错误提示用 `aria-live="polite"`。
- **对比度（正文 ≥4.5:1）**：语义底色与前景色必须**成对**使用，白字只能配深底。

  | 语义 | 底色 | 前景色 | 对比度 |
  |------|------|--------|--------|
  | 成功 success | `#52C41A` | `#0B2E00` 深墨绿 | 6.60:1 |
  | 警告 warn | `#FAAD14` | `#3D2A00` 深褐 | 7.23:1 |
  | 错误 error | `#F5222D`（Toast 用 `#CF1322`） | `#FFFFFF` | 5.59:1 |
  | 信息 info | `--primary-dark`（随行业主题） | `#FFFFFF` | ≥4.5:1 |

  ⚠️ 反例：`#52C41A` 底写白字仅 **2.27:1**、`#FAAD14` 底写白字仅 **1.90:1**，均不可读。这两个底色必须配深色字。
- **强调色不得直接当文字色**：`--secondary`（默认 `#FF6A00`）对白底仅 **2.87:1**、对深色底仅 **4.0:1**，两端都不达 4.5:1。使用规则：

  | 场景 | 用哪个变量 |
  |------|-----------|
  | 白底上的小字 / 正文 | `var(--secondary-text)`（对白底 6.05:1） |
  | 深色底上的小字 | `var(--secondary-on-dark)`（对 `--primary-dark` 5.25:1） |
  | 配白字的色块（角标、标签底） | `background:var(--secondary-text)`（白字 6.05:1） |
  | 纯色块填充、≥18px 粗体 CTA、装饰性描边 | 可直接用 `var(--secondary)` |
- 浅灰辅助字不用于关键信息。
- 弹窗打开可聚焦关闭键；不依赖颜色单独传达信息（涨跌同时有箭头）。
- Tab 顺序与视觉顺序一致；不用正向 tabindex。

## 7. 性能预算

| 指标 | 预算 |
|------|------|
| HTML 单文件体积 | 门户首页 ≤ **120KB**（未 gzip）；列表 / 详情页 ≤ 60KB。实测首页 87KB → gzip 25KB。动效层（粒子 + 全息地球 + 投影计算）本身就占 ~28KB，这是有意付的代价，不是失控 |
| canvas 数量 | ≤ 2 个 / 页；常驻 rAF 循环 ≤ 2 个；离屏必须暂停 |
| 首屏渲染 | CDN 正常时 < 2s（本地打开） |
| Chart.js | 仅在有图表页引用 |
| 图片 | 原型不依赖外链图片；用渐变 + 图标占位；如必须，单图 ≤ 200KB |
| 定时器 | 页面定时器 ≤3 个；轮播/行情条/数量无关逻辑不重复 setInterval |
| 重排 | 滚动与动效只改 transform / opacity；hover 不改尺寸属性 |

## 8. 浏览器兼容与降级

- 目标：Chrome / Edge / Safari 近两年版本 + 移动端 WebKit。
- Chart.js 加载失败：图表容器显示文字"行情图表（加载失败）"，不阻塞其他脚本——脚本中判断 `typeof Chart !== 'undefined'`。
- CDN 全挂：保持灰底文字结构可用，导航与内容仍可读。
- 不用可选链 `?.` 等过新语法（目标环境含旧 WebView 时改 ES5 写法）。

## 9. 反模式（禁止项）

1. ❌ B2C 玩法：秒杀倒计时、拼团、砍一刀、直播悬浮窗、花呗式营销。
2. ❌ 娱乐化配色：荧光色、渐变彩虹、大面积紫粉。
3. ❌ 卡片只写"优质供应商"无任何指标 / 认证 / 数据。
4. ❌ 按钮全是死的，点什么都没反应。
5. ❌ 行情涨跌方向与百分比矛盾；照搬美股绿涨红跌。
6. ❌ 列表硬编码几十条卡片 HTML。
7. ❌ 引用真实企业全称、真实电话、真实备案。
8. ❌ 外链图片裂图、外链字体拖慢加载。
9. ❌ 单文件里塞多个 CSS 框架 / jQuery + 原生混用。
10. ❌ 移动端字号过小：正文与操作文案 <12px；**角标徽标可 10–11px，但不得低于 10px**，且只能承载辅助信息（认证标、来源、时间），不可承载关键信息。

## 10. 交付物结构

单页交付：

```text
【平台名】_【页面类型】.html      ← 唯一交付文件
```

多页交付（放同一目录，相对路径互跳）：

```text
project/
├── index.html          首页
├── list.html           列表页
├── detail.html         详情页
├── rfq.html            询价页
└── shop.html           店铺页（可选）
```

文件第一行不加生成器注释到可见区域；交付前自查 SKILL.md §7 质量门禁全部通过。
