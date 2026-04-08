from __future__ import annotations

import argparse
from collections.abc import Sequence
from statistics import mean
from typing import Any

from pydantic import Field, model_validator

from .adapters import ProbeRequest, ProbeTarget
from .analysis import build_next_actions
from .config import default_threshold_config
from .errors import DependencyUnavailableError, InsufficientEvidenceError
from .models import (
    Finding,
    FindingSeverity,
    ScopeType,
    SegmentationSummary,
    SharedInputBase,
    SkillResult,
)
from .priority1 import (
    AdapterBundle,
    _add_finding,
    _build_result,
    _provider_refs,
    build_adapter_context,
    run_priority1_cli,
)

HIGH_ROAM_COUNT = 5
HIGH_ROAM_LATENCY_MS = 250.0
HIGH_PATH_JITTER_MS = 40.0
HIGH_PATH_LOSS_PCT = 5.0
HIGH_SITE_WIDE_LOSS_PCT = 10.0
HIGH_INTERNAL_PATH_LATENCY_MS = 150.0
HIGH_EXTERNAL_PATH_LATENCY_MS = 250.0
LOW_AUTH_SUCCESS_RATE_PCT = 95.0
HIGH_AUTH_TIMEOUTS = 3
DEFAULT_INTERNAL_TARGETS = [
    "default-gateway",
    "dns-service",
    "radius-service",
]


class RoamingAnalysisInput(SharedInputBase):
    @model_validator(mode="after")
    def validate_identifier(self) -> RoamingAnalysisInput:
        if not (self.client_id or self.client_mac):
            raise ValueError("client_id or client_mac is required")
        return self


class Auth8021xRadiusInput(SharedInputBase):
    @model_validator(mode="after")
    def validate_scope(self) -> Auth8021xRadiusInput:
        if not any((self.client_id, self.client_mac, self.site_id, self.ssid)):
            raise ValueError("one of client_id, client_mac, site_id, or ssid is required")
        return self


class PathProbeInput(SharedInputBase):
    source_probe_id: str | None = None
    source_role: str | None = None
    internal_targets: list[str] = Field(default_factory=lambda: list(DEFAULT_INTERNAL_TARGETS))
    external_target: str | None = None
    sample_count: int = Field(default=4, ge=1)
    probe_timeout_seconds: float = Field(default=5.0, gt=0)

    @model_validator(mode="after")
    def validate_probe_scope(self) -> PathProbeInput:
        if not (self.source_probe_id or self.site_id):
            raise ValueError("site_id or source_probe_id is required")
        if not (self.internal_targets or self.external_target):
            raise ValueError("at least one internal or external target is required")
        return self


class SegmentationPolicyInput(SharedInputBase):
    client_role: str | None = None

    @model_validator(mode="after")
    def validate_identifier(self) -> SegmentationPolicyInput:
        if not (self.client_id or self.client_mac):
            raise ValueError("client_id or client_mac is required")
        return self


def _transition_name(roam_event: Any) -> str:
    source = roam_event.from_ap_name or roam_event.from_ap_id or "unknown"
    destination = roam_event.to_ap_name or roam_event.to_ap_id or "unknown"
    return f"{source}->{destination}"


