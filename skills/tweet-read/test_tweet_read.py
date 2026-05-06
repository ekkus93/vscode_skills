import importlib.util
import pathlib
import sys
from types import ModuleType

import pytest


def load_module(name: str, path: pathlib.Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    loader = spec.loader
    assert loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


MODULE_PATH = pathlib.Path(__file__).resolve().parent / "tweet_read.py"
tweet_read = load_module("tweet_read", MODULE_PATH)


def test_canonicalize_tweet_url_normalizes_hosts_and_query() -> None:
    url = tweet_read.canonicalize_tweet_url(
        "https://twitter.com/Interior/status/463440424141459456?s=20&t=abc"
    )
    assert url == "https://x.com/Interior/status/463440424141459456"


def test_canonicalize_tweet_url_rejects_non_status_url() -> None:
    with pytest.raises(tweet_read.InvalidTweetUrlError):
        tweet_read.canonicalize_tweet_url("https://x.com/githubcopilot")


def test_parse_reply_count_handles_visible_count() -> None:
    assert tweet_read.parse_reply_count("1,234 replies. Reply") == 1234


def test_parse_reply_count_returns_none_when_not_visible() -> None:
    assert tweet_read.parse_reply_count("Reply") is None


def test_normalize_extracted_payload_dedupes_media_and_parses_reply_count() -> None:
    tweet = tweet_read.normalize_extracted_payload(
        {
            "text": "Example tweet text",
            "author": "Example Author",
            "handle": "@example",
            "timestamp": "2026-05-06T12:00:00.000Z",
            "tweet_url": "https://x.com/example/status/123",
            "media_links": [
                "https://pbs.twimg.com/media/example.jpg",
                "https://pbs.twimg.com/media/example.jpg",
                "https://video.twimg.com/ext/example.mp4",
            ],
            "quoted_tweet_text": "Quoted text",
            "reply_aria_label": "27 replies. Reply",
        }
    )
    assert tweet.author == "Example Author"
    assert tweet.handle == "@example"
    assert tweet.reply_count == 27
    assert tweet.media_links == (
        "https://pbs.twimg.com/media/example.jpg",
        "https://video.twimg.com/ext/example.mp4",
    )


def test_normalize_extracted_payload_prefers_full_article_text() -> None:
    tweet = tweet_read.normalize_extracted_payload(
        {
            "text": "Article title only",
            "article_title": "Article title only",
            "article_body": "First paragraph.\n\nSecond paragraph.",
            "author": "Example Author",
            "handle": "@example",
            "timestamp": "2026-05-06T12:00:00.000Z",
            "tweet_url": "https://x.com/example/status/123",
            "media_links": [],
            "quoted_tweet_text": None,
            "reply_aria_label": "12 replies. Reply",
        }
    )
    assert tweet.text == "Article title only\n\nFirst paragraph.\n\nSecond paragraph."
    assert tweet.reply_count == 12


def test_format_login_required_mentions_profile_path() -> None:
    profile_dir = pathlib.Path("/home/tester/vscode-skills-data/tweet-read/chromium-profile")
    message = tweet_read.format_login_required(profile_dir)
    assert "Login required" in message
    assert str(profile_dir) in message
    assert "--login" in message


def test_browser_user_agent_looks_like_normal_chrome() -> None:
    user_agent = tweet_read._browser_user_agent()
    assert "Mozilla/5.0" in user_agent
    assert "Chrome/" in user_agent
    assert "HeadlessChrome" not in user_agent
    assert "automation" not in user_agent.lower()
    assert "test" not in user_agent.lower()


def test_main_emits_json_output(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    fake_tweet = tweet_read.TweetData(
        text="Hello from X",
        author="Example",
        handle="@example",
        timestamp="2026-05-06T12:00:00.000Z",
        tweet_url="https://x.com/example/status/123",
        media_links=("https://pbs.twimg.com/media/example.jpg",),
        quoted_tweet_text=None,
        reply_count=4,
    )
    monkeypatch.setattr(tweet_read, "fetch_tweet", lambda *args, **kwargs: fake_tweet)
    exit_code = tweet_read.main(["https://x.com/example/status/123", "--json"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert '"author": "Example"' in captured.out
    assert '"reply_count": 4' in captured.out
