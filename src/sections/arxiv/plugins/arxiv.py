from __future__ import annotations

from datetime import datetime, timedelta
from urllib.parse import quote_plus

import feedparser
import requests

from src.core.base_plugin import BaseSourcePlugin
from src.core.models import Item
from src.core.utils import build_dedup_key, parse_datetime_value, strip_html


class ArxivPlugin(BaseSourcePlugin):
    section = "arxiv"
    name = "arxiv"

    def __init__(self, session: requests.Session | None = None, timeout: int = 15, retries: int = 2):
        self.session = session or requests.Session()
        self.timeout = timeout
        self.retries = retries

    def fetch(self, since: datetime, until: datetime, config: dict) -> list[Item]:
        keywords = [str(value).strip() for value in config.get("keywords", []) if str(value).strip()]
        categories = [str(value).strip() for value in config.get("categories", []) if str(value).strip()]
        max_results = int(config.get("max_results", 100))
        backcheck_days = max(1, int(config.get("backcheck_days", 2)))
        effective_since = until - timedelta(days=backcheck_days)

        # Use category-first recall for stability, then apply keyword filter locally.
        query = self._build_query(categories)
        if not query:
            return []

        url = (
            "http://export.arxiv.org/api/query"
            f"?search_query={quote_plus(query)}"
            f"&start=0&max_results={max_results}&sortBy=submittedDate&sortOrder=descending"
        )
        response = self.session.get(url, timeout=self.timeout, headers={"User-Agent": "NewsReporter/1.0"})
        response.raise_for_status()
        parsed = feedparser.parse(response.content)

        items: list[Item] = []
        for entry in parsed.entries:
            title = (entry.get("title") or "").replace("\n", " ").strip()
            if not title:
                continue

            source_id = self._extract_arxiv_id(entry)
            url = self._extract_entry_url(entry)
            published_at = parse_datetime_value(entry.get("published")) or parse_datetime_value(entry.get("updated"))
            if published_at and (published_at < effective_since or published_at > until):
                continue

            categories_entry = [tag.get("term", "").strip() for tag in entry.get("tags", []) if tag.get("term")]
            authors = [author.get("name", "").strip() for author in entry.get("authors", []) if author.get("name")]
            summary_raw = strip_html(entry.get("summary") or "")

            if keywords:
                text = f"{title} {summary_raw}".lower()
                if not any(keyword.lower() in text for keyword in keywords):
                    continue

            item = Item(
                section=self.section,
                source=self.name,
                source_id=source_id,
                title=title,
                url=url,
                published_at=published_at,
                summary_raw=summary_raw,
                tags=categories_entry,
                signals={
                    "authors": authors,
                    "categories": categories_entry,
                    "primary_category": categories_entry[0] if categories_entry else "",
                },
                dedup_key=build_dedup_key(
                    source=self.name,
                    source_id=source_id,
                    url=url,
                    title=title,
                    published_at=published_at,
                    section=self.section,
                ),
            )
            items.append(item)
        return items

    def _build_query(self, categories: list[str]) -> str:
        if categories:
            category_part = " OR ".join(f"cat:{value}" for value in categories)
            return f"({category_part})"
        return "all:machine learning"

    @staticmethod
    def _extract_arxiv_id(entry: dict) -> str:
        entry_id = (entry.get("id") or "").strip()
        if "/abs/" in entry_id:
            return entry_id.split("/abs/")[-1]
        return entry_id

    @staticmethod
    def _extract_entry_url(entry: dict) -> str:
        entry_id = (entry.get("id") or "").strip()
        if entry_id:
            return entry_id
        links = entry.get("links", [])
        if links:
            return links[0].get("href", "")
        return ""
