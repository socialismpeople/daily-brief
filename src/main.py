"""主流程：抓取 → 去重 → 排序 → 摘要 → 渲染静态站点。"""
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
MAX_SEEN = 300


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


def collect(config: dict) -> list[feed.Item]:
    all_items: list[feed.Item] = []
    for src in config.get("sources", []):
        name = src.get("name", src.get("url", "?"))
        try:
            items = feed.fetch_source(src)
            print(f"  [ok] {name}: {len(items)} 条")
            all_items.extend(items)
        except Exception as exc:  # noqa: BLE001
            print(f"  [warn] {name} 抓取异常: {exc}")
    return all_items


def run(dry_run: bool = False, top_n: int | None = None) -> int:
    load_env_file()
    config = load_config()
    now = datetime.now(TZ)
    date_str = now.strftime("%Y-%m-%d")
    print(f"=== {date_str} 每日简报 ===")

    out_cfg = config.get("output", {})
    limit = top_n or int(out_cfg.get("top_n", 6))
    max_per_source = int(out_cfg.get("max_per_source", 3))

    print("[1/5] 抓取信源")
    raw_items = collect(config)
    print(f"  合计 {len(raw_items)} 条")
    if not raw_items:
        print("[!] 没有抓到任何内容，退出")
        return 1

    print("[2/5] 去重")
    seen = load_seen()
    unique = dedupe.dedupe(raw_items, seen_hashes=seen)
    print(f"  去重后 {len(unique)} 条（过滤 {len(raw_items) - len(unique)} 条）")

    print("[3/5] 打分排序")
    scored = rank.score_items(unique, config, now=now)
    picked = rank.pick_top(scored, limit, max_per_source)
    print(f"  选出 {len(picked)} 条")
    for it in picked:
        it.link = dedupe.clean_link(it.link)

    print("[4/5] 生成摘要")
    summarize.summarize(picked)

    print("[5/5] 渲染")
    DIGEST_DIR.mkdir(exist_ok=True)
    md = render.build_markdown(picked, date_str, config.get("site", {}))
    (DIGEST_DIR / f"{date_str}.md").write_text(md, encoding="utf-8")

    docs_archive = DOCS_DIR / "archive"
    docs_archive.mkdir(parents=True, exist_ok=True)
    existing = sorted((p.stem for p in docs_archive.glob("*.html") if p.stem != "index"), reverse=True)
    render.write_site(picked, date_str, config, DOCS_DIR, archive=existing)
    render.write_archive_index(DOCS_DIR, config.get("site", {}))
    render.write_index_json(docs_archive, DOCS_DIR)
    print(f"  已写入 docs/index.html 与 docs/archive/{date_str}.html")

    if not dry_run:
        save_seen(seen, picked)

    print("=== 完成 ===")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="每日简报生成器")
    parser.add_argument("--dry-run", action="store_true", help="不更新去重缓存")
    parser.add_argument("--top", type=int, default=None, help="覆盖条数")
    args = parser.parse_args(argv)
    try:
        return run(dry_run=args.dry_run, top_n=args.top)
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
