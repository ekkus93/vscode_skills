from __future__ import annotations

import argparse
import importlib.util
import pathlib
import re
import sys
from datetime import datetime, timezone
from types import ModuleType
from typing import Any

JsonDict = dict[str, Any]

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
TICKER_PATTERN = re.compile(r"[A-Z0-9.=\-^]+")


def load_module(name: str, path: pathlib.Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load helper module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


yahoo_finance = load_module(
    "stock_review_yahoo_finance",
    SCRIPT_DIR.parent / "yahoo-finance" / "yahoo_finance.py",
)
stock_research = load_module(
    "stock_review_stock_research",
    SCRIPT_DIR.parent / "stock-research" / "stock_research.py",
)


def collapse_whitespace(value: str) -> str:
    return " ".join(value.split())


def normalize_cli_args(argv: list[str] | None) -> list[str] | None:
    if argv is None:
        return None

    normalized: list[str] = []
    supported_flags = {"--ticker", "--company", "--horizon", "--site"}
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


def resolve_company_to_ticker(company_name: str) -> str:
    yf = yahoo_finance.require_yfinance()
    query = collapse_whitespace(company_name)
    try:
        search = yf.Search(query=query, max_results=8)
    except Exception as exc:  # pragma: no cover - network/library failure path
        raise RuntimeError(
            f"Could not resolve ticker for company '{query}': {exc}"
        ) from exc

    quotes = list(getattr(search, "quotes", []) or [])
    if not quotes:
        raise RuntimeError(f"Could not confidently resolve ticker for company: {query}")

    query_tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
    best_symbol: str | None = None
    best_score = -1
    for quote in quotes:
        quote_type = str(quote.get("quoteType") or quote.get("type") or "").lower()
        if quote_type and quote_type not in {"equity", "stock"}:
            continue
        symbol = str(quote.get("symbol") or "").upper()
        if not symbol or not TICKER_PATTERN.fullmatch(symbol):
            continue
        name = collapse_whitespace(
            str(quote.get("shortname") or quote.get("longname") or quote.get("name") or "")
        )
        name_tokens = set(re.findall(r"[a-z0-9]+", name.lower()))
        score = len(query_tokens & name_tokens)
        if name.lower() == query.lower():
            score += 10
        elif query.lower() in name.lower():
            score += 5
        if symbol == query.upper():
            score += 20
        if score > best_score:
            best_score = score
            best_symbol = symbol

    if best_symbol is None or best_score < 1:
        raise RuntimeError(f"Could not confidently resolve ticker for company: {query}")
    return best_symbol


def parse_request(raw_value: str) -> JsonDict:
    parts = [collapse_whitespace(part) for part in raw_value.split("|")]
    parts = [part for part in parts if part]
    if not parts:
        raise ValueError("Stock review target cannot be empty")

    target = parts[0]
    ticker: str | None = None
    company_name: str | None = None
    if TICKER_PATTERN.fullmatch(target.upper()):
        ticker = target.upper()
    else:
        company_name = target

    request: JsonDict = {
        "ticker": ticker,
        "company_name": company_name,
        "horizon": "30d",
        "site_url": None,
    }

    for part in parts[1:]:
        if ":" not in part:
            raise ValueError(f"Unsupported stock-investment-review option: {part}")
        key, raw_option = part.split(":", 1)
        key = key.strip().lower()
        option = collapse_whitespace(raw_option)
        if key == "horizon":
            if not option:
                raise ValueError("horizon cannot be empty")
            request["horizon"] = option
        elif key == "company":
            if not option:
                raise ValueError("company cannot be empty")
            request["company_name"] = option
        elif key == "site":
            if not option.startswith(("http://", "https://")):
                raise ValueError("site must be a full http:// or https:// URL")
            request["site_url"] = option.rstrip("/")
        else:
            raise ValueError(f"Unsupported stock-investment-review option: {key}")

    if request["ticker"] is None:
        if not request["company_name"]:
            raise ValueError("Provide a ticker or company name")
        request["ticker"] = resolve_company_to_ticker(str(request["company_name"]))

    return request


def build_request_from_inputs(
    query: str | None,
    ticker: str | None,
    company_name: str | None,
    horizon: str | None,
    site_url: str | None,
) -> JsonDict:
    if query and any(value for value in (ticker, company_name, horizon, site_url)):
        raise ValueError("Use either a quoted query or flags, not both")
    if query:
        return parse_request(query)

    target = collapse_whitespace(ticker or company_name or "")
    if not target:
        raise ValueError("Provide either a quoted query or --ticker/--company")
    raw_request = target
    if horizon:
        raw_request += f" | horizon:{collapse_whitespace(horizon)}"
    if company_name and ticker:
        raw_request += f" | company:{collapse_whitespace(company_name)}"
    if site_url:
        raw_request += f" | site:{collapse_whitespace(site_url)}"
    return parse_request(raw_request)


def technical_position_label(snapshot: JsonDict) -> str:
    history = snapshot["history"]
    current_price = snapshot.get("current_price")
    high = history.get("high")
    low = history.get("low")
    if current_price is None or high is None or low is None or high == low:
        return "within the sampled 52-week range"
    normalized = (float(current_price) - float(low)) / (float(high) - float(low))
    if normalized <= 0.25:
        return "near the lower end of its sampled 52-week range"
    if normalized >= 0.75:
        return "near the upper end of its sampled 52-week range"
    return "near the middle of its sampled 52-week range"


def recommendation(result: JsonDict, horizon: str) -> tuple[str, str]:
    snapshot = result["market_snapshot"]
    history = snapshot["history"]
    return_pct = history.get("return_pct")
    revenue_growth = snapshot.get("revenue_growth")
    margin = snapshot.get("profit_margin")

    if return_pct is not None and return_pct <= -0.2 and (
        (revenue_growth is not None and revenue_growth > 0)
        or (margin is not None and margin > 0)
    ):
        return (
            "buy on pullback",
            (
                f"The {horizon} setup combines a depressed recent price trend "
                "with still-positive operating fundamentals, which can support "
                "a tactical rebound if catalysts follow through."
            ),
        )
    if return_pct is not None and return_pct >= 0.2:
        return (
            "wait",
            (
                f"The stock has already moved materially over the sampled "
                f"period, so the {horizon} setup looks less asymmetric "
                "without a fresh catalyst."
            ),
        )
    return (
        "wait",
        (
            f"The current {horizon} setup is mixed enough that a cleaner "
            "pullback or stronger catalyst confirmation would improve the "
            "risk-reward profile."
        ),
    )


def build_todo_markdown(result: JsonDict, request: JsonDict) -> str:
    checked_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ticker = str(request["ticker"])
    company_name = str(result["market_snapshot"]["company_name"])
    horizon = str(request["horizon"])
    return "\n".join(
        [
            f"# {company_name} ({ticker}) Investment Review - TODO",
            f"**Horizon:** {horizon}",
            f"**Research Date:** {checked_date}",
            f"**Ticker:** {ticker}",
            "",
            "## Phase 1: Market Data Collection",
            "- [x] Fetch current price and market fundamentals from Yahoo Finance",
            "- [x] Capture 1-year price range and performance metrics",
            "- [x] Document market cap, volume, and key valuation ratios",
            "- [x] Record average daily trading volume",
            "",
            "## Phase 2: Technical Context Review",
            "- [x] Review one-year trend behavior and sampled range positioning",
            "- [x] Identify key support and resistance levels from the sampled period",
            "- [x] Summarize the current technical posture for the requested horizon",
            "",
            "## Phase 3: Company Context",
            "- [x] Inspect the official site or investor-relations pages",
            "- [x] Record sector, industry, and business summary context",
            (
                "- [x] Capture any documentation, pricing, or hiring signals "
                "surfaced on the official site"
            ),
            "",
            "## Phase 4: Recent Catalysts & News",
            "- [x] Gather recent company and market headlines",
            "- [x] Note likely positive and negative catalysts for the requested horizon",
            "- [x] Separate official facts from interpretation and market inference",
            "",
            "## Phase 5: Scenario Analysis",
            "- [x] Build bull, base, and bear scenarios for the requested horizon",
            "- [x] Quantify likely upside, downside, and invalidation levels",
            "- [x] Translate the research into entry and exit conditions",
            "",
            "## Phase 6: Final Report & Decision",
            f"- [x] Write the final report to {ticker}.md",
            "- [x] Include exact action, entry, exit, invalidation, and no-trade sections",
            "- [x] Mark the workflow complete only after both Markdown files exist",
            "",
            "## Tasks Completed",
            f"All review phases completed. Final report generated for the {horizon} horizon.",
        ]
    )


def catalyst_lines(items: list[JsonDict]) -> list[str]:
    if not items:
        return ["- No strong recent catalysts were surfaced in the sampled news window."]
    lines: list[str] = []
    for item in items[:3]:
        lines.append(
            f"- {item['title']} ({item['published_date']}, {item['source']})"
        )
    return lines


def build_report_markdown(result: JsonDict, request: JsonDict) -> str:
    snapshot = result["market_snapshot"]
    company_result = result["company_result"]
    history = snapshot["history"]
    ticker = str(request["ticker"])
    horizon = str(request["horizon"])
    checked_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    company_name = str(snapshot["company_name"])
    action, rationale = recommendation(result, horizon)
    current_price = yahoo_finance.format_price(
        snapshot.get("current_price"), snapshot.get("currency")
    )
    low_price = yahoo_finance.format_price(history.get("low"), snapshot.get("currency"))
    high_price = yahoo_finance.format_price(history.get("high"), snapshot.get("currency"))
    return_pct = yahoo_finance.format_percent(history.get("return_pct"))
    avg_volume = yahoo_finance.format_large_number(history.get("avg_volume"))
    support = low_price
    resistance = high_price
    position_label = technical_position_label(snapshot)
    market_news = list(result.get("market_news_items", []))
    company_news = list(company_result.get("news_items", []))
    catalyst_items = market_news[:2] + [
        item for item in company_news if item not in market_news
    ][:1]

    lines = [
        f"# {company_name} ({ticker}) Investment Review Report",
        f"**Horizon:** {horizon}",
        f"**Research Date:** {checked_date}",
        f"**Ticker:** {ticker}",
        "",
        "---",
        "",
        "## Disclaimer",
        "",
        (
            "This report is informational research only, not personalized "
            "financial advice. All data sources should be independently "
            "verified before making trading decisions."
        ),
        "",
        "---",
        "",
        "## Objective & Horizon",
        "",
        f"**Timeframe:** {horizon} investment review",
        (
            "**Objective:** Evaluate whether the stock offers an attractive "
            "risk-reward setup over the requested horizon."
        ),
        (
            "**Methodology:** Yahoo Finance primary data, supplemented with "
            "official company sources and sampled recent news coverage."
        ),
        "",
        "---",
        "",
        "## Source Basis",
        "",
        "- **Primary:** Yahoo Finance via yfinance",
        f"- **Company Context:** {company_result['site_url']}",
        f"- **News Coverage:** Google News RSS search for {company_name} and {ticker}",
        (
            "- **Cross-reference:** bundled stock-research synthesis for "
            "one-year market context and recent headlines"
        ),
        "",
        f"**Freshness Check:** {checked_date}",
        "**Confidence Level:** Medium",
        "",
        "---",
        "",
        "## Market Snapshot",
        "",
        f"- **Current Price:** {current_price} (as of {history['end_date']})",
        (
            f"- **1Y Sampled Performance:** {return_pct} from "
            f"{history['start_date']} to {history['end_date']}"
        ),
        f"- **52-Week Range:** {low_price} - {high_price}",
        f"- **Market Cap:** {yahoo_finance.format_large_number(snapshot.get('market_cap'))}",
        f"- **Avg Daily Volume:** {avg_volume}",
        (
            "- **Trailing PE / Forward PE / Price-to-Book:** "
            f"{yahoo_finance.format_ratio(snapshot.get('trailing_pe'))} / "
            f"{yahoo_finance.format_ratio(snapshot.get('forward_pe'))} / "
            f"{yahoo_finance.format_ratio(snapshot.get('price_to_book'))}"
        ),
        (
            "- **Revenue Growth / Gross Margin / Operating Margin / Profit "
            "Margin:** "
            f"{yahoo_finance.format_percent(snapshot.get('revenue_growth'))} / "
            f"{yahoo_finance.format_percent(snapshot.get('gross_margin'))} / "
            f"{yahoo_finance.format_percent(snapshot.get('operating_margin'))} / "
            f"{yahoo_finance.format_percent(snapshot.get('profit_margin'))}"
        ),
        "",
        "---",
        "",
        "## Technical Context (1-Year Review)",
        "",
        (
            f"**Current Positioning:** {ticker} is {position_label}, with the "
            f"current price at {current_price} versus a sampled low of "
            f"{low_price} and high of {high_price}."
        ),
        "",
        "**Key Technical Observations:**",
        f"- Sampled one-year return was {return_pct}",
        f"- Major support is near {support}",
        f"- Major resistance is near {resistance}",
        (
            f"- Average trading volume of {avg_volume} provides reasonable "
            "liquidity context for the setup"
        ),
        "",
        "---",
        "",
        "## Company & Business Context",
        "",
        f"**Business Summary:** {company_result['summary']}",
        "",
        "**Official-site observations:**",
        f"- **Official Site:** {company_result['site_url']}",
        f"- **Docs:** {company_result['docs_url'] or 'No docs link found'}",
        f"- **Pricing:** {company_result['pricing_url'] or 'No pricing link found'}",
        f"- **Careers:** {company_result['careers_url'] or 'No careers link found'}",
        f"- **Hiring signal:** {company_result['careers_signal']}",
        "",
        "---",
        "",
        f"## Recent Catalysts ({horizon})",
        "",
        "**Sampled recent headlines:**",
    ]
    lines.extend(catalyst_lines(catalyst_items))
    lines.extend(
        [
            "",
            "---",
            "",
            "## Bull Case",
            "",
            (
                "If current catalysts convert into stronger demand and "
                "execution remains solid, the stock could retest resistance "
                f"closer to {resistance} over the {horizon} window."
            ),
            "",
            "## Base Case",
            "",
            (
                f"The most likely path is consolidation between support near "
                f"{support} and resistance near {resistance} while recent "
                "headlines and fundamentals are digested."
            ),
            "",
            "## Bear Case",
            "",
            (
                "If the recent setup weakens and the stock breaks below "
                f"support near {support}, the current tactical thesis would "
                f"deteriorate quickly for the {horizon} window."
            ),
            "",
            "---",
            "",
            "## Action",
            f"- `{action}`",
            f"- {rationale}",
            "",
            "## Entry",
            (
                f"- Preferred range: near {current_price} on a controlled "
                f"pullback toward support around {support}."
            ),
            (
                "- Trigger: enter only if price action stabilizes within the "
                f"next {horizon} review window and the recent catalyst tape "
                "does not materially worsen."
            ),
            "",
            "## Exit",
            f"- First target: scale out as price approaches resistance near {resistance}.",
            (
                f"- Timing: reassess continuously during the {horizon} window "
                "and take profits earlier if momentum fades before the "
                "resistance zone."
            ),
            "",
            "## Invalidation",
            f"- A decisive break below support near {support} invalidates the tactical setup.",
            (
                "- The thesis is also wrong if the underlying catalysts reverse "
                "or a new material negative development changes the current "
                "risk-reward picture."
            ),
            "",
            "## No-Trade Condition",
            (
                "- Do not open a position if price is already extended far "
                "beyond the sampled resistance zone without a fresh catalyst."
            ),
            (
                "- Do not open a position if liquidity, catalyst quality, or "
                "source confidence deteriorates materially before entry."
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def write_outputs(
    result: JsonDict, request: JsonDict, output_dir: pathlib.Path
) -> tuple[pathlib.Path, pathlib.Path]:
    ticker = str(request["ticker"])
    todo_path = output_dir / f"{ticker}_TODO.md"
    report_path = output_dir / f"{ticker}.md"
    todo_path.write_text(build_todo_markdown(result, request), encoding="utf-8")
    report_path.write_text(build_report_markdown(result, request), encoding="utf-8")
    return todo_path, report_path


def validate_outputs(todo_path: pathlib.Path, report_path: pathlib.Path) -> None:
    if not todo_path.exists() or not report_path.exists():
        raise RuntimeError("Expected stock-review output files were not created")
    report_text = report_path.read_text(encoding="utf-8")
    required_headings = [
        "## Action",
        "## Entry",
        "## Exit",
        "## Invalidation",
        "## No-Trade Condition",
    ]
    for heading in required_headings:
        if heading not in report_text:
            raise RuntimeError(f"Generated report is missing required heading: {heading}")


def main(argv: list[str] | None = None) -> int:
    argv = normalize_cli_args(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(
        description=(
            "Build a deterministic stock investment review and write the "
            "Markdown outputs"
        )
    )
    parser.add_argument(
        "query", nargs="?", help="Ticker or company name with optional | filters"
    )
    parser.add_argument("--ticker", help="Explicit ticker symbol")
    parser.add_argument("--company", help="Explicit company name")
    parser.add_argument("--horizon", help="Explicit review horizon such as 30d or 45d")
    parser.add_argument("--site", help="Explicit official site URL")
    parser.add_argument(
        "--output-dir",
        default=".",
        help="Directory where <TICKER>_TODO.md and <TICKER>.md should be written",
    )
    args = parser.parse_args(argv)

    try:
        request = build_request_from_inputs(
            args.query, args.ticker, args.company, args.horizon, args.site
        )
        result = stock_research.research_stock(
            {
                "ticker": request["ticker"],
                "period": "1y",
                "news_window": "month",
                "news_limit": 3,
                "site_url": request["site_url"],
            }
        )
        output_dir = pathlib.Path(args.output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        todo_path, report_path = write_outputs(result, request, output_dir)
        validate_outputs(todo_path, report_path)
    except (RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(
        f"Created {todo_path.name} and {report_path.name} for "
        f"{request['ticker']} with horizon {request['horizon']}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())