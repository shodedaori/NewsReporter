from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clean generated output directories")
    parser.add_argument(
        "--target",
        choices=["preview", "site", "all"],
        default="all",
        help="Which output to clean",
    )
    return parser.parse_args()


def remove_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True, exist_ok=True)


def main() -> int:
    args = parse_args()
    output_root = Path("output")

    if args.target in ("preview", "all"):
        remove_dir(output_root / "preview" / "site")
        print("Cleaned: output/preview/site")
    if args.target in ("site", "all"):
        remove_dir(output_root / "site")
        print("Cleaned: output/site")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
