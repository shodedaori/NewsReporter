from __future__ import annotations

import math
from datetime import datetime

from src.core.base_scorer import BaseScorer
from src.core.models import Item


class HuggingFaceScorer(BaseScorer):
    def __init__(self, scoring_config: dict | None = None):
        config = (scoring_config or {}).get("hf", {})
        self.likes_7d_weight = float(config.get("likes_7d_weight", 1.0))
        self.likes_total_weight = float(config.get("likes_total_weight", 0.3))
        self.downloads_weight = float(config.get("downloads_weight", 0.1))

    def score_item(self, item: Item, now: datetime) -> float:
        del now
        likes_7d = int(item.signals.get("likes_7d", 0))
        likes_total = int(item.signals.get("likes_total", 0))
        downloads = int(item.signals.get("downloads", 0))
        score = (
            self.likes_7d_weight * likes_7d
            + self.likes_total_weight * math.log1p(max(likes_total, 0))
            + self.downloads_weight * math.log1p(max(downloads, 0))
        )
        score = round(score, 2)
        item.signals["score"] = score
        return score
