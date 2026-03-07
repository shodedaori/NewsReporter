from __future__ import annotations

from src.core.base_plugin import BaseSourcePlugin


class HuggingFacePlugin(BaseSourcePlugin):
    section = "huggingface"
    name = "huggingface"

    def fetch(self, since, until, config):  # noqa: ANN001, ANN201
        return []
