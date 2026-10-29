# -*- coding: utf-8 -*-
"""编排入口（skill 版）。

用法：
    python -m wjobs.pipeline                    # 按工作目录的 config.yaml 跑全流程
    python -m wjobs.pipeline --dry-run          # 只看过滤 + 抽取，不落库不出报告
    python -m wjobs.pipeline --no-mail          # 只出本地报告，不产待发送清单
    python -m wjobs.pipeline --limit 20         # 只处理最近 20 条
    python -m wjobs.pipeline --config my.yaml   # 指定配置文件
    python -m wjobs.pipeline --source weread --account "本地宝郑州招聘"
    python -m wjobs.pipeline --to me@qq.com --window-days 1

设计目标：既能当 CLI 手跑，也能被 skill 直接 import 调用（run() 返回结构化结果）。
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List

from .config import load_config
from .extract import extract_jobs
from .fetch import fetch_articles
from .filters import split
from .mailer import mail_window_days, send_report, window_label
from .report import render_email_html, write_reports
from .store import connect, query, query_recent, upsert


def _apply_overrides(cfg: Dict[str, Any], source: str | None, account: str | None,
                     to: str | None, window_days: int | None) -> None:
    """把命令行覆盖项写进内存里的 cfg（不落盘），方便一条命令试不同号。"""
    if source:
        cfg["source"]["type"] = source.strip().lower()
        if source.strip().lower() == "mock":
            cfg["source"]["rss_url"] = "mock"
    if account:
        cfg["source"]["account_name"] = account
    if to:
        cfg["output"].setdefault("mail", {})["to"] = [t.strip() for t in to.split(",") if t.strip()]
    if window_days:
        cfg["output"].setdefault("mail", {})["window_days"] = int(window_days)


def run(config_path: str | None = None, limit: int | None = None,
        dry_run: bool = False, no_mail: bool = False,
        source: str | None = None, account: str | None = None,
        to: str | None = None, window_days: int | None = None,
        quiet: bool = False) -> Dict[str, Any]:
    """跑全流程，返回结构化结果（供 skill / 上层程序消费）。"""
    def log(*a: Any) -> None:
        if not quiet:
            print(*a)

    cfg = load_config(config_path)
    _apply_overrides(cfg, source, account, to, window_days)
    if no_mail:
        cfg["output"].setdefault("mail", {})["enabled"] = False
    account_name = cfg["source"].get("account_name", "")

    # 采集源展示：weread / rss / mock
    stype = (cfg["source"].get("type") or "").strip().lower()
    if not stype:
        raw_url = (cfg["source"].get("rss_url") or "mock").strip()
        stype = ("weread" if raw_url.startswith("weread://")
                 else "mock" if raw_url in ("mock", "", "demo") else "rss")
    if stype == "weread":
        wcfg = cfg["source"].get("weread") or {}
        src_desc = f"微信读书接口 ← {wcfg.get('book_id') or '(未配置 book_id)'}"
    elif stype == "rss":
        src_desc = f"RSS ← {cfg['source'].get('rss_url')}"
    else:
        src_desc = "内置示例数据"

    log(f"[1/5] 采集  ← {src_desc}")
    if account_name:
        log(f"      目标公众号：{account_name}")
    articles = fetch_articles(cfg)
    if limit:
        articles = articles[:limit]
    log(f"      共取到 {len(articles)} 篇文章")

    log("[2/5] 过滤  ← 关键词命中判定")
    candidates, flog = split(articles, cfg["filter"])
    for row in flog:
        flag = "✓ 命中" if row["is_job"] else "· 跳过"
        log(f"      {flag}  {row['title'][:42]}")
    log(f"      候选 {len(candidates)} 篇")

    if not candidates:
        log("没有筛出目标类文章，流程结束。")
        if not dry_run:
            write_reports([], cfg, 0, 0)
        return {"ok": True, "articles": len(articles), "candidates": 0,
                "jobs": 0, "new": 0, "dup": 0, "window": 0,
                "mail_status": "skipped", "reason": "no_candidates"}

    log(f"[3/5] 抽取  ← 模式 {cfg['extract'].get('mode')}")
    jobs = extract_jobs(candidates, cfg)
    for job in jobs:
        log(f"      {job.unit or '(未识别单位)'} | {job.headcount or '人数未知'} | 截止 {job.apply_end or '未注明'}")

    if dry_run:
        log("[dry-run] 跳过落库与报告生成。")
        return {"ok": True, "articles": len(articles), "candidates": len(candidates),
                "jobs": len(jobs), "new": 0, "dup": 0, "window": 0,
                "mail_status": "dry_run"}

    log("[4/5] 去重入库")
    conn = connect(cfg["output"]["data_dir"])
    new_count, dup_count, new_jobs = upsert(conn, [j.to_dict() for j in jobs])
    log(f"      新增 {new_count} 条，跳过重复 {dup_count} 条")

    log("[5/5] 生成日报（本地存档用，含全部历史）")
    recent = query(conn, limit=200)
    paths = write_reports(recent, cfg, new_count, dup_count)
    for p in paths:
        log(f"      → {p}")

    # 邮件只发「最近 N 天」窗口内的岗位（滚动窗口），本地存档仍是全量历史
    days = mail_window_days(cfg)
    send_jobs = query_recent(conn, days=days)
    log(f"[6] 投递邮件  ← {window_label(days)} {len(send_jobs)} 条"
        f"（本次新入库 {len(new_jobs)} 条；库内共 {len(recent)} 条，窗口外的已排除）")

    result: Dict[str, Any] = {
        "ok": True, "articles": len(articles), "candidates": len(candidates),
        "jobs": len(jobs), "new": new_count, "dup": dup_count,
        "window_days": days, "window": len(send_jobs),
        "reports": paths, "mail_status": "unknown",
    }
    try:
        html_doc = render_email_html(send_jobs, cfg, days)
        mail = send_report(cfg, send_jobs, new_count, html_body=html_doc,
                           window_days=days)
        status = mail.get("status")
        result["mail_status"] = status
        result["mail"] = {k: v for k, v in mail.items() if k != "body"}
        if status == "sent":
            log(f"      已发送 → {', '.join(mail['to'])}")
        elif status == "pending_agent":
            log(f"      待发送（Agent Mail）→ {', '.join(mail['to'])}")
            log(f"      from={mail['from']}  subject={mail['subject']}")
            if mail.get("body_path"):
                log(f"      邮件正文已落盘 → {mail['body_path']}"
                    f"  (format={mail.get('body_format', 'PLAIN')})")
        else:
            log(f"      跳过：{mail.get('reason')}")
    except Exception as exc:
        result["mail_status"] = "error"
        result["mail_error"] = str(exc)
        log(f"      [warn] 邮件投递失败：{exc}")

    conn.close()
    return result


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="公众号信息监听流水线（skill 版）")
    parser.add_argument("--config", default=None, help="配置文件路径（默认 ./config.yaml）")
    parser.add_argument("--limit", type=int, default=None, help="最多处理多少篇文章")
    parser.add_argument("--dry-run", action="store_true", help="只做过滤与抽取，不落库")
    parser.add_argument("--no-mail", action="store_true", help="本次不产待发送清单")
    parser.add_argument("--source", default=None,
                        help="临时覆盖采集源：weread / rss / mock")
    parser.add_argument("--account", default=None, help="临时覆盖目标公众号名（报告标题用）")
    parser.add_argument("--to", default=None, help="临时覆盖收件邮箱，逗号分隔")
    parser.add_argument("--window-days", type=int, default=None, help="邮件正文时间窗（天）")
    parser.add_argument("--json", action="store_true", help="最后额外打印一份 JSON 结果")
    args = parser.parse_args(argv)
    try:
        res = run(args.config, args.limit, args.dry_run, args.no_mail,
                  source=args.source, account=args.account, to=args.to,
                  window_days=args.window_days)
        if args.json:
            print("RESULT_JSON " + json.dumps(res, ensure_ascii=False))
        return 0 if res.get("ok") else 1
    except Exception as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
