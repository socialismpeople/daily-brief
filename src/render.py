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

# 兜底：config.json 缺失对应字段时使用
FALLBACK_WALLPAPER = "night.jpg"
FALLBACK_SUBTITLE = "雄关漫道真如铁，而今迈步从头越"

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
    linear-gradient(145deg,rgb(20 22 34/.34) 0%,rgb(20 22 34/.22) 40%,
      rgb(20 22 34/.26) 65%,rgb(20 22 34/.38) 100%),
    linear-gradient(145deg,rgb(255 255 255/.11) 0%,rgb(255 255 255/.04) 38%,
      rgb(255 255 255/.02) 62%,rgb(255 255 255/.07) 100%);
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
    linear-gradient(145deg,rgb(20 22 34/.26) 0%,rgb(20 22 34/.16) 40%,
      rgb(20 22 34/.20) 65%,rgb(20 22 34/.30) 100%),
    linear-gradient(145deg,rgb(255 255 255/.16) 0%,rgb(255 255 255/.07) 38%,
      rgb(255 255 255/.035) 62%,rgb(255 255 255/.10) 100%);
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

/* ============ 毛笔字体 ============ */
@font-face{
  font-family:"XingKai";
  src:url("assets/fonts/xingkai.woff2") format("woff2");
  font-weight:400;font-style:normal;font-display:swap;
}
.brush{
  font-family:"XingKai","STXingkai","华文行楷",
    "Kaiti SC","STKaiti",serif;
  font-weight:400;
}

/* 页头：无玻璃框，直接压在壁纸上 */
header.hero{
  position:relative;
  padding:52px 20px 46px;text-align:center;margin-bottom:8px;
}
.kicker{
  font-size:10.5px;letter-spacing:.34em;text-transform:uppercase;
  font-weight:600;color:rgb(255 255 255/.5);margin-bottom:20px;
}
header.hero h1{
  font-family:"XingKai","STXingkai","华文行楷","Kaiti SC",serif;
  font-size:76px;font-weight:400;letter-spacing:.04em;line-height:1.08;
  color:#fff;
  text-shadow:
    0 2px 28px rgb(0 0 0/.55),
    0 1px 3px rgb(0 0 0/.4);
}
header.hero .sub{
  margin-top:22px;font-size:18px;line-height:1.8;
  color:rgb(255 255 255/.72);font-weight:400;letter-spacing:.08em;
  font-family:"Kaiti SC","STKaiti","XingKai",serif;
  text-shadow:0 1px 12px rgb(0 0 0/.5);
}
/* 词句上方一道细装饰线 */
header.hero .sub::before{
  content:"";display:block;width:44px;height:1px;margin:0 auto 18px;
  background:linear-gradient(90deg,transparent,rgb(255 255 255/.4),transparent);
}

/* ============ 板块：主次编排 ============ */
.sections{
  display:flex;
  flex-direction:column;
  gap:12px;
  margin-bottom:24px;
}
/* 第一个板块横跨两列，做主角 */
.section-card{
  position:relative;display:flex;flex-direction:column;
  padding:26px 26px 22px;text-decoration:none;color:#fff;
  transform:translateZ(0);
  overflow:hidden;
}
.section-card:nth-child(1){
  padding:30px 28px 26px;
  animation-delay:.05s;
}
.section-card:hover{transform:translateY(-5px) scale(1.015) translateZ(0);z-index:20}
.section-card:active{transform:translateY(-2px) scale(1.004) translateZ(0)}

