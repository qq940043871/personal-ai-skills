# -*- coding: utf-8 -*-
"""存储层：SQLite 去重落库。

为什么必须去重？
  采集服务大多按时间窗重复推送（今天推近 30 条，明天还推同样的 30 条里的 29 条）。
  没有指纹去重，你的日报会天天推送同一批岗位，第三天你就不想看了。
"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    fingerprint   TEXT PRIMARY KEY,
    article_title TEXT,
    url           TEXT,
    published     TEXT,
    account       TEXT,
    unit          TEXT,
    category      TEXT,
    headcount     TEXT,
    education     TEXT,
    major         TEXT,
    age           TEXT,
    location      TEXT,
    apply_start   TEXT,
    apply_end     TEXT,
    apply_method  TEXT,
    exam          TEXT,
    salary        TEXT,
    contact       TEXT,
    highlights    TEXT,
    extract_mode  TEXT,
    first_seen    TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_jobs_pub ON jobs(published DESC);
"""

FIELDS = [
    "fingerprint", "article_title", "url", "published", "account", "unit", "category",
    "headcount", "education", "major", "age", "location", "apply_start", "apply_end",
    "apply_method", "exam", "salary", "contact", "highlights", "extract_mode",
]


def connect(data_dir: str) -> sqlite3.Connection:
    os.makedirs(data_dir, exist_ok=True)
    conn = sqlite3.connect(os.path.join(data_dir, "jobs.db"))
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def upsert(conn: sqlite3.Connection, jobs: List[Dict]) -> Tuple[int, int, List[Dict]]:
    """写入并返回 (新增数, 已存在数, 本次新增的岗位列表)。

    第三个返回值是给「只发当日新增」的日报邮件用的：
    日报正文只需要今天真正新出现的岗位，而不是库里累积的全部历史，
    否则收件人每天都会看到同一批老岗位。
    """
    # 重复命中时刷新抽取字段：fingerprint 是内容哈希，同一篇文章的指纹不会变，
    # 但抽取逻辑会随时修（单位名、薪酬噪声…）。若不回写，旧数据会永远留在库里，
    # 修好的抽取规则对历史岗位完全不生效——每次跑都是「跳过重复」。
    # first_seen 保持不动（它记录的是"第一次见到"），其余字段整体覆盖。
    _upd_fields = [f for f in FIELDS if f != "fingerprint"]

    new = 0
    dup = 0
    fresh: List[Dict] = []
    for job in jobs:
        cur = conn.execute("SELECT 1 FROM jobs WHERE fingerprint=?", (job["fingerprint"],))
        if cur.fetchone():
            conn.execute(
                f"UPDATE jobs SET {','.join(f + '=?' for f in _upd_fields)} "
                "WHERE fingerprint=?",
                [job.get(f, "") for f in _upd_fields] + [job["fingerprint"]],
            )
            dup += 1
            continue
        conn.execute(
            f"INSERT INTO jobs ({','.join(FIELDS)}) VALUES ({','.join('?' * len(FIELDS))})",
            [job.get(f, "") for f in FIELDS],
        )
        new += 1
        fresh.append(job)
    conn.commit()
    return new, dup, fresh


def query(conn: sqlite3.Connection, published_from: str = "", limit: int = 500) -> List[Dict]:
    sql = f"SELECT {','.join(FIELDS)} FROM jobs"
    args: List = []
    if published_from:
        sql += " WHERE published >= ?"
        args.append(published_from)
    sql += " ORDER BY COALESCE(NULLIF(published,''),'0000') DESC, first_seen DESC LIMIT ?"
    args.append(limit)
    cols = FIELDS
    return [dict(zip(cols, row)) for row in conn.execute(sql, args).fetchall()]


def query_recent(conn: sqlite3.Connection, days: int = 7, limit: int = 500) -> List[Dict]:
    """取「最近 N 天」的岗位，供日报邮件使用（含今天，故 cutoff = 今天-(N-1)）。

    日期口径优先用公众号发布日期 `published`；个别文章抓不到发布日期时，
    退回到 `first_seen`（我们第一次见到它的日期），避免因为字段缺失被漏掉。

    注意这是**滚动窗口**：只要一条岗位还在 N 天窗口内，每天的邮件里都会出现它。
    这是刻意的——用户漏看某一天的邮件，第二天仍能看到，不会永久错过。
    """
    days = max(1, int(days))
    cutoff = (datetime.now().date() - timedelta(days=days - 1)).isoformat()
    sql = (f"SELECT {','.join(FIELDS)} FROM jobs"
           " WHERE COALESCE(NULLIF(published,''), substr(first_seen,1,10)) >= ?"
           " ORDER BY COALESCE(NULLIF(published,''),'0000') DESC, first_seen DESC LIMIT ?")
    return [dict(zip(FIELDS, row)) for row in conn.execute(sql, [cutoff, limit]).fetchall()]
