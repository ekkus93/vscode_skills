import argparse
import email.utils
import html
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from typing import Any

JsonDict = dict[str, Any]

API_BASE = "https://news.google.com/rss/search"
USER_AGENT = "SharedSkills/1.0 (news-search helper)"
VALID_TIMES = {"day": "1d", "week": "7d", "month": "30d"}
PAYWALLED_SOURCES = {
    "bloomberg",
    "financial times",
    "the information",
    "the wall street journal",
    "wsj",
}
LOW_SIGNAL_AGGREGATORS = {
    "benzinga",
    "newsbreak",
    "twitter",
    "x.com",
    "yahoo",
    "yahoo finance",
}
STOPWORDS = {
    "about",
    "after",
    "amid",
    "also",
    "announces",
    "company",
    "could",
    "from",
    "into",
    "latest",
    "more",
    "news",
    "over",
    "says",
    "search",
    "show",
    "their",
    "there",
    "this",
    "today",
    "week",
    "what",
    "with",
}


def collapse_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def truncate_text(value: str, limit: int = 220) -> str:
    clean = collapse_whitespace(value)
    if len(clean) <= limit:
        return clean
    shortened = clean[: limit - 1].rsplit(" ", 1)[0].rstrip()
    return shortened + "..."


def parse_request(raw_value: str) -> dict[str, Any]:
    parts = [collapse_whitespace(part) for part in raw_value.split("|")]
    parts = [part for part in parts if part]
    if not parts:
        raise ValueError("Search query cannot be empty")

    query = parts[0]
    time_filter = "week"
    limit = 5

    for part in parts[1:]:
        if ":" not in part:
            raise ValueError(f"Unsupported news-search option: {part}")
        key, raw_option = part.split(":", 1)
        key = key.strip().lower()
        option = collapse_whitespace(raw_option).lower()
        if key == "time":
            if option not in VALID_TIMES:
                raise ValueError("time must be one of: day, week, month")
            time_filter = option
        elif key == "limit":
            try:
                limit = int(option)
            except ValueError as exc:
                raise ValueError("limit must be an integer between 1 and 5") from exc
            if limit < 1 or limit > 5:
                raise ValueError("limit must be an integer between 1 and 5")
        else:
            raise ValueError(f"Unsupported news-search option: {key}")

    if not query:
        raise ValueError("Search query cannot be empty")

    return {
        "query": query,
        "time": time_filter,
        "limit": limit,
        "display_query": build_display_query(query, time_filter),
    }


def build_request_from_inputs(
    query: str | None,
    topic: str | None,
    time_filter: str | None,
    limit: int | None,
) -> dict[str, Any]:
    if query and topic:
        raise ValueError("Use either a quoted query or --topic/--query, not both")
    if query:
        return parse_request(query)
    if not topic:
        raise ValueError("Provide either a quoted query or --topic/--query")

    raw_request = collapse_whitespace(topic)
    if time_filter:
        raw_request += f" | time:{collapse_whitespace(time_filter)}"
    if limit is not None:
        raw_request += f" | limit:{limit}"
    return parse_request(raw_request)


def build_display_query(query: str, time_filter: str) -> str:
    parts = [query]
    if time_filter != "week":
        parts.append(f"time:{time_filter}")
    return " | ".join(parts)


def build_feed_url(query: dict[str, Any]) -> str:
    scoped_query = f"{query['query']} when:{VALID_TIMES[query['time']]}"
    params = {
        "q": scoped_query,
        "hl": "en-US",
        "gl": "US",
        "ceid": "US:en",
    }
    return f"{API_BASE}?{urllib.parse.urlencode(params)}"


