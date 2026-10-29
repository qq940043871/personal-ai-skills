---
name: tool-wechat-jobs-monitor
display_name: 公众号信息监听流水线
display_name_en: WeChat Account Monitor Pipeline
description: >
  监听任意微信公众号的新文章并按关键词筛出目标内容（招聘/招标/政策通知等），抽取结构化字段、
  去重落库，生成可直接当邮件正文的完整 HTML 日报，并能投递到指定邮箱。
  当用户说「监听某个公众号」「抓取某公众号的招聘信息」「每天给我发公众号日报」
  「监控公众号更新」「把公众号里的招聘/招标信息整理成邮件」「公众号信息订阅推送」
  「wechat monitor」「monitor a WeChat public account」时使用。
  零 Docker、零第三方服务——直连微信读书接口即可；也支持消费上游 RSS。
description_zh: 监听任意微信公众号，按关键词筛出招聘/招标/政策等信息，去重后生成 HTML 日报并邮件推送。
description_en: Monitor any WeChat public account, filter target posts by keywords, dedupe, and email a clean HTML digest.
version: 1.0.0
author: hasWhere
category: productivity
tags: ["信息资讯", "效率工具"]
permissions:
  - file_write
  - network
permission_notes_zh: 会读写工作目录下的 config.yaml / data/ / out/，并联网访问微信读书接口与 mp.weixin.qq.com 以采集与校验链接。
metadata:
  last_updated: "2026-10-07"
---

# 公众号信息监听流水线

把「一个公众号 + 一组关键词 + 一个邮箱」变成每天自动送达的信息日报。
本 skill 自带完整流水线代码（`scripts/wjobs/`），**零 Docker、零第三方服务**：
采集 → 过滤 → 抽取 → SQLite 去重 → 生成 HTML 日报 → 邮件投递。

> **装完即用**：新机器上第一条命令永远是 `python scripts/bootstrap.py`，
> 它会自动建独立 venv 并装好全部依赖，不污染系统环境。详见「第 0 步」。
> 前置条件只有两个：① 浏览器登录过 `weread.qq.com`；② 在微信读书里关注了目标公众号。

## 何时用本 skill

用户表达下列任一意图时触发：

- 「帮我监听 XX 公众号」「盯着 XX 号，有招聘就发我」
- 「把 XX 公众号最近的招聘信息整理成邮件 / 日报」
- 「每天/每周给我推一份公众号信息简报」
- 「监控某公众号的招标 / 政策通知更新」
- 英文：monitor a WeChat official account, daily digest of a public account

## 核心概念（先记住这三件事）

1. **采集靠微信读书接口，不碰微信本体**。本项目不直连微信、不装 Docker，而是用
   「微信读书已登录的浏览器 cookie」去读你**自己能读到的**公众号文章。
   所以前置条件只有两个：① 浏览器登录过 `weread.qq.com`；② 在微信读书里关注了目标号。
2. **选号比选技术重要一百倍**。同一品牌的主号和垂直子号内容可能完全不同
   （例：「郑州本地宝」是办事指南号，「本地宝郑州招聘」才发招聘）。选错号 =
   以为代码坏了，其实是走错了门。**务必先验证**（见下方向导第 3 步）。
3. **邮件正文 = 最近 N 天的滚动窗口**。本地 `out/jobs_<日期>.html` 存档永远是全量历史，
   但邮件只发窗口内（默认 7 天）的岗位，由 `output.mail.window_days` 控制。

## 交互式引导流程（按顺序与用户对话）

### 第 0 步 · 环境自举（干净电脑必做，且只需一次）

**先跑这一步，任何新机器上都是第一步。**

```bash
python scripts/bootstrap.py
```

它会：
- 探测本机 python，在技能目录下建**独立 venv**（`.venv`，不污染用户环境）；
- 把依赖（feedparser / requests / beautifulsoup4 / lxml / PyYAML）装进去；
- 校验依赖可导入，并打印**之后该用哪个 python 跑流水线**。

