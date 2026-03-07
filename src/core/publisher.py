from __future__ import annotations

import shutil
import tempfile
from pathlib import Path


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
        suffix=".tmp",
    ) as handle:
        handle.write(content)
        tmp_path = Path(handle.name)
    tmp_path.replace(path)


class Publisher:
    def publish(
        self,
        digest_date: str,
        daily_html: str,
        index_html: str,
        output_root: str,
        static_root: str,
    ) -> dict:
        root = Path(output_root)
        daily_path = root / "daily" / digest_date / "index.html"
        index_path = root / "index.html"

        atomic_write_text(daily_path, daily_html)
        atomic_write_text(index_path, index_html)

        styles_src = Path(static_root) / "styles.css"
        styles_dst = root / "styles" / "styles.css"
        styles_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(styles_src, styles_dst)

        return {
            "daily_path": str(daily_path),
            "index_path": str(index_path),
            "root": str(root),
        }
