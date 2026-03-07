from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
import shutil
import tempfile

from src.core.models import Item
from src.core.pipeline import DailyOrchestrator
from src.core.publisher import Publisher
from src.core.store import Store
from src.core.summarizer import Summarizer
from src.core.utils import build_dedup_key
from src.sections.news.pipeline import NewsSectionPipeline
from src.sections.news.scorer import NewsScorer
from src.web.renderer import Renderer


class FakeNewsPlugin:
    section = "news"
    name = "rss_news"

    def fetch(self, since, until, config):  # noqa: ANN001, ANN201
        published = datetime(2026, 3, 7, 10, 0, tzinfo=timezone.utc)
        title = "OpenAI signs enterprise deal"
        url = "https://example.com/news/enterprise-deal"
        dedup_key = build_dedup_key(self.name, "item-1", url, title, published, section=self.section)
        return [
            Item(
                section=self.section,
                source=self.name,
                source_id="item-1",
                title=title,
                url=url,
                published_at=published,
                summary_raw="OpenAI announced a new enterprise partnership.",
                tags=["enterprise"],
                signals={"feed_name": "FakeFeed", "feed_weight": 1},
                dedup_key=dedup_key,
            )
        ]


def test_pipeline_dry_run_generates_preview() -> None:
    cache_root = Path(".cache") / "test_tmp"
    cache_root.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix="test-pipeline-", suffix=".token", dir=str(cache_root), delete=False) as handle:
        token_path = Path(handle.name)

    root = cache_root / token_path.stem
    token_path.unlink(missing_ok=True)
    root.mkdir(parents=True, exist_ok=True)
    database = root / "state.db"
    output_preview = root / "preview" / "site"
    output_site = root / "site"

    app_config = {
        "app": {"site_name": "NewsReporter", "window_hours": 24, "top_items": 10},
        "paths": {
            "database": str(database),
            "output_site": str(output_site),
            "output_preview": str(output_preview),
            "templates": "src/web/templates",
            "static": "src/web/static",
        },
        "scoring": {"source_weights": {"rss_news": 2}, "keywords": ["enterprise"], "companies": ["OpenAI"]},
    }
    source_config = {"rss_news": {"feeds": []}}

    store = Store(str(database))
    try:
        news_pipeline = NewsSectionPipeline(
            app_config=app_config,
            source_config=source_config,
            plugins=[FakeNewsPlugin()],
            scorer=NewsScorer(app_config["scoring"]),
            summarizer=Summarizer(),
        )
        orchestrator = DailyOrchestrator(
            store=store,
            renderer=Renderer(app_config["paths"]["templates"]),
            publisher=Publisher(),
            app_config=app_config,
            section_pipelines=[news_pipeline],
        )
        result = orchestrator.run(digest_date=date(2026, 3, 7), dry_run=True, publish=False)
        assert result["mode"] == "preview"
        assert (output_preview / "index.html").exists()
        assert (output_preview / "daily" / "2026-03-07" / "index.html").exists()
    finally:
        store.close()
        shutil.rmtree(root, ignore_errors=True)
