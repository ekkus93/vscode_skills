"""Finding-code support for NETTOOLS shared support code."""

from .registry import (
    BAD_INPUT,
    DEPENDENCY_TIMEOUT,
    DEPENDENCY_UNAVAILABLE,
    FINDING_CODE_PATTERN,
    INSUFFICIENT_EVIDENCE,
    NOT_IMPLEMENTED,
    UNSUPPORTED_PROVIDER_OPERATION,
    validate_finding_code,
)

__all__ = [
    "BAD_INPUT",
    "DEPENDENCY_TIMEOUT",
    "DEPENDENCY_UNAVAILABLE",
    "FINDING_CODE_PATTERN",
    "INSUFFICIENT_EVIDENCE",
    "NOT_IMPLEMENTED",
    "UNSUPPORTED_PROVIDER_OPERATION",
    "validate_finding_code",
]
