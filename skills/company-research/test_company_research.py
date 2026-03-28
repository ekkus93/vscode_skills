import importlib.util
import pathlib
from datetime import datetime, timezone
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
    / "company_research.py"
)
company_research = load_module("company_research", MODULE_PATH)


SAMPLE_SEARCH_RSS = """<?xml version=\"1.0\" encoding=\"utf-8\" ?>
<rss version=\"2.0\"><channel>
  <item>
    <title>Linear – The system for product development</title>
    <link>https://linear.app/</link>
    <description>Official site for Linear.</description>
  </item>
  <item>
    <title>Random forum post about linear models</title>
    <link>https://example.com/forum</link>
    <description>Unrelated result.</description>
  </item>
</channel></rss>"""

SAMPLE_HTML = """
<html>
  <head>
    <title>Acme | Build better releases</title>
    <meta name="description" content="Acme provides release automation for product teams." />
  </head>
  <body>
    <a href="/docs">Docs</a>
    <a href="/pricing">Pricing</a>
    <a href="/careers">Careers</a>
    <a href="/about">About</a>
    <a href="/platform">Platform</a>
    <a href="/solutions/engineering">Engineering</a>
  </body>
</html>
"""


def test_parse_request_with_site_and_news_options() -> None:
    result = company_research.parse_request(
        "Vercel | site:https://vercel.com | news:week | limit:2"
    )
    assert result["company_name"] == "Vercel"
    assert result["site_url"] == "https://vercel.com"
    assert result["news_window"] == "week"
    assert result["news_limit"] == 2


def test_parse_request_accepts_url_target() -> None:
    result = company_research.parse_request("https://linear.app")
    assert result["company_name"] is None
    assert result["site_url"] == "https://linear.app"


def test_build_request_from_inputs_accepts_direct_flags() -> None:
    result = company_research.build_request_from_inputs(
        None,
        "Oracle",
        "https://www.oracle.com",
        "week",
        2,
    )
    assert result["company_name"] == "Oracle"
    assert result["site_url"] == "https://www.oracle.com"
    assert result["news_window"] == "week"
    assert result["news_limit"] == 2


def test_build_request_from_inputs_merges_query_with_flags() -> None:
    result = company_research.build_request_from_inputs(
        "Oracle | news:month | limit:3",
        None,
        "https://www.oracle.com",
        "day",
        1,
    )
    assert result["company_name"] == "Oracle"
    assert result["site_url"] == "https://www.oracle.com"
    assert result["news_window"] == "day"
    assert result["news_limit"] == 1


def test_build_request_from_inputs_requires_target() -> None:
    try:
        company_research.build_request_from_inputs(None, None, None, None, None)
    except ValueError as exc:
        assert "Provide a company name, official site URL, or query string" in str(exc)
    else:
        raise AssertionError("Expected missing target to raise")


def test_parse_search_results_extracts_items() -> None:
    items = company_research.parse_search_results(SAMPLE_SEARCH_RSS)
    assert len(items) == 2
    assert items[0]["link"] == "https://linear.app/"


def test_resolve_site_prefers_company_like_domain() -> None:
    items = company_research.parse_search_results(SAMPLE_SEARCH_RSS)
    best = sorted(
        items,
        key=lambda item: company_research.candidate_score("Linear", item),
        reverse=True,
    )[0]
    assert best["link"] == "https://linear.app/"
    assert company_research.candidate_score("Linear", best) >= 5


def test_parse_page_extracts_key_links() -> None:
    parsed = company_research.parse_page("https://acme.com", SAMPLE_HTML)
    assert parsed["title"] == "Acme | Build better releases"
    assert parsed["summary"] == "Acme provides release automation for product teams."
    links = parsed["links"]
    assert (
        company_research.pick_best_category_link(
            links,
            company_research.DOC_PATH_HINTS,
            company_research.DOC_KEYWORDS,
        )
        == "https://acme.com/docs"
    )
    assert (
        company_research.pick_best_category_link(
            links,
            company_research.PRICING_PATH_HINTS,
            company_research.PRICING_KEYWORDS,
        )
        == "https://acme.com/pricing"
    )
    assert (
        company_research.pick_best_category_link(
            links,
            company_research.CAREERS_PATH_HINTS,
            company_research.CAREERS_KEYWORDS,
        )
        == "https://acme.com/careers"
    )


