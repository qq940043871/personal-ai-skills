---
name: visual-diagram-suite
display_name: 架构图工具箱（多图型）
display_name_en: Architecture Diagram Suite
description: "架构师画图总入口：先按「你要表达什么」选图型，再从 5 类高频骨架里复制一份改内容，最后用统一脚本导出 2× 高清 PNG 供 Word / PPT 引用。覆盖时序图 / 调用链路、组件依赖图（C4 Container）、部署拓扑图（区域-可用区-实例）、状态机图、管道 / 流水线流程图，含连线自动路由引擎与已定义好的配色类。当用户说「画时序图」「画组件图」「画依赖关系图」「画部署拓扑图」「画状态机」「画管道流程图」「画流水线图」「画调用链路图」「架构图工具箱」「这类图怎么画」时使用。触发词：时序图、顺序图、调用链路、组件图、依赖图、服务依赖、C4、部署拓扑、部署图、容灾拓扑、状态机、状态流转、管道图、管道流程图、流程图、流水线、pipeline、数据管道、阶段图、架构图、画图选型。"
description_zh: 按图型选型 → 复制骨架 → 自动连线 → 导 2× PNG 的一条龙画图技能；含时序图 / 组件依赖图 / 部署拓扑图 / 状态机图 / 管道流程图五类骨架与通用导出器。
description_en: A one-stop architecture-diagram toolkit for architects — pick the diagram type, copy a skeleton, declare topology only, and export 2× print-ready PNG via headless Chrome.
category: Design Tools
version: 0.1.0
author: hasWhere
tags: ["架构图", "时序图", "组件图", "部署拓扑", "状态机", "流程图", "管道图", "HTML", "单文件", "Playwright", "高清导出", "技术方案"]
permissions:
  - file_read
  - file_write
permission_notes_zh: 本 Skill 会在用户指定的项目目录读取骨架 HTML、写入改造后的单文件 HTML，并调用本机无头 Chrome 导出 PNG。图内样式与字体全部内联，导出环节不访问网络，无外部 CDN 依赖。
---

# 架构图工具箱（多图型）

## 这个技能解决什么

架构师日常画的图**不止一种**。这个技能把三件事装在一起：

1. **选型**：给一张"你要表达什么 → 该画哪种图"的决策表；
2. **骨架**：5 类高频图型的可直接复制 HTML（改内容 + 声明拓扑，坐标全自动）；
3. **管线**：一个通用导出脚本（2× 高清 + 连线数核对 + 尺寸联动提示）。

---

## 第一步：选图型（先看这张表，别急着画）

| 你要表达什么 | 用哪个 | 图型特征 |
|---|---|---|
| 系统分几层、每层有什么 | `visual-arch-diagram` | 层带 + 卡片网格，**上下分层、无连线** |
| **一条流水线的阶段推进** | **本技能 · `pipeline-flow.html`** | 阶段列 + 连线拓扑 |
| **谁在什么时候跟谁交互** | **本技能 · `seq-diagram.html`** | 参与者 + 生命线 + 消息箭头 |
| **有哪些服务、谁依赖谁** | **本技能 · `component-deps.html`** | 分区 + 组件卡 + 依赖箭头 |
| **东西部署在哪、怎么容灾** | **本技能 · `deploy-topology.html`** | 区域 / 可用区 / 实例三层嵌套 |
| **一个对象的状态怎么流转** | **本技能 · `state-machine.html`** | 状态 + 转移 + 事件标签 |
| 只在聊天里示意一下 | `mermaid-diagram` | 快，但样式不可控 |

**判断口诀**：
- 「有没有**时间顺序**」→ 有 → **时序图**。
- 「一条流水线**从 A 推进到 B**」→ **管道流程图**。
- 「表达的是一堆东西的**静态关系**」→ 有连线 → **组件图**；落到机器/机房 → **部署拓扑图**。
- 「同一个东西在不同**状态**间跳转」→ **状态机图**。
- **要进正式文档（方案 / 标书 / 评审）→ 用本技能或姊妹技能；只求快 → mermaid。**

### 与姊妹技能的关系

本技能是**总入口**，但不抢姊妹技能的活：

- 分层架构图 → `visual-arch-diagram`（它是**静态网格**，排完就完事，压根没有线）
- 旧位图（截图 / PNG）要还原成可编辑 HTML → 用 `visual-arch-diagram` 的 `restore_bitmap.py` 切出栏目边界，再按本技能对应骨架重画
- 本技能 → **其余 5 类图型**（时序 / 组件依赖 / 部署拓扑 / 状态机 / **管道流程图**）+ 选型决策 + 通用导出器

