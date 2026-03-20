import argparse
import importlib.util
import pathlib
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html.parser import HTMLParser
from types import ModuleType
from typing import Any

JsonDict = dict[str, Any]

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
USER_AGENT = "SharedSkills/1.0 (company-research helper)"
BING_SEARCH_BASE = "https://www.bing.com/search"
VALID_NEWS_WINDOWS = {"day", "week", "month"}
BUSINESS_CONTEXT_HINTS = [
    "insurance",
    "insurer",
    "fintech",
    "payments",
    "banking",
    "lending",
    "developer",
    "developers",
    "framework",
    "infrastructure",
    "cloud",
    "hosting",
    "security",
    "analytics",
    "observability",
    "database",
    "commerce",
    "ecommerce",
    "healthcare",
    "biotech",
    "pharma",
    "logistics",
]
COMPANY_NEWS_SIGNAL_HINTS = [
    "acquisition",
    "api",
    "app",
    "earnings",
    "funding",
    "inc",
    "insurance",
    "investment",
    "investor",
    "partnership",
    "platform",
    "product",
    "shares",
    "software",
    "stake",
    "stock",
    "valuation",
]
COMPANY_NEWS_LOW_SIGNAL_SOURCES = {
    "blockchain.news",
    "mexc",
    "tradingview",
    "traders union",
}
PREFERRED_COMPANY_NEWS_SOURCES = {
    "ap news",
    "associated press",
    "bloomberg",
    "financial times",
    "reuters",
    "the information",
    "the wall street journal",
    "wsj",
}
MID_SIGNAL_COMPANY_NEWS_SOURCES = {
    "the github blog",
}
SEARCH_DOMAIN_BLACKLIST = {
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "reddit.com",
    "wikipedia.org",
    "x.com",
    "youtube.com",
    "zhihu.com",
}
COMPANY_SUFFIX_TOKENS = {
    "app",
    "co",
    "company",
    "corp",
    "corporation",
    "inc",
    "labs",
    "ltd",
    "systems",
    "tech",
    "technologies",
}
DOC_KEYWORDS = ["docs", "documentation", "guide", "api", "developer", "learn"]
PRICING_KEYWORDS = ["pricing", "plans", "billing", "enterprise"]
CAREERS_KEYWORDS = ["careers", "jobs", "hiring", "join us", "work with us"]
ABOUT_KEYWORDS = ["about", "company", "mission", "story"]
PRODUCT_KEYWORDS = ["product", "products", "platform", "features", "solutions"]
DOC_PATH_HINTS = ["/docs", "/documentation", "/developers", "/developer", "/api", "/learn"]
PRICING_PATH_HINTS = ["/pricing", "/plans", "/billing"]
CAREERS_PATH_HINTS = ["/careers", "/jobs", "/job", "/join", "/hiring"]
ABOUT_PATH_HINTS = ["/about", "/company", "/mission", "/story"]