def evaluate_roaming_analysis(
    skill_input: RoamingAnalysisInput, adapters: AdapterBundle
) -> SkillResult:
    if adapters.wireless is None:
        raise DependencyUnavailableError("Wireless adapter is not configured.")

    wireless = adapters.wireless
    context = build_adapter_context(skill_input)
    session = wireless.get_client_session(
        client_id=skill_input.client_id, client_mac=skill_input.client_mac, context=context
    )
    history = wireless.get_client_history(
        client_id=skill_input.client_id, client_mac=skill_input.client_mac, context=context
    )
    roam_events = wireless.get_roam_events(
        client_id=skill_input.client_id, client_mac=skill_input.client_mac, context=context
    )

    if session is None and not history and not roam_events:
        raise InsufficientEvidenceError(
            "Unable to locate roam history or client telemetry for the requested client."
        )

    thresholds = default_threshold_config().wireless
    latencies = [event.latency_ms for event in roam_events if event.latency_ms is not None]
    failed_events = [event for event in roam_events if event.success is False]
    sticky_events = [event for event in roam_events if event.sticky_candidate]
    unique_transitions = sorted({_transition_name(event) for event in roam_events})
    average_latency = mean(latencies) if latencies else None
    resolved_session = session or (history[-1] if history else None)

    findings: list[Finding] = []
    if len(roam_events) >= HIGH_ROAM_COUNT:
        _add_finding(
            findings,
            code="EXCESSIVE_ROAM_COUNT",
            severity=FindingSeverity.WARN,
            message="The client is roaming excessively within the requested window.",
            metric="roam_count",
            value=len(roam_events),
            threshold=HIGH_ROAM_COUNT,
        )
    if average_latency is not None and average_latency >= HIGH_ROAM_LATENCY_MS:
        _add_finding(
            findings,
            code="HIGH_ROAM_LATENCY",
            severity=FindingSeverity.WARN,
            message="Average roam latency is above the expected threshold.",
            metric="avg_roam_latency_ms",
            value=average_latency,
            threshold=HIGH_ROAM_LATENCY_MS,
        )
    if failed_events:
        _add_finding(
            findings,
            code="FAILED_ROAMS",
            severity=FindingSeverity.CRITICAL if len(failed_events) >= 2 else FindingSeverity.WARN,
            message="One or more roam attempts failed during the requested window.",
            metric="failed_roams",
            value=len(failed_events),
            threshold=0,
        )
    if sticky_events or (
        resolved_session is not None
        and resolved_session.rssi_dbm is not None
        and resolved_session.rssi_dbm <= thresholds.low_rssi_dbm
        and not roam_events
        and (resolved_session.disconnect_count or 0) > 0
    ):
        _add_finding(
            findings,
            code="STICKY_CLIENT_PATTERN",
            severity=FindingSeverity.WARN,
            message="The client shows sticky-client symptoms instead of healthy roam behavior.",
        )

    evidence = {
        "roam_count": len(roam_events),
        "failed_roams": len(failed_events),
        "avg_roam_latency_ms": average_latency,
        "sticky_candidates": len(sticky_events),
        "ap_transitions": unique_transitions,
        "current_ap": resolved_session.ap_name if resolved_session is not None else None,
        "current_rssi_dbm": resolved_session.rssi_dbm if resolved_session is not None else None,
    }
    next_actions = build_next_actions(
        [
            (
                "net.ap_rf_health",
                "Validate AP RF conditions around the roam path and nearby cells.",
                bool(findings),
            ),
            (
                "net.client_health",
                "Review current client RF and retry symptoms alongside roam behavior.",
                bool(findings),
            ),
        ]
    )
    raw_refs = _provider_refs(
        wireless, "get_client_session", "get_client_history", "get_roam_events"
    )
    return _build_result(
        skill_name="net.roaming_analysis",
        scope_type=ScopeType.CLIENT,
        scope_id=skill_input.scope_id,
        ok_summary=(
            "Roam history does not show material latency, failure, or sticky-client symptoms."
        ),
        time_window=skill_input.time_window,
        evidence={
            key: value for key, value in evidence.items() if value is not None and value != []
        },
        findings=findings,
        next_actions=next_actions,
        raw_refs=raw_refs,
    )


def _failure_category_count(categories: Sequence[Any], token: str) -> int:
    total = 0
    normalized_token = token.lower()
    for category in categories:
        if normalized_token in category.category.lower():
            total += category.count
    return total


