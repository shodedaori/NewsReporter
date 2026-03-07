from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape


class Renderer:
    def __init__(self, templates_dir: str):
        self.templates_dir = Path(templates_dir)
        self.env = Environment(
            loader=FileSystemLoader(self.templates_dir),
            autoescape=select_autoescape(enabled_extensions=("html",)),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render_daily(self, context: dict) -> str:
        template = self.env.get_template("daily.html")
        return template.render(**context)

    def render_index(self, context: dict) -> str:
        template = self.env.get_template("index.html")
        return template.render(**context)
