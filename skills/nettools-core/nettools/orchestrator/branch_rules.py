from __future__ import annotations

from collections.abc import Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field

from .playbooks import PlaybookDefinition, get_playbook_definition
from .state import DiagnosticDomain, IncidentState


class BranchRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_skill: str
    triggering_findings: list[str] = Field(default_factory=list)
    candidate_next_skills: list[str] = Field(default_factory=list)
    score_adjustments: dict[DiagnosticDomain, float] = Field(default_factory=dict)
    branch_priority: int = Field(default=1, ge=1)


class BranchSelectionDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_skill: str | None = None
    selected_skill: str | None = None
    candidate_scores: dict[str, int] = Field(default_factory=dict)
    rationale: list[str] = Field(default_factory=list)


DEFAULT_BRANCH_RULES: dict[str, list[BranchRule]] = {
    "net.client_health": [
        BranchRule(
            source_skill="net.client_health",
            triggering_findings=["LOW_RSSI", "LOW_SNR", "HIGH_RETRY_RATE", "STICKY_CLIENT"],
            candidate_next_skills=["net.ap_rf_health"],
            score_adjustments={DiagnosticDomain.SINGLE_CLIENT_RF: 0.2},
            branch_priority=5,
        ),
        BranchRule(
            source_skill="net.client_health",
            triggering_findings=["EXCESSIVE_ROAMING", "RAPID_RECONNECTS"],
            candidate_next_skills=["net.roaming_analysis"],
            score_adjustments={DiagnosticDomain.ROAMING_ISSUE: 0.2},
            branch_priority=4,
        ),
        BranchRule(
            source_skill="net.client_health",
            triggering_findings=["HIGH_PACKET_LOSS"],
            candidate_next_skills=["net.dns_latency", "net.path_probe"],
            branch_priority=3,
        ),
    ],
    "net.ap_rf_health": [
        BranchRule(
            source_skill="net.ap_rf_health",
            triggering_findings=[
                "HIGH_CHANNEL_UTILIZATION",
                "HIGH_AP_CLIENT_LOAD",
                "RADIO_RESETS",
                "POTENTIAL_CO_CHANNEL_INTERFERENCE",
            ],
            candidate_next_skills=["net.client_health"],
            score_adjustments={DiagnosticDomain.SINGLE_AP_RF: 0.2},
            branch_priority=4,
        ),
        BranchRule(
            source_skill="net.ap_rf_health",
            triggering_findings=[],
            candidate_next_skills=["net.ap_uplink_health", "net.dns_latency"],
            branch_priority=1,
        ),
    ],
    "net.roaming_analysis": [
        BranchRule(
            source_skill="net.roaming_analysis",
            triggering_findings=["FAILED_ROAMS", "HIGH_ROAM_LATENCY"],
            candidate_next_skills=["net.ap_rf_health"],
            score_adjustments={DiagnosticDomain.ROAMING_ISSUE: 0.3},
            branch_priority=5,
        ),
        BranchRule(
            source_skill="net.roaming_analysis",
            triggering_findings=["EXCESSIVE_ROAM_COUNT"],
            candidate_next_skills=["net.ap_rf_health", "net.client_health"],
            score_adjustments={DiagnosticDomain.ROAMING_ISSUE: 0.2},
            branch_priority=4,
        ),
        BranchRule(
            source_skill="net.roaming_analysis",
            triggering_findings=["STICKY_CLIENT_PATTERN"],
            candidate_next_skills=["net.client_health", "net.ap_rf_health"],
            score_adjustments={DiagnosticDomain.ROAMING_ISSUE: 0.2},
            branch_priority=4,
        ),
    ],
    "net.dhcp_path": [
        BranchRule(
            source_skill="net.dhcp_path",
            triggering_findings=["SCOPE_UTILIZATION_HIGH", "RELAY_PATH_MISMATCH"],
            candidate_next_skills=["net.segmentation_policy"],
            score_adjustments={DiagnosticDomain.SEGMENTATION_POLICY_ISSUE: 0.3},
            branch_priority=5,
        ),
        BranchRule(
            source_skill="net.dhcp_path",
            triggering_findings=[
                "HIGH_DHCP_OFFER_LATENCY",
                "HIGH_DHCP_ACK_LATENCY",
                "DHCP_TIMEOUTS",
                "MISSING_DHCP_ACK",
            ],
            candidate_next_skills=["net.path_probe", "net.dns_latency"],
            score_adjustments={DiagnosticDomain.DHCP_ISSUE: 0.3},
            branch_priority=4,
        ),
    ],
    "net.dns_latency": [
        BranchRule(
            source_skill="net.dns_latency",
            triggering_findings=["HIGH_DNS_LATENCY", "DNS_TIMEOUT_RATE"],
            candidate_next_skills=[
                "net.path_probe",
                "net.dhcp_path",
                "net.client_health",
                "net.ap_rf_health",
                "net.incident_correlation",
            ],
            score_adjustments={DiagnosticDomain.DNS_ISSUE: 0.3},
            branch_priority=5,
        )
    ],
    "net.ap_uplink_health": [
        BranchRule(
            source_skill="net.ap_uplink_health",
            triggering_findings=["UPLINK_VLAN_MISMATCH"],
            candidate_next_skills=["net.segmentation_policy", "net.incident_correlation"],
            score_adjustments={DiagnosticDomain.SEGMENTATION_POLICY_ISSUE: 0.3},
            branch_priority=5,
        ),
        BranchRule(
            source_skill="net.ap_uplink_health",
            triggering_findings=["UPLINK_ERROR_RATE", "UPLINK_FLAPPING"],
            candidate_next_skills=["net.stp_loop_anomaly", "net.incident_correlation"],
            score_adjustments={DiagnosticDomain.AP_UPLINK_ISSUE: 0.3},
            branch_priority=4,
        ),
        BranchRule(
            source_skill="net.ap_uplink_health",
            triggering_findings=["UPLINK_SPEED_MISMATCH", "POE_INSTABILITY"],
            candidate_next_skills=["net.incident_correlation", "net.ap_rf_health"],
            score_adjustments={DiagnosticDomain.AP_UPLINK_ISSUE: 0.2},
            branch_priority=3,
        ),
    ],
    "net.path_probe": [
        BranchRule(
            source_skill="net.path_probe",
            triggering_findings=["INTERNAL_SERVICE_DEGRADATION"],
            candidate_next_skills=["net.dns_latency", "net.dhcp_path"],
            score_adjustments={DiagnosticDomain.SITE_WIDE_INTERNAL_LAN_ISSUE: 0.2},
            branch_priority=4,
        ),
        BranchRule(
            source_skill="net.path_probe",
            triggering_findings=["SITE_WIDE_PATH_LOSS"],
            candidate_next_skills=["net.stp_loop_anomaly", "net.ap_uplink_health"],
            score_adjustments={DiagnosticDomain.SITE_WIDE_INTERNAL_LAN_ISSUE: 0.3},
            branch_priority=5,
        ),
        BranchRule(
            source_skill="net.path_probe",
            triggering_findings=["WAN_EXTERNAL_DEGRADATION"],
            candidate_next_skills=["net.incident_correlation"],
            score_adjustments={DiagnosticDomain.WAN_OR_EXTERNAL_ISSUE: 0.3},
            branch_priority=3,
        ),
    ],
    "net.stp_loop_anomaly": [
        BranchRule(
            source_skill="net.stp_loop_anomaly",
            triggering_findings=["MAC_FLAP_LOOP_SIGNATURE", "TOPOLOGY_CHURN", "STORM_INDICATORS"],
            candidate_next_skills=["net.ap_uplink_health", "net.incident_correlation"],
            score_adjustments={DiagnosticDomain.L2_TOPOLOGY_ISSUE: 0.4},
            branch_priority=5,
        )
    ],
    "net.auth_8021x_radius": [
        BranchRule(
            source_skill="net.auth_8021x_radius",
            triggering_findings=["AUTH_TIMEOUTS", "RADIUS_UNREACHABLE", "RADIUS_HIGH_RTT"],
            candidate_next_skills=["net.dhcp_path", "net.dns_latency"],
            score_adjustments={DiagnosticDomain.AUTH_ISSUE: 0.3},
            branch_priority=4,
        ),
        BranchRule(
            source_skill="net.auth_8021x_radius",
            triggering_findings=["AUTH_CREDENTIAL_FAILURES", "AUTH_CERTIFICATE_FAILURES"],
            candidate_next_skills=["net.segmentation_policy"],
            score_adjustments={DiagnosticDomain.SEGMENTATION_POLICY_ISSUE: 0.2},
            branch_priority=3,
        ),
    ],
    "net.segmentation_policy": [
        BranchRule(
            source_skill="net.segmentation_policy",
            triggering_findings=[
                "VLAN_MISMATCH",
                "POLICY_GROUP_MISMATCH",
                "GATEWAY_ALIGNMENT_MISMATCH",
            ],
            candidate_next_skills=["net.auth_8021x_radius", "net.dhcp_path"],
            score_adjustments={DiagnosticDomain.SEGMENTATION_POLICY_ISSUE: 0.3},
            branch_priority=4,
        )
    ],
}