def evaluate_auth_8021x_radius(
    skill_input: Auth8021xRadiusInput, adapters: AdapterBundle
) -> SkillResult:
    if adapters.auth is None:
        raise DependencyUnavailableError("Auth adapter is not configured.")

    auth = adapters.auth
    context = build_adapter_context(skill_input)
    summary = auth.get_auth_event_summaries(
        client_id=skill_input.client_id,
        client_mac=skill_input.client_mac,
        site_id=skill_input.site_id,
        ssid=skill_input.ssid,
        context=context,
    )
    radius_servers = auth.get_radius_reachability(
        site_id=skill_input.site_id, ssid=skill_input.ssid, context=context
    )
    failure_categories = auth.retrieve_categorized_auth_failures(
        client_id=skill_input.client_id,
        client_mac=skill_input.client_mac,
        site_id=skill_input.site_id,
        ssid=skill_input.ssid,
        context=context,
    )

    if summary is None and not radius_servers and not failure_categories:
        raise InsufficientEvidenceError(
            "Unable to locate authentication telemetry for the requested scope."
        )

    thresholds = default_threshold_config().service
    effective_radius = (
        summary.radius_servers if summary is not None and summary.radius_servers else radius_servers
    )
    findings: list[Finding] = []

    if (
        summary is not None
        and summary.auth_success_rate_pct is not None
        and summary.auth_success_rate_pct < LOW_AUTH_SUCCESS_RATE_PCT
    ):
        _add_finding(
            findings,
            code="LOW_AUTH_SUCCESS_RATE",
            severity=FindingSeverity.WARN,
            message="Authentication success rate is below the expected threshold.",
            metric="auth_success_rate_pct",
            value=summary.auth_success_rate_pct,
            threshold=LOW_AUTH_SUCCESS_RATE_PCT,
        )
    if summary is not None and (summary.timeouts or 0) >= HIGH_AUTH_TIMEOUTS:
        _add_finding(
            findings,
            code="AUTH_TIMEOUTS",
            severity=FindingSeverity.CRITICAL,
            message="802.1X or RADIUS authentication is timing out repeatedly.",
            metric="timeouts",
            value=summary.timeouts,
            threshold=HIGH_AUTH_TIMEOUTS,
        )

    unreachable_servers = [
        server.server for server in effective_radius if server.reachable is False
    ]
    if unreachable_servers:
        _add_finding(
            findings,
            code="RADIUS_UNREACHABLE",
            severity=FindingSeverity.CRITICAL,
            message="One or more RADIUS servers were unreachable.",
            metric="unreachable_radius_servers",
            value=len(unreachable_servers),
            threshold=0,
        )

    high_rtt_servers = [
        server.avg_rtt_ms
        for server in effective_radius
        if server.avg_rtt_ms is not None and server.avg_rtt_ms >= thresholds.auth_timeout_ms
    ]
    if high_rtt_servers:
        _add_finding(
            findings,
            code="RADIUS_HIGH_RTT",
            severity=FindingSeverity.WARN,
            message="RADIUS round-trip time is high enough to threaten authentication reliability.",
            metric="radius_avg_rtt_ms",
            value=max(high_rtt_servers),
            threshold=thresholds.auth_timeout_ms,
        )

    credential_failures = (
        (
            summary.invalid_credentials
            if summary is not None and summary.invalid_credentials is not None
            else 0
        )
        + _failure_category_count(failure_categories, "credential")
        + _failure_category_count(failure_categories, "password")
    )
    if credential_failures > 0:
        _add_finding(
            findings,
            code="AUTH_CREDENTIAL_FAILURES",
            severity=FindingSeverity.WARN,
            message=(
                "Authentication failures are concentrated around credentials "
                "or user identity issues."
            ),
            metric="credential_failures",
            value=credential_failures,
            threshold=0,
        )

    certificate_failures = (
        (summary.cert_failures if summary is not None and summary.cert_failures is not None else 0)
        + _failure_category_count(failure_categories, "cert")
        + _failure_category_count(failure_categories, "tls")
    )
    if certificate_failures > 0:
        _add_finding(
            findings,
            code="AUTH_CERTIFICATE_FAILURES",
            severity=FindingSeverity.WARN,
            message="Recurring certificate or TLS failures were observed during authentication.",
            metric="certificate_failures",
            value=certificate_failures,
            threshold=0,
        )

    evidence = {
        "auth_summary": summary.model_dump(mode="json", exclude_none=True)
        if summary is not None
        else None,
        "radius_servers": [
            server.model_dump(mode="json", exclude_none=True) for server in effective_radius
        ],
        "failure_categories": [
            category.model_dump(mode="json", exclude_none=True) for category in failure_categories
        ],
    }
    next_actions = build_next_actions(
        [
            (
                "net.path_probe",
                "Validate service reachability to the authentication infrastructure.",
                any(
                    f.code in {"AUTH_TIMEOUTS", "RADIUS_UNREACHABLE", "RADIUS_HIGH_RTT"}
                    for f in findings
                ),
            ),
            (
                "net.segmentation_policy",
                "Review policy, NAC, or placement assumptions behind the authentication outcome.",
                any(
                    f.code
                    in {
                        "AUTH_CREDENTIAL_FAILURES",
                        "AUTH_CERTIFICATE_FAILURES",
                        "LOW_AUTH_SUCCESS_RATE",
                    }
                    for f in findings
                ),
            ),
        ]
    )
    raw_refs = _provider_refs(
        auth,
        "get_auth_event_summaries",
        "get_radius_reachability",
        "retrieve_categorized_auth_failures",
    )
    return _build_result(
        skill_name="net.auth_8021x_radius",
        scope_type=ScopeType.SERVICE,
        scope_id=skill_input.scope_id,
        ok_summary=(
            "Authentication telemetry does not show material timeout, "
            "reachability, or credential-pattern issues."
        ),
        time_window=skill_input.time_window,
        evidence={key: value for key, value in evidence.items() if value not in (None, [])},
        findings=findings,
        next_actions=next_actions,
        raw_refs=raw_refs,
    )


