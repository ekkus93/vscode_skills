from __future__ import annotations

from collections.abc import Iterable, Sequence

from pydantic import BaseModel, ConfigDict, Field

from ..models import Confidence, Status
from .state import (
    DiagnosticDomain,
    DomainScore,
    ExecutionRecord,
    IncidentState,
    InvestigationTraceEventType,
)


class ConfidenceThresholds(BaseModel):
    model_config = ConfigDict(extra="forbid")

    medium_min: float = Field(default=0.40, ge=0.0, le=1.0)
    high_min: float = Field(default=0.75, ge=0.0, le=1.0)


class HypothesisScoringConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confidence_thresholds: ConfidenceThresholds = Field(
        default_factory=ConfidenceThresholds
    )
    suspected_threshold: float = Field(default=0.15, ge=0.0, le=1.0)
    eliminated_threshold: float = Field(default=0.05, ge=0.0, le=1.0)
    suppression_trigger: float = Field(default=0.55, ge=0.0, le=1.0)
    unknown_score_without_signal: float = Field(default=0.20, ge=0.0, le=1.0)


class FindingScoreRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supporting_domains: dict[DiagnosticDomain, float] = Field(default_factory=dict)
    contradicting_domains: dict[DiagnosticDomain, float] = Field(default_factory=dict)


class HypothesisScoringDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain_scores: dict[DiagnosticDomain, DomainScore] = Field(default_factory=dict)
    top_domains: list[DiagnosticDomain] = Field(default_factory=list)
    rationale: list[str] = Field(default_factory=list)


