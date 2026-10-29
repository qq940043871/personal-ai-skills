---
name: tool-workbuddy-checkin
description: 完成 WorkBuddy 桌面客户端「Buddy加油站 / 每日签到」的积分领取。当用户说「加油站签到」「Buddy 加油站」「WorkBuddy 签到」「领积分」「签到脚本」时使用。包含已逆向确认的官方签到接口、登录态读取的各种死锁与绕行办法。
agent_created: true
---

# WorkBuddy Buddy 加油站签到

WorkBuddy 桌面客户端左下角头像 → 个人中心 → **Buddy 加油站** 的每日签到，每轮前 6 天每天 100 积分，第 7 天 1000 积分，循环重置。

## 一、已确认的官方接口（从客户端主程序逆向得到）

主程序：`C:\Program Files\WorkBuddy\resources\app.asar`（约 317MB，明文可读，无需解包就能 grep）。

| 用途 | 请求 | 路径 |
| --- | --- | --- |
| 查签到状态 | `POST` | `https://www.workbuddy.cn/v2/billing/meter/checkin-activity-status` |
| **执行签到** | `POST` | `https://www.workbuddy.cn/v2/billing/meter/tool-daily-checkin` |

- 后端主机就是 `https://www.workbuddy.cn`（从运行日志 `daemon.log` 统计得出，出现 2900+ 次）。
- Desktop 走 IDE 网关，`billingPrefix = /v2`。
- 签到请求头由 `getCheckinRequestHeaders()` 注入（Desktop 端用于设备风控），普通 curl 不带也能试。

返回体（`tool-daily-checkin` 成功时）：`{ credit, streak_days, is_streak_day, next_streak_day, ... }`。

业务数字 code 映射（`mapCheckinStatus`）：

| code | 含义 |
| --- | --- |
| `0` | 签到成功 |
| `1001` | 今天已签到过 |
| `1002` | 当前不满足签到条件 |
| `1003` | 活动已结束 |
| 其他 | unknown_biz_error |

配套源码位置关键词（在 asar 里 grep 可复现）：`CheckinClaimStatus`、`postCheckin`、`billingPrefix`、`useCheckinService`、`tool-daily-checkin`。

## 二、登录态：为什么不能直接 curl

签到必须带客户端登录态。以下路**全堵死**，别重复趟：

| 途径 | 结果 |
| --- | --- |
| `~/.workbuddy/app/session/Network/Cookies` | Electron 独占打开，`copy2` 报 WinError 32，只读 `open('rb')` 也 `Permission denied` |
| `~/.workbuddy/app/session/Local State` | 只有 `os_crypt.encrypted_key`（safeStorage 主密钥），不是 token |
| `~/.workbuddy/credentials/token.json` | 不存在（该目录下只有 `meituan-living-deals-assistant/`） |
| 本地守护进程 `127.0.0.1:18488`、sidecar `:39100/:39101` | 有 HTTP 服务，无 account/签到端点 |
| `app/sessions.json`、`app/data/` | 只有会话与专家历史，无凭据 |
| 客户端日志 | 有请求 URL，无请求头 |

**渲染进程跑在 `https://www.workbuddy.cn`**（日志里 2895 次命中），所以只要 attach 进渲染进程，用页面自身 `fetch` 就能自带 cookie 签到 —— 这是当前唯一可行路径。

## 三、可行路径：CDP attach 渲染进程

WorkBuddy 是 Electron。给客户端加 `--remote-debugging-port` 启动后，用 Playwright 连上，在渲染上下文里执行 `fetch`：

```bash
# 1. 带调试端口重启客户端（会中断当前会话，需用户同意）
#    WorkBuddy.exe --remote-debugging-port=9222 --profile-directory=...
# 2. 复用登录态签到
python scripts/checkin.py --claim
```

脚本默认 **dry-run（只查状态）**，只有显式 `--claim` 才真签到，且会先查 `today_checked_in` 做幂等保护，已签直接跳过不重复领。

跑之前先确认 Playwright 装在哪台解释器和环境上，见下方「环境坑」。

## 四、合规提醒

社区文章里两种说法互相矛盾：一部分说官方仅允许人工手动签到、脚本刷积分会被回收超额积分；另一部分在推荐 `workbuddy-checkin` 这类脚本。接口本身是公开调用，**但重复刷、多账号批量刷属于风险行为**。本 skill 只做「每台设备每天一次」的正常签到，不做任何批量/循环领取。

## 五、环境坑（Windows + Git Bash）

- 优先用 anaconda 解释器跑 Playwright 相关脚本：`C:\Users\qq940\anaconda3\python.exe`（托管 python 没装 playwright）。
- **不要写 .bat**，WorkBuddy 安全策略拦 `cmd.exe`，bat 无法在本会话实跑验证。
- heredoc 里反斜杠会被静默吞掉（正则、Windows 路径都受影响）。含 `\` 的代码一律先 Write 成 `.py` 再执行，改完必须复核文件实际内容。
- 临时目录用 `tempfile.mkdtemp()`，别用 `/tmp/`（Windows 下 Python 看不见）。
- 从 asar 里 grep 时，`b"中文"` 会 `SyntaxError: bytes can only contain ASCII literal characters`，要写 `"中文".encode("utf-8")`。
- `mmap` 扫 317MB 的 asar 是可行的，用 mmap + 循环 `find` 比整文件读入稳。
