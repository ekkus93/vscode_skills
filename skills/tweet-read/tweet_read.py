from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

PROFILE_DIR = Path.home() / "vscode-skills-data" / "tweet-read" / "chromium-profile"
STATUS_HOSTS = {"x.com", "www.x.com", "twitter.com", "www.twitter.com", "mobile.twitter.com"}
LOGIN_URL = "https://x.com/home"
BROWSER_CANDIDATES = (
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/snap/bin/chromium",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
)
REAL_CHROME_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
)


class TweetReadError(Exception):
    pass


class InvalidTweetUrlError(TweetReadError):
    pass


class LoginRequiredError(TweetReadError):
    pass


class DependencyError(TweetReadError):
    pass


@dataclass(frozen=True)
class TweetData:
    text: str
    author: str | None
    handle: str | None
    timestamp: str | None
    tweet_url: str
    media_links: tuple[str, ...]
    quoted_tweet_text: str | None
    reply_count: int | None


def canonicalize_tweet_url(raw_url: str) -> str:
    candidate = raw_url.strip()
    if not candidate:
        raise InvalidTweetUrlError("A single tweet URL is required.")

    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"}:
        raise InvalidTweetUrlError("The input must be an http or https tweet URL.")
    if parsed.netloc.lower() not in STATUS_HOSTS:
        raise InvalidTweetUrlError("The input must be an x.com or twitter.com status URL.")

    path_parts = [part for part in parsed.path.split("/") if part]
    if len(path_parts) < 3 or path_parts[1] != "status":
        raise InvalidTweetUrlError("The input must point to a single tweet status URL.")

    username = path_parts[0]
    status_id = path_parts[2]
    if not re.fullmatch(r"\d+", status_id):
        raise InvalidTweetUrlError("The tweet status ID must be numeric.")

    return f"https://x.com/{username}/status/{status_id}"


def parse_reply_count(label: str | None) -> int | None:
    if not label:
        return None
    match = re.search(r"([\d,]+)\s+repl(?:y|ies)", label, re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1).replace(",", ""))


def _clean_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _resolve_visible_text(payload: dict[str, Any]) -> str:
    article_title = _clean_optional_text(payload.get("article_title"))
    article_body = _clean_optional_text(payload.get("article_body"))
    if article_title and article_body:
        return f"{article_title}\n\n{article_body}"
    if article_body:
        return article_body
    if article_title:
        return article_title
    return str(payload.get("text") or "").strip()


def normalize_extracted_payload(payload: dict[str, Any]) -> TweetData:
    text = _resolve_visible_text(payload)
    if not text:
        raise TweetReadError("Tweet text was not found on the visible page.")

    media_links = tuple(
        link
        for link in dict.fromkeys(str(item).strip() for item in payload.get("media_links", []))
        if link
    )

    tweet_url = str(payload.get("tweet_url") or "").strip()
    if not tweet_url:
        raise TweetReadError("Canonical tweet URL was not found on the page.")

    return TweetData(
        text=text,
        author=_clean_optional_text(payload.get("author")),
        handle=_clean_optional_text(payload.get("handle")),
        timestamp=_clean_optional_text(payload.get("timestamp")),
        tweet_url=tweet_url,
        media_links=media_links,
        quoted_tweet_text=_clean_optional_text(payload.get("quoted_tweet_text")),
        reply_count=parse_reply_count(_clean_optional_text(payload.get("reply_aria_label"))),
    )


def format_tweet_data(tweet: TweetData) -> str:
    lines = ["Tweet read result", ""]
    lines.append(f"Tweet URL: {tweet.tweet_url}")
    lines.append(f"Author: {tweet.author or 'Unknown'}")
    lines.append(f"Handle: {tweet.handle or 'Unknown'}")
    lines.append(f"Timestamp: {tweet.timestamp or 'Unknown'}")
    reply_count = tweet.reply_count if tweet.reply_count is not None else "Not visible"
    lines.append(f"Reply count: {reply_count}")
    lines.append("")
    lines.append("Text:")
    lines.append(tweet.text)
    if tweet.quoted_tweet_text:
        lines.extend(["", "Quoted tweet text:", tweet.quoted_tweet_text])
    if tweet.media_links:
        lines.extend(["", "Media links:"])
        lines.extend(f"- {link}" for link in tweet.media_links)
    return "\n".join(lines)


