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
    loader.exec_module(module)
    return module


MODULE_PATH = (
    pathlib.Path(__file__).resolve().parent
    / "yahoo_finance.py"
)
yahoo_finance = load_module("yahoo_finance", MODULE_PATH)


def test_parse_request_defaults_to_one_year() -> None:
    assert yahoo_finance.parse_request("aapl") == {"ticker": "AAPL", "period": "1y"}


def test_parse_request_accepts_period_option() -> None:
    assert yahoo_finance.parse_request("LMND | period:6mo") == {
        "ticker": "LMND",
        "period": "6mo",
    }


def test_build_request_from_inputs_accepts_flags() -> None:
    assert yahoo_finance.build_request_from_inputs(None, "lmnd", "6mo") == {
        "ticker": "LMND",
        "period": "6mo",
    }


def test_parse_request_rejects_bad_period() -> None:
    try:
        yahoo_finance.parse_request("AAPL | period:7mo")
    except ValueError as exc:
        assert "period must be one of" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected ValueError for unsupported period")


def test_format_large_number_uses_suffixes() -> None:
    assert yahoo_finance.format_large_number(1_500_000_000) == "1.50B"


def test_history_metrics_computes_return_and_range() -> None:
    metrics = yahoo_finance.history_metrics(
        [
            {"date": "2026-01-01", "close": 100.0, "high": 101.0, "low": 99.0, "volume": 10.0},
            {"date": "2026-01-02", "close": 110.0, "high": 111.0, "low": 98.0, "volume": 30.0},
        ]
    )
    assert metrics["return_pct"] == 0.10
    assert metrics["high"] == 111.0
    assert metrics["low"] == 98.0
    assert metrics["avg_volume"] == 20.0


def test_format_result_contains_expected_sections() -> None:
    rendered = yahoo_finance.format_result(
        {
            "ticker": "LMND",
            "period": "1y",
            "company_name": "Lemonade, Inc.",
            "quote_type": "EQUITY",
            "exchange": "NYQ",
            "currency": "USD",
            "current_price": 44.1,
            "market_cap": 3_100_000_000,
            "trailing_pe": None,
            "forward_pe": None,
            "price_to_book": 2.5,
            "dividend_yield": None,
            "revenue_growth": 0.18,
            "gross_margin": 0.71,
            "operating_margin": -0.10,
            "profit_margin": -0.08,
            "sector": "Financial Services",
            "industry": "Insurance",
            "website": "https://www.lemonade.com",
            "summary": "Insurance built for the digital era.",
            "history": {
                "start_date": "2025-03-15",
                "end_date": "2026-03-15",
                "start_close": 35.0,
                "end_close": 44.1,
                "return_pct": 0.26,
                "high": 52.0,
                "low": 14.0,
                "avg_volume": 2_000_000,
            },
        }
    )
    assert "Yahoo Finance snapshot for LMND" in rendered
    assert "Market snapshot:" in rendered
    assert "Fundamentals:" in rendered
    assert "Business summary:" in rendered


def test_main_rejects_invalid_ticker(capsys: pytest.CaptureFixture[str]) -> None:
    original_argv = sys.argv
    sys.argv = ["yahoo_finance.py", "bad ticker!"]
    try:
        assert yahoo_finance.main() == 1
    finally:
        sys.argv = original_argv

    captured = capsys.readouterr()
    assert "unsupported characters" in captured.err.lower()


def test_main_rejects_query_and_ticker_mix(capsys: pytest.CaptureFixture[str]) -> None:
    original_argv = sys.argv
    sys.argv = ["yahoo_finance.py", "LMND | period:1y", "--ticker", "LMND"]
    try:
        assert yahoo_finance.main() == 1
    finally:
        sys.argv = original_argv

    captured = capsys.readouterr()
    assert "either a quoted query or --ticker" in captured.err