def request_feed(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8",
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = response.read()
            if isinstance(payload, bytes):
                return payload
            if isinstance(payload, bytearray):
                return bytes(payload)
            return str(payload).encode("utf-8")
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            raise RuntimeError(
                "Google News RSS rate limited the request (HTTP 429); retry later"
            ) from exc
        raise RuntimeError(f"Google News RSS request failed with HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Google News RSS request failed: {exc}") from exc


def parse_pub_date(value: str | None) -> tuple[str, datetime | None]:
    if not value:
        return "not available", None
    try:
        parsed = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        return "not available", None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).strftime("%Y-%m-%d"), parsed.astimezone(timezone.utc)


def normalize_title(title: str) -> str:
    lowered = collapse_whitespace(title).lower()
    lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
    lowered = collapse_whitespace(lowered)
    return lowered


def title_signature(title: str) -> str:
    tokens = [token for token in normalize_title(title).split() if token not in STOPWORDS]
    if not tokens:
        return normalize_title(title)
    return " ".join(tokens[:8])


def source_key(source: str) -> str:
    lowered = collapse_whitespace(source).lower()
    return lowered.replace(" on msn", "")


def source_matches(source: str, candidates: set[str]) -> bool:
    return any(
        source == candidate or source.startswith(candidate + ".")
        for candidate in candidates
    )


def filter_low_signal_sources(items: list[JsonDict]) -> list[JsonDict]:
    filtered = [
        item
        for item in items
        if not source_matches(str(item["source_key"]), LOW_SIGNAL_AGGREGATORS)
    ]
    return filtered if filtered else items


def cleaned_title(title: str, source: str) -> str:
    suffix = f" - {source}"
    if title.lower().endswith(suffix.lower()):
        return title[: -len(suffix)].rstrip()
    return title


def cleaned_description(description: str, title: str, source: str) -> str:
    clean = collapse_whitespace(html.unescape(description).replace("\xa0", " "))
    clean = re.sub(r"\s+&\s+[^ ]+$", "", clean)
    if clean.lower() == title.lower():
        return ""
    if clean.lower().startswith(title.lower()):
        remainder = clean[len(title) :].strip(" -:")
        if remainder.lower() == source.lower():
            return ""
        clean = remainder or clean
    if clean.lower().endswith(source.lower()):
        clean = clean[: -len(source)].rstrip(" -:")
    return clean


def title_words(title: str) -> list[str]:
    return [
        token
        for token in normalize_title(title).split()
        if token not in STOPWORDS and len(token) >= 4
    ]


def parse_feed_items(feed_bytes: bytes) -> list[JsonDict]:
    try:
        root = ET.fromstring(feed_bytes)
    except ET.ParseError as exc:
        raise RuntimeError("Google News RSS returned invalid XML") from exc

    items = root.findall("./channel/item")
    if not items:
        return []

    parsed: list[JsonDict] = []
    for item in items:
        title = collapse_whitespace(item.findtext("title") or "")
        link = collapse_whitespace(item.findtext("link") or "")
        source = collapse_whitespace(item.findtext("source") or "")
        pub_date_text = collapse_whitespace(item.findtext("pubDate") or "")
        description_html = item.findtext("description") or ""
        if not title or not link or not source:
            continue
        clean_title = cleaned_title(title, source)
        description = cleaned_description(
            re.sub(r"<[^>]+>", " ", description_html), clean_title, source
        )
        published_date, published_at = parse_pub_date(pub_date_text)
        parsed.append(
            {
                "title": clean_title,
                "link": link,
                "source": source,
                "source_key": source_key(source),
                "published_date": published_date,
                "published_at": published_at,
                "description": description,
                "signature": title_signature(title),
            }
        )
    return parsed


def dedupe_articles(items: list[JsonDict]) -> list[JsonDict]:
    grouped: dict[str, list[JsonDict]] = {}
    for item in items:
        grouped.setdefault(str(item["signature"]), []).append(item)

    deduped: list[JsonDict] = []
    for signature, group in grouped.items():
        ordered = sorted(
            group,
            key=lambda item: (
                source_priority(str(item["source_key"])),
                -(item["published_at"].timestamp() if item["published_at"] else 0.0),
            ),
        )
        representative = dict(ordered[0])
        representative["signature"] = signature
        representative["coverage_count"] = len(group)
        representative["other_sources"] = [str(item["source"]) for item in ordered[1:4]]
        deduped.append(representative)

    deduped.sort(
        key=lambda item: (
            -(item["coverage_count"]),
            -(item["published_at"].timestamp() if item["published_at"] else 0.0),
            str(item["title"]).lower(),
        )
    )
    return deduped