DEFAULT_FINDING_SCORE_RULES: dict[str, FindingScoreRule] = {
    "LOW_RSSI": FindingScoreRule(
        supporting_domains={DiagnosticDomain.SINGLE_CLIENT_RF: 0.28}
    ),
    "LOW_SNR": FindingScoreRule(
        supporting_domains={DiagnosticDomain.SINGLE_CLIENT_RF: 0.28}
    ),
    "HIGH_RETRY_RATE": FindingScoreRule(
        supporting_domains={DiagnosticDomain.SINGLE_CLIENT_RF: 0.22}
    ),
    "HIGH_PACKET_LOSS": FindingScoreRule(
        supporting_domains={
            DiagnosticDomain.SINGLE_CLIENT_RF: 0.12,
            DiagnosticDomain.DNS_ISSUE: 0.08,
            DiagnosticDomain.DHCP_ISSUE: 0.08,
        }
    ),
    "EXCESSIVE_ROAMING": FindingScoreRule(
        supporting_domains={DiagnosticDomain.ROAMING_ISSUE: 0.28}
    ),
    "RAPID_RECONNECTS": FindingScoreRule(
        supporting_domains={DiagnosticDomain.ROAMING_ISSUE: 0.22}
    ),
    "STICKY_CLIENT": FindingScoreRule(
        supporting_domains={
            DiagnosticDomain.SINGLE_CLIENT_RF: 0.16,
            DiagnosticDomain.ROAMING_ISSUE: 0.14,
        }
    ),
    "HIGH_CHANNEL_UTILIZATION": FindingScoreRule(
        supporting_domains={DiagnosticDomain.SINGLE_AP_RF: 0.30}
    ),
    "HIGH_AP_CLIENT_LOAD": FindingScoreRule(
        supporting_domains={DiagnosticDomain.SINGLE_AP_RF: 0.24}
    ),
    "UNSUITABLE_CHANNEL_WIDTH": FindingScoreRule(
        supporting_domains={DiagnosticDomain.SINGLE_AP_RF: 0.18}
    ),
    "RADIO_RESETS": FindingScoreRule(
        supporting_domains={DiagnosticDomain.SINGLE_AP_RF: 0.24}
    ),
    "POTENTIAL_CO_CHANNEL_INTERFERENCE": FindingScoreRule(
        supporting_domains={DiagnosticDomain.SINGLE_AP_RF: 0.28}
    ),
    "HIGH_DHCP_OFFER_LATENCY": FindingScoreRule(
        supporting_domains={DiagnosticDomain.DHCP_ISSUE: 0.26}
    ),
    "HIGH_DHCP_ACK_LATENCY": FindingScoreRule(
        supporting_domains={DiagnosticDomain.DHCP_ISSUE: 0.26}
    ),
    "DHCP_TIMEOUTS": FindingScoreRule(
        supporting_domains={DiagnosticDomain.DHCP_ISSUE: 0.34}
    ),
    "MISSING_DHCP_ACK": FindingScoreRule(
        supporting_domains={DiagnosticDomain.DHCP_ISSUE: 0.30}
    ),
    "SCOPE_UTILIZATION_HIGH": FindingScoreRule(
        supporting_domains={
            DiagnosticDomain.DHCP_ISSUE: 0.20,
            DiagnosticDomain.SEGMENTATION_POLICY_ISSUE: 0.18,
        }
    ),
    "RELAY_PATH_MISMATCH": FindingScoreRule(
        supporting_domains={
            DiagnosticDomain.DHCP_ISSUE: 0.15,
            DiagnosticDomain.SEGMENTATION_POLICY_ISSUE: 0.24,
        }
    ),
    "HIGH_DNS_LATENCY": FindingScoreRule(
        supporting_domains={DiagnosticDomain.DNS_ISSUE: 0.34},
        contradicting_domains={
            DiagnosticDomain.SITE_WIDE_INTERNAL_LAN_ISSUE: 0.05,
            DiagnosticDomain.WAN_OR_EXTERNAL_ISSUE: 0.05,
        },
    ),
    "DNS_TIMEOUT_RATE": FindingScoreRule(
        supporting_domains={DiagnosticDomain.DNS_ISSUE: 0.36},
        contradicting_domains={
            DiagnosticDomain.SITE_WIDE_INTERNAL_LAN_ISSUE: 0.05,
            DiagnosticDomain.WAN_OR_EXTERNAL_ISSUE: 0.05,
        },
    ),
    "UPLINK_SPEED_MISMATCH": FindingScoreRule(
        supporting_domains={DiagnosticDomain.AP_UPLINK_ISSUE: 0.22}
    ),
    "UPLINK_ERROR_RATE": FindingScoreRule(
        supporting_domains={DiagnosticDomain.AP_UPLINK_ISSUE: 0.34}
    ),
    "UPLINK_FLAPPING": FindingScoreRule(
        supporting_domains={DiagnosticDomain.AP_UPLINK_ISSUE: 0.30}
    ),
    "UPLINK_VLAN_MISMATCH": FindingScoreRule(
        supporting_domains={
            DiagnosticDomain.AP_UPLINK_ISSUE: 0.16,
            DiagnosticDomain.SEGMENTATION_POLICY_ISSUE: 0.22,
        }
    ),
    "POE_INSTABILITY": FindingScoreRule(
        supporting_domains={DiagnosticDomain.AP_UPLINK_ISSUE: 0.24}
    ),
    "TOPOLOGY_CHURN": FindingScoreRule(
        supporting_domains={DiagnosticDomain.L2_TOPOLOGY_ISSUE: 0.30},
        contradicting_domains={DiagnosticDomain.AP_UPLINK_ISSUE: 0.05},
    ),
    "ROOT_BRIDGE_CHANGES": FindingScoreRule(
        supporting_domains={DiagnosticDomain.L2_TOPOLOGY_ISSUE: 0.24},
        contradicting_domains={DiagnosticDomain.AP_UPLINK_ISSUE: 0.04},
    ),
    "MAC_FLAP_LOOP_SIGNATURE": FindingScoreRule(
        supporting_domains={DiagnosticDomain.L2_TOPOLOGY_ISSUE: 0.38},
        contradicting_domains={DiagnosticDomain.AP_UPLINK_ISSUE: 0.10},
    ),
    "STORM_INDICATORS": FindingScoreRule(
        supporting_domains={DiagnosticDomain.L2_TOPOLOGY_ISSUE: 0.32},
        contradicting_domains={DiagnosticDomain.AP_UPLINK_ISSUE: 0.08},
    ),
    "EXCESSIVE_ROAM_COUNT": FindingScoreRule(
        supporting_domains={DiagnosticDomain.ROAMING_ISSUE: 0.24}
    ),
    "HIGH_ROAM_LATENCY": FindingScoreRule(
        supporting_domains={DiagnosticDomain.ROAMING_ISSUE: 0.30}
    ),
    "FAILED_ROAMS": FindingScoreRule(
        supporting_domains={DiagnosticDomain.ROAMING_ISSUE: 0.34}
    ),
    "STICKY_CLIENT_PATTERN": FindingScoreRule(
        supporting_domains={
            DiagnosticDomain.ROAMING_ISSUE: 0.18,
            DiagnosticDomain.SINGLE_CLIENT_RF: 0.10,
        }
    ),
    "LOW_AUTH_SUCCESS_RATE": FindingScoreRule(
        supporting_domains={DiagnosticDomain.AUTH_ISSUE: 0.22}
    ),
    "AUTH_TIMEOUTS": FindingScoreRule(
        supporting_domains={DiagnosticDomain.AUTH_ISSUE: 0.30}
    ),
    "RADIUS_UNREACHABLE": FindingScoreRule(
        supporting_domains={DiagnosticDomain.AUTH_ISSUE: 0.36}
    ),
    "RADIUS_HIGH_RTT": FindingScoreRule(
        supporting_domains={DiagnosticDomain.AUTH_ISSUE: 0.24}
    ),
    "AUTH_CREDENTIAL_FAILURES": FindingScoreRule(
        supporting_domains={
            DiagnosticDomain.AUTH_ISSUE: 0.16,
            DiagnosticDomain.SEGMENTATION_POLICY_ISSUE: 0.10,
        }
    ),
    "AUTH_CERTIFICATE_FAILURES": FindingScoreRule(
        supporting_domains={
            DiagnosticDomain.AUTH_ISSUE: 0.18,
            DiagnosticDomain.SEGMENTATION_POLICY_ISSUE: 0.08,
        }
    ),
    "SITE_WIDE_PATH_LOSS": FindingScoreRule(
        supporting_domains={DiagnosticDomain.SITE_WIDE_INTERNAL_LAN_ISSUE: 0.32}
    ),
    "INTERNAL_SERVICE_DEGRADATION": FindingScoreRule(
        supporting_domains={DiagnosticDomain.SITE_WIDE_INTERNAL_LAN_ISSUE: 0.28},
        contradicting_domains={DiagnosticDomain.WAN_OR_EXTERNAL_ISSUE: 0.10},
    ),
    "WAN_EXTERNAL_DEGRADATION": FindingScoreRule(
        supporting_domains={DiagnosticDomain.WAN_OR_EXTERNAL_ISSUE: 0.34},
        contradicting_domains={DiagnosticDomain.SITE_WIDE_INTERNAL_LAN_ISSUE: 0.10},
    ),
    "VLAN_MISMATCH": FindingScoreRule(
        supporting_domains={DiagnosticDomain.SEGMENTATION_POLICY_ISSUE: 0.34}
    ),
    "POLICY_GROUP_MISMATCH": FindingScoreRule(
        supporting_domains={DiagnosticDomain.SEGMENTATION_POLICY_ISSUE: 0.30}
    ),
    "GATEWAY_ALIGNMENT_MISMATCH": FindingScoreRule(
        supporting_domains={DiagnosticDomain.SEGMENTATION_POLICY_ISSUE: 0.28}
    ),
}


