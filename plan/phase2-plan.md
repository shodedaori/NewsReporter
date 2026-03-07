# Phase 2 Plan (arXiv) — Section-Isolated Pipeline

## 1. 目标与边界

### 目标
- 采集最近 24 小时 arXiv 论文（按配置的关键词/分类）。
- 在 `arxiv` section 内独立完成：标准化、去重、打分、摘要、渲染 payload。
- 合并到每日页面的 arXiv 板块，并保持全局一次 publish。

### 边界
- 不引入 Telegram 机器人流程（Phase 2 只做站内 digest）。
- 不做复杂个性化训练闭环（先留扩展位）。
- 不影响 `news` 评分和排序。

## 2. 参考 arXiv_recbot 的可复用点

来自 `yuandong-tian/arXiv_recbot` 的借鉴（做静态站适配）：
- arXiv API 查询使用关键词 `OR` 组合，按提交时间倒序拉取。
- 首次运行支持回看窗口（类似 backcheck day）。
- 先筛候选再排序，最后只保留 Top-K。
- 预留偏好模型升级路径（后续 Phase 2.x/3 可接入）。

## 3. Phase 2 最小可用架构

arXiv section 流水线：
`collect -> normalize -> score -> select top_items -> summarize -> render payload`

模块与职责：
- `sections/arxiv/plugins/arxiv.py`
  - 基于 arXiv API 拉取候选论文（关键词 OR + 可选 category filter）。
  - 单源失败隔离，超时/重试/退避。
- `sections/arxiv/scorer.py`
  - 解释性打分（见第 4 节）。
- `sections/arxiv/pipeline.py`
  - 仅处理 `arxiv` section，不直接 publish。
  - 输出 `SectionResult(section="arxiv", items, stats, generated_at)`。
- `app/main.py` + `core/pipeline.py`（orchestrator）
  - 执行顺序：`news -> arxiv -> github -> huggingface`（未实现 section 返回空）。
  - 聚合 section payload 后统一渲染并一次 publish。

## 4. arXiv 打分策略（简洁可解释）

Phase 2 使用线性可解释分：

```text
score = freshness_score + topic_match_score + category_bonus
```

建议实现：
- `freshness_score`：按更新时间 24h 内线性衰减。
- `topic_match_score`：标题+摘要命中关键词的加分。
- `category_bonus`：配置中的核心分类（如 `cs.LG`, `cs.AI`）额外加分。

约束：
- 仅在 `arxiv` section 内比较分数。
- 不与 `news` 混排、不做跨 section 归一化。

## 5. 配置与数据契约

新增/完善配置（`configs/sources.yaml`）：
- `arxiv.keywords`（列表）
- `arxiv.categories`（列表）
- `arxiv.max_results`
- `arxiv.backcheck_days`（首次回看窗口）

`Item`（arXiv）规范：
- `section="arxiv"`
- `source="arxiv"`
- `source_id` = arXiv id
- `url` = arXiv abs 链接
- `published_at` / `updated_at` 取可用字段
- `dedup_key = sha256(f"{section}|{source}|{source_id_or_url}")`

## 6. 输出与发布约束

输出路径不变：
- `output/site/index.html`
- `output/site/daily/YYYY-MM-DD/index.html`

发布顺序（不变）：
1. 顺序运行 section pipelines（含 arXiv）
2. 聚合 daily 数据（News + arXiv）
3. 渲染 daily 与 homepage
4. 全局一次原子 publish
5. 标记 digest 已发布

## 7. 测试与验收（DoD）

最小测试集：
- arXiv 插件冒烟测试（查询、字段映射、失败隔离）。
- arXiv 去重测试（同 id / 同 URL）。
- arXiv 评分测试（freshness/topic/category 贡献可解释）。
- 聚合渲染测试（daily 页面出现 arXiv section）。
- 同日重跑幂等测试（无重复发布条目）。

Phase 2 完成判定：
- `arxiv` section 本地可运行、可 dry-run。
- 页面可见 arXiv 板块且排序稳定。
- 不影响 `news` section 结果。
- 全局仍为一次 publish，rerun 安全。
