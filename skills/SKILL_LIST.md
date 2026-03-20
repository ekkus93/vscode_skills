# Skill List

This file lists reusable skills available in the shared workspace skill library.

## How to use this index
1. Match the user task to the closest skill.
2. Open that skill directory.
3. Read the skill's `SKILL.md`.
4. Follow the skill's procedure, constraints, and output format.
5. Do not claim to have used a skill unless you actually read its `SKILL.md`.

## Skills

### stock-investment-review
- Path: `skills/stock-investment-review/`
- Use for: producing a saved stock investment review with a TODO file and Markdown report for a public ticker over a default 30-day horizon or another explicit short-term range
- Typical outputs: `<TICKER>_TODO.md`, `<TICKER>.md`, scenario-based stock review, action/entry/exit/invalidation sections

### stock-research
- Path: `skills/stock-research/`
- Use for: building a longer-form public stock research snapshot that combines market data, company context, and recent headlines
- Typical outputs: stock research summary, market snapshot, business profile, recent market news, recent company news

### company-research
- Path: `skills/company-research/`
- Use for: researching a company from official-site context first, then adding recent company news as supporting context
- Typical outputs: company summary, docs/pricing/careers signals, official URLs, recent company news

### news-search
- Path: `skills/news-search/`
- Use for: finding recent distinct news stories for a topic with source names, dates, links, and deduplicated coverage
- Typical outputs: recent coverage summary, distinct story list, paywall note, source-linked headlines

### yahoo-finance
- Path: `skills/yahoo-finance/`
- Use for: fetching a concise market snapshot for one public stock or ETF ticker with recent performance and basic fundamentals
- Typical outputs: price snapshot, sampled performance, valuation metrics, fundamentals summary

### stock-review-market-context
- Path: `skills/stock-review-market-context/`
- Use for: internal companion rules for one-year market context, technical levels, and bundled stock-review helper usage
- Typical outputs: one-year price context, technical posture summary, helper invocation guidance

### stock-review-output-contract
- Path: `skills/stock-review-output-contract/`
- Use for: internal companion rules for required TODO/report files and the exact final decision section layout
- Typical outputs: TODO structure requirements, report section contract, final decision template

### stock-review-supporting-research
- Path: `skills/stock-review-supporting-research/`
- Use for: internal companion rules for official-site context, recent catalysts, and bundled helper invocation guidance
- Typical outputs: supporting research workflow, company/news helper guidance, corroborating-source rules

### arxiv-search
- Path: `skills/arxiv-search/`
- Use for: searching arXiv for papers by topic, author, category, title, or abstract query
- Typical outputs: concise paper shortlist, abstract links, PDF links, short metadata summaries

### yahoo-finance-cli
- Path: `skills/yahoo-finance-cli/`
- Use for: fetching stock prices, financial data, and market summaries using Yahoo Finance CLI
- Typical outputs: stock quotes, financial metrics, market overviews

### current-date-time
- Path: `skills/current-date-time/`
- Use for: getting the current local date, current time, or current datetime from the system clock
- Typical outputs: current local time, current date, UTC timestamp

### weather
- Path: `skills/weather/`
- Use for: getting the current weather, temperature, and simple forecast for a city or location
- Typical outputs: current conditions, temperature summary, short forecast

### wikipedia
- Path: `skills/wikipedia/`
- Use for: searching Wikipedia and getting a concise summary for a topic, person, place, event, or concept
- Typical outputs: page summary, resolved topic title, short encyclopedia overview

### docx-to-markdown
- Path: `skills/docx-to-markdown/`
- Use for: converting `.docx` and legacy `.doc` files into Markdown `.md` files
- Typical outputs: converted markdown file, output path confirmation

### excel-to-markdown
- Path: `skills/excel-to-markdown/`
- Use for: converting local `.xlsx` and `.xls` workbooks into a single Markdown file for readable workbook review
- Typical outputs: converted markdown workbook, output path confirmation, per-sheet markdown sections

### excel-to-delimited
- Path: `skills/excel-to-delimited/`
- Use for: converting local `.xlsx` and `.xls` workbooks into per-sheet `.csv` or `.tsv` exports
- Typical outputs: output directory path, per-sheet delimited files, sheet-oriented machine-friendly exports

### image-ocr
- Path: `skills/image-ocr/`
- Use for: extracting text from image files with OCR using Tesseract
- Typical outputs: OCR text file, extracted text preview, output path confirmation

### bitcoin-price
- Path: `skills/bitcoin-price/`
- Use for: getting the current Bitcoin price in USD
- Typical outputs: current BTC price, short Bitcoin price summary

### hacker-news-top10
- Path: `skills/hacker-news-top10/`
- Use for: getting the current top 10 Hacker News stories with titles, URLs, and short summaries
- Typical outputs: top 10 story list, article links, short story summaries