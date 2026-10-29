# -*- coding: utf-8 -*-
"""输出层：把结构化岗位渲染成 Markdown / 单文件 HTML 日报。"""
from __future__ import annotations

import html
import os
from datetime import datetime
from typing import Dict, List

COLUMNS = [
    ("unit", "招聘单位"),
    ("category", "岗位类别"),
    ("headcount", "人数"),
    ("education", "学历"),
    ("major", "专业"),
    ("age", "年龄"),
    ("apply_end", "报名截止"),
    ("salary", "薪酬待遇"),
]

_CSS = """
:root{--bg:#f6f7fb;--card:#ffffff;--ink:#1c2333;--muted:#6b7590;--line:#e6e9f2;
--brand:#2f5bd7;--brand-soft:#eef3ff;--warn:#c2410c;--warn-soft:#fff3ea;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:14px/1.7 -apple-system,"Segoe UI","Microsoft YaHei",system-ui,sans-serif;}
.wrap{max-width:1120px;margin:0 auto;padding:32px 20px 64px;}
header{margin-bottom:24px}
h1{margin:0 0 6px;font-size:26px;letter-spacing:.3px}
.sub{color:var(--muted);font-size:13px}
.stats{display:flex;gap:12px;flex-wrap:wrap;margin:20px 0 28px}
.stat{background:var(--card);border:1px solid var(--line);border-radius:12px;
padding:14px 18px;min-width:132px}
.stat b{display:block;font-size:22px;color:var(--brand);letter-spacing:.5px}
.stat span{color:var(--muted);font-size:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;
padding:20px 22px;margin-bottom:16px;box-shadow:0 1px 2px rgba(20,30,60,.04)}
.card h2{margin:0 0 4px;font-size:17px;line-height:1.5}
.meta{color:var(--muted);font-size:12px;margin-bottom:14px;display:flex;
gap:14px;flex-wrap:wrap;align-items:center}
.badge{background:var(--brand-soft);color:var(--brand);border-radius:999px;
padding:2px 10px;font-size:11px;font-weight:600}
.badge.hot{background:var(--warn-soft);color:var(--warn)}
table{width:100%;border-collapse:collapse;font-size:13px}
td,th{padding:7px 10px;border-bottom:1px solid var(--line);vertical-align:top;text-align:left}
th{width:96px;color:var(--muted);font-weight:500;white-space:nowrap}
tr:last-child td{border-bottom:none}
.detail{margin-top:12px;font-size:13px;color:#39405a}
.detail p{margin:6px 0}
.detail .k{color:var(--muted);display:inline-block;min-width:76px}
a{color:var(--brand);text-decoration:none}
a:hover{text-decoration:underline}
.empty{background:var(--card);border:1px dashed var(--line);border-radius:14px;
padding:48px;text-align:center;color:var(--muted)}
footer{margin-top:36px;color:var(--muted);font-size:12px;text-align:center;line-height:2}
"""


def _esc(v: str) -> str:
    return html.escape(str(v or "").replace("\n", " ").strip())


def _urgency(job: Dict) -> str:
    """报名截止 3 天内打「即将截止」标。"""
    end = (job.get("apply_end") or "").strip()
    if not end:
        return ""
    try:
        d = datetime.strptime(end, "%Y-%m-%d").date()
    except ValueError:
        return ""
    days = (d - datetime.now().date()).days
    if days < 0:
        return ""
    return "即将截止" if days <= 3 else ""


def render_markdown(jobs: List[Dict], cfg: Dict, new_count: int, dup_count: int) -> str:
    account = cfg["source"].get("account_name", "")
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"# {account} · 招聘信息日报（{today}）",
        "",
        f"> 本次抓取结构化 {len(jobs)} 条岗位 | 新增 {new_count} 条 | 历史重复 {dup_count} 条",
        "",
    ]
    if not jobs:
        lines.append("_今天没有筛出招聘类文章。_")
        return "\n".join(lines)

    for i, job in enumerate(jobs, 1):
        tag = _urgency(job)
        title = job.get("article_title") or "(无标题)"
        lines.append(f"## {i}. {title}" + (f"  `{tag}`" if tag else ""))
        lines.append("")
        lines.append(f"- 发布：{job.get('published') or '未知'}")
        for key, label in COLUMNS:
            val = (job.get(key) or "").strip()
            if val:
                lines.append(f"- {label}：{val}")
        for key, label in (("apply_method", "报名方式"), ("exam", "考试安排"), ("contact", "联系方式")):
            val = (job.get(key) or "").strip()
            if val:
                lines.append(f"- {label}：{val}")
        if job.get("url"):
            lines.append(f"- 原文：{job['url']}")
        lines.append("")
    lines.append("---")
    lines.append("_由 wechat-jobs 流水线自动生成，信息以官方公告原文为准。_")
    return "\n".join(lines)


