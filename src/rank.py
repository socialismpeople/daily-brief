"""打分排序：关键词 + 信源权重 + 时间衰减。只依赖标准库。"""
from __future__ import annotations

import math
from datetime import datetime, timezone

from .feed import Item


def _hours_ago(dt: datetime | None, now: datetime) -> float:
    if dt is None:
        return 12.0  # 没有时间信息的，给个中间值
    delta = (now - dt).total_seconds() / 3600.0
    return max(0.0, delta)


def score_items(items: list[Item], config: dict, now: datetime | None = None) -> list[Item]:
    now = now or datetime.now(timezone.utc)
    kw = config.get("keywords", {})
    must = [k.lower() for k in kw.get("must", [])]
    boost = [k.lower() for k in kw.get("boost", [])]
    mute = [k.lower() for k in kw.get("mute", [])]
    window = float(config.get("output", {}).get("window_hours", 36))
    decay = 0.08

    out: list[Item] = []
    for it in items:
        haystack = f"{it.title} {it.summary}".lower()

        if any(m in haystack for m in mute):
            continue
        if must and not any(m in haystack for m in must):
            continue

        hours = _hours_ago(it.published, now)
        if hours > window:
            continue

        freshness = math.exp(-decay * hours)
        keyword_bonus = sum(0.18 for b in boost if b in haystack)
        title_hit = sum(0.10 for b in boost if b in it.title.lower())

        it.score = round(
            it.weight * 1.0
            + freshness * 1.2
            + keyword_bonus
            + title_hit,
            4,
        )
        it.extra["hours_ago"] = round(hours, 1)
        out.append(it)

    return sorted(out, key=lambda x: x.score, reverse=True)


def pick_top(items: list[Item], top_n: int, max_per_source: int = 3) -> list[Item]:
    """按分数取 Top N，同时限制单一来源占比，避免被一个站刷屏。"""
    chosen: list[Item] = []
    per_source: dict[str, int] = {}
    for it in items:
        if per_source.get(it.source, 0) >= max_per_source:
            continue
        chosen.append(it)
        per_source[it.source] = per_source.get(it.source, 0) + 1
        if len(chosen) >= top_n:
            break
    return chosen
