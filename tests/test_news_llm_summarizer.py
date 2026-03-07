from __future__ import annotations

from src.core.models import Item
from src.sections.news.summarizer import build_news_summarizer


def test_build_news_summarizer_fallback_extractive() -> None:
    app_config = {"summarizer": {"mode": "extractive"}}
    prompts_config = {}
    summarizer = build_news_summarizer(app_config, prompts_config)

    item = Item(
        section="news",
        source="rss_news",
        source_id="1",
        title="Test title",
        url="https://example.com",
        published_at=None,
        summary_raw="Test summary content.",
    )
    summarized = summarizer.summarize_item(item)
    assert summarized.summary_short
