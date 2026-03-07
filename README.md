# NewsReporter

Daily static publishing pipeline for news digests.

## Phase 1 (News)

Run preview:

```bash
python -m src.app.main --date 2026-03-07 --dry-run
```

Run publish:

```bash
python -m src.app.main --date 2026-03-07 --publish
```

Run tests:

```bash
pytest -q
```

Clean DB for tests:

```bash
python scripts/clean_db.py --reinit
```

Enable LLM news summarizer:

1. Set `summarizer.mode: llm` in `configs/default.yaml`
2. Export `OPENAI_API_KEY`
3. Optional: set `OPENAI_BASE_URL` for compatible gateways
