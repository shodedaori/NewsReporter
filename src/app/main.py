from __future__ import annotations

import argparse
import json
import logging
from datetime import date
from pathlib import Path

import yaml

from src.core.pipeline import DailyOrchestrator
from src.core.publisher import Publisher
from src.core.store import Store
from src.core.summarizer import Summarizer
from src.core.utils import parse_date_arg
from src.sections.news.pipeline import NewsSectionPipeline
from src.sections.news.plugins.rss_news import RSSNewsPlugin
from src.sections.news.scorer import NewsScorer
from src.web.renderer import Renderer


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return data or {}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run NewsReporter phase1 pipeline")
    parser.add_argument("--date", default=date.today().isoformat(), help="Digest date in YYYY-MM-DD")
    parser.add_argument("--dry-run", action="store_true", help="Run with preview output")
    parser.add_argument("--publish", action="store_true", help="Write to publish output path")
    parser.add_argument("--config-dir", default="configs", help="Config directory path")
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

    run_as_publish = args.publish and not args.dry_run
    dry_run = not run_as_publish

    store = Store(default_config["paths"]["database"])
    renderer = Renderer(default_config["paths"]["templates"])
    publisher = Publisher()
    summarizer = Summarizer()
    news_pipeline = NewsSectionPipeline(
        app_config=default_config,
        source_config=source_config,
        plugins=[RSSNewsPlugin()],
        scorer=NewsScorer(default_config.get("scoring", {})),
        summarizer=summarizer,
    )
    orchestrator = DailyOrchestrator(
        store=store,
        renderer=renderer,
        publisher=publisher,
        app_config=default_config,
        section_pipelines=[news_pipeline],
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
