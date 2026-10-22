"""去重：URL 归一化 + 标题指纹 + 相似标题聚类。只依赖标准库。"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from .feed import Item

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "spm", "from", "ref", "ref_src", "share", "share_token", "fbclid",
    "gclid", "yclid", "mc_cid", "mc_eid", "cmpid", "ncid", "sr_share",
}


def normalize_url(url: str) -> str:
    """去掉追踪参数、锚点、末尾斜杠，统一大小写主机名。"""
    try:
        p = urlparse(url.strip())
    except ValueError:
        return url.strip()
    query = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
             if k.lower() not in TRACKING_PARAMS]
    path = p.path.rstrip("/") or "/"
    return urlunparse((
        p.scheme.lower() or "https",
        p.netloc.lower(),
        path,
        "",
        urlencode(query),
        "",
    ))


def url_hash(url: str) -> str:
    return hashlib.sha1(normalize_url(url).encode("utf-8")).hexdigest()[:16]


def clean_link(url: str) -> str:
    """给人看的链接：去掉追踪参数，但保留路径与必要 query。"""
    return normalize_url(url)


_PUNCT = re.compile(r"[\s\-–—_·:：,，。.、!！?？'\"“”‘’()（）\[\]【】|/\\~`]+")


def title_key(title: str) -> str:
    """标题指纹：全角转半角、去标点、去空白、小写。"""
    text = unicodedata.normalize("NFKC", title or "").lower()
    text = _PUNCT.sub("", text)
    return text


def title_hash(title: str) -> str:
    return hashlib.sha1(title_key(title).encode("utf-8")).hexdigest()[:16]


def _shingles(key: str, n: int = 3) -> set[str]:
    if len(key) <= n:
        return {key} if key else set()
    return {key[i:i + n] for i in range(len(key) - n + 1)}


def jaccard(a: str, b: str) -> float:
    sa, sb = _shingles(title_key(a)), _shingles(title_key(b))
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def dedupe(items: list[Item], seen_hashes: set[str] | None = None,
           threshold: float = 0.72) -> list[Item]:
    """三层去重：URL → 标题指纹 → 相似度聚类（同一事件多家转载只留一条）。"""
    seen_hashes = seen_hashes or set()
    kept: list[Item] = []
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()

    # 先按权重降序，保证聚类时留下的是高权重源
    for item in sorted(items, key=lambda x: x.weight, reverse=True):
        uh, th = url_hash(item.link), title_hash(item.title)
        if uh in seen_urls or th in seen_titles:
            continue
        if uh in seen_hashes or th in seen_hashes:
            continue
        # 与已保留条目高度相似 → 视为同一事件
        if any(jaccard(item.title, k.title) >= threshold for k in kept):
            continue
        seen_urls.add(uh)
        seen_titles.add(th)
        item.extra["url_hash"] = uh
        item.extra["title_hash"] = th
        kept.append(item)

    return kept
