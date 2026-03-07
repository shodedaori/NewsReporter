from __future__ import annotations

from datetime import datetime

from src.core.base_scorer import BaseScorer
from src.core.models import Item
from src.core.utils import strip_html


class NewsScorer(BaseScorer):
    def __init__(self, scoring_config: dict):
        self.keywords = [k.lower() for k in scoring_config.get("keywords", [])]
        self.source_weights = scoring_config.get("source_weights", {})

    def score_item(self, item: Item, now: datetime) -> float:
        text = f"{item.title} {strip_html(item.summary_raw)}".lower()
        keyword_hits = sum(1 for keyword in self.keywords if keyword in text)
        match_score = min(30.0, keyword_hits * 4.0)

        base_weight = float(self.source_weights.get(item.source, 0))
        feed_weight = float(item.signals.get("feed_weight", 0))
        total = round(match_score + base_weight + feed_weight, 2)

        item.signals["keyword_hits"] = keyword_hits
        item.signals["source_weight"] = base_weight
        item.signals["feed_weight"] = feed_weight
        item.signals["score"] = total
        return total
