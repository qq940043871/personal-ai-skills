---
name: html-app-workbench
description: "类 APP 工作台快速开发：一句话需求，产出在 iPad/平板/手机全屏运行的类原生 APP 工作台（单文件 HTML、触控友好、内联 SVG 图标、自带本地数据层，可一键发布成链接）。当用户说「做个 XX 工作台」「做 XX APP」「快速开发 XX 应用」「做个 XX 原型」「给娃/家人/团队做个触屏工具」，或要求暗色炫酷、清爽明亮、暖色活泼风格的功能型页面时使用。覆盖需求澄清→UI 设计→原型→接库实现→验证五阶段流水线。数据持久化与应用发布复用 lark-apps（妙搭）命令，不另造轮子。"
---

# 类 APP 工作台快速开发

一句话需求 → 可在 iPad/平板/手机全屏运行的类原生 APP 工作台。产物是**单文件 index.html**（内联全部 CSS/JS/SVG 图标），数据先落 localStorage；用户要真数据库或分享链接时，再接妙搭（lark-apps）建表与发布。

## 何时用 / 不用

- **用**：做个 XX 工作台 / 做 XX APP / 快速开发 XX 应用 / XX 原型 / 给娃·家人·团队做个触屏工具 / 做个能记录 XX 的 APP。
- **不用**：演示文稿走 html-ppt；多维表格类数据管理走 lark-base；用户明确要妙搭云端 AI 生成（自己不碰代码）时交给 lark-apps 云端会话；已初始化的 `.spark/meta.json` 全栈项目按 lark-apps 本地开发流程走。

## 硬性规则（全程有效，交付前按此自检）

1. **单文件交付**：最终只交付一个 `index.html`，CSS/JS/SVG 全部内联。原因：妙搭 html-publish 可直接传单文件，iPad 本地打开零依赖、断网可用。
2. **图标一律内联 SVG**：禁止外链 iconfont、CDN 脚本、网络图片、网络字体。图标手写 24×24 viewBox 的简洁线条 SVG，`stroke="currentColor"` 继承文字色。
3. **触控目标 ≥50×50px**：所有可点元素（按钮、行内操作、tab）实际热区不小于 50px；相邻间距 ≥8px 防误触。
4. **数据层与渲染逻辑用 ES5**：`var` + `function`，禁止箭头函数、`let/const`、模板字符串、`async/await`、`fetch`、解构、class。原因：嵌入运行环境兼容性 + 旧环境 SDK lint 按 ES5 检查（详见 references/library-commands.md 避坑清单）。
5. **主题走 CSS 变量**：颜色、圆角、阴影全部引用 `:root` 里的 token，组件样式里不写死颜色。换主题只改一个变量块。
6. **门禁**：第五阶段自检清单全过才算完成；发布前先量体积（单个 html ≤10MB，见 library-commands.md）。

## 五阶段主流程

### ① 需求：凑齐四要素

四要素：**给谁用**（设备/人群，默认 iPad 竖屏）、**核心功能**（最多 5 个，超出的砍掉并告知）、**数据字段**（要记录什么，天然就是表结构）、**主题偏好**（三选一，默认 ocean-dark）。

- 能从用户一句话里推断的，按合理默认补齐并在最终汇报里说明「我默认了什么」。
- 真缺口才提问，**一轮最多 2 个问题**，禁止连环追问；用户说「你定」就直接定。

### ② UI 设计：套主题

读 [`references/design-system.md`](references/design-system.md)，完成三件事：选定主题（ocean-dark 暗色炫酷 / light-fresh 清爽明亮 / warm-family 暖色育儿，按人群推断）；确定布局骨架（tabbar 还是侧栏、首页放什么卡片）；列出用到的组件清单（从 7 类组件里挑）。此阶段只产出设计要点，不产出单独的设计稿文件；用户未预授权时用一两句话向其确认主题与功能清单，预授权时直接进 ③。

### ③ 原型：生成单文件 HTML

- 骨架整体复制 [`assets/templates/ipad-meta.html`](assets/templates/ipad-meta.html)：已含 iPad 全屏 meta、安全区 padding、tabbar、触控热区与 active 反馈样式。
- 数据层整体并入 [`assets/templates/sdk-init.js`](assets/templates/sdk-init.js) 的 `WorkbenchDB`（ES5，localStorage 实现）。
- 动手前先填 [`assets/templates/schema-template.json`](assets/templates/schema-template.json)：字段定义同时驱动表单、校验和后续建表 SQL。
- 组件规格、间距、字号、交互按 design-system.md 对应主题执行，不要自由发挥。
- 原型阶段数据全走 localStorage，不发起任何网络请求。

### ④ 实现：接库与发布（按需）

用户要「分享链接 / 多人用 / 数据换设备不丢」→ 读 [`references/library-commands.md`](references/library-commands.md)：

- **静态发布**（数据仍在本机）：`+create --app-type html` → `+html-publish` → 拿 `data.url`。
- **真数据库**：升级 full_stack 应用，按该文件的 6 步命令链建表、导种子数据、部署。
- 纯本地自己用 → 跳过本阶段，直接交付文件。

### ⑤ 验证：自检门禁

用浏览器打开 index.html（触屏设备或开发者工具设备模拟），逐项过：

- [ ] 无任何外链资源（断网/离线打开正常）
- [ ] 全屏铺满、刘海与底部安全区无遮挡、无意外滚动条
- [ ] 所有可点元素热区 ≥50px 且有 active 按压反馈
- [ ] 增删改查全部走通，刷新后数据仍在
- [ ] 删除等破坏性操作有确认弹层，保存成功有 toast
- [ ] 颜色全部来自主题 token，无写死值
- [ ] 数据层无 ES6+ 语法（对照硬性规则 4）

任何一项不过 → 修复后重验。全过 → 交付。

## 交付汇报格式

固定包含：产物路径｜主题｜功能清单｜数据存储方式（localStorage / 妙搭数据库）｜自检结果｜默认了哪些假设｜（如已发布）发布态链接 + 「默认仅本人可见，要不要放开可见范围」的提示。

## 与其他 skill 的边界

建表、发布、可见范围、观测全部复用 lark-apps 的 `lark-cli apps +*` 命令（命令契约见 references/library-commands.md，以 `lark-cli apps +<cmd> --help` 实时输出为准）。本 skill 不定义、不臆造任何新的 CLI 命令。
