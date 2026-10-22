"""RSS / Atom 抓取与解析。只依赖标准库。"""
from __future__ import annotations

import gzip
import io
import re
import socket
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "dc": "http://purl.org/dc/elements/1.1/",
    "content": "http://purl.org/rss/1.0/modules/content/",
}


@dataclass
class Item:
    title: str
    link: str
    summary: str = ""
    published: datetime | None = None
    source: str = ""
    weight: float = 1.0
    lang: str = "zh"
    score: float = 0.0
    extra: dict = field(default_factory=dict)


def _strip_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return _clean_boilerplate(text)


# 各站 RSS 里常见的固定噪音：HN 的 "Article URL: ... Comments URL: ... Points: N"
_NOISE_PATTERNS = [
    re.compile(r"Article URL:\s*\S+", re.I),
    re.compile(r"Comments URL:\s*\S+", re.I),
    re.compile(r"Points:\s*\d+", re.I),
    re.compile(r"#\s*Comments:\s*\d+", re.I),
    re.compile(r"^\s*点击查看原文\s*>?\s*$"),
    re.compile(r"^\s*(阅读全文|查看全文|Read more|Continue reading)\s*[.。>»]*\s*$", re.I),
    re.compile(r"The post .{0,120}? appeared first on .{0,80}?\.?", re.I),
    re.compile(r"^\s*(分享到|责任编辑|本文来自|原文链接)[:：].*$"),
]


def _clean_boilerplate(text: str) -> str:
    for pat in _NOISE_PATTERNS:
        text = pat.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    # 去掉只剩标点/空白的情况
    if not re.search(r"[\w\u4e00-\u9fff]", text):
        return ""
    return text


def _parse_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    raw = raw.strip()
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(raw.replace("Z", "+0000") if fmt.endswith("%z") else raw, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            continue
    return None


def _fetch(url: str, timeout: int = 20, retries: int = 2) -> bytes | None:
    last = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": UA,
                    "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
                    "Accept-Encoding": "gzip",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
                if resp.headers.get("Content-Encoding") == "gzip":
                    data = gzip.GzipFile(fileobj=io.BytesIO(data)).read()
                return data
        except (urllib.error.URLError, socket.timeout, OSError, ValueError) as exc:
            last = exc
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
    print(f"  [warn] 抓取失败 {url}: {last}")
    return None


def _text(node, path: str) -> str:
    found = node.find(path, NS) if ":" in path else node.find(path)
    if found is None:
        return ""
    return (found.text or "").strip()


def parse_feed(raw: bytes) -> list[Item]:
    """解析 RSS 2.0 / RSS 1.0(RDF) / Atom。"""
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        # 有些源带 BOM 或前导垃圾字符，截到第一个 '<' 再试
        idx = raw.find(b"<")
        if idx <= 0:
            return []
        try:
            root = ET.fromstring(raw[idx:])
        except ET.ParseError:
            return []

    items: list[Item] = []
    tag = root.tag.split("}")[-1].lower()

    if tag == "feed":  # Atom
        for entry in root.findall("atom:entry", NS):
            title = _text(entry, "atom:title")
            link = ""
            for ln in entry.findall("atom:link", NS):
                rel = ln.get("rel", "alternate")
                if rel == "alternate" and ln.get("href"):
                    link = ln.get("href", "")
                    break
            if not link:
                link = _text(entry, "atom:link")
            summary = _text(entry, "atom:summary") or _text(entry, "atom:content")
            published = _parse_date(
                _text(entry, "atom:published") or _text(entry, "atom:updated")
            )
            if title and link:
                items.append(Item(title=_strip_html(title), link=link.strip(),
                                  summary=_strip_html(summary)[:600], published=published))
        return items

    # RSS 2.0 / RDF
    nodes = root.findall(".//item")
    for node in nodes:
        title = _text(node, "title")
        link = _text(node, "link")
        if not link:
            link = _text(node, "guid")
        summary = (
            _text(node, "description")
            or _text(node, "content:encoded")
            or _text(node, "dc:description")
        )
        published = _parse_date(
            _text(node, "pubDate") or _text(node, "dc:date") or _text(node, "published")
        )
        if title and link:
            items.append(Item(title=_strip_html(title), link=link.strip(),
                              summary=_strip_html(summary)[:600], published=published))
    return items


def fetch_source(source: dict, max_items: int = 30) -> list[Item]:
    raw = _fetch(source["url"])
    if not raw:
        return []
    # 有的站把 RSS 地址重定向到 HTML 页面（反爬），这种直接判定为失败
    head = raw[:200].lstrip().lower()
    if head.startswith(b"<!doctype") or head.startswith(b"<html"):
        print(f"  [warn] {source.get('name', '?')} 返回的是 HTML 而非 RSS，已跳过")
        return []
    items = parse_feed(raw)
    out: list[Item] = []
    for it in items[:max_items]:
        it.source = source.get("name", "")
        it.weight = float(source.get("weight", 1.0))
        it.lang = source.get("lang", "zh")
        out.append(it)
    return out
