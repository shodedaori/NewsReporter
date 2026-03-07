from __future__ import annotations

from src.core.base_plugin import BaseSourcePlugin


class ArxivPlugin(BaseSourcePlugin):
    section = "arxiv"
    name = "arxiv"

    def fetch(self, since, until, config):  # noqa: ANN001, ANN201
        return []
