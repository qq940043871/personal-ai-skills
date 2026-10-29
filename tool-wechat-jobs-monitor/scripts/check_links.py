# -*- coding: utf-8 -*-
r"""校验邮件正文里的 mp.weixin.qq.com 链接是否真的打得开。

**为什么必须单独校验**：微信短链 token 是 Base64 URL-safe 编码（字符集 A-Za-z0-9-_），
而微信读书在 reviewId 里把 `_` 转义成了 `~`。忘了还原 `~`→`_`，就会生成
`/s/<含~的token>`，微信返回一个约 31KB 的「参数错误」页 ——
**HTTP 状态码仍是 200**，只看状态码完全发现不了，属于「静默失败」。

所以判断依据是「页面体量 + 特征串」，不是状态码。

用法：
    python scripts/check_links.py out/mail_body_2026-10-07.html   # 指定文件
    python scripts/check_links.py out/                            # 扫目录下最新的 mail_body_*
退出码：0 全部 OK；1 有 BAD。
"""
from __future__ import annotations

import glob
import os
import re
import sys

import requests

HEADERS = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120 Safari/537.36")}


def is_real_article(text: str) -> bool:
    """失败页特征：正文含「参数错误」，且没有文章结构。"""
    if "参数错误" in text:
        return False
    return "js_content" in text or "msg_title" in text


def find_target(arg: str) -> str:
    if arg and os.path.isfile(arg):
        return arg
    base = arg or os.path.join(os.getcwd(), "out")
    cands = sorted(glob.glob(os.path.join(base, "mail_body_*.html")))
    if not cands:
        cands = sorted(glob.glob(os.path.join(base, "**", "mail_body_*.html"),
                                recursive=True))
    return cands[-1] if cands else ""


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    target = find_target(argv[0] if argv else "")
    if not target:
        print("没找到 mail_body_*.html，先跑一次流水线（run_pipeline.py）。")
        return 1

    html = open(target, encoding="utf-8").read()
    urls = list(dict.fromkeys(
        re.findall(r'href="(https?://mp\.weixin\.qq\.com/s/[^"]+)"', html)))
    if not urls:
        print(f"{os.path.basename(target)}：没找到 mp.weixin.qq.com/s/ 链接。")
        # 正文为空的情况不算失败
        return 0

    print(f"校验 {os.path.basename(target)} 里的 {len(urls)} 个链接\n")
    bad = 0
    for u in urls:
        r = None
        try:
            r = requests.get(u, headers=HEADERS, timeout=25)
            real = is_real_article(r.text)
            size = f"{len(r.text):>9}"
        except Exception as exc:
            real, size = False, "        -"
            print(f"  请求异常：{type(exc).__name__}: {exc}")
        if not real:
            bad += 1
        print(f"{'OK ' if real else 'BAD'} {size}  {u}")

    if bad:
        print(f"\n❌ {bad}/{len(urls)} 个链接打不开。")
        print("   若链接里含 `~`，说明 reviewId 的转义没还原（应为 `_`）——"
              "检查 wjobs/weread.py 的 review_to_url()。")
        return 1
    print(f"\n✅ {len(urls)}/{len(urls)} 个链接全部可正常打开。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