def format_login_required(profile_dir: Path) -> str:
    return "\n".join(
        [
            "Login required: X requires an authenticated session before this tweet can be read.",
            f"Persistent Chromium profile: {profile_dir}",
            (
                "Next step: run the helper with --login, complete sign-in in the Selenium-"
                "launched browser, "
                "then retry the tweet URL."
            ),
        ]
    )


def open_login_browser(*, profile_dir: Path) -> int:
    driver = _open_driver(profile_dir=profile_dir, headless=False)
    profile_dir.mkdir(parents=True, exist_ok=True)
    try:
        driver.get(LOGIN_URL)
        print("Browser opened for X login.")
        print(f"Profile directory: {profile_dir}")
        print("Complete login in the browser window, then press Enter here to close it.")
        input()
    finally:
        driver.quit()
    return 0


def fetch_tweet(url: str, *, profile_dir: Path, headless: bool = True) -> TweetData:
    driver = _open_driver(profile_dir=profile_dir, headless=headless)
    try:
        driver.get(url)
        _wait_for_page_settle(driver)

        if _login_required(driver):
            raise LoginRequiredError(format_login_required(profile_dir))

        payload = driver.execute_script(
            """
            const article = document.querySelector("article[data-testid='tweet']");
            if (!article) {
              return null;
            }

                        const articleTitleNode = article.querySelector('[data-testid="twitter-article-title"]');
                        const articleBodyNode =
                            article.querySelector('[data-testid="twitterArticleRichTextView"]')
                            || article.querySelector('[data-testid="longformRichTextComponent"]');

                        const textNodes = Array.from(
                            article.querySelectorAll('[data-testid="tweetText"], div[dir="auto"]')
                        ).filter(
                            (node) => !node.closest('[data-testid="User-Name"]')
                                && !node.closest('[data-testid="twitterArticleReadView"]')
                        );

                        const textBlocks = textNodes
                            .map((node) => (node.innerText || '').trim())
                            .filter(Boolean);

            const nameParts = Array.from(
              article.querySelectorAll('[data-testid="User-Name"] span')
            )
              .map((node) => (node.textContent || '').trim())
              .filter(Boolean);
            const handle = nameParts.find((part) => part.startsWith('@')) || null;
            const author = nameParts.find(
              (part) => !part.startsWith('@') && part !== '·'
            ) || null;

            const timeNode = article.querySelector('time');
            const timeLink = timeNode ? timeNode.closest('a') : null;
            const tweetUrl = timeLink ? timeLink.href : window.location.href;

            const replyButton = article.querySelector('[data-testid="reply"]');
            const mediaLinks = [];
            for (const image of article.querySelectorAll('img')) {
              const src = image.getAttribute('src') || '';
              if (
                src.includes('twimg.com/media')
                || src.includes('twimg.com/ext_tw_video_thumb')
              ) {
                mediaLinks.push(src);
              }
            }
            for (const video of article.querySelectorAll('video')) {
              const src = video.getAttribute('src');
              const poster = video.getAttribute('poster');
              if (src) mediaLinks.push(src);
              if (poster) mediaLinks.push(poster);
            }

            return {
              text: textBlocks[0] || '',
              article_title: articleTitleNode ? (articleTitleNode.innerText || '').trim() : null,
              article_body: articleBodyNode ? (articleBodyNode.innerText || '').trim() : null,
              quoted_tweet_text:
                                textBlocks.length > 1 ? textBlocks.slice(1).join('\\n\\n') : null,
              author,
              handle,
              timestamp: timeNode ? timeNode.getAttribute('datetime') : null,
              tweet_url: tweetUrl,
              media_links: mediaLinks,
              reply_aria_label: replyButton ? replyButton.getAttribute('aria-label') : null,
            };
            """
        )
    finally:
        driver.quit()

    if not isinstance(payload, dict):
        raise TweetReadError("Tweet extraction returned an unexpected payload.")
    return normalize_extracted_payload(payload)