def _is_external_target(target: str, external_target: str | None) -> bool:
    if external_target is not None and target == external_target:
        return True
    lowered = target.lower()
    return any(token in lowered for token in ("external", "internet", "public"))


def _target_category(target: str, external_target: str | None) -> str:
    lowered = target.lower()
    if _is_external_target(target, external_target):
        return "external"
    if "dns" in lowered:
        return "dns"
    if "dhcp" in lowered:
        return "dhcp"
    if "radius" in lowered or "auth" in lowered:
        return "auth"
    if "gateway" in lowered:
        return "gateway"
    return "internal"


def _degraded_probe(result: Any, *, external: bool) -> bool:
    latency_threshold = HIGH_EXTERNAL_PATH_LATENCY_MS if external else HIGH_INTERNAL_PATH_LATENCY_MS
    return bool(
        (result.loss_pct is not None and result.loss_pct >= HIGH_PATH_LOSS_PCT)
        or (result.jitter_ms is not None and result.jitter_ms >= HIGH_PATH_JITTER_MS)
        or (result.avg_latency_ms is not None and result.avg_latency_ms >= latency_threshold)
        or (result.timeout_count or 0) > 0
    )


def evaluate_path_probe(skill_input: PathProbeInput, adapters: AdapterBundle) -> SkillResult:
    if adapters.probe is None:
        raise DependencyUnavailableError("Probe adapter is not configured.")

    probe = adapters.probe
    context = build_adapter_context(skill_input)
    targets = [ProbeTarget(target=target) for target in skill_input.internal_targets]
    if skill_input.external_target is not None:
        targets.append(ProbeTarget(target=skill_input.external_target))
    request = ProbeRequest(
        source_probe_id=skill_input.source_probe_id or skill_input.site_id or "default-probe",
        source_role=skill_input.source_role,
        targets=targets,
        sample_count=skill_input.sample_count,
        timeout_seconds=skill_input.probe_timeout_seconds,
    )
    results = probe.run_path_probes(request=request, context=context)
    if not results:
        raise InsufficientEvidenceError(
            "Unable to collect path probe telemetry for the requested scope."
        )

    internal_results = [
        result
        for result in results
        if not _is_external_target(result.target or "", skill_input.external_target)
    ]
    external_results = [
        result
        for result in results
        if _is_external_target(result.target or "", skill_input.external_target)
    ]
    internal_degraded = [
        result for result in internal_results if _degraded_probe(result, external=False)
    ]
    external_degraded = [
        result for result in external_results if _degraded_probe(result, external=True)
    ]
    findings: list[Finding] = []

    for category, code in (
        ("dns", "DNS_PATH_DEGRADATION"),
        ("dhcp", "DHCP_PATH_DEGRADATION"),
        ("auth", "RADIUS_PATH_DEGRADATION"),
    ):
        category_results = [
            result
            for result in internal_degraded
            if _target_category(result.target or "", skill_input.external_target) == category
        ]
        if category_results:
            worst_result = max(
                category_results,
                key=lambda item: max(
                    item.loss_pct or 0.0, item.avg_latency_ms or 0.0, item.jitter_ms or 0.0
                ),
            )
            _add_finding(
                findings,
                code=code,
                severity=FindingSeverity.WARN,
                message=f"{category.upper()} path probes are degraded for at least one target.",
                metric="target",
                value=worst_result.target,
                threshold="healthy",
            )

    if (
        internal_degraded
        and len(internal_degraded) == len(internal_results)
        and any((result.loss_pct or 0.0) >= HIGH_SITE_WIDE_LOSS_PCT for result in internal_degraded)
    ):
        _add_finding(
            findings,
            code="SITE_WIDE_PATH_LOSS",
            severity=FindingSeverity.CRITICAL,
            message="All sampled internal paths show substantial loss or timeout behavior.",
            metric="degraded_internal_targets",
            value=len(internal_degraded),
            threshold=len(internal_results),
        )
    elif internal_degraded:
        _add_finding(
            findings,
            code="INTERNAL_SERVICE_DEGRADATION",
            severity=FindingSeverity.WARN,
            message=(
                "One or more internal probe targets show elevated latency, "
                "jitter, loss, or timeouts."
            ),
            metric="degraded_internal_targets",
            value=len(internal_degraded),
            threshold=0,
        )

    if external_degraded and not internal_degraded:
        _add_finding(
            findings,
            code="WAN_EXTERNAL_DEGRADATION",
            severity=FindingSeverity.WARN,
            message=(
                "External path probes are degraded while sampled internal targets remain healthy."
            ),
        )

    evidence = {
        "source_probe_id": request.source_probe_id,
        "source_role": request.source_role,
        "results": [result.model_dump(mode="json", exclude_none=True) for result in results],
        "degraded_internal_targets": [result.target for result in internal_degraded],
        "degraded_external_targets": [result.target for result in external_degraded],
    }
    next_actions = build_next_actions(
        [
            (
                "net.dns_latency",
                "DNS targets look unhealthy in the path-probe results.",
                any(f.code == "DNS_PATH_DEGRADATION" for f in findings),
            ),
            (
                "net.dhcp_path",
                "DHCP-adjacent targets look degraded in the path-probe results.",
                any(f.code == "DHCP_PATH_DEGRADATION" for f in findings),
            ),
            (
                "net.auth_8021x_radius",
                "Authentication-path targets look degraded in the path-probe results.",
                any(f.code == "RADIUS_PATH_DEGRADATION" for f in findings),
            ),
            (
                "net.client_health",
                (
                    "Wireless-origin path probes degraded and client-side "
                    "validation may still be required."
                ),
                bool(internal_degraded)
                and (skill_input.source_role or "").lower() in {"wireless", "wifi", "client"},
            ),
            (
                "net.ap_rf_health",
                "Wireless-origin path probes degraded and AP RF conditions may still need review.",
                bool(internal_degraded)
                and (skill_input.source_role or "").lower() in {"wireless", "wifi", "ap"},
            ),
            (
                "net.topology_map",
                "Path degradation persists and topology context can narrow the failing segment.",
                bool(internal_degraded),
            ),
        ]
    )
    raw_refs = _provider_refs(probe, "run_path_probes")
    return _build_result(
        skill_name="net.path_probe",
        scope_type=ScopeType.PATH,
        scope_id=request.source_probe_id,
        ok_summary=(
            "Sampled path probes do not show material latency, jitter, loss, or timeout symptoms."
        ),
        time_window=skill_input.time_window,
        evidence=evidence,
        findings=findings,
        next_actions=next_actions,
        raw_refs=raw_refs,
    )


