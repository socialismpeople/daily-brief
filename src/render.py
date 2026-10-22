"""渲染：Markdown 归档 + 静态站点。只依赖标准库。"""
from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path

from .feed import Item

CSS = """
:root{
  --bg:#f7f7f5; --fg:#17171a; --muted:#77777f; --faint:#a0a0a8;
  --line:#e6e6e2; --card:#ffffff; --accent:#c8553d; --accent-soft:#f6ece8;
  --shadow:0 1px 2px rgba(0,0,0,.04),0 8px 24px -12px rgba(0,0,0,.10);
  --radius:16px;
}
@media(prefers-color-scheme:dark){
  :root{
    --bg:#0f0f11; --fg:#ececee; --muted:#8e8e96; --faint:#63636b;
    --line:#242428; --card:#17171a; --accent:#e0785f; --accent-soft:#2a1e1a;
    --shadow:0 1px 2px rgba(0,0,0,.4),0 8px 24px -12px rgba(0,0,0,.6);
  }
}
*{box-sizing:border-box;margin:0;padding:0}
html{-webkit-text-size-adjust:100%}
body{
  background:var(--bg);color:var(--fg);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Noto Sans SC","Microsoft YaHei",sans-serif;
  line-height:1.7;-webkit-font-smoothing:antialiased;
  font-feature-settings:"kern" 1;
}
.wrap{max-width:680px;margin:0 auto;padding:0 24px}

/* ---------- 顶部 ---------- */
header.site{padding:64px 0 32px}
.brand{display:flex;align-items:center;gap:10px;margin-bottom:14px}
.dot{width:9px;height:9px;border-radius:50%;background:var(--accent);
  box-shadow:0 0 0 4px var(--accent-soft);flex:none}
header.site h1{font-size:27px;font-weight:750;letter-spacing:-.7px;line-height:1.25}
header.site .sub{margin-top:9px;color:var(--muted);font-size:14.5px;letter-spacing:.1px}

/* ---------- 日期条 ---------- */
.dateline{
  display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;
  padding:18px 0 20px;border-top:1px solid var(--line);
  font-size:13px;color:var(--muted);
}
.dateline .d{font-size:14px;font-weight:600;color:var(--fg);letter-spacing:.3px;
  font-variant-numeric:tabular-nums}
.dateline .n{margin-left:auto;font-variant-numeric:tabular-nums}

/* ---------- 条目 ---------- */
.entry{
  background:var(--card);border:1px solid var(--line);border-radius:var(--radius);
  padding:22px 24px;margin-bottom:14px;box-shadow:var(--shadow);
  transition:transform .18s ease,border-color .18s ease,box-shadow .18s ease;
}
.entry:hover{transform:translateY(-2px);border-color:var(--accent);
  box-shadow:0 2px 4px rgba(0,0,0,.05),0 14px 32px -14px rgba(0,0,0,.18)}
.entry .idx{
  display:inline-flex;align-items:center;justify-content:center;
  min-width:22px;height:22px;padding:0 6px;border-radius:7px;
  background:var(--accent-soft);color:var(--accent);
  font-size:12px;font-weight:700;font-variant-numeric:tabular-nums;
  margin-bottom:11px;
}
.entry h2{font-size:17.5px;font-weight:650;line-height:1.5;letter-spacing:-.15px}
.entry h2 a{color:var(--fg);text-decoration:none;transition:color .15s}
.entry h2 a:hover{color:var(--accent)}
.brief{margin-top:9px;font-size:14.5px;color:var(--muted);line-height:1.72}
.why{
  margin-top:11px;padding:9px 13px;border-radius:10px;
  background:var(--accent-soft);border-left:2px solid var(--accent);
  font-size:13.5px;color:var(--fg);opacity:.92;line-height:1.6;
}
.meta{
  margin-top:14px;display:flex;align-items:center;gap:10px;flex-wrap:wrap;
  font-size:12.5px;color:var(--faint);
}
.tag{
  padding:2px 9px;border-radius:999px;background:var(--bg);
  border:1px solid var(--line);color:var(--muted);font-size:11.5px;font-weight:500;
}
.meta .go{margin-left:auto;color:var(--accent);text-decoration:none;font-weight:600;
  font-size:12.5px;transition:gap .15s}
.meta .go:hover{text-decoration:underline}

/* ---------- 空状态 ---------- */
.empty{
  text-align:center;padding:72px 24px;color:var(--muted);
  background:var(--card);border:1px dashed var(--line);border-radius:var(--radius);
}

/* ---------- 页脚 ---------- */
footer{margin-top:56px;padding:28px 0 64px;border-top:1px solid var(--line);
  font-size:12.5px;color:var(--faint);display:flex;justify-content:space-between;
  align-items:center;gap:12px;flex-wrap:wrap}
footer a{color:var(--muted);text-decoration:none}
footer a:hover{color:var(--accent)}

/* ---------- 归档页 ---------- */
.back{
  display:inline-flex;align-items:center;gap:6px;margin:0 0 22px;
  font-size:13.5px;color:var(--muted);text-decoration:none;
  padding:6px 14px 6px 10px;border:1px solid var(--line);border-radius:999px;
  background:var(--card);transition:all .15s;
}
.back:hover{color:var(--accent);border-color:var(--accent)}
.arch{list-style:none;margin-top:8px}
.arch li{margin-bottom:2px}
.arch a{
  display:flex;align-items:center;justify-content:space-between;
  padding:13px 4px;border-bottom:1px solid var(--line);
  color:var(--fg);text-decoration:none;font-size:14.5px;
  font-variant-numeric:tabular-nums;transition:padding .15s,color .15s;
}
.arch a:hover{color:var(--accent);padding-left:8px}
.arch .arrow{color:var(--faint);font-size:13px}

@media(max-width:560px){
  .wrap{padding:0 18px}
  header.site{padding:44px 0 24px}
  header.site h1{font-size:23px}
  .entry{padding:18px 18px;border-radius:14px}
  .entry h2{font-size:16.5px}
  footer{flex-direction:column;align-items:flex-start;gap:6px}
}
@media(prefers-reduced-motion:reduce){
  *{transition:none!important}
  .entry:hover{transform:none}
}
"""