跑完后，**后续所有脚本命令都要用 bootstrap 打印的那个解释器**，例如：

```bash
"<venv-python>" scripts/run_pipeline.py
```

> 若用户机器 pip 里已有这些依赖，bootstrap 会秒过并直接告诉你可以用系统 python。
> 若报「无法联网 / pip 安装失败」，说明该环境没有 PyPI 访问权限 —— 让用户
> 换用能联网的 python，或提前 `pip install -r requirements.txt`。
> 只用 `--check` 可快速探测而不安装。

### 第 1 步 · 探测是否已配置

```bash
ls config.yaml 2>/dev/null && echo "已配置" || echo "未配置"
```

- **未配置** → 走「首次接入」流程（第 2~5 步）。
- **已配置** → 只有用户想换号/改关键词时才重跑向导；否则直接跳到「日常运行」。

### 第 2 步 · 问清楚要监听什么

一次问清这几个关键信息（能默认的给默认值，别逐个逼问）：

| 要素 | 说明 | 默认 |
|------|------|------|
| 目标公众号 | 名称 or 微信读书阅读页链接 / `MP_WXS_` ID | 必填，没有就跑不了 |
| 内容类型 | 招聘 / 招标采购 / 政策通知 / 自定义关键词 | 招聘 |
| 收件邮箱 | 发到哪 | 必填，没有就追问 |
| 频率 | 每天 / 每周 / 每天几点 | 每天 |

拿到公众号后，**如果用户只给了名称、没给链接**，先让用户提供阅读页链接或 ID；
本 skill 不能凭名称反查 bookId（微信读书没有公开的名称→bookId 接口）。

### 第 3 步 · 拿 cookie（采集前置）

用户需先在浏览器登录 `weread.qq.com` 并关注目标号。然后：

```bash
python scripts/get_cookie.py --browser auto
```

- `auto` 会自动探测本机装了哪些浏览器（Edge/Chrome/Brave）并逐个尝试；也可显式
  指定 `--browser edge|chrome|brave`。
- 成功 → 把打印出的 cookie 串写进 `config.yaml` 的 `source.weread.cookie`，
  `cookie_from: manual`。
- 失败 → 脚本会打印**手动获取指引**（F12 复制 Cookie 整行），照做即可。
- 更细的排错见 `references/cookie-troubleshooting.md`。

> 若用户已有可用的 `config.yaml`（cookie 已填），跳过本步。

### 第 4 步 · 生成配置（含强制验证）

**非交互式**（推荐，Agent 直接调）：

```bash
python scripts/setup_wizard.py \
  --book-id "<阅读页链接或 MP_WXS_ID>" \
  --account "公众号名称" \
  --to "收件邮箱" \
  --preset 招聘 \
  --window-days 7 \
  --yes
```

**交互式**（用户自己在终端跑）：

```bash
python scripts/setup_wizard.py
```

向导会：
- 把用户粘的任意形式（链接/编码串/纯 ID）还原成 bookId；
- **拉取该号最近 5 篇文章做验证**，把公众号名与标题打给用户确认 —— 防止选错号；
- 备份旧 config、写出新的 `config.yaml`。

> ⚠️ 如果验证时显示「没拉到任何文章」，多半是 cookie 失效或该号内容为空。
> 先解决 cookie，再谈其它。

### 第 5 步 · 先小跑一次，确认链路

```bash
python scripts/run_pipeline.py --limit 20 --dry-run   # 只看过滤+抽取，不落库
python scripts/run_pipeline.py --limit 20             # 真跑，生成报告
```

看 `[2/5] 过滤` 那几行：如果**目标文章被漏**或**无关内容混入**，
调 `config.yaml` 的 `filter` 关键词，别去改代码。

### 第 6 步 · 交付日报

跑通后，正文落在 `out/mail_body_<日期>.html`。**发送前必做链接校验**：

```bash
python scripts/check_links.py out/mail_body_<日期>.html
```

- 全部 `OK` → 读该 HTML 文件，用邮件工具发送（见「邮件投递」）。
- 有 `BAD` → 检查是否含 `~`（应为 `_`）；把 BAD 链接原样报告给用户，别硬发。