def _login_required(driver: Any) -> bool:
    current_url = str(driver.current_url)
    if any(token in current_url for token in ("/i/flow/login", "/login", "?mx=2")):
        return True

    return bool(
        driver.execute_script(
            """
            const text = document.body ? document.body.innerText : '';
            if (text.includes('Sign in to X') || text.includes('Log in to X')) {
              return true;
            }
            return Boolean(
              document.querySelector("input[name='text']")
              || document.querySelector("input[autocomplete='username']")
            );
            """
        )
    )


def _load_selenium() -> tuple[Any, Any, Any, Any, Any]:
    try:
        from selenium import webdriver  # type: ignore[import-not-found]
        from selenium.common.exceptions import WebDriverException  # type: ignore[import-not-found]
        from selenium.webdriver.chrome.options import Options  # type: ignore[import-not-found]
        from selenium.webdriver.chrome.service import Service  # type: ignore[import-not-found]
        from selenium.webdriver.common.by import By  # type: ignore[import-not-found]
    except ImportError as exc:
        raise DependencyError(
            "Selenium is not installed. Run: python3 -m pip install selenium"
        ) from exc
    return webdriver, Options, Service, By, WebDriverException


def _resolve_browser_binary() -> str | None:
    for candidate in BROWSER_CANDIDATES:
        path = Path(candidate)
        if path.exists() and path.is_file():
            return str(path)
    return None


def _browser_user_agent() -> str:
    return REAL_CHROME_USER_AGENT


def _open_driver(*, profile_dir: Path, headless: bool) -> Any:
    webdriver, Options, Service, _, WebDriverException = _load_selenium()
    profile_dir.mkdir(parents=True, exist_ok=True)

    options = Options()
    browser_binary = _resolve_browser_binary()
    if browser_binary:
        options.binary_location = browser_binary
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1440,1200")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(f"--user-agent={_browser_user_agent()}")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    if headless:
        options.add_argument("--headless=new")

    try:
        driver = webdriver.Chrome(service=Service(), options=options)
        driver.execute_cdp_cmd(
            "Network.setUserAgentOverride",
            {"userAgent": _browser_user_agent()},
        )
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        return driver
    except WebDriverException as exc:
        raise DependencyError(
            "Selenium could not start Chrome or Chromium. Install a local Chrome-family browser "
            "and ensure Selenium Manager can provision the matching driver."
        ) from exc


def _wait_for_page_settle(driver: Any, timeout_seconds: float = 15.0) -> None:
    _, _, _, By, _ = _load_selenium()
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        ready_state = driver.execute_script("return document.readyState")
        if ready_state == "complete":
            break
        time.sleep(0.25)

    while time.time() < deadline:
        if _login_required(driver):
            return
        if driver.find_elements(By.CSS_SELECTOR, "article[data-testid='tweet']"):
            return
        time.sleep(0.5)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read one X or Twitter status URL using Selenium with Chrome or Chromium."
    )
    parser.add_argument("tweet_url", nargs="?", help="Single X or Twitter status URL to read.")
    parser.add_argument(
        "--login",
        action="store_true",
        help="Open Chrome or Chromium with the persistent profile so the user can log in manually.",
    )
    parser.add_argument(
        "--show-browser",
        action="store_true",
        help="Run the tweet read in a visible Chromium window instead of headless mode.",
    )
    parser.add_argument(
        "--profile-dir",
        default=str(PROFILE_DIR),
        help=(
            "Persistent Chromium profile directory. Defaults to a path under the user's "
            "home directory."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of formatted text.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    profile_dir = Path(args.profile_dir).expanduser()

    try:
        if args.login:
            return open_login_browser(profile_dir=profile_dir)

        if not args.tweet_url:
            parser.error("tweet_url is required unless --login is used")

        url = canonicalize_tweet_url(args.tweet_url)
        tweet = fetch_tweet(url, profile_dir=profile_dir, headless=not args.show_browser)
    except TweetReadError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.json:
        print(
            json.dumps(
                {
                    "text": tweet.text,
                    "author": tweet.author,
                    "handle": tweet.handle,
                    "timestamp": tweet.timestamp,
                    "tweet_url": tweet.tweet_url,
                    "media_links": list(tweet.media_links),
                    "quoted_tweet_text": tweet.quoted_tweet_text,
                    "reply_count": tweet.reply_count,
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(format_tweet_data(tweet))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