def _esc(text: str) -> str:
    return html.escape(text or "", quote=True)


def _nice_date(date_str: str) -> str:
    """2026-10-22 -> 10月22日 星期四"""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return date_str
    week = "一二三四五六日"[dt.weekday()]
    return f"{dt.month}月{dt.day}日 星期{week}"


def build_markdown(items: list[Item], date_str: str, site: dict) -> str:
    lines = [f"# {date_str} 每日简报", ""]
    if not items:
        lines += ["今天没有值得推送的内容。", ""]
        return "\n".join(lines)
    for idx, it in enumerate(items, 1):
        brief = it.extra.get("brief") or ""
        why = it.extra.get("why") or ""
        lines.append(f"## {idx}. {it.title}")
        lines.append("")
        if brief:
            lines.append(brief)
            lines.append("")
        if why:
            lines.append(f"> {why}")
            lines.append("")
        src = it.source
        hours = it.extra.get("hours_ago")
        stamp = f"{hours}h 前" if hours is not None else ""
        lines.append(f"[原文]({it.link}) · {src}" + (f" · {stamp}" if stamp else ""))
        lines.append("")
    return "\n".join(lines)


def build_push_markdown(items: list[Item], date_str: str, site_url: str = "") -> str:
    lines = [f"**{date_str} 每日简报**", ""]
    if not items:
        lines.append("今天没有值得推送的内容。")
        return "\n".join(lines)
    for idx, it in enumerate(items, 1):
        brief = it.extra.get("brief") or it.title
        lines.append(f"**{idx}. {it.title}**")
        lines.append(brief)
        lines.append(f"[阅读原文]({it.link})")
        lines.append("")
    if site_url:
        lines.append(f"[查看完整简报]({site_url})")
    return "\n".join(lines)


def _render_page(title: str, body: str, site: dict, extra_head: str = "") -> str:
    return f"""<!doctype html>
<html lang="{_esc(site.get('lang', 'zh-CN'))}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{_esc(title)}</title>
<meta name="description" content="{_esc(site.get('subtitle', ''))}">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#f7f7f5" media="(prefers-color-scheme:light)">
<meta name="theme-color" content="#0f0f11" media="(prefers-color-scheme:dark)">
{extra_head}
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
{body}
</div>
</body>
</html>
"""


