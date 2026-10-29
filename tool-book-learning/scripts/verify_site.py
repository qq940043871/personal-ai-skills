#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_site.py - 学习站无头回归（Playwright）。

为什么需要它：历次项目手搓了 verify.py / _pwcheck.py / _verify.py / regress.py 四个版本，
断言项大同小异，选择器却各写各的，写错的表现是 30s 超时，极易误判成"站点坏了"。
本脚本把断言固化，并**把选择器集中到SEL 里**，改模板时只改这一处。

⚠ 必须用**已装 Playwright 的解释器**跑（`pip install playwright && playwright install chromium`）。
不同机器路径不同，先探测：
    python -c "import playwright; print('ok')"

用法:
    python verify_site.py --site /path/to/index.html [--shots /path/to/shots] [--keywords 本体,约束,API]
                          [--keep-open] [--timeout 8000]

退出码: 0 = 全过；1 = 有失败项；2 = 环境/参数错误
"""
from __future__ import annotations

import argparse
import os
import pathlib
import re
import sys

# --------------------------------------------------------------------------
# 选择器唯一真源 —— 以 assets/site_template.html 为准，凭印象写必踩坑：
#   搜索框 #q（不是 #search）、命中数 #qcount、自测答案 .ans-btn（点 .qa 无效）、
#   打卡 .done-btn（点 .card 无效）、窄屏汉堡 #menuBtn、章 .chapter / 节 .sec / 卡 .card
# --------------------------------------------------------------------------
SEL = {
    "search": "#q",
    "qcount": "#qcount",
    "chapter": ".chapter",
    "section": ".sec",
    "card": ".card",
    "done_btn": ".done-btn",
    "ans_btn": ".ans-btn",
    "qa": ".qa",
    "qa_answer": ".qa .at",
    "menu_btn": "#menuBtn",
    "sidebar": "#sidebar",
    "theme_btn": "#themeBtn",
    "nav_item": ".nav-item",
    "progress_text": "#progText",
    "panel_quiz": ".panel.quiz",
    "concept_row": ".panel.concepts tbody tr",
    "code_block": ".code-block",
}


def main():
    ap = argparse.ArgumentParser(description="学习站 Playwright 无头回归")
    ap.add_argument("--site", required=True, help="站点 index.html 路径")
    ap.add_argument("--shots", default="", help="截图输出目录")
    ap.add_argument("--keywords", default="", help="搜索验证关键词，逗号分隔")
    ap.add_argument("--timeout", type=int, default=8000, help="单步超时 ms（默认 8000）")
    ap.add_argument("--headful", action="store_true", help="有头模式（调试用）")
    args = ap.parse_args()

    site = os.path.abspath(args.site)
    # file:// URL：Windows 要 C:/...，POSIX 要 file:///home/... （三个斜杠）。
    # 用 pathlib 的 as_uri() 让各平台自己处理，别手拼斜杠数量。
    site_url = pathlib.Path(site).as_uri()
    if not os.path.isfile(site):
        sys.exit("站点不存在: %s" % site)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("需要 Playwright。请用 anaconda python 运行：\n"
                 "  C:\\Users\\qq940\\anaconda3\\python.exe verify_site.py --site ...")

    shots = os.path.abspath(args.shots) if args.shots else os.path.join(
        os.path.dirname(site), "_extract", "_shots")
    os.makedirs(shots, exist_ok=True)

    results = []          # [(名称, ok, 详情)]
    console_errors = []
    page_errors = []

    def check(name, ok, detail=""):
        results.append((name, bool(ok), detail))

    def shot(page, name):
        try:
            page.screenshot(path=os.path.join(shots, name + ".png"))
        except Exception:
            pass

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not args.headful)
        ctx = browser.new_context(viewport={"width": 1440, "height": 950})
        page = ctx.new_page()
        page.set_default_timeout(args.timeout)
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: page_errors.append(str(e)))

        page.goto(site_url)
        page.wait_for_selector(SEL["card"])

        # 1. console / pageerror
        check("console 无报错", not console_errors, "; ".join(console_errors[:3]))
        check("page 无未捕获异常", not page_errors, "; ".join(page_errors[:3]))

        # 2. 占位符 / 脏值残留
        # ⚠ 只扫正文文本节点，跳过 <code>/<pre> —— 技术书正文里本来就有
        # `NaN` / `undefined` 这些字面量（如 JVM 的 dcmpl 遇 NaN 压入 -1），
        # 整页 inner_text 会把代码内容也算进去，属于假失败。
        body = page.evaluate("""()=>{
            const skip = new Set(['CODE','PRE','SAMP','KBD']);
            let out = [];
            (function walk(n){
                if(n.nodeType===3){ out.push(n.nodeValue); return; }
                if(n.nodeType!==1) return;
                if(skip.has(n.tagName)) return;
                for(const c of n.childNodes) walk(c);
            })(document.body);
            return out.join('\\n');
        }""")
        # ⚠ NaN 不能裸判：技术书正文里是合法字面量
        # （如《深入分析Java Web技术内幕》"任一值为 NaN 时分别压入 1 和 -1"）。
        # 只抓"渲染坏掉"的形态：NaN 后面跟着尺寸单位。undefined 仍按整词判。
        bad = [t for t in ("__NAV__", "__CONTENT__", "__TITLE__", "__TOTAL_CARDS__",
                           "[object Object]") if t in body]
        if re.search(r"\bundefined\b", body):
            bad.append("undefined")
        if re.search(r"(?<![\w.])NaN\s*(px|%|em|rem|vh|vw|s)\b", body):
            bad.append("NaN<尺寸>")
        raw = page.content()
        ph = [t for t in ("__NAV__", "__CONTENT__", "__TITLE__", "__STATS__", "__SLUG__")
              if t in raw]
        check("无占位符残留", not ph, str(ph))
        check("正文无 undefined/NaN/[object Object]", not bad, str(bad))
        shot(page, "01_hero")

        # 3. data-id 唯一（打卡依赖它）
        ids = page.eval_on_selector_all(
            SEL["card"], "els=>els.map(e=>e.getAttribute('data-id'))")
        check("data-id 全部非空", all(i for i in ids), "有空 data-id")
        check("data-id 唯一（%d 张卡）" % len(ids), len(ids) == len(set(ids)),
              "重复：%s" % list({i for i in ids if ids.count(i) > 1})[:5])

        # 4. 搜索：命中数与可见卡片数一致
        kws = [k.strip() for k in args.keywords.split(",") if k.strip()]
        if not kws:
            kws = ["的", "a"]      # 无脑默认：至少测两个
        for kw in kws[:3]:
            page.fill(SEL["search"], kw)
            page.wait_for_timeout(180)
            qc = page.inner_text(SEL["qcount"])
            vis = page.eval_on_selector_all(
                SEL["card"], "els=>els.filter(e=>!e.classList.contains('hide')).length")
            m = re.search(r"(\d+)", qc)
            # 零命中时 qcount 显示「无匹配」不含数字，此时 claimed 必须是 0 而不是 -1。
            # 历史 bug：无匹配被算成 claimed=-1 vs vis=0，误报 FAIL。
            claimed = int(m.group(1)) if m else 0
            check("搜索「%s」命中数与可见卡片一致（%d vs %d）" % (kw, claimed, vis),
                  claimed == vis, "qcount=%s 可见=%d" % (qc, vis))
        page.fill(SEL["search"], "")
        page.wait_for_timeout(120)

        # 5. 自测答案可展开且答案非空
        n_ans = page.eval_on_selector_all(SEL["ans_btn"], "els=>els.length")
        if n_ans:
            page.eval_on_selector(SEL["ans_btn"], "e=>e.click()")
            page.wait_for_timeout(160)
            opened = page.eval_on_selector_all(
                SEL["qa"], "els=>els.filter(e=>e.classList.contains('open')).length")
            check("自测答案可展开（%d 题）" % n_ans, opened >= 1, "open=%d" % opened)
            # 全量展开后逐题查答案文本——只查第一道会漏掉
            # 「答案混在题干里、点开是空盒子」这类事故（实测 22 条）。
            page.evaluate("""()=>document.querySelectorAll('.panel.quiz .quiz-acts button[data-act=open]')
                .forEach(b=>b.click())""")
            page.wait_for_timeout(260)
            empty = page.evaluate("""()=>{
                var bad=[];
                document.querySelectorAll('.qa').forEach(function(qa,i){
                    var at=qa.querySelector('.at');
                    if(!(at&&at.innerText.trim())) bad.push(i+1);
                });
                return bad.slice(0,10);
            }""")
            check("全部 %d 道题答案非空" % n_ans, not empty, "空答案题号 %s" % empty)
        else:
            check("存在自测题", False, "没找到 .ans-btn")

        # 6. 打卡写 localStorage + 进度变化
        page.eval_on_selector(SEL["done_btn"], "e=>e.click()")
        page.wait_for_timeout(150)
        prog = page.inner_text(SEL["progress_text"])
        # 只取对象型值：JSON.parse 对非法内容返回 null，直接比较会 TypeError
        ls = page.evaluate(
            "()=>Object.keys(localStorage)"
            ".filter(k=>k.indexOf('done')>=0)"
            ".map(k=>{try{var v=JSON.parse(localStorage.getItem(k));"
            "return [k, (v && typeof v==='object')?Object.keys(v).length:0];}catch(e){return [k,-1];}})")
        check("打卡后进度 > 0（%s）" % prog, "0 /" not in prog, prog)
        check("打卡写入 localStorage", bool(ls) and ls[0][1] > 0, str(ls))
        check("localStorage 键未退化成通用 book",
              bool(ls) and all(k[0] != "pbls:book:done" for k in ls), str(ls))

        # 7. 主题切换
        th_before = page.get_attribute("html", "data-theme")
        page.click(SEL["theme_btn"])
        page.wait_for_timeout(180)
        th_after = page.get_attribute("html", "data-theme")
        check("主题可切换（%s → %s）" % (th_before, th_after), th_before != th_after)
        shot(page, "02_theme")
        page.click(SEL["theme_btn"])
        page.wait_for_timeout(120)

        # 8. 目录跳转
        n_nav = page.eval_on_selector_all(SEL["nav_item"], "els=>els.length")
        y0 = page.evaluate("window.scrollY")
        if n_nav > 1:
            page.eval_on_selector_all(SEL["nav_item"],
                                      "els=>els[els.length-1].click()")
            page.wait_for_timeout(500)
            y1 = page.evaluate("window.scrollY")
            check("目录点击可跳转（%d 条，scrollY %d→%d）" % (n_nav, y0, y1), y1 != y0)
        else:
            check("目录有条目", False, "只有 %d 条" % n_nav)

        # 9. 概念表 / 代码块存在性（信息量检查）
        n_tbl = page.eval_on_selector_all(SEL["concept_row"], "els=>els.length")
        n_code = page.eval_on_selector_all(SEL["code_block"], "els=>els.length")
        print("   统计：章节 %d · 卡片 %d · 概念表行 %d · 代码块 %d · 自测 %d"
              % (page.eval_on_selector_all(SEL["chapter"], "els=>els.length"),
                 len(ids), n_tbl, n_code, n_ans))

        # 10. 阅读体验：A± 字号 / W 宽读 / 排版细节
        for sel in ["#fsPlus", "#fsMinus", "#wideBtn"]:
            check("阅读控件存在 %s" % sel, page.query_selector(sel) is not None)
        if page.query_selector("#fsPlus"):
            # ⚠ 判据不能只看 computed fontSize —— CSS zoom 不改 font-size，
            # 只改渲染尺寸，必须量 getBoundingClientRect。
            # ⚠ 起点不能假设 zoom=100%：localStorage 可能留着上次的值（回归会先跑一遍），
            # 所以"可还原"的判据是**连续两次 A− 能回到自己按 A+ 之前的高度**，
            # 两次 A− 正好抵消一次 A+（步长都是 0.1）。
            def main_h():
                # ⚠ 别量 .main 的 rect —— 新版模板把限宽移到 .hero/.chapter 之后，
                # 带 zoom 的 .main 自身 rect 几乎不随 zoom 变化（实测 185025→184724，
                # 而文档总高 185079→203250，zoom 其实生效了），量 .main 会假失败。
                # 量文档总高才是稳定的判据。
                return page.evaluate(
                    "()=>Math.round(document.documentElement.scrollHeight)")

            h0 = main_h()
            page.click("#fsPlus")
            page.wait_for_timeout(250)
            h1 = main_h()
            check("A+ 字号生效（%d→%dpx）" % (h0, h1), h1 > h0)
            # 核心回归：zoom 绝不能加在 body 上，否则 sticky 顶栏被连带缩放、
            # 按钮命中区偏移导致点击错位（历史踩过，Playwright 实测复现）。
            tb = page.eval_on_selector(".topbar", "e=>getComputedStyle(e).fontSize")
            bd = page.eval_on_selector("body", "e=>getComputedStyle(e).fontSize")
            check("顶栏未被缩放（%s == %s）" % (tb, bd), tb == bd)
            # 还原：步长 0.1，A+ 一次就 A− 一次才能回到起点。
            # ⚠ 不要写成 A− 两次（那是净 -0.1，判据必然假失败）；
            # ⚠ 也不要假设起点 zoom=1 —— localStorage 可能留着上次的值。
            z_after = float(page.evaluate(
                "()=>getComputedStyle(document.body).getPropertyValue('--zoom')") or 1)
            page.click("#fsMinus"); page.wait_for_timeout(280)
            h2 = main_h()
            z_back = float(page.evaluate(
                "()=>getComputedStyle(document.body).getPropertyValue('--zoom')") or 1)
            check("A+ 后 A− 步进对称（%.2f → %.2f）" % (z_after, z_back),
                  abs((z_after - z_back) - 0.1) < 0.011, "%.2f→%.2f" % (z_after, z_back))
            check("A− 字号可还原（%d≈%d）" % (h2, h0), abs(h2 - h0) <= max(4, h0 * 0.002))
            zk = page.evaluate(
                "()=>Object.keys(localStorage).filter(k=>k.endsWith(':zoom'))"
                ".map(k=>[k, localStorage.getItem(k)])")
            check("字号持久化到 localStorage", bool(zk) and 0.8 <= float(zk[0][1]) <= 1.6, str(zk))
        if page.query_selector("#wideBtn"):
            page.click("#wideBtn")
            page.wait_for_timeout(250)
            check("宽读切换生效",
                  page.eval_on_selector("body", "e=>e.classList.contains('wide')"))
            page.click("#wideBtn")
            page.wait_for_timeout(200)
        # 排版细节
        if page.query_selector(".panel.concepts tbody tr:nth-child(even)"):
            zb = page.eval_on_selector(
                ".panel.concepts tbody tr:nth-child(even)",
                "e=>getComputedStyle(e).backgroundColor")
            check("表格斑马纹生效", zb not in ("rgba(0, 0, 0, 0)", "transparent"), zb)
        ov = page.eval_on_selector(".card-body", "e=>getComputedStyle(e).overflowWrap")
        check("长文本折行处理", ov in ("break-word", "anywhere"), ov)

        # 11. 窄屏汉堡菜单
        page.set_viewport_size({"width": 390, "height": 780})
        page.wait_for_timeout(260)
        hidden = page.eval_on_selector(
            SEL["menu_btn"], "e=>getComputedStyle(e).display")
        check("窄屏显示汉堡菜单", hidden != "none", "display=%s" % hidden)
        page.click(SEL["menu_btn"])
        page.wait_for_timeout(300)
        opened = page.eval_on_selector(
            SEL["sidebar"], "e=>e.classList.contains('open')")
        check("汉堡菜单可展开侧栏", opened)
        shot(page, "03_narrow")

        browser.close()

    ok_n = sum(1 for _, ok, _ in results if ok)
    print("\n回归 %s" % site)
    for name, ok, detail in results:
        print("  %s %s%s" % ("PASS" if ok else "FAIL", name,
                             ("  <- " + detail) if (detail and not ok) else ""))
    print("\n%d/%d 通过 · 截图 %s" % (ok_n, len(results), shots))
    sys.exit(0 if ok_n == len(results) else 1)


if __name__ == "__main__":
    main()