def evaluate_segmentation_policy(
    skill_input: SegmentationPolicyInput, adapters: AdapterBundle
) -> SkillResult:
    if adapters.inventory is None:
        raise DependencyUnavailableError("Inventory adapter is not configured.")

    context = build_adapter_context(skill_input)
    wireless = adapters.wireless
    dhcp = adapters.dhcp
    inventory = adapters.inventory
    session = None
    if wireless is not None:
        session = wireless.get_client_session(
            client_id=skill_input.client_id, client_mac=skill_input.client_mac, context=context
        )
    dhcp_summaries = []
    if dhcp is not None:
        dhcp_summaries = dhcp.get_dhcp_transaction_summaries(
            client_id=skill_input.client_id,
            client_mac=skill_input.client_mac,
            site_id=skill_input.site_id,
            ssid=skill_input.ssid or (session.ssid if session is not None else None),
            vlan_id=int(skill_input.vlan_id) if skill_input.vlan_id is not None else None,
            context=context,
        )

    observed_site_id = (
        skill_input.site_id
        or (session.site_id if session is not None else None)
        or (dhcp_summaries[0].site_id if dhcp_summaries else None)
    )
    observed_ssid = (
        skill_input.ssid
        or (session.ssid if session is not None else None)
        or (dhcp_summaries[0].ssid if dhcp_summaries else None)
    )
    expected_mapping = inventory.get_expected_policy_mappings(
        client_id=skill_input.client_id,
        client_mac=skill_input.client_mac,
        site_id=observed_site_id,
        ssid=observed_ssid,
        context=context,
    )
    role_mapping = None
    if (
        observed_site_id is not None
        and observed_ssid is not None
        and skill_input.client_role is not None
    ):
        role_mapping = inventory.get_expected_vlan_by_ssid_client_role(
            site_id=observed_site_id,
            ssid=observed_ssid,
            client_role=skill_input.client_role,
            context=context,
        )

    observed_dhcp = dhcp_summaries[0] if dhcp_summaries else None
    if (
        session is None
        and observed_dhcp is None
        and expected_mapping is None
        and role_mapping is None
    ):
        raise InsufficientEvidenceError(
            "Unable to locate observed or expected segmentation data for the requested client."
        )

    expected_vlan = None
    expected_policy_group = None
    expected_gateway = None
    if expected_mapping is not None:
        expected_vlan = expected_mapping.expected_vlan
        expected_policy_group = expected_mapping.expected_policy_group
        expected_gateway = expected_mapping.expected_gateway
    if role_mapping is not None:
        expected_vlan = expected_vlan if expected_vlan is not None else role_mapping.expected_vlan
        expected_policy_group = (
            expected_policy_group
            if expected_policy_group is not None
            else role_mapping.expected_policy_group
        )
        expected_gateway = (
            expected_gateway if expected_gateway is not None else role_mapping.expected_gateway
        )

    observed_policy_group = observed_dhcp.scope_name if observed_dhcp is not None else None
    observed_gateway = observed_dhcp.relay_ip if observed_dhcp is not None else None
    segmentation = SegmentationSummary(
        client_id=skill_input.client_id,
        client_mac=skill_input.client_mac,
        observed_ssid=observed_ssid,
        observed_vlan=observed_dhcp.vlan_id if observed_dhcp is not None else None,
        expected_vlan=expected_vlan,
        policy_group=observed_policy_group,
        expected_policy_group=expected_policy_group,
        dhcp_scope=observed_dhcp.scope_name if observed_dhcp is not None else None,
        default_gateway=observed_gateway,
        expected_default_gateway=expected_gateway,
    )

    findings: list[Finding] = []
    if (
        segmentation.observed_vlan is not None
        and segmentation.expected_vlan is not None
        and segmentation.observed_vlan != segmentation.expected_vlan
    ):
        _add_finding(
            findings,
            code="VLAN_MISMATCH",
            severity=FindingSeverity.WARN,
            message="Observed client VLAN does not match the expected policy mapping.",
            metric="observed_vlan",
            value=segmentation.observed_vlan,
            threshold=segmentation.expected_vlan,
        )
    if (
        segmentation.policy_group is not None
        and segmentation.expected_policy_group is not None
        and segmentation.policy_group != segmentation.expected_policy_group
    ):
        _add_finding(
            findings,
            code="POLICY_GROUP_MISMATCH",
            severity=FindingSeverity.WARN,
            message=(
                "Observed DHCP scope or policy group does not match the expected policy mapping."
            ),
            metric="policy_group",
            value=segmentation.policy_group,
            threshold=segmentation.expected_policy_group,
        )
    if (
        segmentation.default_gateway is not None
        and segmentation.expected_default_gateway is not None
        and segmentation.default_gateway != segmentation.expected_default_gateway
    ):
        _add_finding(
            findings,
            code="GATEWAY_ALIGNMENT_MISMATCH",
            severity=FindingSeverity.WARN,
            message="Observed gateway or relay alignment does not match the expected mapping.",
            metric="default_gateway",
            value=segmentation.default_gateway,
            threshold=segmentation.expected_default_gateway,
        )

    evidence = segmentation.model_dump(mode="json", exclude_none=True)
    if expected_mapping is not None:
        evidence["expected_policy_mapping"] = expected_mapping.model_dump(
            mode="json", exclude_none=True
        )
    if role_mapping is not None:
        evidence["role_policy_mapping"] = role_mapping.model_dump(mode="json", exclude_none=True)

    next_actions = build_next_actions(
        [
            (
                "net.auth_8021x_radius",
                "Review authentication or NAC policy inputs behind the placement result.",
                bool(findings),
            ),
            (
                "net.dhcp_path",
                "Validate DHCP scope and gateway alignment for the observed client placement.",
                any(
                    f.code
                    in {"VLAN_MISMATCH", "GATEWAY_ALIGNMENT_MISMATCH", "POLICY_GROUP_MISMATCH"}
                    for f in findings
                ),
            ),
            (
                "net.subnet_inventory",
                "Inventory the observed subnet when placement and gateway evidence disagree.",
                any(
                    f.code in {"VLAN_MISMATCH", "GATEWAY_ALIGNMENT_MISMATCH"}
                    for f in findings
                ),
            ),
            (
                "net.topology_map",
                (
                    "Map the local path when segmentation evidence suggests the "
                    "client is in the wrong place."
                ),
                bool(findings),
            ),
        ]
    )
    raw_refs = []
    if wireless is not None:
        raw_refs.extend(_provider_refs(wireless, "get_client_session"))
    if dhcp is not None:
        raw_refs.extend(_provider_refs(dhcp, "get_dhcp_transaction_summaries"))
    raw_refs.extend(_provider_refs(inventory, "get_expected_policy_mappings"))
    if role_mapping is not None:
        raw_refs.extend(_provider_refs(inventory, "get_expected_vlan_by_ssid_client_role"))

    return _build_result(
        skill_name="net.segmentation_policy",
        scope_type=ScopeType.VLAN,
        scope_id=skill_input.scope_id,
        ok_summary="Observed client placement matches the expected VLAN and policy mapping.",
        time_window=skill_input.time_window,
        evidence=evidence,
        findings=findings,
        next_actions=next_actions,
        raw_refs=raw_refs,
    )


