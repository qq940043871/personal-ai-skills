# -*- coding: utf-8 -*-
r"""获取 / 刷新微信读书 cookie（skill 版，跨机器尽量通用）。

三条路，按顺序尝试，哪条通就用哪条：
  1. **CDP 直读**（推荐）：用带调试端口的浏览器读 cookie。需要该浏览器
     登录过 weread.qq.com。本机 Edge/Chrome 127+ 对默认 profile 的 cookie
     用 v20 App-Bound 加密，第三方离线解不开，所以走浏览器的调试端口是正解。
  2. **browser-cookie3 直读**：装了该库且浏览器允许读时可用（新版常被锁）。
  3. **手动粘贴**：把 F12 里的 Cookie 整行粘进来（保底，永远可行）。

本脚本只负责「拿到 cookie 并写出文件」，不直接改 config.yaml ——
避免在配置里留下半截状态。拿到后由 Agent 或用户把 cookie 写回配置。

用法：
    python scripts/get_cookie.py --browser edge            # 自动：CDP → cookie3
    python scripts/get_cookie.py --explicit-profile        # 用独立 profile（v10 可读）
    python scripts/get_cookie.py --manual                  # 打印手动指引
产物：out/cookie_fresh.txt（一行 cookie 串）；成功即打印。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from typing import Dict, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

PORT = 9222
WEREAD = "https://weread.qq.com"


# ---------------------------------------------------------------- 路径

def _browser_exe(browser: str) -> str:
    """定位浏览器可执行文件。除注册表常见路径外，也查 PATH 与用户级安装。"""
    local = os.environ.get("LOCALAPPDATA", "")
    pf = os.environ.get("PROGRAMFILES", r"C:\Program Files")
    pf86 = os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")
    cands = {
        "edge": [os.path.join(pf86, "Microsoft", "Edge", "Application", "msedge.exe"),
                 os.path.join(pf, "Microsoft", "Edge", "Application", "msedge.exe")],
        "chrome": [os.path.join(pf, "Google", "Chrome", "Application", "chrome.exe"),
                   os.path.join(pf86, "Google", "Chrome", "Application", "chrome.exe"),
                   os.path.join(local, "Google", "Chrome", "Application", "chrome.exe")],
        "brave": [os.path.join(pf, "BraveSoftware", "Brave-Browser", "Application",
                               "brave.exe"),
                  os.path.join(local, "BraveSoftware", "Brave-Browser", "Application",
                               "brave.exe")],
    }.get(browser, [])
    for p in cands:
        if os.path.exists(p):
            return p
    # 退回：从 PATH 里找（覆盖自定义安装 / winget 安装）
    import shutil as _sh
    for name in ({"edge": "msedge", "chrome": "chrome", "brave": "brave"}
                 .get(browser, browser),):
        found = _sh.which(name)
        if found:
            return found
    return ""


def detect_browsers() -> list:
    """探测本机装了哪些可用浏览器，按 edge → chrome → brave 顺序返回。"""
    return [b for b in ("edge", "chrome", "brave") if _browser_exe(b)]


def _cdp_ready(port: int) -> Optional[dict]:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version",
                                    timeout=2) as r:
            return json.load(r)
    except Exception:
        return None


# ---------------------------------------------------------------- 路线 1：CDP

def _launch(browser: str, port: int, profile: str, url: str) -> bool:
    exe = _browser_exe(browser)
    if not exe:
        print(f"  [warn] 找不到 {browser} 可执行文件")
        return False
    os.makedirs(profile, exist_ok=True)
    cmd = [exe, f"--remote-debugging-port={port}", f"--user-data-dir={profile}",
           "--no-first-run", "--no-default-browser-check", url]
    print(f"  启动：{exe}")
    print(f"  独立 profile：{profile}")
    subprocess.Popen(cmd, close_fds=True)
    for _ in range(24):
        time.sleep(0.5)
        if _cdp_ready(port):
            return True
    return False


def _cookies_via_cdp(port: int, domain: str = "weread") -> Dict[str, str]:
    try:
        import websocket
    except ImportError:
        print("  [warn] 未装 websocket-client，跳过 CDP 路线（pip install websocket-client）")
        return {}
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=3) as r:
            targets = json.load(r)
    except Exception as exc:
        print(f"  [warn] 读 targets 失败：{exc}")
        return {}
    pages = [t for t in targets if t.get("type") == "page"]
    if not pages:
        return {}
    ws_url = pages[0]["webSocketDebuggerUrl"]
    try:
        ws = websocket.create_connection(ws_url, timeout=10, suppress_origin=True)
    except Exception:
        ws = websocket.create_connection(ws_url, timeout=10, origin=None,
                                         header=["Origin: devtools://devtools"])
    try:
        ws.send(json.dumps({"id": 1, "method": "Network.enable"}))
        ws.recv()
        ws.send(json.dumps({"id": 2, "method": "Network.getCookies",
                            "params": {"urls": [WEREAD, WEREAD + "/web/mp/articles"]}}))
        while True:
            msg = json.loads(ws.recv())
            if msg.get("id") == 2:
                cookies = msg.get("result", {}).get("cookies", [])
                return {c["name"]: c["value"] for c in cookies
                        if domain in c.get("domain", "")}
    finally:
        ws.close()
    return {}


def route_cdp(browser: str, explicit_profile: bool) -> Dict[str, str]:
    print("[路线 1] CDP 读 cookie")
    if not _cdp_ready(PORT):
        # 独立 profile 用 v10 加密（可读），但要用户在这个窗口里登录过；
        # 默认 profile 更可能已登录，但 136+ 在默认目录下禁用了调试端口。
        if explicit_profile:
            profile = os.path.join(os.environ.get("TEMP", "."), f"cdp_{browser}_profile")
            if not _launch(browser, PORT, profile, WEREAD + "/web/shelf"):
                return {}
        else:
            print("  [info] 未指定 --explicit-profile，尝试连接现有调试实例；"
                  "若无，则用独立 profile 启动（需在该窗口登录过微信读书）")
            profile = os.path.join(os.environ.get("TEMP", "."), f"cdp_{browser}_profile")
            if not _launch(browser, PORT, profile, WEREAD + "/web/shelf"):
                return {}
    print("  等页面续期登录态 ...")
    time.sleep(6)
    ck = _cookies_via_cdp(PORT)
    if ck:
        print(f"  [ok] CDP 读到 {len(ck)} 条 weread cookie")
    return ck


# ---------------------------------------------------------------- 路线 2：browser-cookie3

def route_cookie3(browser: str) -> Dict[str, str]:
    print("[路线 2] browser-cookie3 读 cookie")
    try:
        import browser_cookie3
    except ImportError:
        print("  [warn] 未安装 browser-cookie3")
        return {}
    name = {"edge": "edge", "chrome": "chrome", "brave": "brave",
            "firefox": "firefox"}.get(browser, browser)
    try:
        jar = getattr(browser_cookie3, name)(domain_name="weread.qq.com")
    except Exception as exc:
        print(f"  [warn] 读取失败（新版浏览器常加独占锁）：{exc}")
        return {}
    return {c.name: c.value for c in jar}


# ---------------------------------------------------------------- 主流程

def _save(cookies: Dict[str, str]) -> int:
    if "wr_skey" not in cookies:
        print("[fail] 没拿到 wr_skey，cookie 不可用")
        return 1
    line = "; ".join(f"{k}={v}" for k, v in cookies.items())
    out = os.path.join(os.environ.get("WJ_HOME") or os.getcwd(), "out", "cookie_fresh.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(line)
    print("\n>>> COOKIE（已存 " + out + "）：")
    print(line)
    print("\n把上面这串写回 config.yaml 的 source.weread.cookie，"
          "并把 cookie_from 改成 manual。")
    return 0


def _manual_guide() -> int:
    print("""
