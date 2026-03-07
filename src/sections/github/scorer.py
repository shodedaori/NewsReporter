from __future__ import annotations

import math
from datetime import datetime

from src.core.base_scorer import BaseScorer
from src.core.models import Item


class GitHubScorer(BaseScorer):
    def __init__(self, scoring_config: dict | None = None):
        config = (scoring_config or {}).get("github", {})
        self.stars_today_weight = float(config.get("stars_today_weight", 1.0))
        self.stars_total_weight = float(config.get("stars_total_weight", 0.6))

    def score_item(self, item: Item, now: datetime) -> float:
        # Keep score calculation configurable from default.yaml for display/stats.
        # Trending order remains the source of truth for ranking, so this score is not used for sorting.
        stars_today = int(item.signals.get("stars_today", 0))
        stars_total = int(item.signals.get("stars_total", item.signals.get("stars", 0)))
        score = self.stars_today_weight * stars_today + self.stars_total_weight * math.log1p(max(stars_total, 0))
        score = round(score, 2)
        item.signals["score"] = score
        return score
