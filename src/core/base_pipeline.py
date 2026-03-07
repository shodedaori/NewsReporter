from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from src.core.models import Item
from src.core.utils import cross_source_key, day_end_utc, utc_now


@dataclass(slots=True)
class SectionResult:
    section: str
    items: list[Item]
    stats: dict
    generated_at: str


def deduplicate_items(items: list[Item]) -> list[Item]:
    unique_by_source_key: dict[str, Item] = {}
    for item in items:
        unique_by_source_key[item.dedup_key] = item

    unique_by_cross_source: dict[str, Item] = {}
    for item in unique_by_source_key.values():
        cross_key = f"{item.section}|{cross_source_key(item.url, item.title, item.published_at)}"
        current = unique_by_cross_source.get(cross_key)
        if current is None:
            unique_by_cross_source[cross_key] = item
            continue
        current_score = float(current.signals.get("feed_weight", 0))
        next_score = float(item.signals.get("feed_weight", 0))
        if next_score > current_score:
            unique_by_cross_source[cross_key] = item
    return list(unique_by_cross_source.values())


class BaseSectionPipeline(ABC):
    section: str

    def __init__(self, app_config: dict):
        self.app_config = app_config

    @abstractmethod
    def run(self, digest_date: date) -> SectionResult:
        raise NotImplementedError

    def window_end(self, digest_date: date) -> datetime:
        today = utc_now().date()
        if digest_date == today:
            return utc_now()
        return day_end_utc(digest_date)

    def window_start(self, digest_date: date) -> datetime:
        until = self.window_end(digest_date)
        hours = int(self.app_config["app"].get("window_hours", 24))
        return until - timedelta(hours=hours)
