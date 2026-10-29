# -*- coding: utf-8 -*-
"""交互式初始化向导：把「一个公众号 + 一个邮箱」变成一份可跑的 config.yaml。

设计原则
--------
1. **两条路都通**：
   - 交互模式（人类双击/终端跑）：一步步问，带默认值与解释；
   - 非交互模式（Agent 调用）：所有答案走命令行参数，零提问。
2. **温柔失败**：任何一步都能 Ctrl-C 退出且不写坏文件；写 config.yaml 前先备份旧的。
3. **绝不拍脑袋**：公众号选错是这套流程最大的坑（主号/子号内容天差地别），
   所以向导会强制「验证」一次 —— 拉取该号最近文章，把公众号名与标题打给用户看。

用法：
    python scripts/setup_wizard.py                       # 全交互
    python scripts/setup_wizard.py --book-id "MP_WXS_xxx" --account "某某招聘" \\
        --to me@qq.com --preset 招聘 --yes               # 全非交互（Agent 用）

产物：当前工作目录下的 config.yaml（data/、out/ 也以工作目录为根）。
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import datetime

# 让脚本可直接运行：把 scripts/ 加进 path
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from wjobs.config import PRESETS, WORKSPACE  # noqa: E402


# ---------------------------------------------------------------- 工具

def _ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        got = input(f"{prompt}{suffix}: ").strip()
    except EOFError:
        got = ""
    return got or default


def _ask_choice(prompt: str, options: list, default: str) -> str:
    print(f"\n{prompt}")
    for i, opt in enumerate(options, 1):
        mark = " (默认)" if opt == default else ""
        print(f"  {i}. {opt}{mark}")
    got = _ask("请输入序号或名称", default)
    if got.isdigit() and 1 <= int(got) <= len(options):
        return options[int(got) - 1]
    return got if got in options else default


def _ask_yn(prompt: str, default: bool = True) -> bool:
    d = "Y/n" if default else "y/N"
    got = _ask(f"{prompt} ({d})", "").lower()
    if not got:
        return default
    return got in ("y", "yes", "是", "1", "true")


def _resolve_book_id(raw: str) -> str:
    """把用户粘的任何东西（链接/编码串/纯 ID）还原成 bookId。"""
    raw = (raw or "").strip()
    if not raw:
        return ""
    try:
        from wjobs.weread import parse_book_id
        return parse_book_id(raw)
    except Exception:
        return ""


def _probe_account(book_id: str, cookie: str = "") -> tuple:
    """拉一下该号最近文章，返回 (公众号名, 标题列表)。用于强制验证选号。"""
    try:
        from wjobs.weread import WeReadClient, cookie_auto
        ck = cookie
        if not ck:
            ck, used = cookie_auto()
            print(f"  [ok] cookie 来源：{used}")
        client = WeReadClient(ck)
        arts = client.fetch(book_id, limit=5, with_content=False)
        name = ""
        titles = []
        for a in arts:
            titles.append(a.title)
        # 公众号名从 list_articles 原始字段里取
        raw = client.list_articles(book_id, offset=0, count=1)
        if raw:
            name = raw[0].get("mp_name") or ""
        return name, titles
    except Exception as exc:
        print(f"  [warn] 验证失败：{exc}")
        return "", []


# ---------------------------------------------------------------- 主体

def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="公众号监听流水线 · 初始化向导")
    p.add_argument("--book-id", default="", help="公众号 bookId / 阅读页链接 / 编码串")
    p.add_argument("--account", default="", help="公众号名称（报告标题用）")
    p.add_argument("--source", default="", choices=["", "weread", "rss", "mock"],
                   help="采集源类型；给了 book-id 默认 weread")
    p.add_argument("--rss-url", default="", help="source=rss 时的订阅地址")
    p.add_argument("--to", default="", help="收件邮箱，逗号分隔")
    p.add_argument("--preset", default="", choices=list(PRESETS), help="关键词预设")
    p.add_argument("--window-days", type=int, default=7, help="邮件正文时间窗（天）")
    p.add_argument("--backend", default="agentmail",
                   choices=["agentmail", "smtp"], help="投递后端")
    p.add_argument("--cookie", default="", help="微信读书 cookie（也可稍后单独获取）")
    p.add_argument("--cookie-from", dest="cookie_from", default="auto",
                   choices=["auto", "browser", "manual"],
                   help="cookie 获取方式（auto 会按是否给了 cookie 决定）")
    p.add_argument("--verify", dest="verify", action="store_true", default=None,
                   help="强制验证公众号（拉最近文章）")
    p.add_argument("--no-verify", dest="verify", action="store_false",
                   help="跳过验证")
    p.add_argument("--yes", "-y", action="store_true",
                   help="非交互：全部采用参数与默认值，不提问")
    p.add_argument("--out", default="", help="config.yaml 输出路径（默认 ./config.yaml）")
    args = p.parse_args(argv)

    out_path = args.out or os.path.join(WORKSPACE, "config.yaml")
    noninteractive = args.yes

    print("=" * 62)
    print("  微信公众号信息监听流水线 · 初始化向导")
    print("=" * 62)
    print(f"工作目录：{WORKSPACE}")
    print(f"配置文件：{out_path}")

    # ---- 1. 采集源 ----
    book_id = _resolve_book_id(args.book_id)
    source = args.source or ("weread" if (book_id or args.book_id) else "")
    if not noninteractive and not source:
        source = _ask_choice("采集源类型：", ["weread", "rss", "mock"], "weread")
    source = source or "weread"

    rss_url = args.rss_url
    if source == "rss" and not rss_url:
        if noninteractive:
            print("[error] --source rss 需要 --rss-url")
            return 1
        rss_url = _ask("RSS 订阅地址（we-mp-rss / wechat2rss 产物）")

    # ---- 2. 公众号 bookId ----
    if source == "weread" and not book_id:
        if noninteractive:
            print("[error] --source weread 需要 --book-id")
            return 1
        print("\n怎么拿 bookId？浏览器打开目标公众号的微信读书阅读页，把整条链接粘进来即可；")
        print("也可以直接粘 MP_WXS_ 开头的 ID。")
        raw = _ask("请粘贴链接 / bookId")
        book_id = _resolve_book_id(raw)
        if not book_id:
            print("[error] 没能从输入里认出 bookId，请重试。")
            return 1
        print(f"  [ok] 已识别 bookId = {book_id}")

    # ---- 3. 公众号名称 ----
    account = args.account
    verify = args.verify if args.verify is not None else (not noninteractive)
    if source == "weread" and not account and not noninteractive:
        account = _ask("公众号名称（显示用，验证通过后会自动补全）")

    # ---- 4. 强制验证（选号是最大的坑）----
    if source == "weread" and verify:
        print("\n[验证] 拉取该号最近文章，确认没选错号 ...")
        probed_name, titles = _probe_account(book_id, args.cookie)
        if probed_name:
            print(f"  实际公众号名：{probed_name}")
            if not account:
                account = probed_name
            elif account != probed_name:
                print(f"  [注意] 你填的名称「{account}」与接口返回「{probed_name}」不一致。")
        for t in titles[:5]:
            print(f"    · {t[:48]}")
        if not titles:
            print("  [warn] 没拉到任何文章 —— 可能 cookie 失效，或该号没有内容。")
        if not noninteractive:
            if not _ask_yn("以上是你要监听的号吗？", True):
                print("已取消。换对号之后重跑本向导。")
                return 1
    account = account or "未命名公众号"

    # ---- 5. 关键词预设 ----
    preset = args.preset
    if not noninteractive and not preset:
        preset = _ask_choice("内容类型（决定关键词）：", list(PRESETS), "招聘")
    preset = preset or "招聘"

    # ---- 6. 收件邮箱 ----
    to = args.to
    if not noninteractive and not to:
        to = _ask("收件邮箱（多个用逗号分隔）")
    while not to and not noninteractive:
        print("  [必填] 请填一个收件邮箱，否则日报没有收件人。")
        to = _ask("收件邮箱（多个用逗号分隔）")
    to_list = [t.strip() for t in (to or "").split(",") if t.strip()]
    if not to_list:
        to_list = [""]      # 留空占位，运行时若仍为空会给出明确报错

    # ---- 7. 时间窗 ----
    window = args.window_days
    if not noninteractive:
        try:
            window = int(_ask("邮件正文覆盖最近几天（1=今天，7=一周）", str(window)))
        except ValueError:
            window = 7
    window = max(1, window or 7)

    # ---- 8. 投递后端 ----
    backend = args.backend
    if not noninteractive and backend == "agentmail":
        backend = _ask_choice("投递后端：", ["agentmail", "smtp"], "agentmail")

    # ---- 9. cookie ----
    cookie = args.cookie
    if source == "weread" and not cookie and not noninteractive:
        print("\n[微信读书 cookie] 二选一：")
        print("  a) 已用浏览器登录过 weread.qq.com —— 直接回车，运行时自动读取；")
        print("  b) 手动粘贴 cookie 串（含 wr_skey=...）。")
        cookie = _ask("cookie（可留空 = 自动从浏览器读；也可稍后用 tools 单独获取）", "")

    # ---- 10. 写 config.yaml ----
    cfg_text = _render_config(source, book_id, rss_url, account, preset,
                              to_list, window, backend, cookie, args.cookie_from)
    if os.path.exists(out_path):
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        bak = f"{out_path}.bak.{stamp}"
        shutil.copy2(out_path, bak)
        print(f"\n[ok] 已备份旧配置 → {bak}")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(cfg_text)
    print(f"[ok] 已写出配置 → {out_path}")

    print("\n下一步：")
    print(f"  python scripts/run_pipeline.py --config \"{out_path}\"")
    print("（首次建议加 --limit 20 少抓点，验证链路通了再放开）")
    return 0


def _render_config(source: str, book_id: str, rss_url: str, account: str,
                   preset: str, to_list: list, window: int, backend: str,
                   cookie: str, cookie_from: str = "auto") -> str:
    p = PRESETS.get(preset) or PRESETS["招聘"]
    t_inc = "\n".join(f"    - {w}" for w in p["title_include"]) or "    []"
    b_inc = "\n".join(f"    - {w}" for w in p["body_include"]) or "    []"
    exc = "\n".join(f"    - {w}" for w in p["exclude"]) or "    []"
    to_vals = [t for t in to_list if t]
    to_line = "    to:\n" + ("\n".join(f'      - "{t}"' for t in to_vals)
                             if to_vals else '      # - "you@example.com"   # ← 请填写收件邮箱')

    src_block = ""
    if source == "weread":
        cf = "manual" if cookie else "browser"
        # 自动探测本机浏览器，避免在只有 Chrome 的机器上硬写 edge
        try:
            from get_cookie import detect_browsers
            _det = detect_browsers()
        except Exception:
            _det = []
        browser = _det[0] if _det else "edge"
        browser_hint = ("（自动探测）" if _det else "（未探测到，请按本机情况改）")
        src_block = f"""  weread:
    # 目标公众号 bookId。也接受阅读页链接或编码串，运行时自动还原。
    book_id: "{book_id}"
    # browser = 自动从本机浏览器读 cookie（推荐）；manual = 用下面手填的
    cookie_from: {cf}
    browser: {browser}   # {browser_hint}
    cookie: "{cookie}"