DEFAULT_CLEAN_SKILL_RULES: dict[str, FindingScoreRule] = {
    "net.client_health": FindingScoreRule(
        contradicting_domains={DiagnosticDomain.SINGLE_CLIENT_RF: 0.30}
    ),
    "net.ap_rf_health": FindingScoreRule(
        contradicting_domains={DiagnosticDomain.SINGLE_AP_RF: 0.35}
    ),
    "net.roaming_analysis": FindingScoreRule(
        contradicting_domains={DiagnosticDomain.ROAMING_ISSUE: 0.28}
    ),
    "net.dhcp_path": FindingScoreRule(
        contradicting_domains={DiagnosticDomain.DHCP_ISSUE: 0.35}
    ),
    "net.dns_latency": FindingScoreRule(
        contradicting_domains={DiagnosticDomain.DNS_ISSUE: 0.36}
    ),
    "net.auth_8021x_radius": FindingScoreRule(
        contradicting_domains={DiagnosticDomain.AUTH_ISSUE: 0.32}
    ),
    "net.ap_uplink_health": FindingScoreRule(
        contradicting_domains={DiagnosticDomain.AP_UPLINK_ISSUE: 0.35}
    ),
    "net.stp_loop_anomaly": FindingScoreRule(
        contradicting_domains={DiagnosticDomain.L2_TOPOLOGY_ISSUE: 0.40}
    ),
    "net.path_probe": FindingScoreRule(
        contradicting_domains={
            DiagnosticDomain.SITE_WIDE_INTERNAL_LAN_ISSUE: 0.32,
            DiagnosticDomain.WAN_OR_EXTERNAL_ISSUE: 0.28,
        }
    ),
    "net.segmentation_policy": FindingScoreRule(
        contradicting_domains={DiagnosticDomain.SEGMENTATION_POLICY_ISSUE: 0.30}
    ),
}


