# -*- coding: utf-8 -*-
"""过滤层：从一堆公众号文章里挑出「可能是招聘公告」的那几篇。

为什么要有这一层？
  一个政务号一天可能推 6-8 条：天气、限行、消费券、义诊、招聘、政策……
  全量丢给大模型既费钱又容易被无关内容污染。先做低成本粗筛，
  把候选量从 N 压到 1-2 条，再上抽取，是性价比最高的顺序。
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .fetch import Article


def _hits(text: str, words: List[str]) -> List[str]:
    return [w for w in words if w and w in text]


def classify(article: Article, fcfg: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """返回 (是否招聘文, 判定依据)。"""
    title = article.title or ""
    body = article.plain or ""

    title_hits = _hits(title, fcfg.get("title_include", []))
    body_hits = _hits(body, fcfg.get("body_include", []))
    excludes = _hits(f"{title}\n{body}", fcfg.get("exclude", []))

    require_title = bool(fcfg.get("require_title_hit", True))
    if require_title:
        is_job = bool(title_hits)
    else:
        is_job = bool(title_hits or body_hits)

    # 排除词一票否决（但标题明确写"招聘"的，优先信任标题）
    if excludes and not title_hits:
        is_job = False

    reason = {
        "title_hits": title_hits,
        "body_hits": body_hits,
        "excluded_by": excludes,
        "score": len(title_hits) * 3 + len(body_hits),
    }
    return is_job, reason


def split(articles: List[Article], fcfg: Dict[str, Any]) -> Tuple[List[Article], List[Dict[str, Any]]]:
    """把文章切成 (招聘候选, 全部判定记录)。判定记录按相关度降序。"""
    candidates: List[Article] = []
    log: List[Dict[str, Any]] = []
    for art in articles:
        ok, reason = classify(art, fcfg)
        log.append({"title": art.title, "is_job": ok, **reason})
        if ok:
            candidates.append(art)
    log.sort(key=lambda x: (x["is_job"], x["score"]), reverse=True)
    return candidates, log
