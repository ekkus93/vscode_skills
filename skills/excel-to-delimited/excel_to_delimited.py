import argparse
import csv
import importlib.util
import os
import re
import sys
from collections.abc import Callable
from typing import cast

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def load_read_workbook_sheets() -> Callable[[str], list[tuple[str, list[list[str]]]]]:
    module_path = os.path.join(SCRIPT_DIR, "..", "excel-to-markdown", "excel_to_markdown.py")
    spec = importlib.util.spec_from_file_location("excel_to_markdown", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load excel_to_markdown helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return cast(Callable[[str], list[tuple[str, list[list[str]]]]], module.read_workbook_sheets)


read_workbook_sheets = load_read_workbook_sheets()


def default_output_dir(input_file: str, output_format: str) -> str:
    base, _ = os.path.splitext(input_file)
    return base + f"_{output_format}"


def parse_request(request: str) -> tuple[str, str]:
    parts = [part.strip() for part in request.split("|")]
    if not parts or not parts[0]:
        raise RuntimeError("Request must start with a local .xls or .xlsx file path")

    input_file = parts[0]
    output_format = "csv"
    for part in parts[1:]:
        if not part:
            continue
        key, separator, value = part.partition(":")
        if separator != ":":
            raise RuntimeError(f"Unsupported filter: {part}")
        normalized_key = key.strip().lower()
        normalized_value = value.strip().lower()
        if normalized_key != "format":
            raise RuntimeError(f"Unsupported filter: {part}")
        if normalized_value not in {"csv", "tsv"}:
            raise RuntimeError("format must be csv or tsv")
        output_format = normalized_value
    return input_file, output_format


def sanitize_sheet_name(sheet_name: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", sheet_name.strip().lower()).strip("-._")
    return normalized or "sheet"


def build_sheet_filename(index: int, total_sheets: int, sheet_name: str, output_format: str) -> str:
    width = max(2, len(str(total_sheets)))
    prefix = str(index).zfill(width)
    return f"{prefix}-{sanitize_sheet_name(sheet_name)}.{output_format}"


def delimiter_for_format(output_format: str) -> str:
    if output_format == "csv":
        return ","
    if output_format == "tsv":
        return "\t"
    raise RuntimeError("format must be csv or tsv")


def write_delimited_sheets(
    sheets: list[tuple[str, list[list[str]]]], output_dir: str, output_format: str
) -> None:
    delimiter = delimiter_for_format(output_format)
    os.makedirs(output_dir, exist_ok=True)
    total_sheets = len(sheets)
    for index, (sheet_name, rows) in enumerate(sheets, start=1):
        output_path = os.path.join(
            output_dir,
            build_sheet_filename(index, total_sheets, sheet_name, output_format),
        )
        with open(output_path, "w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, delimiter=delimiter, lineterminator="\n")
            for row in rows:
                writer.writerow(row)


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert Excel workbooks to CSV or TSV files")
    parser.add_argument("input_file", nargs="?")
    parser.add_argument("output_dir", nargs="?")
    parser.add_argument("--format", choices=["csv", "tsv"], default="csv")
    parser.add_argument("--request")
    args = parser.parse_args()

    try:
        if args.request:
            input_file_value, output_format = parse_request(args.request)
        else:
            if not args.input_file:
                raise RuntimeError("Missing input file path")
            input_file_value = args.input_file
            output_format = args.format

        input_file = os.path.abspath(input_file_value)
        output_dir = (
            os.path.abspath(args.output_dir)
            if args.output_dir
            else default_output_dir(input_file, output_format)
        )

        if not os.path.isfile(input_file):
            print(f"Input file not found: {input_file}", file=sys.stderr)
            return 2

        if not input_file.lower().endswith((".xls", ".xlsx")):
            print("Input file must end in .xls or .xlsx", file=sys.stderr)
            return 2

        sheets = read_workbook_sheets(input_file)
        write_delimited_sheets(sheets, output_dir, output_format)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if not os.path.isdir(output_dir):
        print("Delimited output directory was not created", file=sys.stderr)
        return 1

    print(output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())