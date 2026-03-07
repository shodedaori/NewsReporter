# Phase 4 Plan — Hugging Face Trending Section（Models + Datasets）

## 1. 目标与原则

- 新增独立 `hf` section（不与 GitHub/HF 其他模块合并）。
- 数据来源使用 Hugging Face 官方 `huggingface_hub.HfApi`。
- 排序严格遵循 HF 返回顺序（trending 顺序），不做本地重排。
- 只做“单次抓取输入去重”（in-memory），不做可持久化去重，不做跨运行去重。
- 保留 `HFScorer`：按 `default.yaml` 权重计算 score，仅用于展示/统计，不用于排序。

## 2. 数据获取策略（官方 API）

- Models：
  - `api.list_models(...)`
  - 主策略：`sort="trending_score"`，并开启 `cardData=True`（或新版本 `expand=["cardData"]`）。
- Datasets：
  - `api.list_datasets(...)`
  - 主策略：`sort="trending_score"`，并开启 `cardData=True`（或新版本 `expand=["cardData"]`）。
- 兼容回退：
  - 若 `trending_score` 在当前 hub 版本不可用，回退到 `likes`/`downloads` 等稳定排序并记录 warning。

## 3. Top 分配规则

- 设 `N = app.top_items`。
- `n_each = N // 2`。
- 展示条数：
  - Models：Top `n_each`
  - Datasets：Top `n_each`
- 补余数（即 `N` 为奇数时，最终展示 `2 * ((N + 1) // 2)` 条），保持规则简单确定。

## 4. HF 流水线

`collect(models+datasets) -> normalize -> input-dedup(minimal) -> top-split(by API order) -> compute score -> summarize -> render payload`

说明：
- `input-dedup(minimal)` 仅处理同次抓取内重复（同 `repo_id`）。
- `compute score` 只写入 `signals.score` 和 section stats，不影响排序。
- 先 Top 截断，再 summary（与现有 section 一致）。

## 5. 数据契约（HF Item）

每条 item 至少包含：
- `section="hf"`
- `source`：`hf_model_trending` 或 `hf_dataset_trending`
- `source_id`：`repo_id`（如 `org/name`）
- `url`
- `summary_raw`（来自 card/描述字段）
- `signals.kind`：`model` 或 `dataset`
- `signals.rank`：该子榜单原始名次
- `signals.likes_7d` / `signals.likes_total`（按可用字段填充）
- `signals.downloads`（按可用字段填充）
- `signals.tags`、`signals.pipeline_tag`、`signals.license`、`signals.language`（尽量填）
- `signals.score`（scorer 计算结果）

## 6. 配置与扩展

- `default.yaml`
  - 新增 `scoring.hf`（如 `likes_weight`、`downloads_weight`、`recency_weight` 等，默认可全 0）。
  - `top_items` 继续全局生效，由 HF 内部分半。
- `sources.yaml`
  - 新增 `hf` 配置（`limit`、`timeout`、`sort`、是否启用 `cardData/expand`）。
- `prompts.yaml`
  - 新增 `hf_llm_summary_system` / `hf_llm_summary_user`（结构与 news/github 对齐：TLDR + keypoints + takeaways）。

## 7. 鲁棒性要求

- models 拉取失败与 datasets 拉取失败相互隔离，单边失败不阻断另一边。
- 单条 item 解析失败隔离，不影响其余条目。
- summary 失败回退 extractive。
- section 失败返回空列表并记录 `failures`，不阻断全局渲染/发布。

## 8. 测试与验收（DoD）

- API 结果映射测试：models/datasets 都能正确落到统一 Item 契约。
- 顺序测试：输出顺序与 API 返回顺序一致（无重排）。
- Top 分配测试：严格执行 `(N + 1) // 2` + `(N + 1) // 2`。
- 去重测试：仅同批次重复去掉，不依赖持久化 dedup。
- scorer 测试：score 可计算并可展示，但不影响排序。
- 渲染测试：daily 页面出现 HF 独立板块，且 model/dataset 都可见。