def load_module(name: str, path: pathlib.Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load helper module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


news_search = load_module(
    "company_news_search",
    SCRIPT_DIR.parent / "news-search" / "news_search.py",
)


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title_parts: list[str] = []
        self.meta_description: str | None = None
        self.links: list[JsonDict] = []
        self.text_parts: list[str] = []
        self._inside_title = False
        self._current_href: str | None = None
        self._current_link_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag == "title":
            self._inside_title = True
        elif tag == "meta":
            name = (attrs_dict.get("name") or attrs_dict.get("property") or "").lower()
            if name in {"description", "og:description"}:
                content = collapse_whitespace(attrs_dict.get("content") or "")
                if content and not self.meta_description:
                    self.meta_description = content
        elif tag == "a":
            href = attrs_dict.get("href")
            if href:
                self._current_href = href
                self._current_link_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._inside_title = False
        elif tag == "a" and self._current_href:
            self.links.append(
                {
                    "href": self._current_href,
                    "text": collapse_whitespace(" ".join(self._current_link_text)),
                }
            )
            self._current_href = None
            self._current_link_text = []

    def handle_data(self, data: str) -> None:
        clean = collapse_whitespace(data)
        if not clean:
            return
        if self._inside_title:
            self.title_parts.append(clean)
        if self._current_href is not None:
            self._current_link_text.append(clean)
        if len(self.text_parts) < 1000:
            self.text_parts.append(clean)


def collapse_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def truncate_text(value: str, limit: int = 220) -> str:
    clean = collapse_whitespace(value)
    if len(clean) <= limit:
        return clean
    shortened = clean[: limit - 1].rsplit(" ", 1)[0].rstrip()
    return shortened + "..."


def normalize_url(value: str) -> str:
    parsed = urllib.parse.urlparse(value)
    cleaned = parsed._replace(fragment="", query="")
    return urllib.parse.urlunparse(cleaned).rstrip("/") or value


def pretty_host(url: str) -> str:
    host = urllib.parse.urlparse(url).netloc.lower()
    return host.removeprefix("www.")


def company_tokens(name: str) -> list[str]:
    tokens = [token for token in re.findall(r"[a-z0-9]+", name.lower()) if len(token) >= 3]
    return [token for token in tokens if token not in COMPANY_SUFFIX_TOKENS]


def request_text(url: str, accept: str = "text/html,application/xhtml+xml") -> tuple[str, str, str]:
    request = urllib.request.Request(
        url,
        headers={"Accept": accept, "User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            final_url = response.geturl()
            content_type = response.headers.get("Content-Type", "")
            body = response.read().decode("utf-8", errors="replace")
        return final_url, content_type, body
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise RuntimeError(f"Official site page was not found: {url}") from exc
        if exc.code == 429:
            raise RuntimeError(
                f"Official site rate limited the request (HTTP 429): {url}"
            ) from exc
        raise RuntimeError(f"Official site request failed with HTTP {exc.code}: {url}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Official site request failed for {url}: {exc}") from exc


def parse_request(raw_value: str) -> dict[str, Any]:
    parts = [collapse_whitespace(part) for part in raw_value.split("|")]
    parts = [part for part in parts if part]
    if not parts:
        raise ValueError("Company target cannot be empty")

    target = parts[0]
    company_name: str | None = None
    site_url: str | None = None
    news_window = "month"
    news_limit = 3

    if target.startswith(("http://", "https://")):
        site_url = normalize_url(target)
    else:
        company_name = target

    for part in parts[1:]:
        if ":" not in part:
            raise ValueError(f"Unsupported company-research option: {part}")
        key, raw_option = part.split(":", 1)
        key = key.strip().lower()
        option = collapse_whitespace(raw_option)
        if key == "site":
            if not option.startswith(("http://", "https://")):
                raise ValueError("site must be a full http:// or https:// URL")
            site_url = normalize_url(option)
        elif key == "news":
            lowered = option.lower()
            if lowered not in VALID_NEWS_WINDOWS:
                raise ValueError("news must be one of: day, week, month")
            news_window = lowered
        elif key == "limit":
            try:
                news_limit = int(option)
            except ValueError as exc:
                raise ValueError("limit must be an integer between 1 and 3") from exc
            if news_limit < 1 or news_limit > 3:
                raise ValueError("limit must be an integer between 1 and 3")
        else:
            raise ValueError(f"Unsupported company-research option: {key}")

    if not company_name and not site_url:
        raise ValueError("Company target cannot be empty")

    return {
        "company_name": company_name,
        "site_url": site_url,
        "news_window": news_window,
        "news_limit": news_limit,
    }


def build_request_from_inputs(
    query: str | None,
    company_name: str | None,
    site_url: str | None,
    news_window: str | None,
    limit: int | None,
) -> dict[str, Any]:
    if query and (company_name or site_url or news_window or limit is not None):
        request = parse_request(query)
    elif query:
        return parse_request(query)
    else:
        request = {
            "company_name": None,
            "site_url": None,
            "news_window": "month",
            "news_limit": 3,
        }

    if company_name:
        request["company_name"] = collapse_whitespace(company_name)
    if site_url:
        normalized_site = collapse_whitespace(site_url)
        if not normalized_site.startswith(("http://", "https://")):
            raise ValueError("site must be a full http:// or https:// URL")
        request["site_url"] = normalize_url(normalized_site)
    if news_window:
        normalized_window = collapse_whitespace(news_window).lower()
        if normalized_window not in VALID_NEWS_WINDOWS:
            raise ValueError("news must be one of: day, week, month")
        request["news_window"] = normalized_window
    if limit is not None:
        if limit < 1 or limit > 3:
            raise ValueError("limit must be an integer between 1 and 3")
        request["news_limit"] = limit

    if not request["company_name"] and not request["site_url"]:
        raise ValueError("Provide a company name, official site URL, or query string")

    return request


def parse_search_results(feed_xml: str) -> list[JsonDict]:
    try:
        root = ET.fromstring(feed_xml)
    except ET.ParseError as exc:
        raise RuntimeError("Bing search RSS returned invalid XML") from exc
    items = root.findall("./channel/item")
    parsed: list[JsonDict] = []
    for item in items:
        title = collapse_whitespace(item.findtext("title") or "")
        link = collapse_whitespace(item.findtext("link") or "")
        description = collapse_whitespace(item.findtext("description") or "")
        if title and link:
            parsed.append({"title": title, "link": link, "description": description})
    return parsed


def candidate_score(company_name: str, item: JsonDict) -> int:
    host = pretty_host(str(item["link"]))
    if any(host == blocked or host.endswith("." + blocked) for blocked in SEARCH_DOMAIN_BLACKLIST):
        return -100
    tokens = company_tokens(company_name)
    host_text = re.sub(r"[^a-z0-9]", " ", host.lower())
    title = str(item["title"]).lower()
    description = str(item.get("description") or "").lower()
    full_name = collapse_whitespace(company_name).lower()
    host_hits = sum(1 for token in tokens if token in host_text)
    title_hits = sum(1 for token in tokens if token in title)
    score = 0
    if host_hits:
        score += 3 + host_hits
    if full_name in title:
        score += 3
    score += min(title_hits, 2)
    if "official site" in title or "official site" in description:
        score += 1
    if host.endswith((".com", ".io", ".dev", ".ai", ".app", ".co")):
        score += 1
    return score


def resolve_site_from_search(company_name: str) -> str:
    query = urllib.parse.quote(f"{company_name} official site")
    feed_url = f"{BING_SEARCH_BASE}?format=rss&q={query}"
    _final_url, _content_type, body = request_text(feed_url, accept="application/rss+xml")
    items = parse_search_results(body)
    if not items:
        raise RuntimeError(
            "Could not resolve an official site from the company name alone; "
            "provide `site:https://...`"
        )
    ranked = sorted(items, key=lambda item: candidate_score(company_name, item), reverse=True)
    best = ranked[0]
    if candidate_score(company_name, best) < 5:
        raise RuntimeError(
            "Could not confidently resolve the official site from the company name alone; "
            "provide `site:https://...`"
        )
    return normalize_url(str(best["link"]))


def same_site(url: str, root_host: str) -> bool:
    host = pretty_host(url)
    return host == root_host or host.endswith("." + root_host)


def keyword_match(haystack: str, keywords: list[str]) -> bool:
    lowered = haystack.lower()
    return any(keyword in lowered for keyword in keywords)


def parse_page(base_url: str, body: str) -> JsonDict:
    parser = PageParser()
    parser.feed(body)
    root_host = pretty_host(base_url)
    links: list[JsonDict] = []
    for link in parser.links[:150]:
        href = link.get("href") or ""
        if href.startswith(("mailto:", "javascript:")):
            continue
        absolute = normalize_url(urllib.parse.urljoin(base_url, href))
        if not absolute.startswith(("http://", "https://")):
            continue
        if not same_site(absolute, root_host):
            continue
        links.append({"href": absolute, "text": collapse_whitespace(link.get("text") or "")})

    text = collapse_whitespace(" ".join(parser.text_parts[:250]))
    title = collapse_whitespace(" ".join(parser.title_parts)) or None
    summary = parser.meta_description or truncate_text(text, limit=240) if text else None
    return {
        "title": title,
        "summary": summary,
        "text": text,
        "links": links,
    }


def pick_first_link(links: list[JsonDict], keywords: list[str]) -> str | None:
    for link in links:
        haystack = f"{link['text']} {link['href']}"
        if keyword_match(haystack, keywords):
            return str(link["href"])
    return None


def score_category_link(link: JsonDict, path_hints: list[str], text_hints: list[str]) -> int:
    href = str(link["href"])
    text = collapse_whitespace(str(link["text"])).lower()
    path = urllib.parse.urlparse(href).path.lower().rstrip("/") or "/"
    score = 0
    for hint in path_hints:
        if path == hint or path.startswith(hint + "/"):
            score += 5
        elif hint in path:
            score += 3
    for hint in text_hints:
        if text == hint or text.startswith(hint + " ") or text.endswith(" " + hint):
            score += 2
        elif hint in text:
            score += 1
    return score


def pick_best_category_link(
    links: list[JsonDict],
    path_hints: list[str],
    text_hints: list[str],
) -> str | None:
    best_link: str | None = None
    best_score = 0
    for link in links:
        score = score_category_link(link, path_hints, text_hints)
        if score > best_score:
            best_score = score
            best_link = str(link["href"])
    return best_link


def product_links(links: list[JsonDict]) -> list[JsonDict]:
    chosen: list[JsonDict] = []
    seen: set[str] = set()
    for link in links:
        haystack = f"{link['text']} {link['href']}"
        if not keyword_match(haystack, PRODUCT_KEYWORDS):
            continue
        href = str(link["href"])
        if href in seen:
            continue
        chosen.append(link)
        seen.add(href)
        if len(chosen) == 3:
            break
    return chosen


def label_from_title(title: str | None, site_url: str) -> str:
    if title:
        for separator in (" | ", " - ", " — ", ": "):
            if separator in title:
                candidate = collapse_whitespace(title.split(separator, 1)[0])
                if candidate:
                    return candidate
        if title:
            return title
    host = pretty_host(site_url)
    primary = host.split(".")[0]
    return primary.capitalize()


def careers_signal(careers_url: str | None, page_text: str) -> str:
    if careers_url:
        return "Careers/jobs page found on the official site."
    if keyword_match(page_text, CAREERS_KEYWORDS):
        return "Hiring or careers wording appears on the official homepage text."
    return "No clear hiring signal was found on the inspected official site pages."


def filter_company_news_sources(items: list[JsonDict]) -> list[JsonDict]:
    filtered = [
        item
        for item in items
        if not news_search.source_matches(
            str(item["source_key"]),
            COMPANY_NEWS_LOW_SIGNAL_SOURCES,
        )
    ]
    return filtered if filtered else items


def business_context_hints(summary_text: str | None, page_text: str) -> list[str]:
    haystack = collapse_whitespace(f"{summary_text or ''} {page_text}").lower()
    hints: list[str] = []
    for hint in BUSINESS_CONTEXT_HINTS:
        if re.search(rf"\b{re.escape(hint)}\b", haystack) and hint not in hints:
            hints.append(hint)
        if len(hints) == 3:
            break
    return hints


def build_news_query_candidates(
    company_name: str,
    summary_text: str | None,
    page_text: str,
) -> list[str]:
    candidates = [collapse_whitespace(company_name)]
    for hint in business_context_hints(summary_text, page_text)[:1]:
        quoted = f'"{company_name}" {hint}'
        plain = f"{company_name} {hint}"
        if quoted not in candidates:
            candidates.append(quoted)
        if plain not in candidates:
            candidates.append(plain)
    return candidates


def company_name_mentioned_case_sensitive(item: JsonDict, company_name: str) -> bool:
    return company_name in str(item.get("title") or "") or company_name in str(
        item.get("description") or ""
    )


def item_mentions_context(item: JsonDict, context_hints: list[str]) -> bool:
    haystack = collapse_whitespace(
        f"{item.get('title') or ''} {item.get('description') or ''}"
    ).lower()
    return any(re.search(rf"\b{re.escape(hint)}\b", haystack) for hint in context_hints)


def company_news_item_score(item: JsonDict, company_name: str, context_hints: list[str]) -> int:
    haystack = collapse_whitespace(
        f"{item.get('title') or ''} {item.get('description') or ''}"
    ).lower()
    score = 0
    if company_name_mentioned_case_sensitive(item, company_name):
        score += 2
    elif company_name.lower() in haystack:
        score += 1
    if item_mentions_context(item, context_hints):
        score += 2
    signal_hits = sum(
        1 for hint in COMPANY_NEWS_SIGNAL_HINTS if re.search(rf"\b{re.escape(hint)}\b", haystack)
    )
    score += min(signal_hits, 2)
    return score


def request_company_news_items(query_text: str, news_window: str, limit: int) -> list[JsonDict]:
    query = news_search.parse_request(f"{query_text} | time:{news_window} | limit:{limit}")
    items = news_search.filter_low_signal_sources(
        news_search.parse_feed_items(news_search.request_feed(news_search.build_feed_url(query)))
    )
    items = filter_company_news_sources(items)
    deduped = news_search.dedupe_articles(items)
    return rank_company_news_items(deduped)


def company_news_source_priority(source: str) -> int:
    if news_search.source_matches(source, PREFERRED_COMPANY_NEWS_SOURCES):
        return 0
    if news_search.source_matches(source, MID_SIGNAL_COMPANY_NEWS_SOURCES):
        return 1
    if news_search.source_matches(source, COMPANY_NEWS_LOW_SIGNAL_SOURCES):
        return 3
    return 2


def rank_company_news_items(items: list[JsonDict]) -> list[JsonDict]:
    return sorted(
        items,
        key=lambda item: (
            company_news_source_priority(str(item["source_key"])),
            -(item["published_at"].timestamp() if item["published_at"] else 0.0),
            str(item["title"]).lower(),
        ),
    )


def build_news_items(
    company_name: str,
    news_window: str,
    limit: int,
    summary_text: str | None,
    page_text: str,
) -> list[JsonDict]:
    context_hints = business_context_hints(summary_text, page_text)
    candidates = build_news_query_candidates(company_name, summary_text, page_text)
    best_items: list[JsonDict] = []
    best_score = -1
    for query_text in candidates:
        ranked = request_company_news_items(query_text, news_window, limit)
        candidate_items = ranked[:limit]
        candidate_score = sum(
            company_news_item_score(item, company_name, context_hints)
            for item in candidate_items
        )
        if candidate_score > best_score:
            best_score = candidate_score
            best_items = candidate_items
    if best_score < 4:
        return []
    return best_items


def research_company(request: dict[str, Any]) -> JsonDict:
    resolved_from_search = False
    site_url = request["site_url"]
    company_name = request["company_name"]
    if site_url is None:
        if company_name is None:
            raise RuntimeError("Company name or site URL is required")
        site_url = resolve_site_from_search(company_name)
        resolved_from_search = True

    final_url, _content_type, body = request_text(site_url)
    page = parse_page(final_url, body)
    label = company_name or label_from_title(page["title"], final_url)
    docs_url = pick_best_category_link(page["links"], DOC_PATH_HINTS, DOC_KEYWORDS)
    pricing_url = pick_best_category_link(page["links"], PRICING_PATH_HINTS, PRICING_KEYWORDS)
    careers_url = pick_best_category_link(page["links"], CAREERS_PATH_HINTS, CAREERS_KEYWORDS)
    about_url = pick_best_category_link(page["links"], ABOUT_PATH_HINTS, ABOUT_KEYWORDS)
    products = product_links(page["links"])
    news_items = build_news_items(
        label,
        request["news_window"],
        request["news_limit"],
        page["summary"],
        str(page["text"]),
    )
    return {
        "label": label,
        "site_url": final_url,
        "resolved_from_search": resolved_from_search,
        "title": page["title"],
        "summary": page["summary"],
        "docs_url": docs_url,
        "pricing_url": pricing_url,
        "careers_url": careers_url,
        "about_url": about_url,
        "products": products,
        "careers_signal": careers_signal(careers_url, str(page["text"])),
        "news_items": news_items,
    }


def format_results(result: JsonDict) -> str:
    checked_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    docs_note = (
        result["docs_url"] or "No docs link was found on the inspected official site."
    )
    pricing_note = (
        result["pricing_url"]
        or "No pricing/plans link was found on the inspected official site."
    )
    careers_note = (
        result["careers_url"]
        or "No careers/jobs link was found on the inspected official site."
    )
    summary_text = str(
        result.get("summary") or "the homepage did not expose a clear short summary"
    )
    lead = (
        f"Company research for {result['label']}: the official site describes the company as "
        f"{truncate_text(summary_text, 180)}."
    )
    lines = [
        lead,
        "",
        (
            "Source basis: official site first, with recent news from Google News RSS "
            "as supporting context."
        ),
        f"Freshness: checked {checked_date}",
        f"Confidence: {'medium' if not result['resolved_from_search'] else 'low-to-medium'}",
        f"Official site: {result['site_url']}",
    ]
    if result["resolved_from_search"]:
        lines.append(
            "Resolution note: official site was inferred from search results; "
            "verify if this is business-critical."
        )
    lines.extend(
        [
            "",
            f"Company summary: {summary_text}",
            f"Docs: {docs_note}",
            f"Pricing: {pricing_note}",
            f"Careers: {careers_note}",
        ]
    )
    if result["about_url"]:
        lines.append(f"About: {result['about_url']}")
    lines.append(f"Hiring signal: {result['careers_signal']}")
    lines.append(
        "Facts vs inference: summary and key-page links come from official site "
        "wording; broader positioning beyond that is not inferred."
    )
    lines.append("")
    lines.append("Products / key pages:")
    if result["products"]:
        for item in result["products"]:
            label = item["text"] or item["href"]
            lines.append(f"- {label}: {item['href']}")
    else:
        lines.append(
            "- No clear product/features/solutions links were identified on the "
            "inspected official site."
        )
    lines.append("")
    lines.append("Recent news:")
    if result["news_items"]:
        for index, item in enumerate(result["news_items"], start=1):
            lines.append(
                f"{index}. {item['title']}"
            )
            lines.append(
                "   Source: "
                f"{item['source']} | Date: {item['published_date']} | Link: {item['link']}"
            )
    else:
        lines.append("No recent news items were found in the sampled Google News results.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Research a company from its official site and recent news"
    )
    parser.add_argument(
        "query",
        nargs="?",
        help="Company name or official site URL, optionally with | filters",
    )
    parser.add_argument("--company", help="Company name for direct shell usage")
    parser.add_argument("--site", help="Explicit official site URL")
    parser.add_argument("--news", help="News window: day, week, or month")
    parser.add_argument("--limit", type=int, help="Maximum company news headlines")
    args = parser.parse_args(argv)

    try:
        request = build_request_from_inputs(
            args.query,
            args.company,
            args.site,
            args.news,
            args.limit,
        )
        print(format_results(research_company(request)))
        return 0
    except (ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())