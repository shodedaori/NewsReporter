from __future__ import annotations

import logging
import time
from datetime import datetime

import feedparser
import requests

from src.core.base_plugin import BaseSourcePlugin
from src.core.models import Item
from src.core.utils import build_dedup_key, parse_datetime_value, strip_html

LOGGER = logging.getLogger(__name__)


class RSSNewsPlugin(BaseSourcePlugin):
    section = "news"
    name = "rss_news"

    def __init__(self, session: requests.Session | None = None, timeout: int = 10, retries: int = 2):
        self.session = session or requests.Session()
        self.timeout = timeout
        self.retries = retries

    def fetch(self, since: datetime, until: datetime, config: dict) -> list[Item]:
        feeds = config.get("feeds", [])
        items: list[Item] = []
        for feed in feeds:
            feed_name = feed["name"]
            feed_url = feed["url"]
            feed_weight = float(feed.get("weight", 0))
            try:
                items.extend(self._fetch_feed(feed_name, feed_url, feed_weight, since, until))
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("RSS feed failed: %s (%s)", feed_name, exc)
        return items

    def _fetch_feed(
        self,
        feed_name: str,
        feed_url: str,
        feed_weight: float,
        since: datetime,
        until: datetime,
    ) -> list[Item]:
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                response = self.session.get(
                    feed_url,
                    timeout=self.timeout,
                    headers={"User-Agent": "NewsReporter/1.0"},
                )
                response.raise_for_status()
                parsed = feedparser.parse(response.content)
                return self._normalize_entries(parsed.entries, feed_name, feed_weight, since, until)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt < self.retries:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                raise
        if last_error:
            raise last_error
        return []

    def _normalize_entries(
        self,
        entries: list,
        feed_name: str,
        feed_weight: float,
        since: datetime,
        until: datetime,
    ) -> list[Item]:
        normalized: list[Item] = []
        for entry in entries:
            title = (entry.get("title") or "").strip()
            if not title:
                continue

            url = (entry.get("link") or "").strip()
            source_id = (entry.get("id") or entry.get("guid") or url or title).strip()
            published_at = self._entry_published_at(entry)
            if published_at and (published_at < since or published_at > until):
                continue

            summary_raw = entry.get("summary") or entry.get("description") or ""
            tags = [tag.get("term", "").strip() for tag in entry.get("tags", []) if tag.get("term")]
            dedup_key = build_dedup_key(
                source=self.name,
                source_id=source_id,
                url=url,
                title=title,
                published_at=published_at,
                section=self.section,
            )
            normalized.append(
                Item(
                    section=self.section,
                    source=self.name,
                    source_id=source_id,
                    title=title,
                    url=url,
                    published_at=published_at,
                    summary_raw=strip_html(summary_raw),
                    tags=tags,
                    signals={"feed_name": feed_name, "feed_weight": feed_weight},
                    dedup_key=dedup_key,
                )
            )
        return normalized

    def _entry_published_at(self, entry: dict) -> datetime | None:
        for key in ("published_parsed", "updated_parsed", "published", "updated"):
            value = entry.get(key)
            parsed = parse_datetime_value(value)
            if parsed:
                return parsed
        return None
