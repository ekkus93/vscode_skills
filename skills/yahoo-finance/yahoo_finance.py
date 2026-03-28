import argparse
import math
import re
import sys
from datetime import datetime, timezone
from typing import Any

JsonDict = dict[str, Any]

VALID_PERIODS = {"1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"}


def collapse_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def truncate_text(value: str, limit: int = 240) -> str:
    clean = collapse_whitespace(value)
    if len(clean) <= limit:
        return clean
    shortened = clean[: limit - 1].rsplit(" ", 1)[0].rstrip()
    return shortened + "..."


def parse_request(raw_value: str) -> JsonDict:
    parts = [collapse_whitespace(part) for part in raw_value.split("|")]
    parts = [part for part in parts if part]
    if not parts:
        raise ValueError("Ticker cannot be empty")

    ticker = parts[0].upper()
    if not re.fullmatch(r"[A-Z0-9.=\-^]+", ticker):
        raise ValueError("Ticker contains unsupported characters")

    period = "1y"
    for part in parts[1:]:
        if ":" not in part:
            raise ValueError(f"Unsupported yahoo-finance option: {part}")
        key, raw_option = part.split(":", 1)
        key = key.strip().lower()
        option = collapse_whitespace(raw_option).lower()
        if key != "period":
            raise ValueError(f"Unsupported yahoo-finance option: {key}")
        if option not in VALID_PERIODS:
            raise ValueError(
                "period must be one of: 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max"
            )
        period = option

    return {"ticker": ticker, "period": period}


