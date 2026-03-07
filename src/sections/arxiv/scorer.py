from __future__ import annotations

from datetime import datetime

from src.core.base_scorer import BaseScorer
from src.core.models import Item
from src.core.utils import strip_html


class ArxivScorer(BaseScorer):
    def __init__(self, scoring_config: dict):
        arxiv_scoring = scoring_config.get("arxiv", {})
        self.keywords = [str(value).lower() for value in arxiv_scoring.get("keywords", [])]
        self.core_categories = [str(value).lower() for value in arxiv_scoring.get("core_categories", [])]
        self.topic_weight = float(arxiv_scoring.get("topic_weight", 6))
        self.category_bonus = float(arxiv_scoring.get("category_bonus", 8))

    def score_item(self, item: Item, now: datetime) -> float:
        text = f"{item.title} {strip_html(item.summary_raw)}".lower()
        topic_hits = sum(1 for keyword in self.keywords if keyword in text)
        topic_match_score = min(35.0, topic_hits * self.topic_weight)

        categories = [str(value).lower() for value in item.signals.get("categories", [])]
        has_core_category = any(category in self.core_categories for category in categories)
        category_score = self.category_bonus if has_core_category else 0.0

        total = round(topic_match_score + category_score, 2)
        item.signals["topic_hits"] = topic_hits
        item.signals["topic_match_score"] = round(topic_match_score, 2)
        item.signals["category_score"] = round(category_score, 2)
        item.signals["score"] = total
        return total
