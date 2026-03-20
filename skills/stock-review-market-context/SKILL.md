---
name: stock-review-market-context
description: Internal companion skill for stock-investment-review that gathers one-year market context, technical levels, and shared-library helper usage rules.
metadata: {"openclaw":{"os":["darwin","linux"],"requires":{"bins":["python3"]}}}
user-invocable: false
---

# Stock Review Market Context

## Purpose
Gather the one-year market and technical context used by `stock-investment-review`.

This companion skill keeps market-data collection, lookback defaults, and stock-versus-crypto routing out of the main orchestration skill.

## When to use
- `stock-investment-review` needs one-year price context and technical levels.
- A longer-form investment workflow needs the correct stock or crypto market-data helper.
- The review needs a baseline combined market snapshot before scenario analysis.

## When not to use
- The user only wants a quick public-market snapshot; use the bundled `yahoo_finance.py` helper directly instead.
- The task is primarily about crypto market context; this shared port does not bundle the old OpenCode crypto helper set.
- The task is about company pages, recent news, or web corroboration; use `stock-review-supporting-research` instead.

## Workflow
1. Default the technical lookback to the past 1 year unless the user explicitly requests another lookback.
2. For stock-like symbols, get the baseline combined snapshot with the shared `stock-research` skill or its helper in `../stock-research/stock_research.py`.
3. Get the clean market-data view and one-year price context with the shared `yahoo-finance` skill or its helper in `../yahoo-finance/yahoo_finance.py`.
4. Extract the key technical context needed for the review, such as trend behavior, support and resistance, one-year range, and sampled performance.
5. If the target is Bitcoin, `BTC-USD`, or another crypto-style symbol, stop and say that this shared port does not bundle the crypto-specific review helpers, rather than guessing or hand-building new market requests.
6. Treat fetched data as intermediate input, not final user-facing output.
7. If a live source returns no usable data, fail honestly instead of guessing.

## Invocation rules
- In this shared port, the supported helper paths are the standalone shared skill folders `../stock-research/` and `../yahoo-finance/`.
- Do not invent missing wrapper commands when the standalone shared skills are the documented path.

## Commands

Combined one-year stock context:

```bash
python3 "{baseDir}/../stock-research/stock_research.py" --ticker WING --period 1y --news month --limit 3
```

Direct one-year market snapshot:

```bash
python3 "{baseDir}/../yahoo-finance/yahoo_finance.py" --ticker WING --period 1y
```

Install the required finance dependency:

```bash
python3 -m pip install yfinance
```

## Output requirements
- State the sampled period or lookback clearly.
- Surface the key technical levels and recent performance needed for the final investment review.
- Keep the output factual and preparatory rather than turning it into a final buy or sell call.

## Implementation note
- For direct shared-library stock context usage, prefer `python3 "{baseDir}/../stock-research/stock_research.py" --ticker <TICKER> --period 1y --news month --limit 3` or `python3 "{baseDir}/../yahoo-finance/yahoo_finance.py" --ticker <TICKER> --period 1y`.
- This shared-library port does not bundle the old OpenCode crypto review wrappers.
