"""渲染：Markdown 归档 + 静态站点。

基础排版使用 Water.css v2（MIT，https://github.com/kognise/water.css），
在其上叠一层轻量卡片与排版微调。只依赖标准库。
"""
from __future__ import annotations

import html
import json
import shutil
from datetime import datetime
from pathlib import Path

from .feed import Item

ROOT = Path(__file__).resolve().parent.parent
VENDOR_CSS = ROOT / "assets" / "water.css"

# 在 Water.css 之上的一层：卡片、编号、来源行、归档列表
THEME_CSS = """
:root{
  --brand:#b8543f;
  --brand-soft:#f7ece8;
  --rule:rgba(128,128,128,.20);
  --card:rgba(128,128,128,.035);
}
@media(prefers-color-scheme:dark){
  :root{ --brand:#e08668; --brand-soft:#2b1d18; --card:rgba(255,255,255,.035); }
}
body{ -webkit-font-smoothing:antialiased; }
.wrap{ max-width:680px; margin:0 auto; padding:52px 22px 84px; }

/* 顶部 */
header.site{ margin-bottom:6px; }
.kicker{ display:flex; align-items:center; gap:9px; margin:0 0 13px;
  font-size:11px; letter-spacing:1.7px; text-transform:uppercase;
  font-weight:700; color:var(--brand); }
.kicker::before{ content:""; width:7px; height:7px; border-radius:50%;
  background:var(--brand); box-shadow:0 0 0 4px var(--brand-soft); }
header.site h1{ margin:0 0 9px; font-size:27px; line-height:1.25;
  letter-spacing:-.6px; font-weight:750; }
header.site .sub{ margin:0; font-size:14.5px; color:var(--text-main); opacity:.62; }

/* 日期条 */
.dateline{ display:flex; justify-content:space-between; align-items:baseline;
  margin:26px 0 4px; padding-top:18px; border-top:1px solid var(--rule);
  font-size:13px; color:var(--text-main); opacity:.62;
  font-variant-numeric:tabular-nums; }
.dateline strong{ font-size:14px; opacity:.95; font-weight:650; }

/* 条目卡片 */
article.entry{
  position:relative; margin:14px 0; padding:20px 22px;
  background:var(--card); border:1px solid var(--rule); border-radius:14px;
  transition:border-color .18s ease, transform .18s ease, background .18s ease;
}
article.entry:hover{ border-color:var(--brand); transform:translateY(-2px); }
article.entry .num{
  display:inline-flex; align-items:center; justify-content:center;
  min-width:22px; height:22px; padding:0 6px; margin:0 0 10px;
  border-radius:7px; background:var(--brand-soft); color:var(--brand);
  font-size:11.5px; font-weight:700; font-variant-numeric:tabular-nums;
  line-height:1;
}
article.entry h2{ margin:0 0 9px; font-size:17.5px; line-height:1.5;
  letter-spacing:-.15px; font-weight:650; }
article.entry h2 a{ color:var(--text-bright); text-decoration:none;
  transition:color .15s ease; }
article.entry h2 a:hover{ color:var(--brand); }
article.entry p.brief{ margin:0 0 10px; font-size:14.5px; line-height:1.72;
  color:var(--text-main); opacity:.74; }
article.entry .why{ margin:11px 0 0; padding:9px 13px; border-radius:10px;
  background:var(--brand-soft); border-left:2px solid var(--brand);
  font-size:13.5px; line-height:1.62; color:var(--text-main); }
article.entry .meta{ display:flex; align-items:center; gap:10px; flex-wrap:wrap;
  margin:13px 0 0; font-size:12.5px; color:var(--text-main); opacity:.55;
  font-variant-numeric:tabular-nums; }
article.entry .tag{ padding:2px 9px; border-radius:999px;
  border:1px solid var(--rule); font-size:11.5px; }
article.entry .go{ margin-left:auto; color:var(--brand); text-decoration:none;
  font-weight:600; opacity:1; }
article.entry .go:hover{ text-decoration:underline; }

/* 空状态 */
.empty{ margin:34px 0; padding:64px 22px; text-align:center; border-radius:14px;
  border:1px dashed var(--rule); color:var(--text-main); opacity:.6; }

/* 页脚 */
footer.site{ display:flex; justify-content:space-between; align-items:center;
  gap:12px; flex-wrap:wrap; margin-top:48px; padding-top:24px;
  border-top:1px solid var(--rule); font-size:12.5px;
  color:var(--text-main); opacity:.52; }
footer.site a{ color:inherit; text-decoration:none; }
footer.site a:hover{ color:var(--brand); opacity:1; }

/* 归档列表 */
.back{ display:inline-flex; align-items:center; gap:6px; margin:20px 0 26px;
  padding:6px 14px 6px 10px; border:1px solid var(--rule); border-radius:999px;
  font-size:13.5px; color:var(--text-main); text-decoration:none;
  transition:color .15s ease, border-color .15s ease; }
.back:hover{ color:var(--brand); border-color:var(--brand); }
ul.arch{ list-style:none; margin:0; padding:0; }
ul.arch li{ margin:0; }
ul.arch a{ display:flex; justify-content:space-between; align-items:center;
  padding:13px 2px; border-bottom:1px solid var(--rule);
  color:var(--text-bright); text-decoration:none; font-size:14.5px;
  font-variant-numeric:tabular-nums; transition:padding .15s ease, color .15s ease; }
ul.arch a:hover{ color:var(--brand); padding-left:8px; }
ul.arch .arrow{ color:var(--text-main); opacity:.4; font-size:13px; }

@media(max-width:560px){
  .wrap{ padding:40px 18px 64px; }
  header.site h1{ font-size:23px; }
  article.entry{ padding:17px 17px; border-radius:12px; }
  article.entry h2{ font-size:16.5px; }
  footer.site{ flex-direction:column; align-items:flex-start; gap:6px; }
}
@media(prefers-reduced-motion:reduce){
  *{ transition:none !important; }
  article.entry:hover{ transform:none; }
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
    """depth=0 首页；depth=1 在 archive/ 子目录里。"""
    prefix = "../" * depth
    return f"""<!doctype html>
<html lang="{_esc(site.get('lang', 'zh-CN'))}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{_esc(title)}</title>
<meta name="description" content="{_esc(site.get('subtitle', ''))}">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#ffffff" media="(prefers-color-scheme:light)">
<meta name="theme-color" content="#202b38" media="(prefers-color-scheme:dark)">
<link rel="stylesheet" href="{prefix}assets/water.css">
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
<div class="num">{idx:02d}</div>
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
    """把 vendor CSS 复制进 docs/assets，保持站点自包含。"""
    dest_dir = out_dir / "assets"
    dest_dir.mkdir(parents=True, exist_ok=True)
    if VENDOR_CSS.exists():
        shutil.copyfile(VENDOR_CSS, dest_dir / "water.css")


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
