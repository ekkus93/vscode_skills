---
name: docx-to-markdown
description: Use when the user wants to convert a .docx or .doc file into a Markdown .md file.
metadata: {"openclaw":{"os":["darwin","linux"],"requires":{"bins":["pandoc"]}}}
user-invocable: true
---

# DOCX To Markdown

## Purpose

Use this skill to convert a `.docx` or `.doc` file into a Markdown `.md` file.

## Invocation

This skill is intended to be user-invocable by name.

If the runtime exposes skill slash commands, invoke it as:

- `/docx-to-markdown <input.docx>`
- `/docx-to-markdown <input.docx> <output.md>`
- `/docx-to-markdown <input.doc> <output.md>`

Examples:

- `/docx-to-markdown notes.docx`
- `/docx-to-markdown report.docx report.md`
- `/docx-to-markdown legacy.doc legacy.md`

If the input path is missing, ask the user which `.docx` or `.doc` file they want to convert.

## When to use

- The user asks to convert a Word document to Markdown.
- The user has a `.docx` file and wants a `.md` version.
- The user has a legacy `.doc` file and wants a `.md` version.
- The user wants text extracted from a `.docx` file in Markdown format.

## Workflow

1. Confirm the input `.docx` or `.doc` path.
2. Determine the output `.md` path.
3. If no output path is provided, use the input filename with the `.md` extension in the same directory.
4. If the input is `.docx`, run `pandoc` directly.
5. If the input is `.doc`, first convert it to `.docx` with LibreOffice or `soffice`, then convert that `.docx` file to Markdown with `pandoc`.
6. Return the output path.
7. If the conversion fails, report the error clearly.

## Commands

Convert with explicit output path:

```bash
pandoc "input.docx" -t gfm -o "output.md"
```

Convert and derive the output name automatically:

```bash
input="notes.docx"
output="${input%.docx}.md"
pandoc "$input" -t gfm -o "$output"
```

Legacy `.doc` conversion using LibreOffice, then `pandoc`:

```bash
input="legacy.doc"
tmp_docx="${input%.doc}.docx"
output="${input%.doc}.md"
soffice --headless --convert-to docx --outdir "$(dirname "$input")" "$input"
pandoc "$tmp_docx" -t gfm -o "$output"
```

## Output

Prefer a short direct answer, for example:

- `Converted notes.docx to notes.md`
- `Converted /path/report.docx to /path/report.md`
- `Converted legacy.doc to legacy.md`

## Constraints

- Use `pandoc` for conversion.
- For legacy `.doc` files, use LibreOffice or `soffice` to produce an intermediate `.docx` file before running `pandoc`.
- Preserve the source file and write a separate `.md` output file.
- Default the output path to the same directory as the input file when not provided.
- If the input file does not exist, say so explicitly.
- If `pandoc` is not installed, say that the conversion cannot be run until it is installed.
- If the input is `.doc` and `soffice` is not installed, say that legacy `.doc` conversion requires LibreOffice.