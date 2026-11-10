# 个人 AI 技能库

> 22 个可直接加载的 Agent Skill，覆盖前端原型、架构图与三维大屏、开发工作流、运维排障与本地自动化。

每个顶层目录就是一个独立技能：目录名等于 `SKILL.md` 中的 `name`，检出后即被 Agent 加载，无需安装或构建。

## 快速开始

仓库默认放在 Agent 的技能目录下（`~/.agents/skills`）：

```bash
git clone https://github.com/qq940043871/personal-ai-skills.git ~/.agents/skills
```

已有目录时直接拉取更新：

```bash
cd ~/.agents/skills && git pull
```

也可以只取用其中某个技能：把对应目录复制到任意 Agent 的技能目录（例如 WorkBuddy 的 `~/.workbuddy/skills/`）。

### 怎么用

直接用自然语言描述任务即可，Agent 会按每个 `SKILL.md` 的 `description`（中文触发词）自动选择技能；也可以点名技能。

| 你说 | 会用到 |
|---|---|
| 「画一张微服务架构图，导出 PNG」 | `visual-arch-diagram` |
| 「画个下单时序图」 | `visual-diagram-suite` |
| 「做个港口数字孪生大屏」 | `visual-digital-twin` |
| 「做个运营后台的合同管理页」 | `html-prototype-base`（02-manage 象限） |
| 「我要开发一个客户管理功能」 | `html-b2b-portal`（路径 B 澄清式功能开发） |
| 「把这本书整理成学习网站」 | `tool-book-learning` |
| 「服务 OOM 了，帮我分析这个 heap dump」 | `dev-prod-triage` |
| 「把这个 H5 游戏打包成 exe 和 APK」 | `html-app-packaging` |
| 「把 skill 上架到技能市场」 | `tool-skill-publish` |

## 技能总览

### 开发与工程 · `dev-`

| 技能 | 用途 |
|---|---|
| `dev-godot-zero-asset-game` | Godot 4.x 零素材 2D 小游戏全流程：数据驱动、无头质量门、Windows / Android 交付 |
| `dev-mipad-landscape` | 小米平板横屏 uni-app 适配：rpx 基准重定义、横屏锁定、三栏布局、安全区 |
| `dev-prod-triage` | 生产问题分层定界（客户端 → Mids → DS → 后端 → 第三方）+ JVM 现场取证与大体积 hprof 流式分析（唯一权威版本） |
| `dev-uniapp-to-miniprogram` | uni-app（Vue3）→ 原生微信小程序工程，含静态与业务双层自检 |
| `dev-web-stress-test` | Web 压测与性能验收方法论：协议侦察、JMeter + WebSocket 双口径、容量探顶、验收报告 |

### 企业 HTML 原型 · `html-`

| 技能 | 用途 |
|---|---|
| `html-prototype-base` | HTML 原型总入口：通用基座（用途 / 菜单布局选择器、主题预设、通用页面模式）+ 四象限（01-design 架构设计文档、02-manage 运营后台、03-client 会员中心、04-mobile 手机端） |
| `html-b2b-portal` | B2B 门户 / 产业互联网平台原型：12 个行业视觉定档、行情组件、3D 与视差动效层；含澄清式功能开发（澄清 → 页面蓝图 → 原型或前后端代码） |

### 图表与三维 · `visual-`

| 技能 | 用途 |
|---|---|
| `visual-arch-diagram` | 层带式技术架构图：单文件 HTML 绘制，2× 高清 PNG 导出，支持旧位图还原 |
| `visual-diagram-suite` | 画图总入口：时序图、组件依赖图、部署拓扑图、状态机图、管道流程图五类骨架 + 统一导出 |
| `visual-echarts-dashboard` | ECharts 深色科技风数据大屏：配置驱动、Mock 数据、任意分辨率自适应 |
| `visual-threejs-scene` | Three.js 场景工具箱：程序化几何、GLB 接入、标签 / 巡检 / 告警 / 拾取、离线打包；含 Blender 实景资产管线（MCP 建模 → GLB 优化体检 → 集成） |
| `visual-digital-twin` | 写实数字孪生大屏生成器（城市 / 工厂 / 港口 / 炼化），配置即交付，含 2D 降级 |

### 自动化工具 · `tool-`

| 技能 | 用途 |
|---|---|
| `tool-skill-publish` | 技能市场上架：frontmatter 合规、zip 结构、表单填写值、打包自检与图标导出 |
| `tool-book-learning` | 把 PDF / 扫描件 / 原著整理成单文件 HTML 学习站：章节卡片、概念表、自测、检索 |
| `tool-b2b-bid-expert` | 「标书军师」：解析招标文件、定位评分办法与废标条款、生成应答表 / 偏离表、合规自检 |
| `tool-b2b-business-expert` | 「商略」：B2B 客户画像、采购决策链、销售漏斗、定价政策、商务谈判 |
| `tool-yuque-export` | 语雀知识库全量导出为 Markdown 文件树 + 本地化图片 |
| `tool-wechat-jobs-monitor` | 公众号监听 → 关键词筛选 → 结构化落库 → HTML 日报 → 邮件推送（**仅作者本人私用**） |
| `tool-checkin-zcode` | 桌面应用签到自动化（当前配置 ZCode）：配置一次按钮坐标，之后一句话执行 |
| `tool-check-trae` | Trae CN 每日签到领积分自动化 |
| `tool-electron-gui-click` | Electron 桌面应用截图定位 + 坐标点击自动化 |

