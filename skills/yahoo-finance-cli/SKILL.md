---
name: yahoo-finance-cli
description: This skill should be used when the user asks to "get stock prices", "check stock quotes", "look up earnings", "get financial data", "find trending stocks", or needs stock market data from Yahoo Finance.
metadata: {"clawdbot":{"requires":{"bins":["jq","yf"]},"install":[{"id":"brew","kind":"brew","package":"jq","bins":["jq"],"label":"Install jq (Homebrew)"},{"id":"npm","kind":"node","package":"yahoo-finance2","bins":["yahoo-finance"],"label":"Install Yahoo Finance CLI (npm)"},{"id":"link-yf","kind":"exec","command":"ln -sf $(npm bin -g)/yahoo-finance /usr/local/bin/yf","label":"Link yf binary"}]}}
---

# Yahoo Finance CLI

A Node.js CLI for fetching comprehensive stock data from Yahoo Finance using the `yahoo-finance2` library.

## Purpose

Use this skill to fetch stock prices, quote data, company fundamentals, earnings information, symbol search results, and trending market symbols from Yahoo Finance.

## Requirements

- Node.js
- npm
- `yahoo-finance2` installed globally or available as `yf`
- `jq`

## When to use

- The user asks for stock prices or stock quotes.
- The user wants company financial data, earnings data, or analyst recommendations.
- The user wants to search for a ticker symbol.
- The user wants Yahoo Finance data from the command line.

## Workflow

1. Confirm what market data the user wants.
2. Check whether the required tools are available: `node`, `npm`, `jq`, and `yf`.
3. If a required dependency is missing, stop and provide step-by-step setup instructions for the user's platform.
4. After setup is complete, verify the installation with version or help commands.
5. Run the requested `yf` command.
6. Return the result directly or summarize the most relevant values.
7. If the command fails for another reason, report the error clearly.

## Install

Check whether the required tools are already installed:

```bash
command -v node
command -v npm
command -v jq
command -v yf
```

Install Node.js and npm on Ubuntu or Debian:

```bash
sudo apt-get update
sudo apt-get install -y nodejs npm
```

Install `jq` on Ubuntu or Debian:

```bash
sudo apt-get install -y jq
```

Install Node.js on macOS with Homebrew:

```bash
brew install node
```

Install `jq` on macOS with Homebrew:

```bash
brew install jq
```

Install the Yahoo Finance CLI globally with npm:

```bash
npm install -g yahoo-finance2
```

Check whether the global CLI is exposed as `yahoo-finance`:

```bash
command -v yahoo-finance
```

If `yf` is not already available, create a `yf` symlink to the installed CLI:

```bash
sudo ln -sf "$(npm bin -g)/yahoo-finance" /usr/local/bin/yf
```

Verify the final setup:

```bash
node --version
npm --version
jq --version
yf search "Apple"
```

Example one-pass setup on Ubuntu or Debian:

```bash
sudo apt-get update
sudo apt-get install -y nodejs npm jq
npm install -g yahoo-finance2
sudo ln -sf "$(npm bin -g)/yahoo-finance" /usr/local/bin/yf
yf search "Apple"
```

Example one-pass setup on macOS with Homebrew:

```bash
brew install node jq
npm install -g yahoo-finance2
sudo ln -sf "$(npm bin -g)/yahoo-finance" /usr/local/bin/yf
yf search "Apple"
```

## Usage

The tool is available as `yf`. It outputs JSON, which can be piped to `jq` for filtering.

```bash
yf <module> <symbol> [queryOptions]
```

## Modules

### Quote (Real-time Price & Data)
Get real-time price, change, and basic data.
```bash
yf quote AAPL
yf quote AAPL | jq '.regularMarketPrice'
```