**管道流程图曾经是独立技能，现已并入本技能**（骨架 `assets/pipeline-flow.html`、同一个导出器）。两类图技术上最大的分水岭是：管道图是**动态拓扑**（连线必须跟着节点位置走），而架构图是静态网格。

两者共用同一套视觉令牌（`--ink` / `--line` / `c-*` / `k-*` 配色），混用也不会串味。**画布统一 1740px → 2× 导出 3720px。**

---

## 第二步：复制骨架改内容

```bash
# 1. 选一个骨架复制走
cp <skill>/assets/pipeline-flow.html     ./我的流程图.html
cp <skill>/assets/seq-diagram.html       ./我的时序图.html
cp <skill>/assets/component-deps.html    ./我的组件图.html
cp <skill>/assets/deploy-topology.html   ./我的部署拓扑图.html
cp <skill>/assets/state-machine.html     ./我的状态机.html

# 2. 导出 2× 高清 PNG（自动等连线引擎、核对连线数量、比对新旧尺寸）
python <skill>/scripts/export_png.py 我的流程图.html

# 3. 目视校验（裁剪改动区域，见「质量校验」）
```

浏览器双击 HTML 也能看，但**交付必须走脚本导出**（保证 2× 与尺寸可复现）。

### 技能文件清单

| 文件 | 用途 |
|---|---|
| `assets/pipeline-flow.html` | 管道流程图骨架：5 阶段 12 节点示例，含自动连线引擎（五种边）与节点配色类 |
| `assets/seq-diagram.html` | 时序图骨架：5 参与者 / 8 消息示例，生命线与消息宽度自动计算 |
| `assets/component-deps.html` | 组件依赖图骨架：3 分区 / 10 组件 / 12 依赖，含肘形路由 + 绕行通道 |
| `assets/deploy-topology.html` | 部署拓扑图骨架：两地三中心，区域/可用区/实例三层，曲线路由 |
| `assets/state-machine.html` | 状态机图骨架：委托指令 10 状态 / 10 转移，出边锚点自动均分 |
| `assets/suite-preview.png` | 四张骨架的导出效果拼图（给用户看效果用） |
| `assets/pipeline-flow.png` | 管道流程图骨架导出预览，给用户看效果用；**改过骨架后请重导覆盖** |
| `scripts/export_png.py` | 通用导出器：等就绪标记、核对 `edges` vs `drawn`、尺寸联动提示、支持批量 |

下文 `<skill>` 指本技能安装目录，如 `~/.workbuddy/skills/visual-diagram-suite/`。

---

## 各骨架改法（改哪几行）

共同点：**内容写在 HTML 里，拓扑写在底部 JS 数组里，坐标一律不手写。**

### 管道流程图 `pipeline-flow.html`

```
.sheet (1740px 白卡)
├─ .hd                头部：h1 + .sub 副标题（关键数字加粗）+ .legend 图例
├─ .flow              流程主区（flex 横向排列，position:relative）
│   ├─ .col.col-io    输入 / 输出端点列（胶囊虚线卡）
│   ├─ .col           阶段列 = .stage-head（编号 + 阶段名）+ N 个 .node
│   ├─ .node          节点卡：h4 标题 + .nt 技术/角色 + .nd 要点
│   └─ svg.edges      连线画布（绝对定位覆盖 .flow，path 由脚本填充）
└─ .notes             页脚注（编号 ①②③）
```

```js
var EDGES = [
  { from: 'src', to: 's1a', kind: 'main' },
  { from: 's2b', to: 's3b', kind: 'async', label: '异步派发' },
  { from: 's4b', to: 's3a', kind: 'back',  label: '驳回重生成' }
];
```

- `from` / `to` 填节点的 `data-node` 值，`label` 可省。**增删节点后只需改这个数组，连线自动重排。**
- 节点卡必须有 `data-node="唯一id"` + `k-*` 配色类。
- **同一个 `.col` 内的节点用同一个 `k-*` 类**——颜色表达"属于哪个阶段"，不是"节点是什么类型"。混用会让读者以为颜色有别的含义。
- 阶段主色按流程推进取色相递进（蓝 → 紫 → 青 → 金 → 珊瑚）；输入/输出端点统一灰色 `k-grey`，表达"这是边界，不是处理环节"。

**列布局要点**：

