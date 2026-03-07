from __future__ import annotations

import argparse
import json
import logging
import os
from datetime import date
from pathlib import Path

import yaml

from src.core.pipeline import DailyOrchestrator
from src.core.publisher import Publisher
from src.core.store import Store
from src.core.summarizer import Summarizer
from src.core.utils import parse_date_arg
from src.sections.arxiv.pipeline import ArxivSectionPipeline
from src.sections.arxiv.plugins.arxiv import ArxivPlugin
from src.sections.arxiv.scorer import ArxivScorer
from src.sections.arxiv.summarizer import build_arxiv_summarizer
from src.sections.news.pipeline import NewsSectionPipeline
from src.sections.news.plugins.rss_news import RSSNewsPlugin
from src.sections.news.scorer import NewsScorer
from src.sections.news.summarizer import build_news_summarizer
from src.web.renderer import Renderer


def load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return data or {}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run NewsReporter phase1 pipeline")
    parser.add_argument("--date", default=date.today().isoformat(), help="Digest date in YYYY-MM-DD")
    parser.add_argument("--dry-run", action="store_true", help="Run with preview output")
    parser.add_argument("--publish", action="store_true", help="Write to publish output path")
    parser.add_argument("--sections", default="news,arxiv", help="Comma-separated sections to run, e.g. news,arxiv")
    parser.add_argument("--config-dir", default="configs", help="Config directory path")
    parser.add_argument("--secret-config", default="configs/secret.setting.yaml", help="Secret settings yaml path")
    parser.add_argument("--log-level", default="INFO", help="Python logging level")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    config_dir = Path(args.config_dir)
    default_config = load_yaml(config_dir / "default.yaml")
    source_config = load_yaml(config_dir / "sources.yaml")
    prompts_config = load_yaml(config_dir / "prompts.yaml")
    secret_config = load_yaml(Path(args.secret_config))

    # Secret file is a fallback entrypoint. Environment variables keep top priority.
    openai_secret = secret_config.get("openai", {}) if isinstance(secret_config, dict) else {}
    if openai_secret.get("api_key") and not os.getenv("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = str(openai_secret["api_key"])
    if openai_secret.get("base_url") and not os.getenv("OPENAI_BASE_URL"):
        os.environ["OPENAI_BASE_URL"] = str(openai_secret["base_url"])

    run_as_publish = args.publish and not args.dry_run
    dry_run = not run_as_publish

    store = Store(default_config["paths"]["database"])
    renderer = Renderer(default_config["paths"]["templates"])
    publisher = Publisher()
    summarizer = build_news_summarizer(default_config, prompts_config)
    news_pipeline = NewsSectionPipeline(
        app_config=default_config,
        source_config=source_config,
        plugins=[RSSNewsPlugin()],
        scorer=NewsScorer(default_config.get("scoring", {})),
        summarizer=summarizer,
    )
    arxiv_pipeline = ArxivSectionPipeline(
        app_config=default_config,
        source_config=source_config,
        plugins=[ArxivPlugin()],
        scorer=ArxivScorer(default_config.get("scoring", {})),
        summarizer=build_arxiv_summarizer(default_config, prompts_config),
    )
    pipeline_map = {
        "news": news_pipeline,
        "arxiv": arxiv_pipeline,
    }
    requested_sections = [value.strip().lower() for value in args.sections.split(",") if value.strip()]
    section_pipelines = [pipeline_map[name] for name in requested_sections if name in pipeline_map]
    if not section_pipelines:
        raise ValueError("No valid sections selected. Supported: news,arxiv")

    orchestrator = DailyOrchestrator(
        store=store,
        renderer=renderer,
        publisher=publisher,
        app_config=default_config,
        section_pipelines=section_pipelines,
    )

    try:
        digest_date = parse_date_arg(args.date)
        result = orchestrator.run(digest_date=digest_date, dry_run=dry_run, publish=run_as_publish)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
