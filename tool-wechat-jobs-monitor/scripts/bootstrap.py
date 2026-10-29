# -*- coding: utf-8 -*-
"""环境自举：让「干净电脑装完技能即可用」成立。

干净电脑的真实情况：pip 里没有 feedparser / requests / bs4 / lxml / PyYAML，
甚至可能没有 python。本脚本负责：

  1. 找到可用的 python（当前解释器 → PATH → 常见安装位置）；
  2. 在技能目录下建一个**独立 venv**（`.venv`），把依赖装进去 —— 不污染用户环境；
  3. 校验关键依赖可导入；缺的可选依赖只警告不阻断；
  4. 打印「之后该用哪个 python 跑流水线」。

设计原则
--------
- **不装全局**：一律进技能目录下的 `.venv`，卸载时删目录即可，干净。
- **可重复运行**：已就绪时秒过，不重复装。
- **失败讲人话**：给出手动命令，而不是抛一堆 pip 天书。

用法：
    python scripts/bootstrap.py            # 装/校验依赖
    python scripts/bootstrap.py --check    # 只检查不安装（CI / 快速探测）
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV_DIR = os.path.join(SKILL_ROOT, ".venv")
REQ_FILE = os.path.join(SKILL_ROOT, "requirements.txt")

# 关键依赖（缺了流水线跑不动）
REQUIRED = ["feedparser", "requests", "bs4", "lxml", "yaml"]
# 可选依赖（缺了只是某些便捷路线不可用）
OPTIONAL = {"browser_cookie3": "自动读浏览器 cookie 的备选路线",
            "websocket": "CDP 方式读 cookie"}

# pip 包名 → import 名（对不上的要映射）
PKG2MOD = {"beautifulsoup4": "bs4", "PyYAML": "yaml",
           "browser-cookie3": "browser_cookie3", "websocket-client": "websocket"}


def _venv_python() -> str:
    if os.name == "nt":
        return os.path.join(VENV_DIR, "Scripts", "python.exe")
    return os.path.join(VENV_DIR, "bin", "python")


def _can_import(py: str, mod: str) -> bool:
    try:
        r = subprocess.run([py, "-c", f"import {mod}"],
                           capture_output=True, timeout=30)
        return r.returncode == 0
    except Exception:
        return False


def _check_all(py: str) -> tuple:
    """返回 (缺失的关键依赖, 缺失的可选依赖, 已装上的关键依赖)。"""
    miss_req = [m for m in REQUIRED if not _can_import(py, m)]
    miss_opt = [m for m in OPTIONAL if not _can_import(py, m)]
    have_req = [m for m in REQUIRED if m not in miss_req]
    return miss_req, miss_opt, have_req


def _find_python() -> str:
    """找一个能建 venv 的 python。优先当前解释器。"""
    cands = [sys.executable, "python3", "python"]
    for c in cands:
        if not c:
            continue
        try:
            r = subprocess.run([c, "--version"], capture_output=True, timeout=15)
            if r.returncode == 0:
                return c
        except Exception:
            continue
    return ""


def _make_venv(base_py: str) -> bool:
    print(f"  创建独立虚拟环境 → {VENV_DIR}")
    try:
        r = subprocess.run([base_py, "-m", "venv", VENV_DIR],
                           capture_output=True, timeout=300)
    except Exception as exc:
        print(f"  [error] 建 venv 失败：{exc}")
        return False
    if r.returncode != 0:
        print("  [error] 建 venv 失败：" + r.stderr.decode("utf-8", "replace")[:300])
        return False
    return True


def _pip_install(py: str, args: list) -> bool:
    cmd = [py, "-m", "pip", "install", "--disable-pip-version-check"] + args
    print(f"  $ {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        print("  [error] pip 安装失败："
              + (r.stderr.decode("utf-8", "replace") or "")[-400:])
        return False
    return True


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="环境自举：安装依赖并校验")
    p.add_argument("--check", action="store_true", help="只检查不安装")
    a = p.parse_args(argv)

    print("=" * 60)
    print("  tool-wechat-jobs-monitor · 环境自举")
    print("=" * 60)

    # 先看当前解释器是否已经够用（很多机器 pip 里就有这些包）
    cur = sys.executable
    miss_req, miss_opt, have_req = _check_all(cur)
    if not miss_req:
        print(f"[ok] 当前解释器已具备全部关键依赖：{cur}")
        for m in miss_opt:
            print(f"[warn] 可选依赖 {m} 缺失 —— {OPTIONAL[m]}（不影响主流程）")
        print(f"\n直接用这个解释器即可：\n  \"{cur}\" scripts/run_pipeline.py")
        return 0

    print(f"[info] 当前解释器 {cur} 缺少关键依赖：{', '.join(miss_req)}")

    if a.check:
        print("\n（--check 模式，不安装）")
        print("修复：python scripts/bootstrap.py")
        return 1

    # 建独立 venv（不污染用户环境）
    if not os.path.exists(_venv_python()):
        base = _find_python()
        if not base:
            print("[error] 找不到可用的 python，请先安装 Python 3.9+。")
            return 1
        print(f"[info] 使用 {base} 创建虚拟环境")
        if not _make_venv(base):
            return 1

    vpy = _venv_python()
    print(f"[info] 在独立 venv 中安装依赖（{REQ_FILE}）")
    # 先升级 pip（老 pip 装 lxml 常翻车）
    _pip_install(vpy, ["--upgrade", "pip"])
    if not _pip_install(vpy, ["-r", REQ_FILE]):
        # 退路：逐包装，容忍可选包失败
        print("[warn] 整体安装失败，改为逐个安装关键依赖 ...")
        if not _pip_install(vpy, REQUIRED):
            print("[error] 关键依赖安装失败。请手动执行：")
            print(f'  "{vpy}" -m pip install ' + " ".join(REQUIRED))
            return 1

    miss_req, miss_opt, have_req = _check_all(vpy)
    if miss_req:
        print(f"[error] 仍有依赖缺失：{', '.join(miss_req)}")
        return 1

    print("\n" + "=" * 60)
    print("[ok] 环境就绪！关键依赖全部可用。")
    for m in miss_opt:
        print(f"[warn] 可选依赖 {m} 缺失 —— {OPTIONAL[m]}（不影响主流程）")
    print("\n之后请用这个解释器运行流水线：")
    print(f'  "{vpy}" scripts/run_pipeline.py')
    print("\n（提示：技能配置文件、数据、报告都落在你当前的工作目录，"
          "不在这里。）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