| 类 | 宽度 | 说明 |
|---|---|---|
| `.col` | `flex:1 1 0` 等分 | 阶段列，加列不用改任何数值 |
| `.col-io` | `flex:0 0 136px` | 输入/输出端点，窄；卡片用 `.node.n-io` 变胶囊虚线 |
| `.stage-head` | 高 30px | 阶段表头；输入输出列用 `.stage-head.io` |

**阶段数建议**：4–6 个是甜点。超过 7 个阶段，列宽会被压到 200px 以下、文字开始频繁换行，此时应该拆成两张图（或把两三个阶段合并成一个 `.col`，内部用多个 `.node` 表达）。

#### 五种边类型

| kind | 外观 | 语义 |
|---|---|---|
| `main` | 实线蓝 `#2C6FBE` | 主流程（默认） |
| `seq` | 细实线灰 `#9AA3AF` | 同一阶段内相邻节点的顺序 |
| `async` | 虚线青 `#2E9E8F` | 异步派发 / 事件驱动 |
| `fail` | 虚线红 `#C0504D` | 异常分支 / 失败重试 |
| `back` | 虚线橙 `#C2803A` | 回退 / 驳回重做 |

#### 路由规则（自动，不用管）

| 相对位置 | 走法 |
|---|---|
| **跨列**（x 区间不重叠） | 三次贝塞尔：起点右/左中点 → 终点左/右中点。同一节点发出的多条线**自然张开成 Y 形**，无需特殊处理 |
| **同列**（x 区间重叠） | 肘形折线，圆角倒圆，从底边中点出发 / 顶边中点进入 |
| **回退**（`back`） | 起终点都走**卡片侧边**，中间走最底部公共通道；多条回退线依次错开 22px |

所有折角用二次贝塞尔倒圆（`roundPath()`，半径 10–12px）。表注（label）在**所有线画完之后**统一追加，用 `path.getPointAtLength(len * 0.46)` 取路径中偏起点的位置——不能画完一条就标一条，否则后面的线会压住前面的字。文字用 `paint-order:stroke` + 白色描边「挖空」背景。

**图例只列实际用到的边类型**——不画就别列，装饰性图例只会稀释信息量。

### 时序图 `seq-diagram.html`

```html
<div class="acts">
  <div class="actor c-sky"><div class="an">C/S 客户端</div><div class="at">交易员终端</div></div>
  ...
</div>
<div class="track">
  <div class="msg m-sync" data-a="1" data-b="2"><div class="bar"><span class="mlbl">① 报单请求</span></div></div>
  ...
</div>
```

- `.actor` 顺序即列序，`c-*` 给配色。
- `.msg` 的 `data-a` / `data-b` = 参与者序号（从 1 起），**自上而下即时间顺序**。
- 消息色调：`m-sync` 蓝（同步）· `m-ret` 灰虚（返回）· `m-async` 青虚（异步）· `m-fail` 红虚（失败）。
- 箭头方向按 `data-a` / `data-b` 大小自动翻转，`a > b` 时箭头朝左。
- 序号 ①②③ 写在标签文本里（不用 JS 生成，方便手改）。

### 组件依赖图 `component-deps.html`

```js
var DEPS = [
  { from: 'client', to: 'gw',    kind: 'sync',  label: 'HTTP' },
  { from: 'trade',  to: 'quote', kind: 'async', label: '行情订阅' }
];
```

- 卡片必须有 `data-cid="唯一id"` + `c-*` 配色类。
- `kind`：`sync` 实线蓝 / `async` 虚线青 / `dep` 点线灰。
- 可选的 `side: ['b','t']` 强制指定出/进边（默认自动判）。

### 部署拓扑图 `deploy-topology.html`

`LINKS` 数组同上；嵌套层级是 `.region > .azs > .az > .row > .inst`。
**监控 / 日志 / 审计这类横切能力不要逐条连线** —— 每个节点连一根会把图彻底糊掉，改在页脚注里声明「各节点统一接入」。

### 状态机图 `state-machine.html`

```js
var TRANS = [
  { from: 'submitted', to: 'rejected', on: '柜台拒单', side: ['b','t'], kind: 'err' },
  { from: 'failed',    to: 'pending',  on: '复核重试', side: ['r','b'], kind: 'end' }
];
```

- 网格固定 6 列，用 `<div class="cell-empty"></div>` 占位断行。
- `kind`：`ok` 实线蓝 / `err` 实线红 / `end` 虚线灰。
- 起始状态用 `.st.st-init`（实心圆），终态加 `.st-final`（双线边框）。
- **同一状态同一侧有多条出边时，锚点自动均分**，不用手工调坐标。

