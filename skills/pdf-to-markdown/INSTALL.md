# PDF To Markdown Install

This file is the quick-start install guide for deploying `pdf-to-markdown` on a real OpenClaw instance or another compatible local workspace.

The source of truth for dependencies remains `skills/install-manifest.json`.
Use this file as the short operator guide for this one skill.

## What this skill needs

Required binaries:

- `python3`
- `pdftoppm`
- `tesseract`

Required Python package:

- `pypdf`

## What this skill does

- Accepts local `.pdf` files
- Extracts embedded PDF text directly when available
- Falls back to OCR for scanned PDFs by rasterizing pages with `pdftoppm` and running `tesseract`
- Writes the output beside the source PDF as `<original-name>.md`

## Install steps

### Ubuntu or Debian

Install system dependencies:

```bash
sudo apt-get update
sudo apt-get install -y python3 poppler-utils tesseract-ocr
```

Install the Python dependency:

```bash
python3 -m pip install pypdf
```

### macOS with Homebrew

Install system dependencies:

```bash
brew install python poppler tesseract
```

Install the Python dependency:

```bash
python3 -m pip install pypdf
```

## Alternative install path from generated requirements

This repo also generates a skill-specific Python requirements file:

- `skills/pdf-to-markdown/requirements.txt`

You can install the Python dependency view for this skill with:

```bash
python3 -m pip install -r skills/pdf-to-markdown/requirements.txt
```

That file only covers Python packages. You still need `pdftoppm` and `tesseract` installed separately.

## Verify the install

Check that `pdftoppm` is available:

```bash
command -v pdftoppm
```

Check that `tesseract` is available:

```bash
command -v tesseract
```

Check that `pypdf` imports correctly:

```bash
python3 -c "import pypdf; print('ok')"
```

## Smoke test

From the workspace root, run:

```bash
python3 skills/pdf-to-markdown/pdf_to_markdown.py /path/to/report.pdf
```

Expected result:

- the command prints an output `.md` path beside the PDF
- the Markdown file is created with page headings in order

Example:

```bash
python3 skills/pdf-to-markdown/pdf_to_markdown.py /tmp/report.pdf
```

To force a non-default OCR language for scanned PDFs:

```bash
python3 skills/pdf-to-markdown/pdf_to_markdown.py /tmp/scan.pdf --ocr-language deu
```

## Common failures

If you see `Missing required binary: pdftoppm`:

- install `poppler-utils` on Ubuntu or Debian, or `poppler` on macOS
- rerun the command

If you see `Missing required binary: tesseract`:

- install Tesseract
- rerun the command

If you see `Missing required Python package: pypdf`:

- install the package with `python3 -m pip install pypdf`
- rerun the command

If you see `PDF contains no extractable text and OCR fallback produced no text`:

- verify the scan is readable
- confirm the needed Tesseract language data is installed
- retry with `--ocr-language` if the scan is not English

If you see `Input file not found` or `Input file must end in .pdf`:

- verify the PDF path exists and is readable from the runtime
- confirm the input ends in `.pdf`