# 每日简报

个人向的多板块资讯简报：RSS 聚合 → 去重排序 → AI 摘要 → 静态站点 → 每日自动发布。

**线上地址**：https://socialismpeople.github.io/daily-brief/

## 板块

| 板块 | 定位 | 信源 |
|---|---|---|
| 科技 | AI、开源、产品与前沿 | 12 个（HN / TechCrunch / 少数派 / 极客公园等） |
| 国际 | 社会运动、劳工与变革 | 14 个（Common Dreams / Electronic Intifada / France24 等） |
| 科普 | 科学发现与自然世界 | 10 个（Quanta / ScienceDaily / NASA 等） |
| 经济 | 宏观、市场与商业 | 8 个（CNBC / Fortune / 界面新闻等） |

## 特性

- **纯标准库**：不依赖任何第三方包，无需 `pip install`，Actions 跑得又快又稳
- **三层去重**：URL 归一化 → 标题指纹 → 相似度聚类，同一事件多家转载只留一条
- **AI 摘要可选**：配了 key 用 DeepSeek 生成一句话摘要 + 为什么值得看；没配则自动降级为原文首句
- **失败不中断**：任何单个信源失败只跳过该源，不影响其他板块
- **壁纸每日轮换**：按日期哈希从图池选一张，同一天固定不变
- **副标题每日轮换**：毛主席词句，12 句轮换
- **归档按日期分目录**：`archive/2026-10-23/tech.html`，历史内容不覆盖

## 目录结构

```
daily-brief/
├── config.json               # 唯一需要改的文件：板块、信源、关键词
├── src/
│   ├── config.py             # 配置与环境变量加载
│   ├── feed.py               # RSS/Atom 抓取与解析
│   ├── dedupe.py             # 三层去重
│   ├── rank.py               # 打分排序（权重 + 时间衰减 + 关键词）
│   ├── summarize.py          # AI 摘要（带降级）
│   ├── render.py             # 生成静态站点
│   └── main.py               # 主流程编排
├── assets/
│   ├── fonts/xingkai.woff2   # 华文行楷子集（37KB，仅含站点用字）
│   └── wallpapers/           # 12 张壁纸
├── docs/                     # 生成的站点（GitHub Pages 从这里发布）
├── digests/                  # Markdown 归档
└── .github/workflows/daily.yml
```

## 本地运行

```bash
python -m src.main --dry-run    # 跑一遍，不更新去重缓存
python -m src.main              # 正式跑
```

需要 AI 摘要时，把 `.env.example` 复制成 `.env` 并填 `LLM_API_KEY`。

## 部署

1. 推到 GitHub 公开仓库
2. `Settings → Pages → Source` 选 **GitHub Actions**
3. `Settings → Secrets → Actions` 添加 `LLM_API_KEY`（可选）
4. `Actions → Daily Brief → Run workflow`

## 配置说明

`config.json` 主要字段：

- `sections[].sources`：信源列表，`weight` 越大越容易入选
- `sections[].window_hours`：该板块的时间窗口（国际板块设为 336 小时，因为部分源更新慢）
- `keywords.boost`：命中加分的词
- `keywords.mute`：命中直接丢弃的词
- `output.top_n`：每板块推几条
- `output.max_per_source`：单一来源最多几条
- `site.wallpapers`：壁纸池
- `site.subtitle_rotation`：副标题词句池

## 定时

`.github/workflows/daily.yml` 默认 `30 23 * * *`（UTC），即**北京时间每天 07:30**。
GitHub 定时任务可能延迟十几分钟到一小时，属正常现象。

## 说明

只抓取公开 RSS 的标题与摘要，正文一律跳转原文链接。
壁纸来自 Unsplash（Unsplash License）与个人 Wallpaper Engine 收藏预览图，仅本地个人使用。
