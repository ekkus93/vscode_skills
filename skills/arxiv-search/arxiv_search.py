#!/usr/bin/env python3
import argparse
import re
import sys
import textwrap
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
OPENSEARCH_NS = {"opensearch": "http://a9.com/-/spec/opensearch/1.1/"}
ARXIV_NS = {"arxiv": "http://arxiv.org/schemas/atom"}

PREFIX_MAP = {
    "author": "au",
    "au": "au",
    "category": "cat",
    "cat": "cat",
    "title": "ti",
    "ti": "ti",
    "abstract": "abs",
    "abs": "abs",
    "all": "all",
}

API_URLS = [
    "https://export.arxiv.org/api/query",
    "http://export.arxiv.org/api/query",
]


def collapse_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def truncate_summary(value: str, limit: int = 320) -> str:
    clean = collapse_whitespace(value)
    if len(clean) <= limit:
        return clean
    shortened = clean[: limit - 1].rsplit(" ", 1)[0].rstrip()
    return shortened + "..."


def format_author_term(value: str) -> str:
    clean = collapse_whitespace(value)
    if not clean:
        raise ValueError("Author query cannot be empty")
    return f'au:"{clean}"'


def format_category_term(value: str) -> str:
    clean = collapse_whitespace(value)
    if not clean:
        raise ValueError("Category query cannot be empty")
    return f"cat:{clean}"


def format_keyword_terms(prefix: str, value: str) -> str:
    tokens = [token for token in re.split(r"\s+", collapse_whitespace(value)) if token]
    if not tokens:
        raise ValueError("Search query cannot be empty")
    if len(tokens) == 1:
        return f"{prefix}:{tokens[0]}"
    return "(" + " AND ".join(f"{prefix}:{token}" for token in tokens) + ")"


def normalize_query(raw_query: str) -> dict[str, str]:
    query = collapse_whitespace(raw_query)
    if not query:
        raise ValueError("Search query cannot be empty")

    match = re.match(
        r"^(author|au|category|cat|title|ti|abstract|abs|all)\s*:\s*(.+)$",
        query,
        re.IGNORECASE,
    )
    if match:
        raw_prefix = match.group(1).lower()
        value = match.group(2)
        prefix = PREFIX_MAP[raw_prefix]
    else:
        raw_prefix = "all"
        prefix = "all"
        value = query

    if prefix == "au":
        search_query = format_author_term(value)
        sort_by = "lastUpdatedDate"
    elif prefix == "cat":
        search_query = format_category_term(value)
        sort_by = "lastUpdatedDate"
    else:
        search_query = format_keyword_terms(prefix, value)
        sort_by = "relevance"

    display = f"{raw_prefix}: {collapse_whitespace(value)}" if match else collapse_whitespace(value)
    return {
        "display_query": display,
        "search_query": search_query,
        "sort_by": sort_by,
        "sort_order": "descending",
    }


def build_request_url(raw_query: str, max_results: int) -> tuple[str, dict[str, str]]:
    normalized = normalize_query(raw_query)
    params = {
        "search_query": normalized["search_query"],
        "start": 0,
        "max_results": max_results,
        "sortBy": normalized["sort_by"],
        "sortOrder": normalized["sort_order"],
    }
    return urllib.parse.urlencode(params), normalized


