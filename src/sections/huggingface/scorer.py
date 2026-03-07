from __future__ import annotations

from datetime import datetime

from src.core.base_scorer import BaseScorer
from src.core.models import Item


class HuggingFaceScorer(BaseScorer):
    def score_item(self, item: Item, now: datetime) -> float:
        item.signals["score"] = 0.0
        return 0.0
