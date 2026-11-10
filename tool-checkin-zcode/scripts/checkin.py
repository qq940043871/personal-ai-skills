# -*- coding: utf-8 -*-
"""Daily check-in automation for Windows desktop apps.

Usage:
  python checkin.py list
  python checkin.py shot <app_id> [out.png]
  python checkin.py run  <app_id> [--no-launch]
  python checkin.py add  <app_id> --title "WinTitle" --exe "C:\\a.exe" --x 100 --y 200 [--clicks 1] [--wait 18]

Config: ../config/checkin.json relative to this script (or CHECKIN_CONFIG env).
"""
import sys, io, os, json, time, argparse, subprocess
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from pywinauto import Desktop, mouse

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CFG = os.path.join(os.path.dirname(HERE), "config", "checkin.json")
CFG_PATH = os.environ.get("CHECKIN_CONFIG", DEFAULT_CFG)


def load_cfg():
    if not os.path.exists(CFG_PATH):
        return {"apps": {}}
    with open(CFG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_cfg(cfg):
    d = os.path.dirname(CFG_PATH)
    if d and not os.path.exists(d):
        os.makedirs(d)
    with open(CFG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def find_window(title_sub):
    for w in Desktop(backend="uia").windows():
        try:
            t = w.window_text()
            if t and title_sub.lower() in t.lower():
                return w
        except Exception:
            continue
    return None


def compute_xy(app, rect):
    """Return (screen_x, screen_y) for the button.

    Two modes:
    - anchor mode (recommended): anchor in {bl, br, tl, tr, c} + dx/dy offset
      from that corner of the window. Survives window resize.
    - absolute mode: x/y are pixels inside the window screenshot (top-left origin).
    """
    anchor = (app.get("anchor") or "").lower()
    if anchor:
        dx = int(app.get("dx", 0))
        dy = int(app.get("dy", 0))
        w, h = rect.width(), rect.height()
        if anchor == "bl":
            return rect.left + dx, rect.top + h + dy
        if anchor == "br":
            return rect.left + w + dx, rect.top + h + dy
        if anchor == "tr":
            return rect.left + w + dx, rect.top + dy
        if anchor == "c":
            return rect.left + w // 2 + dx, rect.top + h // 2 + dy
        # default tl
        return rect.left + dx, rect.top + dy
    return rect.left + int(app["x"]), rect.top + int(app["y"])


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


def launch_via_explorer(exe, wait_sec):
    print("launching via explorer ShellExecute:", exe)
    subprocess.Popen(["explorer.exe", exe])
    time.sleep(wait_sec)


def ensure_window(app, allow_launch=True, wait=18):
    w = find_window(app["title"])
    if w is not None:
        return w, False
    if not allow_launch:
        return None, False
    exe = app.get("exe")
    if exe and os.path.exists(exe):
        launch_via_explorer(exe, wait)
        return find_window(app["title"]), True
    print("exe missing or not set:", exe)
    return None, False


def shot(w, out):
    img = w.capture_as_image()
    img.save(out)
    print("saved:", out, "size:", img.size)
    return out


def cmd_list(cfg):
    apps = cfg.get("apps", {})
    if not apps:
        print("(no apps configured)")
        return
    for k, v in apps.items():
        if v.get("anchor"):
            pos = "anchor=%s d=(%s,%s)" % (v["anchor"], v.get("dx"), v.get("dy"))
        else:
            pos = "abs=(%s,%s)" % (v.get("x"), v.get("y"))
        print("%-12s title=%r  %s clicks=%s" % (k, v.get("title"), pos, v.get("clicks", 1)))


def cmd_shot(cfg, app_id, out=None):
    app = cfg["apps"][app_id]
    w, launched = ensure_window(app, True, app.get("launch_wait", 18))
    if w is None:
        print("FAIL: window not found:", app["title"])
        sys.exit(3)
    activate(w)
    d = app.get("shot_dir") or os.getcwd()
    out = out or os.path.join(d, "%s_%s.png" % (app_id, time.strftime("%m%d_%H%M%S")))
    shot(w, out)


def cmd_run(cfg, app_id, allow_launch=True):
    app = cfg["apps"][app_id]
    w, launched = ensure_window(app, allow_launch, app.get("launch_wait", 18))
    if w is None:
        print("FAIL: window not found:", app["title"])
        sys.exit(3)
    activate(w)
    r = w.rectangle()
    print("window rect:", r, "size:", (r.width(), r.height()))

    clicks = int(app.get("clicks", 1))
    d = app.get("shot_dir") or os.getcwd()
    stamp = time.strftime("%m%d_%H%M%S")
    before = os.path.join(d, "%s_%s_before.png" % (app_id, stamp))
    shot(w, before)

    for i in range(clicks):
        sx, sy = compute_xy(app, r)
        print("click %d/%d at screen (%s,%s)" % (i + 1, clicks, sx, sy))
        mouse.click(button='left', coords=(sx, sy))
        if i + 1 < clicks:
            time.sleep(1.2)

    time.sleep(2.0)
    after = os.path.join(d, "%s_%s_after.png" % (app_id, stamp))
    shot(w, after)
    print("DONE verify:", after)


def cmd_add(cfg, args):
    app = {
        "title": args.title,
        "exe": args.exe,
        "clicks": args.clicks,
        "launch_wait": args.wait,
        "shot_dir": args.shot_dir or os.getcwd(),
    }
    if args.anchor:
        app["anchor"] = args.anchor
        app["dx"] = args.dx
        app["dy"] = args.dy
    else:
        if args.x is None or args.y is None:
            print("need --anchor with --dx/--dy, or absolute --x/--y")
            sys.exit(1)
        app["x"] = args.x
        app["y"] = args.y
    cfg.setdefault("apps", {})[args.app_id] = app
    save_cfg(cfg)
    print("saved config for", args.app_id)
    print(json.dumps(app, ensure_ascii=False, indent=2))


def main():
    p = argparse.ArgumentParser(description="daily check-in automation")
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("list")

    s = sub.add_parser("shot")
    s.add_argument("app_id")
    s.add_argument("out", nargs="?")

    r = sub.add_parser("run")
    r.add_argument("app_id")
    r.add_argument("--no-launch", action="store_true")

    a = sub.add_parser("add")
    a.add_argument("app_id")
    a.add_argument("--title", required=True)
    a.add_argument("--exe", default="")
    a.add_argument("--anchor", default="", help="bl|br|tl|tr|c — button anchored to window corner (resize-proof)")
    a.add_argument("--dx", type=int, default=0)
    a.add_argument("--dy", type=int, default=0)
    a.add_argument("--x", type=int, help="absolute mode: pixel x inside window shot")
    a.add_argument("--y", type=int, help="absolute mode: pixel y inside window shot")
    a.add_argument("--clicks", type=int, default=1)
    a.add_argument("--wait", type=int, default=18)
    a.add_argument("--shot_dir", default="")

    args = p.parse_args()
    cfg = load_cfg()

    if args.cmd == "list":
        cmd_list(cfg)
    elif args.cmd == "shot":
        cmd_shot(cfg, args.app_id, args.out)
    elif args.cmd == "run":
        cmd_run(cfg, args.app_id, not args.no_launch)
    elif args.cmd == "add":
        cmd_add(cfg, args)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
