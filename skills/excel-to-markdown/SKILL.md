---
name: excel-to-markdown
description: Convert local .xlsx and .xls spreadsheet files into Markdown that Copilot can read, using deterministic local Python workbook parsing.
metadata: {"openclaw":{"os":["darwin","linux"],"requires":{"bins":["python3"]}}}
user-invocable: true
---

# Excel To Markdown

## Purpose

Convert local Microsoft Excel workbooks into `.md` files using deterministic local tooling.

For spreadsheet conversion in this shared library, prefer direct workbook parsing over screenshots or manual copy-paste.
Write one Markdown file beside the workbook so sheet names, headers, and rows are available as plain text for Copilot.

## Invocation

This skill is intended to be user-invocable by name.

If the runtime exposes skill slash commands, invoke it as:

- `/excel-to-markdown <input.xlsx>`
- `/excel-to-markdown <input.xls>`
- `/excel-to-markdown <input.xlsx> <output.md>`

Examples:

- `/excel-to-markdown /path/to/research-notes.xlsx`
- `/excel-to-markdown /tmp/vendor-pricing.xls`
- `/excel-to-markdown /tmp/vendor-pricing.xls /tmp/vendor-pricing.md`

If the input path is missing, ask the user which `.xlsx` or `.xls` workbook they want to convert.

## When to use

- The user asks to convert a local `.xlsx` file into Markdown.
- The user asks to convert a local legacy `.xls` file into Markdown.
- The user wants spreadsheet contents in a format the local model can read reliably.

## When not to use

- The request is not about a local `.xls` or `.xlsx` file.
- The user has not provided a usable local file path.
- The workbook is very large and the user wants per-sheet `.csv` or `.tsv` outputs instead; use `excel-to-delimited`.
- The task needs spreadsheet formulas recalculated, charts preserved, or pixel-perfect Office fidelity.
- The task is about CSV, PDFs, images, or screenshots instead of Excel workbooks.

## Workflow

1. Identify the local input path and confirm it ends in `.xls` or `.xlsx`.
2. If the path is missing or ambiguous, ask for the minimum clarification needed.
3. Prefer deterministic local parsing with Python packages in this order:
	- `openpyxl` for `.xlsx`
	- `xlrd` for `.xls`
4. For shell usage in the shared library, run `python3 "{baseDir}/excel_to_markdown.py" ...`.
5. Check the required package before conversion:
	- `python3 -m pip show openpyxl` for `.xlsx`
	- `python3 -m pip show xlrd` for `.xls`
6. If the required package is missing, stop before conversion and explain exactly what needs to be installed.
7. Prefer setup instructions that match this shared library workflow and this OS:
	- Step 1: install spreadsheet helpers with `python3 -m pip install openpyxl xlrd`
	- Step 2: verify the packages with `python3 -m pip show openpyxl xlrd`
	- Step 3: retry the conversion request
8. Tailor the setup instructions to the actual missing package instead of always listing both.
9. By default, write the Markdown file next to the input file using the same basename and a `.md` extension.
10. Render each worksheet as its own Markdown section and preserve tabular data as readable tables.
11. Do not invent cell contents or claim a successful conversion if the output file was not created.

## Output requirements

- State which file was processed.
- Return the output Markdown file path.
- State clearly when required Python packages are missing and provide step-by-step setup instructions tailored to the missing package.
- Preserve worksheet names in the output.
- Keep the output useful for downstream model reading rather than returning raw binary or opaque workbook metadata.

## Commands

Convert with derived output path:

```bash
python3 "{baseDir}/excel_to_markdown.py" "/path/to/research-notes.xlsx"
```

Convert with explicit output path:

```bash
python3 "{baseDir}/excel_to_markdown.py" "/tmp/vendor-pricing.xls" "/tmp/vendor-pricing.md"
```

Install spreadsheet helpers:

```bash
python3 -m pip install openpyxl xlrd
```

## Constraints

- Use the bundled helper instead of ad hoc workbook parsing.
- Preserve the source workbook and write a separate `.md` output file.
- Default the output path to the same directory as the input file when not provided.
- If the input file does not exist, say so explicitly.
- If the required Python package is missing, explain that the conversion cannot run until it is installed.