DEFAULT_CROSS_DOMAIN_SUPPRESSIONS: dict[DiagnosticDomain, dict[DiagnosticDomain, float]] = {
    DiagnosticDomain.L2_TOPOLOGY_ISSUE: {
        DiagnosticDomain.AP_UPLINK_ISSUE: 0.12,
    },
    DiagnosticDomain.DNS_ISSUE: {
        DiagnosticDomain.SITE_WIDE_INTERNAL_LAN_ISSUE: 0.08,
        DiagnosticDomain.WAN_OR_EXTERNAL_ISSUE: 0.06,
    },
    DiagnosticDomain.WAN_OR_EXTERNAL_ISSUE: {
        DiagnosticDomain.SITE_WIDE_INTERNAL_LAN_ISSUE: 0.10,
    },
}


def all_diagnostic_domains() -> list[DiagnosticDomain]:
    return list(DiagnosticDomain)


def confidence_from_score(
    score: float,
    thresholds: ConfidenceThresholds | None = None,
) -> Confidence:
    resolved_thresholds = thresholds or ConfidenceThresholds()
    if score >= resolved_thresholds.high_min:
        return Confidence.HIGH
    if score >= resolved_thresholds.medium_min:
        return Confidence.MEDIUM
    return Confidence.LOW


def initialize_domain_scores(
    *,
    config: HypothesisScoringConfig | None = None,
) -> dict[DiagnosticDomain, DomainScore]:
    resolved_config = config or HypothesisScoringConfig()
    return {
        domain: DomainScore(
            domain=domain,
            score=(
                resolved_config.unknown_score_without_signal
                if domain is DiagnosticDomain.UNKNOWN
                else 0.0
            ),
            confidence=confidence_from_score(
                resolved_config.unknown_score_without_signal
                if domain is DiagnosticDomain.UNKNOWN
                else 0.0,
                resolved_config.confidence_thresholds,
            ),
        )
        for domain in DiagnosticDomain
    }


def _clamp_score(value: float) -> float:
    return max(0.0, min(1.0, round(value, 3)))


def _apply_rule(
    scores: dict[DiagnosticDomain, float],
    supporting: dict[DiagnosticDomain, set[str]],
    contradicting: dict[DiagnosticDomain, set[str]],
    *,
    label: str,
    rule: FindingScoreRule,
    rationale: list[str],
) -> None:
    for domain, delta in rule.supporting_domains.items():
        scores[domain] = _clamp_score(scores[domain] + delta)
        supporting[domain].add(label)
        rationale.append(f"{label} increased {domain.value} by {delta:.2f}.")
    for domain, delta in rule.contradicting_domains.items():
        scores[domain] = _clamp_score(scores[domain] - delta)
        contradicting[domain].add(label)
        rationale.append(f"{label} reduced {domain.value} by {delta:.2f}.")


def _apply_clean_skill_rules(
    records: Iterable[ExecutionRecord],
    scores: dict[DiagnosticDomain, float],
    supporting: dict[DiagnosticDomain, set[str]],
    contradicting: dict[DiagnosticDomain, set[str]],
    rationale: list[str],
) -> None:
    for record in records:
        if record.result.status is not Status.OK or record.result.findings:
            continue
        rule = DEFAULT_CLEAN_SKILL_RULES.get(record.skill_name)
        if rule is None:
            continue
        _apply_rule(
            scores,
            supporting,
            contradicting,
            label=f"{record.skill_name}:clean",
            rule=rule,
            rationale=rationale,
        )


def _apply_cross_domain_suppressions(
    scores: dict[DiagnosticDomain, float],
    contradicting: dict[DiagnosticDomain, set[str]],
    *,
    config: HypothesisScoringConfig,
    rationale: list[str],
) -> None:
    for domain, suppressions in DEFAULT_CROSS_DOMAIN_SUPPRESSIONS.items():
        if scores[domain] < config.suppression_trigger:
            continue
        for suppressed_domain, delta in suppressions.items():
            scores[suppressed_domain] = _clamp_score(scores[suppressed_domain] - delta)
            contradicting[suppressed_domain].add(f"suppressed_by:{domain.value}")
            rationale.append(
                f"Strong {domain.value} evidence suppressed "
                f"{suppressed_domain.value} by {delta:.2f}."
            )