def _blocked_skills(state: IncidentState) -> set[str]:
    return {failure.skill_name for failure in state.dependency_failures}


def _exhausted_skills(state: IncidentState) -> set[str]:
    return {record.skill_name for record in state.skill_trace}


def _choose_playbook(
    playbook: PlaybookDefinition | str | None,
    state: IncidentState,
) -> PlaybookDefinition | None:
    if isinstance(playbook, PlaybookDefinition):
        return playbook
    if isinstance(playbook, str):
        return get_playbook_definition(playbook)
    if state.playbook_used is not None:
        return get_playbook_definition(state.playbook_used)
    return None


def _score_default_sequence(playbook: PlaybookDefinition, source_skill: str) -> dict[str, int]:
    default_scores: dict[str, int] = {}
    try:
        source_index = playbook.default_sequence.index(source_skill)
    except ValueError:
        source_index = -1

    for index, skill_name in enumerate(playbook.default_sequence):
        if source_index >= 0 and index <= source_index:
            continue
        default_scores[skill_name] = max(1, len(playbook.default_sequence) - index)
    return default_scores


def _playbook_index(playbook: PlaybookDefinition, skill_name: str) -> int | None:
    try:
        return playbook.default_sequence.index(skill_name)
    except ValueError:
        return None


def _allowed_targets(playbook: PlaybookDefinition | None, source_skill: str) -> list[str]:
    if playbook is None:
        return []
    return list(playbook.allowed_branch_transitions.get(source_skill, []))


