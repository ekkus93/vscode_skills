from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest
from nettools.models import (
    Confidence,
    NextAction,
    ScopeType,
    SkillResult,
    Status,
    TimeWindow,
)
from nettools.orchestrator import (
    DEFAULT_PLAYBOOKS,
    DiagnoseIncidentReport,
    DiagnosticDomain,
    DomainScore,
    IncidentState,
    IncidentType,
    InvestigationStatus,
    PlaybookDefinition,
    RankedCause,
    SkillExecutionRecord,
    StopReason,
    StopReasonCode,
    get_playbook_definition,
)
from pydantic import ValidationError


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _record(
    skill_name: str,
    *,
    incident_record: dict[str, Any] | None = None,
) -> SkillExecutionRecord:
    observed_at = _now()
    result = SkillResult(
        status=Status.OK,
        skill_name=skill_name,
        scope_type=ScopeType.SERVICE,
        scope_id="scope-1",
        summary=f"{skill_name} ok",
        confidence=Confidence.MEDIUM,
        observed_at=observed_at,
        time_window=TimeWindow(start=observed_at, end=observed_at),
        evidence={"incident_record": incident_record} if incident_record is not None else {},
        findings=[],
        next_actions=[NextAction(skill="net.incident_correlation", reason="follow-up")],
        raw_refs=[],
    )
    return SkillExecutionRecord(
        invocation_id=f"inv-{skill_name}",
        skill_name=skill_name,
        started_at=observed_at,
        finished_at=observed_at,
        duration_ms=1,
        input_summary={},
        result=result,
    )


def test_domain_score_derives_confidence_from_score() -> None:
    low_score = DomainScore(domain=DiagnosticDomain.UNKNOWN, score=0.2)
    medium_score = DomainScore(domain=DiagnosticDomain.DNS_ISSUE, score=0.6)
    high_score = DomainScore(domain=DiagnosticDomain.AUTH_ISSUE, score=0.9)

    assert low_score.confidence == Confidence.LOW
    assert medium_score.confidence == Confidence.MEDIUM
    assert high_score.confidence == Confidence.HIGH


def test_incident_state_appends_execution_and_dependency_failure() -> None:
    state = IncidentState(
        incident_id="inc-1",
        incident_type=IncidentType.SINGLE_CLIENT,
        playbook_used="single_client_wifi_issue",
    )
    failed_record = SkillExecutionRecord(
        invocation_id="inv-1",
        skill_name="net.dns_latency",
        started_at=_now(),
        finished_at=_now(),
        duration_ms=5,
        input_summary={"site_id": "hq-1"},
        result=_record("net.dns_latency").result.model_copy(
            update={
                "status": Status.FAIL,
                "summary": "Dependency timed out",
            }
        ),
        error_type="DependencyTimeoutError",
    )

    state.append_execution(failed_record)

    assert state.skill_trace[0].skill_name == "net.dns_latency"
    assert state.skill_trace[0].raw_result is None
    assert state.evidence_log[0].summary == "Dependency timed out"
    assert state.dependency_failures[0].error_type == "DependencyTimeoutError"


def test_incident_state_tracks_domains_and_report() -> None:
    state = IncidentState(incident_id="inc-2")

    state.set_domain_score(
        DiagnosticDomain.DNS_ISSUE,
        score=0.82,
        supporting_findings=["DNS_TIMEOUTS"],
    )
    state.eliminate_domain(DiagnosticDomain.UNKNOWN)
    state.recommend_next("net.dns_latency")
    state.status = InvestigationStatus.COMPLETED
    state.set_stop_reason(
        StopReason(
            code=StopReasonCode.HIGH_CONFIDENCE_DIAGNOSIS,
            message="DNS evidence is sufficient to stop.",
            related_domains=[DiagnosticDomain.DNS_ISSUE],
        )
    )
    report = state.build_report(
        summary="Likely DNS incident.",
        top_causes=[
            RankedCause(
                domain=DiagnosticDomain.DNS_ISSUE,
                score=0.82,
                confidence=Confidence.HIGH,
                rationale="Multiple DNS findings point to resolver latency.",
                supporting_findings=["DNS_TIMEOUTS"],
            )
        ],
    )

    assert DiagnosticDomain.DNS_ISSUE in state.suspected_domains
    assert DiagnosticDomain.UNKNOWN in state.eliminated_domains
    assert report.recommended_next_skill == "net.dns_latency"
    assert report.stop_reason is not None
    assert report.top_causes[0].domain == DiagnosticDomain.DNS_ISSUE


def test_incident_state_rejects_overlapping_domain_sets() -> None:
    with pytest.raises(ValidationError, match="must be disjoint"):
        IncidentState(
            incident_id="inc-3",
            suspected_domains=[DiagnosticDomain.DNS_ISSUE],
            eliminated_domains=[DiagnosticDomain.DNS_ISSUE],
        )


