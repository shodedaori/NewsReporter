from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class Item:
    section: str
    source: str
    source_id: str
    title: str
    url: str
    published_at: datetime | None
    summary_raw: str | None
    summary_short: str | None = None
    tags: list[str] = field(default_factory=list)
    signals: dict = field(default_factory=dict)
    dedup_key: str = ""


@dataclass(slots=True)
class Digest:
    digest_date: str
    generated_at: str
    status: str
    output_path: str
    stats: dict
