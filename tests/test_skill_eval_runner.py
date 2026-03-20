import importlib.util
import pathlib
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


MODULE_PATH = pathlib.Path(__file__).resolve().parents[1] / "evals" / "runner" / "skill_eval.py"
skill_eval = load_module("vscode_skill_eval", MODULE_PATH)


def test_discover_case_files_filters_by_skill() -> None:
    cases = skill_eval.discover_case_files(
        pathlib.Path(__file__).resolve().parents[1] / "evals" / "cases",
        skill="arxiv-search",
    )
    assert cases
    assert all(path.parent.name == "arxiv-search" for path in cases)


def test_evaluate_assertions_passes_for_matching_output() -> None:
    case = {
        "assertions": {
            "text_contains": ["Abstract:", "PDF:"],
            "text_not_contains": ["<feed"],
            "regex_contains": [r"Confidence:\s+high"],
            "min_nonempty_lines": 3,
        }
    }
    output = """1. Example Paper
Authors: Alice Example
Summary: Example summary
Abstract: https://arxiv.org/abs/1234.5678
PDF: https://arxiv.org/pdf/1234.5678
Confidence: high
"""
    assert skill_eval.evaluate_assertions(case, output) == []


def test_evaluate_assertions_reports_missing_and_forbidden_text() -> None:
    case = {
        "assertions": {
            "text_contains": ["Abstract:"],
            "text_not_contains": ["raw xml"],
        }
    }
    output = "Summary only\nraw xml"
    failures = skill_eval.evaluate_assertions(case, output)
    assert "missing required text: Abstract:" in failures
    assert "found forbidden text: raw xml" in failures


def test_build_summary_marks_pass_and_fail() -> None:
    case = {"id": "example", "skill": "arxiv-search"}
    passed = skill_eval.build_summary(case, "ok", [])
    failed = skill_eval.build_summary(case, "bad", ["missing required text: Abstract:"])
    assert "Result: PASS" in passed
    assert "Result: FAIL" in failed
    assert "missing required text: Abstract:" in failed


def expected_sample_output_path(case_path: pathlib.Path) -> pathlib.Path:
    repo_root = pathlib.Path(__file__).resolve().parents[1]
    return repo_root / "evals" / "sample_outputs" / case_path.parent.name / f"{case_path.stem}.txt"


def sample_output_pairs() -> list[tuple[pathlib.Path, pathlib.Path]]:
    repo_root = pathlib.Path(__file__).resolve().parents[1]
    cases_dir = repo_root / "evals" / "cases"
    pairs: list[tuple[pathlib.Path, pathlib.Path]] = []

    for case_path in sorted(cases_dir.glob("*/*.json")):
        sample_output_path = expected_sample_output_path(case_path)
        if sample_output_path.is_file():
            pairs.append((case_path, sample_output_path))

    return pairs


def test_each_case_has_matching_sample_output() -> None:
    cases_dir = pathlib.Path(__file__).resolve().parents[1] / "evals" / "cases"
    missing_outputs = [
        str(case_path.relative_to(cases_dir.parent))
        for case_path in sorted(cases_dir.glob("*/*.json"))
        if not expected_sample_output_path(case_path).is_file()
    ]

    assert missing_outputs == [], (
        "Missing sample outputs for eval cases:\n- " + "\n- ".join(missing_outputs)
    )


@pytest.mark.parametrize(("case_path", "sample_output_path"), sample_output_pairs())
def test_checked_in_sample_outputs_pass_eval_cases(
    case_path: pathlib.Path, sample_output_path: pathlib.Path
) -> None:
    case = skill_eval.load_json_file(case_path)
    output_text = sample_output_path.read_text(encoding="utf-8")
    failures = skill_eval.evaluate_assertions(case, output_text)
    assert failures == [], skill_eval.build_summary(case, output_text, failures)