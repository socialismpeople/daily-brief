"""渲染：Markdown 归档 + 静态站点。

视觉方案：壁纸 + 玻璃拟态（glassmorphism）+ Apple 式圆角与动效。
玻璃基础沿用 daisyUI 的 .glass（MIT，https://daisyui.com）并做了渐变强化。
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

# 默认壁纸池（config.json 的 site.wallpapers 可覆盖；为空则用目录下全部）
DEFAULT_POOL = [
    "we_eri.jpg", "we_ai.jpg", "we_rei.jpg", "we_inori.jpg", "we_star.jpg",
    "we_lake.jpg", "we_forest.jpg", "we_sea.jpg", "we_shanshui.jpg", "we_rain.jpg",
    "night.jpg", "aurora.jpg",
]

CSS = """
/* ============ 基础 ============ */
*{margin:0;padding:0;box-sizing:border-box}
html{min-height:100%;-webkit-text-size-adjust:100%}
body{
  min-height:100vh;color:#fff;
  font-family:-apple-system,BlinkMacSystemFont,"SF Pro SC","SF Pro Text",
    "Segoe UI","PingFang SC","Hiragino Sans GB","Noto Sans SC","Microsoft YaHei",sans-serif;
  -webkit-font-smoothing:antialiased;
  -moz-osx-font-smoothing:grayscale;
  background:#0b0d12;
  padding:56px 18px 80px;
  text-rendering:optimizeLegibility;
}
/* 固定背景层：比 background-attachment:fixed 兼容性更好 */
body::after{
  content:"";position:fixed;inset:0;z-index:-2;
  background:var(--wall) center/cover no-repeat;
  transform:translateZ(0);
}
body::before{
  content:"";position:fixed;inset:0;z-index:-1;
  background:var(--overlay);
  pointer-events:none;
}
.wrap{position:relative;z-index:1;max-width:700px;margin:0 auto;padding:0 10px}

/* ============ Apple 式连续圆角 ============ */
.r-lg{border-radius:28px}
.r-md{border-radius:22px}
.r-sm{border-radius:16px}

/* ============ 玻璃：渐变反光版 ============ */
.glass{
  position:relative;
  background-color:transparent;
  backdrop-filter:blur(38px) saturate(180%);
  -webkit-backdrop-filter:blur(38px) saturate(180%);
  /* 四层：主渐变反光 + 高光斜切 + 顶部内亮 + 底部内暗 */
  background-image:
    linear-gradient(
      145deg,
      rgb(255 255 255 / .13) 0%,
      rgb(255 255 255 / .05) 38%,
      rgb(255 255 255 / .025) 62%,
      rgb(255 255 255 / .08) 100%
    ),
    linear-gradient(
      100deg,
      rgb(255 255 255 / .07) 0%,
      transparent 28%,
      transparent 72%,
      rgb(255 255 255 / .05) 100%
    );
  box-shadow:
    inset 0 1px 0 0 rgb(255 255 255 / .22),
    inset 0 -1px 0 0 rgb(0 0 0 / .12),
    inset 0 0 0 1px rgb(255 255 255 / .10),
    0 10px 34px -6px rgb(0 0 0 / .34),
    0 2px 8px -2px rgb(0 0 0 / .22);
  transition:
    transform .48s cubic-bezier(.34,1.7,.5,1),
    box-shadow .48s cubic-bezier(.34,1.7,.5,1),
    background-image .42s ease;
  will-change:transform;
}
.glass:hover{
  background-image:
    linear-gradient(
      145deg,
      rgb(255 255 255 / .16) 0%,
      rgb(255 255 255 / .07) 38%,
      rgb(255 255 255 / .035) 62%,
      rgb(255 255 255 / .10) 100%
    ),
    linear-gradient(
      100deg,
      rgb(255 255 255 / .11) 0%,
      transparent 28%,
      transparent 72%,
      rgb(255 255 255 / .08) 100%
    );
  box-shadow:
    inset 0 1px 0 0 rgb(255 255 255 / .32),
    inset 0 -1px 0 0 rgb(0 0 0 / .12),
    inset 0 0 0 1px rgb(255 255 255 / .16),
    0 22px 54px -10px rgb(0 0 0 / .46),
    0 4px 14px -2px rgb(0 0 0 / .28);
}

