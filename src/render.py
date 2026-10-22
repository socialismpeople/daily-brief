"""渲染：Markdown 归档 + 静态站点。

排版底座为 Marx v4.0.0（MIT，https://github.com/mblode/marx），
在其上补充深色模式、条目分隔与页脚。只依赖标准库。
"""
from __future__ import annotations

import html
import json
import shutil
from datetime import datetime
from pathlib import Path

from .feed import Item

ROOT = Path(__file__).resolve().parent.parent
VENDOR_CSS = ROOT / "assets" / "marx.css"

# Marx 之上的一层：深色模式 + 简报专用排版
THEME_CSS = """
:root{
  --ink:#1a1a1a;
  --ink-soft:#5c5c5c;
  --ink-faint:#9a9a9a;
  --paper:#fffefb;
  --rule:rgba(0,0,0,.10);
  --brand:#b3402e;
}
@media(prefers-color-scheme:dark){
  :root{
    --ink:#e8e6e1;
    --ink-soft:#a8a5a0;
    --ink-faint:#6e6b66;
    --paper:#14130f;
    --rule:rgba(255,255,255,.12);
    --brand:#e0775c;
  }
}
html{ background:var(--paper); }
body{
  background:var(--paper); color:var(--ink);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC",
    "Hiragino Sans GB","Noto Sans SC","Microsoft YaHei",sans-serif;
  -webkit-font-smoothing:antialiased;
  line-height:1.78;
}
.wrap{ max-width:660px; margin:0 auto; padding:64px 26px 88px; }

/* 顶部 */
header.site{ margin-bottom:38px; }
header.site .kicker{
  font-size:10.5px; letter-spacing:2.2px; text-transform:uppercase;
  font-weight:650; color:var(--ink-faint); margin:0 0 14px;
}
header.site h1{
  font-size:29px; line-height:1.22; letter-spacing:-.7px;
  font-weight:750; margin:0 0 10px; color:var(--ink);
}
header.site .sub{
  font-size:14px; color:var(--ink-soft); margin:0; line-height:1.6;
}

/* 日期条 */
.dateline{
  display:flex; justify-content:space-between; align-items:baseline;
  padding:16px 0 18px; margin:0 0 8px;
  border-top:1px solid var(--rule); border-bottom:1px solid var(--rule);
  font-size:12.5px; color:var(--ink-faint);
  font-variant-numeric:tabular-nums; letter-spacing:.3px;
}
.dateline strong{
  font-size:13px; font-weight:650; color:var(--ink-soft);
}

/* 条目 */
article.entry{ padding:28px 0 26px; border-bottom:1px solid var(--rule); }
article.entry:last-of-type{ border-bottom:none; }
article.entry .num{ display:none; }
article.entry h2{
  margin:0 0 10px; font-size:18px; line-height:1.48;
  letter-spacing:-.2px; font-weight:680;
}
article.entry h2 a{
  color:var(--ink); text-decoration:none;
  background-image:linear-gradient(var(--rule),var(--rule));
  background-size:0% 1px; background-position:0 100%;
  background-repeat:no-repeat;
  transition:background-size .25s ease,color .2s ease;
}
article.entry h2 a:hover{
  color:var(--brand);
  background-size:100% 1px;
}
article.entry p.brief{
  margin:0 0 10px; font-size:15px; line-height:1.75;
  color:var(--ink-soft);
}
article.entry .why{
  margin:11px 0 0; padding-left:14px;
  border-left:2px solid var(--brand);
  font-size:13.5px; line-height:1.68; color:var(--ink-soft);
  font-style:italic;
}
article.entry .meta{
  display:flex; align-items:center; gap:9px; flex-wrap:wrap;
  margin:14px 0 0; font-size:12px; color:var(--ink-faint);
  letter-spacing:.2px; font-variant-numeric:tabular-nums;
}
article.entry .tag{ color:var(--ink-soft); font-weight:600; }
article.entry .go{
  margin-left:auto; color:var(--ink-faint); text-decoration:none;
  transition:color .15s ease;
}
article.entry .go:hover{ color:var(--brand); }

/* 空状态 */
.empty{
  padding:64px 20px; text-align:center;
  color:var(--ink-faint); font-size:14.5px; line-height:1.8;
}

/* 页脚 */
footer.site{
  display:flex; justify-content:space-between; align-items:center;
  gap:12px; flex-wrap:wrap;
  margin-top:52px; padding-top:22px; border-top:1px solid var(--rule);
  font-size:12px; color:var(--ink-faint); letter-spacing:.2px;
}
footer.site a{ color:var(--ink-faint); text-decoration:none; }
footer.site a:hover{ color:var(--brand); }

/* 归档 */
.back{
  display:inline-block; margin:0 0 30px;
  font-size:13px; color:var(--ink-faint); text-decoration:none;
  transition:color .15s ease;
}
.back:hover{ color:var(--brand); }
ul.arch{ list-style:none; margin:0; padding:0; }
ul.arch li{ margin:0; }
ul.arch a{
  display:flex; justify-content:space-between; align-items:center;
  padding:15px 0; border-bottom:1px solid var(--rule);
  color:var(--ink); text-decoration:none; font-size:15px;
  font-variant-numeric:tabular-nums;
  transition:color .15s ease,padding-left .18s ease;
}
ul.arch a:hover{ color:var(--brand); padding-left:6px; }
ul.arch .arrow{ color:var(--ink-faint); font-size:13px; }

@media(max-width:560px){
  .wrap{ padding:44px 20px 68px; }
  header.site h1{ font-size:24px; }
  article.entry{ padding:24px 0 22px; }
  article.entry h2{ font-size:16.5px; }
  footer.site{ flex-direction:column; align-items:flex-start; gap:6px; }
}
@media(prefers-reduced-motion:reduce){
  *{ transition:none !important; }
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


def _render_page(title: str, body: str, site: dict, extra_head: str = "",
                 depth: int = 0) -> str:
    prefix = "../" * depth
    return f"""<!doctype html>
