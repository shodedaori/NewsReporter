from __future__ import annotations

import logging
from datetime import date

from src.core.base_pipeline import BaseSectionPipeline, SectionResult
from src.core.base_plugin import BaseSourcePlugin
from src.core.models import Item
from src.core.summarizer import Summarizer
from src.core.utils import utc_now
from src.sections.huggingface.scorer import HuggingFaceScorer

LOGGER = logging.getLogger(__name__)

class HuggingFaceSectionPipeline(BaseSectionPipeline):
    section = "hf"

    def __init__(
        self,
        app_config: dict,
        source_config: dict,
        plugins: list[BaseSourcePlugin],
        scorer: HuggingFaceScorer,
        summarizer: Summarizer,
    ):
        super().__init__(app_config=app_config)
        self.source_config = source_config
        self.plugins = plugins
        self.scorer = scorer
        self.summarizer = summarizer

    def run(self, digest_date: date) -> SectionResult:
        print(f"[progress] section=hf start date={digest_date.isoformat()}", flush=True)
        until = self.window_end(digest_date)
        since = self.window_start(digest_date)

        all_items: list[Item] = []
        failures = 0
        for plugin in self.plugins:
            plugin_config = self.source_config.get(plugin.name, {})
            try:
                print(f"[progress] section=hf fetch plugin={plugin.name}", flush=True)
                all_items.extend(plugin.fetch(since=since, until=until, config=plugin_config))
            except Exception as exc:  # noqa: BLE001
                failures += 1
                LOGGER.warning("Section %s plugin failed: %s (%s)", self.section, plugin.name, exc)

        unique_items = self._dedup_input_items([item for item in all_items if item.section == self.section])
        print(
            f"[progress] section=hf dedup done total={len(all_items)} unique={len(unique_items)}",
            flush=True,
        )

        top_n = int(self.app_config["app"].get("top_items", 8))
        each_n = top_n // 2
        model_items = [item for item in unique_items if item.signals.get("kind") == "model"]
        dataset_items = [item for item in unique_items if item.signals.get("kind") == "dataset"]
        selected_items = model_items[:each_n] + dataset_items[:each_n]
        print(
            f"[progress] section=hf select models={min(each_n, len(model_items))} datasets={min(each_n, len(dataset_items))}",
            flush=True,
        )

        for item in selected_items:
            self.scorer.score_item(item, now=until)
        print("[progress] section=hf score computed", flush=True)

        summarized_items = self.summarizer.summarize_items(selected_items)
        print(f"[progress] section=hf summarize done items={len(summarized_items)}", flush=True)

        selected_likes_total = sum(int(item.signals.get("likes_total", 0)) for item in selected_items)
        selected_likes_7d_total = sum(int(item.signals.get("likes_7d", 0)) for item in selected_items)
        selected_downloads_total = sum(int(item.signals.get("downloads", 0)) for item in selected_items)
        stats = {
            "item_count": len(all_items),
            "unique_count": len(unique_items),
            "selected_count": len(selected_items),
            "selected_models_count": min(each_n, len(model_items)),
            "selected_datasets_count": min(each_n, len(dataset_items)),
            "published_count": len(summarized_items),
            "selected_likes_total": selected_likes_total,
            "selected_likes_7d_total": selected_likes_7d_total,
            "selected_downloads_total": selected_downloads_total,
            "failures": failures,
        }
        print(f"[progress] section=hf finished stats={stats}", flush=True)
        return SectionResult(
            section=self.section,
            items=summarized_items,
            stats=stats,
            generated_at=utc_now().isoformat(),
        )

    @staticmethod
    def _dedup_input_items(items: list[Item]) -> list[Item]:
        seen: set[str] = set()
        output: list[Item] = []
        for item in items:
            key = f"{item.source}|{(item.source_id or item.url or '').strip().lower()}"
            if not key.strip("|"):
                output.append(item)
                continue
            if key in seen:
                continue
            seen.add(key)
            output.append(item)
        return output
