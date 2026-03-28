from __future__ import annotations

from datetime import datetime, timezone

from nettools.models import (
    Confidence,
    Finding,
    FindingSeverity,
    NextAction,
    ScopeType,
    SkillResult,
    Status,
    TimeWindow,
)


def test_skill_result_serializes_to_expected_contract_shape() -> None:
    result = SkillResult(
        status=Status.WARN,
        skill_name="net.client_health",
        scope_type=ScopeType.CLIENT,
        scope_id="client-123",
        summary="Client shows elevated retry rate.",
        confidence=Confidence.MEDIUM,
        observed_at=datetime(2026, 3, 28, 7, 0, tzinfo=timezone.utc),
        time_window=TimeWindow(
            start=datetime(2026, 3, 28, 6, 45, tzinfo=timezone.utc),
            end=datetime(2026, 3, 28, 7, 0, tzinfo=timezone.utc),
        ),
        evidence={"retry_pct": 24.2},
        findings=[
            Finding(
                code="HIGH_RETRY_RATE",
                severity=FindingSeverity.WARN,
                message="Client retry rate exceeded threshold.",
                metric="retry_pct",
                value=24.2,
                threshold=15.0,
            )
        ],
        next_actions=[
            NextAction(
                skill="net.ap_rf_health",
                reason="Validate the AP and channel serving the affected client.",
            )
        ],
        raw_refs=["controller:client/123"],
    )

    payload = result.model_dump(mode="json")

    assert payload["status"] == "warn"
    assert payload["scope_type"] == "client"
    assert payload["confidence"] == "medium"
    assert payload["time_window"]["start"] == "2026-03-28T06:45:00Z"
    assert payload["findings"][0]["code"] == "HIGH_RETRY_RATE"
    assert payload["next_actions"][0]["skill"] == "net.ap_rf_health"


def test_time_window_rejects_inverted_bounds() -> None:
    start = datetime(2026, 3, 28, 7, 0, tzinfo=timezone.utc)
    end = datetime(2026, 3, 28, 6, 45, tzinfo=timezone.utc)

    try:
        TimeWindow(start=start, end=end)
    except ValueError as exc:
        assert "earlier than or equal to end" in str(exc)
    else:
        raise AssertionError("Expected inverted time window validation failure")