### Quote Summary (Fundamentals & More)
Get detailed modules like earnings, financial data, and profiles.
```bash
# Get specific sub-modules
yf quoteSummary AAPL '{"modules":["assetProfile", "financialData", "defaultKeyStatistics"]}'

# Common modules to request:
# - assetProfile (Company info, sector)
# - financialData (Target price, margins, cash)
# - defaultKeyStatistics (Enterprise value, float, shares)
# - calendarEvents (Earnings dates)
# - earnings (History and trend)
# - recommendationTrend (Analyst ratings)
# - upgradeDowngradeHistory
```

### Insights
Get technical and fundamental insights (valuation, outlook).
```bash
yf insights AAPL
```

### Search
Search for symbols.
```bash
yf search "Apple"
yf search "BTC-USD"
```

### Historical Data (Deprecated)
Get historical OHLCV data. Note: `historical` is deprecated; use `chart` instead.
```bash
# Deprecated - use chart instead
yf historical AAPL '{"period1":"2024-01-01","period2":"2024-12-31"}'

# Recommended: use chart
yf chart AAPL '{"period1":"2024-01-01","period2":"2024-12-31"}'
```

### Trending
See what's trending.
```bash
yf trendingSymbols US
```

## Examples

**Quick Price Check**
```bash
# Full JSON then filter with jq
yf quote NVDA | jq '{symbol: .symbol, price: .regularMarketPrice, changePct: .regularMarketChangePercent}'
```

**Next Earnings Date**
```bash
# Use single quotes around the JSON option in zsh/bash
yf quoteSummary TSLA '{"modules":["calendarEvents"]}' | jq '.calendarEvents.earnings.earningsDate'
```

**Analyst Recommendations**
```bash
yf quoteSummary AAPL '{"modules":["recommendationTrend"]}'
```

**Company Profile**
```bash
yf quoteSummary MSFT '{"modules":["assetProfile"]}'
```

**Historical OHLCV**
```bash
# Using chart (recommended)
yf chart AAPL '{"period1":"2024-01-01","period2":"2024-12-31","interval":"1d"}' | jq '.quotes[0:5]'

# Using historical (deprecated, but still works)
yf historical AAPL '{"period1":"2024-01-01","period2":"2024-12-31","interval":"1d"}' | jq '.[0:5]'
```

**Search for Symbols**
```bash
yf search 'Apple'
yf search 'BTC-USD'
```

**Trending Symbols (US)**
```bash
yf trendingSymbols US
```

**Insights (valuation, outlook)**
```bash
yf insights AAPL
```

## Troubleshooting

- **Cookies:** The tool automatically handles cookies (stored in `~/.yf2-cookies.json`). If you encounter issues, try deleting this file.
- **JSON Output:** The output is pure JSON. Use `jq` to parse it for scripts or readability.

Additional tips:
- If you see authentication or parsing errors, delete the cookie file and retry:

```bash
rm -f ~/.yf2-cookies.json
yf quote AAPL
```

- On macOS with zsh, prefer single quotes around JSON option arguments and use double quotes inside (see examples above).
- If you want a compact numeric value only (no jq), use a short jq filter, e.g.:

```bash
yf quote AAPL | jq -r '.regularMarketPrice'
```

## Missing Dependency Response

If the required tools are missing, provide a short setup guide instead of attempting the finance command. Prefer a step-by-step response, for example:

1. `Install Node.js and npm.`
	Ubuntu or Debian: `sudo apt-get update && sudo apt-get install -y nodejs npm`
	macOS: `brew install node`
2. `Install jq.`
	Ubuntu or Debian: `sudo apt-get install -y jq`
	macOS: `brew install jq`
3. `Install the Yahoo Finance CLI globally.`
	Run: `npm install -g yahoo-finance2`
4. `Expose the command as yf if needed.`
	Run: `sudo ln -sf "$(npm bin -g)/yahoo-finance" /usr/local/bin/yf`
5. `Verify the setup.`
	Run: `yf search "Apple"`

If only one dependency is missing, give only the steps relevant to that missing dependency.
