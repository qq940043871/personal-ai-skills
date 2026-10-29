# -*- coding: utf-8 -*-
"""Electron app GUI helper (Windows, pywinauto).

Usage:
  python electron_click.py shot "<title substring>" <out.png>
  python electron_click.py click "<title substring>" <x> <y> [wait_sec] [out.png]

Coordinates are pixels inside the window screenshot (1:1 with window rect).
"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from pywinauto import Desktop, mouse


def find_main(title_sub):
    desktop = Desktop(backend="uia")
    for w in desktop.windows():
        try:
            t = w.window_text()
            if title_sub.lower() in t.lower() and t.strip():
                return w
        except Exception:
            pass
    return None


def activate(w):
    try:
        if w.is_minimized():
            w.restore()
            time.sleep(1.0)
    except Exception as e:
        print("restore err:", e)
    try:
        w.set_focus()
    except Exception as e:
        print("focus err:", e)
    time.sleep(0.8)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    cmd, title = sys.argv[1], sys.argv[2]
    w = find_main(title)
    if w is None:
        print("NO WINDOW matching %r" % title)
        sys.exit(2)
    activate(w)
    r = w.rectangle()
    print("window rect:", r, "size:", (r.width(), r.height()))

    if cmd == "shot":
        out = sys.argv[3]
        img = w.capture_as_image()
        img.save(out)
        print("saved:", out, "size:", img.size)
    elif cmd == "click":
        x, y = int(sys.argv[3]), int(sys.argv[4])
        wait = float(sys.argv[5]) if len(sys.argv) > 5 else 1.5
        out = sys.argv[6] if len(sys.argv) > 6 else "after_click.png"
        sx, sy = r.left + x, r.top + y
        print("click screen:", sx, sy)
        mouse.click(button='left', coords=(sx, sy))
        time.sleep(wait)
        img = w.capture_as_image()
        img.save(out)
        print("saved:", out)
    else:
        print("unknown cmd:", cmd)
        sys.exit(1)


if __name__ == "__main__":
    main()
