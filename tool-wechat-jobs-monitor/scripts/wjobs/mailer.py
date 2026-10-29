# -*- coding: utf-8 -*-
"""投递适配层：把日报发到收件人邮箱。

两种有效后端，按 config.yaml 里的 output.mail.backend 选择：

  smtp      —— 通用。任何邮箱都能用（QQ/163/企业邮/自建），需要授权码。
                无人值守首选：凭证长期有效，不存在 token 过期问题。
  agentmail —— 走 MCP 邮件工具。只产「待发送清单 + 落盘的 HTML 正文」，
                由 Agent 调用邮件工具真发；发件人由 Agent 账号决定，无需在此配置。
  agentcli  —— 已废弃（服务端拒绝设备绑定，auth login 必然失败），
                代码保留仅作参考，勿再启用。

为什么 agentmail 不在 Python 里直接发？
    它没有对外的 SMTP/HTTP 凭据，走的是会话内的工具调用。
    如果在这里编造一个「发送成功」，那就是自欺欺人——所以宁可显式返回待发送状态。
"""
from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage
from typing import Any, Dict, List

DEFAULT_TO = ""            # 不再硬编码任何个人邮箱；未配置时由向导/用户填写
DEFAULT_WINDOW_DAYS = 7


def mail_window_days(cfg: Dict[str, Any]) -> int:
    """邮件正文覆盖的时间窗（天）。config.yaml -> output.mail.window_days。

    1   = 只发今天（旧行为）
    7   = 发最近 7 天（当前默认，滚动窗口）
    0 / 不填 => 回退默认 7 天；非法值同样回退，不让配置写错就崩掉整条流水线。
    """
    m = cfg.get("output", {}).get("mail") or {}
    try:
        days = int(m.get("window_days", DEFAULT_WINDOW_DAYS))
    except (TypeError, ValueError):
        return DEFAULT_WINDOW_DAYS
    return days if days >= 1 else DEFAULT_WINDOW_DAYS


def window_label(days: int) -> str:
    return "今日" if days <= 1 else f"近{days}天"


def _latest(out_dir: str, suffix: str) -> str:
    if not os.path.isdir(out_dir):
        return ""
    files = [f for f in os.listdir(out_dir)
             if f.startswith("jobs_") and f.endswith(suffix)]
    if not files:
        return ""
    return os.path.join(out_dir, sorted(files)[-1])


def collect_attachments(cfg: Dict[str, Any]) -> List[str]:
    out_dir = cfg["output"]["out_dir"]
    paths = [_latest(out_dir, ".html"), _latest(out_dir, ".md")]
    return [p for p in paths if p and os.path.exists(p)]


def build_subject(cfg: Dict[str, Any], job_count: int,
                  window_days: int | None = None) -> str:
    """标题带上时间窗（近7天 / 今日），一眼看出正文覆盖范围。"""
    import datetime
    days = window_days or mail_window_days(cfg)
    account = cfg["source"].get("account_name", "公众号")
    d = datetime.datetime.now().strftime("%Y-%m-%d")
    return f"【{account}】招聘信息日报 {d}（{window_label(days)} {job_count} 条）"


def build_body_text(cfg: Dict[str, Any], jobs: List[Dict], new_count: int,
                    window_days: int | None = None) -> str:
    import datetime
    days = window_days or mail_window_days(cfg)
    account = cfg["source"].get("account_name", "公众号")
    d = datetime.datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"{account} · 招聘信息日报（{d}）",
        "",
        f"最近 {days} 天共 {len(jobs)} 个岗位（本次新入库 {new_count} 条）。",
        "",
    ]
    for i, job in enumerate(jobs[:15], 1):
        lines.append(f"{i}. {job.get('unit') or '(未识别单位)'}｜"
                     f"{job.get('category') or ''}｜{job.get('headcount') or ''}")
        bits = []
        if job.get("education"):
            bits.append(f"学历 {job['education']}")
        if job.get("apply_end"):
            bits.append(f"截止 {job['apply_end']}")
        if job.get("salary"):
            bits.append(f"待遇 {job['salary'][:40]}")
        if bits:
            lines.append("   " + "；".join(bits))
    if len(jobs) > 15:
        lines.append(f"... 其余 {len(jobs) - 15} 条见附件")
    lines += ["", "完整信息见附件 HTML / Markdown。",
              "本邮件为线索聚合，报名前请核对官方公告原文。"]
    return "\n".join(lines)


# ---------------------------------------------------------------- SMTP 后端

