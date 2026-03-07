from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from src.core.models import Item


class BaseScorer(ABC):
    @abstractmethod
    def score_item(self, item: Item, now: datetime) -> float:
        raise NotImplementedError

    def score_items(self, items: list[Item], now: datetime) -> list[Item]:
        for item in items:
            self.score_item(item, now)
        return sorted(
            items,
            key=lambda value: (
                float(value.signals.get("score", 0)),
                value.published_at.isoformat() if value.published_at else "",
            ),
            reverse=True,
        )
