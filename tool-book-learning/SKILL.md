---
name: tool-book-learning
description: 把一本书（技术 PDF / 扫描件 / 公众号合集 / 无 PDF 的原著导读）整理成可交互的单文件 HTML 学习网站。当用户说"整理这本书的要点"、"把 PDF 书做成学习网站/笔记站"、"帮我读这本书并产出学习页面"，或给出书籍要求提炼章节知识点、核心概念、代码要点/关键论断、自测题时使用。产出：章节要点卡片、核心概念表、代码片段、常见误区、自测问答，支持章→节两级目录、全文检索、掌握度打卡、深浅主题、快捷键，零 CDN 离线可用。
---

# 书籍 → 学习网站

## 做什么

输入一本书，输出一个**单文件 HTML 学习站**：左侧章→节两级目录 + 全文检索，正文按
"节 → 知识点卡片"组织，每章附核心概念表、代码要点（无代码书则为关键论断）、常见误区、
自测问答、本章收获；支持打卡进度（localStorage）、深/浅主题、快捷键。

**目录约定：一本书 = 一个文件夹**，文件夹名 = 书名，站点 HTML 放文件夹根。
所有中间产物收在 `<书名>/_extract/`，不污染书籍库上层。

## 脚本

| 脚本 | 用途 | 解释器 |
| --- | --- | --- |
| `init_book.py` | 按书名建文件夹 + map.json 骨架（有书签自动填章） | anaconda |
| `pdf_probe.py` | 探测页数/文字层/书签，决定提取路线 | anaconda |
| `make_map.py` | **书签不可信时**造 map.json：dump 书签树 / 按标题定位 / 手工范围 / 渲染章首页 | anaconda |
| `extract_text.py` | 文字层快路：按章抽文本 | anaconda |
| `render_pages.py` | 渲染页 PNG（带 PDFIDX 防错位标签） | anaconda |
| `ocr_extract.py` | 扫描件默认路线：OCR 抽文本 + 自动挑出需视觉补看的图页 | anaconda |
| `audit_notes.py` | **结构审计**：notes 是否符合契约（编笔记后必跑） | 任意 |
| `build_site.py` | 编译成单文件站点（`--book` 一键推导路径） | 任意 |
| `retemplate.py` | **旧站换外壳**：无 notes / 手工站重套当前模板，自动保留自定义 CSS | 任意 |
| `verify_site.py` | **Playwright 无头回归**（编完后必跑） | **anaconda** |
| `assets/site_template.html` | 站点模板（改样式/交互改这里，不动 Python） | - |
| `references/notes-format.md` | 章节笔记契约（build_site 依赖） | - |

anaconda = 「已装 Playwright 的解释器」（PyMuPDF / Pillow / rapidocr / Playwright 都在这）。
纯标准库脚本（audit / build_site）用托管 python 即可。
OCR 首选 `rapidocr-onnxruntime`（已装）；本机 `pytesseract` 缺 tesseract.exe 引擎，不能用。

## 路线决策树

```
有 PDF？
├─ 无 → 【路线 D】无 PDF 原创导读
└─ 有 → pdf_probe 判定
   ├─ 有文字层 → 【路线 A】文字层快路
   └─ 扫描件 → 【路线 B】OCR 混合路由（默认）
                └─ OCR 不可用 → 【路线 C】纯视觉路（贵，最后手段）

任何路线都要先解决"切章"：
├─ init_book 切出的章数合理（十几章~几十章）→ 直接用
└─ 章数离谱（0 章 / 470 章 / 一章独占 180 页）→ make_map.py 重切
```

## 路线 A：文字层快路（成本极低）

```bash
$PY scripts/init_book.py --pdf "$BOOK.pdf" --root D:/books
$PY scripts/pdf_probe.py $BOOK.pdf          # 确认 route=text-extract
$PY scripts/extract_text.py --pdf "$BOOK.pdf" --map $MAP_JSON --out $BOOK_DIR/_extract/pages_text
```

**必须检查 init_book.py 输出的章数**。十几章以下或上百章，说明书签层级不对 → 转 make_map.py。
纯文本会丢图表信息，重要插图用 `render_pages.py` 渲染对应页补看。

