# RULE.md — NewsReporter Vibe Coding Rules

> Goal: generate the latest 24-hour **news**, **arXiv**, **Hugging Face trending**, and **GitHub trending**, publish them to a **local static blog**, and distribute with **Nginx**.

## 0. Core Product Shape

We build a **daily static publishing system**, not a generic chatbot and not a CMS.

Lifecycle is fixed (per section):

`collect -> normalize -> score -> summarize -> render`

Execution model is fixed:
- each section has its own pipeline (`news`, `arxiv`, `github`, `huggingface`)
- run section pipelines sequentially
- aggregate section outputs into one daily static page + homepage
- publish once at the end (global publish), never per-section publish

Current frontend template base:

- use `ButterCMS/blog-template`
- keep its responsive HTML/CSS structure
- adapt it to our daily briefing pages
- do **not** fight the template on day 1

## 1. Three-Phase Delivery Plan

### Phase 1 — News
Target:
- collect latest 24h company news from RSS
- deduplicate
- generate short summaries
- render one daily page
- publish to blog

Output:
- homepage with latest digest
- archive page for the day

### Phase 2 — arXiv
Target:
- collect latest 24h papers from configured arXiv categories/topics
- define a simple, explainable trending score
- add arXiv section to daily digest

### Phase 3 — GitHub + Hugging Face
Target:
- define our own trending metrics
- compute scores from saved snapshots
- add GH / HF sections to daily digest

## 2. Non-Negotiables

1. **Static site first**
   - no WordPress
   - no runtime database-backed website
   - generated HTML is the product

2. **Section-isolated pipelines**
   - every section must go through the same lifecycle:
     - fetch
     - normalize
     - score
     - summarize
     - render
   - scoring/dedup/ranking are isolated by section
   - `news` and `arxiv` must not affect each other's scores

3. **Base class + subclass architecture**
   - define base abstractions for `Item`, `Scorer`, `Pipeline`, `SourcePlugin`
   - each section implements its own subclass
   - no section-specific hacks inside shared base logic

4. **Idempotent publishing**
   - rerunning the same date must update or overwrite the same digest
   - it must not create duplicate pages

5. **Configuration driven**
   - company list
   - RSS feeds
   - arXiv categories
   - GH/HF topics
   - publish schedule
   - scoring weights
   - all configurable, not hardcoded

6. **Simple first**
   - no React
   - no Next.js
   - no Postgres
   - no Redis
   - no admin panel
   - no feature theater

## 3. Tech Stack Rules

### Required stack
- Python
- SQLite
- Jinja2
- static HTML/CSS
- Nginx
- cron

### Template rule
Use `ButterCMS/blog-template` as the blog shell.

Adapt:
- `index.html` -> homepage
- `post.html` -> daily digest page

Do not rebuild a new frontend from scratch unless the current template blocks core publishing.

## 4. Project Layout

```text
newsreporter/
  RULE.md
  README.md
  requirements.txt
  configs/
    default.yaml
    sources.yaml
    prompts.yaml
  src/
    app/
      main.py
    core/
      models.py
      base_pipeline.py
      base_scorer.py
      base_plugin.py
      store.py
      summarizer.py
      publisher.py
      utils.py
    sections/
      news/
        pipeline.py
        scorer.py
        plugins/
          rss_news.py
      arxiv/
        pipeline.py
        scorer.py
        plugins/
          arxiv.py
      github/
        pipeline.py
        scorer.py
        plugins/
          github.py
      huggingface/
        pipeline.py
        scorer.py
        plugins/
          huggingface.py
    plugins/
      # optional shared plugin helpers only
    web/
      renderer.py
      templates/
        base.html
        index.html
        daily.html
      static/
        styles.css
  data/
    state.db
  output/
    site/
      index.html
      daily/
        YYYY-MM-DD/
          index.html
  scripts/
    run_daily.sh
    init_db.sql
  deploy/
    nginx/
      newsreporter.conf
  tests/
```

## 5. Data Model Rules

Every source must normalize to one common item shape.

```python
Item = {
  "section": str,  # news|arxiv|github|huggingface
  "source": str,
  "source_id": str,
  "title": str,
  "url": str,
  "published_at": str | None,
  "summary_raw": str | None,
  "summary_short": str | None,
  "tags": list[str],
  "signals": dict,
  "dedup_key": str,
}
```

### dedup_key
Must be stable:

```text
sha256(f"{section}|{source}|{source_id_or_url}")
```

Priority:
1. source_id
2. url
3. title + published_at

## 6. Storage Rules

SQLite is the source of truth.

Minimum tables:
- `items_canonical`
- `snapshots`
- `daily_digest`
- `runs`

### `items_canonical`
Stores normalized source items.

### `snapshots`
Stores GH / HF historical metrics for trend calculation.

### `daily_digest`
Stores one digest per day.

Suggested fields:
- `digest_date`
- `status`
- `output_path`
- `generated_at`
- `stats_json`

### `runs`
Stores execution history.

