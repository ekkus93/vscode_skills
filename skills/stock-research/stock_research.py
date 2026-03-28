import argparse
import importlib.util
import pathlib
import sys
from datetime import datetime, timezone
from types import ModuleType
from typing import Any, cast

JsonDict = dict[str, Any]

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
VALID_NEWS_WINDOWS = {"day", "week", "month"}


def load_module(name: str, path: pathlib.Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load helper module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


yahoo_finance = load_module(
    "stock_research_yahoo_finance",
    SCRIPT_DIR.parent / "yahoo-finance" / "yahoo_finance.py",
)
company_research = load_module(
    "stock_research_company_research",
    SCRIPT_DIR.parent / "company-research" / "company_research.py",
)
news_search = load_module(
    "stock_research_news_search",
    SCRIPT_DIR.parent / "news-search" / "news_search.py",
)


def collapse_whitespace(value: str) -> str:
    return " ".join(value.split())


def normalize_cli_args(argv: list[str] | None) -> list[str] | None:
    if argv is None:
        return None

    normalized: list[str] = []
    supported_flags = {"--ticker", "--period", "--news", "--limit", "--site"}
    for arg in argv:
        matched = False
        for flag in supported_flags:
            prefix = f"{flag}:"
            if arg.startswith(prefix):
                normalized.extend([flag, arg[len(prefix) :]])
                matched = True
                break
        if not matched:
            normalized.append(arg)
    return normalized


def parse_request(raw_value: str) -> JsonDict:
    parts = [collapse_whitespace(part) for part in raw_value.split("|")]
    parts = [part for part in parts if part]
    if not parts:
        raise ValueError("Ticker cannot be empty")

    parsed_ticker = yahoo_finance.parse_request(parts[0])
    request: JsonDict = {
        "ticker": parsed_ticker["ticker"],
        "period": "1y",
        "news_window": "month",
        "news_limit": 3,
        "site_url": None,
    }

    for part in parts[1:]:
        if ":" not in part:
            raise ValueError(f"Unsupported stock-research option: {part}")
        key, raw_option = part.split(":", 1)
        key = key.strip().lower()
        option = collapse_whitespace(raw_option)
        lowered = option.lower()
        if key == "period":
            if lowered not in yahoo_finance.VALID_PERIODS:
                raise ValueError(
                    "period must be one of: 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max"
                )
            request["period"] = lowered
        elif key == "news":
            if lowered not in VALID_NEWS_WINDOWS:
                raise ValueError("news must be one of: day, week, month")
            request["news_window"] = lowered
        elif key == "limit":
            try:
                limit = int(lowered)
            except ValueError as exc:
                raise ValueError("limit must be an integer between 1 and 3") from exc
            if limit < 1 or limit > 3:
                raise ValueError("limit must be an integer between 1 and 3")
            request["news_limit"] = limit
        elif key == "site":
            if not option.startswith(("http://", "https://")):
                raise ValueError("site must be a full http:// or https:// URL")
            request["site_url"] = option.rstrip("/")
        else:
            raise ValueError(f"Unsupported stock-research option: {key}")
    return request


def build_request_from_inputs(
    query: str | None,
    ticker: str | None,
    period: str | None,
    news_window: str | None,
    limit: int | None,
    site_url: str | None,
) -> JsonDict:
    if query and ticker:
        raise ValueError("Use either a quoted query or --ticker, not both")
    if query:
        return parse_request(query)
    if not ticker:
        raise ValueError("Provide either a quoted query or --ticker")

    raw_request = collapse_whitespace(ticker)
    if period:
        raw_request += f" | period:{collapse_whitespace(period)}"
    if news_window:
        raw_request += f" | news:{collapse_whitespace(news_window)}"
    if limit is not None:
        raw_request += f" | limit:{limit}"
    if site_url:
        raw_request += f" | site:{collapse_whitespace(site_url)}"
    return parse_request(raw_request)


def build_market_news_query(company_name: str, ticker: str) -> str:
    name = collapse_whitespace(company_name)
    if name and name.upper() != ticker.upper():
        return f"{name} {ticker} stock"
    return f"{ticker} stock"


def build_market_news_queries(company_name: str, ticker: str) -> list[str]:
    primary_query = build_market_news_query(company_name, ticker)
    queries = [primary_query, f"{ticker} earnings", f"{ticker} analyst"]
    unique_queries: list[str] = []
    for query in queries:
        if query not in unique_queries:
            unique_queries.append(query)
    return unique_queries


def fetch_market_news(query_text: str, news_window: str, limit: int) -> list[JsonDict]:
    request = news_search.parse_request(f"{query_text} | time:{news_window} | limit:{limit}")
    items = cast(
        list[JsonDict],
        news_search.filter_low_signal_sources(
        news_search.parse_feed_items(news_search.request_feed(news_search.build_feed_url(request)))
        ),
    )
    return cast(list[JsonDict], news_search.dedupe_articles(items)[:limit])


def news_item_key(item: JsonDict) -> tuple[str, str]:
    title = collapse_whitespace(str(item.get("title", ""))).lower()
    link = str(item.get("link", ""))
    return title, link


def choose_market_news(
    company_name: str,
    ticker: str,
    news_window: str,
    limit: int,
    company_news_items: list[JsonDict],
) -> tuple[str, list[JsonDict]]:
    company_keys = {news_item_key(item) for item in company_news_items}
    first_query = ""
    first_items: list[JsonDict] = []
    for query in build_market_news_queries(company_name, ticker):
        items = fetch_market_news(query, news_window, limit)
        if not first_query:
            first_query = query
            first_items = items
        unique_items = [item for item in items if news_item_key(item) not in company_keys]
        if unique_items:
            return query, unique_items[:limit]
    return first_query, first_items


def research_stock(request: JsonDict) -> JsonDict:
    market_snapshot = yahoo_finance.fetch_snapshot(
        {"ticker": request["ticker"], "period": request["period"]}
    )
    company_site = request["site_url"] or market_snapshot.get("website")
    company_result = company_research.research_company(
        {
            "company_name": str(market_snapshot["company_name"]),
            "site_url": company_site,
            "news_window": request["news_window"],
            "news_limit": request["news_limit"],
        }
    )
    market_news_query, market_news_items = choose_market_news(
        str(market_snapshot["company_name"]),
        request["ticker"],
        request["news_window"],
        request["news_limit"],
        list(company_result["news_items"]),
    )
    return {
        "ticker": request["ticker"],
        "period": request["period"],
        "news_window": request["news_window"],
        "market_snapshot": market_snapshot,
        "company_result": company_result,
        "market_news_query": market_news_query,
        "market_news_items": market_news_items,
    }


def research_takeaways(result: JsonDict) -> list[str]:
    snapshot = result["market_snapshot"]
    history = snapshot["history"]
    takeaways: list[str] = []

    if history.get("return_pct") is not None:
        takeaways.append(
            f"Sampled price performance over {result['period']} was "
            f"{yahoo_finance.format_percent(history['return_pct'])}."
        )
    if snapshot.get("revenue_growth") is not None or snapshot.get("profit_margin") is not None:
        takeaways.append(
            "Growth and profitability remain worth checking together: "
            f"revenue growth {yahoo_finance.format_percent(snapshot.get('revenue_growth'))}, "
            f"profit margin {yahoo_finance.format_percent(snapshot.get('profit_margin'))}."
        )
    if result["market_news_items"]:
        takeaways.append(
            "Recent sampled market headlines were queried with "
            f"'{result['market_news_query']}'."
        )
    else:
        takeaways.append(
            "No useful recent market headlines were found in the sampled "
            "news window; broaden or retry if needed."
        )
    return takeaways[:3]


def format_market_news(items: list[JsonDict]) -> list[str]:
    lines: list[str] = []
    if not items:
        return ["No recent market-news items were found in the sampled results."]
    for index, item in enumerate(items, start=1):
        lines.append(f"{index}. {item['title']}")
        lines.append(
            "   Source: "
            f"{item['source']} | Date: {item['published_date']} | Link: {item['link']}"
        )
        if item.get("description"):
            lines.append(
                f"   Summary: {news_search.truncate_text(str(item['description']))}"
            )
    return lines


def format_company_news(items: list[JsonDict]) -> list[str]:
    lines: list[str] = []
    if not items:
        return ["No recent company-news items were found in the sampled results."]
    for index, item in enumerate(items, start=1):
        lines.append(f"{index}. {item['title']}")
        lines.append(
            "   Source: "
            f"{item['source']} | Date: {item['published_date']} | Link: {item['link']}"
        )
    return lines


def format_result(result: JsonDict) -> str:
    checked_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    snapshot = result["market_snapshot"]
    company_result = result["company_result"]
    history = snapshot["history"]

    lead = (
        f"Stock research for {result['ticker']} ({snapshot['company_name']}): "
        "shares last closed at "
        f"{yahoo_finance.format_price(snapshot['current_price'], snapshot['currency'])} "
        "and returned "
        f"{yahoo_finance.format_percent(history['return_pct'])} over the "
        f"sampled {result['period']} period, while the official site describes "
        "the business as "
        f"{company_research.truncate_text(str(company_result['summary']), 140)}."
    )
    lines = [
        lead,
        "",
        "Source basis: Yahoo Finance data via yfinance, official site "
        "inspection, and Google News RSS market/news sampling.",
        f"Freshness: checked {checked_date}",
        "Confidence: medium",
        "Caveat: this is a research snapshot, not personalized investment "
        "advice; verify critical figures before trading.",
        f"Target: {result['ticker']} | period:{result['period']} | news:{result['news_window']}",
        "",
        "Market snapshot:",
        (
            "- Current price: "
            f"{yahoo_finance.format_price(snapshot['current_price'], snapshot['currency'])} "
            f"on {history['end_date']}"
        ),
        (
            "- Sampled performance: "
            f"{yahoo_finance.format_percent(history['return_pct'])} from "
            f"{yahoo_finance.format_price(history['start_close'], snapshot['currency'])} "
            f"on {history['start_date']} to "
            f"{yahoo_finance.format_price(history['end_close'], snapshot['currency'])} "
            f"on {history['end_date']}"
        ),
        (
            "- Sampled high / low: "
            f"{yahoo_finance.format_price(history['high'], snapshot['currency'])} / "
            f"{yahoo_finance.format_price(history['low'], snapshot['currency'])}"
        ),
        f"- Average volume: {yahoo_finance.format_large_number(history['avg_volume'])}",
        f"- Market cap: {yahoo_finance.format_large_number(snapshot['market_cap'])}",
        (
            "- Trailing PE / forward PE / price-to-book: "
            f"{yahoo_finance.format_ratio(snapshot['trailing_pe'])} / "
            f"{yahoo_finance.format_ratio(snapshot['forward_pe'])} / "
            f"{yahoo_finance.format_ratio(snapshot['price_to_book'])}"
        ),
        (
            f"- Revenue growth / gross margin / operating margin / profit margin: "
            f"{yahoo_finance.format_percent(snapshot['revenue_growth'])} / "
            f"{yahoo_finance.format_percent(snapshot['gross_margin'])} / "
            f"{yahoo_finance.format_percent(snapshot['operating_margin'])} / "
            f"{yahoo_finance.format_percent(snapshot['profit_margin'])}"
        ),
        "",
        "Business profile:",
        f"- Official site: {company_result['site_url']}",
        f"- Summary: {company_result['summary']}",
        f"- Sector / industry: {snapshot['sector']} / {snapshot['industry']}",
        f"- Docs: {company_result['docs_url'] or 'No docs link found.'}",
        f"- Pricing: {company_result['pricing_url'] or 'No pricing link found.'}",
        f"- Careers: {company_result['careers_url'] or 'No careers link found.'}",
        f"- Hiring signal: {company_result['careers_signal']}",
        "",
        "Research takeaways:",
    ]
    for takeaway in research_takeaways(result):
        lines.append(f"- {takeaway}")
    lines.extend(["", f"Market headlines sampled with query: {result['market_news_query']}", ""])
    lines.append("Recent market news:")
    lines.extend(format_market_news(result["market_news_items"]))
    lines.extend(["", "Recent company news:"])
    lines.extend(format_company_news(company_result["news_items"]))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    argv = normalize_cli_args(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(
        description=(
            "Combine Yahoo Finance, company profile, and news into a "
            "longer-form stock research snapshot"
        )
    )
    parser.add_argument(
        "query",
        nargs="?",
        help="Ticker plus optional | filters, quoted as one argument",
    )
    parser.add_argument("--ticker", help="Ticker symbol for direct shell usage")
    parser.add_argument("--period", help="Sampling period such as 1y or 6mo")
    parser.add_argument("--news", help="News window: day, week, or month")
    parser.add_argument("--limit", type=int, help="Maximum headlines per news section")
    parser.add_argument("--site", help="Explicit official site URL")
    args = parser.parse_args(argv)

    try:
        request = build_request_from_inputs(
            args.query,
            args.ticker,
            args.period,
            args.news,
            args.limit,
            args.site,
        )
        print(format_result(research_stock(request)))
        return 0
    except (ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())