def render_html(jobs: List[Dict], cfg: Dict, new_count: int, dup_count: int) -> str:
    account = cfg["source"].get("account_name", "")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    with_url = sum(1 for j in jobs if j.get("apply_end"))
    urgent = sum(1 for j in jobs if _urgency(j))

    cards = []
    for job in jobs:
        tag = _urgency(job)
        rows = "".join(
            f"<tr><th>{label}</th><td>{_esc(job.get(key))}</td></tr>"
            for key, label in COLUMNS if (job.get(key) or "").strip()
        )
        details = "".join(
            f"<p><span class='k'>{label}</span>{_esc(job.get(key))}</p>"
            for key, label in (("apply_method", "报名方式"), ("exam", "考试安排"), ("contact", "联系方式"))
            if (job.get(key) or "").strip()
        )
        link = (f"<a href='{_esc(job.get('url'))}' target='_blank' rel='noopener'>查看原文 ↗</a>"
                if job.get("url") else "")
        cards.append(f"""
    <article class="card">
      <h2>{_esc(job.get('article_title'))}</h2>
      <div class="meta">
        <span class="badge{' hot' if tag else ''}">{_esc(tag or '招聘')}</span>
        <span>发布 {_esc(job.get('published') or '未知')}</span>
        <span>{_esc(job.get('extract_mode'))} 抽取</span>
        <span>{link}</span>
      </div>
      <table>{rows}</table>
      <div class="detail">{details}</div>
    </article>""")

    body = "\n".join(cards) if cards else \
        '<div class="empty">本次没有筛出招聘类文章。<br>检查采集源是否正常，或调整 config.yaml 的关键词。</div>'

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_esc(account)} · 招聘信息日报</title>
<style>{_CSS}</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>{_esc(account)} · 招聘信息日报</h1>
    <div class="sub">生成时间 {now} · 自动监听取自公众号 RSS，仅作线索聚合，一切以官方公告原文为准</div>
  </header>

  <section class="stats">
    <div class="stat"><b>{len(jobs)}</b><span>筛出的岗位数</span></div>
    <div class="stat"><b>{new_count}</b><span>本次新增</span></div>
    <div class="stat"><b>{dup_count}</b><span>历史重复已跳过</span></div>
    <div class="stat"><b>{with_url}</b><span>有明确报名截止</span></div>
    <div class="stat"><b>{urgent}</b><span>3 天内截止</span></div>
  </section>

  {body}

  <footer>
    由 wechat-jobs 流水线自动生成 · 数据源：公众号 RSS（自建采集服务）<br>
    本页为线索汇总，报名前请务必点开原文逐条核对岗位表与资格条件
  </footer>
