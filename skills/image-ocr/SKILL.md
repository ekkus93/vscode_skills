---
name: image-ocr
description: Use when the user wants OCR text extraction from an image file such as .png, .jpg, .jpeg, .tif, or .tiff.
metadata: {"openclaw":{"os":["darwin","linux"],"requires":{"bins":["tesseract"]}}}
user-invocable: true
---

# Image OCR

## Purpose

Use this skill to extract text from an image file with OCR and write the result to a text file.

## Invocation

This skill is intended to be user-invocable by name.

If the runtime exposes skill slash commands, invoke it as:

- `/image-ocr <input-image>`
- `/image-ocr <input-image> <output-base>`
- `/image-ocr <input-image> <output-base> <language>`

Examples:

- `/image-ocr receipt.png`
- `/image-ocr scan.jpg scan-ocr`
- `/image-ocr form.tif form-ocr eng`

If the input path is missing, ask the user which image file they want to process.

## When to use

- The user wants OCR on an image file.
- The user wants text extracted from a screenshot, scan, photo, or receipt.
- The user has a `.png`, `.jpg`, `.jpeg`, `.tif`, or `.tiff` file and wants the text content.
- The user wants the OCR result saved to a file.

## Workflow

1. Confirm the input image path.
2. Determine the output base path.
3. If no output base path is provided, use the input filename without its extension in the same directory.
4. If no OCR language is provided, default to `eng`.
5. Verify that the input file exists.
6. Run `tesseract` against the input image and output base path.
7. Return the generated output path, which will normally be `<output-base>.txt`.
8. If the user asked for the extracted text directly, provide a concise text result or preview in addition to the output path.
9. If `tesseract` is not installed, tell the user how to install it on their platform before retrying.
10. If OCR fails for another reason, report the error clearly.

## Commands

Convert with derived output path:

```bash
input="receipt.png"
output_base="${input%.*}"
tesseract "$input" "$output_base" -l eng
```

Convert with explicit output base:

```bash
tesseract "scan.jpg" "scan-ocr" -l eng
```

Convert with an explicit language:

```bash
tesseract "form.tif" "form-ocr" -l eng
```

Check whether Tesseract is installed:

```bash
command -v tesseract
```

Install on Ubuntu or Debian:

```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr
```

Install on Fedora:

```bash
sudo dnf install -y tesseract
```

Install on Arch Linux:

```bash
sudo pacman -S tesseract
```

Install on macOS with Homebrew:

```bash
brew install tesseract
```

## Output

Prefer a short direct answer, for example:

- `Extracted text from receipt.png to receipt.txt`
- `Extracted text from /path/scan.jpg to /path/scan-ocr.txt`
- `OCR complete: form-ocr.txt`

## Constraints

- Use `tesseract` for OCR.
- Preserve the source image and write the OCR result to a separate output file.
- Default the output path to the same directory as the input image when not provided.
- The output base path passed to `tesseract` should not include the `.txt` extension.
- If the input file does not exist, say so explicitly.
- If `tesseract` is not installed, explain that OCR cannot run yet and provide install instructions appropriate to the platform when possible.
- If a requested OCR language is unavailable in the local Tesseract installation, report that clearly.

## Missing Dependency Response

If `tesseract` is missing, prefer a short direct answer that includes install guidance, for example:

- `Tesseract is not installed, so OCR cannot run yet. On Ubuntu or Debian, run: sudo apt-get update && sudo apt-get install -y tesseract-ocr`
- `Tesseract is not installed. On macOS with Homebrew, run: brew install tesseract`
- `Tesseract is not installed. Install it first, then rerun the OCR command.`