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
from nettools.orchestrator import IncidentState, IncidentType, select_next_branch
from nettools.orchestrator.state import DependencyFailure, ExecutionRecord


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _execution_record(
    skill_name: str,
    *,
    finding_codes: list[str] | None = None,
    next_skills: list[str] | None = None,
) -> ExecutionRecord:
    observed_at = _now()
    result = SkillResult(
        status=Status.WARN if finding_codes else Status.OK,
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
        next_actions=[
            NextAction(skill=skill_name, reason=f"follow {skill_name}")
            for skill_name in next_skills or []
        ],
        raw_refs=[],
    )
    return ExecutionRecord.model_validate({
        "invocation_id": f"inv-{skill_name}",
        "skill_name": skill_name,
        "started_at": observed_at,
        "finished_at": observed_at,
        "duration_ms": 1,
        "input_summary": {},
        "result": result,
        "error_type": None,
    })


def test_branch_selector_prefers_explicit_rule_over_next_action_hint() -> None:
    state = IncidentState(
        incident_id="inc-branch-1",
        incident_type=IncidentType.SINGLE_CLIENT,
        playbook_used="single_client_wifi_issue",
    )
    state.skill_trace.append(
        _execution_record(
            "net.client_health",
            finding_codes=["LOW_RSSI"],
            next_skills=["net.dns_latency"],
        )
    )

    decision = select_next_branch(state)

    assert decision.source_skill == "net.client_health"
    assert decision.selected_skill == "net.ap_rf_health"
    assert (
        decision.candidate_scores["net.ap_rf_health"]
        > decision.candidate_scores["net.dns_latency"]
    )
    assert state.recommended_next_skill == "net.ap_rf_health"
    assert any("Explicit rule" in line for line in state.branch_selection_rationale)


def test_branch_selector_uses_next_action_when_no_explicit_rule_matches() -> None:
    state = IncidentState(
        incident_id="inc-branch-2",
        incident_type=IncidentType.SINGLE_CLIENT,
        playbook_used="single_client_wifi_issue",
    )
    state.skill_trace.append(
        _execution_record(
            "net.ap_rf_health",
            finding_codes=[],
            next_skills=["net.dns_latency"],
        )
    )

    decision = select_next_branch(state)

    assert decision.selected_skill == "net.dns_latency"
    assert (
        decision.candidate_scores["net.dns_latency"]
        > decision.candidate_scores["net.ap_uplink_health"]
    )
    assert any("next_action suggested net.dns_latency" in line for line in decision.rationale)


def test_branch_selector_filters_exhausted_and_blocked_skills() -> None:
    state = IncidentState(
        incident_id="inc-branch-3",
        incident_type=IncidentType.SITE_WIDE,
        playbook_used="site_wide_internal_slowdown",
        dependency_failures=[
            DependencyFailure(
                skill_name="net.stp_loop_anomaly",
                error_type="timeout",
                summary="switch telemetry unavailable",
                recorded_at=_now(),
            )
        ],
    )
    state.skill_trace.extend(
        [
            _execution_record("net.change_detection"),
            _execution_record(
                "net.path_probe",
                finding_codes=["SITE_WIDE_PATH_LOSS"],
                next_skills=["net.stp_loop_anomaly"],
            ),
        ]
    )

    decision = select_next_branch(state)

    assert decision.selected_skill == "net.dns_latency"
    assert "net.stp_loop_anomaly" not in decision.candidate_scores
    assert any("blocked by dependency failure" in line for line in decision.rationale)


def test_branch_selector_excludes_prior_execution_without_revisit() -> None:
    state = IncidentState(
        incident_id="inc-branch-4",
        incident_type=IncidentType.SINGLE_CLIENT,
        playbook_used="single_client_wifi_issue",
    )
    state.skill_trace.extend(
        [
            _execution_record("net.ap_rf_health"),
            _execution_record(
                "net.client_health",
                finding_codes=["LOW_SNR"],
                next_skills=["net.ap_rf_health", "net.dns_latency"],
            ),
        ]
    )

    decision = select_next_branch(state)

    assert decision.selected_skill == "net.dns_latency"
    assert "net.ap_rf_health" not in decision.candidate_scores
    assert any("already been executed" in line for line in decision.rationale)


