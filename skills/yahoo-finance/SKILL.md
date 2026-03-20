---
name: yahoo-finance
description: Fetch a public stock or ETF snapshot from Yahoo Finance via the yfinance Python library, including recent price performance and basic fundamentals.
metadata: {"openclaw":{"os":["darwin","linux"],"requires":{"bins":["python3"]}}}
user-invocable: true
---

# Yahoo Finance

## Purpose
Fetch a concise public-market ticker snapshot from Yahoo Finance using the `yfinance` Python library.

For shared-skill market data, use the bundled helper in this skill folder rather than ad hoc browsing.
Keep the result focused on recent price action, market snapshot, and basic fundamentals for one ticker at a time.

## When to use
- The user wants a quick snapshot for a public stock or ETF ticker.
- The user wants recent price performance plus basic valuation or margin metrics in one place.
- The user provides one ticker symbol, optionally with a sampling period.

## When not to use
- The user needs deep SEC filing analysis, discounted cash flow modeling, or portfolio construction.
- The request is for personalized investment advice, entry timing, or exit timing.
- The user wants a longer-form stock research snapshot that also includes official-site company context and recent headlines; use `stock-research` instead.
- The task is really about company websites or product positioning; use `company-research` instead.

## Workflow
1. Accept one ticker symbol, optionally followed by `| period:<value>`.
2. In v1, support these periods: `1mo`, `3mo`, `6mo`, `1y`, `2y`, `5y`, `10y`, `ytd`, `max`.
3. Use the local `yfinance` Python package as the authoritative source for price history and ticker metadata.
4. For shell usage in the shared library, run `python3 "{baseDir}/yahoo_finance.py" ...`.
5. If `yfinance` is not installed, stop and explain exactly how to install it with `python3 -m pip install yfinance`.
7. Fetch one ticker only.
8. Return recent performance, market snapshot, and basic fundamentals.
9. If Yahoo Finance returns no usable history for the ticker, fail honestly instead of guessing.
10. Label the result as market data, not investment advice.

## Output requirements
- Lead with a short direct summary of the ticker and sampled performance.
- Include market snapshot and fundamentals sections.
- State the sampling period used.
- Include a caveat that `yfinance` is an unofficial Yahoo Finance wrapper.
- Avoid giving buy, sell, entry, or exit recommendations.

## Example prompts
- `/yahoo-finance AAPL`
- `/yahoo-finance LMND | period:1y`

## Commands

Query with a single request string:

```bash
python3 "{baseDir}/yahoo_finance.py" "AAPL | period:1y"
```

Query with explicit flags:

```bash
python3 "{baseDir}/yahoo_finance.py" --ticker AAPL --period 1y
```

Install the required package:

```bash
python3 -m pip install yfinance
```

## Constraints
- Use the bundled helper instead of ad hoc Yahoo Finance scraping.
- Support one ticker at a time.
- Keep the result factual and non-advisory.