---

## 统一视觉令牌

五类骨架共用同一份 `<style>` 头部，改配色只改这一处：

```css
:root{
  --ink:#1F2937; --ink2:#4B5563; --ink3:#8A93A0;   /* 三级文字 */
  --line:#E3E7EE; --paper:#FFFFFF; --canvas:#F1F4F9;
}
body{
  font-family:"Microsoft YaHei","PingFang SC","Hiragino Sans GB",
              "Source Han Sans SC","Noto Sans CJK SC",sans-serif;
}
.sheet{ width:1740px; margin:0 auto; background:var(--paper);
        border-radius:16px; padding:30px 30px 22px;
        box-shadow:0 10px 34px rgba(23,42,77,.10), 0 2px 8px rgba(23,42,77,.05); }
```

**画布宽 1740px（设计值）→ 2× 导出 3720px**，五张骨架与 `visual-arch-diagram` **全部一致**。

### 配色类（9 个，必须全部有定义）

| 图型 | 前缀 | 类名 |
|---|---|---|
| 时序 / 组件 / 部署 / 状态机 | `c-` | `c-blue` `c-teal` `c-purple` `c-amber` `c-coral` `c-gold` `c-sky` `c-red` `c-grey` |
| **管道流程图** | `k-` | `k-blue` `k-teal` `k-purple` `k-amber` `k-coral` `k-gold` `k-sky` `k-red` `k-grey` |

```css
.c-blue  {--c:#2C6FBE; --cbg:#F3F8FE;}   .c-teal  {--c:#2E9E8F; --cbg:#F1FAF8;}
.c-purple{--c:#7C5CBF; --cbg:#F8F5FE;}   .c-amber {--c:#C98A1F; --cbg:#FEFAF0;}
.c-coral {--c:#D16B65; --cbg:#FEF7F6;}   .c-gold  {--c:#C2803A; --cbg:#FDF8F0;}
.c-sky   {--c:#4AA3D8; --cbg:#F2F9FD;}   .c-red   {--c:#C0504D; --cbg:#FDF3F2;}
.c-grey  {--c:#8A93A0; --cbg:#F7F8FA;}
```

> **漏定义 = 静默失效**：卡片靠 `var(--c)` / `var(--cbg)` 取边框与底色，类没定义时**整条声明失效**，卡片退化成"没边框没底色的一块文字"，**浏览器一个警告都不给**。骨架已全部预置，自己加色时务必同步加定义。
>
> ```bash
> # 自查：引用到但没定义的配色类（输出为空 = 通过）；同时覆盖 c-* 与 k-*
> comm -23 <(grep -oE 'class="[^"]*[ck]-[a-z]+' 图.html | grep -oE '[ck]-[a-z]+$' | sort -u) \
>          <(grep -oE '^\.[ck]-[a-z]+' 图.html | sed 's/^\.//' | sort -u)
> ```

---

## 导出与质量校验

```bash
python <skill>/scripts/export_png.py 图.html [输出.png] [--width 1860] [--scale 2] [--strict]
python <skill>/scripts/export_png.py a.html b.html c.html --outdir ./png     # 批量
```

脚本会依次报告：`console errors`（**必须为空**）、图形类型 / 节点数 / **声明连线数 vs 实际绘制数**、导出尺寸与旧尺寸对比。

> 五张骨架默认视口宽都是 **1860**（= 1740 画布 + 左右 padding）→ 导出 **3720px**，无需为某张图单独调 `--width`。

### 四查（缺一不可）

1. **查 console**：必须 `[]`。骨架脚本一旦报错，连线会静默画不出来。
2. **查连线数**：`edges`（数组长度）必须等于 `drawn`（实际画出的 path 数）。
   **少画一条线图照样能看，肉眼极难发现** —— 这是本类图最容易埋的雷，所以把它做成了脚本里的自动断言（`--strict` 时不一致即失败退出）。
   > 对不上基本都是 `data-node` / `data-cid` / `from` / `to` 拼写错了。
3. **查线长**：**可见线长 < 30px 就等于没画**（箭头本身就有 9px）。量法：
   ```javascript
   const L = path.getTotalLength();   // 逐条打印，看有没有个位数
   ```
4. **查尺寸**：`print(im.size)` 与改动前比对，变了就要联动下游。

### 连线坐标的诊断手法

