---
name: stock-investment-review
description: Use when the user wants a 30-day stock investment review, or another explicit short-term horizon, with a saved TODO file and Markdown report for a public stock.
metadata: {"openclaw":{"os":["darwin","linux"],"requires":{"bins":["python3"]}}}
user-invocable: true
---

# Stock Investment Review

## Purpose
Evaluate whether a public stock looks attractive over a default 30-day horizon, or another explicit time range, by orchestrating one-year market context, company and catalyst research, and a saved TODO and report pair.

This is the user-facing entry skill for the full review workflow. It should stay focused on orchestration and final decision quality, while delegating repeated details to these companion skills:
- `stock-review-market-context`
- `stock-review-supporting-research`
- `stock-review-output-contract`

This shared-library port uses the standalone shared `stock-research`, `company-research`, `news-search`, and `yahoo-finance` helper skills rather than the old OpenCode repo wrappers.

## When to use
- The user wants to decide whether a public stock looks investable over roughly the next 30 days.
- The user wants the same workflow applied to a different explicit time horizon such as 2 weeks, 45 days, 3 months, or 6 months.
- The user wants a more opinionated research workflow than a simple data snapshot.
- The user wants a TODO checklist and a saved Markdown report file.
- The user wants market data plus additional sources from news, company pages, or the broader web.

## When not to use
- The user only wants a fast market snapshot; use `yahoo-finance` instead.
- The user only wants a concise combined research summary; use `stock-research` instead.
- The user wants guaranteed returns, exact timing certainty, or personalized investment advice.
- The task needs deep SEC filing analysis, discounted cash flow modeling, or portfolio construction.

## Inputs
- If the runtime exposes skill slash commands, invoke it as `/stock-investment-review <query>`.
- For shell usage, run the bundled helper directly with `python3 "{baseDir}/stock_investment_review.py" ...`.
- Do not invent wrapper names or repo-root commands that do not exist in this shared library.
- Never emit a bare `|` in Bash for this workflow. In shell context, `|` starts a pipeline and causes tokens like `horizon:30d` to be executed as separate commands.
- Accept one public ticker symbol or one public company name.
- Default the investment horizon to the next 30 days.
- Optionally accept `| horizon:<value>` where value is a plain-language range such as `14d`, `30d`, `45d`, `3mo`, or `6mo`.
- Optionally accept `| company:<name>` when the company name is useful for broader web searches.
- Optionally accept `| site:https://...` when the official site should be pinned explicitly.
- If the user provides a company name without a ticker, resolve the most likely public ticker first and continue automatically.
- Only ask a follow-up when the company name is ambiguous, maps to multiple plausible public companies, or does not clearly map to a public ticker.

Examples:
- `<TICKER>`
- `<COMPANY_NAME>`
- `<TICKER> | horizon:45d`
- `<TICKER> | company:<COMPANY_NAME>`
- `<TICKER> | horizon:3mo | company:<COMPANY_NAME> | site:https://<OFFICIAL_SITE>`

Shell examples:
- `python3 "{baseDir}/stock_investment_review.py" <TICKER>`
- `python3 "{baseDir}/stock_investment_review.py" "<TICKER> | horizon:45d | company:<COMPANY_NAME> | site:https://<OFFICIAL_SITE>"`
- `python3 "{baseDir}/stock_investment_review.py" --ticker <TICKER> --horizon 45d --company <COMPANY_NAME> --site https://<OFFICIAL_SITE>`

Invalid shell example:
- `python3 "{baseDir}/stock_investment_review.py" <TICKER> | company:<COMPANY_NAME>`