手动获取 cookie（保底方案，永远可行）：
  1. 浏览器打开 https://weread.qq.com 并确认已登录；
  2. F12 → Network → 刷新页面 → 随便点一个请求 → 复制请求头里的 Cookie 整行；
  3. 粘到 config.yaml 的 source.weread.cookie，并把 cookie_from 改成 manual。
""")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="获取微信读书 cookie")
    p.add_argument("--browser", default="auto",
                   choices=["auto", "edge", "chrome", "brave"],
                   help="auto = 自动探测本机浏览器（推荐）")
    p.add_argument("--explicit-profile", action="store_true",
                   help="用独立 profile 启动（v10 cookie，较易读；需在该窗口登录过）")
    p.add_argument("--manual", action="store_true", help="只打印手动指引")
    a = p.parse_args(argv)

    if a.manual:
        return _manual_guide()

    # 决定要尝试的浏览器顺序
    if a.browser == "auto":
        order = detect_browsers()
        if not order:
            print("[warn] 没探测到 Edge/Chrome/Brave，直接给手动指引。")
            return _manual_guide() or 1
        print(f"[info] 自动探测到浏览器：{', '.join(order)}")
    else:
        order = [a.browser]

    cookies = {}
    for b in order:
        print(f"\n-- 尝试浏览器：{b} --")
        cookies = route_cdp(b, a.explicit_profile)
        if "wr_skey" in cookies:
            break
        cookies = route_cookie3(b)
        if "wr_skey" in cookies:
            break

    if "wr_skey" not in cookies:
        print("\n[!] 自动路线都没拿到可用 cookie。")
        _manual_guide()
        return 1
    return _save(cookies)


if __name__ == "__main__":
    raise SystemExit(main())
