from __future__ import annotations

import re

FINDING_CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")

NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
BAD_INPUT = "BAD_INPUT"
DEPENDENCY_TIMEOUT = "DEPENDENCY_TIMEOUT"
DEPENDENCY_UNAVAILABLE = "DEPENDENCY_UNAVAILABLE"
INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
UNSUPPORTED_PROVIDER_OPERATION = "UNSUPPORTED_PROVIDER_OPERATION"


def validate_finding_code(code: str) -> str:
    if not FINDING_CODE_PATTERN.fullmatch(code):
        raise ValueError("Finding codes must be uppercase snake case, for example HIGH_RETRY_RATE")
    return code
