from __future__ import annotations

from datetime import datetime, timezone

from src.sections.github.plugins.github import GitHubPlugin
from src.sections.github.scorer import GitHubScorer


class DummyResponse:
    def __init__(self, body: str, status_code: int = 200):
        self.text = body
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError("http error")


class DummySession:
    def __init__(self, body: str):
        self.body = body

    def get(self, *_args, **_kwargs) -> DummyResponse:
        return DummyResponse(self.body)


class DummySessionMap:
    def __init__(self, responses: dict[str, DummyResponse]):
        self.responses = responses

    def get(self, url: str, *_args, **_kwargs) -> DummyResponse:
        return self.responses.get(url, DummyResponse("", status_code=404))


def test_github_plugin_parse_trending_html() -> None:
    html_text = """
    <article class="Box-row">
      <h2 class="h3 lh-condensed"><a href="/openai/openai-python"> openai / openai-python </a></h2>
      <p class="col-9 color-fg-muted my-1 pr-4">The official Python library for OpenAI API.</p>
      <span itemprop="programmingLanguage">Python</span>
      <a href="/openai/openai-python/stargazers">12,345</a>
      <a href="/openai/openai-python/forks">2,100</a>
      <span class="d-inline-block float-sm-right">321 stars today</span>
    </article>
    """
    plugin = GitHubPlugin(session=DummySession(html_text))
    items = plugin.fetch(since=None, until=None, config={"trending_url": "https://github.com/trending?since=daily"})

    assert len(items) == 1
    item = items[0]
    assert item.section == "github"
    assert item.source_id == "openai/openai-python"
    assert item.signals["language"] == "Python"
    assert item.signals["stars"] == 12345
    assert item.signals["stars_total"] == 12345
    assert item.signals["stars_today"] == 321


def test_github_plugin_parse_compact_stars_format() -> None:
    html_text = """
    <article class="Box-row">
      <h2 class="h3 lh-condensed"><a href="/openai/codex"> openai / codex </a></h2>
      <span itemprop="programmingLanguage">Python</span>
      <a href="/openai/codex/stargazers"><svg></svg>12.3k</a>
      <a href="/openai/codex/forks"><span>1.2k</span></a>
      <span class="d-inline-block float-sm-right">987 stars today</span>
    </article>
    """
    plugin = GitHubPlugin(session=DummySession(html_text))
    items = plugin.fetch(since=None, until=None, config={"trending_url": "https://github.com/trending?since=daily"})
    assert len(items) == 1
    item = items[0]
    assert item.signals["stars_total"] == 12300
    assert item.signals["forks"] == 1200
    assert item.signals["stars_today"] == 987


def test_github_plugin_readme_fetch_via_api() -> None:
    repo = "openai/openai-python"
    api_url = f"https://api.github.com/repos/{repo}/readme"
    plugin = GitHubPlugin(
        session=DummySessionMap(
            {
                api_url: DummyResponse("# OpenAI Python\nA client library."),
            }
        )
    )
    text = plugin.fetch_readme(repo, config={"request_timeout": 5, "readme_max_chars": 200})
    assert "OpenAI Python" in text


def test_github_scorer_uses_stars_today_and_total() -> None:
    plugin = GitHubPlugin(session=DummySession("<article class=\"Box-row\"></article>"))
    item = plugin._parse_trending_html(
        """
        <article class="Box-row">
          <h2><a href="/owner/repo">owner/repo</a></h2>
          <a href="/owner/repo/stargazers">100</a>
          <span class="d-inline-block float-sm-right">20 stars today</span>
        </article>
        """
    )[0]
    scorer = GitHubScorer({"github": {"stars_today_weight": 1.0, "stars_total_weight": 0.6}})
    score = scorer.score_item(item, now=datetime.now(timezone.utc))
    assert score > 20.0
