import importlib.util
import pathlib
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


MODULE_PATH = pathlib.Path(__file__).resolve().parent / "arxiv_search.py"
arxiv_search = load_module("shared_arxiv_search", MODULE_PATH)


SAMPLE_FEED = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/"
      xmlns:arxiv="http://arxiv.org/schemas/atom">
  <opensearch:totalResults>42</opensearch:totalResults>
  <entry>
    <id>http://arxiv.org/abs/1234.5678v1</id>
    <updated>2024-01-03T12:34:56Z</updated>
    <published>2024-01-01T12:34:56Z</published>
    <title> Example Paper Title </title>
    <summary>  This is a sample abstract for testing the parser. </summary>
    <author><name>Alice Example</name></author>
    <author><name>Bob Example</name></author>
    <link href="http://arxiv.org/abs/1234.5678v1" rel="alternate" type="text/html" />
        <link
            title="pdf"
            href="http://arxiv.org/pdf/1234.5678v1"
            rel="related"
            type="application/pdf"
        />
    <arxiv:primary_category term="cs.LG" scheme="http://arxiv.org/schemas/atom" />
    <category term="cs.LG" scheme="http://arxiv.org/schemas/atom" />
    <category term="cs.AI" scheme="http://arxiv.org/schemas/atom" />
  </entry>
</feed>
"""


def test_normalize_plain_topic_query() -> None:
    result = arxiv_search.normalize_query("transformer attention")
    assert result["search_query"] == "(all:transformer AND all:attention)"
    assert result["sort_by"] == "relevance"
    assert result["display_query"] == "transformer attention"


def test_normalize_author_query() -> None:
    result = arxiv_search.normalize_query("author: Geoffrey Hinton")
    assert result["search_query"] == 'au:"Geoffrey Hinton"'
    assert result["sort_by"] == "lastUpdatedDate"
    assert result["display_query"] == "author: Geoffrey Hinton"


def test_normalize_empty_query_raises() -> None:
    with pytest.raises(ValueError, match="Search query cannot be empty"):
        arxiv_search.normalize_query("   ")


def test_parse_feed_extracts_core_fields() -> None:
    parsed = arxiv_search.parse_feed(SAMPLE_FEED)
    assert parsed["total_results"] == 42
    assert len(parsed["entries"]) == 1
    entry = parsed["entries"][0]
    assert entry["title"] == "Example Paper Title"
    assert entry["primary_category"] == "cs.LG"
    assert entry["authors"] == ["Alice Example", "Bob Example"]
    assert entry["abstract_url"] == "http://arxiv.org/abs/1234.5678v1"
    assert entry["pdf_url"] == "http://arxiv.org/pdf/1234.5678v1"


def test_format_results_includes_expected_sections() -> None:
    parsed = arxiv_search.parse_feed(SAMPLE_FEED)
    formatted = arxiv_search.format_results(
        {
            "display_query": "transformer attention",
            "sort_by": "relevance",
        },
        parsed,
    )
    assert 'Found 1 arXiv result(s) for "transformer attention"' in formatted
    assert "Example Paper Title" in formatted
    assert "Primary category: cs.LG" in formatted
    assert "Abstract: http://arxiv.org/abs/1234.5678v1" in formatted
    assert "PDF: http://arxiv.org/pdf/1234.5678v1" in formatted
    assert "Confidence: high" in formatted


def test_format_results_handles_empty_result_set() -> None:
    formatted = arxiv_search.format_results(
        {
            "display_query": "unknown topic",
            "sort_by": "relevance",
        },
        {"total_results": 0, "entries": []},
    )
    assert 'No arXiv results found for "unknown topic".' in formatted
    assert "Confidence: high" in formatted
