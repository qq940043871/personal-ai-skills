---
name: tool-daily-checkin
description: 桌面应用每日签到/领福利自动化。为 Windows 桌面应用（Electron 或普通 GUI）记住"签到按钮在哪"，之后一句话完成每日签到：自动拉起应用、截图、点击签到按钮、回拍验证。当用户说"签到""领一下""每日打卡""帮我点一下 X 的签到"时使用。
author: hasWhere
agent_created: true
---

# 每日签到自动化

把"打开应用 → 找到签到按钮 → 点击 → 确认成功"这条流水线固化下来。核心是**配置记忆**：每个应用的签到按钮坐标只需录入一次，之后每天一句话执行。

## 快速使用

```bash
# 列出已配置的应用
python checkin.py list

# 执行签到（自动启动 → 截图 → 点击 → 回拍验证）
python checkin.py run zcode

# 只截图看当前界面（用于首次定位按钮坐标）
python checkin.py shot zcode

# 录入/更新一个应用的签到点
python checkin.py add <app_id> --title "窗口标题" --exe "C:\path\app.exe" --x 198 --y 648
```

脚本路径：`scripts/checkin.py`，配置：`config/checkin.json`。

## 录入新应用的标准流程

1. **先人工把按钮位置找出来**：`python checkin.py shot <app_id>` 截图 → 用 Read 看图片 → 读出按钮中心在窗口内的像素坐标 (x, y)。
2. **写入配置**：`python checkin.py add <app_id> --title "窗口标题子串" --exe "exe 绝对路径" --x <x> --y <y>`
3. **试跑一次**：`python checkin.py run <app_id>`，然后 Read 回拍截图确认是否弹出"签到成功"。
4. 若没成功，多半是坐标偏了或按钮位置每天会变，回到第 1 步重新定位并 `add` 覆盖。

## 配置字段

| 字段 | 含义 |
|---|---|
| `title` | 窗口标题子串，用于定位窗口（不依赖 PID，重启也不失效） |
| `exe` | 应用 exe 绝对路径，未运行时用它启动 |
| `anchor` + `dx`/`dy` | **推荐**：锚定模式。anchor ∈ `bl`(左下)/`br`/`tl`/`tr`/`c`，dx/dy 为相对该角的偏移（dy 负值=向上）。窗口缩放不失效 |
| `x` / `y` | 兼容旧模式：按钮在**窗口截图内**的绝对像素坐标（窗口尺寸一变就失效，尽量别用） |
| `clicks` | 点击次数，默认 1；若界面常有模态弹窗挡路，**设 2**（第一击被遮罩吃掉） |
| `launch_wait` | 启动后等待秒数，Electron 类建议 15~20 |
| `shot_dir` | 截图输出目录 |

坐标计算规则：锚定模式 `屏幕坐标 = 窗口角 + (dx, dy)`；绝对模式 `= 窗口左上 + (x, y)`。截图与窗口 rect 是 1:1 像素对应。

## 关键坑（血泪实测）

- **启动必须借 explorer 的手**：从受限父进程直接 `Start-Process` / bash 直跑 / Python subprocess 启动 Electron 应用，会**静默退出**（exit code 0，零报错）。必须走 ShellExecute：`explorer.exe "C:\path\App.exe"`。脚本已内置此逻辑。
- **模态弹窗吞第一击**：屏幕中间有弹窗时，第一次点目标位置只会关弹窗/被遮罩吸收，要点第二次。把 `clicks` 设成 2 即可（多点的代价通常只是关掉弹窗）。
- **Electron 的 UIA 控件树是空的**（未开可访问性），别指望 pywinauto 控件定位，只能截图视觉定位。
- **坐标优先用锚定模式**（anchor + dx/dy）：签到按钮通常锚定在窗口角落，窗口一缩放绝对坐标就全废（实测 1200×800 录的坐标在 1936×1168 窗口下直接指到别处）。录入时若窗口尺寸日后可能变化，务必用 anchor 模式。
- 每次执行完**必须 Read 回拍截图确认**，别只看脚本返回码——脚本并不知道按钮点没点中。

## 每日执行约定

用户说"签到"/"领一下"时：先 `list` 看有哪些应用，再逐个 `run`，每个都 Read 回拍截图确认结果，最后汇总报告（成功 / 未找到按钮 / 应用起不来）。
