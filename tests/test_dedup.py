from __future__ import annotations

from datetime import datetime, timezone

from src.core.models import Item
from src.core.pipeline import deduplicate_items
from src.core.utils import build_dedup_key


def _item(source: str, source_id: str, url: str, weight: int) -> Item:
    published = datetime(2026, 3, 7, 10, 0, tzinfo=timezone.utc)
    return Item(
        section="news",
        source=source,
        source_id=source_id,
        title="OpenAI releases new model",
        url=url,
        published_at=published,
        summary_raw="A short summary.",
        tags=[],
        signals={"feed_weight": weight},
        dedup_key=build_dedup_key(source, source_id, url, "OpenAI releases new model", published, section="news"),
    )


def test_deduplicate_prefers_higher_weight_for_same_url() -> None:
    item_a = _item("rss_news", "a", "https://example.com/news/1", 1)
    item_b = _item("rss_news_backup", "b", "https://example.com/news/1", 3)

    unique = deduplicate_items([item_a, item_b])

    assert len(unique) == 1
    assert unique[0].source == "rss_news_backup"
