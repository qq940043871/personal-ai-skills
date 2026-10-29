# -*- coding: utf-8 -*-
"""采集层。

两条入口：
  - load_mock()  : 读内置示例 feed，用于离线演示 / 单测
  - load_rss()   : 读真实 RSS/Atom 源（we-mp-rss、wechat2rss 等采集服务的产物）

设计原则：这一层只负责「拿到文章原文」。
微信端的反爬对抗（登录态、限频、验证码）全部交给上游采集服务，
本流水线不碰微信接口，因此不会给账号带来额外风险。
"""
from __future__ import annotations

import os
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import feedparser
import requests
from bs4 import BeautifulSoup

# mock feed 随 skill 打包在 assets/ 下；找不到时退回工作目录，方便用户自带示例
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_MOCK_CANDIDATES = [
    os.path.join(ROOT, "assets", "mock_feed.sample.xml"),
    os.path.join(os.environ.get("WJ_HOME") or os.getcwd(), "mock", "zzfabu.sample.xml"),
    os.path.join(os.environ.get("WJ_HOME") or os.getcwd(), "mock_feed.sample.xml"),
]


def _find_mock_feed() -> str:
    for p in _MOCK_CANDIDATES:
        if os.path.exists(p):
            return p
    return _MOCK_CANDIDATES[0]

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}


@dataclass
class Article:
    """一篇公众号文章。"""
    title: str
    link: str = ""
    published: str = ""
    summary: str = ""
    content: str = ""

    @property
    def plain(self) -> str:
        """标题 + 摘要 + 正文的纯文本，供过滤与抽取使用。"""
        return html_to_text("\n".join([self.title, self.summary, self.content]))


def html_to_text(html: str) -> str:
    """把公众号文章 HTML 压成纯文本（保留换行结构）。"""
    if not html:
        return ""
    # BeautifulSoup 对「看着像文件名/URL 的短纯文本」会发 MarkupResemblesLocatorWarning，
    # 而这里经常喂进来的正是 URL、标题这类短字符串。这类输入本来就没什么可解析的，
    # 直接返回原文，既避免警告又不做无谓解析。
    if "<" not in html and len(html) < 500:
        return re.sub(r"\s+", " ", html).strip()
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "svg"]):
        tag.decompose()
    # 块级元素补换行，避免所有文字糊成一坨
    for tag in soup.find_all(["p", "div", "br", "li", "tr", "h1", "h2", "h3", "section"]):
        tag.append("\n")
    text = soup.get_text("")
    text = text.replace("\u3000", " ").replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def _pick(entry: Any, *keys: str) -> str:
    for k in keys:
        v = entry.get(k)
        if v:
            return str(v)
    return ""


def _parse_entries(parsed: Any, limit: int) -> List[Article]:
    items: List[Article] = []
    for entry in (parsed.entries or [])[:limit]:
        content = ""
        # feedparser 把 <content:encoded> 放在 entry.content 列表里
        if entry.get("content"):
            content = entry["content"][0].get("value", "")
        if not content:
            content = _pick(entry, "summary", "description")
        items.append(Article(
            title=html_to_text(_pick(entry, "title")).strip(),
            link=_pick(entry, "link", "id"),
            published=_pick(entry, "published", "updated"),
            summary=_pick(entry, "summary", "description"),
            content=content,
        ))
    return items


def load_mock(limit: int = 60) -> List[Article]:
    feed = _find_mock_feed()
    if not os.path.exists(feed):
        raise FileNotFoundError(
            f"示例 feed 缺失: {feed}\n"
            "（离线演示需要 assets/mock_feed.sample.xml；也可把源换成 weread/rss 跑真实数据）")
    with open(feed, "rb") as fh:
        parsed = feedparser.parse(fh.read())
    return _parse_entries(parsed, limit)


def load_rss(url: str, limit: int = 60, timeout: int = 15) -> List[Article]:
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    parsed = feedparser.parse(resp.content)
    if parsed.bozo and not parsed.entries:
        raise RuntimeError(f"RSS 解析失败: {parsed.get('bozo_exception')}")
    items = _parse_entries(parsed, limit)
    if not items:
        raise RuntimeError("RSS 源返回 0 条文章，检查地址或采集服务是否正常")
    return items