**不要靠眼睛看缩略图判断线对不对**——缩略图只能看出"有点挤"，看不出"线是 0 宽"。直接打印路径数据：

```javascript
document.querySelectorAll('#paths path, #egrp path')
  .forEach(p => console.log(p.getAttribute('d')));
```

一眼就能看出：起点是不是压在卡片边缘、水平段长度是不是个位数、有没有绕到别的分区里去。

---

## ⚠️ 通用踩坑（时序 / 组件 / 部署 / 状态机：四张骨架静默失效点）

### 1. 分区框设了 `z-index` → 连线被背景吃掉 或 反过来盖住卡片

`.zone` / `.region` 一旦设 `z-index` 就**创建层叠上下文**，把内部的卡片锁死在自己这一层，外层 svg 无论怎么调都进不去。症状：线在分区内部**完全看不见**，只在分区之间的缝隙里露一小段。

**正确层级**：分区背景（`position:relative`，**不设 z-index**，即 auto） < 连线 `z-index:2` < 卡片 `z-index:3`。

### 2. flex 容器里的横线宽度会塌成 0

时序图的消息线如果写成「`.msg` 是 flex 容器，`.bar` 靠 `margin` 撑开」——**flex item 没有 `flex-grow` 时宽度就是 0**。实测八条消息全部零宽，线根本画不出来，但标签文字照常显示，看起来很"正常"。

**修法**：`.bar` 用 `position:absolute`，`left` / `width` 由脚本按参与者中心**实测像素**设定（不要用百分比近似——实测偏 7px，跨列时还会叠加估算误差）。

### 3. `autoSides` 的判据决定整张图好不好看

自动判断出入边，别用这两个常见思路：

| 判据 | 后果 |
|---|---|
| 「左右优先」 | 跨行且目标偏左的连线退化成一根 30px 的竖线，看不出在连谁 |
| 「哪个方向间隙大」 | 同一行内的跨区连线被判成垂直，在两个分区之间拉出竖线 |

**用「是否同属一个分区」**：同分区（同 `.zone` / `.region`）→ 水平；跨分区 → 垂直。语义最直白，也最贴合阅读顺序：

```javascript
function autoSides(a, b) {
  var same = a.el.closest('.zone') === b.el.closest('.zone');
  if (same) return b.cx > a.cx ? ['r', 'l'] : ['l', 'r'];
  return b.cy > a.cy ? ['b', 't'] : ['t', 'b'];
}
```

### 4. 「同行中间有别的组件」检测，只比 x 会误判

水平线会从中间的卡片身上穿过去（线在卡片下层，被遮断）。所以加了绕行检测——但**必须同时判垂直重叠**，否则别的行上的组件也会被算成遮挡物，结果相邻两个组件之间也被判成"需要绕行"，整张图全是绕行线。

```javascript
if (c.cx > lo && c.cx < hi && c.t < yb && c.b > yt) return true;   // 两个条件都要
```

多条绕行线用 `laneN` 依次下移（+8px 递增），并把分区 `padding-bottom` 留到 26–28px 给通道。

### 5. 组件间距 < 30px → 相邻组件的连线等于没有

`gap` 12px 时，相邻两卡的连线只有 **7px**（还要减掉给箭头留的 5px）——比 9px 的箭头还短。**判据：可见线长 < 30px 等于没画。** 组件行 `gap` 用 **34px**。

### 6. 视口高必须贴合内容高，且不能用 `scrollHeight` 量

`full_page=True` 截的是 `max(视口高, 内容高)`。视口写死 1200 而图只有 500 高时，**下方会截出一大片底色空白**（实测占掉整图一大半）。

量内容高必须用 `document.body.getBoundingClientRect().height`，**不能用 `scrollHeight`**（它至少等于视口高，量不出真实内容）。量完再 `set_viewport_size()`，然后等 180ms（resize 可能触发骨架重绘）。

> 曲线类骨架还有个连带坑：控制点长度**写死会有"过度伸展"**（近距离连线时曲线先冲出去再折回来）。要自适应：`dist = max(16, min(56, gap * 0.45))`。

---

## ⚠️ 管道流程图专属的坑（改 `pipeline-flow.html` 时别破坏）

### 1. 间距会吃掉连线长度（本类图最隐蔽的一个）

骨架初版用 `列间距 34px` + `列内间距 14px`，结果：

| 连线 | 实际可见长度 |
|---|---|
| 跨列（如 `s3a → s4a`） | **22px** —— 减去两端各 6px 留白后所剩无几 |
| 同列（如 `s1a → s1b`） | **2px** —— 比 7px 的箭头还短，视觉上只剩一个箭头 |

