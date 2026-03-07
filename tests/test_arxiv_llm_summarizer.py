from __future__ import annotations

from src.core.models import Item
from src.sections.arxiv.summarizer import build_arxiv_summarizer


def test_build_arxiv_summarizer_fallback_extractive() -> None:
    app_config = {"summarizer": {"mode": "extractive", "arxiv_mode": "extractive"}}
    prompts_config = {}
    summarizer = build_arxiv_summarizer(app_config, prompts_config)

    item = Item(
        section="arxiv",
        source="arxiv",
        source_id="2603.00003v1",
        title="Test arXiv title",
        url="https://arxiv.org/abs/2603.00003",
        published_at=None,
        summary_raw="This is an abstract for test.",
        signals={"authors": ["A"], "categories": ["cs.AI"]},
    )
    summarized = summarizer.summarize_item(item)
    assert summarized.summary_short
