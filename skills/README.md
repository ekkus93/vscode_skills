# Shared Skills Library

This folder is a small shared library of reusable skills.

A skill is a directory that usually contains a `SKILL.md` file with instructions for when the skill should be used, what it is for, and what workflow the agent should follow.

## How This Library Works

There are two parts to pay attention to:

1. `SKILL_LIST.md`
2. The individual skill folders

`SKILL_LIST.md` is the index and source of truth for what skills are considered available.

The skill folders contain the actual implementation details, usually in `SKILL.md`.

In practice, the workflow is:

1. Look at the user task.
2. Match it to a skill in `SKILL_LIST.md`.
3. Open that skill's folder.
4. Read its `SKILL.md`.
5. Follow the instructions in that file.

## Important Rule

A folder existing on disk does not automatically make it an available skill.

For example, this directory currently contains a `list-skills` folder, but `list-skills` is not registered in `SKILL_LIST.md`.

That means the index is treated as authoritative. If a skill is not listed in `SKILL_LIST.md`, it should not be assumed to be part of the official shared skill set.

## Directory Layout

The current pattern looks like this:

```text
skills/
	README.md
	SKILL_LIST.md
	arxiv-search/
		SKILL.md
		arxiv_search.py
		test_arxiv_search.py
	bitcoin-price/
		SKILL.md
	company-research/
		SKILL.md
		company_research.py
		test_company_research.py
	current-date-time/
		SKILL.md
	docx-to-markdown/
		SKILL.md
	excel-to-delimited/
		SKILL.md
		excel_to_delimited.py
		test_excel_to_delimited.py
	excel-to-markdown/
		SKILL.md
		excel_to_markdown.py
		test_excel_to_markdown.py
	hacker-news-top10/
		SKILL.md
	image-ocr/
		SKILL.md
	news-search/
		SKILL.md
		news_search.py
		test_news_search.py
	stock-investment-review/
		SKILL.md
		stock_investment_review.py
		test_stock_investment_review.py
	stock-research/
		SKILL.md
		stock_research.py
		test_stock_research.py
	stock-review-market-context/
		SKILL.md
	stock-review-output-contract/
		SKILL.md
	stock-review-supporting-research/
		SKILL.md
	weather/
		SKILL.md
	wikipedia/
		SKILL.md
	yahoo-finance/
		SKILL.md
		yahoo_finance.py
		test_yahoo_finance.py
	yahoo-finance-cli/
		SKILL.md
	list-skills/
		SKILL.md
```

Typical meanings:

- `README.md`: human documentation for this library
- `SKILL_LIST.md`: index of the skills that should be treated as available
- `<skill-name>/SKILL.md`: instructions for that skill
- optional extra files like `_meta.json`: metadata or publishing history for a skill

## What Goes In A Skill

Based on the current skills in this folder, a skill usually includes:

- a clear purpose
- when to use it
- when not to use it
- a required workflow
- an expected output format
- any constraints or caveats

Some skills are simple markdown instructions.

Some skills may also use YAML frontmatter and extra metadata files if they are intended to work with external registries or toolchains.

Some shared skills also bundle helper code and tests inside the skill folder when the workflow needs deterministic local behavior. For example, `arxiv-search`, `excel-to-markdown`, `excel-to-delimited`, `yahoo-finance`, `news-search`, `company-research`, `stock-research`, and `stock-investment-review` include helper code or tests alongside `SKILL.md`.

## How To Use A Skill

When a task comes in:

1. Read `SKILL_LIST.md` first.
2. Pick the closest matching skill.
3. Read that skill's `SKILL.md` completely.
4. Use the skill's workflow and output format when handling the task.
5. Do not claim to have used a skill unless you actually read its `SKILL.md`.

## How To Add A New Skill

If you want to add a new shared skill here, do both of these things:

1. Create a new folder for the skill.
2. Add the skill to `SKILL_LIST.md`.

Recommended process:

