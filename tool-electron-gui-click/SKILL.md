---
name: tool-electron-gui-click
description: 自动化操作 Windows 上已运行的 Electron 桌面应用（ZCode/Cursor/Trae 等）的 UI：截图定位按钮并坐标点击。当用户说"打开 X 应用并点击某按钮"、"帮我在 X 里点一下"而该应用无网页版时使用。
author: hasWhere
agent_created: true
---

# Electron 桌面应用 GUI 点击自动化

适用场景：目标应用是 Electron（`Chrome_WidgetWin_1` 窗口类），UIA 控件树为空 Pane（可访问性未开启），无法用 pywinauto 控件定位。

## 核心思路

**控件树定位 → 失败则截图视觉定位 → 屏幕坐标换算 → mouse.click → 回拍截图验证。**

## 步骤

1. **找进程**：`tasklist //FI "IMAGENAME eq <App>.exe"`，内存最大的那个通常是主进程（有窗口的）。
2. **找窗口**：pywinauto `Desktop(backend="uia")` 遍历 `desktop.windows()`，按 PID + 非空标题过滤。窗口 rect 若为 (0,0,0,0) 说明最小化，先 `restore()` + `set_focus()`。
3. **截图**：`w.capture_as_image()` 保存 PNG，用 Read 工具看图，读出目标按钮在截图内的像素坐标 (x, y)。
4. **换算并点击**：屏幕坐标 = `(rect.left + x, rect.top + y)`（capture_as_image 与窗口 rect 是 1:1 像素对应）。用 `pywinauto.mouse.click(coords=(sx, sy))`。
5. **验证**：点击后等待 1.5~2.5s，再 `capture_as_image()` 回拍确认结果。

## 坑（实测）

- **应用未运行时，从沙箱/受限父进程直接启动会静默退出（exit 0，无任何输出）**：Start-Process、bash 直接跑 exe、Python subprocess 全都秒退。解法：让 explorer 当父进程走 ShellExecute——
  `explorer.exe "C:\path\to\App.exe"`（必要时配 dangerouslyDisableSandbox）。此法已实测可救活 ZCode。
- **模态弹窗遮罩会吸收第一击**：若屏幕中间有模态弹窗挡路，第一次点击目标位置只会关掉弹窗/被遮罩吃掉，**必须点第二次**才真正命中按钮。弹窗的 X 按钮和 ESC 键可能都无效，别死磕，直接点目标两次。
- **点击前后都要 `set_focus()`**，否则点击可能落到别的窗口。
- **窗口可能被最小化**：rect 全 0 时先 restore，等待 1s 再截图。
- **PID 会变**：应用重启后主进程 PID 更新，不要硬编码旧值；按"内存最大的进程"或重新 tasklist 查。
- pywinauto 的 `mouse.click` 发送的是真实系统输入（SetCursorPos + mouse_event），Electron 能正常接收。
- 含反斜杠/正则的 Python 代码一律先 Write 成 .py 文件再跑，不要走 heredoc 内联。

## 附带脚本

`scripts/electron_click.py` —— 通用命令行工具：

```bash
python electron_click.py shot "<窗口标题子串>" out.png
python electron_click.py click "<窗口标题子串>" <x> <y> [wait_sec] [out.png]
```

自动按标题子串找窗口（不依赖 PID）、自动 restore/focus、截图 / 点击并回拍验证。