def test_pick_best_category_link_prefers_path_matches_over_loose_text() -> None:
    links = [
        {"text": "Enterprise teams", "href": "https://example.com/solutions/enterprise"},
        {"text": "Pricing", "href": "https://example.com/pricing"},
        {"text": "Events", "href": "https://example.com/events"},
    ]
    assert (
        company_research.pick_best_category_link(
            links,
            company_research.PRICING_PATH_HINTS,
            company_research.PRICING_KEYWORDS,
        )
        == "https://example.com/pricing"
    )


def test_product_links_returns_product_like_pages() -> None:
    parsed = company_research.parse_page("https://acme.com", SAMPLE_HTML)
    products = company_research.product_links(parsed["links"])
    assert len(products) == 2
    assert products[0]["href"] == "https://acme.com/platform"


def test_build_news_query_candidates_adds_disambiguating_hint() -> None:
    candidates = company_research.build_news_query_candidates(
        "Lemonade",
        "Lemonade is an insurance company.",
        "Insurance for renters and homeowners.",
    )
    assert candidates == ["Lemonade", '"Lemonade" insurance', "Lemonade insurance"]


def test_build_news_items_retries_with_disambiguating_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generic_items = [
        {
            "title": "kids run lemonade stand for charity",
            "description": "A neighborhood fundraiser served fresh lemonade.",
            "source": "Local News",
            "source_key": "local news",
            "published_date": "2026-03-15",
            "published_at": datetime(2026, 3, 15, tzinfo=timezone.utc),
            "link": "https://news.google.com/rss/articles/GENERIC",
        }
    ]
    company_items = [
        {
            "title": "Lemonade expands car insurance availability",
            "description": "Lemonade said its insurance product is expanding.",
            "source": "Reuters",
            "source_key": "reuters",
            "published_date": "2026-03-15",
            "published_at": datetime(2026, 3, 15, tzinfo=timezone.utc),
            "link": "https://news.google.com/rss/articles/COMPANY",
        }
    ]

    def fake_request(
        query_text: str, news_window: str, limit: int
    ) -> list[dict[str, object]]:
        if query_text == "Lemonade":
            return generic_items
        if query_text == '"Lemonade" insurance':
            return company_items
        return []

    monkeypatch.setattr(company_research, "request_company_news_items", fake_request)

    items = company_research.build_news_items(
        "Lemonade",
        "month",
        1,
        "Lemonade is an insurance company.",
        "Insurance for renters and homeowners.",
    )

    assert items == company_items


def test_build_news_items_skips_irrelevant_fallback_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_request(
        query_text: str, news_window: str, limit: int
    ) -> list[dict[str, object]]:
        if query_text == "Lemonade":
            return [
                {
                    "title": "kids run lemonade stand for charity",
                    "description": "A neighborhood fundraiser served fresh lemonade.",
                    "source": "Local News",
                    "source_key": "local news",
                    "published_date": "2026-03-15",
                    "published_at": datetime(2026, 3, 15, tzinfo=timezone.utc),
                    "link": "https://news.google.com/rss/articles/GENERIC1",
                }
            ]
        if query_text in {'"Lemonade" insurance', "Lemonade insurance"}:
            return [
                {
                    "title": "Panera debuts first energy drinks since Charged Lemonade lawsuits",
                    "description": "The menu update follows Charged Lemonade headlines.",
                    "source": "WWBT",
                    "source_key": "wwbt",
                    "published_date": "2026-03-14",
                    "published_at": datetime(2026, 3, 14, tzinfo=timezone.utc),
                    "link": "https://news.google.com/rss/articles/GENERIC2",
                }
            ]
        return []

    monkeypatch.setattr(company_research, "request_company_news_items", fake_request)

    items = company_research.build_news_items(
        "Lemonade",
        "month",
        2,
        "Lemonade is an insurance company.",
        "Insurance for renters and homeowners.",
    )

    assert items == []


def test_filter_company_news_sources_prefers_higher_signal_publishers() -> None:
    items = [
        {
            "title": "Acme wins major customer",
            "source": "Traders Union",
            "source_key": "traders union",
            "published_date": "2026-03-13",
            "link": "https://news.google.com/rss/articles/AAA",
        },
        {
            "title": "Acme expands enterprise offering",
            "source": "Reuters",
            "source_key": "reuters",
            "published_date": "2026-03-13",
            "link": "https://news.google.com/rss/articles/BBB",
        },
    ]
    filtered = company_research.filter_company_news_sources(items)
    assert len(filtered) == 1
    assert filtered[0]["source"] == "Reuters"


