---
name: pdf-to-markdown
description: Convert local PDF files into Markdown files using direct text extraction first and OCR fallback for scanned PDFs.
metadata: {"openclaw":{"os":["darwin","linux"],"requires":{"bins":["python3","pdftoppm","tesseract"]}}}
user-invocable: true
---

# PDF To Markdown

## Purpose

Convert local `.pdf` files into `.md` files using deterministic local tooling.

Write one Markdown file beside the PDF so the extracted content is easier for Copilot to read and reuse.

This skill prefers embedded text extraction first, then automatically falls back to OCR for scanned PDFs.

For deployment and operator setup guidance, see `INSTALL.md` in this skill folder.

## Invocation

This skill is intended to be user-invocable by name.

If the runtime exposes skill slash commands, invoke it as:

- `/pdf-to-markdown <input.pdf>`
- `/pdf-to-markdown <input.pdf> <output.md>`

Examples:

- `/pdf-to-markdown /path/to/report.pdf`
- `/pdf-to-markdown /tmp/notes.pdf /tmp/notes.md`

If the input path is missing, ask the user which local `.pdf` file they want to convert.

## When to use

- The user asks to convert a local PDF into Markdown.
- The user has a text-based or scanned `.pdf` file and wants a `.md` version.
- The user wants PDF text extracted into a format the local model can read reliably.

## When not to use

- The request is not about a local `.pdf` file.
- The user has not provided a usable local file path.
- The task requires pixel-perfect layout preservation, complex tables, or embedded-image extraction.

## Workflow

1. Identify the local input path and confirm it ends in `.pdf`.
2. If the path is missing or ambiguous, ask for the minimum clarification needed.
3. For shell usage in the shared library, run `python3 "{baseDir}/pdf_to_markdown.py" ...`.
4. Check the required package before conversion:
   - `python3 -m pip show pypdf`
5. If `pypdf` is missing, stop before conversion and explain exactly what needs to be installed.
6. Prefer setup instructions that match this shared library workflow:
   - Step 1: install the PDF helper with `python3 -m pip install pypdf`
   - Step 2: verify it with `python3 -m pip show pypdf`
   - Step 3: retry the conversion request
7. By default, write the Markdown file next to the input file using the same basename and a `.md` extension.
8. If the PDF has embedded text, extract it directly with `pypdf`.
9. If the PDF has no embedded text, rasterize the pages with `pdftoppm` and run OCR with `tesseract`.
10. Preserve page order and clearly separate extracted content by page in the output.
11. Do not invent text or claim a successful conversion if the output file was not created.
12. If OCR fallback is needed but `pdftoppm` or `tesseract` is missing, say so clearly and provide install guidance.

## Output requirements

- State which file was processed.
- Return the output Markdown file path.
- State clearly when `pypdf` is missing and provide step-by-step setup instructions.
- State clearly when OCR fallback cannot run because `pdftoppm` or `tesseract` is missing.
- Keep the output useful for downstream model reading rather than opaque PDF metadata.

## Commands

Convert with derived output path:

```bash
python3 "{baseDir}/pdf_to_markdown.py" "/path/to/report.pdf"
```

Convert with explicit output path:

```bash
python3 "{baseDir}/pdf_to_markdown.py" "/tmp/notes.pdf" "/tmp/notes.md"
```

Install the PDF helper dependency:

```bash
python3 -m pip install pypdf
```

OCR fallback prerequisites for scanned PDFs:

```bash
command -v pdftoppm
command -v tesseract
```

## Constraints

- Use the bundled helper instead of ad hoc PDF parsing.
- Preserve the source PDF and write a separate `.md` output file.
- Default the output path to the same directory as the input file when not provided.
- If the input file does not exist, say so explicitly.
- If `pypdf` is missing, explain that the conversion cannot run until it is installed.
- For scanned PDFs, OCR fallback requires both `pdftoppm` and `tesseract`.
- OCR quality depends on scan quality and installed Tesseract language data.