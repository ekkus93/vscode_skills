import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

JsonDict = dict[str, Any]

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CASES_DIR = REPO_ROOT / "evals" / "cases"


def load_json_file(path: Path) -> JsonDict:
    return json.loads(path.read_text(encoding="utf-8"))


def discover_case_files(cases_dir: Path, skill: str | None = None) -> list[Path]:
    pattern = "*.json" if skill is None else f"{skill}/*.json"
    return sorted(cases_dir.glob(pattern))


def evaluate_assertions(case: JsonDict, output_text: str) -> list[str]:
    assertions = case.get("assertions", {})
    failures: list[str] = []
    lowered_output = output_text.lower()

    for needle in assertions.get("text_contains", []):
        if str(needle).lower() not in lowered_output:
            failures.append(f"missing required text: {needle}")

    for needle in assertions.get("text_not_contains", []):
        if str(needle).lower() in lowered_output:
            failures.append(f"found forbidden text: {needle}")

    for pattern in assertions.get("regex_contains", []):
        if re.search(str(pattern), output_text, flags=re.MULTILINE) is None:
            failures.append(f"missing required regex match: {pattern}")

    for pattern in assertions.get("regex_not_contains", []):
        if re.search(str(pattern), output_text, flags=re.MULTILINE) is not None:
            failures.append(f"found forbidden regex match: {pattern}")

    min_lines = assertions.get("min_nonempty_lines")
    if isinstance(min_lines, int):
        nonempty_line_count = len([line for line in output_text.splitlines() if line.strip()])
        if nonempty_line_count < min_lines:
            failures.append(
                f"expected at least {min_lines} non-empty lines, got {nonempty_line_count}"
            )

    return failures


def build_summary(case: JsonDict, output_text: str, failures: list[str]) -> str:
    lines = [f"Case: {case.get('id', '<unknown>')}", f"Skill: {case.get('skill', '<unknown>')}"]
    if failures:
        lines.append("Result: FAIL")
        lines.append("")
        lines.append("Failures:")
        for failure in failures:
            lines.append(f"- {failure}")
    else:
        lines.append("Result: PASS")

    lines.append("")
    lines.append("Output:")
    lines.append(output_text.rstrip())
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate captured Copilot skill output")
    parser.add_argument("--case", required=True, help="Path to the eval case JSON file")
    parser.add_argument(
        "--output-file",
        help="Path to a text file containing the captured assistant output",
    )
    parser.add_argument(
        "--output-text",
        help="Captured assistant output passed directly on the command line",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    case = load_json_file(Path(args.case))

    sources = [value for value in [args.output_file, args.output_text] if value]
    if len(sources) != 1:
        print("Provide exactly one of --output-file or --output-text", file=sys.stderr)
        return 2

    if args.output_file:
        output_text = Path(args.output_file).read_text(encoding="utf-8")
    else:
        output_text = str(args.output_text)

    failures = evaluate_assertions(case, output_text)
    sys.stdout.write(build_summary(case, output_text, failures))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())