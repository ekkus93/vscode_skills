---
name: stock-review-supporting-research
description: Internal companion skill for stock-investment-review that gathers company context, recent catalysts, and corroborating source guidance using the shared helper bundle.
metadata: {"openclaw":{"os":["darwin","linux"],"requires":{"bins":["python3"]}}}
user-invocable: false
---

# Stock Review Supporting Research

## Purpose
Gather the company, catalyst, and corroborating research used by `stock-investment-review`.

This companion skill keeps company context, recent news, and exact shared-helper invocation rules out of the main orchestration skill.

## When to use
- `stock-investment-review` needs official-site company context.
- The review needs recent headlines, catalysts, or one more non-Yahoo supporting source.
- The workflow needs exact repo helper names so shell usage stays deterministic.

## When not to use
- The task is only a company profile; use the bundled `company_research.py` helper directly instead.
- The task is only recent news coverage; use the bundled `news_search.py` helper directly instead.
- The task is only open-web discovery and needs a dedicated search workflow outside this shared helper bundle.
- The task is only market-data collection; use `stock-review-market-context` instead.

## Workflow
1. Get official-site context with the shared `company-research` skill or its helper in `../company-research/company_research.py` when the company site is known or can be resolved safely.
2. Get recent headlines and catalyst scanning with the shared `news-search` skill or its helper in `../news-search/news_search.py`.
3. Get at least one additional non-Yahoo supporting source only when you already have a reliable direct URL or an official investor-relations page to cite.
4. Prefer official investor-relations pages, company pages, or direct publisher pages over low-signal aggregators when adding non-Yahoo sources.
5. If a URL is model-generated or uncertain, say that it is unvalidated rather than treating it as confirmed.
6. Keep facts from official or company sources separate from inference or market interpretation.
7. If a live source fails, report that failure plainly instead of guessing.

## Invocation rules
- In this shared port, the supported helper paths are the standalone shared skill folders `../company-research/` and `../news-search/`.
- Do not invent missing shared skills or wrapper names from the old OpenCode repo.

## Exact supported helper forms
- Company context:

```bash
python3 "{baseDir}/../company-research/company_research.py" "Wingstop | site:https://www.wingstop.com"
```

- Recent news:

```bash
python3 "{baseDir}/../news-search/news_search.py" --topic "Wingstop WING stock price recent catalysts" --time month --limit 3
```

## Invalid patterns
- Do not invent helper names such as `company.py`; the bundled helper is `company_research.py`.
- Do not invent missing wrapper names such as `news_search.sh`, `web_search.sh`, or `brave-search` for this shared port.
- Do not treat missing shared skills as if they were registered runtime tools.