def build_request_from_inputs(
    query: str | None,
    ticker: str | None,
    period: str | None,
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
    return parse_request(raw_request)


def maybe_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        number = float(value)
        if math.isnan(number) or math.isinf(number):
            return None
        return number
    return None


def first_present(*values: Any) -> Any:
    for value in values:
        if value is not None and value != "":
            return value
    return None


def format_price(value: float | None, currency: str | None = None) -> str:
    if value is None:
        return "not available"
    prefix = "$" if currency == "USD" else ""
    return f"{prefix}{value:,.2f}"


def format_large_number(value: float | None) -> str:
    if value is None:
        return "not available"
    absolute = abs(value)
    if absolute >= 1_000_000_000_000:
        return f"{value / 1_000_000_000_000:.2f}T"
    if absolute >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    if absolute >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if absolute >= 1_000:
        return f"{value / 1_000:.2f}K"
    return f"{value:,.0f}"


def format_ratio(value: float | None) -> str:
    if value is None:
        return "not available"
    return f"{value:.2f}"


def format_percent(value: float | None) -> str:
    if value is None:
        return "not available"
    return f"{value * 100:+.1f}%"


def normalize_dividend_yield(
    trailing_yield: Any,
    dividend_rate: Any,
    current_price: float | None,
    raw_dividend_yield: Any,
) -> float | None:
    trailing_value = maybe_float(trailing_yield)
    if trailing_value is not None:
        return trailing_value

    dividend_rate_value = maybe_float(dividend_rate)
    if dividend_rate_value is not None and current_price and current_price > 0:
        return dividend_rate_value / current_price

    raw_value = maybe_float(raw_dividend_yield)
    if raw_value is None:
        return None
    if raw_value > 1 or raw_value >= 0.15:
        return raw_value / 100
    return raw_value


def history_rows_from_frame(history: Any) -> list[JsonDict]:
    rows: list[JsonDict] = []
    for index, row in history.iterrows():
        date_text = index.strftime("%Y-%m-%d") if hasattr(index, "strftime") else str(index)[:10]
        rows.append(
            {
                "date": date_text,
                "close": maybe_float(row.get("Close")),
                "high": maybe_float(row.get("High")),
                "low": maybe_float(row.get("Low")),
                "volume": maybe_float(row.get("Volume")),
            }
        )
    return rows


def history_metrics(rows: list[JsonDict]) -> JsonDict:
    close_rows = [row for row in rows if row.get("close") is not None]
    if not close_rows:
        raise RuntimeError("Yahoo Finance returned no usable price history")

    start_row = close_rows[0]
    end_row = close_rows[-1]
    start_close = float(start_row["close"])
    end_close = float(end_row["close"])
    lows = [float(row["low"]) for row in rows if row.get("low") is not None]
    highs = [float(row["high"]) for row in rows if row.get("high") is not None]
    volumes = [float(row["volume"]) for row in rows if row.get("volume") is not None]
    return {
        "start_date": start_row["date"],
        "end_date": end_row["date"],
        "start_close": start_close,
        "end_close": end_close,
        "return_pct": ((end_close - start_close) / start_close) if start_close else None,
        "high": max(highs) if highs else None,
        "low": min(lows) if lows else None,
        "avg_volume": (sum(volumes) / len(volumes)) if volumes else None,
    }


def require_yfinance() -> Any:
    try:
        import yfinance as yf  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError(
            "Missing required Python package: yfinance. "
            "Install it with python3 -m pip install yfinance"
        ) from exc
    return yf


def fetch_snapshot(request: JsonDict) -> JsonDict:
    yf = require_yfinance()
    ticker = yf.Ticker(request["ticker"])

    try:
        history = ticker.history(period=request["period"], auto_adjust=False)
    except Exception as exc:  # pragma: no cover - network/library failure path
        raise RuntimeError(
            f"Yahoo Finance history request failed for {request['ticker']}: {exc}"
        ) from exc
    if history is None or getattr(history, "empty", False):
        raise RuntimeError(
            f"Yahoo Finance returned no price history for ticker: {request['ticker']}"
        )

    history_data = history_metrics(history_rows_from_frame(history))

    info: JsonDict = {}
    try:
        info = ticker.get_info()
    except Exception:
        info = {}

    fast_info: JsonDict = {}
    try:
        fast_info = dict(ticker.fast_info)
    except Exception:
        fast_info = {}

    currency = first_present(info.get("currency"), fast_info.get("currency"), "USD")
    current_price = maybe_float(
        first_present(
            fast_info.get("lastPrice"),
            info.get("currentPrice"),
            history_data["end_close"],
        )
    )
    dividend_yield = normalize_dividend_yield(
        info.get("trailingAnnualDividendYield"),
        info.get("dividendRate"),
        current_price,
        info.get("dividendYield"),
    )

    return {
        "ticker": request["ticker"],
        "period": request["period"],
        "company_name": first_present(
            info.get("longName"), info.get("shortName"), request["ticker"]
        ),
        "quote_type": first_present(
            info.get("quoteType"), info.get("instrumentType"), "not available"
        ),
        "exchange": first_present(
            info.get("exchange"), info.get("fullExchangeName"), "not available"
        ),
        "currency": currency,
        "current_price": current_price,
        "market_cap": maybe_float(first_present(fast_info.get("marketCap"), info.get("marketCap"))),
        "trailing_pe": maybe_float(info.get("trailingPE")),
        "forward_pe": maybe_float(info.get("forwardPE")),
        "price_to_book": maybe_float(info.get("priceToBook")),
        "dividend_yield": dividend_yield,
        "revenue_growth": maybe_float(info.get("revenueGrowth")),
        "gross_margin": maybe_float(info.get("grossMargins")),
        "operating_margin": maybe_float(info.get("operatingMargins")),
        "profit_margin": maybe_float(info.get("profitMargins")),
        "sector": first_present(info.get("sector"), "not available"),
        "industry": first_present(info.get("industry"), "not available"),
        "website": first_present(info.get("website"), None),
        "summary": truncate_text(
            info.get("longBusinessSummary") or "No business summary available."
        ),
        "history": history_data,
    }


def format_result(result: JsonDict) -> str:
    checked_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    history = result["history"]
    lead = (
        f"Yahoo Finance snapshot for {result['ticker']} ({result['company_name']}): "
        f"shares last closed at {format_price(result['current_price'], result['currency'])} "
        f"and returned {format_percent(history['return_pct'])} over the sampled "
        f"{result['period']} period."
    )
    lines = [
        lead,
        "",
        "Source: Yahoo Finance data via the yfinance Python library.",
        f"Freshness: checked {checked_date}",
        "Confidence: medium",
        (
            "Caveat: yfinance is an unofficial Yahoo Finance wrapper; verify "
            "critical numbers before trading or filing-sensitive use."
        ),
        f"Target: {result['ticker']} | period:{result['period']}",
        "",
        "Market snapshot:",
        (
            f"- Current price: {format_price(result['current_price'], result['currency'])} "
            f"on {history['end_date']}"
        ),
        (
            f"- Sampled performance: {format_percent(history['return_pct'])} from "
            f"{format_price(history['start_close'], result['currency'])} on "
            f"{history['start_date']} to "
            f"{format_price(history['end_close'], result['currency'])} on {history['end_date']}"
        ),
        (
            f"- Sampled high / low: {format_price(history['high'], result['currency'])} / "
            f"{format_price(history['low'], result['currency'])}"
        ),
        f"- Average volume: {format_large_number(history['avg_volume'])}",
        f"- Market cap: {format_large_number(result['market_cap'])}",
        f"- Exchange / quote type: {result['exchange']} / {result['quote_type']}",
        "",
        "Fundamentals:",
        f"- Sector / industry: {result['sector']} / {result['industry']}",
        (
            f"- Trailing PE / forward PE / price-to-book: {format_ratio(result['trailing_pe'])} / "
            f"{format_ratio(result['forward_pe'])} / {format_ratio(result['price_to_book'])}"
        ),
        (
            f"- Revenue growth / gross margin / operating margin / profit margin: "
            f"{format_percent(result['revenue_growth'])} / "
            f"{format_percent(result['gross_margin'])} / "
            f"{format_percent(result['operating_margin'])} / "
            f"{format_percent(result['profit_margin'])}"
        ),
        f"- Dividend yield: {format_percent(result['dividend_yield'])}",
    ]
    if result.get("website"):
        lines.append(f"- Website: {result['website']}")
    lines.extend(["", f"Business summary: {result['summary']}"])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fetch a public ticker snapshot from Yahoo Finance via yfinance"
    )
    parser.add_argument(
        "query",
        nargs="?",
        help="Ticker plus optional | period: filter, quoted as one argument",
    )
    parser.add_argument("--ticker", help="Ticker symbol for direct shell usage")
    parser.add_argument("--period", help="Sampling period such as 1y or 6mo")
    args = parser.parse_args(argv)

    try:
        request = build_request_from_inputs(args.query, args.ticker, args.period)
        result = fetch_snapshot(request)
        print(format_result(result))
        return 0
    except (ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())