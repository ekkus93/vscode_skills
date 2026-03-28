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
    BranchRule,
    ConfidenceThresholds,
    DiagnoseIncidentAuditTrail,
    DiagnoseIncidentReport,
    DiagnosticDomain,
    DomainScore,
    HypothesisScoringConfig,
    IncidentState,
    IncidentType,
    InvestigationBudgetConfig,
    InvestigationMetricsSummary,
    InvestigationStatus,
    InvestigationTraceEventType,
    OrchestratorConfig,
    PlaybookDefinition,
    PolicyControlConfig,
    RankedCause,
    SamplingDefaultsConfig,
    SkillExecutionRecord,
    StopReason,
    StopReasonCode,
    StopThresholdConfig,
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


def test_incident_state_serializes_investigation_trace() -> None:
    state = IncidentState(incident_id="inc-trace-1")

    state.append_trace(
        InvestigationTraceEventType.PLAYBOOK_SELECTION,
        "Selected playbook single_client_wifi_issue for single_client.",
        details={
            "incident_type": "single_client",
            "playbook_name": "single_client_wifi_issue",
        },
    )

    payload = state.model_dump(mode="json")

    assert payload["investigation_trace"] == [
        {
            "event_type": "playbook_selection",
            "recorded_at": payload["investigation_trace"][0]["recorded_at"],
            "message": "Selected playbook single_client_wifi_issue for single_client.",
            "details": {
                "incident_type": "single_client",
                "playbook_name": "single_client_wifi_issue",
            },
        }
    ]


def test_audit_trail_serializes_state_trace_and_execution_records() -> None:
    state = IncidentState(
        incident_id="inc-audit-1",
        incident_type=IncidentType.SINGLE_CLIENT,
        playbook_used="single_client_wifi_issue",
    )
    state.append_execution(_record("net.client_health"))
    state.append_trace(
        InvestigationTraceEventType.PLAYBOOK_SELECTION,
        "Selected playbook single_client_wifi_issue for single_client.",
        details={"playbook_name": "single_client_wifi_issue"},
    )

    audit_trail = DiagnoseIncidentAuditTrail.from_incident_state(
        state,
        incident_record={"incident_id": "inc-audit-1", "summary": "Audit me"},
    )
    payload = audit_trail.model_dump(mode="json")

    assert payload["incident_id"] == "inc-audit-1"
    assert payload["incident_record"]["summary"] == "Audit me"
    assert payload["execution_records"][0]["skill_name"] == "net.client_health"
    assert payload["investigation_trace"][0]["event_type"] == "playbook_selection"
    assert payload["metrics_summary"]["playbook_invocations"] == {
        "single_client_wifi_issue": 1,
    }
    assert audit_trail.replay_state().incident_id == state.incident_id


def test_investigation_metrics_summary_formats_counts() -> None:
    state = IncidentState(
        incident_id="inc-metrics-1",
        incident_type=IncidentType.SINGLE_CLIENT,
        playbook_used="single_client_wifi_issue",
    )
    state.append_execution(_record("net.client_health"))
    state.append_execution(_record("net.dns_latency"))
    state.set_stop_reason(
        StopReason(
            code=StopReasonCode.HIGH_CONFIDENCE_DIAGNOSIS,
            message="DNS evidence is sufficient to stop.",
            related_domains=[DiagnosticDomain.DNS_ISSUE],
        )
    )

    metrics = InvestigationMetricsSummary.from_incident_state(
        state,
        result_status=Status.WARN,
        ranked_causes=[
            RankedCause(
                domain=DiagnosticDomain.DNS_ISSUE,
                score=0.82,
                confidence=Confidence.HIGH,
                rationale="dns_issue is supported by HIGH_DNS_LATENCY.",
                supporting_findings=["HIGH_DNS_LATENCY"],
            )
        ],
    )
    payload = metrics.model_dump(mode="json")

    assert payload == {
        "playbook_invocations": {"single_client_wifi_issue": 1},
        "stop_reason_counts": {"high_confidence_diagnosis": 1},
        "diagnosis_domains_by_outcome": {"warn": {"dns_issue": 1}},
        "average_skill_count_per_investigation": 2.0,
    }


