import importlib.util
import pathlib
from types import ModuleType

import pytest


def load_module(name: str, path: pathlib.Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    loader = spec.loader
    assert loader is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


MODULE_PATH = (
  pathlib.Path(__file__).resolve().parent
    / "news_search.py"
)
news_search = load_module("news_search", MODULE_PATH)


SAMPLE_FEED = b"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<rss version=\"2.0\">
  <channel>
    <item>
      <title>OpenAI signs new enterprise deal</title>
      <link>https://news.google.com/rss/articles/AAA</link>
      <pubDate>Thu, 13 Mar 2026 10:00:00 GMT</pubDate>
      <description>
        OpenAI expanded its enterprise footprint with a new partner announcement.
      </description>
      <source>Reuters</source>
    </item>
    <item>
      <title>OpenAI signs new enterprise deal</title>
      <link>https://news.google.com/rss/articles/BBB</link>
      <pubDate>Thu, 13 Mar 2026 09:00:00 GMT</pubDate>
      <description>Similar coverage from a second outlet.</description>
      <source>CNBC</source>
    </item>
    <item>
      <title>OpenAI launches new agent tooling</title>
      <link>https://news.google.com/rss/articles/CCC</link>
      <pubDate>Wed, 12 Mar 2026 08:00:00 GMT</pubDate>
      <description>Another distinct story about OpenAI products.</description>
      <source>Bloomberg</source>
    </item>
  </channel>
</rss>"""


def test_parse_request_with_filters() -> None:
    result = news_search.parse_request("openai | time:day | limit:3")
    assert result["query"] == "openai"
    assert result["time"] == "day"
    assert result["limit"] == 3


def test_build_request_from_inputs_accepts_flags() -> None:
  result = news_search.build_request_from_inputs(None, "openai", "month", 2)
  assert result["query"] == "openai"
  assert result["time"] == "month"
  assert result["limit"] == 2


def test_main_accepts_query_flag_alias(
  monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
  monkeypatch.setattr(news_search, "request_feed", lambda _url: SAMPLE_FEED)
  exit_code = news_search.main(["--query", "openai", "--time", "month", "--limit", "2"])
  captured = capsys.readouterr()
  assert exit_code == 0
  assert "Recent news coverage for openai | time:month" in captured.out


def test_build_feed_url_uses_google_news_query_scoping() -> None:
    query = news_search.parse_request("nvidia | time:month")
    url = news_search.build_feed_url(query)
    assert "news.google.com/rss/search?" in url
    assert "when%3A30d" in url


def test_parse_feed_items_extracts_source_and_date() -> None:
    items = news_search.parse_feed_items(SAMPLE_FEED)
    assert len(items) == 3
    assert items[0]["source"] == "Reuters"
    assert items[0]["published_date"] == "2026-03-13"


def test_dedupe_articles_merges_duplicate_headlines() -> None:
    items = news_search.parse_feed_items(SAMPLE_FEED)
    deduped = news_search.dedupe_articles(items)
    assert len(deduped) == 2
    assert deduped[0]["coverage_count"] == 2
    assert "CNBC" in deduped[0]["other_sources"]


def test_paywall_note_detects_likely_paywalled_sources() -> None:
    items = news_search.parse_feed_items(SAMPLE_FEED)
    assert news_search.paywall_note(items) == "Bloomberg"


def test_filter_low_signal_sources_prefers_news_publishers() -> None:
  items = news_search.parse_feed_items(SAMPLE_FEED) + [
    {
      "title": "OpenAI summit thread",
      "link": "https://news.google.com/rss/articles/DDD",
      "source": "x.com",
      "source_key": "x.com",
      "published_date": "2026-03-13",
      "published_at": None,
      "description": "",
      "signature": "openai summit thread",
    }
  ]
  filtered = news_search.filter_low_signal_sources(items)
  assert all(item["source"] != "x.com" for item in filtered)


def test_format_results_mentions_duplicates_and_link_note() -> None:
    query = news_search.parse_request("openai")
    rendered = news_search.format_results(query, news_search.parse_feed_items(SAMPLE_FEED))
    assert "duplicate result" in rendered
    assert "Link note: results use Google News feed links" in rendered
    assert "Paywall note: likely paywalled outlets" in rendered