<html lang="{_esc(site.get('lang', 'zh-CN'))}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{_esc(title)}</title>
<meta name="description" content="{_esc(site.get('subtitle', ''))}">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#fffefb" media="(prefers-color-scheme:light)">
<meta name="theme-color" content="#14130f" media="(prefers-color-scheme:dark)">
<link rel="stylesheet" href="{prefix}assets/marx.css">
<style>{THEME_CSS}</style>
{extra_head}
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


def _copy_assets(out_dir: Path) -> None:
    dest_dir = out_dir / "assets"
    dest_dir.mkdir(parents=True, exist_ok=True)
    if VENDOR_CSS.exists():
        shutil.copyfile(VENDOR_CSS, dest_dir / "marx.css")


def write_site(items: list[Item], date_str: str, config: dict, out_dir: Path,
               archive: list[str] | None = None) -> Path:
    site = config.get("site", {})
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "archive").mkdir(exist_ok=True)
    _copy_assets(out_dir)

    body = f"""<header class="site">
<p class="kicker">Daily Brief</p>
<h1>{_esc(site.get('title', '每日简报'))}</h1>
<p class="sub">{_esc(site.get('subtitle', ''))}</p>
</header>
<div class="dateline">
<strong>{_nice_date(date_str)}</strong>
<span>共 {len(items)} 条</span>
</div>
{_entries_html(items)}
<footer class="site">
<span>{_esc(site.get('title', ''))}</span>
<span><a href="archive/index.html">历史归档</a></span>
</footer>"""

    page = _render_page(f"{_nice_date(date_str)} · {site.get('title', '')}", body, site)
    index_path = out_dir / "index.html"
    index_path.write_text(page, encoding="utf-8")

    archive_body = f"""<header class="site">
<p class="kicker">Archive</p>
<h1>{_esc(site.get('title', '每日简报'))}</h1>
<p class="sub">{_nice_date(date_str)} 的简报</p>
</header>
<a class="back" href="../index.html">← 返回最新</a>
{_entries_html(items)}"""
    archive_page = _render_page(
        f"{_nice_date(date_str)} · 归档 · {site.get('title', '')}", archive_body, site,
        extra_head='<meta name="robots" content="noindex">', depth=1,
    )
    (out_dir / "archive" / f"{date_str}.html").write_text(archive_page, encoding="utf-8")
    return index_path


def write_archive_index(out_dir: Path, site: dict) -> None:
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
<p class="kicker">Archive</p>
<h1>历史归档</h1>
<p class="sub">共 {len(dates)} 期</p>
</header>
<a class="back" href="../index.html">← 返回最新</a>
{listing}"""
    page = _render_page(f"历史归档 · {site.get('title', '')}", body, site,
                        extra_head='<meta name="robots" content="noindex">', depth=1)
    (archive_dir / "index.html").write_text(page, encoding="utf-8")


def write_index_json(archive_dir: Path, out_dir: Path) -> None:
    dates = sorted((p.stem for p in archive_dir.glob("*.html") if p.stem != "index"), reverse=True)
    (out_dir / "dates.json").write_text(
        json.dumps(dates, ensure_ascii=False, indent=2), encoding="utf-8"
    )