### 端到端流程

| 技能 | 用途 |
|---|---|
| `html-app-packaging` | 纯静态 HTML/H5 → Windows exe（Electron）+ Android APK（HBuilderX）套壳打包，强制同步 + SHA-256 校验 |

## 目录结构

```
<skill-name>/
├── SKILL.md        入口：YAML frontmatter + 工作流
├── references/     深度文档，按需加载
├── assets/         可复制的骨架、模板、数据
├── scripts/        可执行脚本（Python / Node / Java / Shell）
└── templates/  config/   可选
```

`SKILL.md` 只保留索引与关键规则，重内容放 `references/`，由「何时读取」表按需加载。

## 技能约定

- **触发词即接口**：`description` 里的中文短语决定技能何时被选中，修改等同于改行为。
- **生成器技能的 `assets/` 是模板**：会被复制进用户工程，而不是原地使用（如 `dev-uniapp-to-miniprogram/assets/*` → 工程的 `tools/`）。
- **产物落在用户指定目录**，不写回技能目录；通常是一个自包含单文件 HTML。
- **CDN 策略按家族区分**：`visual-*` 零 CDN、全内联，断网可用；`html-prototype-base`（含其四象限）刻意使用 Tailwind / Chart.js CDN，零构建；`html-b2b-portal` 允许 CDN 但需优雅降级。
- **版本从 `0.1.0` 起**，版本号同时存在于 `SKILL.md`、`config.json`（如有）、包文件名与交付文档，改版需一起更新。
- **署名默认 `hasWhere`**，除非明确要求更换。
- **字节保真**：`.gitattributes` 设置 `* -text`，禁止换行符转换；图片、GLB、字体等二进制文件保持原样。

## 自检与打包

主要检查脚本（在仓库根目录运行）：

```bash
# 技能上架包自检（结构 / frontmatter / 引用 / 垃圾文件 / 包内自检 / 三方 md5）
python tool-skill-publish/scripts/check_package.py <包.zip> --src <开发目录> --dst <安装副本>

# 反向回归：证明上述检查项仍会报错
python tool-skill-publish/scripts/test_checker_asserts.py

# 图表导出
python visual-arch-diagram/scripts/export_png.py 图.html --out 图.png

# 三维大屏构建与无头验证
python visual-digital-twin/scripts/build_twin.py --scene city --out out.html
python visual-digital-twin/scripts/verify_screen.py out.html --shot out.png

# HTML 原型门禁
python html-b2b-portal/scripts/check_prototype.py 原型.html
```

完整的命令清单、解释器注意事项与跨技能路由，见 [CODEBUDDY.md](CODEBUDDY.md)。

> 部分脚本依赖 Playwright / PyMuPDF / RapidOCR，需要用已安装这些库的 Python 解释器运行；纯标准库脚本（`audit_notes`、`build_site`、`check_package` 等）任意解释器均可。

## 使用范围

- `tool-wechat-jobs-monitor` 依据其 [NOTICE.md](tool-wechat-jobs-monitor/NOTICE.md) **仅限作者本机私人使用**，不得打包、分发或二次发布。
- 其余技能可自由读取与修改；对外发布时请遵守各技能 `SKILL.md` 中的权限与依赖声明。

## 维护提示

- JVM 取证工具只有一份：`dev-prod-triage/scripts/jvm/`（`dev-jvm-triage` 已整体并入，勿再新建副本）。
- `dev-feature-scaffold` 已整体并入 `html-b2b-portal`（路径 B：澄清 → 蓝图 → 原型或前后端代码），布局库 L/P/D/M/R 在 `html-b2b-portal/references/feature-scaffold.md`；勿重建该目录。
- `visual-arch-diagram` 与 `visual-diagram-suite` 的 `export_png.py` CLI 相同但实现不同，不要互相覆盖。
- `html-*` 技能描述的是外部原型工程（`01-design/`、`02-manage/`、`03-client/`、`04-mobile/`），这些目录不在本仓库内。
- HTML 原型只有一个技能：`html-prototype-base`。四象限已并入其 `references/`（`01-design-architecture.md`、`02-manage-pages.md`、`03-client-pages.md`、`04-mobile-pages.md`），shell 模板与页面模式分别在 `layouts.md`、`page-patterns.md`；不要重建 `html-manage-pages` 等旧目录。
- `visual-threejs-scene` 已并入 `visual-real-twin`（Blender 实景资产管线），勿重建该目录；跨技能引用较多（如 `arch-diagram` ↔ `diagram-suite`、`digital-twin` ↔ `threejs-scene`），重命名技能后需全仓搜索引用。
