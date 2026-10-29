---
name: visual-arch-diagram
display_name: 技术架构图（HTML 高保真）
display_name_en: High-Fidelity Architecture Diagram in HTML
description: "用单文件 HTML（纯内联 CSS、零 CDN）绘制层带式技术架构图，并用 Playwright + Chrome 无头导出 2× 高清 PNG 供 Word / PPT 引用；也支持把旧位图架构图（截图/PNG）逐层转录还原成可编辑 HTML。当用户说「画架构图」「重绘这张架构图」「把这张图做成可编辑的」「架构图导出PNG」「系统架构图画一张」「架构图改一下」时使用。触发词：架构图、系统架构图、技术架构图、重绘架构图、架构图还原、位图还原成HTML、架构图PNG、分层架构图、微服务架构图。"
description_zh: 用零依赖单文件 HTML 绘制可精修、可导 2× 高清 PNG、可嵌入 Word 的层带式技术架构图；含六层配色体系、卡片配色类、导出管线与位图还原流程。
description_en: Build layered technical architecture diagrams as zero-dependency single-file HTML with fully inline CSS, export 2× print-ready PNG via headless Chrome, and transcribe legacy bitmap diagrams back into editable HTML.
category: Design Tools
version: 0.1.0
author: hasWhere
tags: ["架构图", "HTML", "单文件", "Playwright", "高清导出", "位图还原", "技术方案", "信创"]
permissions:
  - file_read
  - file_write
permission_notes_zh: 本 Skill 会读取骨架 HTML / 待还原的位图，在用户指定的项目目录写入单文件 HTML，并调用本机无头 Chrome 导出 PNG。图内样式与字体全部内联，导出环节不访问网络，无外部 CDN 依赖。
---

# 技术架构图（HTML 高保真）

## 这个技能解决什么

把"系统架构"变成一张**能改、能印、能直接塞进 Word/PPT**的图。

**与姊妹技能的分工**（别混用）：

| 你手上是什么 | 用哪个 |
|---|---|
| 分层架构图：层带 + 卡片网格，**上下分层** | **本技能** |
| 管道 / 流水线流程图：阶段推进 + **连线拓扑** | `visual-diagram-suite`（`pipeline-flow.html`） |
| 时序图 / 组件依赖图 / 部署拓扑图 / 状态机图 | `visual-diagram-suite` |
| 快速示意、聊天里贴一张、结构探索阶段 | `mermaid-diagram` |

> 不确定该画哪种？先看 **`visual-diagram-suite`** 的图型选型表（它是画图总入口）。

**本质区别**：架构图是**静态网格**——CSS 排完就完事，没有连线；流程图是**动态拓扑**——连线必须跟着节点位置走。
**图里有"线"，且线要跟着节点走吗？有 → 用 `visual-diagram-suite` 的管道流程图骨架。**

一句话判断：**这张图要进正式文档吗？要 → 用本技能或 `visual-diagram-suite`。**
（Mermaid 样式几乎不可控，导出质量一般，仅适合示意。）

## 三条铁律

1. **单文件、零 CDN、纯内联 CSS** —— 双击就开，断网可用；图片导出不依赖外部字体/图标。
2. **固定画布宽 1740px**（设计宽度），导出倍率 2× 得 **3720px** 宽。
3. **先量后改** —— 任何文案改动重导后，**先 `print(im.size)` 与旧尺寸比对**，再决定是否需要联动下游（见「尺寸联动」）。不靠感觉。

---

## 快速开始（三步）

```bash
# 1. 复制骨架，改标题 / 层数 / 卡片文案
cp <skill>/assets/arch-skeleton.html ./我的架构图.html

# 2. 导出 2× 高清 PNG（同时会校验 console 报错）
python <skill>/scripts/export_png.py 我的架构图.html 我的架构图.png

# 3. 目视校验（裁剪改动区域，见「质量校验」）
```

浏览器直接双击 HTML 也能看，但**交付必须走脚本导出**（保证 2× 与尺寸可复现）。

### 技能文件清单

