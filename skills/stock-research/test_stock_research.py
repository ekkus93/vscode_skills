import importlib.util
import pathlib
import sys
from types import ModuleType


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
    / "stock_research.py"
)
stock_research = load_module("stock_research", MODULE_PATH)


def test_parse_request_defaults() -> None:
    assert stock_research.parse_request("aapl") == {
        "ticker": "AAPL",
        "period": "1y",
        "news_window": "month",
        "news_limit": 3,
        "site_url": None,
    }


def test_parse_request_with_options() -> None:
    assert stock_research.parse_request(
        "LMND | period:6mo | news:week | limit:2 | site:https://www.lemonade.com"
    ) == {
        "ticker": "LMND",
        "period": "6mo",
        "news_window": "week",
        "news_limit": 2,
        "site_url": "https://www.lemonade.com",
    }


def test_build_request_from_inputs_accepts_flags() -> None:
    assert stock_research.build_request_from_inputs(
        None,
        "LMND",
        "6mo",
        "week",
        2,
        "https://www.lemonade.com",
    ) == {
        "ticker": "LMND",
        "period": "6mo",
        "news_window": "week",
        "news_limit": 2,
        "site_url": "https://www.lemonade.com",
    }


def test_build_market_news_queries_include_fallbacks() -> None:
    assert stock_research.build_market_news_queries("Lemonade, Inc.", "LMND") == [
        "Lemonade, Inc. LMND stock",
        "LMND earnings",
        "LMND analyst",
    ]


def test_research_takeaways_includes_news_gap() -> None:
    result = {
        "period": "1y",
        "market_snapshot": {
            "revenue_growth": 0.12,
            "profit_margin": -0.05,
            "history": {"return_pct": 0.15},
        },
        "market_news_query": "LMND stock",
        "market_news_items": [],
    }
    takeaways = stock_research.research_takeaways(result)
    assert "+15.0%" in takeaways[0]
    assert "No useful recent market headlines" in takeaways[-1]


def test_format_result_contains_sections() -> None:
    rendered = stock_research.format_result(
        {
            "ticker": "LMND",
            "period": "1y",
            "news_window": "month",
            "market_news_query": "Lemonade LMND stock",
            "market_snapshot": {
                "ticker": "LMND",
                "company_name": "Lemonade, Inc.",
                "currency": "USD",
                "current_price": 55.15,
                "market_cap": 4_210_000_000,
                "trailing_pe": None,
                "forward_pe": -145.13,
                "price_to_book": 7.84,
                "revenue_growth": 0.535,
                "gross_margin": 0.53,
                "operating_margin": -0.035,
                "profit_margin": -0.224,
                "sector": "Financial Services",
                "industry": "Insurance",
                "history": {
                    "end_date": "2026-03-13",
                    "start_date": "2025-03-14",
                    "start_close": 34.97,
                    "end_close": 55.15,
                    "return_pct": 0.577,
                    "high": 99.90,
                    "low": 24.31,
                    "avg_volume": 2_490_000,
                },
            },
            "company_result": {
                "site_url": "https://www.lemonade.com",
                "summary": "Insurance built for the digital era.",
                "docs_url": "https://www.lemonade.com/api",
                "pricing_url": None,
                "careers_url": None,
                "careers_signal": "No clear hiring signal was found.",
                "news_items": [
                    {
                        "title": "Lemonade expands auto coverage",
                        "source": "Reuters",
                        "published_date": "2026-03-14",
                        "link": "https://news.google.com/rss/articles/company",
                    }
                ],
            },
            "market_news_items": [
                {
                    "title": "Lemonade stock rises after earnings",
                    "source": "Reuters",
                    "published_date": "2026-03-15",
                    "link": "https://news.google.com/rss/articles/market",
                    "description": "Shares rose after quarterly results.",
                }
            ],
        }
    )
    assert "Stock research for LMND" in rendered
    assert "Market snapshot:" in rendered
    assert "Business profile:" in rendered
    assert "Research takeaways:" in rendered
    assert "Recent market news:" in rendered
    assert "Recent company news:" in rendered


