from __future__ import annotations

from datetime import datetime, timedelta, timezone

from nettools.models import Confidence
from nettools.orchestrator import (
    DependencyFailure,
    DiagnosticDomain,
    IncidentState,
    InvestigationStatus,
    StopReasonCode,
    evaluate_stop_conditions,
)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def test_high_confidence_stop() -> None:
    state = IncidentState(
        incident_id="inc-stop-1",
        playbook_used="single_client_wifi_issue",
    )
    state.set_domain_score(
        DiagnosticDomain.DNS_ISSUE,
        score=0.82,
        confidence=Confidence.HIGH,
        supporting_findings=["HIGH_DNS_LATENCY", "DNS_TIMEOUT_RATE"],
    )

    decision = evaluate_stop_conditions(state)

    assert decision.should_stop is True
    assert decision.stop_reason is not None
    assert decision.stop_reason.code is StopReasonCode.HIGH_CONFIDENCE_DIAGNOSIS
    assert state.status is InvestigationStatus.COMPLETED


def test_ambiguity_stop() -> None:
    state = IncidentState(
        incident_id="inc-stop-2",
        playbook_used="single_client_wifi_issue",
    )
    state.set_domain_score(
        DiagnosticDomain.DNS_ISSUE,
        score=0.58,
        confidence=Confidence.MEDIUM,
        supporting_findings=["HIGH_DNS_LATENCY"],
    )
    state.set_domain_score(
        DiagnosticDomain.DHCP_ISSUE,
        score=0.53,
        confidence=Confidence.MEDIUM,
        supporting_findings=["HIGH_DHCP_OFFER_LATENCY"],
    )

    decision = evaluate_stop_conditions(state)

    assert decision.should_stop is True
    assert decision.stop_reason is not None
    assert decision.stop_reason.code is StopReasonCode.TWO_DOMAIN_BOUNDED_AMBIGUITY
    assert decision.stop_reason.uncertainty_summary is not None


def test_budget_stop() -> None:
    created_at = _now() - timedelta(minutes=10)
    state = IncidentState(
        incident_id="inc-stop-3",
        playbook_used="single_client_wifi_issue",
        created_at=created_at,
        updated_at=created_at,
    )

    decision = evaluate_stop_conditions(state, now=_now())

    assert decision.should_stop is True
    assert decision.stop_reason is not None
    assert decision.stop_reason.code is StopReasonCode.INVESTIGATION_BUDGET_EXHAUSTED


def test_dependency_block_stop() -> None:
    state = IncidentState(
        incident_id="inc-stop-4",
        playbook_used="site_wide_internal_slowdown",
        dependency_failures=[
            DependencyFailure(
                skill_name="net.path_probe",
                error_type="DependencyUnavailableError",
                summary="probe adapter unavailable",
                recorded_at=_now(),
            )
        ],
    )

    decision = evaluate_stop_conditions(state)

    assert decision.should_stop is True
    assert decision.stop_reason is not None
    assert decision.stop_reason.code is StopReasonCode.DEPENDENCY_BLOCKED
    assert state.status is InvestigationStatus.BLOCKED


def test_no_progress_stop() -> None:
    state = IncidentState(
        incident_id="inc-stop-5",
        playbook_used="single_client_wifi_issue",
    )
    state.set_domain_score(
        DiagnosticDomain.DNS_ISSUE,
        score=0.41,
        confidence=Confidence.MEDIUM,
        supporting_findings=["HIGH_DNS_LATENCY"],
    )

    decision = evaluate_stop_conditions(
        state,
        previous_score_snapshots=[
            {DiagnosticDomain.DNS_ISSUE: 0.40},
            {DiagnosticDomain.DNS_ISSUE: 0.39},
        ],
    )

    assert decision.should_stop is True
    assert decision.stop_reason is not None
    assert decision.stop_reason.code is StopReasonCode.NO_NEW_INFORMATION
    assert decision.stop_reason.recommended_human_actions