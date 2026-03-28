from __future__ import annotations

from datetime import datetime, timezone

from nettools.errors import BadInputError, DependencyTimeoutError, error_to_skill_result
from nettools.findings import validate_finding_code
from nettools.models import ScopeType, Status, TimeWindow


def test_validate_finding_code_accepts_upper_snake_case() -> None:
    assert validate_finding_code("HIGH_RETRY_RATE") == "HIGH_RETRY_RATE"


def test_validate_finding_code_rejects_invalid_format() -> None:
    try:
        validate_finding_code("highRetryRate")
    except ValueError as exc:
        assert "uppercase snake case" in str(exc)
    else:
        raise AssertionError("Expected finding-code validation failure")


def test_error_to_skill_result_maps_bad_input_to_fail() -> None:
    result = error_to_skill_result(
        error=BadInputError("Missing client identifier."),
        skill_name="net.client_health",
        scope_type=ScopeType.CLIENT,
        scope_id="unscoped",
        time_window=TimeWindow(
            start=datetime(2026, 3, 28, 6, 45, tzinfo=timezone.utc),
            end=datetime(2026, 3, 28, 7, 0, tzinfo=timezone.utc),
        ),
    )

    assert result.status == Status.FAIL
    assert result.findings[0].code == "BAD_INPUT"


def test_error_to_skill_result_maps_dependency_timeout_to_unknown() -> None:
    result = error_to_skill_result(
        error=DependencyTimeoutError("Switch adapter timed out during port lookup."),
        skill_name="net.ap_uplink_health",
        scope_type=ScopeType.SWITCH_PORT,
        scope_id="Gi1/0/18",
        time_window=TimeWindow(
            start=datetime(2026, 3, 28, 6, 45, tzinfo=timezone.utc),
            end=datetime(2026, 3, 28, 7, 0, tzinfo=timezone.utc),
        ),
        observed_at=datetime(2026, 3, 28, 7, 0, tzinfo=timezone.utc),
    )

    assert result.status == Status.UNKNOWN
    assert result.findings[0].code == "DEPENDENCY_TIMEOUT"
    assert result.observed_at == datetime(2026, 3, 28, 7, 0, tzinfo=timezone.utc)
