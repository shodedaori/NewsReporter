from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from src.core.models import Item
from src.core.utils import utc_now


class Store:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._configure()
        self.init_schema()

    def _configure(self) -> None:
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")

    def init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS items_canonical (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              dedup_key TEXT NOT NULL UNIQUE,
              section TEXT NOT NULL DEFAULT 'news',
              source TEXT NOT NULL,
              source_id TEXT,
              title TEXT NOT NULL,
              url TEXT,
              published_at TEXT,
              summary_raw TEXT,
              summary_short TEXT,
              tags_json TEXT NOT NULL,
              signals_json TEXT NOT NULL,
              score REAL NOT NULL DEFAULT 0,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS snapshots (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              source TEXT NOT NULL,
              source_ref TEXT NOT NULL,
              snapshot_at TEXT NOT NULL,
              metrics_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS daily_digest (
              digest_date TEXT PRIMARY KEY,
              status TEXT NOT NULL,
              output_path TEXT NOT NULL,
              generated_at TEXT NOT NULL,
              stats_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS runs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              run_date TEXT NOT NULL,
              status TEXT NOT NULL,
              dry_run INTEGER NOT NULL,
              started_at TEXT NOT NULL,
              ended_at TEXT,
              message TEXT,
              stats_json TEXT
            );
            """
        )
        self._migrate_items_canonical_section()
        self.conn.commit()

    def _migrate_items_canonical_section(self) -> None:
        columns = self.conn.execute("PRAGMA table_info(items_canonical)").fetchall()
        names = {row[1] for row in columns}
        if "section" not in names:
            self.conn.execute("ALTER TABLE items_canonical ADD COLUMN section TEXT NOT NULL DEFAULT 'news'")

    def start_run(self, run_date: str, dry_run: bool) -> int:
        started_at = utc_now().isoformat()
        cursor = self.conn.execute(
            """
            INSERT INTO runs (run_date, status, dry_run, started_at)
            VALUES (?, ?, ?, ?)
            """,
            (run_date, "running", 1 if dry_run else 0, started_at),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def finish_run(self, run_id: int, status: str, message: str, stats: dict) -> None:
        self.conn.execute(
            """
            UPDATE runs
            SET status = ?, ended_at = ?, message = ?, stats_json = ?
            WHERE id = ?
            """,
            (status, utc_now().isoformat(), message, json.dumps(stats, ensure_ascii=False), run_id),
        )
        self.conn.commit()

    def upsert_items(self, items: list[Item]) -> None:
        now = utc_now().isoformat()
        for item in items:
            self.conn.execute(
                """
                INSERT INTO items_canonical (
                  dedup_key, section, source, source_id, title, url, published_at, summary_raw,
                  summary_short, tags_json, signals_json, score, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(dedup_key) DO UPDATE SET
                  section = excluded.section,
                  source = excluded.source,
                  source_id = excluded.source_id,
                  title = excluded.title,
                  url = excluded.url,
                  published_at = excluded.published_at,
                  summary_raw = excluded.summary_raw,
                  summary_short = excluded.summary_short,
                  tags_json = excluded.tags_json,
                  signals_json = excluded.signals_json,
                  score = excluded.score,
                  updated_at = excluded.updated_at
                """,
                (
                    item.dedup_key,
                    item.section,
                    item.source,
                    item.source_id,
                    item.title,
                    item.url,
                    item.published_at.isoformat() if item.published_at else None,
                    item.summary_raw,
                    item.summary_short,
                    json.dumps(item.tags, ensure_ascii=False),
                    json.dumps(item.signals, ensure_ascii=False),
                    float(item.signals.get("score", 0)),
                    now,
                    now,
                ),
            )
        self.conn.commit()

    def save_digest(self, digest_date: str, status: str, output_path: str, stats: dict) -> None:
        self.conn.execute(
            """
            INSERT INTO daily_digest (digest_date, status, output_path, generated_at, stats_json)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(digest_date) DO UPDATE SET
              status = excluded.status,
              output_path = excluded.output_path,
              generated_at = excluded.generated_at,
              stats_json = excluded.stats_json
            """,
            (
                digest_date,
                status,
                output_path,
                utc_now().isoformat(),
                json.dumps(stats, ensure_ascii=False),
            ),
        )
        self.conn.commit()

    def list_recent_digests(self, limit: int = 14, include_preview: bool = False) -> list[dict]:
        if include_preview:
            query = """
                SELECT digest_date, status, output_path, generated_at, stats_json
                FROM daily_digest
                ORDER BY digest_date DESC
                LIMIT ?
            """
            rows = self.conn.execute(query, (limit,)).fetchall()
        else:
            query = """
                SELECT digest_date, status, output_path, generated_at, stats_json
                FROM daily_digest
                WHERE status = 'published'
                ORDER BY digest_date DESC
                LIMIT ?
            """
            rows = self.conn.execute(query, (limit,)).fetchall()

        digests: list[dict] = []
        for row in rows:
            item = dict(row)
            item["stats"] = json.loads(item.pop("stats_json"))
            digests.append(item)
        return digests

    def close(self) -> None:
        self.conn.close()