"""
    elif source == "rss":
        src_block = f"""  # type: rss —— 消费上游采集服务产出的标准 RSS
  rss_url: "{rss_url}"
"""
    else:
        src_block = '  rss_url: "mock"\n'

    return f"""# ============================================================
#  公众号信息监听 —— 配置文件（由 setup_wizard.py 生成）
#  改完直接重跑：python scripts/run_pipeline.py
# ============================================================

source:
  # 采集源：weread（零依赖直连微信读书）/ rss（上游采集服务）/ mock（离线演示）
  type: {source}
{src_block}
  # 目标公众号名称（仅用于报告标题与打标）
  account_name: "{account}"

  # 单次最多处理多少条文章
  max_items: 60
  fetch_workers: 4
  timeout: 15


filter:
  # 关键词预设：{preset}
  title_include:
{t_inc}
  body_include:
{b_inc}
  exclude:
{exc}
  # true = 必须命中标题关键词才算目标文（更准，推荐）
  require_title_hit: {str(p['require_title_hit']).lower()}


extract:
  # rule = 纯正则，离线零成本（默认）；llm = 调大模型抽取（需填 api_key）
  mode: rule
  # 运营方自己的投稿/合作邮箱域名（自动从「联系方式」里剔除）。
  # 按需增删，例如本地宝类账号会挂自己的投稿邮箱。
  contact_email_deny: []
  llm:
    base_url: "https://api.deepseek.com/v1"
    api_key: ""
    model: "deepseek-chat"
    temperature: 0


output:
  data_dir: "data"
  out_dir: "out"
  formats: ["md", "html"]

  mail:
    enabled: true
    # agentmail = 走 Agent 邮箱 MCP 工具（只产待发送清单，由 Agent 真发）
    # smtp      = 通用 SMTP，凭证长效，无人值守首选
    backend: {backend}
{to_line}
    attach: false
    # 邮件正文覆盖最近 N 天（按发布日算，含今天）；7=一周一覆盖
    window_days: {window}
    # agentmail 后端只用于展示；发件人实际由你登录的账号决定。
    agentmail_from: ""

    smtp_host: "smtp.qq.com"
    smtp_port: 465
    smtp_user: ""
    smtp_password: ""
    from: ""
"""


if __name__ == "__main__":
    raise SystemExit(main())