## 路线 B：扫描件 OCR 混合路由（默认）

**OCR 搬文字，图页才交给视觉**——token 约为纯视觉路的四分之一。

1. **校准 map.json**：渲染目录页（通常前 25 页），用 Read 读图，把各章
   `book_pages / pdf_start / pdf_end` 填进 map.json 并校准 `page_offset`。
   符号约定 `书页 = PDF 0-based索引 + page_offset`（通常是负数）。
   校准细节与扉页陷阱见 `references/pitfalls.md` 第二节。
2. **跑 OCR**（约 3.5 秒/页）：
   ```bash
   $PY scripts/ocr_extract.py --pdf "$BOOK.pdf" --map $MAP_JSON \
       --out $BOOK_DIR/_extract/pages_ocr --chapters ch04
   ```
3. **只**对 manifest 里 `need_vision=true` 的页用 Read 读 PNG 补图语义。
4. 结合 OCR 文本 + 补看的图撰写 `$NOTES_DIR/chNN.md`。

## 路线 C：纯视觉路（回退，成本高）

按章渲染 `render_pages.py` → Read 读 PNG，每批 4-6 页，**先核对图上红色 PDFIDX 标签
与预期页码一致**再写笔记。整本几百页很贵：未指定范围时先做前 3 章样例，经确认再继续。

## 路线 D：无 PDF 的书

直接「原创笔记 → audit → build_site」，**跳过 probe/extract/OCR**。
只需手写 map.json（或用 `make_map.py --range`）列出章节。

版权敏感的书（如在售版权书的中文版）：**只做中文原创导读**，要点/概念表/自测题全部重写，
不含译本原文。事实核对可用作者本人官方免费公开的全文，并在交付时向用户明示。

## 主流程（写笔记 → 交付）

### 1. 撰写章节笔记

严格遵循 `references/notes-format.md`。要点：

- 文件名 `chNN.md`（与 map.json 的 id 一致），`# 第N章 标题` + `> 一句话概括` 开头
- `## N.N 节标题` → `### 知识点标题`（卡片）两级结构
- 章末五个固定小节；**非技术书第 2 个是「关键论断」而不是「代码要点」**
- 忠于原书：类名/方法名/参数/数字要具体，不编造原书没有的结论
- 中断可续：notes 里已有的章节跳过，只补缺的

**章多时（>8 章）走并行子代理**：详细提示词模板与坑见 `references/parallel-playbook.md`。
要点：3 并发上限、提示词必须写清五件事、**子代理自报"校验通过"不可信**。

### 2. 结构审计（必做）

```bash
$PY scripts/audit_notes.py --book $BOOK_DIR --profile tech   # 或 prose
```

检查 H1 唯一 / 围栏配平 / 五固定小节齐全且顺序正确 / 每代码块有 caption /
Q-A 配对 / 无 `- **误区**：` 前缀 / 章号可识别 / 占位符残留。
缺 caption 的块按语义逐个补说明文字（**别用模板自动填充**）。

### 3. 编译站点

```bash
$PY scripts/build_site.py --book $BOOK_DIR --profile tech
```

非技术书：`--profile prose`。**不需要复制脚本、不需要打补丁、不需要传 `--template`**。
map.json 登记但 notes 缺失的章节渲染成"待补充"占位，站点结构始终完整；
每补一章笔记重跑本命令即可增量更新。

> ⚠ **重编译前先确认产物可弃**：若某本书的 `index.html` 含手工增强内容
> （自制 CSS / 图表 / 17 章而 notes 只有 2 章），直接编译会把它覆盖成占位版。
> 判据：`len(notes/ch*.md) < len(map.json 的 chapters)` → 先备份、确认可弃。

### 3b. 旧站重套（不能走重建的书）

命中上面那条 ⚠ 时（没有 `chNN.md`、或站点是手工装配的），用 `retemplate.py`
**只换外壳**（CSS + JS + hero + footer），内容 DOM 原样搬运：