## 邮件投递（两种后端）

`config.yaml` 的 `output.mail.backend` 决定投递方式：

### backend: agentmail（当前默认，走 Agent 邮箱）

流水线**只产待发送清单 + 落盘 HTML 正文**，不直接发信。Agent 需要：

1. 用 Read 读取 `out/mail_body_<日期>.html` 的**完整内容**；
2. 调用邮件工具发送：`to` = 用户邮箱，`body_format: "HTML"`，
   `body` = 上一步读到的**完整 HTML 原文**（不要缩写成摘要、不要改成附件、
   不要删条目），`subject` 建议格式：`【<公众号名>】信息日报 <日期>（近N天 <条数> 条）`；
3. 用户明确授权自动发送时可带 `skip_confirmation: true`。

> **附件 file_id 约 6 小时过期**，必须当天上传当天用，禁止复用历史 file_id。

### backend: smtp（无人值守首选）

凭证长期有效，不存在 token 过期问题。在 `config.yaml` 填 `smtp_host / smtp_user /
smtp_password`（QQ 邮箱用**授权码**，不是登录密码），流水线会直接发出，无需 Agent 干预。

### 正文太长怎么办

邮件工具单条正文有长度限制。**约 12000 字符**为安全线：

- 正文 ≤ 12KB → 单封发出。
- 超了 → 拆成多封，每封 **25~29 条完整 HTML**（保持 HTML 结构完整，别截断标签），
  subject 后缀加「· 第 N/M 部分」。

## 日常运行

> 首次在新机器上跑之前，先执行一次 `python scripts/bootstrap.py`（见第 0 步）。
> 之后用 bootstrap 报告里的解释器运行即可。

```bash
python scripts/run_pipeline.py                 # 按 ./config.yaml 跑全流程
python scripts/run_pipeline.py --no-mail       # 只出本地报告，不产待发送清单
python scripts/run_pipeline.py --source mock   # 用内置离线数据验证链路
```

做定时任务时，用调度工具创建自动化，prompt 里点明：
「运行 tool-wechat-jobs-monitor skill 的流水线并把 HTML 日报邮件发给 <邮箱>」，
并显式写清目标公众号名、时间窗、收件人（自动化每次是全新上下文，不会记得本次对话）。

## 排错速查

| 症状 | 原因 | 处理 |
|------|------|------|
| `errCode=-2012` / 登录超时 | cookie 过期 | 重跑 `get_cookie.py` 刷新 cookie 写回配置 |
| 验证号时拉到 0 篇 | cookie 失效 / 号选错 | 先修 cookie，再确认 bookId |
| 报告里 0 条候选 | 关键词太窄 / 号选错 | 调 `filter` 关键词，或核对公众号 |
| 链接全 BAD（31KB 页面） | token 里 `~` 没还原成 `_` | 检查 `wjobs/weread.py` 的 `review_to_url()` |
| mock 源链接全 BAD | **正常**，示例数据是假链接 | 换真实 `weread` 源即正常 |
| `ModuleNotFoundError` | 依赖没装（干净电脑常见） | `python scripts/bootstrap.py` 一键装进独立 venv |
| `bootstrap.py` 报 pip 无法联网 | 环境无 PyPI 权限 | 换联网 python，或手动 `pip install -r requirements.txt` |
| `收件人未配置` | `output.mail.to` 为空 | 填邮箱，或重跑 `setup_wizard.py` |

依赖：`feedparser` `requests` `beautifulsoup4` `lxml` `PyYAML`（关键）；
`browser-cookie3`、`websocket-client`（可选，cookie 自动读取用）。
**统统一条命令搞定**：`python scripts/bootstrap.py`。

## 参考文档

- `references/select-account.md` —— 为什么选号最容易翻车、如何 30 秒验证
- `references/cookie-troubleshooting.md` —— cookie 各条获取路线的取舍与坑
- `references/config-reference.md` —— config.yaml 每个字段的含义
