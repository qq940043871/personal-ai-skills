# -*- coding: utf-8 -*-
"""Trae CN daily check-in automation (Windows, pywinauto).

签到路径：Trae 左下角头像栏 -> 账号菜单 -> 「每日领 100 积分」行右侧按钮。

Usage:
  python trae_checkin.py run                 # 完整流程：ESC -> 点头像 -> 截菜单 -> 点签到 -> 回拍
  python trae_checkin.py menu                # 只打开账号菜单并截图（查看今天是「签到」还是「已签到」）
  python trae_checkin.py shot [out.png]      # 截 Trae 主窗口
  python trae_checkin.py click <x> <y> [wait] [out.png]   # 窗口内相对坐标点击并回拍（校准用）
  python trae_checkin.py crop <img> <x1> <y1> <x2> <y2> [scale]  # 放大裁剪（读坐标用）

Config: ../config/trae.json relative to this script (or TRAE_CHECKIN_CFG env).
窗口定位不依赖标题（Trae 主窗口标题随视图变化，实测为 'Agent'），
改为：进程名 Trae CN.exe + 最大的 Chrome_WidgetWin_1 窗口。
"""
import sys, io, os, json, time, argparse, subprocess, ctypes
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from pywinauto import Desktop, mouse
from pywinauto.keyboard import send_keys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CFG = os.path.join(os.path.dirname(HERE), "config", "trae.json")
CFG_PATH = os.environ.get("TRAE_CHECKIN_CFG", DEFAULT_CFG)
DEFAULT_SHOT_DIR = os.path.join(os.path.dirname(HERE), "shots")


# ----------------------------- config -----------------------------

def load_cfg():
    if not os.path.exists(CFG_PATH):
        raise SystemExit("config not found: %s" % CFG_PATH)
    with open(CFG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ----------------------------- windows -----------------------------

def proc_image_name(pid):
    """Full process image path via Win32 API (no psutil dependency)."""
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    h = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(260)
        sz = ctypes.c_uint32(260)
        ok = ctypes.windll.kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(sz))
        return os.path.basename(buf.value) if ok else ""
    finally:
        ctypes.windll.kernel32.CloseHandle(h)


def find_main_window(cfg):
    """Largest Chrome_WidgetWin_1 window owned by the configured process."""
    proc = cfg.get("process", "Trae CN.exe").lower()
    best = None  # (area, wrapper, rect)
    for w in Desktop(backend="uia").windows():
        try:
            if proc_image_name(w.process_id()).lower() != proc:
                continue
            cls = ""
            try:
                cls = (w.element_info.class_name or "").lower()
            except Exception:
                pass
            if cls != "chrome_widgetwin_1":
                continue
            r = w.rectangle()
            if r.width() < 800 or r.height() < 600:
                continue
            area = r.width() * r.height()
            if best is None or area > best[0]:
                best = (area, w, r)
        except Exception:
            continue
    return best


def activate(w):
    try:
        if w.is_minimized():
            w.restore()
            time.sleep(1.0)
    except Exception:
        pass
    try:
        w.set_focus()
    except Exception:
        pass
    time.sleep(0.8)


def launch_via_explorer(cfg):
    """从受限父进程直接启动 Electron 会静默退出，必须走 explorer ShellExecute。"""
    exe = cfg.get("exe", "")
    if not exe or not os.path.exists(exe):
        print("FAIL: exe missing:", exe)
        return False
    print("launching via explorer:", exe)
    subprocess.Popen(["explorer.exe", exe])
    time.sleep(float(cfg.get("launch_wait", 22)))
    return True


def ensure_main(cfg, allow_launch=True):
    """Return (window_tuple, launched_by_script)."""
    t = find_main_window(cfg)
    if t is not None:
        return t, False
    if allow_launch and launch_via_explorer(cfg):
        t = find_main_window(cfg)
    if t is None:
        print("FAIL: Trae main window not found")
        sys.exit(3)
    return t, True


