import importlib.util
import pathlib

MODULE_PATH = (
    pathlib.Path(__file__).resolve().parent
    / "stock_investment_review.py"
)

spec = importlib.util.spec_from_file_location("stock_investment_review", MODULE_PATH)
assert spec is not None and spec.loader is not None
stock_investment_review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stock_investment_review)


def sample_result() -> dict[str, object]:
    return {
        "ticker": "WING",
        "period": "1y",
        "news_window": "month",
        "market_snapshot": {
            "company_name": "Wingstop Inc.",
            "current_price": 199.22,
            "currency": "USD",
            "market_cap": 5_540_000_000.0,
            "trailing_pe": 32.03,
            "forward_pe": 33.49,
            "price_to_book": -7.43,
            "revenue_growth": 0.086,
            "gross_margin": 0.487,
            "operating_margin": 0.272,
            "profit_margin": 0.25,
            "sector": "Consumer Cyclical",
            "industry": "Restaurants",
            "history": {
                "start_date": "2025-03-17",
                "end_date": "2026-03-16",
                "start_close": 214.16,
                "end_close": 199.22,
                "return_pct": -0.07,
                "high": 388.14,
                "low": 192.87,
                "avg_volume": 852_440.0,
            },
        },
        "company_result": {
            "site_url": "https://ir.wingstop.com",
            "summary": (
                "Wingstop operates a global restaurant franchise focused on "
                "cooked-to-order wings."
            ),
            "docs_url": "https://ir.wingstop.com/stock-info/irs-documentation",
            "pricing_url": None,
            "careers_url": None,
            "careers_signal": "Hiring or careers wording appears on the official homepage text.",
            "news_items": [
                {
                    "title": "Wingstop's Stellar Q4 Earnings Boost Stocks Amid Global Expansion",
                    "source": "timothysykes.com",
                    "published_date": "2026-03-15",
                    "link": "https://example.com/company-news",
                }
            ],
        },
        "market_news_query": "Wingstop Inc. WING stock",
        "market_news_items": [
            {
                "title": "Wingstop Stock (-7.4%): Director Sale Sparks Investor Concern",
                "source": "Trefis",
                "published_date": "2026-03-04",
                "link": "https://example.com/market-news",
            }
        ],
    }


def test_parse_request_supports_ticker_and_options() -> None:
    request = stock_investment_review.parse_request(
        "WING | horizon:45d | company:Wingstop | site:https://www.wingstop.com"
    )

    assert request == {
        "ticker": "WING",
        "company_name": "Wingstop",
        "horizon": "45d",
        "site_url": "https://www.wingstop.com",
    }


def test_build_todo_markdown_mentions_horizon_and_report() -> None:
    todo_text = stock_investment_review.build_todo_markdown(
        sample_result(),
        {
            "ticker": "WING",
            "company_name": "Wingstop",
            "horizon": "45d",
            "site_url": "https://www.wingstop.com",
        },
    )

    assert "# Wingstop Inc. (WING) Investment Review - TODO" in todo_text
    assert "**Horizon:** 45d" in todo_text
    assert "Write the final report to WING.md" in todo_text


def test_build_report_markdown_has_required_headings_and_horizon() -> None:
    report_text = stock_investment_review.build_report_markdown(
        sample_result(),
        {
            "ticker": "WING",
            "company_name": "Wingstop",
            "horizon": "45d",
            "site_url": "https://www.wingstop.com",
        },
    )

    assert "**Horizon:** 45d" in report_text
    assert "informational research only, not personalized financial advice" in report_text
    assert "## Action" in report_text
    assert "## Entry" in report_text
    assert "## Exit" in report_text
    assert "## Invalidation" in report_text
    assert "## No-Trade Condition" in report_text