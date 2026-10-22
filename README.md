# 每日简报

RSS 聚合 + AI 摘要 + 静态站点，每天由 GitHub Actions 自动生成并发布到 GitHub Pages。

## 特点

- **零依赖**：只用 Python 标准库，不需要 `pip install`，Actions 跑得又快又稳
- **零成本**：GitHub Actions + Pages 免费额度足够
- **可回退**：AI 挂了自动降级为原文首句，流程不会中断
- **好维护**：加信源、改关键词只改 `config.json`，不动代码

## 目录

```
daily-brief/
├── config.json              # 唯一需要改的文件：信源、关键词、条数
├── src/
│   ├── feed.py              # RSS/Atom 抓取解析
│   ├── dedupe.py            # 三层去重
│   ├── rank.py              # 打分排序
│   ├── summarize.py         # AI 摘要（带降级）
│   ├── render.py            # 生成网页
│   └── main.py              # 主流程
├── docs/                    # 生成的站点（GitHub Pages 从这里发布）
├── digests/                 # Markdown 归档
├── data/seen.json           # 去重指纹缓存
└── .github/workflows/daily.yml
```

## 本地运行

```bash
python -m src.main --dry-run    # 跑一遍，不动缓存
python -m src.main              # 正式跑
```

需要 AI 摘要时，把 `.env.example` 复制成 `.env` 并填 key；不填也能跑，只是摘要会退化成原文首句。

## 部署到 GitHub Pages

1. 新建一个**公开**仓库，把本目录所有文件推上去
2. `Settings → Pages → Source` 选 **GitHub Actions**
3. `Settings → Secrets and variables → Actions → New repository secret`
   - `LLM_API_KEY`：DeepSeek 的 key（可选，不填则用降级摘要）
4. 到 `Actions` 页点 `Daily Brief → Run workflow` 手动跑一次
5. 完成后访问 `https://你的用户名.github.io/仓库名/`

## 配置说明

`config.json` 里主要改这几块：

- `sources`：信源列表，`weight` 越大越容易入选
- `keywords.boost`：命中加分的词
- `keywords.mute`：命中直接丢弃的词
- `keywords.must`：非空时，只保留命中的（谨慎使用，容易一条都不剩）
- `output.top_n`：每天推几条
- `output.window_hours`：只看最近多少小时

## 定时

`.github/workflows/daily.yml` 里默认 `30 23 * * *`（UTC），即**北京时间每天 07:30**。
GitHub 定时任务可能延迟十几分钟到一小时，属正常现象。

## 免责

只抓取公开 RSS 的标题与摘要，正文一律跳转原文链接。