| 文件 | 用途 |
|---|---|
| `assets/arch-skeleton.html` | 可直接复制的完整骨架：全部 CSS + **已补全的卡片配色类** + 三层示例（覆盖 band / card / bar / zones / flows / notes 全部组件） |
| `scripts/export_png.py` | HTML → 2× 高清 PNG；自动校验 console 报错，并对比新旧尺寸、提示是否需联动 extent |
| `scripts/restore_bitmap.py` | 位图 → 层带边界坐标 + 左右半幅放大切片（反向还原流程用） |

下文 `<skill>` 指本技能安装目录，如 `~/.workbuddy/skills/visual-arch-diagram/`。

---

## 骨架结构

```
.sheet (1740px 白卡, 圆角 16px, 投影)
├─ .hd            头部：h1 + .sub 副标题 + .legend 图例
├─ .stack
│   ├─ .band      层带（六层主体，逐层堆叠）
│   │   ├─ .rail  左侧竖排层号（一/二/三…）
│   │   └─ .bd
│   │       ├─ .bd-head   h2 层名 + p 副标题 + .pin 角标
│   │       ├─ .row       网格行（c3/c4/c5/c6/c7/c4b）
│   │       │   └─ .card  h3 标题 + .tech 技术栈 + .desc 描述 + .badge/.mini
│   │       ├─ .bar       通栏主数据条（1 条足够，别每条都上）
│   │       ├─ .zones     分区（.zone h4 + .box）
│   │       └─ .floating  层内悬浮标注
│   └─ .flows     层间流向条（.fl chip：实线=同步，虚线=异步/反向）
└─ .notes         页脚注（编号 ①②③）
```

**网格类速查**（`.row` 上加）：

| 类 | 列宽 | 适用 |
|---|---|---|
| `c3` | 3 等分 | 网关层、集成层 |
| `c4` | 4 等分 | 用户层、核心服务卡 |
| `c5` | 5 等分 | 中等密度 |
| `c6` | 6 等分 | 应用层（终端入口） |
| `c7` | 非等分 7 列 | 业务微服务群（列宽按内容微调） |
| `c4b` | 非等分 4 列 | 核心卡（主卡宽、说明卡窄） |

同一层内需要两组卡片时：`<div class="row c7 gap-lg">`，`gap-lg` 给 14px 上间距。

**层数建议**：6 层是甜点（一屏/一页 A4 能容纳，视线不疲劳）。超过 7 层先把"基础设施/横切能力"降级为 `.pin` 角标或页脚注，别硬堆层带。

---

## ⚠️ 卡片配色类：必须定义，否则静默失效

这是**本技能最容易翻车的点**，且浏览器**不报任何错**。

`.card` 靠变量取色：

```css
.card { border: 1.6px solid var(--c); background: var(--cbg); }
```

而 `--c` / `--cbg` 必须由卡片配色类提供：

```css
.c-amber  { --c:#D8A94A; --cbg:#FEFAF0; }   /* 金 · 用户层 */
.c-blue   { --c:#4A88CE; --cbg:#F3F8FE; }   /* 蓝 · 应用层 / Java 服务 */
.c-purple { --c:#8871C9; --cbg:#F8F5FE; }   /* 紫 · 网关层 */
.c-coral  { --c:#D16B65; --cbg:#FEF7F6; }   /* 珊瑚 · 服务层 / 交易核心 */
.c-teal   { --c:#2E9E8F; --cbg:#F1FAF8; }   /* 青 · Go 行情 */
.c-gold   { --c:#C2803A; --cbg:#FDF8F0; }   /* 棕金 · Java 业务 */
.c-sky    { --c:#4AA3D8; --cbg:#F2F9FD; }   /* 天蓝 · 移动端 */
.c-red    { --c:#C0504D; --cbg:#FDF3F2; }   /* 红 · 约束/警告 */
.c-grey   { --c:#9AA3AF; --cbg:#F7F8FA; }   /* 灰 · 外部系统 */
```

**若只写 `class="card c-blue"` 却没定义 `.c-blue{...}`** → `var(--c)` 无效 → **整条 `border` 与 `background` 声明失效** → 卡片退化成"无边框、无底色的一块文字"，层次感全靠层带撑着。

