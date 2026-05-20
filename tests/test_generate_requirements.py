import importlib.util
import pathlib
import sys
from types import ModuleType


def load_module(name: str, path: pathlib.Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    loader = spec.loader
    assert loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "tools" / "generate_requirements.py"
generate_requirements = load_module("generate_requirements", MODULE_PATH)


def _generated_files(root: pathlib.Path) -> dict[pathlib.Path, str]:
    return {
        path.relative_to(root): path.read_text(encoding="utf-8")
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_build_repo_python_packages_uses_registered_skills() -> None:
    skill_requirements = generate_requirements.load_skill_requirements(
        REPO_ROOT / "skills" / "install-manifest.json"
    )

    assert generate_requirements.build_repo_python_packages(skill_requirements) == [
        "faster-whisper",
        "openpyxl",
        "pypdf",
        "selenium",
        "xlrd",
        "yfinance",
    ]


def test_resolve_skill_dependency_closure_includes_transitive_dependencies() -> None:
    skill_requirements = generate_requirements.load_skill_requirements(
        REPO_ROOT / "skills" / "install-manifest.json"
    )

    closure = generate_requirements.resolve_skill_dependency_closure(
        "stock-investment-review", skill_requirements
    )

    assert closure[-1] == "stock-investment-review"
    assert "stock-research" in closure
    assert "company-research" in closure
    assert "yahoo-finance" in closure
    assert generate_requirements.collect_python_packages(closure, skill_requirements) == [
        "yfinance"
    ]


def test_excel_to_delimited_skill_requirements_include_transitive_python_packages() -> None:
    skill_requirements = generate_requirements.load_skill_requirements(
        REPO_ROOT / "skills" / "install-manifest.json"
    )

    closure = generate_requirements.resolve_skill_dependency_closure(
        "excel-to-delimited", skill_requirements
    )

    assert closure == ["excel-to-markdown", "excel-to-delimited"]
    assert generate_requirements.collect_python_packages(closure, skill_requirements) == [
        "openpyxl",
        "xlrd",
    ]


def test_write_requirements_outputs_writes_repo_and_per_skill_files(tmp_path: pathlib.Path) -> None:
    manifest_path = REPO_ROOT / "skills" / "install-manifest.json"

    generate_requirements.write_requirements_outputs(
        manifest_path=manifest_path,
        repo_root=tmp_path,
    )

    skill_requirements = (
        tmp_path / "skills" / "excel-to-delimited" / "requirements.txt"
    ).read_text(encoding="utf-8")
    tweet_requirements = (
        tmp_path / "skills" / "tweet-read" / "requirements.txt"
    ).read_text(encoding="utf-8")

    assert "Resolved skills: excel-to-markdown, excel-to-delimited" in skill_requirements
    assert "xlrd" in skill_requirements
    assert "selenium" in tweet_requirements


def test_write_requirements_outputs_skips_non_python_skills(tmp_path: pathlib.Path) -> None:
    manifest_path = REPO_ROOT / "skills" / "install-manifest.json"

    generate_requirements.write_requirements_outputs(
        manifest_path=manifest_path,
        repo_root=tmp_path,
    )

    assert not (tmp_path / "skills" / "weather" / "requirements.txt").exists()
    assert not (tmp_path / "skills" / "docx-to-markdown" / "requirements.txt").exists()


def test_checked_in_generated_requirements_are_up_to_date(tmp_path: pathlib.Path) -> None:
    manifest_path = REPO_ROOT / "skills" / "install-manifest.json"
    generated_root = tmp_path / "generated"
    generated_root.mkdir()

    generate_requirements.write_requirements_outputs(
        manifest_path=manifest_path,
        repo_root=generated_root,
    )

    expected_files = _generated_files(generated_root)
    committed_files = {
        path.relative_to(REPO_ROOT): path.read_text(encoding="utf-8")
        for path in sorted(REPO_ROOT.glob("skills/*/requirements.txt"))
    }

    assert committed_files == expected_files, (
        "Generated requirements outputs are out of date. "
        "Run `python3 tools/generate_requirements.py` and commit the changes."
    )