```bash
$PY scripts/retemplate.py --book $BOOK_DIR --profile tech --dry-run   # 先看会搬什么
$PY scripts/retemplate.py --book $BOOK_DIR --profile tech             # 落盘（自动备份）
```

- 统计按内容区真实 DOM 重新计算，不信任旧 hero 的硬编码数字
- `--extra-css auto`（默认）：自动把旧站 CSS 里"新模板没有的选择器"追加进来，
  手工站的自定义样式（如 SVG 图解配色 `.figbox / .fig .tx`）不会丢
- 只适用于模板结构一致的站点（需有 `<div class="content" id="content">` 与 `<nav class="nav" id="nav">`）

### 4. 验收（必做）

```bash
$PY scripts/verify_site.py \
    --site $BOOK_DIR/index.html --keywords 本体,约束,API
```

29 项断言：console 无报错 / 占位符残留 / data-id 唯一 / 搜索命中数与可见卡片一致 /
全部自测答案非空 / 打卡写 localStorage / 主题切换 / 目录跳转 / 窄屏汉堡 /
A± 字号生效且不缩放顶栏 / 宽读 / 斑马纹 / 长文本折行等阅读体验项。
再跑一次统计条核对：

```bash
$PY scripts/audit_notes.py --book $BOOK_DIR --profile tech --check-site $BOOK_DIR/index.html
```

这会强制"统计口径 == 渲染口径"——站点自己骗自己（报 536 实际 537）这种事会被当场抓住。
完整清单见 `references/verify-checklist.md`。

### 5. 交付

`present_files` 交付 `<书名>/index.html`，附一句统计（N 章 / M 张卡片 / K 个代码块 / J 道自测题）。

## 产物结构

```
<书名>/
├── index.html                    # 最终交付物（单文件，双击即开）
└── _extract/
    ├── map.json                  # 章节映射（id/书页/PDF页/offset/book_dir）
    ├── notes/chNN.md             # 章节笔记（中间产物，也是站点的数据源）
    ├── pages_text/chNN.txt       # 文字层快路抽取文本
    ├── pages_ocr/chNN.txt        # OCR 混合路：按页分隔全文
    ├── pages_ocr/manifest.json   # 每页字数 + need_vision 判定
    ├── pages_ocr/vision/chNN/*.png   # 待多模态补看的图页
    ├── pages_homes/*.png         # make_map --render-homes 渲染的章首页
    └── _shots/*.png              # verify_site 截图
```

## 站点已有功能（模板内置，别重复实现）

**导航与阅读**：章→节两级目录（箭头展开/自动展开当前章）· 章+节双高亮 scrollspy ·
每章进度徽标 + 章头进度条 · 回到顶部 · 阅读位置记忆 + 恢复提示条

**检索与练习**：全文检索覆盖卡片/概念表/问答/代码/章节标题，分类计数（卡x·概念y·问答z·代码w）·
自测每章全展开/收起 + 单题点开看答案

**代码阅读**：行号 + 超 24 行折叠 + 一键复制 + 命中自动展开

**排版与无障碍**：A± 字号缩放（85%~150%，持久化）· 宽读/限宽排版切换 ·
主题跟随系统（可手动覆盖）· 表格斑马纹 · 卡片内 strong 提亮（打卡后高亮）·
中文长段落/长 URL 折行 · 选区配色 · 细滚动条

**快捷键**：`/` 搜索 · `Esc` 清空 · `g` 回顶 · `t` 主题 · `w` 宽读 · `+`/`-` 字号 · `n`/`p` 上下节

> 字号缩放用 CSS `zoom` **只加在 `.main`**，绝不能加 `body` ——
> body 缩放会连带缩放 sticky 顶栏，导致按钮命中区偏移、点击错位。
> `verify_site.py` 有这条的专项回归断言。

## 深入文档

- `references/notes-format.md` —— 笔记 Markdown 契约（写笔记前必读）
- `references/pitfalls.md` —— **踩过的坑分类清单**（遇到症状时查）
- `references/parallel-playbook.md` —— 子代理并行写章的提示词模板与核验方法
- `references/verify-checklist.md` —— 验收清单与选择器对照表