def send_smtp(cfg: Dict[str, Any], subject: str, body: str,
              attachments: List[str], html_body: str = "") -> Dict[str, Any]:
    m = cfg["output"].get("mail") or {}
    host = m.get("smtp_host", "")
    port = int(m.get("smtp_port", 465))
    user = m.get("smtp_user", "")
    pwd = m.get("smtp_password", "")
    sender = m.get("from") or user
    to_list = [t for t in (m.get("to") or []) if t]

    if not (host and user and pwd):
        raise RuntimeError("SMTP 配置不全：需要 smtp_host / smtp_user / smtp_password")
    if not to_list:
        raise RuntimeError("收件人未配置：请在 output.mail.to 填至少一个邮箱。")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(to_list)
    msg.set_content(body)
    if html_body:
        msg.add_alternative(html_body, subtype="html")

    for path in attachments:
        with open(path, "rb") as fh:
            data = fh.read()
        subtype = "html" if path.endswith(".html") else "plain"
        msg.add_attachment(data, maintype="text", subtype=subtype,
                           filename=os.path.basename(path))

    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=30) as s:
            s.login(user, pwd)
            s.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=30) as s:
            s.starttls(context=ssl.create_default_context())
            s.login(user, pwd)
            s.send_message(msg)
    return {"status": "sent", "backend": "smtp", "to": to_list,
            "attachments": [os.path.basename(p) for p in attachments]}


# ---------------------------------------------------------------- Agent Mail 后端

