import importlib.util
import pathlib
import sys
import types
from types import ModuleType
from typing import Any

import pytest


def load_module(name: str, path: pathlib.Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    loader = spec.loader
    assert loader is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def pytest_import_openpyxl() -> Any:
    return pytest.importorskip("openpyxl")


MODULE_PATH = pathlib.Path(__file__).resolve().parent / "excel_to_markdown.py"
excel_to_markdown = load_module("excel_to_markdown", MODULE_PATH)


def test_default_output_path_uses_md_extension() -> None:
    assert excel_to_markdown.default_output_path("/tmp/report.xlsx") == "/tmp/report.md"


def test_sheet_to_markdown_uses_first_row_as_header_when_multiple_rows() -> None:
    markdown = excel_to_markdown.sheet_to_markdown(
        [["Region", "Revenue"], ["North", "10"], ["South", "12"]]
    )
    assert "| Region | Revenue |" in markdown
    assert "| North | 10 |" in markdown


def test_sheet_to_markdown_uses_generic_headers_for_single_row() -> None:
    markdown = excel_to_markdown.sheet_to_markdown([["only", "row"]])
    assert "| Column 1 | Column 2 |" in markdown
    assert "| only | row |" in markdown


def test_sheet_to_markdown_marks_empty_sheet() -> None:
    assert excel_to_markdown.sheet_to_markdown([["", ""], []]) == "_Empty sheet._"


def test_workbook_to_markdown_includes_all_sheet_sections() -> None:
    markdown = excel_to_markdown.workbook_to_markdown(
        "Quarterly Results",
        [("Summary", [["Metric", "Value"], ["ARR", "100"]]), ("Empty", [])],
    )
    assert markdown.startswith("# Quarterly Results\n")
    assert "## Summary" in markdown
    assert "## Empty" in markdown
    assert "_Empty sheet._" in markdown


def test_load_xls_sheets_reads_legacy_workbook(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeCell:
        def __init__(self, ctype: int, value: object) -> None:
            self.ctype = ctype
            self.value = value

    class FakeSheet:
        name = "Legacy"
        nrows = 2
        ncols = 2

        def cell(self, row_index: int, column_index: int) -> FakeCell:
            values = {
                (0, 0): FakeCell(1, "Name"),
                (0, 1): FakeCell(1, "Enabled"),
                (1, 0): FakeCell(1, "Acme"),
                (1, 1): FakeCell(4, 1),
            }
            return values[(row_index, column_index)]

    class FakeWorkbook:
        datemode = 0

        def sheets(self) -> list[FakeSheet]:
            return [FakeSheet()]

    fake_xlrd = types.SimpleNamespace(
        XL_CELL_DATE=3,
        XL_CELL_BOOLEAN=4,
        open_workbook=lambda _: FakeWorkbook(),
        xldate_as_datetime=lambda value, datemode: value,
    )
    monkeypatch.setitem(sys.modules, "xlrd", fake_xlrd)

    sheets = excel_to_markdown.load_xls_sheets("/tmp/legacy.xls")

    assert sheets == [("Legacy", [["Name", "Enabled"], ["Acme", "TRUE"]])]


def test_main_writes_markdown_file_for_xlsx(tmp_path: pathlib.Path) -> None:
    openpyxl = pytest_import_openpyxl()

    workbook = openpyxl.Workbook()
    summary = workbook.active
    summary.title = "Summary"
    summary.append(["Company", "Score"])
    summary.append(["Acme", 9])
    detail = workbook.create_sheet("Detail")
    detail.append(["Status"])
    detail.append(["Ready"])

    input_file = tmp_path / "research.xlsx"
    workbook.save(input_file)
    workbook.close()

    original_argv = sys.argv
    sys.argv = ["excel_to_markdown.py", str(input_file)]
    try:
        assert excel_to_markdown.main() == 0
    finally:
        sys.argv = original_argv

    output_file = tmp_path / "research.md"
    rendered = output_file.read_text(encoding="utf-8")
    assert "# research" in rendered
    assert "## Summary" in rendered
    assert "| Company | Score |" in rendered
    assert "| Acme | 9 |" in rendered
    assert "## Detail" in rendered


def test_main_rejects_non_excel_input(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    input_file = tmp_path / "sample.txt"
    input_file.write_text("hello", encoding="utf-8")

    original_argv = sys.argv
    sys.argv = ["excel_to_markdown.py", str(input_file)]
    try:
        assert excel_to_markdown.main() == 2
    finally:
        sys.argv = original_argv

    captured = capsys.readouterr()
    assert "Input file must end in .xls or .xlsx" in captured.err