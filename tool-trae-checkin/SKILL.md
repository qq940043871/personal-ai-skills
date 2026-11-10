---
name: tool-trae-checkin
description: Trae CN 桌面端每日签到（每日领 100 积分）自动化。自动拉起/聚焦 Trae CN，打开左下角账号菜单，点击「每日领 100 积分」按钮，回拍截图验证「已签到」。当用户说"trae签到""trae 每日签到""trae 领积分""帮我签到 trae""trae 打卡"时使用。
author: hasWhere
agent_created: true
---

# Trae CN 每日签到自动化

固化「打开头像菜单 → 点每日领积分 → 确认已签到」流水线。Trae CN 是 Electron 应用，UIA 控件树为空，只能截图视觉定位 + 屏幕坐标点击（与 tool-electron-gui-click / tool-daily-checkin 同一技术路线，但针对 Trae 做了两处专门处理）。

## 快速使用

脚本目录：`scripts/trae_checkin.py`，配置：`config/trae.json`，截图输出：`shots/`。

```bash
# 执行每日签到（自动拉起 Trae → ESC 复位 → 点头像 → 截菜单 → 点签到 → 回拍 → 自动关菜单）
python trae_checkin.py run

# 无人值守模式：签到完直接退出 Trae（仅当 Trae 是本次脚本拉起时才会退出）
python trae_checkin.py run --quit-app

# 只打开账号菜单截图，查看今天是「签到」还是「已签到」（不点击领取）
python trae_checkin.py menu

# 截主窗口 / 窗口内坐标点击 / 放大裁剪读坐标（校准用）
python trae_checkin.py shot
python trae_checkin.py click <x> <y> [wait]
python trae_checkin.py crop <img> <x1> <y1> <x2> <y2> [scale]
```

## 收尾：自动关闭（默认开启）

- `run` 在 after 回拍后**自动发两次 ESC 关闭账号菜单**（第一次兜二级弹窗、第二次关菜单），再拍一张 `final` 截图确认界面复位，输出标记 `DONE_MENU_CLOSED`。不会再留菜单挂在屏幕上。
- 若希望签到完**连 Trae 应用一起退出**（计划任务无人值守场景）：用 `run --quit-app` 或把配置 `quit_app_after` 改 true。
- **安全护栏**：退出应用只在「Trae 由本次脚本拉起」时生效；如果 Trae 本来就是用户开着的（`launched_by_script: False`，日常对话中执行都是这种情况），会打印 `SKIP QUIT` 并降级为只关菜单，绝不杀掉用户在用的工作区。退出时先走 WM_CLOSE 优雅关闭，8s 未关再 `taskkill /T /F` 兜底。

## 执行约定（agent 必做）

1. 跑 `run`。
2. **必须用 Read 工具查看输出的 menu / after 截图**，脚本不知道点没点中：
   - 菜单图中按钮为灰色「已签到」→ 今天已签，`after` 无变化属正常，报告「今日已签到」。
   - 菜单图中为彩色「签到/领取」态，`after` 中变「已签到」或出现「签到成功/+100 积分」→ 报告签到成功（可顺带记录积分余额，菜单头像右侧有数字）。
   - 菜单没弹出来 / 点到别处 → 按下方「重新校准」处理。
3. Read `final` 截图确认菜单确实已关闭（脚本只发 ESC，不知道关没关掉）。
4. 用户只说"签到"且配置了多个签到应用时，Trae 与其他应用逐个执行、各自回拍确认。

## 签到入口与已录入坐标

入口路径：**左下角账号栏（头像 + 昵称 + 免费）→ 弹出菜单 →「每日领 100 积分」行右侧按钮**。菜单位置锚定窗口左下角，与窗口宽度无关；坐标用 anchor=bl + dx/dy（dy 负=向上），基于 1936×1168 最大化窗口实测（2026-11-01 录入）：

| 步骤 | dx | dy | 窗口内绝对坐标（高 1168 时） |
|---|---|---|---|
| 点头像栏 | 60 | −30 | (60, 1138) |
| 点签到按钮 | 248 | −425 | (248, 743)，按钮热区约 x 207–290 / y 724–762 |

## 两个 Trae 专门处理（与通用签到脚本的差异）

