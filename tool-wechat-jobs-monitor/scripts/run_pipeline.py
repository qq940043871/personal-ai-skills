# -*- coding: utf-8 -*-
r"""一键跑流水线的薄封装（给 skill 与人类共用）。

为什么不让用户直接 `python -m wjobs.pipeline`？
    因为 skill 装在 ~/.workbuddy/skills/… 下，而用户的工作目录另有其处；
    直接 -m 需要先 cd 到 scripts/ 再设 PYTHONPATH，对普通用户是天书。
    本脚本自动把 scripts/ 加进 sys.path，并以**当前工作目录**为配置/数据根，
    所以从任意目录都能一键跑。

用法：
    python scripts/run_pipeline.py                        # 按 ./config.yaml
    python scripts/run_pipeline.py --limit 20             # 少抓点，先验证链路
    python scripts/run_pipeline.py --dry-run              # 只看过滤+抽取
    python scripts/run_pipeline.py --json                 # 额外打印机器可读结果

退出码：0 成功；1 失败。JSON 结果以 `RESULT_JSON ` 前缀打在最后一行，
方便 Agent 用正则抓取。
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# 允许用 WJ_HOME 显式指定工作目录（定时任务里更稳）
os.environ.setdefault("WJ_HOME", os.getcwd())

from wjobs.pipeline import main as pipeline_main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(pipeline_main())
