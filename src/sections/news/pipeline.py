from __future__ import annotations

import logging
from datetime import date

from src.core.base_pipeline import BaseSectionPipeline, SectionResult, deduplicate_items
from src.core.base_plugin import BaseSourcePlugin
from src.core.summarizer import Summarizer
from src.core.utils import utc_now
from src.sections.news.scorer import NewsScorer

LOGGER = logging.getLogger(__name__)


class NewsSectionPipeline(BaseSectionPipeline):
    section = "news"

    def __init__(
        self,
        app_config: dict,
        source_config: dict,
        plugins: list[BaseSourcePlugin],
        scorer: NewsScorer,
        summarizer: Summarizer,
    ):
        super().__init__(app_config=app_config)
        self.source_config = source_config
        self.plugins = plugins
        self.scorer = scorer
        self.summarizer = summarizer

    def run(self, digest_date: date) -> SectionResult:
        print(f"[progress] section=news start date={digest_date.isoformat()}", flush=True)
        until = self.window_end(digest_date)
        since = self.window_start(digest_date)

        all_items = []
        failures = 0
        for plugin in self.plugins:
            plugin_config = self.source_config.get(plugin.name, {})
            try:
                print(f"[progress] section=news fetch plugin={plugin.name}", flush=True)
                all_items.extend(plugin.fetch(since=since, until=until, config=plugin_config))
            except Exception as exc:  # noqa: BLE001
                failures += 1
                LOGGER.warning("Section %s plugin failed: %s (%s)", self.section, plugin.name, exc)

        unique_items = deduplicate_items([item for item in all_items if item.section == self.section])
        print(
            f"[progress] section=news dedup done total={len(all_items)} unique={len(unique_items)}",
            flush=True,
        )
        scored_items = self.scorer.score_items(unique_items, now=until)
        print(f"[progress] section=news scoring done items={len(scored_items)}", flush=True)
        top_n = int(self.app_config["app"].get("top_items", 5))
        selected_items = scored_items[:top_n]
        print(f"[progress] section=news select top_items={len(selected_items)}", flush=True)
        summarized_items = self.summarizer.summarize_items(selected_items)
        print(f"[progress] section=news summarize done items={len(summarized_items)}", flush=True)
        stats = {
            "item_count": len(all_items),
            "unique_count": len(unique_items),
            "selected_count": len(selected_items),
            "published_count": len(summarized_items),
            "failures": failures,
        }
        print(f"[progress] section=news finished stats={stats}", flush=True)
        return SectionResult(
            section=self.section,
            items=summarized_items,
            stats=stats,
            generated_at=utc_now().isoformat(),
        )