**判据**：箭头本身约 7px 长。**可见线长 < 30px 就等于没有线。**

**修好的参数**（骨架现状，别改小）：

| 参数 | 值 | 理由 |
|---|---|---|
| `.flow` 列间距 | `58px` | 跨列线可见 50px |
| `.col` 列内间距 | `32px` | 同列线可见 24px |
| `GAP`（端点留白） | `4px` | 留白越大线越短，4px 刚好不让箭头压住卡片 |

**量法**（改完间距后自查，别靠眼睛）：

```python
pg.evaluate('''() => [...document.querySelectorAll('#egrp path')]
  .map(p => { const b = p.getBBox();
              return [Math.round(b.width), Math.round(b.height)]; })''')
# 出现 [22, 2] / [0, 2] 这种极小值 → 间距还是太窄
```

### 2. 回退线的竖段会从同列卡片背后穿过

**症状**：`back` 边如果从目标节点**底边中心**直接进入，而目标列下方还有别的卡片，竖段就会被那张卡片遮住（节点 `z-index` 高于 `svg`），只在缝隙里露出一小截箭头——**看起来像是从下面那张卡片冒出来的**，语义完全错。

**解法**：回退线的**起终点都走卡片侧边**，中间走最底部公共通道：

```
源节点左边 → 侧移到列缝 → 下沉到最底部通道 → 横移到目标列缝 → 上升到目标高度 → 从左侧进入目标
```

通道基准 `FLOOR` 取**所有节点底边的最大值** + 26px（不是只取两端节点的较大者，否则会紧贴同列其他卡片）。进入点放在目标**左下 3/4 处**（`b.y + b.h * 0.74`），避开主流程线通常进入的「左边中点」位置。

### 3. 表注要在所有线画完之后统一追加

画完一条标一条 → 后面的线会压住前面的字，出现"文字断断续续"。必须收集成 `labels` 数组，`EDGES.forEach` 结束后再统一 `getPointAtLength(len * 0.46)` 定位追加。

### 4. 副标题里的数字必须与实际一致

副标题常写「N 阶段 / M 节点 / K 条流转」。**写之前数一遍 `EDGES.length`**——这是最容易被评审抓的硬伤。

---

## 尺寸联动

改完 HTML 重导 PNG，**尺寸变没变**决定后续动作：

> **判断口诀：只问「可见行数 / 节点数变没变」。**

| 情况 | 尺寸 | 动作 |
|---|---|---|
| 同行内换词、改文案不跨行、改一条边的 `kind`、加删参与者（列宽自适应） | 多数**不变** | 直接换图，下游零改动 |
| 增删节点/状态导致换行、加删阶段列、图例加减行、说明文字多一行 | **变** | 必须联动：图已嵌入 Word 时，**`wp:extent` 与 `a:ext` 两处的 `cy` 都要改** |

计算式（保持显示宽度、按新纵横比算高）：`cy_new = round(cx_old × h_new / w_new)`

图已嵌入 Word 的换图完整配方见技能 **`docx-batch-revise`**（含"两处 extent 必须同改，只改一处会被覆盖而拉伸变形"的坑与断言写法）。

> **五张骨架导出宽统一为 3720px**，换图进 Word 前只需确认 `cx` 的纵横比，不必再区分"这张是架构图还是流程图"。

---

## 落地顺序（照着走）

1. 用上面第一张表**选图型**，别硬套。
2. 复制对应骨架，改文案 + 配色类 + 底部拓扑数组
   （管道图改 `EDGES`；组件图 / 部署图改 `DEPS` / `LINKS`；状态机改 `TRANS`；时序图改 `data-a,b`）。
3. `python <skill>/scripts/export_png.py 图.html` —— 看 console、看连线数、看尺寸。
4. 裁改动区域目视（用 `getBoundingClientRect()` 拿真实坐标 × `device_scale_factor` 换算，别凭感觉裁）。
   **管道图建议至少看三处**：一个分叉点、一个汇合点、一条回退线——这三处最容易出问题。
5. 尺寸变了 → 走「尺寸联动」；没变 → 直接交付。
6. 交付时**同时给 HTML 与 PNG**：HTML 用来改，PNG 用来插文档。

## 一句话总结

**只声明「谁连谁、什么类型」，坐标全部交给脚本算。** 手写坐标的图，改一个节点名就全废——这是本技能存在的全部理由。
