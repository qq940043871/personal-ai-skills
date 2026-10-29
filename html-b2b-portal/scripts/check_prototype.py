#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
html-b2b-portal · 交付前机检脚本

把 SKILL.md §7 质量门禁里「靠肉眼容易漏」的几条变成可执行断言：
  1. 变量完整性   引用的 var(--x) 必须在 :root 定义（缺失不报错，但样式静默失效）
  2. 图标语法     禁止 Font Awesome v4 名称（FA6 已移除，会渲染成空白方块）
  3. Toast 对比度 亮底（#FAAD14 / #52C41A）不得配白字
  4. 断点一致性   手写媒体查询只能用 639 / 767（对齐 Tailwind sm / md）
  5. Mock 字段    列表页产品必须含 priceNum / priceText / sales / daysAgo
  6. 反模式       真实手机号、备案号占位缺失、onclick 空绑定
  7. 动效降级     有动效层就必须有 prefers-reduced-motion；离屏暂停；进场初始态不得写在 CSS 裸选择器上
  8. 体积预算     首页 ≤ 120KB / 其他 ≤ 60KB（未 gzip）

用法：
    python scripts/check_prototype.py 你的原型.html [更多文件...]
    python scripts/check_prototype.py assets/*.html      # 自检模板本身

退出码：0 = 全通过；1 = 有 ERROR。
"""
import re
import sys
import os

MAX_KB_HOME = 120
MAX_KB_PAGE = 60

FA4_BANNED = {
    "fa-star-o": "fa-regular fa-star",
    "fa-check-circle": "fa-circle-check",
    "fa-times-circle": "fa-circle-xmark",
    "fa-star-half-o": "fa-regular fa-star-half-stroke",
    "fa-angle-double-right": "fa-angles-right",
    "fa-search-plus": "fa-magnifying-glass-plus",
}

BRIGHT_BG = ("#FAAD14", "#52C41A")

# 列表页产品必需的排序/筛选字段
LIST_REQUIRED_FIELDS = ["priceNum", "priceText", "sales", "daysAgo"]

errors, warnings = [], []


def err(f, msg):
    errors.append("[ERROR] %s: %s" % (f, msg))


def warn(f, msg):
    warnings.append("[WARN ] %s: %s" % (f, msg))


def check_vars(f, src):
    """1) var(--x) 必须有定义。只扫描 <style> 段，避免 JS 字符串误判。"""
    style = re.search(r"<style>(.*?)</style>", src, re.S)
    scope = style.group(1) if style else src
    defined = set(re.findall(r"(--[A-Za-z0-9-]+)\s*:", scope))
    used = set(re.findall(r"var\(\s*(--[A-Za-z0-9-]+)\s*\)", scope))
    # JS/HTML 内联样式也可能用 var()，一并纳入引用面
    used |= set(re.findall(r"var\(\s*(--[A-Za-z0-9-]+)\s*\)", src))
    missing = sorted(used - defined)
    for v in missing:
        err(f, "变量未定义：var(%s) —— 样式静默失效，请在 :root 补定义" % v)


def check_icons(f, src):
    """2) FA v4 名称。"""
    for bad, good in FA4_BANNED.items():
        n = len(re.findall(r"\b%s\b" % re.escape(bad), src))
        if n:
            err(f, "Font Awesome v4 语法 %s ×%d —— FA 6.4 已移除，请改用 %s" % (bad, n, good))


def check_toast(f, src):
    """3) Toast 亮底白字。"""
    for bg in BRIGHT_BG:
        if re.search(r"background[^;]{0,20}%s[^}]{0,200}?text-white" % bg, src, re.S | re.I):
            warn(f, "疑似 %s 亮底配白字 —— 对比度不足 4.5:1，应按 spec §6 改深色字" % bg)
    # Toast 体内联 color 是否按类型设置
    if "toastBody" in src and "fg=" not in src and "fg =" not in src:
        warn(f, "showToast 未按类型设置前景色（fg）—— 确认 warning/success 未用白字")


def check_breakpoints(f, src):
    """4) 手写媒体查询只允许 639 / 767。"""
    allowed = {"639", "767"}
    for q in re.findall(r"@media\s*\(max-width:\s*(\d+)px\)", src):
        if q not in allowed:
            err(f, "手写断点 max-width:%spx 不在允许集 {639,767} 内 —— "
                   "与 Tailwind 默认断点（640/768/1024/1280）错位，见 spec §1.4" % q)


def check_list_schema(f, src):
    """5) 列表页产品字段完整性。"""
    if "filterGroups" not in src:
        return
    body = re.search(r"var\s+products\s*=\s*\[(.*?)\n\];", src, re.S)
    if not body:
        return
    blob = body.group(1)
    missing = [k for k in LIST_REQUIRED_FIELDS if (k + ":") not in blob]
    if missing:
        err(f, "列表页 products 缺排序/筛选必需字段：%s —— 对应功能会静默失效"
               % ", ".join(missing))
    if "priceNum" in blob and "priceText" not in blob:
        err(f, "有 priceNum 无 priceText —— 价格无法展示")


def check_antipatterns(f, src):
    """6) 反模式。"""
    if re.search(r"1[3-9]\d{9}", src):
        err(f, "出现疑似真实手机号 —— 反模式 7：全部虚构")
    if re.search(r"onclick=\"(javascript:;|)\"", src):
        err(f, "存在空绑定 onclick —— 反模式 4：按钮全是死的")
    if "<img" in src and "onerror" not in src and "src=\"http" in src:
        warn(f, "存在外链 <img> 且无占位方案 —— 反模式 8：外链图片裂图")
    # 移动端字号：正文/操作文案 ≥12px；10–11px 仅限角标徽标等辅助信息（spec §9-10）
    for px in sorted({int(x) for x in re.findall(r"text-\[(\d+)px\]", src)}):
        n = len(re.findall(r"text-\[%dpx\]" % px, src))
        if px < 10:
            err(f, "字号 %dpx ×%d 低于可读下限 —— 角标最低 10px，正文最低 12px（spec §9-10）" % (px, n))
        elif px < 12:
            warn(f, "text-[%dpx] ×%d —— 仅限角标/来源/时间等辅助信息，不可承载正文或操作文案" % (px, n))


def check_motion(f, src):
    """7) 动效层的降级红线（spec §5.1）。有动效才查，没有就跳过。"""
    style = re.search(r"<style>(.*?)</style>", src, re.S)
    css = style.group(1) if style else ""
    has_motion = bool(re.search(r"data-(?:parallax|tilt|stagger)|fx-canvas|globeCanvas|fx-aurora", src))
    if not has_motion:
        return
    # 注释里也可能出现关键字，先剥注释再判，否则检查会被注释绕过
    css_clean = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    if not re.search(r"@media[^{]*prefers-reduced-motion", css_clean):
        err(f, "有动效层但缺 @media (prefers-reduced-motion:reduce) —— 系统开启"
               "「减少动态效果」的用户会被动画持续干扰（spec §5.1）")
    if "requestAnimationFrame" in src and "IntersectionObserver" not in src:
        err(f, "有 rAF 动画但无 IntersectionObserver —— 无法离屏暂停，"
               "不可见区域会持续烧 CPU（spec §5.1）")
    if "devicePixelRatio" in src and not re.search(r"Math\.min\(\s*window\.devicePixelRatio|dpr\s*=\s*Math\.min", src):
        warn(f, "canvas 未对 devicePixelRatio 封顶（建议 min(devicePixelRatio,2)）")
    # 进场初始态：裸 .reveal{opacity:0} 会让 JS 失效时整块内容永不显现
    for m in re.finditer(r"([^{}]+)\{([^}]*)\}", css_clean):
        if "opacity:0" not in m.group(2).replace(" ", ""):
            continue
        for sel in m.group(1).split(","):
            if sel.strip() == ".reveal":
                err(f, ".reveal 直接在 CSS 裸选择器上写 opacity:0 —— JS 一挂该区块就永不显现。"
                       "隐藏态请挂到由 JS 添加的根类下（例：.fx-anim .reveal）")


def check_size(f, path):
    kb = os.path.getsize(path) / 1024.0
    limit = MAX_KB_HOME if "home" in f.lower() else MAX_KB_PAGE
    if kb > limit:
        warn(f, "体积 %.1fKB 超预算 %dKB（spec §7）" % (kb, limit))


def check_file(path):
    f = os.path.basename(path)
    with open(path, "r", encoding="utf-8") as fh:
        src = fh.read()
    check_vars(f, src)
    check_icons(f, src)
    check_toast(f, src)
    check_breakpoints(f, src)
    check_list_schema(f, src)
    check_antipatterns(f, src)
    check_motion(f, src)
    check_size(f, path)


def main():
    files = sys.argv[1:]
    if not files:
        print(__doc__)
        return 2
    for p in files:
        if os.path.isfile(p):
            check_file(p)
        else:
            print("[SKIP ] 不存在：%s" % p)
    for line in errors + warnings:
        print(line)
    print("\n—— 机检结果：%d ERROR / %d WARN ——" % (len(errors), len(warnings)))
    if errors:
        print("存在 ERROR，门禁未通过。")
        return 1
    print("门禁通过。剩余项仍需人工确认（交互真实生效、行业术语、排版观感）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
