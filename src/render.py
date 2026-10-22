"""渲染：多板块静态站点。

首页 = 四板块入口；每板块独立页面 + 归档。
视觉：壁纸 + 玻璃拟态 + Apple 式圆角与动效。
"""
from __future__ import annotations

import hashlib
import html
import json
import shutil
from datetime import datetime
from pathlib import Path

from .feed import Item

ROOT = Path(__file__).resolve().parent.parent
ASSETS_SRC = ROOT / "assets"
WALLPAPER_DIR = ASSETS_SRC / "wallpapers"

DEFAULT_POOL = [
    "we_eri.jpg", "we_ai.jpg", "we_rei.jpg", "we_inori.jpg", "we_star.jpg",
    "we_lake.jpg", "we_forest.jpg", "we_sea.jpg", "we_shanshui.jpg", "we_rain.jpg",
    "night.jpg", "aurora.jpg",
]

DEFAULT_SUBTITLES = [
    "雄关漫道真如铁，而今迈步从头越",
    "不到长城非好汉，屈指行程二万",
    "数风流人物，还看今朝",
    "一万年太久，只争朝夕",
    "世上无难事，只要肯登攀",
    "牢骚太盛防肠断，风物长宜放眼量",
    "为有牺牲多壮志，敢教日月换新天",
    "天若有情天亦老，人间正道是沧桑",
    "无限风光在险峰",
    "待到山花烂漫时，她在丛中笑",
    "江山如此多娇，引无数英雄竞折腰",
    "雄关漫道真如铁",
]

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
html{min-height:100%;-webkit-text-size-adjust:100%}
body{
  min-height:100vh;color:#fff;
  font-family:-apple-system,BlinkMacSystemFont,"SF Pro SC","SF Pro Text",
    "Segoe UI","PingFang SC","Hiragino Sans GB","Noto Sans SC","Microsoft YaHei",sans-serif;
  -webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;
  background:#0b0d12;padding:56px 18px 80px;text-rendering:optimizeLegibility;
}
body::after{
  content:"";position:fixed;inset:0;z-index:-2;
  background:var(--wall) center/cover no-repeat;transform:translateZ(0);
}
body::before{
  content:"";position:fixed;inset:0;z-index:-1;
  background:var(--overlay);pointer-events:none;
}
.wrap{position:relative;z-index:1;max-width:760px;margin:0 auto;padding:0 10px}

.r-lg{border-radius:28px}
.r-md{border-radius:22px}
.r-sm{border-radius:16px}

