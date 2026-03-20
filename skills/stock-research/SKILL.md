---
name: stock-research
description: Build a longer-form public stock research snapshot by combining Yahoo Finance market data, official-site company profiling, and recent news context.
metadata: {"openclaw":{"os":["darwin","linux"],"requires":{"bins":["python3"]}}}
user-invocable: true
---

# Stock Research

## Purpose
Build a longer-form public stock research snapshot by combining Yahoo Finance ticker data, official-site company profiling, and recent news context.

For shared-skill stock research, prefer a deterministic helper that gathers one ticker's market snapshot, business profile, and recent headlines into one result.
Keep the output factual and research-oriented rather than turning it into personalized trading advice.
Do not hand-build search or news `curl` URLs for this task when `stock-research`, `news-search`, and the shared helper bundle already cover the lookup.

## When to use
- The user wants a longer-form research snapshot for one public stock ticker.
- The user wants market data plus official company context plus recent headlines in one place.
- The user provides one ticker, optionally with a market-data period and news window.

## When not to use
- The user only wants a fast price and fundamentals snapshot; use `yahoo-finance` instead.
- The user only wants company website and product context; use `company-research` instead.
- The user wants entry price, exit price, or personalized trade timing.
- The user needs full SEC-filing analysis or portfolio construction.

## Workflow
1. Accept one ticker symbol, optionally followed by `|`-separated options.
2. If the runtime exposes skill slash commands, prefer `/stock-research ...`.
3. For shell usage in the shared library, run `python3 "{baseDir}/stock_research.py" ...`.
4. In v1, support:
	- `period:<value>` where value is one of `1mo`, `3mo`, `6mo`, `1y`, `2y`, `5y`, `10y`, `ytd`, `max`
	- `news:<value>` where value is one of `day`, `week`, `month`
	- `limit:<value>` where value is an integer from `1` to `3`
	- `site:https://...` when the company official site should be pinned explicitly
5. Use `yfinance` for market data and basic fundamentals.
6. Use the shared `company-research` helper for official-site profile information.
7. Use the shared `news-search` helper logic for recent market headlines.
8. If `yfinance` is missing, explain how to install it with `python3 -m pip install yfinance`.
9. Use the company-research workflow for official-site profile information.
10. Use the news-search workflow for recent market headlines.
11. If any upstream source returns no usable data, fail honestly instead of guessing.
12. Keep the result factual, concise, and explicitly non-advisory.

## Output requirements
- Lead with a short direct stock-research summary.
- Include sections for market snapshot, business profile, research takeaways, recent market news, and recent company news.
- State the sampled `period` and `news` window.
- Include a caveat that the result is a research snapshot, not investment advice.
- Avoid buy, sell, entry, or exit recommendations.

## Example prompts
- `/stock-research AAPL`
- `/stock-research LMND | period:1y | news:month`
- `/stock-research <TICKER> | period:6mo | news:week | limit:2`

## Commands

Use one quoted request string:

```bash
python3 "{baseDir}/stock_research.py" "AAPL | period:1y | news:month | limit:2"
```

Use explicit flags:

```bash
python3 "{baseDir}/stock_research.py" --ticker AAPL --period 1y --news month --limit 2
```

Install the required finance dependency:

```bash
python3 -m pip install yfinance
```

## Constraints
- Use the shared `yahoo-finance`, `company-research`, and `news-search` helper logic through deterministic local helpers.
- Keep the result factual and non-advisory.
- Support one ticker at a time.