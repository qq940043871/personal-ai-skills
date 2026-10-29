# -*- coding: utf-8 -*-
"""微信公众号招聘信息监听流水线（skill 内置包）。

对外入口：
    from wjobs import run_pipeline, load_config
"""
from .config import SKILL_ROOT, WORKSPACE, config_path, load_config, PRESETS  # noqa: F401
from .pipeline import run  # noqa: F401

__version__ = "1.0.0"