### SQLite settings
Use:
```sql
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
```

## 7. Source Plugin Rules

Each section plugin implements one plugin interface.

```python
class SourcePlugin:
    section: str
    name: str
    def fetch(self, since, config) -> list[Item]:
        ...
```

### Plugin responsibilities
- fetch data
- normalize data
- provide basic signals
- handle timeout / retry / backoff
- fail independently

### Plugin must NOT
- publish pages
- update homepage
- send Telegram
- contain global ranking logic
- hardcode secrets

## 8. Scoring Rules

## Phase 1 — News scoring
Use simple, explainable scoring:
- keyword/topic/company match
- source preference if needed

Example:
```text
score = keyword_match_score + source_weight + feed_weight
```

## Phase 2 — arXiv scoring
Use a simple trending proxy:
- freshness
- topic match
- optional author/institution prior
- optional category bonus

Keep it explainable.

## Phase 3 — GitHub / HF scoring
Trending must be **velocity-based**, not just popularity-based.
Each section has its own scorer subclass and score space.
No cross-section score normalization in Phase 1-3.

### GitHub
Use:
- stars_1d
- stars_7d
- recent_update_decay
- topic_match

### Hugging Face
Use:
- downloads_delta
- likes_delta
- recent_update_decay
- tag_match

No “top by total stars/downloads” nonsense masquerading as trend.

## 9. Summary Rules

Two-level summary strategy:

### Level 1 — Extractive first
- title
- first 1–2 important sentences
- source metadata

### Level 2 — Short generated summary
- one short TL;DR sentence
- must stay grounded in input
- no invented facts

Rule:
If the source text is thin, the summary must stay thin. No decorative hallucination.

## 10. Rendering Rules

We generate static pages only.

### Required pages
1. homepage
   - latest digest
   - recent archive links

2. daily page
   - one page per date
   - sections:
     - News
     - arXiv
     - GitHub
     - Hugging Face

### Output paths
```text
output/site/index.html
output/site/daily/YYYY-MM-DD/index.html
```

### Rendering engine
Use Jinja2.

### Frontend rule
Template and CSS live inside project.
Nginx is only the distributor, not the styling layer.

## 11. Publishing Rules

Publish flow:
1. run section pipelines in order (`news -> arxiv -> github -> huggingface`)
2. collect each section's output payload
3. render one combined daily page
4. render homepage
5. write files atomically
6. mark digest as published

Publishing must be rerunnable.

If a run for the same date happens twice:
- update the same output path
- do not create duplicate archive entries

## 12. Nginx Rules

Nginx serves generated static files.

It is **outside** the app logic.

App writes to:
```text
/var/www/newsreporter_site/
```

Nginx serves that directory.

Project may contain an Nginx config template in:
```text
deploy/nginx/newsreporter.conf
```

But Nginx itself is infra, not application code.

## 13. Scheduler Rules

Use cron.

Two modes are allowed:

### Mode A — simple daily mode
Run once per day and generate the whole site.

### Mode B — prefetch + publish mode
- prefetch job runs more often
- publish job runs once daily

For now, Phase 1 should prefer **simple daily mode**.

## 14. Dry-Run Rule

Every major command must support dry-run.

Dry-run means:
- fetch
- score
- summarize
- render preview
- no final publish overwrite unless explicitly requested

If a system cannot dry-run, it is not ready.

## 15. Failure Rules

Single-source failure must not kill its section.
Single-section failure must not kill the whole digest.

Allowed behavior:
- source fails
- log failure
- continue with remaining sources in that section
- continue with remaining sections
- publish partial digest if enough content exists

Do not fail the entire page because one feed threw a tantrum.

## 16. Testing Rules

Minimum tests:
- dedup logic
- daily digest generation
- template rendering smoke test
- one smoke test per plugin

We are not chasing perfect coverage.
We are preventing obvious self-inflicted chaos.

## 17. Security Rules

- secrets live in `.env` or server environment
- never commit tokens
- never print env vars
- never print auth headers
- lock dependency versions
- keep logs clean

## 18. Vibe Coding Workflow

### Step 1
Make data generation stable.

### Step 2
Make one daily digest JSON stable.

### Step 3
Make one daily HTML page stable.

### Step 4
Make homepage stable.

### Step 5
Deploy to local blog directory.

### Step 6
Serve with Nginx.

### Step 7
Then add arXiv.

### Step 8
Then add GH / HF trending.

Order matters. Chaos also has an order, but we do not need to imitate it.

## 19. Definition of Done

A phase is done only if:

- it runs locally
- it can dry-run
- it writes stable output
- rerun is safe
- homepage updates correctly
- archive page exists
- output can be served by Nginx
- no secret leakage
- no duplicate digest generation

## 20. Final Principle

This project is not “an RSS script.”

It is a **daily publishing engine**.

Think in this order:
- robust pipeline
- stable output
- clean archive
- easy deploy
- then smarter ranking

Build the newspaper press first. Then argue about headline philosophy.
