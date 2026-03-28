from __future__ import annotations

import re
from pathlib import Path

from nettools.findings import validate_finding_code

EMITTED_CODE_PATTERN = re.compile(r'code="([A-Z][A-Z0-9_]*)"')
DOC_CODE_PATTERN = re.compile(r"^\| `(?P<code>[A-Z][A-Z0-9_]*)` \|")

FRAMEWORK_CODES = {
    "NOT_IMPLEMENTED",
    "BAD_INPUT",
    "DEPENDENCY_TIMEOUT",
    "DEPENDENCY_UNAVAILABLE",
    "INSUFFICIENT_EVIDENCE",
    "UNSUPPORTED_PROVIDER_OPERATION",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _extract_emitted_finding_codes() -> set[str]:
    root = _repo_root()
    emitted_codes: set[str] = set()
    for relative_path in [
        "skills/nettools-core/nettools/priority1.py",
        "skills/nettools-core/nettools/priority2.py",
        "skills/nettools-core/nettools/priority3.py",
    ]:
        text = (root / relative_path).read_text(encoding="utf-8")
        emitted_codes.update(EMITTED_CODE_PATTERN.findall(text))
    emitted_codes.update(FRAMEWORK_CODES)
    return emitted_codes


def _parse_documented_codes() -> set[str]:
    doc_path = _repo_root() / "docs" / "NETTOOLS_FINDING_CODES.md"
    documented: set[str] = set()
    for line in doc_path.read_text(encoding="utf-8").splitlines():
        match = DOC_CODE_PATTERN.match(line)
        if match is None:
            continue
        documented.add(match.group("code"))
    return documented


def test_all_emitted_finding_codes_are_documented() -> None:
    emitted_codes = _extract_emitted_finding_codes()
    documented_codes = _parse_documented_codes()

    assert emitted_codes == documented_codes
    assert all(validate_finding_code(code) == code for code in documented_codes)


def test_finding_code_documentation_includes_registry_context() -> None:
    doc_text = (_repo_root() / "docs" / "NETTOOLS_FINDING_CODES.md").read_text(
        encoding="utf-8"
    )

    assert "Severity semantics:" in doc_text
    assert "| Code | Default Severity | Producer Skills | Summary |" in doc_text