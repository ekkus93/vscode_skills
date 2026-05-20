import importlib.util
import pathlib
import sys
from types import ModuleType, SimpleNamespace

import pytest


def load_module(name: str, path: pathlib.Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    loader = spec.loader
    assert loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


MODULE_PATH = pathlib.Path(__file__).resolve().parent / "pdf_to_markdown.py"
pdf_to_markdown = load_module("pdf_to_markdown", MODULE_PATH)


def test_default_output_path_uses_md_extension() -> None:
    assert pdf_to_markdown.default_output_path("/tmp/report.pdf") == pathlib.Path(
        "/tmp/report.md"
    )


def test_clean_page_text_collapses_blank_lines() -> None:
    cleaned = pdf_to_markdown.clean_page_text(
        " Title \n\n\n First paragraph. \r\n Second line \n\n"
    )

    assert cleaned == "Title\n\nFirst paragraph.\nSecond line"


def test_render_markdown_preserves_page_order() -> None:
    rendered = pdf_to_markdown.render_markdown("Demo Report", ["Page one text", ""])

    assert rendered.startswith("# Demo Report\n")
    assert "## Page 1\n\nPage one text" in rendered
    assert "## Page 2\n\n_No extractable text on this page._" in rendered


def test_extract_text_pages_uses_pypdf_reader(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_reader = lambda path: SimpleNamespace(  # noqa: E731
        pages=[
            SimpleNamespace(extract_text=lambda: "Hello\n\nworld"),
            SimpleNamespace(extract_text=lambda: "Second page"),
        ]
    )
    monkeypatch.setattr(
        pdf_to_markdown.importlib,
        "import_module",
        lambda name: SimpleNamespace(PdfReader=fake_reader),
    )

    page_texts = pdf_to_markdown.extract_text_pages("/tmp/report.pdf")

    assert page_texts == ["Hello\n\nworld", "Second page"]


def test_extract_pdf_pages_falls_back_to_ocr_when_text_extraction_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pdf_to_markdown, "extract_text_pages", lambda path: ["", ""])
    monkeypatch.setattr(
        pdf_to_markdown,
        "ocr_pdf_pages",
        lambda path, language="eng": ["OCR page 1", "OCR page 2"],
    )

    page_texts = pdf_to_markdown.extract_pdf_pages("/tmp/scan.pdf")

    assert page_texts == ["OCR page 1", "OCR page 2"]


def test_extract_pdf_pages_reports_empty_ocr_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pdf_to_markdown, "extract_text_pages", lambda path: [""])
    monkeypatch.setattr(pdf_to_markdown, "ocr_pdf_pages", lambda path, language="eng": [""])

    with pytest.raises(RuntimeError, match="OCR fallback produced no text"):
        pdf_to_markdown.extract_pdf_pages("/tmp/scan.pdf")


def test_rasterize_pdf_pages_reports_missing_pdftoppm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pdf_to_markdown.shutil, "which", lambda _: None)

    with pytest.raises(RuntimeError, match="Missing required binary: pdftoppm"):
        pdf_to_markdown.rasterize_pdf_pages("/tmp/scan.pdf", "/tmp/out")


def test_ocr_image_file_reports_missing_tesseract(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pdf_to_markdown.shutil, "which", lambda _: None)

    with pytest.raises(RuntimeError, match="Missing required binary: tesseract"):
        pdf_to_markdown.ocr_image_file("/tmp/page-1.png")


def test_convert_pdf_to_markdown_writes_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    input_file = tmp_path / "notes.pdf"
    input_file.write_bytes(b"%PDF-1.4")

    monkeypatch.setattr(
        pdf_to_markdown,
        "extract_pdf_pages",
        lambda path, language="eng": ["First page", "Second page"],
    )

    output_path = pdf_to_markdown.convert_pdf_to_markdown(input_file)

    assert output_path == tmp_path / "notes.md"
    rendered = output_path.read_text(encoding="utf-8")
    assert "# notes" in rendered
    assert "## Page 1" in rendered
    assert "First page" in rendered


def test_main_rejects_non_pdf_input(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    input_file = tmp_path / "sample.txt"
    input_file.write_text("hello", encoding="utf-8")

    assert pdf_to_markdown.main([str(input_file)]) == 2

    captured = capsys.readouterr()
    assert "Input file must end in .pdf" in captured.err


def test_main_prints_output_path_on_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    input_file = tmp_path / "paper.pdf"
    input_file.write_bytes(b"%PDF-1.4")
    expected_output = tmp_path / "paper.md"

    monkeypatch.setattr(
        pdf_to_markdown,
        "convert_pdf_to_markdown",
        lambda input_file, output_file=None, ocr_language="eng": expected_output,
    )

    assert pdf_to_markdown.main([str(input_file)]) == 0

    captured = capsys.readouterr()
    assert str(expected_output) in captured.out


def test_main_passes_ocr_language_on_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    input_file = tmp_path / "scan.pdf"
    input_file.write_bytes(b"%PDF-1.4")
    expected_output = tmp_path / "scan.md"

    def fake_convert(
        input_file: str | pathlib.Path,
        output_file: str | pathlib.Path | None = None,
        ocr_language: str = "eng",
    ) -> pathlib.Path:
        assert pathlib.Path(input_file).name == "scan.pdf"
        assert output_file is None
        assert ocr_language == "deu"
        return expected_output

    monkeypatch.setattr(pdf_to_markdown, "convert_pdf_to_markdown", fake_convert)

    assert pdf_to_markdown.main([str(input_file), "--ocr-language", "deu"]) == 0

    captured = capsys.readouterr()
    assert str(expected_output) in captured.out