def configure_path_probe_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source-probe-id")
    parser.add_argument("--source-role")
    parser.add_argument("--target", action="append", dest="internal_targets")
    parser.add_argument("--external-target")
    parser.add_argument("--sample-count", type=int)
    parser.add_argument("--probe-timeout-seconds", type=float)


def configure_segmentation_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--client-role")


def main_roaming_analysis(argv: Sequence[str] | None = None) -> int:
    return run_priority1_cli(
        argv=argv,
        skill_name="net.roaming_analysis",
        description="Analyze Wi-Fi roam history, failures, latency, and sticky-client patterns.",
        scope_type=ScopeType.CLIENT,
        input_model=RoamingAnalysisInput,
        handler=evaluate_roaming_analysis,
    )


def main_auth_8021x_radius(argv: Sequence[str] | None = None) -> int:
    return run_priority1_cli(
        argv=argv,
        skill_name="net.auth_8021x_radius",
        description="Assess 802.1X success rate, RADIUS reachability, and auth failure patterns.",
        scope_type=ScopeType.SERVICE,
        input_model=Auth8021xRadiusInput,
        handler=evaluate_auth_8021x_radius,
    )


def main_path_probe(argv: Sequence[str] | None = None) -> int:
    return run_priority1_cli(
        argv=argv,
        skill_name="net.path_probe",
        description=(
            "Measure internal and optional external path quality between representative targets."
        ),
        scope_type=ScopeType.PATH,
        input_model=PathProbeInput,
        handler=evaluate_path_probe,
        configure_parser=configure_path_probe_parser,
    )


def main_segmentation_policy(argv: Sequence[str] | None = None) -> int:
    return run_priority1_cli(
        argv=argv,
        skill_name="net.segmentation_policy",
        description="Compare observed client placement against expected VLAN and policy mappings.",
        scope_type=ScopeType.VLAN,
        input_model=SegmentationPolicyInput,
        handler=evaluate_segmentation_policy,
        configure_parser=configure_segmentation_parser,
    )