1. **主窗口不能按标题找**：Trae 主窗口标题随活动视图变化（实测为 `Agent`，不是 "Trae CN"）；标题恒为 "Trae CN" 的反而是托盘区 105×105 小窗。脚本按 **进程名 `Trae CN.exe` + 类名 `Chrome_WidgetWin_1` + 面积最大（>800×600）** 定位主窗口，多开工作区时取最大窗口。
2. **点头像前先发一次 ESC**：菜单已展开时再点头像会把菜单关掉。先 ESC 复位，保证这一点击必然是「开菜单」。已签到时签到按钮置灰，点击零副作用，因此 `run` 幂等、可重复跑。

## 关键坑

- **启动必须借 explorer 的手**：从沙箱/受限父进程直接 Start-Process / subprocess 拉起 Electron 会静默 exit 0。脚本内置 `explorer.exe "<exe>"`（若仍秒退，Shell 调用时配 `dangerouslyDisableSandbox`）。启动后等 `launch_wait`（默认 22s）。
- **截图与窗口 rect 1:1**：`capture_as_image()` 的像素坐标 + 窗口左上偏移 = 屏幕坐标，多屏负坐标也成立（rect.left 可为 −8）。
- **点击前后都要 set_focus**，点击发的是真实鼠标输入（SetCursorPos + mouse_event），Electron 可正常接收。
- **未实测的分支**：录入当天（2026-11-01）账号已是「已签到」，彩色「签到」按钮的实际文案、点击后是否弹签到日历/Toast 尚未观测。第一次在未签到日跑时，务必 Read 截图确认；若点击后弹出的是二级弹窗（如签到日历），可能需要在 `steps` 里追加第三击（参考 tool-daily-checkin 的 clicks=2 教训）。
- **冷启动首次 run 可能点空（2026-11-05 实测）**：`--quit-app` 把 Trae 关掉后隔天再跑，22s `launch_wait` 之后窗口还在渲染（before 图偏暗、menu 图里没菜单），第一次点头像的点击被丢掉，紧接着那一次「点签到」实际点在了编辑器里。判据：menu 图完全看不到账号菜单。处置：直接再跑一次 `menu`（此时 UI 已就绪，菜单能正常弹出并截图确认），确认后再跑 `run`；`launch_wait` 已由 22 调到 30。**不要**把这种情况当成坐标漂移去改 steps。
- **`--quit-app` 的保护会让「先跑 menu 校准过」的那次 run 拒绝退出**：`menu` 把 Trae 拉起后脚本自己退出，随后 `run` 看到的 `launched_by_script` 是 False，于是打印 `SKIP QUIT`。若确实要无人值守后不留进程，可先用 WM_CLOSE（`Get-Process ... | CloseMainWindow()`）收尾；实测 Trae 会忽略该请求（有更新提示/会话进行中时），此时**不要** `/F` 强杀——留着比杀掉安全。
- **DPI/侧栏变化会使锚点偏移**：改显示器缩放、Trae 侧栏布局大改后若点偏，重新校准。

## 重新校准

1. `python trae_checkin.py shot` → Read 截图，找到左下角账号栏。
2. 头像栏点一下：`python trae_checkin.py click 60 1138`（或目测新坐标）。
3. `python trae_checkin.py menu` 得菜单图；`crop` 放大签到行读按钮中心像素 `(x, y)`。
4. 新坐标换算：`dx=x, dy=y-窗口高`（窗口高从 `shot` 打印的 rect 读取），改 `config/trae.json` 的 steps。
5. 再跑一次 `run`，Read 回拍确认。

## 配置字段（config/trae.json）

| 字段 | 含义 |
|---|---|
| `process` | 进程名，主窗口定位用 |
| `exe` | 未运行时经 explorer 启动的绝对路径 |
| `launch_wait` | 启动后等待秒数 |
| `anchor` | 固定 `bl`（窗口左下角） |
| `close_menu_after` | `true`（默认）签到回拍后自动 ESC 关闭账号菜单并拍 final 图；设 `false` 则保留菜单 |
| `quit_app_after` | `false`（默认）设 `true` 时签到后退出 Trae，**仅对脚本自己拉起的实例生效**；命令行 `--quit-app` 等价 |
| `steps[].dx/dy` | 相对左下角偏移；dy 负值向上 |
| `steps[].wait_after` | 该步点击后等待秒数（头像 1.2 够菜单展开，领取后留 2.2 接 Toast/弹窗） |
| `shot_dir` | 截图目录，默认 skill 下 `shots/` |
