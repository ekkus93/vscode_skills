---
name: excel-to-delimited
description: Convert local .xlsx and .xls workbooks into per-sheet .csv or .tsv files for large-workbook review and downstream machine-friendly processing.
metadata: {"openclaw":{"os":["darwin","linux"],"requires":{"bins":["python3"]}}}
user-invocable: true
---

# Excel To Delimited

## Purpose

Convert local Microsoft Excel workbooks into per-sheet `.csv` or `.tsv` files using deterministic local tooling.

For very large workbooks in this shared library, prefer delimited exports over one giant Markdown file.
Write one output directory beside the workbook and put one file per worksheet inside it so the contents stay chunkable and easy for tools or the model to inspect.

## Invocation

This skill is intended to be user-invocable by name.

If the runtime exposes skill slash commands, invoke it as:

- `/excel-to-delimited <input.xlsx>`
- `/excel-to-delimited <input.xls> | format:csv`
- `/excel-to-delimited <input.xls> | format:tsv`

Examples:

- `/excel-to-delimited /path/to/research-notes.xlsx`
- `/excel-to-delimited /tmp/vendor-pricing.xls | format:tsv`

If the input path is missing, ask the user which `.xlsx` or `.xls` workbook they want to convert.

## When to use

- The user asks to convert a local `.xlsx` or `.xls` workbook into `.csv` files.
- The user asks to convert a local `.xlsx` or `.xls` workbook into `.tsv` files.
- The workbook is large enough that one combined Markdown file would be unwieldy.
- The user wants machine-friendly per-sheet exports for later filtering or targeted reading.

## When not to use

- The request is not about a local `.xls` or `.xlsx` file.
- The user has not provided a usable local file path.
- The user wants a single combined Markdown representation of the workbook instead; use `excel-to-markdown`.
- The task needs formulas recalculated, charts preserved, or pixel-perfect Office fidelity.

## Workflow

1. Identify the local input path and confirm it ends in `.xls` or `.xlsx`.
2. If the path is missing or ambiguous, ask for the minimum clarification needed.
3. Accept an optional `| format:csv` or `| format:tsv` filter, defaulting to `csv`.
4. Prefer deterministic local parsing with Python packages in this order:
	- `openpyxl` for `.xlsx`
	- `xlrd` for `.xls`
5. For shell usage in the shared library, run `python3 "{baseDir}/excel_to_delimited.py" ...`.
6. Check the required package before conversion:
	- `python3 -m pip show openpyxl` for `.xlsx`
	- `python3 -m pip show xlrd` for `.xls`
7. If the required package is missing, stop before conversion and explain exactly what needs to be installed.
8. Prefer setup instructions that match this shared library workflow and this OS:
	- Step 1: install spreadsheet helpers with `python3 -m pip install openpyxl xlrd`
	- Step 2: verify the packages with `python3 -m pip show openpyxl xlrd`
	- Step 3: retry the conversion request
9. By default, write the exported files into a sibling directory named from the workbook basename plus `_csv` or `_tsv`.
10. Preserve worksheet order by numbering output filenames and keep worksheet names visible in the filenames.
11. Do not invent cell contents or claim a successful conversion if the output directory was not created.

## Output requirements

- State which file was processed.
- Return the output directory path.
- State which format was written when that is known.
- State clearly when required Python packages are missing and provide step-by-step setup instructions tailored to the missing package.
- Keep the output machine-friendly and sheet-oriented instead of collapsing everything into one large Markdown document.

## Commands

Convert with default CSV output:

```bash
python3 "{baseDir}/excel_to_delimited.py" "/path/to/research-notes.xlsx"
```

Convert with TSV request syntax:

```bash
python3 "{baseDir}/excel_to_delimited.py" --request "/tmp/vendor-pricing.xls | format:tsv"
```

Install spreadsheet helpers:

```bash
python3 -m pip install openpyxl xlrd
```

## Constraints

- Use the bundled helper instead of ad hoc workbook parsing.
- Preserve the source workbook and write separate per-sheet delimited files.
- Default the output directory to the same directory as the input file when not provided.
- If the input file does not exist, say so explicitly.
- If the required Python package is missing, explain that the conversion cannot run until it is installed.
