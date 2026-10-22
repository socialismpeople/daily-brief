"""主流程：多板块抓取 → 去重 → 排序 → 摘要 → 渲染。"""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from datetime import datetime, timedelta, timezone

from . import dedupe, feed, rank, render, summarize
from .config import ROOT, load_config, load_env_file

TZ = timezone(timedelta(hours=8))  # Asia/Shanghai
DATA_DIR = ROOT / "data"
DOCS_DIR = ROOT / "docs"
DIGEST_DIR = ROOT / "digests"
SEEN_PATH = DATA_DIR / "seen.json"
MAX_SEEN = 800


def load_seen() -> set[str]:
    if not SEEN_PATH.exists():
        return set()
    try:
        data = json.loads(SEEN_PATH.read_text(encoding="utf-8"))
        return set(data.get("hashes", []))
    except (json.JSONDecodeError, OSError):
        return set()


def save_seen(hashes: set[str], new_items: list[feed.Item]) -> None:
    for it in new_items:
        uh = it.extra.get("url_hash")
        th = it.extra.get("title_hash")
        if uh:
            hashes.add(uh)
        if th:
            hashes.add(th)
    ordered = [h for h in hashes if h][-MAX_SEEN:]
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SEEN_PATH.write_text(
        json.dumps({"hashes": ordered}, ensure_ascii=False), encoding="utf-8"
    )


def collect(sources: list[dict]) -> list[feed.Item]:
    all_items: list[feed.Item] = []
    for src in sources:
        name = src.get("name", src.get("url", "?"))
        try:
            items = feed.fetch_source(src)
            print(f"    [ok] {name}: {len(items)} 条")
            all_items.extend(items)
        except Exception as exc:  # noqa: BLE001
            print(f"    [warn] {name} 抓取异常: {exc}")
    return all_items


def build_section(section: dict, config: dict, seen: set[str],
                  now: datetime, top_n: int | None = None) -> list[feed.Item]:
    """处理单个板块：抓取 → 去重 → 排序 → 摘要。"""
    sid = section.get("id", "?")
    name = section.get("name", sid)
    print(f"\n[{name}] 抓取 {len(section.get('sources', []))} 个源")
    raw = collect(section.get("sources", []))
    print(f"  合计 {len(raw)} 条")
    if not raw:
        return []

    unique = dedupe.dedupe(raw, seen_hashes=seen)
    print(f"  去重后 {len(unique)} 条")

    # 板块级关键词覆盖
    sec_config = dict(config)
    sec_config["keywords"] = section.get("keywords", config.get("keywords", {}))
    scored = rank.score_items(unique, sec_config, now=now)

    limit = top_n or int(section.get("top_n", config.get("output", {}).get("top_n", 6)))
    max_per_source = int(config.get("output", {}).get("max_per_source", 2))
    picked = rank.pick_top(scored, limit, max_per_source)
    print(f"  选出 {len(picked)} 条")

    for it in picked:
        it.link = dedupe.clean_link(it.link)
        it.extra["section"] = sid

    summarize.summarize(picked)
    return picked


def run(dry_run: bool = False, top_n: int | None = None) -> int:
    load_env_file()
    config = load_config()
    now = datetime.now(TZ)
    date_str = now.strftime("%Y-%m-%d")
    print(f"=== {date_str} 每日简报（多板块）===")

    sections = config.get("sections", [])
    if not sections:
        print("[!] config.json 里没有 sections")
        return 1

    seen = load_seen()
    results: dict[str, list[feed.Item]] = {}
    for section in sections:
        try:
            results[section.get("id", "?")] = build_section(section, config, seen, now, top_n)
        except Exception:  # noqa: BLE001
            traceback.print_exc()
            results[section.get("id", "?")] = []

    total = sum(len(v) for v in results.values())
    print(f"\n=== 共生成 {total} 条（{len(sections)} 个板块）===")

    print("\n[渲染]")
    DIGEST_DIR.mkdir(exist_ok=True)

    # 全量 Markdown 归档
    md_parts = [f"# {date_str} 每日简报\n"]
    for section in sections:
        sid = section.get("id", "?")
        name = section.get("name", sid)
        md_parts.append(f"\n## {section.get('icon', '')} {name}\n")
        md_parts.append(render.build_markdown(results.get(sid, []), date_str,
                                              config.get("site", {}), heading_offset=2))
    (DIGEST_DIR / f"{date_str}.md").write_text("\n".join(md_parts), encoding="utf-8")

    render.write_all(results, sections, date_str, config, DOCS_DIR)
    print("  已写入 docs/index.html 与各板块页")

    if not dry_run:
        all_picked = [it for v in results.values() for it in v]
        save_seen(seen, all_picked)

    print("\n=== 完成 ===")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="多板块每日简报")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--top", type=int, default=None, help="覆盖每板块条数")
    args = parser.parse_args(argv)
    try:
        return run(dry_run=args.dry_run, top_n=args.top)
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