> **自查方法**（写完图先跑一遍，能抓出漏定义的配色类）：
> ```bash
> # 引用到的 vs 已定义的，取差集 —— 出现在左边、不在右边的就是漏定义
> comm -23 \
>   <(grep -o 'card c-[a-z]*' 图.html | sed 's/.* //' | sort -u) \
>   <(grep -o '\.c-[a-z]* *{' 图.html | tr -d ' {.' | sort -u)
> # 输出为空 = 全部有定义；有输出 = 这些类静默失效了
> ```

---

## 层带配色（六层参考定档）

层带颜色写在 `.band` 的**内联 style** 上，三个变量一组：

| 层 | `--rail` 色轨/层名 | `--line` 边框 | `--bg` 底色 |
|---|---|---|---|
| 一 · 用户层 | `#B8860B` 金 | `#E4CB84` | `#FEFAF0` |
| 二 · 应用层 | `#2C6FBE` 蓝 | `#A9C9EA` | `#F3F8FE` |
| 三 · 网关层 | `#7C5CBF` 紫 | `#C6B6E6` | `#F8F5FE` |
| 四 · 服务层 | `#C0504D` 红 | `#EBC0BE` | `#FEF7F6` |
| 五 · 数据层 | `#C97B70` 陶土 | `#EBC6C0` | `#FDF4F2` |
| 六 · 集成层 | `#6B7280` 灰 | `#CFD4DB` | `#F5F6F8` |

```html
<div class="band b4" style="--rail:#C0504D;--line:#EBC0BE;--bg:#FEF7F6;">
  <div class="rail"><i>四</i></div>
  <div class="bd"> ... </div>
</div>
```

**配色原则**：相邻层必须可辨（色相拉开，别两个蓝挨着）；服务层用红/珊瑚是刻意的（承载最核心交易逻辑，视觉权重最高）；集成层用灰表示"外部、非我方"。

**语言/技术栈标签**（图例 + 卡片角标共用）：

```css
.lang { font-size:10.5px; font-weight:700; color:#fff; padding:2px 7px; border-radius:4px; }
.lang.cpp  { background:#C0504D; }   /* C++  */
.lang.go   { background:#2E9E8F; }   /* Go   */
.lang.java { background:#C2803A; }   /* Java */
.lang.het  { background:#2C5F8A; }   /* 异构 */
```
同族语言（如 C 与 C++）用**同色系深浅区分**，靠内联 style 指定（`style="background:#A8443F"` 比 C++ 深一档），别用两种毫无关系的颜色——那会让读者以为它们是两类东西。

### 标签体系（画之前先定，别边画边加）

标签用来说明「这类东西是什么」。**图例是颜色语义的定义处，正文标签只能用图例已定义的类** —— 否则会出现「图例写红=核心，网关层卡片却挂红标写接入」这种自己打自己脸的情况，浏览器不报错，只有人眼能发现。

分两套，按图的类型选一套，别混：

| 图类型 | 标签类 | 语义 |
|---|---|---|
| **多语言异构技术方案图** | `.lang.cpp` / `.lang.go` / `.lang.java` / `.lang.het` | 按**实现语言**区分 |
| **业务/分层架构图**（本例即此类） | `.lang.core` `#C0504D` 红 / `.lang.gw` `#7C5CBF` 紫 / `.lang.cfg` `#C2803A` 金 / `.lang.ext` `#6B7280` 灰 | 核心业务 / 接入网关 / 配置驱动 / 外部生态 |

**落地前的对齐自检**（逐行核对，缺一不可）：

```bash
grep -o 'lang [a-z]*' 图.html | sed 's/lang //' | sort | uniq -c   # 正文实际引用（含图例自身）
grep -o '\.lang\.[a-z]*' 图.html | sort -u                          # 已定义
```

两边必须**一一对应**：正文里出现的每个类都要有定义，图例里列的每个类都要在正文真的出现（只列不用的图例行是噪声，会稀释图例的信息量）。

