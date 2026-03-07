from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.plugins.rss_news import RSSNewsPlugin


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


def test_rss_plugin_fetch_and_normalize() -> None:
    rss_xml = """
    <rss version="2.0">
      <channel>
        <title>Demo Feed</title>
        <item>
          <title>OpenAI launches update</title>
          <link>https://example.com/openai-update</link>
          <guid>abc123</guid>
          <description>OpenAI announced a production update.</description>
          <pubDate>Sat, 07 Mar 2026 10:00:00 GMT</pubDate>
        </item>
      </channel>
    </rss>
    """
    plugin = RSSNewsPlugin(session=DummySession(rss_xml))
    since = datetime(2026, 3, 6, 12, 0, tzinfo=timezone.utc)
    until = since + timedelta(hours=24)
    config = {"feeds": [{"name": "Demo Feed", "url": "https://example.com/rss", "weight": 2}]}

    items = plugin.fetch(since=since, until=until, config=config)

    assert len(items) == 1
    assert items[0].title == "OpenAI launches update"
    assert items[0].signals["feed_name"] == "Demo Feed"
    assert items[0].dedup_key