def _build_scored_domains(
    scores: dict[DiagnosticDomain, float],
    supporting: dict[DiagnosticDomain, set[str]],
    contradicting: dict[DiagnosticDomain, set[str]],
    *,
    config: HypothesisScoringConfig,
) -> dict[DiagnosticDomain, DomainScore]:
    return {
        domain: DomainScore(
            domain=domain,
            score=scores[domain],
            confidence=confidence_from_score(
                scores[domain],
                config.confidence_thresholds,
            ),
            supporting_findings=sorted(supporting[domain]),
            contradicting_findings=sorted(contradicting[domain]),
        )
        for domain in DiagnosticDomain
    }


def _select_top_domains(
    scored_domains: dict[DiagnosticDomain, DomainScore],
) -> list[DiagnosticDomain]:
    ordered = sorted(
        scored_domains.values(),
        key=lambda item: (-item.score, item.domain.value),
    )
    return [item.domain for item in ordered if item.score > 0.0]


def score_incident_hypotheses(
    state: IncidentState,
    *,
    config: HypothesisScoringConfig | None = None,
    execution_records: Sequence[ExecutionRecord] | None = None,
) -> HypothesisScoringDecision:
    resolved_config = config or HypothesisScoringConfig()
    records = list(execution_records) if execution_records is not None else list(state.skill_trace)
    scores = {domain: 0.0 for domain in DiagnosticDomain}
    if not records:
        scores[DiagnosticDomain.UNKNOWN] = resolved_config.unknown_score_without_signal
    supporting: dict[DiagnosticDomain, set[str]] = {
        domain: set() for domain in DiagnosticDomain
    }
    contradicting: dict[DiagnosticDomain, set[str]] = {
        domain: set() for domain in DiagnosticDomain
    }
    rationale: list[str] = []

    for record in records:
        for finding in record.result.findings:
            rule = DEFAULT_FINDING_SCORE_RULES.get(finding.code)
            if rule is None:
                continue
            _apply_rule(
                scores,
                supporting,
                contradicting,
                label=finding.code,
                rule=rule,
                rationale=rationale,
            )

    _apply_clean_skill_rules(records, scores, supporting, contradicting, rationale)
    _apply_cross_domain_suppressions(
        scores,
        contradicting,
        config=resolved_config,
        rationale=rationale,
    )

    non_unknown_scores = [
        score for domain, score in scores.items() if domain is not DiagnosticDomain.UNKNOWN
    ]
    if all(score < resolved_config.suspected_threshold for score in non_unknown_scores):
        scores[DiagnosticDomain.UNKNOWN] = max(
            scores[DiagnosticDomain.UNKNOWN],
            resolved_config.unknown_score_without_signal,
        )
        rationale.append("No strong domain signal found; preserved unknown domain as plausible.")
    else:
        scores[DiagnosticDomain.UNKNOWN] = 0.0

    scored_domains = _build_scored_domains(
        scores,
        supporting,
        contradicting,
        config=resolved_config,
    )
    top_domains = _select_top_domains(scored_domains)

    state.domain_scores = scored_domains
    state.suspected_domains = [
        domain
        for domain, score in scores.items()
        if score >= resolved_config.suspected_threshold
    ]
    state.eliminated_domains = [
        domain
        for domain, score in scores.items()
        if score <= resolved_config.eliminated_threshold
    ]
    overlap = set(state.suspected_domains).intersection(state.eliminated_domains)
    if overlap:
        state.eliminated_domains = [
            domain for domain in state.eliminated_domains if domain not in overlap
        ]

    if len(state.suspected_domains) > 1:
        rationale.append(
            "Mixed evidence keeps multiple domains plausible instead of forcing a single cause."
        )

    state.append_trace(
        InvestigationTraceEventType.SCORE_UPDATE,
        f"Updated domain scores using {len(records)} execution records.",
        details={
            "top_domains": [domain.value for domain in top_domains[:3]],
            "suspected_domains": [domain.value for domain in state.suspected_domains],
            "eliminated_domains": [domain.value for domain in state.eliminated_domains],
            "rationale": list(rationale),
            "domain_scores": {
                domain.value: scored_domains[domain].score for domain in DiagnosticDomain
            },
        },
    )

    return HypothesisScoringDecision(
        domain_scores=scored_domains,
        top_domains=top_domains,
        rationale=rationale,
    )


def rank_hypotheses(
    state: IncidentState,
    *,
    limit: int | None = None,
) -> list[tuple[DiagnosticDomain, float]]:
    ordered = sorted(
        state.domain_scores.items(),
        key=lambda item: (-item[1].score, item[0].value),
    )
    ranked = [(domain, score.score) for domain, score in ordered if score.score > 0.0]
    if limit is None:
        return ranked
    return ranked[:limit]