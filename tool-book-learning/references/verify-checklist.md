# 验收清单

编完站点后跑两个脚本，不要靠肉眼。

## 1. 结构审计（编译前，任意 python）

```bash
$PY scripts/audit_notes.py --book $BOOK_DIR --profile tech
# 非技术书：--profile prose
# 可选：--expect-sections 4,6,3（每章正节数预期）  --strict（WARN 也算失败）
```

| 检查项 | 级别 | 说明 |
| --- | --- | --- |
| H1 恰为 1 | ERROR | 统计前已按 ``` 切块排除代码内注释 |
| 代码围栏配平 | ERROR | 未闭合会让后面全部解析错位 |
| 五个固定小节齐全 | ERROR | 缺任一即报 |
| 固定小节顺序正确 | ERROR | 核心概念→代码要点→误区→自测→收获 |
| 每个代码块有 caption | ERROR | 最高频错误 |
| 空代码块 | ERROR | |
| Q/A 数量配对 | ERROR | 不配对会渲染成空答案盒子 |
| 无 `- **误区**：` 前缀 | ERROR | 模板自带 ⚠ 图标，写了重复 |
| 占位符 / TODO 残留 | ERROR | 注意：中文省略号 `……` **不算**占位符 |
| 章号可被识别 | WARN | 不匹配时站点上章号不显示 |
| 卡片数 < --min-cards | WARN | 默认 3 |
| 每章 3-6 道自测 | WARN | 0 题会报 WARN |

## 2. 统计条 vs DOM 核对（编译后）

```bash
$PY scripts/audit_notes.py --book $BOOK_DIR --profile tech --check-site $BOOK_DIR/index.html
```

强制"统计口径 == 渲染口径"，并检查产物里的占位符与脏值。
**这个检查抓到过真 bug**：统计条报 536 卡片 / 115 代码块，DOM 实际 537 / 144。

## 3. Playwright 无头回归（交付前）

⚠ 必须用 anaconda python，Playwright 只装在那个解释器里。

```bash
$PY scripts/verify_site.py \
    --site $BOOK_DIR/index.html --keywords 关键词1,关键词2,关键词3 \
    --shots $BOOK_DIR/_extract/_shots
```

18 项断言：

| # | 断言 | 为什么 |
| --- | --- | --- |
| 1-2 | console / pageerror 无报错 | JS 语法与运行期错误 |
| 3 | 无占位符残留 | 模板新增 `__XXX__` 忘了接线 |
| 4 | 无 undefined / NaN / [object Object] | 脏值 |
| 5-6 | data-id 全部非空且唯一 | 打卡进度依赖它，重复会串号 |
| 7-9 | 搜索命中数 == 可见卡片数（3 个关键词） | 隐藏范围漏一个就对不上 |
| 10 | 自测答案可展开 | |
| 11 | **全部题目答案非空** | 抓「答案混在题干里」的空盒子事故 |
| 12-14 | 打卡后进度 >0 / 写入 localStorage / 键未退化成 `book` | 中文书名 slug 陷阱 |
| 15 | 主题可切换 | |
| 16 | 目录点击可跳转 | |
| 17-18 | 阅读控件存在（A± / 宽读） | |
| 19 | **A+ 字号生效** | 用 `getBoundingClientRect().height` 判定，**不能用 computed fontSize** —— CSS zoom 不改 font-size |
| 20 | **顶栏未被缩放** | zoom 加在 body 上会连带缩放 sticky 顶栏，按钮命中区偏移 → 点击错位 |
| 21 | A+ 后 A− 步进对称 | 步长 0.1，**A+ 一次配 A− 一次**；写两次 A− 是净 −0.1，必然假失败 |
| 22 | 字号持久化到 localStorage | |
| 23 | 宽读切换生效 | |
| 24 | 表格斑马纹生效 | |
| 25 | 长文本折行处理 | `overflow-wrap: break-word` |
| 26-27 | 窄屏显示汉堡 / 可展开侧栏 | |

> 共 29 项。写断言时注意两个易错点：
> ① **别假设 zoom 起点是 100%**——Playwright `new_context()` 每次都是全新隔离环境，
> 但若改成复用 context，localStorage 会留上次的值；
> ② 「可还原」= A+ 一次后A− 一次（净值 0），不是 A− 两次。

## 选择器对照表（凭印象写必踩坑）

| 目标 | 正确选择器 | 常见错误 |
| --- | --- | --- |
| 搜索框 | `#q` | `#search`（不存在） |
| 命中数 | `#qcount` | |
| 卡片 | `.card` | |
| 打卡按钮 | `.done-btn` | 点 `.card` **无效** |
| 自测答案 | `.ans-btn` | 点 `.qa` **无效**（JS 是给 `.qa` 加 `.open`） |
| 答案文本 | `.qa .at` | 答案为空说明内容漏在 `.at` 外面 |
| 全展开按钮 | `.panel.quiz .quiz-acts button[data-act=open]` | |
| 窄屏汉堡 | `#menuBtn` | |
| 侧栏 | `#sidebar` | |
| 主题按钮 | `#themeBtn` | |
| 进度文本 | `#progText` | |

**写错选择器的表现是 Playwright 30s 超时，很容易误判成"站点坏了"。**

## 常见失败原因速查

| 现象 | 原因 |
| --- | --- |
| console 报 `x is not defined` | 模板 JS 用了 `var` 提升作用域外的变量；检查 `#menuBtn` / `#topBtn` 是否为空就 addEventListener |
| console 报 null 上加 classList | 注入的 widget 插到了 `<script>` **之后**，`$()` 取到 null，功能静默失效。widgets 必须插在 script **之前** |
| 搜索命中数与可见数对不上 | `.hide` 覆盖面漏了某个容器（tr / qa / code-block / panel） |
| 点击超时 | 被 fixed 元素遮挡，用 `eval_on_selector(e=>e.click())` 绕过 |
| 进度一直是 0 | localStorage 键被清洗成 `pbls:book:done`（全中文书名 + 只留 ASCII 的 slug） |
| 产物比预期小很多 | 编译覆盖了手工增强版；`len(notes/ch*.md) < len(map.chapters)` 是预警信号 |