## Workflow
1. Treat the horizon as the next 30 days by default, but override it when the request includes an explicit `horizon:` value.
2. If the input is a company name rather than a ticker, resolve the most likely public ticker before starting the research workflow. For example, `Oracle` should resolve to `ORCL` without a follow-up.
3. Only ask for clarification when the company-to-ticker mapping is genuinely ambiguous or when there is no clear public ticker.
4. Keep the technical lookback at the past 1 year unless the user explicitly asks for a different lookback.
5. Do not delegate this workflow to a separate background runner when the current agent can execute it directly.
6. Load the companion skills when you need their rules, or use the bundled helper files in this folder when operating in a shell context.
7. Start by following `stock-review-output-contract` to create `<RESOLVED_TICKER>_TODO.md` and `<RESOLVED_TICKER>.md` in the current directory.
8. Follow `stock-review-market-context` to gather the baseline market view, one-year price context, technical levels, and any crypto-specific routing.
9. Follow `stock-review-supporting-research` to gather company context, recent catalysts, corroborating web research, URL validation, and exact helper-invocation rules.
10. Keep facts from company or official sources separate from inference or market interpretation.
11. If a required live source fails, say so explicitly in the report rather than filling the gap with guesses.
12. Translate entry and exit timing into practical trigger windows or conditions, not exact clock times.
13. Tailor the urgency and scenario framing to the requested horizon instead of forcing everything into a 30-day lens.
14. Finish only when both files exist, the TODO file reflects completed work, and the report ends with the exact headings `## Action`, `## Entry`, `## Exit`, `## Invalidation`, and `## No-Trade Condition`.

## Invocation rules
- `stock-investment-review` is the user-facing entry skill for the whole workflow, not a request to invent new runtime tools.
- Companion names such as `stock-review-market-context`, `stock-review-supporting-research`, and `stock-review-output-contract` can be loaded through the skill system when available.
- The bundled helper entrypoint is `python3 "{baseDir}/stock_investment_review.py" ...`.
- The main helper entrypoint delegates to the standalone shared helper modules in the sibling `stock-research` and `yahoo-finance` skill folders.
- Do not invent missing shared skills or wrapper commands for this workflow.

## Commands

Run a full review with a default 30-day horizon:

```bash
python3 "{baseDir}/stock_investment_review.py" "WING | company:Wingstop | site:https://www.wingstop.com"
```

Run a 45-day review:

```bash
python3 "{baseDir}/stock_investment_review.py" "WING | horizon:45d | company:Wingstop | site:https://www.wingstop.com"
```

Run with explicit flags:

```bash
python3 "{baseDir}/stock_investment_review.py" --ticker WING --horizon 45d --company Wingstop --site https://www.wingstop.com
```

Check whether Python is installed:

```bash
command -v python3
```

Install the required finance dependency:

```bash
python3 -m pip install yfinance
```

## Output requirements
- Create exactly two files in the current directory:
  - `<RESOLVED_TICKER>_TODO.md`
  - `<RESOLVED_TICKER>.md`
- Do not return only an inline chat summary when this skill is used; the two Markdown files are required deliverables.
- The TODO file should be detailed, actionable, and visibly updated as tasks are completed.
- The report file must follow `stock-review-output-contract`, including the required final decision template.
- Include a caveat that the report is informational research, not personalized financial advice.
- Make source quality explicit when relying on weaker web evidence.
- Do not stop at general position-management advice; the final report must end with a clear user-facing action or a clear no-trade conclusion.

## Companion skills

### `stock-review-market-context`
- One-year market-data and technical-lookback rules.
- Shared-library guidance for using the bundled `stock_research.py` and `yahoo_finance.py` helpers.
- Honest handling of unsupported crypto-specific routing in this shared port.

### `stock-review-supporting-research`
- Official-site company context.
- Recent headlines and catalyst scanning.
- Additional corroborating source guidance when a reliable URL is already available.
- Exact supported helper names in the bundled helper folder.

### `stock-review-output-contract`
- Required TODO and report files.
- Required TODO phases and update behavior.
- Required report sections and final decision template.

## Example prompt
- `/stock-investment-review <TICKER> | company:<COMPANY_NAME> | site:https://<OFFICIAL_SITE>`
- `/stock-investment-review <TICKER> | horizon:45d | company:<COMPANY_NAME> | site:https://<OFFICIAL_SITE>`
- `/stock-investment-review <TICKER> | company:<COMPANY_NAME> | horizon:30d`

## Constraints
- This shared port depends on the standalone shared `stock-research`, `company-research`, `news-search`, and `yahoo-finance` helper skills.
- The helper needs `python3` and the `yfinance` package.
- The default technical lookback remains 1 year.
- The report must end with `## Action`, `## Entry`, `## Exit`, `## Invalidation`, and `## No-Trade Condition`.
- This workflow is for informational research, not personalized financial advice.