def test_filter_company_news_sources_falls_back_when_all_items_are_filtered() -> None:
    items = [
        {
            "title": "Acme mentioned in market roundup",
            "source": "blockchain.news",
            "source_key": "blockchain.news",
            "published_date": "2026-03-13",
            "link": "https://news.google.com/rss/articles/AAA",
        }
    ]
    assert company_research.filter_company_news_sources(items) == items


def test_rank_company_news_items_prefers_high_signal_publishers() -> None:
    items = [
        {
            "title": "Acme launches new feature",
            "source": "Reuters",
            "source_key": "reuters",
            "published_at": datetime(2026, 3, 11, tzinfo=timezone.utc),
        },
        {
            "title": "Acme launches new feature",
            "source": "RACER - Racing News",
            "source_key": "racer - racing news",
            "published_at": datetime(2026, 3, 12, tzinfo=timezone.utc),
        },
        {
            "title": "Acme launches new feature",
            "source": "TradingView",
            "source_key": "tradingview",
            "published_at": datetime(2026, 3, 13, tzinfo=timezone.utc),
        },
    ]
    ranked = company_research.rank_company_news_items(items)
    assert [item["source"] for item in ranked] == [
        "Reuters",
        "RACER - Racing News",
        "TradingView",
    ]


def test_rank_company_news_items_prefers_mid_signal_blog_over_weaker_outlets() -> None:
    items = [
        {
            "title": "Acme ecosystem update",
            "source": "The GitHub Blog",
            "source_key": "the github blog",
            "published_at": datetime(2026, 3, 10, tzinfo=timezone.utc),
        },
        {
            "title": "Acme ecosystem update",
            "source": "iZOOlogic",
            "source_key": "izoologic",
            "published_at": datetime(2026, 3, 11, tzinfo=timezone.utc),
        },
        {
            "title": "Acme ecosystem update",
            "source": "RACER - Racing News",
            "source_key": "racer - racing news",
            "published_at": datetime(2026, 3, 12, tzinfo=timezone.utc),
        },
    ]
    ranked = company_research.rank_company_news_items(items)
    assert ranked[0]["source"] == "The GitHub Blog"
    assert {item["source"] for item in ranked[1:]} == {
        "iZOOlogic",
        "RACER - Racing News",
    }


def test_rank_company_news_items_keeps_preferred_sources_above_mid_signal_blog() -> None:
    items = [
        {
            "title": "Acme funding round",
            "source": "The GitHub Blog",
            "source_key": "the github blog",
            "published_at": datetime(2026, 3, 13, tzinfo=timezone.utc),
        },
        {
            "title": "Acme funding round",
            "source": "Reuters",
            "source_key": "reuters",
            "published_at": datetime(2026, 3, 12, tzinfo=timezone.utc),
        },
    ]
    ranked = company_research.rank_company_news_items(items)
    assert [item["source"] for item in ranked] == ["Reuters", "The GitHub Blog"]


def test_rank_company_news_items_keeps_recency_within_same_quality_band() -> None:
    items = [
        {
            "title": "Older Reuters story",
            "source": "Reuters",
            "source_key": "reuters",
            "published_at": datetime(2026, 3, 11, tzinfo=timezone.utc),
        },
        {
            "title": "Newer Reuters story",
            "source": "Reuters",
            "source_key": "reuters",
            "published_at": datetime(2026, 3, 13, tzinfo=timezone.utc),
        },
    ]
    ranked = company_research.rank_company_news_items(items)
    assert [item["title"] for item in ranked] == [
        "Newer Reuters story",
        "Older Reuters story",
    ]


def test_format_results_includes_sections() -> None:
    rendered = company_research.format_results(
        {
            "label": "Acme",
            "site_url": "https://acme.com",
            "resolved_from_search": False,
            "title": "Acme | Build better releases",
            "summary": "Acme provides release automation for product teams.",
            "docs_url": "https://acme.com/docs",
            "pricing_url": "https://acme.com/pricing",
            "careers_url": "https://acme.com/careers",
            "about_url": "https://acme.com/about",
            "products": [{"text": "Platform", "href": "https://acme.com/platform"}],
            "careers_signal": "Careers/jobs page found on the official site.",
            "news_items": [
                {
                    "title": "Acme raises Series B",
                    "source": "Reuters",
                    "published_date": "2026-03-13",
                    "link": "https://news.google.com/rss/articles/AAA",
                }
            ],
        }
    )
    assert "Company summary:" in rendered
    assert "Products / key pages:" in rendered
    assert "Recent news:" in rendered
    assert "Acme raises Series B" in rendered