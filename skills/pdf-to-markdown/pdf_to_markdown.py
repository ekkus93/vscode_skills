from __future__ import annotations

import argparse
import importlib
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_OCR_LANGUAGE = "eng"


class InputValidationError(RuntimeError):
    pass


def default_output_path(input_file: str | Path) -> Path:
    return Path(input_file).with_suffix(".md")


def title_from_path(input_file: str | Path) -> str:
    stem = Path(input_file).stem
    return re.sub(r"[-_]+", " ", stem).strip() or "Document"


def clean_page_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in normalized.split("\n")]

    collapsed: list[str] = []
    previous_blank = False
    for line in lines:
        if line:
            collapsed.append(line)
            previous_blank = False
            continue
        if not previous_blank:
            collapsed.append("")
        previous_blank = True

    return "\n".join(collapsed).strip()


def render_markdown(title: str, page_texts: list[str]) -> str:
    parts = [f"# {title}", ""]
    for index, page_text in enumerate(page_texts, start=1):
        parts.append(f"## Page {index}")
        parts.append("")
        parts.append(page_text or "_No extractable text on this page._")
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def ensure_binary_available(binary_name: str, install_hint: str) -> None:
    if shutil.which(binary_name) is None:
        raise RuntimeError(f"Missing required binary: {binary_name}. {install_hint}")


def extract_text_pages(input_file: str | Path) -> list[str]:
    try:
        pypdf = importlib.import_module("pypdf")
    except ImportError as exc:
        raise RuntimeError(
            "Missing required Python package: pypdf. Install it with "
            "python3 -m pip install pypdf"
        ) from exc

    reader = pypdf.PdfReader(str(input_file))
    return [clean_page_text(page.extract_text() or "") for page in reader.pages]


def rasterize_pdf_pages(input_file: str | Path, output_dir: str | Path) -> list[Path]:
    ensure_binary_available(
        "pdftoppm",
        "Install poppler-utils on Ubuntu/Debian or poppler on macOS, then retry OCR fallback.",
    )
    output_prefix = Path(output_dir) / "page"
    command = [
        "pdftoppm",
        "-png",
        str(input_file),
        str(output_prefix),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "unknown pdftoppm error"
        raise RuntimeError(f"pdftoppm failed during OCR fallback: {detail}")

    images = sorted(Path(output_dir).glob("page-*.png"))
    if not images:
        raise RuntimeError("OCR fallback could not render PDF pages to images")
    return images


def ocr_image_file(image_file: str | Path, language: str = DEFAULT_OCR_LANGUAGE) -> str:
    ensure_binary_available(
        "tesseract",
        "Install Tesseract first, then retry OCR fallback for scanned PDFs.",
    )
    command = ["tesseract", str(image_file), "stdout", "-l", language]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "unknown tesseract error"
        raise RuntimeError(f"tesseract failed during OCR fallback: {detail}")
    return clean_page_text(completed.stdout)


def ocr_pdf_pages(input_file: str | Path, language: str = DEFAULT_OCR_LANGUAGE) -> list[str]:
    with tempfile.TemporaryDirectory(prefix="pdf-to-markdown-ocr-") as temp_dir:
        images = rasterize_pdf_pages(input_file, temp_dir)
        return [ocr_image_file(image_path, language=language) for image_path in images]


def extract_pdf_pages(input_file: str | Path, language: str = DEFAULT_OCR_LANGUAGE) -> list[str]:
    text_pages = extract_text_pages(input_file)
    if any(text_pages):
        return text_pages

    ocr_pages = ocr_pdf_pages(input_file, language=language)
    if any(ocr_pages):
        return ocr_pages

    raise RuntimeError(
        "PDF contains no extractable text and OCR fallback produced no text. "
        "Verify that the PDF is readable and that Tesseract language data is installed."
    )


def convert_pdf_to_markdown(
    input_file: str | Path,
    output_file: str | Path | None = None,
    ocr_language: str = DEFAULT_OCR_LANGUAGE,
) -> Path:
    input_path = Path(input_file).expanduser().resolve()
    if not input_path.is_file():
        raise InputValidationError(f"Input file not found: {input_path}")
    if input_path.suffix.lower() != ".pdf":
        raise InputValidationError("Input file must end in .pdf")

    output_path = (
        Path(output_file).expanduser().resolve()
        if output_file is not None
        else default_output_path(input_path)
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    page_texts = extract_pdf_pages(input_path, language=ocr_language)
    markdown = render_markdown(title_from_path(input_path), page_texts)
    output_path.write_text(markdown, encoding="utf-8")

    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise RuntimeError("Markdown output was not created")

    return output_path


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert text-based PDF files to Markdown")
    parser.add_argument("input_file", help="Path to the local PDF file to convert")
    parser.add_argument(
        "output_file",
        nargs="?",
        default=None,
        help="Optional output path for the Markdown file",
    )
    parser.add_argument(
        "--ocr-language",
        default=DEFAULT_OCR_LANGUAGE,
        help="Tesseract OCR language to use for scanned PDFs (defaults to eng)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    try:
        output_path = convert_pdf_to_markdown(
            args.input_file,
            args.output_file,
            ocr_language=args.ocr_language,
        )
    except InputValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())