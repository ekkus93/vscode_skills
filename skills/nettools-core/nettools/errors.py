from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .findings import (
    BAD_INPUT,
    DEPENDENCY_TIMEOUT,
    DEPENDENCY_UNAVAILABLE,
    INSUFFICIENT_EVIDENCE,
    UNSUPPORTED_PROVIDER_OPERATION,
)
from .models import Confidence, Finding, FindingSeverity, ScopeType, SkillResult, Status, TimeWindow


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


class NettoolsError(Exception):
    finding_code = INSUFFICIENT_EVIDENCE
    finding_severity = FindingSeverity.WARN
    result_status = Status.UNKNOWN

    def __init__(self, message: str, *, raw_refs: list[Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.raw_refs = raw_refs or []


class BadInputError(NettoolsError):
    finding_code = BAD_INPUT
    finding_severity = FindingSeverity.WARN
    result_status = Status.FAIL


class DependencyTimeoutError(NettoolsError):
    finding_code = DEPENDENCY_TIMEOUT
    finding_severity = FindingSeverity.WARN
    result_status = Status.UNKNOWN


class DependencyUnavailableError(NettoolsError):
    finding_code = DEPENDENCY_UNAVAILABLE
    finding_severity = FindingSeverity.WARN
    result_status = Status.UNKNOWN


class InsufficientEvidenceError(NettoolsError):
    finding_code = INSUFFICIENT_EVIDENCE
    finding_severity = FindingSeverity.WARN
    result_status = Status.UNKNOWN


class UnsupportedProviderOperationError(NettoolsError):
    finding_code = UNSUPPORTED_PROVIDER_OPERATION
    finding_severity = FindingSeverity.WARN
    result_status = Status.FAIL


def error_to_skill_result(
    *,
    error: NettoolsError,
    skill_name: str,
    scope_type: ScopeType,
    scope_id: str,
    time_window: TimeWindow,
    observed_at: datetime | None = None,
    raw_refs: list[Any] | None = None,
) -> SkillResult:
    observed = observed_at or utc_now()
    combined_raw_refs = [*error.raw_refs, *(raw_refs or [])]
    return SkillResult(
        status=error.result_status,
        skill_name=skill_name,
        scope_type=scope_type,
        scope_id=scope_id,
        summary=error.message,
        confidence=Confidence.LOW,
        observed_at=observed,
        time_window=time_window,
        evidence={},
        findings=[
            Finding(
                code=error.finding_code,
                severity=error.finding_severity,
                message=error.message,
            )
        ],
        next_actions=[],
        raw_refs=combined_raw_refs,
    )
