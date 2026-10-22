"""渲染：Markdown 归档 + 静态站点。

视觉方案：壁纸 + 玻璃拟态（glassmorphism）。
玻璃效果沿用 daisyUI 的 .glass 实现（MIT，https://daisyui.com），
背景图来自 Unsplash（Unsplash License，可免费商用）。
"""
from __future__ import annotations

import html
import json
import shutil
from datetime import datetime
from pathlib import Path

from .feed import Item

ROOT = Path(__file__).resolve().parent.parent
ASSETS_SRC = ROOT / "assets"

# 默认壁纸（可在 config.json 的 site.wallpaper 覆盖）
DEFAULT_WALLPAPER = "night.jpg"

CSS = """
/* ============ daisyUI .glass（MIT）============ */
.glass{
  --glass-opacity:18%;
  --glass-border-opacity:14%;
  --glass-reflex-degree:100deg;
  --glass-reflex-opacity:9%;
  --glass-blur:40px;
  backdrop-filter:blur(var(--glass-blur));
  -webkit-backdrop-filter:blur(var(--glass-blur));
  background-color:transparent;
  background-image:
    linear-gradient(135deg, rgb(255 255 255 / var(--glass-opacity)) 0%, transparent 100%),
    linear-gradient(var(--glass-reflex-degree),
      rgb(255 255 255 / var(--glass-reflex-opacity)) 25%, transparent 25%);
  box-shadow:
    0 0 0 1px rgb(255 255 255 / var(--glass-border-opacity)) inset,
    0 8px 32px rgb(0 0 0 / .28);
}
.glass:hover{
  --glass-opacity:25%;
  --glass-border-opacity:15%;
}

/* ============ 基础 ============ */
*{margin:0;padding:0;box-sizing:border-box}
html{min-height:100%}
body{
  min-height:100vh;color:#fff;
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC",
    "Hiragino Sans GB","Noto Sans SC","Microsoft YaHei",sans-serif;
  -webkit-font-smoothing:antialiased;
  background:#0b0d12 center/cover fixed no-repeat;
  padding:56px 18px 80px;
}
body::before{
  content:"";position:fixed;inset:0;z-index:0;
  background:var(--overlay);
  pointer-events:none;
}
.wrap{position:relative;z-index:1;max-width:700px;margin:0 auto}

/* 头部 */
header.hero{
  border-radius:26px;padding:36px 28px;text-align:center;margin-bottom:16px;
  transition:transform .35s cubic-bezier(.2,.8,.2,1);
}
header.hero:hover{transform:translateY(-3px)}
.kicker{
  font-size:10.5px;letter-spacing:.24em;text-transform:uppercase;
  font-weight:700;color:rgba(255,255,255,.62);margin-bottom:12px;
}
header.hero h1{
  font-size:31px;font-weight:750;letter-spacing:-.6px;line-height:1.2;
  text-shadow:0 2px 16px rgba(0,0,0,.4);
}
header.hero .sub{margin-top:10px;font-size:14px;color:rgba(255,255,255,.68)}

/* 日期条 */
.dateline{
  border-radius:14px;padding:13px 20px;margin-bottom:16px;
  display:flex;justify-content:space-between;align-items:center;
  font-size:12.5px;color:rgba(255,255,255,.72);
  font-variant-numeric:tabular-nums;
}
.dateline strong{font-weight:650;color:rgba(255,255,255,.9)}

/* 卡片 */
.card{
  border-radius:20px;padding:24px 26px;margin-bottom:14px;
  transition:transform .35s cubic-bezier(.2,.8,.2,1),box-shadow .35s ease;
  opacity:0;animation:rise .6s cubic-bezier(.2,.8,.2,1) forwards;
}
.card:nth-of-type(1){animation-delay:.05s}
.card:nth-of-type(2){animation-delay:.10s}
.card:nth-of-type(3){animation-delay:.15s}
.card:nth-of-type(4){animation-delay:.20s}
.card:nth-of-type(5){animation-delay:.25s}
.card:nth-of-type(6){animation-delay:.30s}
@keyframes rise{
  from{opacity:0;transform:translateY(18px)}
  to{opacity:1;transform:none}
}
.card:hover{
  transform:translateY(-5px);
  box-shadow:
    0 0 0 1px rgb(255 255 255 / .18) inset,
    0 20px 52px rgb(0 0 0 / .38);
}
.row{display:flex;align-items:center;gap:10px;margin-bottom:12px}
.idx{
  display:inline-flex;align-items:center;justify-content:center;
  min-width:26px;height:26px;padding:0 7px;border-radius:9px;
  background:rgba(255,255,255,.16);
  box-shadow:0 0 0 1px rgba(255,255,255,.2) inset;
  font-size:11.5px;font-weight:750;font-variant-numeric:tabular-nums;
}
.src{font-size:12px;font-weight:650;color:rgba(255,255,255,.88)}
.time{
  margin-left:auto;font-size:11.5px;color:rgba(255,255,255,.52);
  font-variant-numeric:tabular-nums;
}
.card h2{
  font-size:18px;font-weight:680;line-height:1.5;letter-spacing:-.2px;
  text-shadow:0 1px 10px rgba(0,0,0,.3);
}
.card h2 a{color:#fff;text-decoration:none}
.card h2 a:hover{
  text-decoration:underline;text-underline-offset:4px;
  text-decoration-color:rgba(255,255,255,.5);
}
.card p.brief{
  margin-top:10px;font-size:14.5px;line-height:1.72;
  color:rgba(255,255,255,.78);
}
.card p.why{
  margin-top:11px;padding:9px 14px;border-radius:11px;
  background:rgba(255,255,255,.09);
  border-left:2px solid rgba(255,255,255,.45);
  font-size:13.5px;line-height:1.65;color:rgba(255,255,255,.88);
  font-style:italic;
}
.card .go{
  display:inline-block;margin-top:14px;font-size:13px;font-weight:650;
  color:rgba(255,255,255,.72);text-decoration:none;
  transition:color .2s ease,letter-spacing .2s ease;
}
.card .go:hover{color:#fff;letter-spacing:.3px}
.card .go span{display:inline-block;transition:transform .2s ease}
.card .go:hover span{transform:translateX(4px)}

/* 空状态 */
.empty{
  border-radius:20px;padding:64px 24px;text-align:center;
  font-size:14.5px;line-height:1.8;color:rgba(255,255,255,.6);
}

/* 页脚 */
footer.site{
  border-radius:14px;padding:16px 22px;margin-top:28px;
  display:flex;justify-content:space-between;align-items:center;
  gap:12px;flex-wrap:wrap;
  font-size:12px;color:rgba(255,255,255,.5);
}
footer.site a{color:rgba(255,255,255,.6);text-decoration:none}
footer.site a:hover{color:#fff}

/* 归档 */
.back{
  display:inline-block;margin:4px 0 20px;padding:8px 18px;
  border-radius:999px;font-size:13px;
  color:rgba(255,255,255,.8);text-decoration:none;
  transition:color .2s ease,transform .2s ease;
}
.back:hover{color:#fff;transform:translateX(-3px)}
ul.arch{list-style:none}
ul.arch li{margin:0}
ul.arch a{
  display:flex;justify-content:space-between;align-items:center;
  padding:15px 20px;margin-bottom:9px;border-radius:14px;
  color:#fff;text-decoration:none;font-size:14.5px;
  font-variant-numeric:tabular-nums;
  transition:transform .25s cubic-bezier(.2,.8,.2,1),box-shadow .25s ease;
}
ul.arch a:hover{
  transform:translateX(5px);
  box-shadow:
    0 0 0 1px rgb(255 255 255 / .2) inset,
    0 12px 32px rgb(0 0 0 / .32);
}
ul.arch .arrow{color:rgba(255,255,255,.5);font-size:13px}

@media(max-width:600px){
  body{padding:30px 12px 56px;background-attachment:scroll}
  header.hero{padding:26px 20px;border-radius:20px}
  header.hero h1{font-size:24px}
  .card{padding:19px 19px;border-radius:16px}
  .card h2{font-size:16.5px}
  footer.site{flex-direction:column;align-items:flex-start;gap:6px}
}
@media(prefers-reduced-motion:reduce){
  *{animation:none!important;transition:none!important}
  .card{opacity:1!important}
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
    wall = site.get("wallpaper") or DEFAULT_WALLPAPER
    overlay = site.get("overlay") or "linear-gradient(180deg,rgba(8,8,20,.48),rgba(8,8,20,.80))"
    return f"""<!doctype html>
