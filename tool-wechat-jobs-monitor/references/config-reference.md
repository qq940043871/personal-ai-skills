# config.yaml 字段参考

由 `setup_wizard.py` 生成，也可手改。改完直接重跑 `run_pipeline.py`。

## source —— 采集源

| 字段 | 说明 |
|------|------|
| `type` | `weread`（直连微信读书，零依赖）/ `rss`（上游采集服务）/ `mock`（离线演示） |
| `account_name` | 公众号名称，仅用于报告标题与打标 |
| `max_items` | 单次最多处理多少篇文章 |
| `fetch_workers` | 抓正文并发数；站点慢就别开大 |
| `timeout` | 请求超时（秒） |

### type: weread 专有

| 字段 | 说明 |
|------|------|
| `weread.book_id` | 目标公众号 ID。链接 / 编码串 / `MP_WXS_ID` 都认，自动还原 |
| `weread.cookie_from` | `browser`（自动从浏览器读）/ `manual`（用下面手填的） |
| `weread.browser` | `chrome` / `edge` / `brave` / `firefox` |
| `weread.cookie` | cookie 串（含 `wr_skey=...`） |

### type: rss 专有

| 字段 | 说明 |
|------|------|
| `rss_url` | 订阅地址，如 `http://127.0.0.1:8001/feeds/MP_WXS_xxx.rss` |

## filter —— 关键词过滤

| 字段 | 说明 |
|------|------|
| `title_include` | 【标题】命中任一即认为是目标文（最强信号） |
| `body_include` | 【正文】标题没命中时的兜底召回 |
| `exclude` | 命中任一直接排除（一票否决，但标题明确命中的优先信任标题） |
| `require_title_hit` | `true` = 必须命中标题才算（更准，推荐）；`false` = 标题或正文命中即可 |

调优原则：**漏了就加词，脏了就加排除词**，别改代码。

## extract —— 抽取

| 字段 | 说明 |
|------|------|
| `mode` | `rule`（纯正则，离线零成本）/ `llm`（调大模型，需填 api_key） |
| `contact_email_deny` | 运营方自己的投稿邮箱域名（自动从「联系方式」里剔除，按需增删） |
| `llm.base_url` / `api_key` / `model` | 任意 OpenAI 兼容端点（DeepSeek / 通义 / 本地 vLLM…） |

`llm` 模式失败会**自动回退 **`rule`，不会让流水线空手而归。

## output —— 输出与投递

| 字段 | 说明 |
|------|------|
| `data_dir` | SQLite 去重库目录（相对工作目录） |
| `out_dir` | 报告输出目录 |
| `formats` | `["md", "html"]`，本地存档格式 |
| `mail.enabled` | 是否投递 |
| `mail.backend` | `agentmail`（走 Agent 邮箱工具）/ `smtp`（直接发） |
| `mail.to` | 收件邮箱列表（**必填**，为空时投递会明确报错） |
| `mail.agentmail_from` | 仅展示用；发件人实际由 Agent 登录账号决定，无需配置 |
| `mail.attach` | 是否附上 HTML/MD 附件（默认 false，正文本身即完整 HTML） |
| `mail.window_days` | 邮件正文覆盖最近 N 天（按发布日算，含今天）。`1`=今天，`7`=一周一覆盖 |
| `mail.smtp_*` | backend=smtp 时填；QQ 邮箱用**授权码**不是登录密码 |

### window_days 是滚动窗口

一条岗位只要还在 N 天窗口内，每天的邮件都会出现它。好处是漏看某天不丢信息。
**本地 `out/jobs_<日期>.html` 存档不受影响，永远是全量历史。**

## 环境变量

| 变量 | 作用 |
|------|------|
| `WJ_HOME` | 指定工作目录（config/data/out 的根）。定时任务里显式指定更稳 |
| `WJ_CONFIG` | 直接指定 config.yaml 路径，优先级高于 WJ_HOME/config.yaml |
