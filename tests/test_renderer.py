from __future__ import annotations

from src.web.renderer import Renderer


def test_renderer_smoke_templates() -> None:
    renderer = Renderer("src/web/templates")

    daily_html = renderer.render_daily(
        {
            "site_name": "NewsReporter",
            "page_title": "2026-03-07 News Digest",
            "page_description": "desc",
            "digest_date": "2026-03-07",
            "generated_at": "2026-03-07T12:00:00+00:00",
            "stats": {"unique_count": 1},
            "items": [
                {
                    "title": "Test title",
                    "url": "https://example.com",
                    "published_at": "2026-03-07T11:00:00+00:00",
                    "summary_short": "Short summary",
                    "signals": {"score": 10, "feed_name": "Test"},
                }
            ],
        }
    )
    index_html = renderer.render_index(
        {
            "site_name": "NewsReporter",
            "page_title": "Home",
            "page_description": "desc",
            "latest": {"digest_date": "2026-03-07", "stats": {"item_count": 1, "unique_count": 1}},
            "digests": [{"digest_date": "2026-03-07", "stats": {"unique_count": 1, "failures": 0}}],
        }
    )

    assert "2026-03-07 News Digest" in daily_html
    assert "Back to all digests" in daily_html
    assert "Latest Digest" in index_html
