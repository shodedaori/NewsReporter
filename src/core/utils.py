from __future__ import annotations

import hashlib
import re
from datetime import date, datetime, time, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


_HTML_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def parse_date_arg(value: str) -> date:
    return date.fromisoformat(value)


def day_end_utc(target: date) -> datetime:
    return datetime.combine(target, time.max, tzinfo=timezone.utc)


def parse_datetime_value(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return ensure_utc(value)
    if hasattr(value, "tm_year"):
        return ensure_utc(datetime(*value[:6], tzinfo=timezone.utc))
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
            return ensure_utc(dt)
        except ValueError:
            pass
        try:
            return ensure_utc(parsedate_to_datetime(text))
        except (TypeError, ValueError):
            return None
    return None


def strip_html(text: str | None) -> str:
    if not text:
        return ""
    no_tags = _HTML_TAG_RE.sub(" ", text)
    return _SPACE_RE.sub(" ", no_tags).strip()


def first_sentences(text: str, count: int = 2) -> str:
    if not text:
        return ""
    sentences = _SENTENCE_SPLIT_RE.split(text)
    return " ".join(part.strip() for part in sentences[:count] if part.strip()).strip()


def clip_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    if limit <= 1:
        return text[:limit]
    return text[: limit - 1].rstrip() + "…"


def normalize_url(url: str | None) -> str:
    if not url:
        return ""
    parsed = urlsplit(url.strip())
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    query = urlencode(sorted(parse_qsl(parsed.query, keep_blank_values=False)))
    return urlunsplit((parsed.scheme.lower(), netloc, path, query, ""))


def build_dedup_key(
    source: str,
    source_id: str | None,
    url: str | None,
    title: str,
    published_at: datetime | None,
    section: str = "news",
) -> str:
    source_id_or_url = (source_id or "").strip() or normalize_url(url)
    if not source_id_or_url:
        published_text = published_at.isoformat() if published_at else ""
        source_id_or_url = f"{title.strip()}|{published_text}"
    return hashlib.sha256(f"{section}|{source}|{source_id_or_url}".encode("utf-8")).hexdigest()


def cross_source_key(url: str | None, title: str, published_at: datetime | None) -> str:
    normalized_url = normalize_url(url)
    if normalized_url:
        return hashlib.sha256(normalized_url.encode("utf-8")).hexdigest()
    published_text = published_at.isoformat() if published_at else ""
    raw = f"{title.strip().lower()}|{published_text}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