/* 板块序号：左上角很淡的编号 */
.sec-no{
  position:absolute;top:14px;right:20px;
  font-family:"XingKai",serif;font-size:44px;line-height:1;
  color:rgb(255 255 255/.10);
  pointer-events:none;user-select:none;
}
.sec-head{display:flex;align-items:baseline;gap:12px;margin-bottom:9px}
.sec-name{
  font-family:"XingKai","STXingkai","华文行楷",serif;
  font-size:34px;font-weight:400;letter-spacing:.06em;line-height:1.1;
  text-shadow:0 2px 16px rgb(0 0 0/.45);
}
.section-card:not(:first-child) .sec-name{font-size:29px}
.sec-count{
  font-size:12.5px;color:rgb(255 255 255/.45);
  font-variant-numeric:tabular-nums;letter-spacing:.04em;
}
.sec-desc{
  font-size:13.5px;color:rgb(255 255 255/.55);line-height:1.55;
  letter-spacing:.02em;
}
/* 预览列表：默认收起，悬停展开 */
.sec-preview{
  max-height:0;overflow:hidden;
  margin-top:0;padding-top:0;border-top:0;
  font-size:14.5px;color:rgb(255 255 255/.7);line-height:1.7;
  opacity:0;
  transition:
    max-height .5s cubic-bezier(.34,1.4,.5,1),
    margin-top .4s ease,
    padding-top .4s ease,
    opacity .35s ease;
}
.section-card:hover .sec-preview{
  max-height:220px;
  margin-top:18px;padding-top:16px;
  border-top:1px solid rgb(255 255 255/.09);
  opacity:1;
}
.sec-preview li{
  list-style:none;margin-bottom:9px;padding-left:16px;position:relative;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
}
.sec-preview li:last-child{margin-bottom:0}
.sec-preview li::before{
  content:"";position:absolute;left:0;top:.72em;
  width:6px;height:1px;background:rgb(255 255 255/.32);
}

/* 进入箭头 */
.sec-arrow{
  display:inline-flex;align-items:center;gap:7px;margin-top:16px;
  font-size:12.5px;font-weight:600;color:rgb(255 255 255/.5);
  letter-spacing:.08em;
  transition:color .25s ease,gap .32s cubic-bezier(.34,1.7,.5,1);
}
.sec-arrow span{
  display:inline-block;transition:transform .32s cubic-bezier(.34,1.7,.5,1);
}
.section-card:hover .sec-arrow{color:rgb(255 255 255/.9);gap:11px}
.section-card:hover .sec-arrow span{transform:translateX(3px)}

/* 条目 */
.card{
  padding:24px 26px;margin-bottom:24px;
  transform:translateZ(0);backface-visibility:hidden;
}
@keyframes fadeUp{from{opacity:0;translate:0 16px}to{opacity:1;translate:0 0}}
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
  font-size:13px;font-weight:750;font-variant-numeric:tabular-nums;
}
.src{font-size:14px;font-weight:650;color:rgb(255 255 255/.9)}
.time{margin-left:auto;font-size:13px;color:rgb(255 255 255/.5);
  font-variant-numeric:tabular-nums}
.card h2{
  font-size:21px;font-weight:680;line-height:1.48;letter-spacing:-.3px;
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
.card p.brief{margin-top:11px;font-size:16.5px;line-height:1.76;color:rgb(255 255 255/.76)}
.card p.why{
  margin-top:12px;padding:10px 15px;border-radius:13px;
  background:linear-gradient(135deg,rgb(255 255 255/.13),rgb(255 255 255/.06));
  box-shadow:inset 0 0 0 1px rgb(255 255 255/.08);
  border-left:2px solid rgb(255 255 255/.42);
  font-size:15.5px;line-height:1.7;color:rgb(255 255 255/.9);font-style:italic;
}
.card .go{
  display:inline-flex;align-items:center;gap:5px;margin-top:15px;padding:7px 15px;
  border-radius:12px;font-size:14px;font-weight:650;color:rgb(255 255 255/.78);
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

.empty{padding:64px 24px;text-align:center;font-size:16.5px;line-height:1.8;
  color:rgb(255 255 255/.58)}

footer.site{
  padding:16px 22px;margin-top:28px;
  display:flex;justify-content:space-between;align-items:center;
  gap:12px;flex-wrap:wrap;font-size:13.5px;color:rgb(255 255 255/.48);
}
footer.site a{color:rgb(255 255 255/.62);text-decoration:none;transition:color .2s}
footer.site a:hover{color:#fff}

/* 返回与归档 */
.back{
  display:inline-flex;align-items:center;gap:6px;margin:4px 0 20px;padding:8px 18px;
  font-size:15px;color:rgb(255 255 255/.8);text-decoration:none;
  transition:all .3s cubic-bezier(.22,.61,.36,1);
}
.back:hover{color:#fff;transform:translateX(-4px)}
ul.arch{list-style:none}
ul.arch a{
  display:flex;justify-content:space-between;align-items:center;
  padding:16px 20px;margin-bottom:14px;color:#fff;text-decoration:none;
  font-size:16.5px;font-variant-numeric:tabular-nums;
  transition:all .32s cubic-bezier(.22,.61,.36,1);
}
ul.arch a:hover{transform:translateX(6px) scale(1.008)}
ul.arch .arrow{color:rgb(255 255 255/.45);font-size:13px;transition:transform .32s}
ul.arch a:hover .arrow{transform:translateX(4px);color:rgb(255 255 255/.85)}

/* 归档：按日期分组 */
.arch-day{
  display:flex;align-items:center;gap:14px;flex-wrap:wrap;
  padding:16px 20px;margin-bottom:12px;
  background:rgb(20 22 34/.30);
  border-radius:16px;
  box-shadow:inset 0 0 0 1px rgb(255 255 255/.08);
}
.arch-date{
  font-family:"XingKai","STXingkai",serif;
  font-size:21px;color:#fff;letter-spacing:.04em;
  flex:none;
}
.arch-links{display:flex;gap:8px;flex-wrap:wrap;margin-left:auto}
.arch-sub{
  display:inline-block;padding:5px 13px;border-radius:10px;
  font-size:13px;font-weight:600;color:rgb(255 255 255/.75);
  text-decoration:none;background:rgb(255 255 255/.08);
  box-shadow:inset 0 0 0 1px rgb(255 255 255/.10);
  transition:all .26s cubic-bezier(.34,1.7,.5,1);
}
.arch-sub:hover{
  color:#fff;background:rgb(255 255 255/.18);
  transform:translateY(-2px);
}

/* 板块页导航 */
.tabs{
  display:flex;gap:8px;margin-bottom:20px;padding:8px;flex-wrap:wrap;
  justify-content:center;
}
.tab{
  padding:7px 16px;border-radius:12px;font-size:15px;font-weight:600;
  color:rgb(255 255 255/.65);text-decoration:none;
  transition:all .28s cubic-bezier(.34,1.7,.5,1);
}
.tab:hover{color:#fff;background:rgb(255 255 255/.1)}
.tab.active{
  color:#fff;background:rgb(255 255 255/.18);
  box-shadow:inset 0 0 0 1px rgb(255 255 255/.22);
}

/* ============ 响应式 ============ */
/* 平板 */
@media(max-width:820px){
  .wrap{padding:0 14px}
}

/* 手机 */
@media(max-width:600px){
  body{padding:26px 10px 48px}

  /* 页头：毛笔字缩小但保持气势 */
  header.hero{padding:32px 10px 28px}
  header.hero h1{font-size:54px;letter-spacing:.02em}
  header.hero .sub{font-size:15px;margin-top:14px;line-height:1.7}
  header.hero .sub::before{width:36px;margin-bottom:14px}
  .kicker{font-size:9.5px;letter-spacing:.28em;margin-bottom:16px}

  /* 板块卡：单列、紧凑 */
  .sections{gap:10px;margin-bottom:18px}
  .section-card{padding:20px 18px 16px}
  .section-card:nth-child(1){padding:22px 18px 18px}
  .sec-name{font-size:28px}
  .section-card:not(:first-child) .sec-name{font-size:25px}
  .sec-count{font-size:11.5px}
  .sec-desc{font-size:13px}
  .sec-no{font-size:34px;top:10px;right:14px}
  .sec-preview{margin-top:14px;padding-top:12px;font-size:13.5px;line-height:1.65}
  .sec-preview li{margin-bottom:7px;padding-left:14px}
  .sec-arrow{font-size:12px;margin-top:12px}

  /* 条目卡 */
  .card{padding:18px 17px;margin-bottom:14px}
  .card h2{font-size:17.5px;line-height:1.5}
  .card p.brief{font-size:15px;margin-top:9px;line-height:1.7}
  .card p.why{font-size:14px;margin-top:10px;padding:9px 12px}
  .card .go{font-size:13px;margin-top:12px;padding:6px 13px}
  .row{margin-bottom:10px}
  .idx{min-width:24px;height:24px;font-size:12px}
  .src{font-size:13px}
  .time{font-size:12px}

  /* 圆角略收 */
  .r-lg{border-radius:22px}
  .r-md{border-radius:18px}
  .r-sm{border-radius:14px}

  /* 导航标签：可横向滑动 */
  .tabs{
    padding:6px;gap:5px;flex-wrap:nowrap;overflow-x:auto;
    justify-content:flex-start;
    -webkit-overflow-scrolling:touch;scrollbar-width:none;
    margin-bottom:16px;
  }
  .tabs::-webkit-scrollbar{display:none}
  .tab{padding:6px 13px;font-size:13.5px;flex:none}

  /* 页脚 */
  footer.site{
    flex-direction:row;justify-content:space-between;align-items:center;
    font-size:12.5px;padding:14px 16px;
  }

  /* 返回 / 归档 */
  .back{font-size:13.5px;padding:7px 15px;margin-bottom:16px}
  ul.arch a{padding:14px 16px;margin-bottom:11px;font-size:14.5px}
  .empty{padding:48px 18px;font-size:15px}

  /* 移动端关闭 hover 位移与跟随高光 */
  .card:hover,.glass:hover,.section-card:hover{transform:none;z-index:auto}
  .card::after{display:none}
}

/* 超小屏（iPhone SE 等） */
@media(max-width:380px){
  header.hero h1{font-size:44px}
  header.hero .sub{font-size:13.5px}
  .sec-name{font-size:25px}
  .section-card:not(:first-child) .sec-name{font-size:23px}
  .card h2{font-size:16px}
  .card p.brief{font-size:14.5px}
}

/* 横屏手机 */
@media(max-width:900px) and (orientation:landscape) and (max-height:500px){
  body{padding:20px 12px 32px}
  header.hero{padding:20px 10px}
  header.hero h1{font-size:38px}
  header.hero .sub{font-size:13px;margin-top:8px}
  header.hero .sub::before{display:none}
}

/* 减少动画 */

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
    """按日期稳定轮换壁纸：同一天固定同一张，每天换一张。"""
    pool = site.get("wallpapers") or []
    pool = [p for p in pool if (WALLPAPER_DIR / p).exists()]
    if not pool:
        return FALLBACK_WALLPAPER
    return pool[_seed(date_str) % len(pool)]


def pick_subtitle(date_str: str, site: dict) -> str:
    """按日期稳定轮换副标题（毛主席词句）。"""
    pool = site.get("subtitle_rotation") or []
    if not pool:
        return FALLBACK_SUBTITLE
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
    # 字体
    font_src = ASSETS_SRC / "fonts"
    font_dest = out_dir / "assets" / "fonts"
    if font_src.exists():
        font_dest.mkdir(parents=True, exist_ok=True)
        for f in font_src.glob("*.woff2"):
            shutil.copyfile(f, font_dest / f.name)


def _tabs(sections: list[dict], active: str, depth: int = 0) -> str:
    prefix = "../" * depth
    parts = [f'<a class="tab" href="{prefix}index.html">首页</a>']
    for s in sections:
        sid = s.get("id")
        cls = "tab active" if sid == active else "tab"
        parts.append(
            f'<a class="{cls}" href="{prefix}{sid}.html">'
            f'{_esc(s.get("name", sid))}</a>'
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
        idx_no = f"{sections.index(s) + 1:02d}"
        cards.append(f"""<a class="glass section-card r-md" href="{sid}.html">
<div class="sheen"></div>
<span class="sec-no">{idx_no}</span>
<div class="sec-head">
<span class="sec-name">{_esc(s.get('name', sid))}</span>
<span class="sec-count">{len(items)} 条</span>
</div>
<p class="sec-desc">{_esc(s.get('desc', ''))}</p>
<ul class="sec-preview">{preview}</ul>
<span class="sec-arrow">进入 <span>→</span></span>
</a>""")

    home_body = f"""<header class="hero">
<p class="kicker">Daily Brief</p>
<h1 class="brush">{_esc(title)}</h1>
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
        body = f"""<header class="hero">
<p class="kicker">Daily Brief</p>
<h1 class="brush">{_esc(name)}</h1>
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

        # 板块归档页：按日期分目录，避免每天覆盖
        arch_dir = out_dir / "archive" / date_str
        arch_dir.mkdir(parents=True, exist_ok=True)
        arch_body = f"""<header class="hero">
<p class="kicker">Archive</p>
<h1 class="brush">{_nice_date(date_str)}</h1>
<p class="sub">{_esc(subtitle)}</p>
</header>
<a class="back glass r-sm" href="../../{sid}.html">← 返回{_esc(name)}</a>
{_tabs(sections, sid, depth=2)}
{_entries_html(items)}"""
        (arch_dir / f"{sid}.html").write_text(
            _render_page(f"{name} · 归档 · {_nice_date(date_str)}", arch_body, site,
                         extra_head='<meta name="robots" content="noindex">',
                         depth=2, wallpaper=wall),
            encoding="utf-8",
        )

    # ---------- 归档索引：按日期分组 ----------
    dates = _all_archive_dates(out_dir)
    day_blocks = []
    for d in dates:
        links = "".join(
            f'<a class="arch-sub" href="{d}/{s.get("id")}.html">'
            f'{_esc(s.get("name", ""))}</a>'
            for s in sections
            if (out_dir / "archive" / d / f"{s.get('id')}.html").exists()
        )
        day_blocks.append(
            f'<li class="arch-day">'
            f'<span class="arch-date">{_nice_date(d)}</span>'
            f'<span class="arch-links">{links}</span>'
            f'</li>'
        )

    arch_body = f"""<header class="hero">
<p class="kicker">Archive</p>
<h1 class="brush">历史归档</h1>
<p class="sub">共 {len(dates)} 期</p>
</header>
<a class="back glass r-sm" href="../index.html">← 返回首页</a>
<ul class="arch">{''.join(day_blocks) or '<li class="arch-day"><span>暂无归档</span></li>'}</ul>"""
    (out_dir / "archive" / "index.html").write_text(
        _render_page("历史归档", arch_body, site,
                     extra_head='<meta name="robots" content="noindex">',
                     depth=1, wallpaper=wall),
        encoding="utf-8",
    )

    # 日期索引
    (out_dir / "dates.json").write_text(
        json.dumps(dates, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _all_archive_dates(out_dir: Path) -> list[str]:
    """扫描 archive/ 下所有 YYYY-MM-DD 目录，倒序返回。"""
    arch = out_dir / "archive"
    if not arch.exists():
        return []
    dates = [
        p.name for p in arch.iterdir()
        if p.is_dir() and len(p.name) == 10 and p.name[4] == "-" and p.name[7] == "-"
    ]
    return sorted(dates, reverse=True)
