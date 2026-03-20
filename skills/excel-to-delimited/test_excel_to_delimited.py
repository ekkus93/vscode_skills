import importlib.util
import pathlib
import sys
from types import ModuleType

import pytest


def load_module(name: str, path: pathlib.Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    loader = spec.loader
    assert loader is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


MODULE_PATH = pathlib.Path(__file__).resolve().parent / "excel_to_delimited.py"
excel_to_delimited = load_module("excel_to_delimited", MODULE_PATH)


def test_default_output_dir_uses_format_suffix() -> None:
    assert excel_to_delimited.default_output_dir("/tmp/report.xlsx", "csv") == "/tmp/report_csv"


def test_parse_request_defaults_to_csv() -> None:
    assert excel_to_delimited.parse_request("/tmp/report.xlsx") == ("/tmp/report.xlsx", "csv")


def test_parse_request_reads_tsv_filter() -> None:
    assert excel_to_delimited.parse_request("/tmp/report.xlsx | format:tsv") == (
        "/tmp/report.xlsx",
        "tsv",
    )


def test_build_sheet_filename_numbers_and_sanitizes_names() -> None:
    assert (
        excel_to_delimited.build_sheet_filename(2, 12, "Q1 Summary / North", "csv")
        == "02-q1-summary-north.csv"
    )


def test_write_delimited_sheets_writes_tsv(tmp_path) -> None:
    output_dir = tmp_path / "out"
    excel_to_delimited.write_delimited_sheets(
        [("Summary", [["Company", "Priority"], ["Acme", "1"]])],
        str(output_dir),
        "tsv",
    )

    rendered = (output_dir / "01-summary.tsv").read_text(encoding="utf-8")
    assert rendered == "Company\tPriority\nAcme\t1\n"


def test_main_writes_csv_files_for_xlsx(tmp_path) -> None:
    openpyxl = pytest.importorskip("openpyxl")

    workbook = openpyxl.Workbook()
    summary = workbook.active
    summary.title = "Summary"
    summary.append(["Company", "Score"])
    summary.append(["Acme", 9])
    notes = workbook.create_sheet("Notes")
    notes.append(["Topic", "Note"])
    notes.append(["Research", "Large workbook"])

    input_file = tmp_path / "research.xlsx"
    workbook.save(input_file)
    workbook.close()

    original_argv = sys.argv
    sys.argv = ["excel_to_delimited.py", str(input_file)]
    try:
        assert excel_to_delimited.main() == 0
    finally:
        sys.argv = original_argv

    output_dir = tmp_path / "research_csv"
    assert (output_dir / "01-summary.csv").read_text(encoding="utf-8") == "Company,Score\nAcme,9\n"
    assert (output_dir / "02-notes.csv").read_text(encoding="utf-8") == (
        "Topic,Note\nResearch,Large workbook\n"
    )


def test_main_honors_request_tsv_filter(tmp_path, monkeypatch) -> None:
    input_file = tmp_path / "legacy.xls"
    input_file.write_text("placeholder", encoding="utf-8")

    monkeypatch.setattr(
        excel_to_delimited,
        "read_workbook_sheets",
        lambda _: [("Legacy Sheet", [["Name", "Enabled"], ["Acme", "TRUE"]])],
    )

    original_argv = sys.argv
    sys.argv = ["excel_to_delimited.py", "--request", f"{input_file} | format:tsv"]
    try:
        assert excel_to_delimited.main() == 0
    finally:
        sys.argv = original_argv

    output_dir = tmp_path / "legacy_tsv"
    assert (output_dir / "01-legacy-sheet.tsv").read_text(encoding="utf-8") == (
        "Name\tEnabled\nAcme\tTRUE\n"
    )


def test_main_rejects_non_excel_input(tmp_path, capsys) -> None:
    input_file = tmp_path / "sample.txt"
    input_file.write_text("hello", encoding="utf-8")

    original_argv = sys.argv
    sys.argv = ["excel_to_delimited.py", str(input_file)]
    try:
        assert excel_to_delimited.main() == 2
    finally:
        sys.argv = original_argv

    captured = capsys.readouterr()
    assert "Input file must end in .xls or .xlsx" in captured.err