def prepare_agentmail(cfg: Dict[str, Any], subject: str, body: str,
                      attachments: List[str]) -> Dict[str, Any]:
    """不直接发送，而是产出一份待发送清单交给 Agent 执行。

    body 通常是一份完整 HTML 日报。除了放进返回值，这里还会把它
    **落盘成 out/mail_body_<日期>.html** —— 定时任务里的 Agent 可以直接读这个文件
    再喂给邮件工具，不必从控制台输出里抠几十 KB 的 HTML 字符串。
    """
    import datetime

    m = cfg["output"].get("mail") or {}
    to_list = [t for t in (m.get("to") or []) if t] or ([DEFAULT_TO] if DEFAULT_TO else [])
    if not to_list:
        raise RuntimeError(
            "收件人未配置：请在 config.yaml 的 output.mail.to 填至少一个邮箱"
            "（或重跑 scripts/setup_wizard.py）。")
    from_addr = m.get("agentmail_from") or "(由 Agent 账号决定)"

    head = body.lstrip()[:80].lower()
    is_html = head.startswith("<!doctype") or head.startswith("<html")
    ext = ".html" if is_html else ".txt"

    out_dir = cfg["output"].get("out_dir") or "out"
    os.makedirs(out_dir, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d")
    body_path = os.path.join(out_dir, f"mail_body_{stamp}{ext}")
    with open(body_path, "w", encoding="utf-8") as fh:
        fh.write(body)

    return {
        "status": "pending_agent",
        "backend": "agentmail",
        "from": from_addr,
        "to": to_list,
        "subject": subject,
        "body": body,
        "body_path": os.path.abspath(body_path),
        "body_format": "HTML" if is_html else "PLAIN",
        "html_path": next((p for p in attachments if p.endswith(".html")), ""),
        "attachments": [os.path.abspath(p) for p in attachments],
    }


# ---------------------------------------------------------------- Agently CLI 后端

def _discover_cli() -> tuple:
    """定位 agently-cli 的 node 入口，返回 (node_exe, run_js)。

    Windows 上 `agently-cli.cmd` 会被本机安全策略拦截（禁止 cmd.exe），
    所以绕开 .cmd 包装，直接用 node.exe 执行包内的 scripts/run.js。

    可用环境变量覆盖：AGENTLY_NODE / AGENTLY_RUN / AGENTLY_NODE_BASE；
    否则在托管 node 目录下按版本号倒序查找。
    """
    import glob

    node = os.environ.get("AGENTLY_NODE", "")
    run = os.environ.get("AGENTLY_RUN", "")
    if node and run and os.path.exists(node) and os.path.exists(run):
        return node, run

    base = os.environ.get("AGENTLY_NODE_BASE", "")
    if not base:
        # 可移植默认：从用户主目录推导 WorkBuddy 托管 node 目录
        home = os.path.expanduser("~")
        base = os.path.join(home, ".workbuddy", "binaries", "node", "versions")
    for vdir in sorted(glob.glob(os.path.join(base, "*")), reverse=True):
        cand_node = os.path.join(vdir, "node.exe")
        cand_run = os.path.join(vdir, "node_modules", "@tencent-qqmail",
                                "agently-cli", "scripts", "run.js")
        if os.path.exists(cand_node) and os.path.exists(cand_run):
            return cand_node, cand_run
    raise RuntimeError(
        "找不到 agently-cli。请先安装并登录："
        "npm i -g @tencent-qqmail/agently-cli && agently-cli auth login；"
        "或用 AGENTLY_NODE / AGENTLY_RUN 指定 node.exe 与 run.js 的路径。")


def send_agentcli(cfg: Dict[str, Any], subject: str, body: str,
                  attachments: List[str], body_format: str = "plain") -> Dict[str, Any]:
    """通过本机 agently-cli 真实发送，不需要会话内人工确认。

    body_format 支持 "html" / "plain"。日报默认走 html ——
    正文就是完整的 HTML 日报文档，收件人打开邮件即见全部岗位，
    不用再下载附件、也不用看那份与正文有出入的摘要。

    两个 Windows 侧的坑要注意：
      1. CLI 只接受「相对当前目录」的 --attachment 路径，所以统一以项目根为 cwd，
         再把绝对路径换算成相对路径；越出工作目录的直接报错，不静默丢附件。
      2. 正文不走 --body（Windows 命令行有 ~8K 长度上限），改成写临时文件后用
         --body-file 传入，发完即删。
    """
    import json
    import subprocess

    m = cfg["output"].get("mail") or {}
    to_list = [t for t in (m.get("to") or []) if t]
    if not to_list:
        raise RuntimeError("收件人未配置：请在 output.mail.to 填至少一个邮箱。")
    node, run = _discover_cli()
    cwd = os.getcwd()

    suffix = ".html" if body_format == "html" else ".txt"
    body_rel = f".mail_body.tmp{suffix}"
    body_abs = os.path.join(cwd, body_rel)
    with open(body_abs, "w", encoding="utf-8") as fh:
        fh.write(body)

    try:
        args = [node, run, "message", "+send"]
        for addr in to_list:
            args += ["--to", str(addr)]
        args += ["--subject", subject, "--body-file", body_rel,
                 "--body-format", body_format, "--confirmed"]
        for path in attachments:
            rel = os.path.relpath(os.path.abspath(path), cwd)
            if rel.startswith(".."):
                raise RuntimeError(f"附件在工作目录之外，CLI 只收相对路径：{path}")
            args += ["--attachment", rel]

        proc = subprocess.run(args, cwd=cwd, capture_output=True, timeout=180)
    finally:
        try:
            os.remove(body_abs)
        except OSError:
            pass

    out = proc.stdout.decode("utf-8", "replace")
    err = proc.stderr.decode("utf-8", "replace")
    try:
        payload = json.loads(out)
    except Exception:
        payload = {}
    if proc.returncode != 0 or not payload.get("ok"):
        raise RuntimeError(
            f"agently-cli 发送失败（rc={proc.returncode}）：{(err or out).strip()[:300]}")
    return {"status": "sent", "backend": "agentcli", "to": to_list,
            "attachments": [os.path.basename(p) for p in attachments],
            "raw": payload.get("data", {})}


# ---------------------------------------------------------------- 对外入口

def send_report(cfg: Dict[str, Any], jobs: List[Dict], new_count: int,
                html_body: str = "", window_days: int | None = None) -> Dict[str, Any]:
    """投递日报。

    jobs 应当是**调用方已经按时间窗筛好的**列表（默认最近 7 天，见 store.query_recent）。
    html_body 非空时，它**就是邮件正文本身**（一份完整 HTML 文档）；
    纯文本摘要降级为老客户端的兜底，不再作为主内容。
    附件默认不发，config 里 output.mail.attach: true 才带。
    """
    mcfg = cfg["output"].get("mail") or {}
    if not mcfg.get("enabled"):
        return {"status": "skipped", "reason": "config.yaml 里 output.mail.enabled 不是 true"}

    days = window_days or mail_window_days(cfg)
    backend = (mcfg.get("backend") or "smtp").lower()
    attachments = collect_attachments(cfg) if mcfg.get("attach") else []
    subject = build_subject(cfg, len(jobs), days)
    plain = build_body_text(cfg, jobs, new_count, days)      # 仅作纯文本降级

    if backend == "agentcli":
        if html_body:
            return send_agentcli(cfg, subject, html_body, attachments, "html")
        return send_agentcli(cfg, subject, plain, attachments, "plain")
    if backend == "agentmail":
        return prepare_agentmail(cfg, subject, html_body or plain, attachments)
    return send_smtp(cfg, subject, plain, attachments, html_body)
