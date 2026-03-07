from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.store import Store


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clean NewsReporter sqlite database for tests")
    parser.add_argument("--db-path", default="data/state.db", help="SQLite db path")
    parser.add_argument(
        "--reinit",
        action="store_true",
        help="Recreate an empty database with schema after cleanup",
    )
    return parser.parse_args()


def remove_db_files(db_path: Path) -> None:
    for suffix in ("", "-wal", "-shm"):
        file_path = Path(str(db_path) + suffix)
        if file_path.exists():
            file_path.unlink()


def main() -> int:
    args = parse_args()
    db_path = Path(args.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    remove_db_files(db_path)
    print(f"Removed database files for: {db_path}")

    if args.reinit:
        store = Store(str(db_path))
        store.close()
        print(f"Reinitialized empty schema: {db_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