---

## 导出 2× 高清 PNG

```bash
python <skill>/scripts/export_png.py <输入.html> [输出.png] [--width 1860] [--scale 2]
```

关键参数与理由：

| 参数 | 值 | 为什么 |
|---|---|---|
| `channel` | `'chrome'` | 本机 Chromium 常缺中文字体，Chrome 渲染中文最稳；失败自动回落 |
| `viewport.width` | `1860` | = 1740 画布 + 左右 padding（26+20+20 舍入），保证不横向截断 |
| `device_scale_factor` | `2` | 得 3720px 宽，印刷/Word 缩放后仍清晰 |
| `full_page=True` | — | 整页截图，不受视口高度限制 |
| 等待 | `timeout=1200ms` + `document.fonts.ready` | 等字体加载完，否则可能截到 fallback 字体 |

**输出尺寸 = `viewport.width × scale` × `页面 scrollHeight × scale`**。文字行长变化会改 `scrollHeight`，所以导出后**必须比对尺寸**。

---

## 质量校验（四查，缺一不可）

1. **查 console**：脚本会打印 `console errors`，**必须为空数组**（空即正常，`[]`）。
2. **查尺寸**：`print(im.size)` 与改动前比对——变了就触发「尺寸联动」。
3. **查局部**：裁剪改动区域目视。用 `getBoundingClientRect()` 拿真实坐标再乘 `device_scale_factor` 换算，别凭感觉裁：
   ```python
   r = pg.evaluate('''() => {
     const c = [...document.querySelectorAll('.card')]
       .find(c => c.querySelector('h3').textContent.includes('交易核心'));
     return c.getBoundingClientRect().toJSON();
   }''')
   box = (int(r['x'])*2-16, int(r['y'])*2-16,
          int((r['x']+r['width'])*2)+16, int((r['y']+r['height'])*2)+16)
   im.crop(box).save('chk.png')
   ```
4. **查关键词**：文案类改动用 `grep -c` 确认旧词**归零**、新词**到位**（防止改一处漏三处）。

---

## 尺寸联动（改图后最容易漏的一环）

改完 HTML 重导 PNG，**尺寸变没变**决定后续动作：

> **判断口诀：只问「可见行数变没变」。**

| 情况 | 尺寸 | 动作 |
|---|---|---|
| 同层内换词、删几个字，不跨行（卡片宽度由网格固定） | **不变** | 直接换图，下游零改动 |
| 增删可见行（图例加一行、长句被挤成两行、加/删卡片） | **变** | 必须联动：若图已嵌入 Word，**`wp:extent` 与 `a:ext` 两处 `cy` 都要改** |

**图已嵌入 Word 时**，换图与 extent 同步的完整配方见技能 **`docx-batch-revise`**（含"两处 extent 必须同改，只改一处会被覆盖而拉伸变形"的坑与断言写法）。

计算式（保持显示宽度、按新纵横比算高）：`cy_new = round(cx_old × h_new / w_new)`

---

## 反向用法：把位图架构图还原成可编辑 HTML

用户丢一张 `架构图.png`（旧图、截图、别人画的）说"重新绘制一下"，走这条流程：

### 1. 先定层带边界（别凭肉眼裁）

用 numpy 扫**每行的非白像素占比**，占比接近 0 的连续行 = 层间空隙，据此切出每一层的精确 y 区间：

```bash
python <skill>/scripts/restore_bitmap.py 架构图.png --out ./_crop --zoom 3
```

产出 `layers.txt`（每层精确 y 区间）+ `band_XX_L/R.png`（左右半幅放大切片）。

**它用的是「双信号」，别只用其中一个**：

| 信号 | 判据 | 作用 |
|---|---|---|
| **长横线**（主） | 某行存在连续非白像素 > `rule-ratio × 图宽` | 层带上下边框，最可靠 |
| 空白行（辅） | 非白占比 < `gap-threshold` 的连续行 | 层间空隙；**层带紧贴时会失灵** |

