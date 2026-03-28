from __future__ import annotations

from datetime import datetime, timezone

from nettools.models import (
    Confidence,
    Finding,
    FindingSeverity,
    ScopeType,
    SkillResult,
    Status,
    TimeWindow,
)
from nettools.orchestrator import (
    ConfidenceThresholds,
    DiagnosticDomain,
    ExecutionRecord,
    HypothesisScoringConfig,
    IncidentState,
    confidence_from_score,
    score_incident_hypotheses,
)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _execution_record(
    skill_name: str,
    *,
    finding_codes: list[str] | None = None,
    status: Status = Status.OK,
) -> ExecutionRecord:
    observed_at = _now()
    result = SkillResult(
        status=status,
        skill_name=skill_name,
        scope_type=ScopeType.SERVICE,
        scope_id="scope-1",
        summary=f"{skill_name} summary",
        confidence=Confidence.MEDIUM,
        observed_at=observed_at,
        time_window=TimeWindow(start=observed_at, end=observed_at),
        evidence={},
        findings=[
            Finding(code=code, severity=FindingSeverity.WARN, message=code)
            for code in finding_codes or []
        ],
        next_actions=[],
        raw_refs=[],
    )
    return ExecutionRecord.model_validate(
        {
            "invocation_id": f"inv-{skill_name}",
            "skill_name": skill_name,
            "started_at": observed_at,
            "finished_at": observed_at,
            "duration_ms": 1,
            "input_summary": {},
            "result": result,
            "error_type": None,
        }
    )


def test_dns_issue_score_increases_from_dns_findings() -> None:
    state = IncidentState(incident_id="inc-score-1")
    state.skill_trace.append(
        _execution_record("net.dns_latency", finding_codes=["HIGH_DNS_LATENCY"])
    )

    decision = score_incident_hypotheses(state)

    assert decision.domain_scores[DiagnosticDomain.DNS_ISSUE].score >= 0.34
    assert DiagnosticDomain.DNS_ISSUE in state.suspected_domains
    assert (
        "HIGH_DNS_LATENCY"
        in decision.domain_scores[DiagnosticDomain.DNS_ISSUE].supporting_findings
    )


def test_rf_scores_drop_after_clean_client_and_ap_results() -> None:
    state = IncidentState(incident_id="inc-score-2")
    state.skill_trace.extend(
        [
            _execution_record("net.client_health"),
            _execution_record("net.ap_rf_health"),
        ]
    )

    decision = score_incident_hypotheses(state)

    assert decision.domain_scores[DiagnosticDomain.SINGLE_CLIENT_RF].score == 0.0
    assert decision.domain_scores[DiagnosticDomain.SINGLE_AP_RF].score == 0.0
    assert DiagnosticDomain.SINGLE_CLIENT_RF in state.eliminated_domains
    assert DiagnosticDomain.SINGLE_AP_RF in state.eliminated_domains


def test_ap_uplink_score_increases_from_crc_and_flap_findings() -> None:
    state = IncidentState(incident_id="inc-score-3")
    state.skill_trace.append(
        _execution_record(
            "net.ap_uplink_health",
            finding_codes=["UPLINK_ERROR_RATE", "UPLINK_FLAPPING"],
            status=Status.WARN,
        )
    )

    decision = score_incident_hypotheses(state)

    assert decision.domain_scores[DiagnosticDomain.AP_UPLINK_ISSUE].score >= 0.64
    assert decision.domain_scores[DiagnosticDomain.AP_UPLINK_ISSUE].confidence == Confidence.MEDIUM


def test_l2_score_increases_from_mac_flap_findings() -> None:
    state = IncidentState(incident_id="inc-score-4")
    state.skill_trace.append(
        _execution_record(
            "net.stp_loop_anomaly",
            finding_codes=["MAC_FLAP_LOOP_SIGNATURE", "TOPOLOGY_CHURN"],
            status=Status.FAIL,
        )
    )

    decision = score_incident_hypotheses(state)

    assert decision.domain_scores[DiagnosticDomain.L2_TOPOLOGY_ISSUE].score >= 0.68
    assert DiagnosticDomain.L2_TOPOLOGY_ISSUE in state.suspected_domains


def test_mixed_evidence_preserves_ambiguity() -> None:
    state = IncidentState(incident_id="inc-score-5")
    state.skill_trace.extend(
        [
            _execution_record("net.dns_latency", finding_codes=["DNS_TIMEOUT_RATE"]),
            _execution_record("net.ap_uplink_health", finding_codes=["UPLINK_ERROR_RATE"]),
        ]
    )

    decision = score_incident_hypotheses(state)

    assert DiagnosticDomain.DNS_ISSUE in state.suspected_domains
    assert DiagnosticDomain.AP_UPLINK_ISSUE in state.suspected_domains
    assert any("Mixed evidence" in line for line in decision.rationale)


def test_confidence_mapping_is_configurable() -> None:
    thresholds = ConfidenceThresholds(medium_min=0.30, high_min=0.60)
    config = HypothesisScoringConfig(confidence_thresholds=thresholds)
    state = IncidentState(incident_id="inc-score-6")
    state.skill_trace.append(
        _execution_record("net.ap_uplink_health", finding_codes=["UPLINK_ERROR_RATE"])
    )

    decision = score_incident_hypotheses(state, config=config)

    assert confidence_from_score(0.31, thresholds) == Confidence.MEDIUM
    assert decision.domain_scores[DiagnosticDomain.AP_UPLINK_ISSUE].confidence == Confidence.MEDIUM