/* 玻璃 */
.glass{
  position:relative;background-color:transparent;
  backdrop-filter:blur(38px) saturate(180%);
  -webkit-backdrop-filter:blur(38px) saturate(180%);
  background-image:
    linear-gradient(145deg,rgb(255 255 255/.13) 0%,rgb(255 255 255/.05) 38%,
      rgb(255 255 255/.025) 62%,rgb(255 255 255/.08) 100%),
    linear-gradient(100deg,rgb(255 255 255/.07) 0%,transparent 28%,
      transparent 72%,rgb(255 255 255/.05) 100%);
  box-shadow:
    inset 0 1px 0 0 rgb(255 255 255/.22),
    inset 0 -1px 0 0 rgb(0 0 0/.12),
    inset 0 0 0 1px rgb(255 255 255/.10),
    0 10px 34px -6px rgb(0 0 0/.34),
    0 2px 8px -2px rgb(0 0 0/.22);
  transition:transform .48s cubic-bezier(.34,1.7,.5,1),
    box-shadow .48s cubic-bezier(.34,1.7,.5,1),background-image .42s ease;
  will-change:transform;
}
.glass:hover{
  background-image:
    linear-gradient(145deg,rgb(255 255 255/.19) 0%,rgb(255 255 255/.09) 38%,
      rgb(255 255 255/.045) 62%,rgb(255 255 255/.12) 100%),
    linear-gradient(100deg,rgb(255 255 255/.11) 0%,transparent 28%,
      transparent 72%,rgb(255 255 255/.08) 100%);
  box-shadow:
    inset 0 1px 0 0 rgb(255 255 255/.32),
    inset 0 -1px 0 0 rgb(0 0 0/.12),
    inset 0 0 0 1px rgb(255 255 255/.16),
    0 22px 54px -10px rgb(0 0 0/.46),
    0 4px 14px -2px rgb(0 0 0/.28);
}
.glass::before{
  content:"";position:absolute;inset:0;border-radius:inherit;padding:1.5px;
  background:linear-gradient(145deg,rgb(255 255 255/.5) 0%,rgb(255 255 255/.16) 22%,
    rgb(255 255 255/.04) 48%,rgb(255 255 255/.07) 72%,rgb(255 255 255/.34) 100%);
  -webkit-mask:linear-gradient(#fff 0 0) content-box,linear-gradient(#fff 0 0);
  -webkit-mask-composite:xor;
  mask:linear-gradient(#fff 0 0) content-box,linear-gradient(#fff 0 0);
  mask-composite:exclude;
  pointer-events:none;opacity:.95;transition:opacity .42s ease;
}
.glass:hover::before{opacity:1}
.glass .sheen{
  position:absolute;inset:0;border-radius:inherit;overflow:hidden;pointer-events:none;
}
.glass .sheen::before{
  content:"";position:absolute;top:-60%;left:-40%;width:60%;height:220%;
  background:linear-gradient(100deg,transparent 0%,rgb(255 255 255/.08) 30%,
    rgb(255 255 255/.2) 50%,rgb(255 255 255/.08) 70%,transparent 100%);
  transform:rotate(14deg);filter:blur(1px);opacity:.8;
  transition:transform .9s cubic-bezier(.22,.61,.36,1),opacity .5s ease;
}
.glass:hover .sheen::before{transform:rotate(14deg) translateX(190%);opacity:1}

/* 页头 */
header.hero{
  padding:40px 28px;text-align:center;margin-bottom:22px;
  --hero-scale:1.1;transform:translateZ(0);
}
header.hero:hover{
  transform:translateY(-4px) scale(var(--hero-scale)) translateZ(0);z-index:20;
}
.kicker{
  font-size:10.5px;letter-spacing:.26em;text-transform:uppercase;
  font-weight:700;color:rgb(255 255 255/.58);margin-bottom:14px;
}
header.hero h1{
  font-size:32px;font-weight:760;letter-spacing:-.8px;line-height:1.18;
  text-shadow:0 2px 18px rgb(0 0 0/.42);
}
header.hero .sub{
  margin-top:14px;font-size:15px;line-height:1.7;
  color:rgb(255 255 255/.78);font-weight:400;letter-spacing:.3px;
  font-family:"Kaiti SC","STKaiti",Georgia,serif;
}

/* 板块入口卡片 */
.sections{display:grid;gap:16px;margin-bottom:22px}
.section-card{
  display:block;padding:26px 28px;text-decoration:none;color:#fff;
  transform:translateZ(0);opacity:0;translate:0 18px;
  animation:fadeUp .6s cubic-bezier(.22,.61,.36,1) forwards;
}
.section-card:nth-child(1){animation-delay:.06s}
.section-card:nth-child(2){animation-delay:.12s}
.section-card:nth-child(3){animation-delay:.18s}
.section-card:nth-child(4){animation-delay:.24s}
.section-card:hover{transform:translateY(-6px) scale(1.02) translateZ(0);z-index:20}
.section-card:active{transform:translateY(-3px) scale(1.005) translateZ(0)}
.sec-head{display:flex;align-items:center;gap:14px;margin-bottom:10px}
.sec-icon{
  font-size:26px;line-height:1;filter:drop-shadow(0 2px 8px rgb(0 0 0/.4));
}
.sec-name{font-size:20px;font-weight:720;letter-spacing:-.3px}
.sec-count{
  margin-left:auto;font-size:12px;color:rgb(255 255 255/.55);
  font-variant-numeric:tabular-nums;
}
.sec-desc{font-size:13.5px;color:rgb(255 255 255/.62);line-height:1.6}
.sec-preview{
  margin-top:14px;padding-top:14px;border-top:1px solid rgb(255 255 255/.10);
  font-size:13px;color:rgb(255 255 255/.72);line-height:1.65;
}
.sec-preview li{
  list-style:none;margin-bottom:6px;padding-left:14px;position:relative;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
}
.sec-preview li::before{
  content:"·";position:absolute;left:2px;color:rgb(255 255 255/.4);
}
.sec-arrow{
  display:inline-flex;align-items:center;gap:6px;margin-top:14px;
  font-size:12.5px;font-weight:650;color:rgb(255 255 255/.68);
  transition:color .2s ease,gap .3s cubic-bezier(.34,1.7,.5,1);
}
.section-card:hover .sec-arrow{color:#fff;gap:10px}

/* 条目 */
.card{
  padding:24px 26px;margin-bottom:24px;opacity:0;translate:0 20px;
  animation:fadeUp .68s cubic-bezier(.22,.61,.36,1) forwards;
  transform:translateZ(0);backface-visibility:hidden;
}
.card:nth-of-type(1){animation-delay:.06s}
.card:nth-of-type(2){animation-delay:.12s}
.card:nth-of-type(3){animation-delay:.18s}
.card:nth-of-type(4){animation-delay:.24s}
.card:nth-of-type(5){animation-delay:.30s}
.card:nth-of-type(6){animation-delay:.36s}
@keyframes fadeUp{from{opacity:0;translate:0 20px}to{opacity:1;translate:0 0}}
.card:hover{transform:translateY(-10px) scale(1.045) translateZ(0);z-index:20}
.card:active{transform:translateY(-5px) scale(1.01) translateZ(0);transition-duration:.1s}
.card::after{
  content:"";position:absolute;inset:0;border-radius:inherit;
  background:radial-gradient(420px circle at var(--mx,50%) var(--my,0%),
    rgb(255 255 255/.13),transparent 62%);
  opacity:0;transition:opacity .35s ease;pointer-events:none;
}
.card:hover::after{opacity:1}

.row{display:flex;align-items:center;gap:10px;margin-bottom:12px}
.idx{
  display:inline-flex;align-items:center;justify-content:center;
  min-width:27px;height:27px;padding:0 8px;border-radius:10px;
  background:linear-gradient(145deg,rgb(255 255 255/.22),rgb(255 255 255/.10));
  box-shadow:inset 0 1px 0 rgb(255 255 255/.3),inset 0 0 0 1px rgb(255 255 255/.14);
  font-size:11.5px;font-weight:750;font-variant-numeric:tabular-nums;
}
.src{font-size:12px;font-weight:650;color:rgb(255 255 255/.9)}
.time{margin-left:auto;font-size:11.5px;color:rgb(255 255 255/.5);
  font-variant-numeric:tabular-nums}
.card h2{
  font-size:18px;font-weight:680;line-height:1.5;letter-spacing:-.25px;
  text-shadow:0 1px 12px rgb(0 0 0/.32);
}
.card h2 a{
  color:#fff;text-decoration:none;
  background-image:linear-gradient(90deg,rgb(255 255 255/.85),rgb(255 255 255/.45));
  background-size:0% 1.5px;background-position:0 calc(100% - 1px);
  background-repeat:no-repeat;padding-bottom:2px;
  transition:background-size .38s cubic-bezier(.22,.61,.36,1);
}
.card h2 a:hover{background-size:100% 1.5px}
.card h2 a:focus-visible{
  outline:none;background-size:100% 1.5px;
  box-shadow:0 0 0 3px rgb(255 255 255/.28);border-radius:6px;
}
.card p.brief{margin-top:10px;font-size:14.5px;line-height:1.74;color:rgb(255 255 255/.76)}
.card p.why{
  margin-top:12px;padding:10px 15px;border-radius:13px;
  background:linear-gradient(135deg,rgb(255 255 255/.13),rgb(255 255 255/.06));
  box-shadow:inset 0 0 0 1px rgb(255 255 255/.08);
  border-left:2px solid rgb(255 255 255/.42);
  font-size:13.5px;line-height:1.66;color:rgb(255 255 255/.9);font-style:italic;
}
.card .go{
  display:inline-flex;align-items:center;gap:5px;margin-top:15px;padding:7px 15px;
  border-radius:12px;font-size:12.5px;font-weight:650;color:rgb(255 255 255/.78);
  text-decoration:none;
  background:linear-gradient(145deg,rgb(255 255 255/.12),rgb(255 255 255/.05));
  box-shadow:inset 0 0 0 1px rgb(255 255 255/.10);
  transition:all .3s cubic-bezier(.22,.61,.36,1);
}
.card .go:hover{
  color:#fff;background:linear-gradient(145deg,rgb(255 255 255/.22),rgb(255 255 255/.10));
  box-shadow:inset 0 0 0 1px rgb(255 255 255/.2),0 6px 18px -6px rgb(0 0 0/.4);
  transform:translateY(-1px);
}
.card .go span{display:inline-block;transition:transform .3s cubic-bezier(.22,.61,.36,1)}
.card .go:hover span{transform:translateX(4px)}

.empty{padding:64px 24px;text-align:center;font-size:14.5px;line-height:1.8;
  color:rgb(255 255 255/.58)}

footer.site{
  padding:16px 22px;margin-top:28px;
  display:flex;justify-content:space-between;align-items:center;
  gap:12px;flex-wrap:wrap;font-size:12px;color:rgb(255 255 255/.48);
}
footer.site a{color:rgb(255 255 255/.62);text-decoration:none;transition:color .2s}
footer.site a:hover{color:#fff}

/* 返回与归档 */
.back{
  display:inline-flex;align-items:center;gap:6px;margin:4px 0 20px;padding:8px 18px;
  font-size:13px;color:rgb(255 255 255/.8);text-decoration:none;
  transition:all .3s cubic-bezier(.22,.61,.36,1);
}
.back:hover{color:#fff;transform:translateX(-4px)}
ul.arch{list-style:none}
ul.arch a{
  display:flex;justify-content:space-between;align-items:center;
  padding:16px 20px;margin-bottom:14px;color:#fff;text-decoration:none;
  font-size:14.5px;font-variant-numeric:tabular-nums;
  transition:all .32s cubic-bezier(.22,.61,.36,1);
}
ul.arch a:hover{transform:translateX(6px) scale(1.008)}
ul.arch .arrow{color:rgb(255 255 255/.45);font-size:13px;transition:transform .32s}
ul.arch a:hover .arrow{transform:translateX(4px);color:rgb(255 255 255/.85)}

/* 板块页导航 */
.tabs{
  display:flex;gap:8px;margin-bottom:20px;padding:8px;flex-wrap:wrap;
  justify-content:center;
}
.tab{
  padding:7px 16px;border-radius:12px;font-size:13px;font-weight:600;
  color:rgb(255 255 255/.65);text-decoration:none;
  transition:all .28s cubic-bezier(.34,1.7,.5,1);
}
.tab:hover{color:#fff;background:rgb(255 255 255/.1)}
.tab.active{
  color:#fff;background:rgb(255 255 255/.18);
  box-shadow:inset 0 0 0 1px rgb(255 255 255/.22);
}

@media(max-width:820px){header.hero{--hero-scale:1.05}}
@media(max-width:600px){
  body{padding:30px 12px 56px}
  header.hero{padding:28px 20px}
  header.hero h1{font-size:25px}
  header.hero .sub{font-size:13.5px;margin-top:11px}
  .card{padding:19px 19px;margin-bottom:18px}
  .card h2{font-size:16.5px}
  .section-card{padding:20px 20px}
  .sec-name{font-size:18px}
  .r-lg{border-radius:22px}
  .r-md{border-radius:18px}
  .r-sm{border-radius:14px}
  footer.site{flex-direction:column;align-items:flex-start;gap:6px}
  .card:hover,.glass:hover,header.hero:hover,.section-card:hover{transform:none;z-index:auto}
  .card::after{display:none}
}
@media(prefers-reduced-motion:reduce){
  *{animation:none!important;transition:none!important}
  .card,.section-card{opacity:1!important}
  .card:hover,.glass:hover,.back:hover,ul.arch a:hover{transform:none}
}
"""

JS = """
(function(){
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  if (window.matchMedia('(hover: none)').matches) return;
  document.querySelectorAll('.card').forEach(function(card){
    card.addEventListener('pointermove', function(e){
      var r = card.getBoundingClientRect();
      card.style.setProperty('--mx', ((e.clientX - r.left) / r.width * 100) + '%');
      card.style.setProperty('--my', ((e.clientY - r.top) / r.height * 100) + '%');
    });
    card.addEventListener('pointerleave', function(){
      card.style.setProperty('--mx', '50%');
      card.style.setProperty('--my', '0%');
    });
  });
})();
"""


def _esc(text: str) -> str:
    return html.escape(text or "", quote=True)


def _nice_date(date_str: str) -> str:
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return date_str
    week = "一二三四五六日"[dt.weekday()]
    return f"{dt.month}月{dt.day}日 星期{week}"


def _seed(text: str) -> int:
    return int(hashlib.md5(text.encode()).hexdigest()[:8], 16)


def pick_wallpaper(date_str: str, site: dict) -> str:
    pool = site.get("wallpapers") or DEFAULT_POOL
    pool = [p for p in pool if (WALLPAPER_DIR / p).exists()]
    if not pool:
        return "night.jpg"
    return pool[_seed(date_str) % len(pool)]


def pick_subtitle(date_str: str, site: dict) -> str:
    pool = site.get("subtitle_rotation") or DEFAULT_SUBTITLES
    if not pool:
        return ""
    return pool[_seed("sub-" + date_str) % len(pool)]


def build_markdown(items: list[Item], date_str: str, site: dict,
                   heading_offset: int = 1) -> str:
    h = "#" * heading_offset
    lines = [f"{h} {date_str}", ""] if heading_offset == 1 else []
    if not items:
        lines += ["今天没有值得推送的内容。", ""]
        return "\n".join(lines)
    for idx, it in enumerate(items, 1):
        brief = it.extra.get("brief") or ""
        why = it.extra.get("why") or ""
        lines.append(f"{h}## {idx}. {it.title}")
        lines.append("")
        if brief:
            lines.append(brief)
            lines.append("")
        if why:
            lines.append(f"> {why}")
            lines.append("")
        hours = it.extra.get("hours_ago")
        stamp = f"{hours}h 前" if hours is not None else ""
        lines.append(f"[原文]({it.link}) · {it.source}" + (f" · {stamp}" if stamp else ""))
        lines.append("")
    return "\n".join(lines)


def _render_page(title: str, body: str, site: dict, extra_head: str = "",
                 depth: int = 0, wallpaper: str = "") -> str:
    prefix = "../" * depth
    wall = wallpaper or site.get("wallpaper") or "night.jpg"
    overlay = site.get("overlay") or (
        "linear-gradient(180deg,rgba(4,5,14,.20) 0%,"
        "rgba(4,5,14,.38) 50%,rgba(4,5,14,.52) 100%)"
    )
    return f"""<!doctype html>
<html lang="{_esc(site.get('lang', 'zh-CN'))}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{_esc(title)}</title>
<meta name="description" content="{_esc(site.get('title', ''))}">
<meta name="color-scheme" content="dark">
<meta name="theme-color" content="#0b0d12">
<link rel="preload" as="image" href="{prefix}assets/wallpapers/{_esc(wall)}">
<style>
body{{--wall:url("{prefix}assets/wallpapers/{_esc(wall)}")}}
body{{--overlay:{overlay}}}
{CSS}
</style>
{extra_head}
</head>
<body>
<div class="wrap">
{body}
</div>
<script>{JS}</script>
</body>
</html>
"""


def _entries_html(items: list[Item]) -> str:
    if not items:
        return '<div class="empty glass r-md">今天没有值得推送的内容。<br>明天见。</div>'
    parts = []
    for idx, it in enumerate(items, 1):
        brief = _esc(it.extra.get("brief") or "")
        why = _esc(it.extra.get("why") or "")
        hours = it.extra.get("hours_ago")
        stamp = f'<span class="time">{hours}h 前</span>' if hours is not None else ""
        brief_html = f'<p class="brief">{brief}</p>' if brief else ""
        why_html = f'<p class="why">{why}</p>' if why else ""
        parts.append(f"""<article class="glass card r-md">
<div class="sheen"></div>
<div class="row"><span class="idx">{idx:02d}</span>
<span class="src">{_esc(it.source)}</span>{stamp}</div>
<h2><a href="{_esc(it.link)}" target="_blank" rel="noopener">{_esc(it.title)}</a></h2>
{brief_html}
{why_html}
<a class="go" href="{_esc(it.link)}" target="_blank" rel="noopener">阅读原文 <span>→</span></a>
</article>""")
    return "\n".join(parts)


def _copy_assets(out_dir: Path) -> None:
    dest = out_dir / "assets" / "wallpapers"
    dest.mkdir(parents=True, exist_ok=True)
    if WALLPAPER_DIR.exists():
        for img in WALLPAPER_DIR.glob("*.jpg"):
            shutil.copyfile(img, dest / img.name)


def _tabs(sections: list[dict], active: str, depth: int = 0) -> str:
    prefix = "" if depth == 0 else ""
    parts = [f'<a class="tab" href="{prefix}index.html">首页</a>']
    for s in sections:
        sid = s.get("id")
        cls = "tab active" if sid == active else "tab"
        parts.append(
            f'<a class="{cls}" href="{prefix}{sid}.html">'
            f'{_esc(s.get("icon", ""))} {_esc(s.get("name", sid))}</a>'
        )
    return f'<nav class="tabs glass r-md">{"".join(parts)}</nav>'


def write_all(results: dict[str, list[Item]], sections: list[dict], date_str: str,
              config: dict, out_dir: Path) -> None:
    """首页 + 每板块页 + 归档。"""
    site = config.get("site", {})
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "archive").mkdir(exist_ok=True)
    _copy_assets(out_dir)
    wall = pick_wallpaper(date_str, site)
    subtitle = pick_subtitle(date_str, site)
    title = site.get("title", "每日简报")

    # ---------- 首页：四板块入口 ----------
    cards = []
    for s in sections:
        sid = s.get("id", "?")
        items = results.get(sid, [])
        preview = "".join(
            f"<li>{_esc(it.title)}</li>" for it in items[:3]
        )
        cards.append(f"""<a class="glass section-card r-md" href="{sid}.html">
<div class="sheen"></div>
<div class="sec-head">
<span class="sec-icon">{_esc(s.get('icon', ''))}</span>
<span class="sec-name">{_esc(s.get('name', sid))}</span>
<span class="sec-count">{len(items)} 条</span>
</div>
<p class="sec-desc">{_esc(s.get('desc', ''))}</p>
<ul class="sec-preview">{preview}</ul>
<span class="sec-arrow">进入板块 <span>→</span></span>
</a>""")

    home_body = f"""<header class="hero glass r-lg">
<div class="sheen"></div>
<p class="kicker">Daily Brief</p>
<h1>{_esc(title)}</h1>
<p class="sub">{_esc(subtitle)}</p>
</header>
<div class="sections">
{''.join(cards)}
</div>
<footer class="site glass r-sm">
<span>{_nice_date(date_str)}</span>
<span><a href="archive/index.html">历史归档</a></span>
</footer>"""
    (out_dir / "index.html").write_text(
        _render_page(title, home_body, site, wallpaper=wall), encoding="utf-8"
    )

    # ---------- 各板块页 ----------
    for s in sections:
        sid = s.get("id", "?")
        name = s.get("name", sid)
        items = results.get(sid, [])
        body = f"""<header class="hero glass r-lg">
<div class="sheen"></div>
<p class="kicker">{_esc(s.get('icon', ''))} {_esc(name)}</p>
<h1>{_esc(name)}</h1>
<p class="sub">{_esc(subtitle)}</p>
</header>
{_tabs(sections, sid)}
{_entries_html(items)}
<footer class="site glass r-sm">
<span>{_nice_date(date_str)} · {len(items)} 条</span>
<span><a href="archive/{sid}.html">往期</a></span>
</footer>"""
        (out_dir / f"{sid}.html").write_text(
            _render_page(f"{name} · {_nice_date(date_str)}", body, site, wallpaper=wall),
            encoding="utf-8",
        )

        # 板块归档页
        arch_body = f"""<header class="hero glass r-lg">
<div class="sheen"></div>
<p class="kicker">{_esc(s.get('icon', ''))} {_esc(name)} · 归档</p>
<h1>{_nice_date(date_str)}</h1>
<p class="sub">{_esc(subtitle)}</p>
</header>
<a class="back glass r-sm" href="../{sid}.html">← 返回{_esc(name)}</a>
{_entries_html(items)}"""
        (out_dir / "archive" / f"{sid}.html").write_text(
            _render_page(f"{name} · 归档 · {_nice_date(date_str)}", arch_body, site,
                         extra_head='<meta name="robots" content="noindex">',
                         depth=1, wallpaper=wall),
            encoding="utf-8",
        )

    # ---------- 归档索引 ----------
    arch_items = "".join(
        f'<li><a class="glass r-sm" href="archive/{s.get("id")}.html">'
        f'<span>{_esc(s.get("icon", ""))} {_esc(s.get("name", ""))}'
        f' · {_nice_date(date_str)}</span>'
        f'<span class="arrow">→</span></a></li>'
        for s in sections
    )
    arch_body = f"""<header class="hero glass r-lg">
<div class="sheen"></div>
<p class="kicker">Archive</p>
<h1>历史归档</h1>
<p class="sub">{_nice_date(date_str)}</p>
</header>
<a class="back glass r-sm" href="../index.html">← 返回首页</a>
<ul class="arch">{arch_items}</ul>"""
    (out_dir / "archive" / "index.html").write_text(
        _render_page("历史归档", arch_body, site,
                     extra_head='<meta name="robots" content="noindex">',
                     depth=1, wallpaper=wall),
        encoding="utf-8",
    )

    # 日期索引
    (out_dir / "dates.json").write_text(
        json.dumps([date_str], ensure_ascii=False, indent=2), encoding="utf-8"
    )