def _entries_html(items: list[Item]) -> str:
    if not items:
        return '<div class="empty">今天没有值得推送的内容。<br>明天见。</div>'
    parts = []
    for idx, it in enumerate(items, 1):
        brief = _esc(it.extra.get("brief") or "")
        why = _esc(it.extra.get("why") or "")
        hours = it.extra.get("hours_ago")
        stamp = f"<span>{hours}h 前</span>" if hours is not None else ""
        brief_html = f'<p class="brief">{brief}</p>' if brief else ""
        why_html = f'<div class="why">{why}</div>' if why else ""
        parts.append(f"""<article class="entry">
<div class="idx">{idx:02d}</div>
<h2><a href="{_esc(it.link)}" target="_blank" rel="noopener">{_esc(it.title)}</a></h2>
{brief_html}
{why_html}
<div class="meta">
<span class="tag">{_esc(it.source)}</span>
{stamp}
<a class="go" href="{_esc(it.link)}" target="_blank" rel="noopener">原文 →</a>
</div>
</article>""")
    return "\n".join(parts)


def write_site(items: list[Item], date_str: str, config: dict, out_dir: Path,
               archive: list[str] | None = None) -> Path:
    site = config.get("site", {})
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "archive").mkdir(exist_ok=True)

    body = f"""<header class="site">
<div class="brand"><span class="dot"></span><span style="font-size:12px;letter-spacing:1.5px;
text-transform:uppercase;color:var(--muted);font-weight:600">Daily Brief</span></div>
<h1>{_esc(site.get('title', '每日简报'))}</h1>
<p class="sub">{_esc(site.get('subtitle', ''))}</p>
</header>
<div class="dateline">
<span class="d">{_nice_date(date_str)}</span>
<span class="n">共 {len(items)} 条</span>
</div>
{_entries_html(items)}
<footer>
<span>{_esc(site.get('title', ''))}</span>
<span><a href="archive/index.html">历史归档</a></span>
</footer>"""

    page = _render_page(f"{_nice_date(date_str)} · {site.get('title', '')}", body, site)
    index_path = out_dir / "index.html"
    index_path.write_text(page, encoding="utf-8")

    archive_body = f"""<header class="site">
<div class="brand"><span class="dot"></span><span style="font-size:12px;letter-spacing:1.5px;
text-transform:uppercase;color:var(--muted);font-weight:600">Archive</span></div>
<h1>{_esc(site.get('title', '每日简报'))}</h1>
<p class="sub">{_nice_date(date_str)} 的简报</p>
</header>
<a class="back" href="../index.html">← 返回最新</a>
{_entries_html(items)}"""
    archive_page = _render_page(
        f"{_nice_date(date_str)} · 归档 · {site.get('title', '')}", archive_body, site,
        extra_head='<meta name="robots" content="noindex">',
    )
    (out_dir / "archive" / f"{date_str}.html").write_text(archive_page, encoding="utf-8")
    return index_path


def write_archive_index(out_dir: Path, site: dict) -> None:
    """生成 /archive/index.html：所有往期列表。"""
    archive_dir = out_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    dates = sorted((p.stem for p in archive_dir.glob("*.html") if p.stem != "index"), reverse=True)

    if dates:
        rows = "\n".join(
            f'<li><a href="{d}.html"><span>{_nice_date(d)}</span>'
            f'<span class="arrow">→</span></a></li>'
            for d in dates
        )
        listing = f'<ul class="arch">{rows}</ul>'
    else:
        listing = '<div class="empty">还没有归档。</div>'

    body = f"""<header class="site">
<div class="brand"><span class="dot"></span><span style="font-size:12px;letter-spacing:1.5px;
text-transform:uppercase;color:var(--muted);font-weight:600">Archive</span></div>
<h1>历史归档</h1>
<p class="sub">共 {len(dates)} 期</p>
</header>
<a class="back" href="../index.html">← 返回最新</a>
{listing}"""
    page = _render_page(f"历史归档 · {site.get('title', '')}", body, site,
                        extra_head='<meta name="robots" content="noindex">')
    (archive_dir / "index.html").write_text(page, encoding="utf-8")


def write_index_json(archive_dir: Path, out_dir: Path) -> None:
    dates = sorted((p.stem for p in archive_dir.glob("*.html") if p.stem != "index"), reverse=True)
    (out_dir / "dates.json").write_text(
        json.dumps(dates, ensure_ascii=False, indent=2), encoding="utf-8"
    )
