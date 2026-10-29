# -*- coding: utf-8 -*-
"""配置加载（skill 版）。

与仓库版的唯一区别：**路径锚点**。
仓库版把 config / data / out 锚定到「包所在目录」，因为代码和数据同处一个仓库。
但在 skill 形态下，代码装在 ~/.workbuddy/skills/…，用户的工作目录另有其处 ——
所以这里把 config.yaml、data/、out/ 一律锚定到 **cwd（用户当前工作目录）**。

可用环境变量 WJ_CONFIG 强制指定 config 路径；data_dir / out_dir 仍按「相对 cwd」解析，
写绝对路径也可（以 / 或 X: 开头的原样保留）。
"""
from __future__ import annotations

import os
from typing import Any, Dict

import yaml

# skill 根目录（…/scripts/wjobs/config.py → …/scripts/wjobs → …/scripts → skill 根）
SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 用户工作目录：默认 cwd，可用 WJ_HOME 覆盖（定时任务里显式指定更稳）
WORKSPACE = os.environ.get("WJ_HOME") or os.getcwd()


def config_path(path: str | None = None) -> str:
    if path:
        return os.path.abspath(path)
    env = os.environ.get("WJ_CONFIG")
    if env:
        return os.path.abspath(env)
    return os.path.join(WORKSPACE, "config.yaml")


DEFAULTS: Dict[str, Any] = {
    "source": {"type": "mock", "rss_url": "mock", "account_name": "未命名公众号",
               "max_items": 60, "fetch_workers": 4, "timeout": 15},
    "filter": {"title_include": [], "body_include": [], "exclude": [],
               "require_title_hit": True},
    "extract": {"mode": "rule", "llm": {"base_url": "", "api_key": "",
                                        "model": "", "temperature": 0}},
    "output": {"data_dir": "data", "out_dir": "out", "formats": ["md", "html"]},
}


def _merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def _anchor(p: str) -> str:
    """相对路径锚定到 WORKSPACE；已是绝对路径的原样返回。"""
    if not p:
        return p
    if os.path.isabs(p):
        return p
    return os.path.join(WORKSPACE, p)


def load_config(path: str | None = None) -> Dict[str, Any]:
    p = config_path(path)
    if not os.path.exists(p):
        raise FileNotFoundError(
            f"配置文件不存在: {p}\n"
            f"先跑一次初始化向导生成它：\n"
            f"  python scripts/setup_wizard.py\n"
            f"（或把 WJ_CONFIG 指向你的配置文件）")
    with open(p, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    cfg = _merge(DEFAULTS, raw)

    for key in ("data_dir", "out_dir"):
        cfg["output"][key] = _anchor(cfg["output"][key])
    cfg["_config_path"] = p
    return cfg


# ---------------------------------------------------------------- 关键词预设

# 开箱即用的关键词预设。不同行业的号内容差别大，预设能让向导少问几个问题。
PRESETS: Dict[str, Dict[str, Any]] = {
    "招聘": {
        "title_include": ["招聘", "招录", "招考", "公开选调", "遴选", "人才引进",
                          "岗位表", "招贤", "补录", "公开招聘"],
        "body_include": ["公开招聘", "事业单位", "报名条件", "岗位需求", "笔试",
                         "面试", "编制", "公务员"],
        "exclude": ["天气", "大风", "降温", "限行", "停水", "停电", "交通管制",
                    "消费券", "义诊", "口袋公园", "延时运营"],
        "require_title_hit": True,
    },
    "招标采购": {
        "title_include": ["招标", "采购", "询价", "竞价", "中标", "成交公告",
                          "竞争性磋商", "公开选取"],
        "body_include": ["投标", "开标", "评标", "中标候选人", "采购需求"],
        "exclude": ["天气", "限行", "消费券"],
        "require_title_hit": True,
    },
    "政策通知": {
        "title_include": ["通知", "公告", "公示", "政策", "办法", "实施意见"],
        "body_include": ["申报", "受理", "截止时间", "申报条件"],
        "exclude": ["天气", "限行", "消费券"],
        "require_title_hit": True,
    },
    "自定义": {
        "title_include": [], "body_include": [], "exclude": [],
        "require_title_hit": True,
    },
}