def select_next_branch(
    state: IncidentState,
    *,
    playbook: PlaybookDefinition | str | None = None,
    source_skill: str | None = None,
    branch_rules: Mapping[str, Sequence[BranchRule]] | None = None,
    allow_revisit: bool = False,
) -> BranchSelectionDecision:
    resolved_playbook = _choose_playbook(playbook, state)
    current_source = source_skill or (
        state.skill_trace[-1].skill_name if state.skill_trace else None
    )
    if current_source is None:
        decision = BranchSelectionDecision(
            rationale=["No executed skill is available to branch from."]
        )
        state.set_branch_recommendation(None, rationale=decision.rationale)
        return decision

    last_record = None
    for record in reversed(state.skill_trace):
        if record.skill_name == current_source:
            last_record = record
            break
    if last_record is None:
        decision = BranchSelectionDecision(
            source_skill=current_source,
            rationale=[f"No execution record found for branch source {current_source}."],
        )
        state.set_branch_recommendation(None, rationale=decision.rationale)
        return decision

    allowed_targets = _allowed_targets(resolved_playbook, current_source)
    if not allowed_targets and resolved_playbook is not None:
        allowed_targets = [
            skill_name
            for skill_name in resolved_playbook.default_sequence
            if skill_name != current_source
        ]

    exhausted = _exhausted_skills(state)
    blocked = _blocked_skills(state)
    candidate_scores: dict[str, int] = {skill_name: 0 for skill_name in allowed_targets}
    rationale = [f"Branch source is {current_source}."]

    findings = {finding.code for finding in last_record.result.findings}
    active_rules = branch_rules or DEFAULT_BRANCH_RULES
    for rule in active_rules.get(current_source, []):
        if rule.triggering_findings and not findings.intersection(rule.triggering_findings):
            continue
        for skill_name in rule.candidate_next_skills:
            if skill_name not in candidate_scores:
                continue
            candidate_scores[skill_name] += rule.branch_priority * 10
            if resolved_playbook is not None:
                source_index = _playbook_index(resolved_playbook, current_source)
                target_index = _playbook_index(resolved_playbook, skill_name)
                if (
                    source_index is not None
                    and target_index is not None
                    and target_index < source_index
                ):
                    candidate_scores[skill_name] += 3
                    rationale.append(
                        "Explicit rule from "
                        f"{current_source} allows a backward branch to {skill_name}."
                    )
            rationale.append(
                f"Explicit rule from {current_source} increased {skill_name} due to findings match."
            )

    for action in last_record.result.next_actions:
        if action.skill in candidate_scores:
            candidate_scores[action.skill] += 5
            rationale.append(
                f"Lower-level next_action suggested {action.skill}: {action.reason}"
            )

    if resolved_playbook is not None:
        default_order_scores = _score_default_sequence(resolved_playbook, current_source)
        for skill_name, score in default_order_scores.items():
            if skill_name in candidate_scores:
                candidate_scores[skill_name] += score

    filtered_scores: dict[str, int] = {}
    for skill_name, score in candidate_scores.items():
        if skill_name in blocked:
            rationale.append(f"Excluded {skill_name} because it is blocked by dependency failure.")
            continue
        if not allow_revisit and skill_name in exhausted:
            rationale.append(f"Excluded {skill_name} because it has already been executed.")
            continue
        filtered_scores[skill_name] = score

    if not filtered_scores:
        decision = BranchSelectionDecision(
            source_skill=current_source,
            candidate_scores={},
            rationale=rationale + ["No eligible branch targets remain after filtering."],
        )
        state.set_branch_recommendation(None, rationale=decision.rationale)
        return decision

    selected_skill = sorted(filtered_scores.items(), key=lambda item: (-item[1], item[0]))[0][0]
    rationale.append(f"Selected {selected_skill} as the highest-ranked eligible branch target.")
    decision = BranchSelectionDecision(
        source_skill=current_source,
        selected_skill=selected_skill,
        candidate_scores=filtered_scores,
        rationale=rationale,
    )
    state.set_branch_recommendation(selected_skill, rationale=decision.rationale)
    return decision