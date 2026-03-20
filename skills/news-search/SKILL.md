---
name: news-search
description: Search recent news coverage, current events, breaking news, or what is happening now for a topic using Google News RSS and return concise, de-duplicated story summaries with source names, dates, and links.
metadata: {"openclaw":{"os":["darwin","linux"],"requires":{"bins":["python3"]}}}
user-invocable: true
---

# News Search

## Purpose
Search recent news coverage for a topic and return a concise, source-linked summary of the most relevant distinct stories.

For shared-skill news search, prefer a deterministic RSS-based workflow over generic browsing.
Use Google News RSS search as the primary discovery source because it supports unauthenticated topic search with recency scoping.
Treat feed entries as intermediate data, not user-facing output.
Prefer distinct stories over repeated syndicated coverage, and call out likely paywalled outlets when they appear.

## When to use
- The user wants recent news coverage for a company, product, technology, or broader topic.
- The user wants a quick view of what distinct stories are being covered in the last day, week, or month.
- The user wants duplicate coverage merged into a smaller set of representative headlines.

## When not to use
- The task needs a full article summary after reading the publisher page itself.
- The task needs long-form company research rather than recent news discovery.
- The task depends on private or subscription-only content being fully readable.

## Workflow
1. Accept one topic string, optionally followed by `|`-separated filters such as `time:day`, `time:week`, `time:month`, or `limit:3`.
2. If the query is empty, ask for the minimum clarification needed.
3. Query Google News RSS search with a recency operator scoped into the query string.
4. Parse feed items into title, source, publication date, description, and link.
5. Merge near-duplicate headlines so the result list focuses on distinct stories.
6. Prefer representative coverage from direct publishers over low-signal aggregator sources when duplicates exist.
7. Return 3 to 5 distinct stories by default.
8. Mention likely paywalled outlets when they appear in the sample.
9. If no useful results are found, say so explicitly.
10. If live retrieval fails, fail honestly instead of guessing.

## Output requirements
- Lead with a short answer that directly characterizes the recent coverage.
- Return 3 to 5 distinct stories by default unless the user asks for a different count.
- Include source names, dates, and links.
- Mention when duplicate headlines were merged.
- Prefer original-reporting sources where visible and avoid presenting aggregator repetition as multiple distinct stories.
- Include a confidence label and freshness date.

## Example prompts
- `/news-search OpenAI | time:week | limit:3`
- `/news-search nuclear energy | time:month | limit:3`

## Commands

Use one quoted request string:

```bash
python3 "{baseDir}/news_search.py" "OpenAI | time:week | limit:3"
```

Use explicit flags:

```bash
python3 "{baseDir}/news_search.py" --topic "OpenAI" --time week --limit 3
```

## Constraints
- Use Google News RSS through the bundled helper.
- Do not hand-build NewsAPI or other news `curl` URLs when this workflow already covers the lookup.
- Keep the result focused on distinct stories rather than repeated syndicated coverage.