#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
probe_blender.py —— 探测本机 Blender 环境（纯标准库，任意 python 可跑）

检查项：
1. Blender 可执行文件（PATH + Windows/macOS/Linux 常见安装路径）
2. 版本（blender --version 首行）
3. blender-mcp addon 是否安装（4.2+ extensions / 旧版 scripts/addons）
4. uvx 是否可用（blender-mcp MCP server 依赖 `uvx blender-mcp` 启动）

exit 0 = 找到 Blender（可走实景路线 B）；exit 1 = 无 Blender（走程序化降级路线 A）。
"""
import json
import os
import re
import shutil
import subprocess
import sys
import glob

APPDATA = os.environ.get("APPDATA", "")


def find_blender_exe():
    """返回 (路径或None, 来源)"""
    p = shutil.which("blender")
    if p:
        return p, "PATH"
    candidates = []
    if sys.platform == "win32":
        candidates += glob.glob(r"C:\Program Files\Blender Foundation\Blender *\blender.exe")
        candidates += glob.glob(r"C:\Program Files (x86)\Blender Foundation\Blender *\blender.exe")
        local = os.environ.get("LOCALAPPDATA", "")
        if local:
            candidates += glob.glob(os.path.join(local, "Programs", "Blender Foundation",
                                                "Blender *", "blender.exe"))
    elif sys.platform == "darwin":
        candidates += glob.glob("/Applications/Blender.app/Contents/MacOS/Blender")
    else:
        candidates += ["/usr/bin/blender", "/usr/local/bin/blender", "/snap/bin/blender"]
        candidates += glob.glob(os.path.expanduser("~/.local/bin/blender*"))
    for c in candidates:
        if os.path.isfile(c):
            return c, "常见安装路径"
    return None, None


def blender_version(exe):
    try:
        out = subprocess.run([exe, "--version"], capture_output=True, text=True,
                             timeout=30, creationflags=0x08000000 if sys.platform == "win32" else 0)
        m = re.search(r"Blender (\d+\.\d+\.\d+)", out.stdout or "")
        return m.group(1) if m else (out.stdout or "").splitlines()[0:1] or None
    except Exception as e:
        return "探测失败: %s" % e


def config_roots(exe):
    """Blender 用户配置根目录列表（可能有多个版本目录）"""
    roots = []
    if sys.platform == "win32" and APPDATA:
        roots.append(os.path.join(APPDATA, "Blender Foundation", "Blender"))
    elif sys.platform == "darwin":
        roots.append(os.path.expanduser("~/Library/Application Support/Blender"))
    else:
        roots.append(os.path.expanduser("~/.config/blender"))
        roots.append(os.path.expanduser("~/.var/app/org.blender.Blender/config/blender"))
    out = []
    for r in roots:
        if os.path.isdir(r):
            out += [os.path.join(r, d) for d in os.listdir(r) if d[0].isdigit()]
    return out


def check_mcp_addon(exe):
    """探测 blender-mcp 插件（socket server 端）"""
    hits = []
    for root in config_roots(exe):
        for pattern in (
            os.path.join(root, "extensions", "blender_org", "blender_mcp*"),
            os.path.join(root, "extensions", "*", "blender_mcp*"),
            os.path.join(root, "scripts", "addons", "blender_mcp*"),
        ):
            hits += glob.glob(pattern)
    return hits


def check_mcp_server():
    """MCP server 端：uvx blender-mcp"""
    uvx = shutil.which("uvx") or shutil.which("uv")
    pip = shutil.which("pip") or shutil.which("pip3")
    return {"uvx": uvx, "pip": pip}


def main():
    exe, src = find_blender_exe()
    report = {
        "blender": exe,
        "source": src,
        "version": blender_version(exe) if exe else None,
        "mcp_addon": check_mcp_addon(exe) if exe else [],
        "mcp_server": check_mcp_server(),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print()
    if not exe:
        print("结论: 未找到 Blender —— 走路线 A（程序化几何交付）。")
        print("升级路径: 安装 https://www.blender.org/download/ 后重跑本脚本；")
        print("          实景还原还需 blender-mcp 插件 + `uvx blender-mcp`（见 references/blender-mcp.md）。")
        return 1
    print("结论: Blender %s 可用（%s）—— 可走路线 B（实景还原）。"
          % (report["version"], src))
    if not report["mcp_addon"]:
        print("注意: 未检测到 blender-mcp 插件 —— MCP 交互建模不可用，")
        print("      但 CLI 批处理（export_webgl.py）与已有 .blend 优化仍可跑。")
    if not report["mcp_server"]["uvx"]:
        print("注意: 未找到 uvx/uv —— blender-mcp MCP server 无法启动，装 uv 后在")
        print("      ~/.workbuddy/mcp.json 加 {\"command\":\"uvx\",\"args\":[\"blender-mcp\"]}。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
