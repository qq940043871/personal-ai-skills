import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import trae_checkin as t

cfg = t.load_cfg()
found = t.find_main_window(cfg)
if found is None:
    print("NO_TRAE_WINDOW")
    sys.exit(0)
area, w, r = found
t.quit_app(cfg, w, r)
print("ALIVE" if t.find_main_window(cfg) else "GONE")