def source_priority(source: str) -> int:
    if source_matches(source, LOW_SIGNAL_AGGREGATORS):
        return 2
    if source_matches(source, PAYWALLED_SOURCES):
        return 1
    return 0


def theme_summary(items: list[JsonDict], query_text: str) -> str:
    ignored = set(title_words(query_text)) | STOPWORDS
    counts: Counter[str] = Counter()
    for item in items:
        for token in title_words(str(item["title"])):
            if token in ignored:
                continue
            counts[token] += 1
    if not counts:
        return "No single repeated angle dominated the sampled headlines."
    return ", ".join(token for token, _count in counts.most_common(4))


def paywall_note(items: list[JsonDict]) -> str | None:
    paywalled = sorted(
        {
            str(item["source"])
            for item in items
            if source_matches(str(item["source_key"]), PAYWALLED_SOURCES)
        }
    )
    if not paywalled:
        return None
    return ", ".join(paywalled[:3])


def format_results(query: dict[str, Any], items: list[JsonDict]) -> str:
    checked_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    deduped = dedupe_articles(items)[: query["limit"]]
    if not deduped:
        return (
            f"No useful news results were found for '{query['query']}' "
            f"in the last {query['time']}.\n\n"
            "Source: Google News RSS search\n"
            f"Freshness: checked {checked_date}\n"
            "Confidence: low"
        )

    themes = theme_summary(deduped, query["query"])
    duplicates_merged = sum(max(int(item["coverage_count"]) - 1, 0) for item in deduped)
    paywall_sources = paywall_note(deduped)
    lead = (
        f"Recent news coverage for {query['display_query']} is active, with sampled headlines "
        f"clustered around {themes}. Similar headlines from {duplicates_merged} duplicate "
        "result(s) were merged to keep the list focused on distinct stories."
    )
    lines = [
        lead,
        "",
        "Source: Google News RSS search",
        f"Freshness: checked {checked_date}",
        "Confidence: medium",
        "Link note: results use Google News feed links and may redirect through Google News.",
    ]
    if paywall_sources:
        lines.append(f"Paywall note: likely paywalled outlets in sample include {paywall_sources}.")
    lines.append("")

    for index, item in enumerate(deduped, start=1):
        lines.append(f"{index}. {item['title']}")
        lines.append(
            "   "
            + (
                f"Source: {item['source']} | Date: {item['published_date']} | "
                f"Coverage cluster: {item['coverage_count']} similar headline(s)"
            )
        )
        if item["other_sources"]:
            lines.append(f"   Also covered by: {', '.join(item['other_sources'])}")
        if item["description"]:
            lines.append(f"   Summary: {truncate_text(item['description'])}")
        lines.append(f"   Link: {item['link']}")
        lines.append("")

    return "\n".join(lines).rstrip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Search recent news coverage for a topic")
    parser.add_argument(
        "query",
        nargs="?",
        help="Search query, optionally with | filters, quoted as one argument",
    )
    parser.add_argument(
        "--topic",
        "--query",
        dest="topic",
        help="Topic string for direct shell usage",
    )
    parser.add_argument("--time", help="Recency window: day, week, or month")
    parser.add_argument("--limit", type=int, help="Maximum distinct stories to return")
    args = parser.parse_args(argv)

    try:
        request = build_request_from_inputs(args.query, args.topic, args.time, args.limit)
        items = filter_low_signal_sources(
            parse_feed_items(request_feed(build_feed_url(request)))
        )
        print(format_results(request, items))
        return 0
    except (ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())