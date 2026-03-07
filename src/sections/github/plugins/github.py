from __future__ import annotations

import html
import os
import re
from datetime import datetime

import requests

from src.core.base_plugin import BaseSourcePlugin
from src.core.models import Item
from src.core.utils import build_dedup_key


class GitHubPlugin(BaseSourcePlugin):
    section = "github"
    name = "github"
    item_source = "github_trending"

    def __init__(self, session: requests.Session | None = None, timeout: int = 15):
        self.session = session or requests.Session()
        self.timeout = timeout

    def fetch(self, since: datetime, until: datetime, config: dict) -> list[Item]:
        url = str(config.get("trending_url", "https://github.com/trending?since=daily"))
        response = self.session.get(url, timeout=int(config.get("request_timeout", self.timeout)), headers=self._headers())
        response.raise_for_status()
        return self._parse_trending_html(response.text)

    def enrich_with_readme(self, items: list[Item], config: dict) -> list[Item]:
        max_chars = int(config.get("readme_max_chars", 8000))
        for item in items:
            readme = self.fetch_readme(item.source_id, config=config)
            if not readme:
                continue
            readme = readme[:max_chars]
            item.signals["readme_text"] = readme
            item.signals["has_readme"] = True
        return items

    def fetch_readme(self, repo_full_name: str, config: dict) -> str:
        timeout = int(config.get("request_timeout", self.timeout))
        api_url = f"https://api.github.com/repos/{repo_full_name}/readme"
        try:
            response = self.session.get(
                api_url,
                timeout=timeout,
                headers={**self._headers(), "Accept": "application/vnd.github.raw+json"},
            )
            if response.status_code == 200:
                return self._normalize_readme_text(response.text)
        except requests.RequestException:
            pass

        fallback_url = f"https://raw.githubusercontent.com/{repo_full_name}/HEAD/README.md"
        try:
            response = self.session.get(fallback_url, timeout=timeout, headers=self._headers())
            if response.status_code == 200:
                return self._normalize_readme_text(response.text)
        except requests.RequestException:
            return ""
        return ""

    def _parse_trending_html(self, html_text: str) -> list[Item]:
        items: list[Item] = []
        article_pattern = re.compile(r"<article[^>]*class=\"[^\"]*Box-row[^\"]*\"[^>]*>(.*?)</article>", re.DOTALL)
        repo_pattern = re.compile(r"href=\"/([^\"/]+/[^\"/]+)\"")
        desc_pattern = re.compile(r"<p[^>]*>(.*?)</p>", re.DOTALL)
        language_pattern = re.compile(r"itemprop=\"programmingLanguage\">(.*?)</span>", re.DOTALL)
        stars_pattern = re.compile(r"href=\"/[^\"/]+/[^\"/]+/stargazers\"[^>]*>(.*?)</a>", re.DOTALL)
        forks_pattern = re.compile(r"href=\"/[^\"/]+/[^\"/]+/forks\"[^>]*>(.*?)</a>", re.DOTALL)
        stars_today_pattern = re.compile(r"([0-9,]+)\s+stars?\s+today", re.DOTALL | re.IGNORECASE)

        for rank, article in enumerate(article_pattern.findall(html_text), start=1):
            repo_match = repo_pattern.search(article)
            if not repo_match:
                continue
            full_name = repo_match.group(1).strip()
            repo_url = f"https://github.com/{full_name}"

            description = ""
            desc_match = desc_pattern.search(article)
            if desc_match:
                description = self._clean_html_text(desc_match.group(1))

            language = ""
            language_match = language_pattern.search(article)
            if language_match:
                language = self._clean_html_text(language_match.group(1))

            stars_total = self._extract_compact_number(stars_pattern, article)
            forks = self._extract_compact_number(forks_pattern, article)
            stars_today = self._extract_number(stars_today_pattern, article)

            item = Item(
                section=self.section,
                source=self.item_source,
                source_id=full_name,
                title=full_name,
                url=repo_url,
                published_at=None,
                summary_raw=description,
                tags=[language] if language else [],
                signals={
                    "language": language,
                    "stars_total": stars_total,
                    "stars": stars_total,
                    "forks": forks,
                    "stars_today": stars_today,
                    "rank": rank,
                },
                dedup_key=build_dedup_key(
                    source=self.item_source,
                    source_id=full_name,
                    url=repo_url,
                    title=full_name,
                    published_at=None,
                    section=self.section,
                ),
            )
            items.append(item)
        return items

    @staticmethod
    def _clean_html_text(value: str) -> str:
        no_tags = re.sub(r"<[^>]+>", " ", value)
        collapsed = re.sub(r"\s+", " ", no_tags).strip()
        return html.unescape(collapsed)

    @staticmethod
    def _extract_number(pattern: re.Pattern, text: str) -> int:
        match = pattern.search(text)
        if not match:
            return 0
        raw = match.group(1).replace(",", "").strip()
        try:
            return int(raw)
        except ValueError:
            return 0

    @classmethod
    def _extract_compact_number(cls, pattern: re.Pattern, text: str) -> int:
        match = pattern.search(text)
        if not match:
            return 0
        anchor_text = cls._clean_html_text(match.group(1))
        token_match = re.search(r"([0-9][0-9,]*(?:\.[0-9]+)?\s*[kKmM]?)", anchor_text)
        if not token_match:
            return 0
        return cls._parse_compact_number(token_match.group(1))

    @staticmethod
    def _parse_compact_number(raw: str) -> int:
        value = raw.replace(",", "").strip().lower()
        if not value:
            return 0
        multiplier = 1
        if value.endswith("k"):
            multiplier = 1_000
            value = value[:-1].strip()
        elif value.endswith("m"):
            multiplier = 1_000_000
            value = value[:-1].strip()
        try:
            return int(float(value) * multiplier)
        except ValueError:
            return 0

    @staticmethod
    def _normalize_readme_text(value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()

    @staticmethod
    def _headers() -> dict:
        token = os.getenv("GITHUB_TOKEN", "").strip()
        headers = {"User-Agent": "NewsReporter/1.0"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers
