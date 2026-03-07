# Phase 1 Plan (News) — ButterCMS Blog Template

## 1. 目标与边界

### 目标
- 采集最近 24 小时公司新闻（RSS）。
- 统一结构、去重、打分、短摘要。
- 生成静态页面并发布到本地站点目录。
- 首页展示最新 digest，支持当日归档页。

### 边界
- 本阶段只做 `News`，不做 arXiv / GitHub / Hugging Face。
- 不引入 React/Next.js/Postgres/Redis/CMS。
- 保持 ButterCMS 模板响应式结构，不重做前端框架。

## 2. 模板落地策略（基于 ButterCMS/blog-template）

已确认模板核心文件：
- `index.html`
- `post.html`
- `styles/styles.css`（由 `styles.scss` 生成）

映射规则：
- `index.html` -> 我们的首页模板（最新 digest + 近期归档链接）。
- `post.html` -> 我们的每日 digest 页模板（当天 News 列表）。
- 保留现有主结构和 class 命名，优先替换内容区，不大改布局。
- 去掉与 Phase 1 无关的交互块（如订阅表单、评论脚本）或改为静态占位。

## 3. Phase 1 最小可用架构

固定流水线：
`collect -> normalize -> score -> summarize -> render -> publish`

模块与职责：
- `plugins/rss_news.py`
  - 按配置抓取 RSS，超时/重试/退避。
  - 输出统一 `Item` 结构并给出基础 `signals`。
- `core/pipeline.py`
  - 串联全流程，按日期窗口（24h）执行。
  - 单源失败不终止全局。
- `core/scorer.py`
  - 可解释打分：`freshness + keyword/company match + source_weight`。
- `core/summarizer.py`
  - 两级摘要：抽取优先，短 TL;DR 兜底；输入薄则输出薄。
- `core/store.py`（SQLite）
  - 最少落表：`items_canonical`、`daily_digest`、`runs`。
  - 打开 `WAL` 和 `synchronous=NORMAL`。
- `web/renderer.py`（Jinja2）
  - 渲染首页与每日页，输出到 `output/site/...`。
- `core/publisher.py`
  - 原子写入（临时文件 + replace）。
  - 同日重跑覆盖同一路径，不新增重复归档。

## 4. 配置与数据契约

必须配置化（禁止硬编码）：
- 公司列表、RSS 源、关键词、source 权重、发布时区/调度。

统一数据结构（Phase 1 必用）：
- `source`
- `source_id`
- `title`
- `url`
- `published_at`
- `summary_raw`
- `summary_short`
- `tags`
- `signals`
- `dedup_key`

`dedup_key`：
- `sha256(f"{source}|{source_id_or_url}")`
- 优先级：`source_id > url > title+published_at`

## 5. 输出与发布约束

输出路径固定：
- `output/site/index.html`
- `output/site/daily/YYYY-MM-DD/index.html`

发布顺序固定：
1. 生成当日 digest 数据
2. 渲染 daily 页
3. 渲染首页
4. 原子写文件
5. 标记 digest 已发布

幂等性：
- 同一天重复执行只更新同一输出，不产生重复条目或重复归档链接。

## 6. 命令与运行模式

建议命令：
- `python -m src.app.main --date YYYY-MM-DD --dry-run`
- `python -m src.app.main --date YYYY-MM-DD --publish`

要求：
- `dry-run` 完整跑采集/打分/摘要/渲染预览，但不覆盖正式发布目录。
- 调度先用 cron 的 daily 模式（每天一次）。

## 7. 测试与验收（DoD）

最小测试集：
- 去重逻辑测试（同源重复、跨源同链接）。
- 日 digest 生成测试（24h 窗口正确）。
- 模板渲染冒烟测试（首页/每日页可生成）。
- RSS 插件冒烟测试（超时、失败隔离）。
- 同日重跑幂等测试（不重复、不新增垃圾文件）。

Phase 1 完成判定：
- 本地可运行。
- 可 dry-run。
- 可稳定生成静态输出。
- 重跑安全（幂等）。
- 首页正确指向最新 digest。
- 当日归档页存在且可访问。
- 可被 Nginx 直接静态托管。