def fetch_fulltext(article: Article, timeout: int = 15) -> Article:
    """正文兜底：RSS 只给了摘要时，去原文链接抓一次全文。

    注意：这条路径直连 mp.weixin.qq.com，可能触发验证码。
    所以仅在 summary 明显过短时才尝试，失败就静默保留摘要。
    """
    if not article.link or "mp.weixin.qq.com" not in article.link:
        return article
    if len(html_to_text(article.content or article.summary)) > 400:
        return article  # 已经有像样的正文了，别去招惹微信
    try:
        resp = requests.get(article.link, headers=HEADERS, timeout=timeout)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "lxml")
            node = soup.find(id="js_content") or soup.find("div", class_="rich_media_content")
            if node:
                article.content = str(node)
    except Exception:
        pass  # 拿不到就退回摘要，不中断流水线
    return article


def load_weread(cfg: Dict[str, Any], limit: int) -> List[Article]:
    """免 Docker 采集源：直连微信读书接口。

    配置里的 rss_url 写成 weread://MP_WXS_xxxx 也可以，等价于 type: weread + book_id。
    """
    from .weread import WeReadClient, cookie_auto, parse_book_id

    wcfg = cfg["source"].get("weread") or {}
    raw_book = (wcfg.get("book_id") or "").strip()
    # 允许直接粘微信读书阅读页链接或编码串，自动还原成 bookId
    book_id = parse_book_id(raw_book) or raw_book
    if not book_id:
        raise RuntimeError(
            "未配置 source.weread.book_id。\n"
            "最简单的取法：浏览器打开目标公众号的微信读书阅读页，把整条链接粘进来即可，\n"
            "例如 book_id: \"https://weread.qq.com/web/mp/reader/647423d2...\"\n"
            "也可以先验证：python -m src.weread parse \"<链接>\"\n"
            "或跑 python -m src.weread subs 看已订阅列表。"
        )
    if book_id != raw_book and raw_book:
        print(f"[ok] 已从链接还原 bookId = {book_id}")
    timeout = int(cfg["source"].get("timeout", 15))
    cookie = (wcfg.get("cookie") or "").strip()
    if not cookie and (wcfg.get("cookie_from", "browser") == "browser"):
        preferred = (wcfg.get("browser") or "chrome").lower()
        order = [preferred] + [b for b in ("chrome", "edge", "brave", "firefox")
                               if b != preferred]
        cookie, used = cookie_auto(order)
        print(f"[ok] cookie 来源：{used}")
    return WeReadClient(cookie, timeout=timeout).fetch(book_id, limit=limit)


def fetch_articles(cfg: Dict[str, Any]) -> List[Article]:
    """统一入口：按配置拉取文章列表，并并发补齐正文。"""
    src = cfg["source"]
    limit = int(src.get("max_items", 60))
    timeout = int(src.get("timeout", 15))
    url = (src.get("rss_url") or "mock").strip()

    # 源类型判定：显式 type 优先，否则从 rss_url 前缀推断，最后按 mock/rss 兜底
    stype = (src.get("type") or "").strip().lower()
    if not stype:
        if url.startswith("weread://"):
            stype, book = "weread", url[len("weread://"):].strip("/")
            src.setdefault("weread", {})
            if book and not src["weread"].get("book_id"):
                src["weread"]["book_id"] = book
        elif url in ("mock", "", "demo"):
            stype = "mock"
        else:
            stype = "rss"

    if stype == "mock":
        return load_mock(limit)
    if stype == "weread":
        return load_weread(cfg, limit)

    articles = load_rss(url, limit=limit, timeout=timeout)

    workers = max(1, int(src.get("fetch_workers", 4)))
    if workers > 1:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            articles = list(pool.map(lambda a: fetch_fulltext(a, timeout), articles))
    else:
        articles = [fetch_fulltext(a, timeout) for a in articles]
    return articles