# ----------------------------- helpers -----------------------------

def capture(w, out):
    img = w.capture_as_image()
    img.save(out)
    print("saved:", out, "size:", img.size)
    return out


def shot_path(cfg, tag):
    d = cfg.get("shot_dir") or DEFAULT_SHOT_DIR
    if not os.path.exists(d):
        os.makedirs(d)
    return os.path.join(d, "trae_%s_%s.png" % (tag, time.strftime("%m%d_%H%M%S")))


def anchor_point(step, r):
    """屏幕坐标 = 窗口左下角 + (dx, dy)。dy 负值=向上。"""
    return r.left + int(step["dx"]), r.bottom + int(step["dy"])


def esc():
    """先关掉可能已打开的菜单/弹窗，保证「点头像=开菜单」而不是关菜单。"""
    try:
        send_keys("{ESC}")
        time.sleep(0.4)
    except Exception as e:
        print("esc warn:", e)


def close_menu():
    """签到完成后关闭账号菜单：连发两次 ESC（第一次关可能弹出的二级弹窗，第二次关菜单）。"""
    try:
        send_keys("{ESC}")
        time.sleep(0.35)
        send_keys("{ESC}")
        time.sleep(0.6)
        print("menu closed via ESC")
    except Exception as e:
        print("close menu warn:", e)


def quit_app(cfg, w, r):
    """退出 Trae 本体。仅在调用方确认本次为脚本拉起时执行，避免误杀用户在用的工作区。

    优先 WM_CLOSE 优雅退出；窗口未在 8s 内消失则 taskkill 进程树兜底。
    """
    pid = w.process_id()
    print("quitting Trae (pid=%d) ..." % pid)
    try:
        w.close()
    except Exception as e:
        print("WM_CLOSE warn:", e)
    deadline = time.time() + 8.0
    while time.time() < deadline:
        if find_main_window(cfg) is None:
            print("Trae closed gracefully")
            return
        time.sleep(0.5)
    print("window still alive, taskkill /T /F pid=%d" % pid)
    subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                   capture_output=True, text=True)


# ----------------------------- commands -----------------------------

def cmd_shot(cfg, out=None):
    (_, w, r), _ = ensure_main(cfg)
    activate(w)
    print("window rect:", r, "size:", (r.width(), r.height()))
    capture(w, out or shot_path(cfg, "main"))


def cmd_menu(cfg):
    """打开账号菜单并截图（不点击签到）。"""
    (_, w, r), _ = ensure_main(cfg)
    activate(w)
    print("window rect:", r)
    esc()
    sx, sy = anchor_point(cfg["steps"][0], r)
    print("click avatar at screen (%d,%d)" % (sx, sy))
    mouse.click(button='left', coords=(sx, sy))
    time.sleep(float(cfg["steps"][0].get("wait_after", 1.2)))
    out = shot_path(cfg, "menu")
    capture(w, out)
    print("MENU_SHOT:", out)