1. Create `skills/<skill-name>/`.
2. Add `skills/<skill-name>/SKILL.md`.
3. Write the skill's purpose, usage conditions, workflow, output format, and constraints.
4. Add an entry for it in `SKILL_LIST.md` with:
	 - skill name
	 - path
	 - what it is for
	 - typical outputs
5. Only treat it as officially available after it has been added to `SKILL_LIST.md`.

## How To Update A Skill

When changing an existing skill:

1. Update the skill's `SKILL.md`.
2. Update `SKILL_LIST.md` if the purpose, path, or typical outputs changed.
3. Keep the index and the folder contents in sync.

## Current Skills

According to `SKILL_LIST.md`, the currently registered shared skills are:

- `arxiv-search`: search arXiv for relevant papers and return concise, source-linked results
- `bitcoin-price`: get the current Bitcoin price in USD
- `current-date-time`: get the current local date, time, or datetime from the system clock
- `docx-to-markdown`: convert `.docx` and legacy `.doc` files into Markdown `.md` files
- `excel-to-markdown`: convert `.xlsx` and `.xls` workbooks into a Markdown file for model-readable review
- `excel-to-delimited`: convert `.xlsx` and `.xls` workbooks into per-sheet `.csv` or `.tsv` exports
- `hacker-news-top10`: get the current top 10 Hacker News stories with titles, URLs, and short summaries
- `image-ocr`: extract text from image files with OCR using Tesseract
- `company-research`: build a concise company profile from official-site context plus recent news
- `news-search`: search recent distinct news coverage for a topic
- `stock-investment-review`: build a stock review with a saved TODO checklist and Markdown report
- `stock-research`: build a longer-form public stock research snapshot
- `stock-review-market-context`: companion rules for one-year market context and technical framing
- `stock-review-output-contract`: companion rules for the required TODO/report deliverables and final decision template
- `stock-review-supporting-research`: companion rules for company context, catalysts, and supporting research guidance
- `weather`: get the current weather, temperature, or a simple forecast for a location
- `wikipedia`: search Wikipedia and return a concise topic summary
- `yahoo-finance`: fetch a concise market snapshot from Yahoo Finance via `yfinance`
- `yahoo-finance-cli`: fetch stock prices, financial data, and market summaries with the Yahoo Finance CLI

## OpenClaw Prerequisites

If you want to install this shared skill set on a real OpenClaw bot, these are the runtime dependencies to plan for.

The machine-readable version of this dependency audit lives in `skills/install-manifest.json`.

### Core binaries

These cover most of the registered skills:

- `python3`
- `curl`
- `date`

### Extra binaries or CLIs used by specific skills

- `pandoc` for `docx-to-markdown`
- `soffice` or LibreOffice for legacy `.doc` input in `docx-to-markdown`
- `tesseract` for `image-ocr`
- `jq` for `yahoo-finance-cli`
- `node` and `npm` for `yahoo-finance-cli`
- `yf` for `yahoo-finance-cli`, usually exposed by the globally installed `yahoo-finance2` package

### Python packages used by specific skills

- `yfinance` for `yahoo-finance`, `stock-research`, `stock-investment-review`, and `stock-review-market-context`
- `openpyxl` for `.xlsx` support in `excel-to-markdown` and `excel-to-delimited`
- `xlrd` for `.xls` support in `excel-to-markdown` and `excel-to-delimited`

### Internet access

These skills depend on live network access at runtime:

- `arxiv-search`
- `bitcoin-price`
- `company-research`
- `hacker-news-top10`
- `news-search`
- `stock-investment-review`
- `stock-research`
- `stock-review-market-context`
- `stock-review-supporting-research`
- `weather`
- `wikipedia`
- `yahoo-finance`
- `yahoo-finance-cli`

### One-pass install guidance

Ubuntu or Debian baseline:

