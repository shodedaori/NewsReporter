from __future__ import annotations

import logging
from datetime import date

from src.core.base_pipeline import BaseSectionPipeline, SectionResult
from src.core.base_plugin import BaseSourcePlugin
from src.core.models import Item
from src.core.summarizer import Summarizer
from src.core.utils import utc_now
from src.sections.github.plugins.github import GitHubPlugin
from src.sections.github.scorer import GitHubScorer

LOGGER = logging.getLogger(__name__)


class GitHubSectionPipeline(BaseSectionPipeline):
    section = "github"

    def __init__(
        self,
        app_config: dict,
        source_config: dict,
        plugins: list[BaseSourcePlugin],
        scorer: GitHubScorer,
        summarizer: Summarizer,
    ):
        super().__init__(app_config=app_config)
        self.source_config = source_config
        self.plugins = plugins
        self.scorer = scorer
        self.summarizer = summarizer

    def run(self, digest_date: date) -> SectionResult:
        print(f"[progress] section=github start date={digest_date.isoformat()}", flush=True)
        until = self.window_end(digest_date)
        since = self.window_start(digest_date)

        all_items = []
        failures = 0
        for plugin in self.plugins:
            plugin_config = self.source_config.get(plugin.name, {})
            try:
                print(f"[progress] section=github fetch plugin={plugin.name}", flush=True)
                all_items.extend(plugin.fetch(since=since, until=until, config=plugin_config))
            except Exception as exc:  # noqa: BLE001
                failures += 1
                LOGGER.warning("Section %s plugin failed: %s (%s)", self.section, plugin.name, exc)

        unique_items = self._dedup_input_items([item for item in all_items if item.section == self.section])
        print(
            f"[progress] section=github dedup done total={len(all_items)} unique={len(unique_items)}",
            flush=True,
        )
        ranked_items = sorted(unique_items, key=lambda item: int(item.signals.get("rank", 10**9)))
        top_n = int(self.app_config["app"].get("top_items", 5))
        selected_items = ranked_items[:top_n]
        print(f"[progress] section=github select top_items={len(selected_items)}", flush=True)

        for item in selected_items:
            self.scorer.score_item(item, now=until)
        print("[progress] section=github star score computed", flush=True)
        selected_stars_total = sum(int(item.signals.get("stars_total", item.signals.get("stars", 0))) for item in selected_items)
        selected_stars_today_total = sum(int(item.signals.get("stars_today", 0)) for item in selected_items)

        for plugin in self.plugins:
            if isinstance(plugin, GitHubPlugin):
                plugin_config = self.source_config.get(plugin.name, {})
                selected_items = plugin.enrich_with_readme(selected_items, config=plugin_config)
                break
        print("[progress] section=github readme enrichment done", flush=True)

        summarized_items = self.summarizer.summarize_items(selected_items)
        print(f"[progress] section=github summarize done items={len(summarized_items)}", flush=True)
        stats = {
            "item_count": len(all_items),
            "unique_count": len(unique_items),
            "selected_count": len(selected_items),
            "published_count": len(summarized_items),
            "selected_stars_total": selected_stars_total,
            "selected_stars_today_total": selected_stars_today_total,
            "failures": failures,
        }
        print(f"[progress] section=github finished stats={stats}", flush=True)
        return SectionResult(
            section=self.section,
            items=summarized_items,
            stats=stats,
            generated_at=utc_now().isoformat(),
        )

    @staticmethod
    def _dedup_input_items(items: list[Item]) -> list[Item]:
        # Minimal input dedup for a single crawl batch: keep first occurrence by repo identity.
        seen: set[str] = set()
        output: list[Item] = []
        for item in items:
            key = (item.source_id or item.url or "").strip().lower()
            if not key:
                output.append(item)
                continue
            if key in seen:
                continue
            seen.add(key)
            output.append(item)
        return output