def fetch_xml(query_string: str) -> str:
    headers = {"User-Agent": "vscode_skills/1.0 (arxiv-search helper)"}
    last_error: urllib.error.URLError | None = None
    for base_url in API_URLS:
        request = urllib.request.Request(f"{base_url}?{query_string}", headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = response.read()
                if isinstance(payload, bytes):
                    return payload.decode("utf-8", errors="replace")
                if isinstance(payload, bytearray):
                    return bytes(payload).decode("utf-8", errors="replace")
                return str(payload)
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                raise RuntimeError(
                    "arXiv API rate limited the request (HTTP 429); retry later"
                ) from exc
            last_error = exc
        except urllib.error.URLError as exc:
            last_error = exc
    if last_error is None:
        raise RuntimeError("arXiv search failed before sending a request")
    raise RuntimeError(f"arXiv search failed: {last_error}")


def _text(node: ET.Element | None, path: str, namespace: dict[str, str]) -> str:
    if node is None:
        return ""
    child = node.find(path, namespace)
    return collapse_whitespace(child.text if child is not None and child.text else "")


def parse_feed(xml_text: str) -> dict[str, object]:
    root = ET.fromstring(xml_text)
    total_results = int(_text(root, "opensearch:totalResults", OPENSEARCH_NS) or "0")
    entries: list[dict[str, object]] = []
    for entry in root.findall("atom:entry", ATOM_NS):
        title = _text(entry, "atom:title", ATOM_NS)
        summary = _text(entry, "atom:summary", ATOM_NS)
        if title == "Error":
            raise RuntimeError(summary or "arXiv returned an error")

        authors = [
            collapse_whitespace(author.findtext("atom:name", default="", namespaces=ATOM_NS))
            for author in entry.findall("atom:author", ATOM_NS)
            if collapse_whitespace(author.findtext("atom:name", default="", namespaces=ATOM_NS))
        ]
        categories = [
            item.attrib.get("term", "")
            for item in entry.findall("atom:category", ATOM_NS)
            if item.attrib.get("term")
        ]
        primary_category_node = entry.find("arxiv:primary_category", ARXIV_NS)
        abstract_url = ""
        pdf_url = ""
        for link in entry.findall("atom:link", ATOM_NS):
            href = link.attrib.get("href", "")
            title_attr = link.attrib.get("title", "")
            rel_attr = link.attrib.get("rel", "")
            if rel_attr == "alternate" and href:
                abstract_url = href
            if title_attr == "pdf" and href:
                pdf_url = href
        entries.append(
            {
                "title": title,
                "published": _text(entry, "atom:published", ATOM_NS),
                "updated": _text(entry, "atom:updated", ATOM_NS),
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": (
                    primary_category_node.attrib.get("term", "")
                    if primary_category_node is not None
                    else ""
                ),
                "abstract_url": abstract_url,
                "pdf_url": pdf_url,
            }
        )
    return {"total_results": total_results, "entries": entries}


def format_authors(authors: list[str]) -> str:
    if not authors:
        return "Unknown"
    if len(authors) <= 4:
        return ", ".join(authors)
    shown = ", ".join(authors[:4])
    return f"{shown}, +{len(authors) - 4} more"


def format_results(query_info: dict[str, str], parsed: dict[str, object]) -> str:
    checked_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    entries = parsed["entries"]
    total_results = parsed["total_results"]
    if not isinstance(entries, list) or not isinstance(total_results, int):
        raise RuntimeError("arXiv search returned an unexpected response structure")
    if not entries:
        return textwrap.dedent(
            f'''\
            No arXiv results found for "{query_info["display_query"]}".

            Confidence: high
            Freshness: checked {checked_date}
            '''
        ).strip()

    sort_label = "relevance" if query_info["sort_by"] == "relevance" else "last updated date"
    lines = [
        (
            f'Found {len(entries)} arXiv result(s) for "{query_info["display_query"]}" '
            f"(showing {len(entries)} of {total_results}), sorted by {sort_label}."
        ),
        "",
    ]
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            raise RuntimeError("arXiv search returned an unexpected entry structure")
        authors = entry.get("authors", [])
        categories = entry.get("categories", [])
        lines.append(f"{index}. {entry.get('title', '')}")
        lines.append(f"   Authors: {format_authors(authors if isinstance(authors, list) else [])}")
        published = entry.get("published", "")
        updated = entry.get("updated", "")
        primary_category = entry.get("primary_category", "")
        summary = entry.get("summary", "")
        abstract_url = entry.get("abstract_url", "")
        pdf_url = entry.get("pdf_url", "")
        if isinstance(published, str) and published:
            lines.append(f"   Published: {published[:10]}")
        if isinstance(updated, str) and updated:
            lines.append(f"   Updated: {updated[:10]}")
        if isinstance(primary_category, str) and primary_category:
            lines.append(f"   Primary category: {primary_category}")
        elif isinstance(categories, list) and categories:
            lines.append(f"   Categories: {', '.join(str(item) for item in categories[:3])}")
        lines.append(f"   Summary: {truncate_summary(str(summary))}")
        if isinstance(abstract_url, str) and abstract_url:
            lines.append(f"   Abstract: {abstract_url}")
        if isinstance(pdf_url, str) and pdf_url:
            lines.append(f"   PDF: {pdf_url}")
        lines.append("")
    lines.append("Confidence: high")
    lines.append(f"Freshness: checked {checked_date}")
    return "\n".join(lines).rstrip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Search arXiv and summarize results")
    parser.add_argument("query")
    parser.add_argument("--max-results", type=int, default=5)
    args = parser.parse_args()

    if args.max_results < 1 or args.max_results > 5:
        print("max-results must be between 1 and 5", file=sys.stderr)
        return 2

    try:
        query_string, query_info = build_request_url(args.query, args.max_results)
        xml_text = fetch_xml(query_string)
        parsed = parse_feed(xml_text)
        print(format_results(query_info, parsed))
        return 0
    except (ValueError, RuntimeError, ET.ParseError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())