> **踩过的坑**：只用"空白行"扫，会把**紧贴的层带整块合并**成一条（实测把 6 层并成 1 条 h=1052 的巨带）。所以必须靠横线定界。

**参数调优**（脚本会在输出里提示方向）：

| 现象 | 调法 |
|---|---|
| 层带数少于实际层数 | 调小 `--rule-ratio`（默认 0.75 → 试 0.5） |
| 把一行文字误判成层带 | 调大 `--rule-ratio`（→ 试 0.9） |
| 大色块被当成边框 | `--max-thickness`（默认 8 行）把过厚块判为实心色块并排除 |

**脚本会自动告警**：某层带高度 > 中位数 2 倍时，打印「可能合并了多层，务必人工核对」。看到这条**一定要看对应切片**——那是它唯一拿不准的地方。

**收益**：不会把文字裁掉半截，也不必反复试错重裁；自动化到 80%，剩下 20% 由告警点出来。

### 2. 分栏放大辨小字（2–5×）

原图小字（10–12px）直接看**必糊**，且"看起来像"的字最危险。做法：每层带切成左/右半幅，各自放大 2–5×（`Image.LANCZOS`）再逐字读。

### 3. 逐层转录 + 标注不确定性

按"一 · 用户层 → … → 六 · 集成层"顺序转录，**凡是猜的都要标出来**。宁可写"此字段原图不可辨，按域内一致性补为 X"并在交付时告知，也不要静默编造。

### 4. 补域内一致性（并如实交代）

还原常见三类缺口，处理原则：
- **被排版事故挤在一行的副标题** → 按归属拆回各自卡片（原图错，还原时修正）。
- **明显不符合业务常识的转录** → 修正并说明（例：把"采购商"与"客户"这类同指多称谓统一）。
- **题眼句** → 必须保留，别当废话删（例："两套账同源成交数据驱动"这种一句话定调的描述，是整张图的价值所在）。

### 5. 告诉用户你改了什么

还原不是复印。**改进项与失真项分开列**（"我改了三处，属改进"vs"这里我没读懂，请确认"），让用户能校验。

---

## 踩坑清单

| 坑 | 现象 | 解法 |
|---|---|---|
| 卡片配色类未定义 | 卡片无边框无底色，**浏览器不报错** | 见「卡片配色类」；`grep` 比对引用数与定义数 |
| **图例标签语义 ≠ 正文标签语义** | 图例写「红=核心」，网关层卡片却挂红标写「接入」，图文自相矛盾 | 图例是**颜色语义的定义处**，正文只能用图例已定义的标签类。落地前 `grep -o 'lang [a-z]*' 图.html \| sort \| uniq -c` 统计正文实际引用，图例只列**实际出现**的类，逐一对齐。见「标签体系」 |
| 业务型架构图硬套语言标签 | 业务/分层架构图里出现 `cpp/go/java` 标签，语义错位 | 语言标签只用于**多语言异构技术方案**图。业务型架构图自定义业务语义标签（如 `core/gw/cfg/ext`），并在图例写清含义 |
| 图例加行撑高画布 | PNG 高度变了，Word 里图被拉伸 | 先量尺寸再联动 extent（`docx-batch-revise`） |
| 只改一处 extent | 改完仍拉伸 | `wp:extent` + `a:ext` **两处**同改，加断言 |
| 凭感觉裁图校验 | 裁到半行字，看不出问题还白高兴 | `getBoundingClientRect()` 取真实坐标 ×2 |
| 中文字体渲染异常 | 导出图字变方块/回退字体 | `channel='chrome'`；等 `document.fonts.ready` |
| 层带相邻同色 | 视觉上分不清层 | 色相拉开；层带色表按顺序用 |
| 直接双击看就交付 | 尺寸/字体与导出不一致 | 交付一律走 `export_png.py` |

## 交付规范

- 产出 **HTML + 同名 PNG** 两个文件（HTML 可改、PNG 可印）。
- 改了图若已入 Word/PPT，**必须同步内嵌图**——否则图文版本漂移，评审必被抓。
- 交付时说明：画布尺寸、导出倍率、本次改了什么、哪些是还原时的推断。