def test_orchestrator_config_resolves_runtime_overrides() -> None:
    config = OrchestratorConfig(
        playbook_mapping={IncidentType.SINGLE_CLIENT: "auth_or_onboarding_issue"},
        branch_rules={
            "net.client_health": [
                BranchRule(
                    source_skill="net.client_health",
                    triggering_findings=["LOW_RSSI"],
                    candidate_next_skills=["net.path_probe"],
                    branch_priority=7,
                )
            ]
        },
        stop_thresholds=StopThresholdConfig(
            high_confidence_threshold=0.91,
            ambiguity_gap=0.05,
            ambiguity_min_score=0.51,
            no_new_information_delta=0.02,
            no_new_information_window=3,
        ),
        domain_score_thresholds=HypothesisScoringConfig(
            suspected_threshold=0.25,
            confidence_thresholds=ConfidenceThresholds(
                medium_min=0.35,
                high_min=0.8,
            ),
        ),
        investigation_budgets=InvestigationBudgetConfig(
            max_skill_invocations=3,
            max_elapsed_seconds=120,
            max_branch_depth=1,
        ),
        sampling_defaults=SamplingDefaultsConfig(
            max_sampled_clients=2,
            max_sampled_aps=4,
            allow_client_sampling=True,
            allow_ap_sampling=True,
        ),
        allowed_optional_branches={
            "single_client_wifi_issue": {
                "net.client_health": ["net.dns_latency", "net.ap_rf_health"]
            }
        },
    )

    resolved_mapping = config.resolved_playbook_mapping()
    resolved_playbook = config.resolve_playbook_definition("single_client_wifi_issue")
    stop_config = config.build_stop_condition_config()
    branch_rules = config.merged_branch_rules()

    assert resolved_mapping[IncidentType.SINGLE_CLIENT] == "auth_or_onboarding_issue"
    assert resolved_playbook.stop_settings.max_skill_invocations == 3
    assert resolved_playbook.stop_settings.max_elapsed_seconds == 120
    assert resolved_playbook.stop_settings.max_branch_depth == 1
    assert resolved_playbook.stop_settings.high_confidence_threshold == 0.91
    assert resolved_playbook.sampling_settings.max_sampled_clients == 2
    assert resolved_playbook.sampling_settings.max_sampled_aps == 4
    assert resolved_playbook.sampling_settings.allow_client_sampling is True
    assert resolved_playbook.sampling_settings.allow_ap_sampling is True
    assert resolved_playbook.allowed_branch_transitions["net.client_health"] == [
        "net.dns_latency",
        "net.ap_rf_health",
    ]
    assert stop_config.ambiguity_gap == 0.05
    assert stop_config.ambiguity_min_score == 0.51
    assert stop_config.no_new_information_window == 3
    assert stop_config.scoring.suspected_threshold == 0.25
    assert stop_config.scoring.confidence_thresholds.high_min == 0.8
    assert branch_rules["net.client_health"][0].candidate_next_skills == ["net.path_probe"]


def test_orchestrator_config_loads_default_policy_controls() -> None:
    config = OrchestratorConfig()

    assert config.policy_controls.allow_active_probes is True
    assert config.policy_controls.allow_capture_triggers is True
    assert config.policy_controls.allow_external_resolver_comparisons is True
    assert config.policy_controls.allow_optional_expensive_branches is True
    assert config.policy_controls.expensive_branch_skills == []


def test_orchestrator_config_rejects_unknown_playbook_mapping() -> None:
    with pytest.raises(ValidationError, match="unknown playbooks"):
        OrchestratorConfig(
            playbook_mapping={IncidentType.SINGLE_CLIENT: "not_a_real_playbook"}
        )


def test_orchestrator_config_rejects_unknown_expensive_branch_skill() -> None:
    with pytest.raises(ValidationError, match="unknown skills"):
        OrchestratorConfig(
            policy_controls=PolicyControlConfig(
                expensive_branch_skills=["net.not_a_real_skill"]
            )
        )


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