def test_branch_selector_falls_back_to_playbook_order() -> None:
    state = IncidentState(
        incident_id="inc-branch-5",
        incident_type=IncidentType.AUTH_OR_ONBOARDING,
        playbook_used="auth_or_onboarding_issue",
    )
    state.skill_trace.append(_execution_record("net.auth_8021x_radius"))

    decision = select_next_branch(state)

    assert decision.selected_skill == "net.dhcp_path"
    assert (
        decision.candidate_scores["net.dhcp_path"]
        > decision.candidate_scores["net.segmentation_policy"]
    )
    assert state.recommended_next_skill == "net.dhcp_path"


def test_branch_selector_ignores_disallowed_transition_hints() -> None:
    state = IncidentState(
        incident_id="inc-branch-6",
        incident_type=IncidentType.SINGLE_CLIENT,
        playbook_used="single_client_wifi_issue",
    )
    state.skill_trace.append(
        _execution_record(
            "net.client_health",
            next_skills=["net.path_probe"],
        )
    )

    decision = select_next_branch(state)

    assert decision.selected_skill == "net.roaming_analysis"
    assert "net.path_probe" not in decision.candidate_scores


def test_branch_selector_uses_roaming_rules_for_failed_roams() -> None:
    state = IncidentState(
        incident_id="inc-branch-7",
        incident_type=IncidentType.SINGLE_CLIENT,
        playbook_used="single_client_wifi_issue",
    )
    state.skill_trace.append(
        _execution_record(
            "net.roaming_analysis",
            finding_codes=["FAILED_ROAMS"],
            next_skills=["net.client_health"],
        )
    )

    decision = select_next_branch(state)

    assert decision.selected_skill == "net.ap_rf_health"
    assert (
        decision.candidate_scores["net.ap_rf_health"]
        > decision.candidate_scores["net.client_health"]
    )


def test_branch_selector_uses_dhcp_rules_for_scope_mismatch() -> None:
    state = IncidentState(
        incident_id="inc-branch-8",
        incident_type=IncidentType.AUTH_OR_ONBOARDING,
        playbook_used="auth_or_onboarding_issue",
    )
    state.skill_trace.append(
        _execution_record(
            "net.dhcp_path",
            finding_codes=["SCOPE_UTILIZATION_HIGH"],
            next_skills=["net.dns_latency"],
        )
    )

    decision = select_next_branch(state)

    assert decision.selected_skill == "net.segmentation_policy"
    assert (
        decision.candidate_scores["net.segmentation_policy"]
        > decision.candidate_scores["net.dns_latency"]
    )


def test_branch_selector_uses_dns_rules_with_legal_playbook_targets() -> None:
    state = IncidentState(
        incident_id="inc-branch-9",
        incident_type=IncidentType.SINGLE_CLIENT,
        playbook_used="single_client_wifi_issue",
    )
    state.skill_trace.append(
        _execution_record(
            "net.dns_latency",
            finding_codes=["HIGH_DNS_LATENCY"],
            next_skills=["net.path_probe"],
        )
    )

    decision = select_next_branch(state)

    assert decision.selected_skill == "net.dhcp_path"
    assert "net.path_probe" not in decision.candidate_scores


def test_branch_selector_uses_ap_uplink_rules_for_vlan_mismatch() -> None:
    state = IncidentState(
        incident_id="inc-branch-10",
        incident_type=IncidentType.SINGLE_CLIENT,
        playbook_used="single_client_wifi_issue",
    )
    state.skill_trace.append(
        _execution_record(
            "net.ap_uplink_health",
            finding_codes=["UPLINK_VLAN_MISMATCH"],
        )
    )

    decision = select_next_branch(state)

    assert decision.selected_skill == "net.segmentation_policy"
    assert "net.incident_correlation" in decision.candidate_scores
