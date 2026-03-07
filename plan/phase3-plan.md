# Phase 3 Plan — GitHub Section (Standalone) + HF Section (Standalone)

## 1. 原则

- GitHub 与 Hugging Face 永久分离，分别是独立 section。
- GitHub 列表顺序严格使用 Trending 原始排名，不做自定义重排。
- 保留 GitHub scorer，但仅用于计算 `star score` 和统计展示，不用于排序。
- 去重只在爬虫接入阶段做最小化输入去重（防解析异常重复）；不做持久化去重，不做跨运行去重。
- 最终统一一次渲染与一次 publish。

## 2. GitHub 目标

- 数据源：`https://github.com/trending?since=daily`
- 按页面顺序生成 `rank`，并按 `rank` 截断 Top-N。
- Top-N 再执行 README 拉取与摘要生成。
- 页面展示支持：排名、stars、stars today、star score、summary。

## 3. GitHub 流水线

`collect trending -> normalize -> input-dedup(minimal) -> select top_items(by rank) -> compute star score -> fetch readme -> summarize -> render payload`

约束：
- `rank` 只来自 Trending 页面顺序（1..N）。
- `compute star score` 仅写入 `signals` 与 section stats，不改变顺序。
- `input-dedup(minimal)` 仅处理同次抓取内的明显重复（同 repo 重复项），不引入持久化唯一键策略。
- 单条失败隔离，不影响其余条目。

## 4. GitHub 数据契约

每条 item 至少包含：
- `section="github"`
- `source="github_trending"`
- `source_id="owner/repo"`
- `url`
- `summary_raw`（trending description）
- `signals.rank`
- `signals.language`
- `signals.stars_today`
- `signals.stars`（total stars）
- `signals.score`（由 scorer 计算的 star score）
- `signals.readme_text`（可选）

section stats 至少包含：
- `item_count`
- `unique_count`
- `selected_count`
- `published_count`
- `selected_stars_total`
- `selected_stars_today_total`
- `failures`

去重边界：
- 仅限当前抓取批次（in-memory）内处理重复 repo。
- 数据库存储不依赖 dedup 作为业务语义约束。

## 5. HF 边界（本阶段）

- HF 仅定义边界，不与 GitHub 复用榜单或排序逻辑。
- HF 后续独立实现 plugin/scorer/pipeline/summarizer。

## 6. 运行与发布

- section 顺序：`news -> arxiv -> github -> huggingface`
- 每个 section 各自产出 payload。
- 全部 section 完成后统一 publish。

## 7. 鲁棒性

- Trending 抓取失败：GitHub section 返回空并记录失败，不中断全局。
- README 抓取失败：回退 `summary_raw`，继续流程。
- 同日重跑幂等：覆盖同一路径输出，不重复累积脏数据。

## 8. 验收（DoD）

- GitHub 最终展示顺序与 Trending 顺序一致。
- scorer 已执行并能看到 `signals.score`，但排序结果不受其影响。
- Top-N 在 summary 前截断（先 top，再 summary）。
- 页面可展示 stars 相关信息与摘要。
- HF 仍为独立 section 边界。