/* 渐变描边：1.5px 渐变边框 */
.glass::before{
  content:"";position:absolute;inset:0;border-radius:inherit;
  padding:1.5px;
  background:linear-gradient(
    145deg,
    rgb(255 255 255 / .55) 0%,
    rgb(255 255 255 / .18) 22%,
    rgb(255 255 255 / .04) 48%,
    rgb(255 255 255 / .08) 72%,
    rgb(255 255 255 / .38) 100%
  );
  -webkit-mask:
    linear-gradient(#fff 0 0) content-box,
    linear-gradient(#fff 0 0);
  -webkit-mask-composite:xor;
  mask:
    linear-gradient(#fff 0 0) content-box,
    linear-gradient(#fff 0 0);
  mask-composite:exclude;
  pointer-events:none;
  opacity:.95;
  transition:opacity .42s ease;
}
.glass:hover::before{opacity:1}

/* 斜向高光带：卡片上那道明显的渐变反光 */
.glass .sheen{
  position:absolute;inset:0;border-radius:inherit;overflow:hidden;
  pointer-events:none;
}
.glass .sheen::before{
  content:"";position:absolute;
  top:-60%;left:-40%;
  width:60%;height:220%;
  background:linear-gradient(
    100deg,
    transparent 0%,
    rgb(255 255 255 / .08) 30%,
    rgb(255 255 255 / .20) 50%,
    rgb(255 255 255 / .08) 70%,
    transparent 100%
  );
  transform:rotate(14deg);
  filter:blur(1px);
  transition:transform .9s cubic-bezier(.22,.61,.36,1),opacity .5s ease;
  opacity:.8;
}
.glass:hover .sheen::before{
  transform:rotate(14deg) translateX(190%);
  opacity:1;
}

/* ============ 头部 ============ */
header.hero{
  padding:38px 28px;text-align:center;margin-bottom:18px;
  --hero-scale:1.15;
  transform:translateZ(0);
  transition:
    transform .5s cubic-bezier(.34,1.7,.5,1),
    box-shadow .5s cubic-bezier(.34,1.7,.5,1);
  will-change:transform;
}
header.hero:hover{
  transform:translateY(-4px) scale(var(--hero-scale)) translateZ(0);
  z-index:20;
}
.kicker{
  font-size:10.5px;letter-spacing:.26em;text-transform:uppercase;
  font-weight:700;color:rgb(255 255 255 / .58);margin-bottom:13px;
}
header.hero h1{
  font-size:31px;font-weight:760;letter-spacing:-.7px;line-height:1.18;
  text-shadow:0 2px 18px rgb(0 0 0 / .42);
}
header.hero .sub{margin-top:11px;font-size:14px;color:rgb(255 255 255 / .66)}

/* ============ 日期条 ============ */
.dateline{
  padding:13px 20px;margin-bottom:22px;
  display:flex;justify-content:space-between;align-items:center;
  font-size:12.5px;color:rgb(255 255 255 / .72);
  font-variant-numeric:tabular-nums;
}
.dateline strong{font-weight:650;color:rgb(255 255 255 / .92)}

/* ============ 卡片 ============ */
.card{
  padding:24px 26px;margin-bottom:24px;
  opacity:0;
  /* 用独立的 translate 属性做入场位移，避免 animation 锁死 transform */
  translate:0 20px;
  animation:fadeUp .68s cubic-bezier(.22,.61,.36,1) forwards;
  transform:translateZ(0);
  backface-visibility:hidden;
  transition:
    transform .48s cubic-bezier(.34,1.7,.5,1),
    box-shadow .48s cubic-bezier(.34,1.7,.5,1),
    background-image .42s ease;
}
.card:nth-of-type(1){animation-delay:.06s}
.card:nth-of-type(2){animation-delay:.12s}
.card:nth-of-type(3){animation-delay:.18s}
.card:nth-of-type(4){animation-delay:.24s}
.card:nth-of-type(5){animation-delay:.30s}
.card:nth-of-type(6){animation-delay:.36s}
@keyframes fadeUp{
  from{opacity:0;translate:0 20px}
  to{opacity:1;translate:0 0}
}
.card:hover{
  transform:translateY(-10px) scale(1.045) translateZ(0);
  z-index:20;
}
/* 按下时轻微回弹 */
.card:active{transform:translateY(-5px) scale(1.01) translateZ(0);transition-duration:.1s}

/* 鼠标跟随高光 */
.card::after{
  content:"";position:absolute;inset:0;border-radius:inherit;
  background:radial-gradient(
    420px circle at var(--mx,50%) var(--my,0%),
    rgb(255 255 255 / .13),
    transparent 62%
  );
  opacity:0;transition:opacity .35s ease;pointer-events:none;
}
.card:hover::after{opacity:1}

.row{display:flex;align-items:center;gap:10px;margin-bottom:12px}
.idx{
  display:inline-flex;align-items:center;justify-content:center;
  min-width:27px;height:27px;padding:0 8px;border-radius:10px;
  background:linear-gradient(145deg,rgb(255 255 255 / .22),rgb(255 255 255 / .10));
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / .3),
    inset 0 0 0 1px rgb(255 255 255 / .14);
  font-size:11.5px;font-weight:750;font-variant-numeric:tabular-nums;
  letter-spacing:.02em;
}
.src{font-size:12px;font-weight:650;color:rgb(255 255 255 / .9)}
.time{
  margin-left:auto;font-size:11.5px;color:rgb(255 255 255 / .5);
  font-variant-numeric:tabular-nums;
}
.card h2{
  font-size:18px;font-weight:680;line-height:1.5;letter-spacing:-.25px;
  text-shadow:0 1px 12px rgb(0 0 0 / .32);
}
.card h2 a{
  color:#fff;text-decoration:none;
  /* 下划线用渐变，从左往右展开 */
  background-image:linear-gradient(
    90deg,
    rgb(255 255 255 / .85),
    rgb(255 255 255 / .45)
  );
  background-size:0% 1.5px;
  background-position:0 calc(100% - 1px);
  background-repeat:no-repeat;
  transition:background-size .38s cubic-bezier(.22,.61,.36,1);
  padding-bottom:2px;
}
.card h2 a:hover{background-size:100% 1.5px}
/* 键盘聚焦也能看到 */
.card h2 a:focus-visible{
  outline:none;background-size:100% 1.5px;
  box-shadow:0 0 0 3px rgb(255 255 255 / .28);border-radius:6px;
}
.card p.brief{
  margin-top:10px;font-size:14.5px;line-height:1.74;
  color:rgb(255 255 255 / .76);
}
.card p.why{
  margin-top:12px;padding:10px 15px;border-radius:13px;
  background:linear-gradient(135deg,rgb(255 255 255 / .13),rgb(255 255 255 / .06));
  box-shadow:inset 0 0 0 1px rgb(255 255 255 / .08);
  border-left:2px solid rgb(255 255 255 / .42);
  font-size:13.5px;line-height:1.66;color:rgb(255 255 255 / .9);
  font-style:italic;
}
.card .go{
  display:inline-flex;align-items:center;gap:5px;
  margin-top:15px;padding:7px 15px;border-radius:12px;
  font-size:12.5px;font-weight:650;color:rgb(255 255 255 / .78);
  text-decoration:none;
  background:linear-gradient(145deg,rgb(255 255 255 / .12),rgb(255 255 255 / .05));
  box-shadow:inset 0 0 0 1px rgb(255 255 255 / .10);
  transition:all .3s cubic-bezier(.22,.61,.36,1);
}
.card .go:hover{
  color:#fff;
  background:linear-gradient(145deg,rgb(255 255 255 / .22),rgb(255 255 255 / .10));
  box-shadow:
    inset 0 0 0 1px rgb(255 255 255 / .2),
    0 6px 18px -6px rgb(0 0 0 / .4);
  transform:translateY(-1px);
}
.card .go span{display:inline-block;transition:transform .3s cubic-bezier(.22,.61,.36,1)}
.card .go:hover span{transform:translateX(4px)}

/* ============ 空状态 ============ */
.empty{
  padding:64px 24px;text-align:center;
  font-size:14.5px;line-height:1.8;color:rgb(255 255 255 / .58);
}

/* ============ 页脚 ============ */
footer.site{
  padding:16px 22px;margin-top:28px;
  display:flex;justify-content:space-between;align-items:center;
  gap:12px;flex-wrap:wrap;
  font-size:12px;color:rgb(255 255 255 / .48);
}
footer.site a{color:rgb(255 255 255 / .62);text-decoration:none;transition:color .2s}
footer.site a:hover{color:#fff}

/* ============ 归档 ============ */
.back{
  display:inline-flex;align-items:center;gap:6px;
  margin:4px 0 20px;padding:8px 18px;
  font-size:13px;color:rgb(255 255 255 / .8);text-decoration:none;
  transition:all .3s cubic-bezier(.22,.61,.36,1);
}
.back:hover{color:#fff;transform:translateX(-4px)}
ul.arch{list-style:none}
ul.arch li{margin:0}
ul.arch a{
  display:flex;justify-content:space-between;align-items:center;
  padding:16px 20px;margin-bottom:14px;
  color:#fff;text-decoration:none;font-size:14.5px;
  font-variant-numeric:tabular-nums;
  transition:all .32s cubic-bezier(.22,.61,.36,1);
}
ul.arch a:hover{transform:translateX(6px) scale(1.008)}
ul.arch a:active{transform:translateX(2px) scale(.997)}
ul.arch .arrow{color:rgb(255 255 255 / .45);font-size:13px;
  transition:transform .32s cubic-bezier(.22,.61,.36,1)}
ul.arch a:hover .arrow{transform:translateX(4px);color:rgb(255 255 255 / .85)}

/* ============ 响应式 ============ */
@media(max-width:820px){
  header.hero{--hero-scale:1.06}
}
@media(max-width:600px){
  body{padding:30px 12px 56px;background-attachment:scroll}
  header.hero{padding:28px 20px}
  header.hero h1{font-size:24px}
  .card{padding:19px 19px}
  .card h2{font-size:16.5px}
  .r-lg{border-radius:22px}
  .r-md{border-radius:18px}
  .r-sm{border-radius:14px}
  footer.site{flex-direction:column;align-items:flex-start;gap:6px}
  /* 移动端禁用 hover 位移，避免误触 */
  .card:hover,.glass:hover,header.hero:hover{transform:none;z-index:auto}
  .card::after{display:none}
}
@media(prefers-reduced-motion:reduce){
  *{animation:none!important;transition:none!important}
  .card{opacity:1!important}
  .card:hover,.glass:hover,.back:hover,ul.arch a:hover{transform:none}
}
"""

JS = """
// 鼠标跟随高光：让玻璃卡片的光斑跟着指针走
(function(){
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  if (window.matchMedia('(hover: none)').matches) return;
  var cards = document.querySelectorAll('.card');
  cards.forEach(function(card){
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
    """2026-10-22 -> 10月22日 星期四"""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return date_str
    week = "一二三四五六日"[dt.weekday()]
    return f"{dt.month}月{dt.day}日 星期{week}"


def pick_wallpaper(date_str: str, site: dict) -> str:
    """按日期稳定轮换壁纸：同一天固定同一张，每天换一张。"""
    pool = site.get("wallpapers") or DEFAULT_POOL
    pool = [p for p in pool if (WALLPAPER_DIR / p).exists()]
    if not pool:
        return "night.jpg"
    # 用日期做种子，保证同一天不变、不同天不同
    seed = int(hashlib.md5(date_str.encode()).hexdigest()[:8], 16)
    return pool[seed % len(pool)]


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
                 depth: int = 0, wallpaper: str = "") -> str:
    prefix = "../" * depth
    wall = wallpaper or site.get("wallpaper") or "night.jpg"
    # 透明玻璃：只留极淡的压暗，让壁纸完整透出来
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
<meta name="description" content="{_esc(site.get('subtitle', ''))}">
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
    dest_walls = out_dir / "assets" / "wallpapers"
    dest_walls.mkdir(parents=True, exist_ok=True)
    if WALLPAPER_DIR.exists():
        for img in WALLPAPER_DIR.glob("*.jpg"):
            shutil.copyfile(img, dest_walls / img.name)


def write_site(items: list[Item], date_str: str, config: dict, out_dir: Path,
               archive: list[str] | None = None) -> Path:
    site = config.get("site", {})
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "archive").mkdir(exist_ok=True)
    _copy_assets(out_dir)
    wall = pick_wallpaper(date_str, site)

    body = f"""<header class="hero glass r-lg">
<p class="kicker">Daily Brief</p>
<h1>{_esc(site.get('title', '每日简报'))}</h1>
<p class="sub">{_esc(site.get('subtitle', ''))}</p>
</header>
<div class="dateline glass r-sm">
<strong>{_nice_date(date_str)}</strong><span>共 {len(items)} 条</span>
</div>
{_entries_html(items)}
<footer class="site glass r-sm">
<span>{_esc(site.get('title', ''))}</span>
<span><a href="archive/index.html">历史归档</a></span>
</footer>"""

    page = _render_page(f"{_nice_date(date_str)} · {site.get('title', '')}", body, site,
                        wallpaper=wall)
    index_path = out_dir / "index.html"
    index_path.write_text(page, encoding="utf-8")

    archive_body = f"""<header class="hero glass r-lg">
<p class="kicker">Archive</p>
<h1>{_esc(site.get('title', '每日简报'))}</h1>
<p class="sub">{_nice_date(date_str)} 的简报</p>
</header>
<a class="back glass r-sm" href="../index.html">← 返回最新</a>
{_entries_html(items)}"""
    archive_page = _render_page(
        f"{_nice_date(date_str)} · 归档 · {site.get('title', '')}", archive_body, site,
        extra_head='<meta name="robots" content="noindex">', depth=1, wallpaper=wall,
    )
    (out_dir / "archive" / f"{date_str}.html").write_text(archive_page, encoding="utf-8")
    return index_path


def write_archive_index(out_dir: Path, site: dict) -> None:
    archive_dir = out_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    dates = sorted((p.stem for p in archive_dir.glob("*.html") if p.stem != "index"), reverse=True)

    if dates:
        rows = "\n".join(
            f'<li><a class="glass r-sm" href="{d}.html"><span>{_nice_date(d)}</span>'
            f'<span class="arrow">→</span></a></li>'
            for d in dates
        )
        listing = f'<ul class="arch">{rows}</ul>'
    else:
        listing = '<div class="empty glass r-md">还没有归档。</div>'

    body = f"""<header class="hero glass r-lg">
<p class="kicker">Archive</p>
<h1>历史归档</h1>
<p class="sub">共 {len(dates)} 期</p>
</header>
<a class="back glass r-sm" href="../index.html">← 返回最新</a>
{listing}"""
    today = dates[0] if dates else datetime.now().strftime("%Y-%m-%d")
    page = _render_page(f"历史归档 · {site.get('title', '')}", body, site,
                        extra_head='<meta name="robots" content="noindex">', depth=1,
                        wallpaper=pick_wallpaper(today, site))
    (archive_dir / "index.html").write_text(page, encoding="utf-8")


def write_index_json(archive_dir: Path, out_dir: Path) -> None:
    dates = sorted((p.stem for p in archive_dir.glob("*.html") if p.stem != "index"), reverse=True)
    (out_dir / "dates.json").write_text(
        json.dumps(dates, ensure_ascii=False, indent=2), encoding="utf-8"
    )