<html lang="{_esc(site.get('lang', 'zh-CN'))}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{_esc(title)}</title>
<meta name="description" content="{_esc(site.get('subtitle', ''))}">
<meta name="color-scheme" content="dark">
<meta name="theme-color" content="#0b0d12">
<link rel="preload" as="image" href="{prefix}assets/wallpapers/{_esc(wall)}">
<style>
body{{background-image:url("{prefix}assets/wallpapers/{_esc(wall)}")}}
body{{--overlay:{overlay}}}
{CSS}
</style>
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
        return '<div class="empty glass">今天没有值得推送的内容。<br>明天见。</div>'
    parts = []
    for idx, it in enumerate(items, 1):
        brief = _esc(it.extra.get("brief") or "")
        why = _esc(it.extra.get("why") or "")
        hours = it.extra.get("hours_ago")
        stamp = f'<span class="time">{hours}h 前</span>' if hours is not None else ""
        brief_html = f'<p class="brief">{brief}</p>' if brief else ""
        why_html = f'<p class="why">{why}</p>' if why else ""
        parts.append(f"""<article class="glass card">
<div class="row"><span class="idx">{idx:02d}</span>
<span class="src">{_esc(it.source)}</span>{stamp}</div>
<h2><a href="{_esc(it.link)}" target="_blank" rel="noopener">{_esc(it.title)}</a></h2>
{brief_html}
{why_html}
<a class="go" href="{_esc(it.link)}" target="_blank" rel="noopener">阅读原文 <span>→</span></a>
</article>""")
    return "\n".join(parts)