```bash
sudo apt-get update
sudo apt-get install -y python3 curl jq pandoc tesseract-ocr nodejs npm libreoffice
python3 -m pip install yfinance openpyxl xlrd
npm install -g yahoo-finance2
sudo ln -sf "$(npm bin -g)/yahoo-finance" /usr/local/bin/yf
```

macOS with Homebrew baseline:

```bash
brew install python curl jq pandoc tesseract node libreoffice
python3 -m pip install yfinance openpyxl xlrd
npm install -g yahoo-finance2
sudo ln -sf "$(npm bin -g)/yahoo-finance" /usr/local/bin/yf
```

If you do not need every skill, you can install only the subset required by the skills you plan to enable.

## Per-Skill Dependency Matrix

| Skill | Needs installable dependencies? | What to install | Notes |
| --- | --- | --- | --- |
| `arxiv-search` | Yes | `python3` | Uses the bundled Python helper and arXiv network access. |
| `bitcoin-price` | Yes | `curl`, `python3` | Calls CoinGecko over HTTP. |
| `company-research` | Yes | `python3` | Uses the bundled Python helper and live web/news retrieval. |
| `current-date-time` | Yes | `date` | Uses the system clock only. |
| `docx-to-markdown` | Yes | `pandoc` | Also needs `soffice` or LibreOffice if you want legacy `.doc` support. |
| `excel-to-delimited` | Yes | `python3`, `openpyxl`, `xlrd` | `openpyxl` is for `.xlsx`; `xlrd` is for legacy `.xls`. |
| `excel-to-markdown` | Yes | `python3`, `openpyxl`, `xlrd` | `openpyxl` is for `.xlsx`; `xlrd` is for legacy `.xls`. |
| `hacker-news-top10` | Yes | `curl`, `python3` | Uses the Hacker News API and linked page fetches. |
| `image-ocr` | Yes | `tesseract` | Additional Tesseract language packs may be needed for non-English OCR. |
| `news-search` | Yes | `python3` | Uses the bundled Python helper and Google News RSS. |
| `stock-investment-review` | Yes | `python3`, `yfinance` | Also depends on the registered helper skills `stock-research`, `company-research`, `news-search`, and `yahoo-finance`. |
| `stock-research` | Yes | `python3`, `yfinance` | Also uses the shared `company-research` and `news-search` helpers. |
| `stock-review-market-context` | Yes | `python3`, `yfinance` | Companion skill that routes through `stock-research` and `yahoo-finance`. |
| `stock-review-output-contract` | No extra install | none | Markdown/file-structure rules only. |
| `stock-review-supporting-research` | Yes | `python3` | Companion skill that routes through `company-research` and `news-search`. |
| `weather` | Yes | `curl` | Uses `wttr.in` over HTTP. |
| `wikipedia` | Yes | `curl`, `python3` | Uses the Wikipedia API over HTTP. |
| `yahoo-finance` | Yes | `python3`, `yfinance` | Uses the bundled Python helper and Yahoo Finance network access. |
| `yahoo-finance-cli` | Yes | `node`, `npm`, `jq`, `yahoo-finance2`, `yf` | Install `yahoo-finance2` globally, then expose or symlink the CLI as `yf`. |
| `list-skills` | No extra install | none | Unregistered helper skill that only reads `SKILL_LIST.md`. |

## Minimum Install Sets

If you want a smaller OpenClaw deployment, these bundles cover the major categories:

- Research-only bundle: `python3 curl`
- Finance bundle: `python3 curl jq node npm` plus `python3 -m pip install yfinance` and global `npm install -g yahoo-finance2`
- Document conversion bundle: `pandoc` plus `python3 -m pip install openpyxl xlrd`, and LibreOffice if you need `.doc`
- OCR bundle: `tesseract`

## Summary

The simplest way to think about this directory is:

- the folders hold the skill content
- `SKILL_LIST.md` declares which skills are officially available
- a skill should be read before it is used
- adding a folder alone is not enough; the index must also be updated