def cmd_run(cfg, force_quit=False):
    (_, w, r), launched = ensure_main(cfg)
    activate(w)
    print("window rect:", r, "size:", (r.width(), r.height()), "launched_by_script:", launched)

    before = shot_path(cfg, "before")
    capture(w, before)

    esc()
    steps = cfg["steps"]
    for i, step in enumerate(steps):
        sx, sy = anchor_point(step, r)
        print("step %d %s -> screen (%d,%d)" % (i + 1, step.get("name", ""), sx, sy))
        mouse.click(button='left', coords=(sx, sy))
        time.sleep(float(step.get("wait_after", 1.5)))
        if i == 0:
            # 菜单展开后立刻留一张图：可判读点击前是「签到」还是「已签到」
            menu = shot_path(cfg, "menu")
            capture(w, menu)

    after = shot_path(cfg, "after")
    capture(w, after)

    # 收尾：先关菜单（默认），再按配置决定是否退出应用
    want_quit = force_quit or bool(cfg.get("quit_app_after", False))
    if want_quit and not launched:
        print("SKIP QUIT: Trae 是用户已打开的窗口（非脚本拉起），拒绝退出，仅关闭菜单。")
        want_quit = False

    if want_quit:
        # 退出应用前不需要单独关菜单，WM_CLOSE 会带走整个窗口；留个 ESC 兜底二级弹窗
        esc()
        quit_app(cfg, w, r)
        print("DONE_APP_QUIT")
    elif cfg.get("close_menu_after", True):
        close_menu()
        final = shot_path(cfg, "final")
        capture(w, final)
        print("FINAL_SHOT:", final)
        print("DONE_MENU_CLOSED")
    else:
        print("DONE")

    print("BEFORE_SHOT:", before)
    print("AFTER_SHOT:", after)
    print("NOTE: 需用 Read 查看 menu/after 截图确认：按钮是否由「签到/领取」变为「已签到」，"
          "或出现「签到成功」提示。已签到状态下按钮置灰，点了无副作用。")


def cmd_click(cfg, x, y, wait=2.0, out=None):
    (_, w, r), _ = ensure_main(cfg)
    activate(w)
    sx, sy = r.left + x, r.top + y
    print("window:", r, "-> screen (%d,%d)" % (sx, sy))
    mouse.click(button='left', coords=(sx, sy))
    time.sleep(wait)
    capture(w, out or shot_path(cfg, "click"))


def cmd_crop(path, x1, y1, x2, y2, scale=3):
    from PIL import Image, ImageDraw
    im = Image.open(path).convert("RGB").crop((x1, y1, x2, y2))
    im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
    d = ImageDraw.Draw(im)
    for gx in range(0, x2 - x1 + 1, 25):
        X = gx * scale
        d.line([(X, 0), (X, im.height)], fill=(255, 0, 0), width=1)
        d.text((X + 2, 2), str(x1 + gx), fill=(255, 0, 0))
    for gy in range(0, y2 - y1 + 1, 25):
        Y = gy * scale
        d.line([(0, Y), (im.width, Y)], fill=(255, 0, 0), width=1)
        d.text((2, Y + 2), str(y1 + gy), fill=(255, 0, 0))
    out = path.rsplit(".", 1)[0] + "_crop.png"
    im.save(out)
    print("saved:", out, im.size)


def main():
    p = argparse.ArgumentParser(description="Trae CN daily check-in")
    sub = p.add_subparsers(dest="cmd")
    r = sub.add_parser("run")
    r.add_argument("--quit-app", action="store_true",
                   help="签到后退出 Trae（仅当 Trae 由本次脚本拉起时生效，保护用户已打开的工作区）")
    sub.add_parser("menu")
    s = sub.add_parser("shot")
    s.add_argument("out", nargs="?")
    c = sub.add_parser("click")
    c.add_argument("x", type=int)
    c.add_argument("y", type=int)
    c.add_argument("wait", nargs="?", type=float, default=2.0)
    c.add_argument("out", nargs="?")
    cr = sub.add_parser("crop")
    cr.add_argument("img")
    cr.add_argument("x1", type=int)
    cr.add_argument("y1", type=int)
    cr.add_argument("x2", type=int)
    cr.add_argument("y2", type=int)
    cr.add_argument("scale", nargs="?", type=int, default=3)

    args = p.parse_args()
    if args.cmd == "crop":
        cmd_crop(args.img, args.x1, args.y1, args.x2, args.y2, args.scale)
        return

    cfg = load_cfg()
    if args.cmd == "run":
        cmd_run(cfg, force_quit=args.quit_app)
    elif args.cmd == "menu":
        cmd_menu(cfg)
    elif args.cmd == "shot":
        cmd_shot(cfg, args.out)
    elif args.cmd == "click":
        cmd_click(cfg, args.x, args.y, args.wait, args.out)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
