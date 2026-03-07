from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.core.models import Item
from src.sections.arxiv.plugins.arxiv import ArxivPlugin
from src.sections.arxiv.scorer import ArxivScorer


class DummyResponse:
    def __init__(self, body: str):
        self.content = body.encode("utf-8")

    def raise_for_status(self) -> None:
        return None


class DummySession:
    def __init__(self, body: str):
        self.body = body

    def get(self, *_args, **_kwargs) -> DummyResponse:
        return DummyResponse(self.body)


def test_arxiv_plugin_fetch_and_normalize() -> None:
    atom_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <id>http://arxiv.org/abs/2603.00001v1</id>
        <updated>2026-03-07T08:00:00Z</updated>
        <published>2026-03-07T07:00:00Z</published>
        <title>Reasoning with Multimodal Agents</title>
        <summary>We propose a new framework for multimodal reasoning.</summary>
        <author><name>Alice</name></author>
        <author><name>Bob</name></author>
        <category term="cs.AI"/>
        <category term="cs.LG"/>
      </entry>
    </feed>
    """
    plugin = ArxivPlugin(session=DummySession(atom_xml))
    since = datetime(2026, 3, 6, 12, 0, tzinfo=timezone.utc)
    until = since + timedelta(hours=24)
    items = plugin.fetch(
        since=since,
        until=until,
        config={"keywords": ["reasoning"], "categories": ["cs.AI"], "max_results": 10},
    )

    assert len(items) == 1
    item = items[0]
    assert item.section == "arxiv"
    assert item.source == "arxiv"
    assert item.source_id == "2603.00001v1"
    assert "cs.AI" in item.signals["categories"]


def test_arxiv_scorer_assigns_positive_score() -> None:
    item = Item(
        section="arxiv",
        source="arxiv",
        source_id="2603.00002v1",
        title="Planning and Reasoning for Agents",
        url="http://arxiv.org/abs/2603.00002v1",
        published_at=datetime(2026, 3, 7, 9, 0, tzinfo=timezone.utc),
        summary_raw="This paper studies multimodal planning.",
        tags=["cs.AI"],
        signals={"categories": ["cs.AI", "cs.LG"]},
    )
    scorer = ArxivScorer(
        {
            "arxiv": {
                "topic_weight": 6,
                "category_bonus": 8,
                "keywords": ["reasoning", "planning", "multimodal"],
                "core_categories": ["cs.ai", "cs.lg"],
            }
        }
    )
    score = scorer.score_item(item, now=datetime(2026, 3, 7, 12, 0, tzinfo=timezone.utc))
    assert score > 0
    assert item.signals["topic_hits"] >= 2