def test_incident_state_serializes_expected_shape() -> None:
    state = IncidentState(
        incident_id="inc-4",
        playbook_used="single_client_wifi_issue",
    )
    record = _record("net.client_health")
    state.append_execution(
        SkillExecutionRecord(
            invocation_id=record.invocation_id,
            skill_name=record.skill_name,
            started_at=record.started_at,
            finished_at=record.finished_at,
            duration_ms=record.duration_ms,
            input_summary=record.input_summary,
            result=record.result,
            raw_result={"skill_name": "net.client_health", "status": "ok"},
            error_type=record.error_type,
        )
    )
    payload = state.model_dump(mode="json")

    assert payload["incident_id"] == "inc-4"
    assert payload["skill_trace"][0]["skill_name"] == "net.client_health"
    assert payload["skill_trace"][0]["raw_result"]["skill_name"] == "net.client_health"
    assert payload["evidence_log"][0]["status"] == "ok"


def test_diagnose_incident_report_formats_ranked_causes() -> None:
    state = IncidentState(
        incident_id="inc-report-ranked",
        incident_type=IncidentType.SINGLE_CLIENT,
        playbook_used="single_client_wifi_issue",
    )
    ranked_causes = [
        RankedCause(
            domain=DiagnosticDomain.DNS_ISSUE,
            score=0.82,
            confidence=Confidence.HIGH,
            rationale="dns_issue is supported by HIGH_DNS_LATENCY, DNS_TIMEOUT_RATE.",
            supporting_findings=["HIGH_DNS_LATENCY", "DNS_TIMEOUT_RATE"],
        ),
        RankedCause(
            domain=DiagnosticDomain.AUTH_ISSUE,
            score=0.41,
            confidence=Confidence.MEDIUM,
            rationale="auth_issue remains weakly plausible despite contradicting signals.",
            supporting_findings=["AUTH_TIMEOUTS"],
        ),
    ]

    report = DiagnoseIncidentReport.from_incident_state(
        state,
        result_status=Status.WARN,
        summary="Investigation narrowed the issue to dns_issue with high confidence.",
        ranked_causes=ranked_causes,
        recommended_human_actions=["Check DNS resolver latency for client client-42."],
    )
    payload = report.model_dump(mode="json")

    assert payload["ranked_causes"][0] == {
        "domain": "dns_issue",
        "score": 0.82,
        "confidence": "high",
        "rationale": "dns_issue is supported by HIGH_DNS_LATENCY, DNS_TIMEOUT_RATE.",
        "supporting_findings": ["HIGH_DNS_LATENCY", "DNS_TIMEOUT_RATE"],
    }
    assert payload["ranked_causes"][1]["domain"] == "auth_issue"
    assert payload["confidence"] == "high"


def test_diagnose_incident_report_formats_eliminated_domains() -> None:
    state = IncidentState(
        incident_id="inc-report-eliminated",
        incident_type=IncidentType.SITE_WIDE,
        playbook_used="site_wide_internal_slowdown",
    )
    state.eliminate_domain(DiagnosticDomain.ROAMING_ISSUE)
    state.eliminate_domain(DiagnosticDomain.UNKNOWN)

    report = DiagnoseIncidentReport.from_incident_state(
        state,
        result_status=Status.UNKNOWN,
        summary="Investigation completed without a strong automated diagnosis.",
        ranked_causes=[],
        recommended_human_actions=["Pause automation and gather new external evidence."],
    )
    payload = report.model_dump(mode="json")

    assert payload["eliminated_domains"] == ["roaming_issue", "unknown"]
    assert payload["ranked_causes"] == []


def test_default_playbooks_load_from_registry() -> None:
    playbook = get_playbook_definition("site_wide_internal_slowdown")

    assert playbook is not None
    assert playbook.name == "site_wide_internal_slowdown"
    assert playbook.default_sequence[:3] == [
        "net.incident_intake",
        "net.change_detection",
        "net.path_probe",
    ]
    assert IncidentType.SITE_WIDE in playbook.incident_types
    assert DEFAULT_PLAYBOOKS[playbook.name] is playbook


def test_playbook_definition_rejects_unknown_skill() -> None:
    with pytest.raises(ValidationError, match="unknown skills"):
        PlaybookDefinition(
            name="broken",
            incident_types=[IncidentType.UNKNOWN_SCOPE],
            default_sequence=["net.incident_intake", "net.not_real"],
        )


def test_playbook_definition_requires_required_skills_in_sequence() -> None:
    with pytest.raises(ValidationError, match="required_skills must be included"):
        PlaybookDefinition(
            name="broken-required",
            incident_types=[IncidentType.UNKNOWN_SCOPE],
            default_sequence=["net.incident_intake"],
            required_skills=["net.client_health"],
        )