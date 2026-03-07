from __future__ import annotations

from src.core.models import Item
from src.sections.github.summarizer import build_github_summarizer


def test_build_github_summarizer_fallback_extractive() -> None:
    app_config = {"summarizer": {"mode": "extractive", "github_mode": "extractive"}}
    prompts_config = {}
    summarizer = build_github_summarizer(app_config, prompts_config)

    item = Item(
        section="github",
        source="github",
        source_id="owner/repo",
        title="owner/repo",
        url="https://github.com/owner/repo",
        published_at=None,
        summary_raw="A useful project for testing.",
    )
    summarized = summarizer.summarize_item(item)
    assert summarized.summary_short