def test_research_stock_wires_helpers(monkeypatch) -> None:
    monkeypatch.setattr(
        stock_research.yahoo_finance,
        "fetch_snapshot",
        lambda request: {
            "ticker": request["ticker"],
            "period": request["period"],
            "company_name": "Lemonade, Inc.",
            "website": "https://www.lemonade.com",
            "currency": "USD",
            "current_price": 55.15,
            "market_cap": 4_210_000_000,
            "trailing_pe": None,
            "forward_pe": -145.13,
            "price_to_book": 7.84,
            "revenue_growth": 0.535,
            "gross_margin": 0.53,
            "operating_margin": -0.035,
            "profit_margin": -0.224,
            "sector": "Financial Services",
            "industry": "Insurance",
            "history": {
                "end_date": "2026-03-13",
                "start_date": "2025-03-14",
                "start_close": 34.97,
                "end_close": 55.15,
                "return_pct": 0.577,
                "high": 99.90,
                "low": 24.31,
                "avg_volume": 2_490_000,
            },
        },
    )
    monkeypatch.setattr(
        stock_research.company_research,
        "research_company",
        lambda request: {
            "site_url": request["site_url"],
            "summary": "Insurance built for the digital era.",
            "docs_url": "https://www.lemonade.com/api",
            "pricing_url": None,
            "careers_url": None,
            "careers_signal": "No clear hiring signal was found.",
            "news_items": [],
        },
    )
    monkeypatch.setattr(
        stock_research,
        "fetch_market_news",
        lambda query_text, news_window, limit: [
            {
                "title": f"Headline for {query_text}",
                "source": "Reuters",
                "published_date": "2026-03-15",
                "link": "https://news.google.com/rss/articles/market",
                "description": "Shares moved after results.",
            }
        ],
    )
    result = stock_research.research_stock(
        {
            "ticker": "LMND",
            "period": "1y",
            "news_window": "month",
            "news_limit": 2,
            "site_url": None,
        }
    )
    assert result["market_news_query"] == "Lemonade, Inc. LMND stock"
    assert result["company_result"]["site_url"] == "https://www.lemonade.com"


def test_choose_market_news_falls_back_when_company_news_overlaps(monkeypatch) -> None:
    responses = {
        "Lemonade, Inc. LMND stock": [
            {
                "title": "Duplicate headline",
                "source": "Reuters",
                "published_date": "2026-03-15",
                "link": "https://example.com/duplicate",
                "description": "Same item as company news.",
            }
        ],
        "LMND earnings": [
            {
                "title": "Fresh earnings headline",
                "source": "Reuters",
                "published_date": "2026-03-16",
                "link": "https://example.com/earnings",
                "description": "Different market-news item.",
            }
        ],
    }

    monkeypatch.setattr(
        stock_research,
        "fetch_market_news",
        lambda query_text, news_window, limit: responses.get(query_text, []),
    )

    query, items = stock_research.choose_market_news(
        "Lemonade, Inc.",
        "LMND",
        "month",
        2,
        [
            {
                "title": "Duplicate headline",
                "source": "Reuters",
                "published_date": "2026-03-15",
                "link": "https://example.com/duplicate",
            }
        ],
    )

    assert query == "LMND earnings"
    assert items[0]["title"] == "Fresh earnings headline"


def test_main_rejects_bad_limit(capsys) -> None:
    original_argv = sys.argv
    sys.argv = ["stock_research.py", "AAPL | limit:5"]
    try:
        assert stock_research.main() == 1
    finally:
        sys.argv = original_argv
    captured = capsys.readouterr()
    assert "limit must be an integer between 1 and 3" in captured.err


def test_main_accepts_colon_style_news_flag(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        stock_research,
        "build_request_from_inputs",
        lambda query, ticker, period, news_window, limit, site_url: {
            "query": query,
            "ticker": ticker,
            "period": period,
            "news_window": news_window,
            "limit": limit,
            "site_url": site_url,
        },
    )
    monkeypatch.setattr(stock_research, "research_stock", lambda request: request)
    monkeypatch.setattr(stock_research, "format_result", lambda result: str(result))

    exit_code = stock_research.main(["--ticker", "NVDA", "--news:month"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "'ticker': 'NVDA'" in captured.out
    assert "'news_window': 'month'" in captured.out