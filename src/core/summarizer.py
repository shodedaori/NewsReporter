from __future__ import annotations

from src.core.models import Item
from src.core.utils import clip_text, first_sentences, strip_html


class Summarizer:
    def summarize_item(self, item: Item) -> Item:
        source_text = strip_html(item.summary_raw) or strip_html(item.title)
        extractive = first_sentences(source_text, count=2) or strip_html(item.title)
        short_summary = clip_text(extractive, 220)
        item.summary_short = short_summary
        return item

    def summarize_items(self, items: list[Item]) -> list[Item]:
        return [self.summarize_item(item) for item in items]