</div>
</body>
</html>"""


# ---------------------------------------------------------------- 邮件正文（HTML）

_MAIL_FONT = ("-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC',"
              "'Microsoft YaHei',system-ui,sans-serif")


def render_email_html(jobs: List[Dict], cfg: Dict, window_days: int | None = None) -> str:
    """渲染可直接当作邮件正文的完整 HTML 文档。

    设计约束（每条都是为了「能真的发出去」）：

    · **只用极少量内联样式**，不用 CSS 变量 / flex / 外部样式表 —— 邮件客户端
      对这些支持参差，QQ 邮箱与手机端都要能正常显示。
    · **体积必须小**。正文要作为字符串经 SendMessage 的 body 参数传入；
      若按逐字段铺开的写法（每个字段一个带完整样式的 div），58 条会到 80KB，
      既慢又容易在搬运途中出错。所以改成「一个岗位 = 一个带分隔线的块，
      字段用 ｜ 串成一行」，实测约 20KB。
    · 只承载**最近 N 天**（默认 7 天）窗口内的岗位，由调用方用
      store.query_recent 筛好后传入；超出窗口的历史岗位不再进正文。
    """
    from .mailer import mail_window_days, window_label

    days = window_days or mail_window_days(cfg)
    scope = window_label(days)
    account = cfg["source"].get("account_name", "")
    today = datetime.now().strftime("%Y-%m-%d")
    total = len(jobs)

    FIELDS = [("unit", "单位"), ("category", "岗位类别"), ("headcount", "人数"),
              ("education", "学历"), ("major", "专业"), ("age", "年龄"),
              ("apply_end", "报名截止"), ("salary", "薪酬")]
    EXTRA = [("apply_method", "报名方式"), ("exam", "考试安排"),
             ("contact", "联系方式")]

    blocks = []
    for i, job in enumerate(jobs, 1):
        tag = _urgency(job)
        badge = (f' <b class="h">[{_esc(tag)}]</b>') if tag else ""

        meta = "｜".join(
            f"{lbl}：{_esc(job.get(key))[:120]}"
            for key, lbl in FIELDS if (job.get(key) or "").strip())
        extra = "；".join(
            f"{lbl}：{_esc(job.get(key))[:150]}"
            for key, lbl in EXTRA if (job.get(key) or "").strip())

        url = job.get("url") or ""
        blocks.append(
            '<div class="i">'
            f'<div class="t">{i}. '
            f'{_esc(job.get("article_title") or "(无标题)")}{badge}</div>'
            + (f'<div class="m">{meta}</div>' if meta else "")
            + (f'<div class="e">{extra}</div>' if extra else "")
            + (f'<div class="l"><a href="{_esc(url)}">查看原文 ↗</a></div>'
               if url else "")
            + "</div>")

    body = "\n".join(blocks) if blocks else (
        '<div class="m" style="padding:36px 0;text-align:center;">'
        f'{scope}内没有筛出招聘信息。</div>')

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_esc(account)} · 招聘信息日报 {today}（{scope}）</title>
<style>
body{{margin:0;padding:0;background:#f4f6fb}}
.wrap{{max-width:680px;margin:0 auto;padding:22px 16px 40px;
font-family:{_MAIL_FONT};color:#1c2333}}
h1{{margin:0;font-size:20px;font-weight:700}}
.sub{{font-size:13px;color:#6b7590;margin-top:4px}}
.i{{border-bottom:1px solid #e6e9f2;padding:12px 0}}
.t{{font-size:15px;font-weight:600;color:#1c2333;line-height:1.55}}
.m{{font-size:13px;color:#39405a;margin-top:6px;line-height:1.8}}
.e{{font-size:12px;color:#6b7590;margin-top:4px;line-height:1.7}}
.l{{font-size:13px;margin-top:6px}}
a{{color:#2f5bd7;text-decoration:none}}
.h{{color:#c2410c}}
.n{{color:#2f5bd7}}
.foot{{margin-top:24px;font-size:12px;color:#6b7590;text-align:center;
line-height:1.9}}
</style>
</head>
<body>
<div class="wrap">

  <div>
    <h1>{_esc(account)} · 招聘信息日报</h1>
    <div class="sub">{today} · {scope}共 <b class="n">{total}</b> 条</div>
  </div>

{body}

  <div class="foot">
    由 wechat-jobs 流水线自动生成，仅推送最近 {days} 天发布的岗位。<br>
    本邮件为线索聚合，报名前请点开原文逐条核对岗位表与资格条件。
  </div>
</div>
</body>
</html>"""


def write_reports(jobs: List[Dict], cfg: Dict, new_count: int, dup_count: int) -> List[str]:
    out_dir = cfg["output"]["out_dir"]
    os.makedirs(out_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d")
    written: List[str] = []

    if "md" in cfg["output"].get("formats", []):
        path = os.path.join(out_dir, f"jobs_{stamp}.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(render_markdown(jobs, cfg, new_count, dup_count))
        written.append(path)

    if "html" in cfg["output"].get("formats", []):
        path = os.path.join(out_dir, f"jobs_{stamp}.html")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(render_html(jobs, cfg, new_count, dup_count))
        written.append(path)

    return written