def _copy_assets(out_dir: Path) -> None:
    """把壁纸复制进 docs/assets，站点自包含。"""
    src_walls = ASSETS_SRC / "wallpapers"
    dest_walls = out_dir / "assets" / "wallpapers"
    dest_walls.mkdir(parents=True, exist_ok=True)
    if src_walls.exists():
        for img in src_walls.glob("*.jpg"):
            shutil.copyfile(img, dest_walls / img.name)


def write_site(items: list[Item], date_str: str, config: dict, out_dir: Path,
               archive: list[str] | None = None) -> Path:
    site = config.get("site", {})
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "archive").mkdir(exist_ok=True)
    _copy_assets(out_dir)

    body = f"""<header class="hero glass">
<p class="kicker">Daily Brief</p>
<h1>{_esc(site.get('title', '每日简报'))}</h1>
<p class="sub">{_esc(site.get('subtitle', ''))}</p>
</header>
<div class="dateline glass">
<strong>{_nice_date(date_str)}</strong><span>共 {len(items)} 条</span>
</div>
{_entries_html(items)}
<footer class="site glass">
<span>{_esc(site.get('title', ''))}</span>
<span><a href="archive/index.html">历史归档</a></span>
</footer>"""

    page = _render_page(f"{_nice_date(date_str)} · {site.get('title', '')}", body, site)
    index_path = out_dir / "index.html"
    index_path.write_text(page, encoding="utf-8")

    archive_body = f"""<header class="hero glass">
<p class="kicker">Archive</p>
<h1>{_esc(site.get('title', '每日简报'))}</h1>
<p class="sub">{_nice_date(date_str)} 的简报</p>
</header>
<a class="back glass" href="../index.html">← 返回最新</a>
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
            f'<li><a class="glass" href="{d}.html"><span>{_nice_date(d)}</span>'
            f'<span class="arrow">→</span></a></li>'
            for d in dates
        )
        listing = f'<ul class="arch">{rows}</ul>'
    else:
        listing = '<div class="empty glass">还没有归档。</div>'

    body = f"""<header class="hero glass">
<p class="kicker">Archive</p>
<h1>历史归档</h1>
<p class="sub">共 {len(dates)} 期</p>
</header>
<a class="back glass" href="../index.html">← 返回最新</a>
{listing}"""
    page = _render_page(f"历史归档 · {site.get('title', '')}", body, site,
                        extra_head='<meta name="robots" content="noindex">', depth=1)
    (archive_dir / "index.html").write_text(page, encoding="utf-8")


def write_index_json(archive_dir: Path, out_dir: Path) -> None:
    dates = sorted((p.stem for p in archive_dir.glob("*.html") if p.stem != "index"), reverse=True)
    (out_dir / "dates.json").write_text(
        json.dumps(dates, ensure_ascii=False, indent=2), encoding="utf-8"
    )
