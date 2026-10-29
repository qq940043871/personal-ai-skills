#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WorkBuddy「Buddy 加油站」每日签到。

默认 dry-run：只查签到状态，不领取。
只有显式加 --claim 才真签到，且会先查 today_checked_in 做幂等保护。

用法：
    python checkin.py --cdp-port 9222            # 只查状态
    python checkin.py --cdp-port 9222 --claim    # 签到
    python checkin.py --cdp-port 9222 --list     # 打印所有页面，挑正确的渲染页

渲染进程跑在 https://www.workbuddy.cn 上，用页面自身 fetch 可自带登录态。
"""

import argparse
import json
import sys

HOST = "https://www.workbuddy.cn"
STATUS_PATH = "/v2/billing/meter/checkin-activity-status"
CLAIM_PATH = "/v2/billing/meter/tool-daily-checkin"

STATUS_CODE = {
    0: "成功",
    1001: "今天已签到过",
    1002: "当前不满足签到条件",
    1003: "活动已结束",
}


def fetch_json(page, path):
    """在渲染上下文里发同源 POST，自动带上 Electron session 的登录态。"""
    expr = (
        "async (p) => {"
        "const r = await fetch(p, {method:'POST',"
        "headers:{'Content-Type':'application/json'},body:'{}'});"
        "const t = await r.text();"
        "try { return {status: r.status, body: JSON.parse(t)}; }"
        "catch (e) { return {status: r.status, body: t}; }"
        "}"
    )
    return page.evaluate(expr, HOST + path)


def pick_page(context, verbose_pages=False):
    """挑出加载了 www.workbuddy.cn 的渲染页。"""
    for ctx in context.pages if hasattr(context, "pages") else [context]:
        for page in (context.pages if hasattr(context, "pages") else [context]):
            if verbose_pages:
                try:
                    print("  page:", page.url[:120])
                except Exception:
                    print("  page: <no url>")
            if "workbuddy.cn" in page.url:
                return page
    return None


def run(args):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("缺少 playwright。请改用 anaconda 解释器运行：")
        print("  C:\\Users\\qq940\\anaconda3\\python.exe scripts/checkin.py ...")
        return 2

    cdp = "http://127.0.0.1:%d" % args.cdp_port
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(cdp, timeout=15000)
        ctx = browser.contexts[0] if browser.contexts else None
        if ctx is None:
            print("连不上浏览器上下文，确认客户端是带 --remote-debugging-port 启动的。")
            return 3

        if args.list:
            for page in ctx.pages:
                try:
                    print("  %s" % page.url[:140])
                except Exception:
                    print("  <no url>")
            return 0

        page = pick_page(ctx)
        if page is None:
            print("没找到 workbuddy.cn 的渲染页，先用 --list 看一眼页面列表。")
            return 4

        print("目标页面:", page.url[:120])

        print("\n[1/2] 查询今日签到状态 ...")
        try:
            r = fetch_json(page, STATUS_PATH)
            st = r["body"] if isinstance(r.get("body"), dict) else {}
            data = st.get("data") or {}
            code = st.get("code")
            if code == 0 and data:
                print("  已签到:", data.get("today_checked_in"))
                print("  连签天数:", data.get("streak_days"))
                print("  每日积分:", data.get("daily_credit"))
                print("  今日已领:", data.get("today_credit"))
                print("  活动进行中:", data.get("active"))
                if data.get("today_checked_in"):
                    print("\n今天已经领过了，跳过，不做重复领取。")
                    browser.close()
                    return 0
            else:
                print("  状态查询返回 code=%s %s" % (code, STATUS_CODE.get(code, "")))
                print("  原始:", json.dumps(st, ensure_ascii=False)[:400])
        except Exception as e:
            print("  状态查询失败（非致命）:", e)

        if not args.claim:
            print("\n[dry-run] 未指定 --claim，不执行领取。")
            browser.close()
            return 0

        print("\n[2/2] 执行签到 ...")
        r = fetch_json(page, CLAIM_PATH)
        body = r["body"]
        if isinstance(body, dict):
            code = body.get("code")
            data = body.get("data") or {}
            print("  HTTP:", r.get("status"))
            print("  业务码:", code, STATUS_CODE.get(code, "未知"))
            if code == 0:
                print("  本次积分:", data.get("credit"))
                print("  连签天数:", data.get("streak_days"))
                print("  是否大奖日:", data.get("is_streak_day"))
                print("\n签到完成。")
            else:
                print("  未领取。原始:", json.dumps(body, ensure_ascii=False)[:400])
                return 1
        else:
            print("  原始:", str(body)[:400])
            return 1
        browser.close()
    return 0


def main():
    ap = argparse.ArgumentParser(description="WorkBuddy Buddy 加油站签到")
    ap.add_argument("--cdp-port", type=int, default=9222, help="客户端调试端口，默认 9222")
    ap.add_argument("--claim", action="store_true", help="真正执行签到（默认只查状态）")
    ap.add_argument("--list", action="store_true", help="只列出渲染页面 URL")
    args = ap.parse_args()
    sys.exit(run(args))


if __name__ == "__main__":
    main()
