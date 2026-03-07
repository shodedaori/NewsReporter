PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

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
