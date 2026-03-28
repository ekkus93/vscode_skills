from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import mean
from typing import Any, Callable, Sequence, TypeVar

from pydantic import Field, ValidationError, model_validator

from .adapters import (
    AdapterContext,
    AuthAdapter,
    InventoryConfigAdapter,
    ProbeAdapter,
    StubAuthAdapter,
    StubDhcpAdapter,
    StubDnsAdapter,
    StubInventoryConfigAdapter,
    StubProbeAdapter,
    StubSwitchAdapter,
    StubSyslogEventAdapter,
    StubWirelessControllerAdapter,
    SwitchAdapter,
    SyslogEventAdapter,
    WirelessControllerAdapter,
    DhcpAdapter,
    DnsAdapter,
    load_stub_fixture_file,
)
from .analysis import (
    build_next_actions,
    compare_to_baseline,
    compare_to_threshold,
    confidence_from_evidence,
)
from .cli import build_common_parser
from .config import default_threshold_config
from .errors import (
    BadInputError,
    DependencyTimeoutError,
    DependencyUnavailableError,
    InsufficientEvidenceError,
    NettoolsError,
    error_to_skill_result,
)
from .logging import StructuredLogger, configure_logging
from .models import (
    AccessPointState,
    ClientSession,
    Confidence,
    DhcpSummary,
    DnsSummary,
    Finding,
    FindingSeverity,
    NextAction,
    ScopeType,
    SharedInputBase,
    SkillResult,
    StpSummary,
    SwitchPortState,
)

HIGH_PACKET_LOSS_PCT = 2.0
HIGH_ROAM_COUNT = 5
HIGH_RECONNECT_COUNT = 3
HIGH_AP_CLIENT_LOAD = 35
HIGH_RADIO_RESETS = 2
HIGH_INTERFERENCE_SCORE = 70.0
HIGH_DNS_TIMEOUT_PCT = 10.0
HIGH_DHCP_TIMEOUTS = 3
HIGH_SCOPE_UTILIZATION_PCT = 90.0
HIGH_UPLINK_FLAPS = 3
HIGH_MAC_FLAP_EVENTS = 5

DEFAULT_DNS_QUERIES = [
    "example.com",
    "microsoft.com",
    "internal.service.local",
]

SkillInputType = TypeVar("SkillInputType", bound=SharedInputBase)


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


@dataclass
class AdapterBundle:
    wireless: WirelessControllerAdapter | None = None
    switch: SwitchAdapter | None = None
    dhcp: DhcpAdapter | None = None
    dns: DnsAdapter | None = None
    auth: AuthAdapter | None = None
    probe: ProbeAdapter | None = None
    inventory: InventoryConfigAdapter | None = None
    syslog: SyslogEventAdapter | None = None


class ClientHealthInput(SharedInputBase):
    @model_validator(mode="after")
    def validate_identifier(self) -> "ClientHealthInput":
        if not (self.client_id or self.client_mac):
            raise ValueError("client_id or client_mac is required")
        return self


class ApRfHealthInput(SharedInputBase):
    @model_validator(mode="after")
    def validate_ap_identifier(self) -> "ApRfHealthInput":
        if not (self.ap_id or self.ap_name):
            raise ValueError("ap_id or ap_name is required")
        return self


class DhcpPathInput(SharedInputBase):
    @model_validator(mode="after")
    def validate_scope(self) -> "DhcpPathInput":
        if not any((self.client_id, self.client_mac, self.ssid, self.vlan_id, self.site_id)):
            raise ValueError("one of client_id, client_mac, ssid, vlan_id, or site_id is required")
        return self


class DnsLatencyInput(SharedInputBase):
    queries: list[str] = Field(default_factory=lambda: list(DEFAULT_DNS_QUERIES))


class ApUplinkHealthInput(SharedInputBase):
    @model_validator(mode="after")
    def validate_scope(self) -> "ApUplinkHealthInput":
        if not (self.ap_id or self.ap_name or (self.switch_id and self.switch_port)):
            raise ValueError("ap_id or ap_name is required unless switch_id and switch_port are both provided")
        return self


class StpLoopAnomalyInput(SharedInputBase):
    pass


def build_stub_adapter_bundle(fixtures: dict[str, Any]) -> AdapterBundle:
    return AdapterBundle(
        wireless=StubWirelessControllerAdapter(fixtures=fixtures),
        switch=StubSwitchAdapter(fixtures=fixtures),
        dhcp=StubDhcpAdapter(fixtures=fixtures),
        dns=StubDnsAdapter(fixtures=fixtures),
        auth=StubAuthAdapter(fixtures=fixtures),
        probe=StubProbeAdapter(fixtures=fixtures),
        inventory=StubInventoryConfigAdapter(fixtures=fixtures),
        syslog=StubSyslogEventAdapter(fixtures=fixtures),
    )


def load_stub_adapter_bundle(fixture_file: str | None) -> AdapterBundle:
    resolved_fixture_file = fixture_file or os.environ.get("NETTOOLS_FIXTURE_FILE")
    if not resolved_fixture_file:
        raise DependencyUnavailableError(
            "No fixture file or provider implementation is configured for this NETTOOLS skill.",
            raw_refs=["runtime:missing_fixture_file"],
        )
    fixtures = load_stub_fixture_file(resolved_fixture_file)
    return build_stub_adapter_bundle(fixtures)


def build_adapter_context(shared_input: SharedInputBase) -> AdapterContext:
    return AdapterContext(
        time_window=shared_input.time_window,
        include_raw=shared_input.include_raw,
    )


def _provider_refs(adapter: Any, *operations: str) -> list[str]:
    provider_name = getattr(adapter, "provider_name", "adapter")
    return [f"adapter:{provider_name}:{operation}" for operation in operations]


def _status_from_findings(findings: Sequence[Finding]) -> str:
    if any(finding.severity == FindingSeverity.CRITICAL for finding in findings):
        return "fail"
    if any(finding.severity == FindingSeverity.WARN for finding in findings):
        return "warn"
    return "ok"


def _summary_from_findings(ok_summary: str, findings: Sequence[Finding]) -> str:
    if not findings:
        return ok_summary
    primary = findings[0]
    if len(findings) == 1:
        return primary.message
    return f"{primary.message} ({len(findings)} findings total)."


def _build_result(
    *,
    skill_name: str,
    scope_type: ScopeType,
    scope_id: str,
    ok_summary: str,
    time_window: Any,
    evidence: dict[str, Any],
    findings: list[Finding],
    next_actions: list[NextAction],
    raw_refs: list[str],
    baseline_present: bool = False,
    partial_failure_count: int = 0,
) -> SkillResult:
    status = _status_from_findings(findings)
    return SkillResult(
        status=status,
        skill_name=skill_name,
        scope_type=scope_type,
        scope_id=scope_id,
        summary=_summary_from_findings(ok_summary, findings),
        confidence=confidence_from_evidence(
            evidence_count=len(evidence),
            source_count=len(set(raw_refs)),
            partial_failure_count=partial_failure_count,
            baseline_present=baseline_present,
        ),
        observed_at=utc_now(),
        time_window=time_window,
        evidence=evidence,
        findings=findings,
        next_actions=next_actions,
        raw_refs=raw_refs,
    )


def _add_finding(
    findings: list[Finding],
    *,
    code: str,
    severity: FindingSeverity,
    message: str,
    metric: str | None = None,
    value: Any | None = None,
    threshold: Any | None = None,
) -> None:
    findings.append(
        Finding(
            code=code,
            severity=severity,
            message=message,
            metric=metric,
            value=value,
            threshold=threshold,
        )
    )


def evaluate_client_health(skill_input: ClientHealthInput, adapters: AdapterBundle) -> SkillResult:
    if adapters.wireless is None:
        raise DependencyUnavailableError("Wireless adapter is not configured.")

    context = build_adapter_context(skill_input)
    wireless = adapters.wireless
    session = wireless.get_client_session(client_id=skill_input.client_id, client_mac=skill_input.client_mac, context=context)
    history = wireless.get_client_history(client_id=skill_input.client_id, client_mac=skill_input.client_mac, context=context)
    roam_events = wireless.get_roam_events(client_id=skill_input.client_id, client_mac=skill_input.client_mac, context=context)

    if session is None and not history:
        raise InsufficientEvidenceError("Unable to locate client session data for the requested client.")

    thresholds = default_threshold_config().wireless
    resolved_session = session or history[0]
    ap_state = None
    neighbors: list[AccessPointState] = []
    if resolved_session.ap_id or resolved_session.ap_name:
        ap_state = wireless.get_ap_state(ap_id=resolved_session.ap_id, ap_name=resolved_session.ap_name, context=context)
        neighbors = wireless.get_neighboring_ap_data(ap_id=resolved_session.ap_id, ap_name=resolved_session.ap_name, context=context)

    findings: list[Finding] = []
    evidence = {
        "rssi_dbm": resolved_session.rssi_dbm,
        "snr_db": resolved_session.snr_db,
        "retry_pct": resolved_session.retry_pct,
        "packet_loss_pct": resolved_session.packet_loss_pct,
        "connected_ap": resolved_session.ap_name or (ap_state.ap_name if ap_state else None),
        "channel": resolved_session.channel,
        "band": resolved_session.band,
        "recent_roams": len(roam_events),
        "disconnect_count": resolved_session.disconnect_count,
        "reassociation_count": resolved_session.reassociation_count,
    }

    if resolved_session.rssi_dbm is not None and compare_to_threshold("rssi_dbm", resolved_session.rssi_dbm, thresholds.low_rssi_dbm, direction="lte").breached:
        _add_finding(
            findings,
            code="LOW_RSSI",
            severity=FindingSeverity.WARN,
            message="Client RSSI is below the configured threshold.",
            metric="rssi_dbm",
            value=resolved_session.rssi_dbm,
            threshold=thresholds.low_rssi_dbm,
        )
    if resolved_session.snr_db is not None and compare_to_threshold("snr_db", resolved_session.snr_db, thresholds.low_snr_db, direction="lte").breached:
        _add_finding(
            findings,
            code="LOW_SNR",
            severity=FindingSeverity.WARN,
            message="Client SNR is below the configured threshold.",
            metric="snr_db",
            value=resolved_session.snr_db,
            threshold=thresholds.low_snr_db,
        )
    if resolved_session.retry_pct is not None and compare_to_threshold("retry_pct", resolved_session.retry_pct, thresholds.high_retry_pct, direction="gte").breached:
        _add_finding(
            findings,
            code="HIGH_RETRY_RATE",
            severity=FindingSeverity.WARN,
            message="Client retry rate exceeded the configured threshold.",
            metric="retry_pct",
            value=resolved_session.retry_pct,
            threshold=thresholds.high_retry_pct,
        )
    if resolved_session.packet_loss_pct is not None and compare_to_threshold("packet_loss_pct", resolved_session.packet_loss_pct, HIGH_PACKET_LOSS_PCT, direction="gte").breached:
        _add_finding(
            findings,
            code="HIGH_PACKET_LOSS",
            severity=FindingSeverity.WARN,
            message="Client packet loss is elevated.",
            metric="packet_loss_pct",
            value=resolved_session.packet_loss_pct,
            threshold=HIGH_PACKET_LOSS_PCT,
        )

    roam_count = resolved_session.roam_count if resolved_session.roam_count is not None else len(roam_events)
    if roam_count and roam_count >= HIGH_ROAM_COUNT:
        _add_finding(
            findings,
            code="EXCESSIVE_ROAMING",
            severity=FindingSeverity.WARN,
            message="The client is roaming frequently within the requested time window.",
            metric="roam_count",
            value=roam_count,
            threshold=HIGH_ROAM_COUNT,
        )
    reconnect_cycles = (resolved_session.disconnect_count or 0) + (resolved_session.reassociation_count or 0)
    if reconnect_cycles >= HIGH_RECONNECT_COUNT:
        _add_finding(
            findings,
            code="RAPID_RECONNECTS",
            severity=FindingSeverity.WARN,
            message="The client is repeatedly disconnecting or re-associating.",
            metric="reconnect_events",
            value=reconnect_cycles,
            threshold=HIGH_RECONNECT_COUNT,
        )
    if neighbors and resolved_session.rssi_dbm is not None and resolved_session.rssi_dbm <= thresholds.low_rssi_dbm and roam_count == 0:
        _add_finding(
            findings,
            code="STICKY_CLIENT",
            severity=FindingSeverity.WARN,
            message="The client appears sticky on a poor AP despite neighboring AP visibility.",
        )

    next_actions = build_next_actions(
        [
            ("net.ap_rf_health", "RF indicators on the current AP should be validated.", bool(findings)),
            ("net.roaming_analysis", "Roam activity or sticky behavior needs deeper review.", any(f.code in {"EXCESSIVE_ROAMING", "STICKY_CLIENT"} for f in findings)),
            ("net.ap_uplink_health", "Client symptoms could also reflect AP uplink issues.", any(f.code in {"HIGH_RETRY_RATE", "HIGH_PACKET_LOSS"} for f in findings)),
        ]
    )
    raw_refs = _provider_refs(wireless, "get_client_session", "get_client_history", "get_roam_events")
    if ap_state is not None:
        raw_refs.extend(_provider_refs(wireless, "get_ap_state", "get_neighboring_ap_data"))

    return _build_result(
        skill_name="net.client_health",
        scope_type=ScopeType.CLIENT,
        scope_id=skill_input.scope_id,
        ok_summary="Client session does not show material RF or retry issues.",
        time_window=skill_input.time_window,
        evidence={key: value for key, value in evidence.items() if value is not None},
        findings=findings,
        next_actions=next_actions,
        raw_refs=raw_refs,
    )


def _iter_radios(ap_state: AccessPointState) -> list[tuple[str, Any]]:
    radios = []
    for radio_name in ("radio_2g", "radio_5g", "radio_6g"):
        radio = getattr(ap_state, radio_name)
        if radio is not None:
            radios.append((radio_name, radio))
    return radios


def evaluate_ap_rf_health(skill_input: ApRfHealthInput, adapters: AdapterBundle) -> SkillResult:
    if adapters.wireless is None:
        raise DependencyUnavailableError("Wireless adapter is not configured.")
    wireless = adapters.wireless
    context = build_adapter_context(skill_input)
    ap_state = wireless.get_ap_state(ap_id=skill_input.ap_id, ap_name=skill_input.ap_name, context=context)
    if ap_state is None:
        raise InsufficientEvidenceError("Unable to locate AP state for the requested AP.")
    neighbors = wireless.get_neighboring_ap_data(ap_id=skill_input.ap_id or ap_state.ap_id, ap_name=skill_input.ap_name or ap_state.ap_name, context=context)

    thresholds = default_threshold_config().wireless
    findings: list[Finding] = []
    radio_evidence: dict[str, Any] = {}

    for radio_name, radio in _iter_radios(ap_state):
        radio_evidence[radio_name] = radio.model_dump(mode="json", exclude_none=True)
        if radio.utilization_pct is not None and compare_to_threshold("utilization_pct", radio.utilization_pct, thresholds.high_channel_utilization_pct, direction="gte").breached:
            _add_finding(
                findings,
                code="HIGH_CHANNEL_UTILIZATION",
                severity=FindingSeverity.WARN,
                message=f"{radio_name} channel utilization is above threshold.",
                metric=f"{radio_name}.utilization_pct",
                value=radio.utilization_pct,
                threshold=thresholds.high_channel_utilization_pct,
            )
        if radio.client_count is not None and radio.client_count >= HIGH_AP_CLIENT_LOAD:
            _add_finding(
                findings,
                code="HIGH_AP_CLIENT_LOAD",
                severity=FindingSeverity.WARN,
                message=f"{radio_name} is serving an unusually high client load.",
                metric=f"{radio_name}.client_count",
                value=radio.client_count,
                threshold=HIGH_AP_CLIENT_LOAD,
            )
        if radio.width_mhz is not None:
            is_24 = radio.band == "2.4GHz" or (radio.channel is not None and radio.channel <= 14)
            if is_24 and radio.width_mhz > 20:
                _add_finding(
                    findings,
                    code="UNSUITABLE_CHANNEL_WIDTH",
                    severity=FindingSeverity.WARN,
                    message=f"{radio_name} channel width is too wide for dense 2.4 GHz use.",
                    metric=f"{radio_name}.width_mhz",
                    value=radio.width_mhz,
                    threshold=20,
                )
        if radio.reset_count is not None and radio.reset_count >= HIGH_RADIO_RESETS:
            _add_finding(
                findings,
                code="RADIO_RESETS",
                severity=FindingSeverity.WARN,
                message=f"{radio_name} shows repeated radio resets.",
                metric=f"{radio_name}.reset_count",
                value=radio.reset_count,
                threshold=HIGH_RADIO_RESETS,
            )
        if radio.interference_score is not None and radio.interference_score >= HIGH_INTERFERENCE_SCORE:
            _add_finding(
                findings,
                code="POTENTIAL_CO_CHANNEL_INTERFERENCE",
                severity=FindingSeverity.WARN,
                message=f"{radio_name} indicates significant interference or overlap.",
                metric=f"{radio_name}.interference_score",
                value=radio.interference_score,
                threshold=HIGH_INTERFERENCE_SCORE,
            )

    if ap_state.radio_resets_last_24h is not None and ap_state.radio_resets_last_24h >= HIGH_RADIO_RESETS:
        _add_finding(
            findings,
            code="RADIO_RESETS",
            severity=FindingSeverity.WARN,
            message="The AP has experienced repeated radio resets in the last 24 hours.",
            metric="radio_resets_last_24h",
            value=ap_state.radio_resets_last_24h,
            threshold=HIGH_RADIO_RESETS,
        )
    if neighbors and len(neighbors) >= 3 and any(f.code == "HIGH_CHANNEL_UTILIZATION" for f in findings):
        _add_finding(
            findings,
            code="POTENTIAL_CO_CHANNEL_INTERFERENCE",
            severity=FindingSeverity.WARN,
            message="Neighbor density and utilization suggest possible co-channel contention.",
        )

    next_actions = build_next_actions(
        [
            ("net.client_health", "Validate whether affected clients show session-level symptoms.", bool(findings)),
            ("net.ap_uplink_health", "Confirm the AP uplink is clean before attributing symptoms to RF.", any(f.code in {"RADIO_RESETS", "HIGH_CHANNEL_UTILIZATION"} for f in findings)),
        ]
    )
    raw_refs = _provider_refs(wireless, "get_ap_state", "get_neighboring_ap_data")
    evidence = {
        "ap_id": ap_state.ap_id,
        "ap_name": ap_state.ap_name,
        "client_count": ap_state.client_count,
        "radio_resets_last_24h": ap_state.radio_resets_last_24h,
        "neighbor_count": len(neighbors),
        **radio_evidence,
    }
    return _build_result(
        skill_name="net.ap_rf_health",
        scope_type=ScopeType.AP,
        scope_id=skill_input.scope_id,
        ok_summary="AP radios do not show material utilization or instability issues.",
        time_window=skill_input.time_window,
        evidence={key: value for key, value in evidence.items() if value is not None},
        findings=findings,
        next_actions=next_actions,
        raw_refs=raw_refs,
    )


def evaluate_dhcp_path(skill_input: DhcpPathInput, adapters: AdapterBundle) -> SkillResult:
    if adapters.dhcp is None:
        raise DependencyUnavailableError("DHCP adapter is not configured.")
    dhcp = adapters.dhcp
    context = build_adapter_context(skill_input)
    summaries = dhcp.get_dhcp_transaction_summaries(
        client_id=skill_input.client_id,
        client_mac=skill_input.client_mac,
        site_id=skill_input.site_id,
        ssid=skill_input.ssid,
        vlan_id=int(skill_input.vlan_id) if skill_input.vlan_id is not None else None,
        context=context,
    )
    scope_summaries = dhcp.get_scope_utilization(
        site_id=skill_input.site_id,
        vlan_id=int(skill_input.vlan_id) if skill_input.vlan_id is not None else None,
        scope_name=None,
        context=context,
    )
    relay_metadata = dhcp.get_relay_path_metadata(
        site_id=skill_input.site_id,
        vlan_id=int(skill_input.vlan_id) if skill_input.vlan_id is not None else None,
        client_mac=skill_input.client_mac,
        context=context,
    )

    if not summaries and not scope_summaries:
        raise InsufficientEvidenceError("Unable to locate DHCP telemetry for the requested scope.")

    summary = summaries[0] if summaries else scope_summaries[0]
    thresholds = default_threshold_config().service
    findings: list[Finding] = []
    evidence = summary.model_dump(mode="json", exclude_none=True)
    if relay_metadata:
        evidence["relay_path"] = [item.model_dump(mode="json", exclude_none=True) for item in relay_metadata]

    if summary.avg_offer_latency_ms is not None and compare_to_threshold("avg_offer_latency_ms", summary.avg_offer_latency_ms, thresholds.high_dhcp_latency_ms, direction="gte").breached:
        _add_finding(
            findings,
            code="HIGH_DHCP_OFFER_LATENCY",
            severity=FindingSeverity.WARN,
            message="DHCP discover-to-offer latency is elevated.",
            metric="avg_offer_latency_ms",
            value=summary.avg_offer_latency_ms,
            threshold=thresholds.high_dhcp_latency_ms,
        )
    if summary.avg_ack_latency_ms is not None and compare_to_threshold("avg_ack_latency_ms", summary.avg_ack_latency_ms, thresholds.high_dhcp_latency_ms, direction="gte").breached:
        _add_finding(
            findings,
            code="HIGH_DHCP_ACK_LATENCY",
            severity=FindingSeverity.WARN,
            message="DHCP request-to-ack latency is elevated.",
            metric="avg_ack_latency_ms",
            value=summary.avg_ack_latency_ms,
            threshold=thresholds.high_dhcp_latency_ms,
        )
    if (summary.timeouts or 0) >= HIGH_DHCP_TIMEOUTS:
        _add_finding(
            findings,
            code="DHCP_TIMEOUTS",
            severity=FindingSeverity.CRITICAL,
            message="DHCP transactions are timing out repeatedly.",
            metric="timeouts",
            value=summary.timeouts,
            threshold=HIGH_DHCP_TIMEOUTS,
        )
    if (summary.missing_acks or 0) > 0:
        _add_finding(
            findings,
            code="MISSING_DHCP_ACK",
            severity=FindingSeverity.CRITICAL,
            message="DHCP ACKs are missing for some transactions.",
            metric="missing_acks",
            value=summary.missing_acks,
            threshold=0,
        )
    if summary.scope_utilization_pct is not None and compare_to_threshold("scope_utilization_pct", summary.scope_utilization_pct, HIGH_SCOPE_UTILIZATION_PCT, direction="gte").breached:
        _add_finding(
            findings,
            code="SCOPE_UTILIZATION_HIGH",
            severity=FindingSeverity.WARN,
            message="The DHCP scope is close to exhaustion.",
            metric="scope_utilization_pct",
            value=summary.scope_utilization_pct,
            threshold=HIGH_SCOPE_UTILIZATION_PCT,
        )
    if relay_metadata and summary.relay_ip and relay_metadata[0].relay_ip and summary.relay_ip != relay_metadata[0].relay_ip:
        _add_finding(
            findings,
            code="RELAY_PATH_MISMATCH",
            severity=FindingSeverity.WARN,
            message="Observed relay metadata does not match the DHCP transaction relay IP.",
        )

    next_actions = build_next_actions(
        [
            ("net.segmentation_policy", "DHCP scope or relay issues may reflect the wrong network placement.", any(f.code in {"SCOPE_UTILIZATION_HIGH", "RELAY_PATH_MISMATCH"} for f in findings)),
            ("net.path_probe", "Service-path validation can confirm whether DHCP latency is network-wide.", any(f.code in {"HIGH_DHCP_OFFER_LATENCY", "HIGH_DHCP_ACK_LATENCY", "DHCP_TIMEOUTS"} for f in findings)),
        ]
    )
    raw_refs = _provider_refs(dhcp, "get_dhcp_transaction_summaries", "get_scope_utilization", "get_relay_path_metadata")
    return _build_result(
        skill_name="net.dhcp_path",
        scope_type=ScopeType.SERVICE,
        scope_id=skill_input.scope_id,
        ok_summary="DHCP transactions do not show material latency or failure symptoms.",
        time_window=skill_input.time_window,
        evidence=evidence,
        findings=findings,
        next_actions=next_actions,
        raw_refs=raw_refs,
    )


def evaluate_dns_latency(skill_input: DnsLatencyInput, adapters: AdapterBundle) -> SkillResult:
    if adapters.dns is None:
        raise DependencyUnavailableError("DNS adapter is not configured.")
    dns = adapters.dns
    context = build_adapter_context(skill_input)
    summary = dns.retrieve_dns_telemetry(site_id=skill_input.site_id, client_id=skill_input.client_id, context=context)
    if summary is None:
        summary = dns.run_dns_probes(
            queries=skill_input.queries,
            site_id=skill_input.site_id,
            client_id=skill_input.client_id,
            probe_locations=[skill_input.site_id] if skill_input.site_id else None,
            context=context,
        )
    if summary is None:
        raise InsufficientEvidenceError("Unable to locate DNS telemetry for the requested scope.")

    thresholds = default_threshold_config().service
    findings: list[Finding] = []
    evidence = summary.model_dump(mode="json", exclude_none=True)
    latency_issues = []
    for resolver in summary.resolver_results:
        if resolver.avg_latency_ms is not None and compare_to_threshold("avg_latency_ms", resolver.avg_latency_ms, thresholds.high_dns_latency_ms, direction="gte").breached:
            latency_issues.append(resolver.avg_latency_ms)
    if latency_issues:
        _add_finding(
            findings,
            code="HIGH_DNS_LATENCY",
            severity=FindingSeverity.WARN,
            message="One or more DNS resolvers are responding slowly.",
            metric="avg_latency_ms",
            value=max(latency_issues),
            threshold=thresholds.high_dns_latency_ms,
        )
    timeout_values = [resolver.timeout_pct for resolver in summary.resolver_results if resolver.timeout_pct is not None]
    overall_timeout = summary.overall_timeout_pct if summary.overall_timeout_pct is not None else (max(timeout_values) if timeout_values else None)
    if overall_timeout is not None and compare_to_threshold("overall_timeout_pct", overall_timeout, HIGH_DNS_TIMEOUT_PCT, direction="gte").breached:
        _add_finding(
            findings,
            code="DNS_TIMEOUT_RATE",
            severity=FindingSeverity.CRITICAL,
            message="DNS timeout rate is above the acceptable threshold.",
            metric="overall_timeout_pct",
            value=overall_timeout,
            threshold=HIGH_DNS_TIMEOUT_PCT,
        )

    baseline_reference = None
    if summary.overall_avg_latency_ms is not None:
        baseline_reference = compare_to_baseline("dns_latency_ms", summary.overall_avg_latency_ms, 18.0)
        evidence["baseline_comparison"] = baseline_reference.model_dump(mode="json")

    next_actions = build_next_actions(
        [
            ("net.path_probe", "Path probing can confirm whether DNS is the isolated bottleneck.", bool(findings)),
        ]
    )
    raw_refs = _provider_refs(dns, "retrieve_dns_telemetry", "run_dns_probes")
    return _build_result(
        skill_name="net.dns_latency",
        scope_type=ScopeType.SERVICE,
        scope_id=skill_input.scope_id,
        ok_summary="DNS lookups do not show material latency or timeout issues.",
        time_window=skill_input.time_window,
        evidence=evidence,
        findings=findings,
        next_actions=next_actions,
        raw_refs=raw_refs,
        baseline_present=baseline_reference is not None,
    )


def evaluate_ap_uplink_health(skill_input: ApUplinkHealthInput, adapters: AdapterBundle) -> SkillResult:
    if adapters.switch is None:
        raise DependencyUnavailableError("Switch adapter is not configured.")
    switch = adapters.switch
    inventory = adapters.inventory
    context = build_adapter_context(skill_input)

    port_state = None
    if skill_input.switch_id and skill_input.switch_port:
        port_state = switch.get_switch_port_state(switch_id=skill_input.switch_id, port=skill_input.switch_port, context=context)
    else:
        port_state = switch.resolve_ap_to_switch_port(ap_id=skill_input.ap_id, ap_name=skill_input.ap_name, context=context)
    if port_state is None:
        raise InsufficientEvidenceError("Unable to resolve the AP to a switch port.")

    counters = None
    if port_state.switch_id and port_state.port:
        counters = switch.get_interface_counters(switch_id=port_state.switch_id, port=port_state.port, context=context)
    expectation = None
    if inventory is not None:
        expectation = inventory.get_expected_ap_uplink_characteristics(ap_id=skill_input.ap_id or port_state.ap_id, ap_name=skill_input.ap_name or port_state.ap_name, context=context)

    thresholds = default_threshold_config().wired
    findings: list[Finding] = []
    evidence = port_state.model_dump(mode="json", exclude_none=True)
    if counters is not None:
        evidence["counters"] = counters.model_dump(mode="json", exclude_none=True)
    if expectation is not None:
        evidence["expected_uplink"] = expectation.model_dump(mode="json", exclude_none=True)

    expected_speed = expectation.expected_speed_mbps if expectation and expectation.expected_speed_mbps is not None else 1000
    if port_state.speed_mbps is not None and port_state.speed_mbps < expected_speed:
        _add_finding(
            findings,
            code="UPLINK_SPEED_MISMATCH",
            severity=FindingSeverity.WARN,
            message="The AP uplink negotiated below the expected speed.",
            metric="speed_mbps",
            value=port_state.speed_mbps,
            threshold=expected_speed,
        )

    total_errors = sum(
        value or 0
        for value in (
            port_state.crc_errors,
            port_state.input_errors,
            port_state.output_errors,
            counters.crc_errors if counters else None,
            counters.input_errors if counters else None,
            counters.output_errors if counters else None,
        )
    )
    if total_errors >= thresholds.high_crc_errors:
        _add_finding(
            findings,
            code="UPLINK_ERROR_RATE",
            severity=FindingSeverity.CRITICAL if total_errors >= thresholds.high_crc_errors * 2 else FindingSeverity.WARN,
            message="The AP uplink shows elevated CRC or interface error counts.",
            metric="interface_errors",
            value=total_errors,
            threshold=thresholds.high_crc_errors,
        )
    flaps = port_state.flaps_last_24h or 0
    if flaps >= HIGH_UPLINK_FLAPS:
        _add_finding(
            findings,
            code="UPLINK_FLAPPING",
            severity=FindingSeverity.WARN,
            message="The AP uplink has flapped repeatedly in the last 24 hours.",
            metric="flaps_last_24h",
            value=flaps,
            threshold=HIGH_UPLINK_FLAPS,
        )
    if expectation is not None:
        if expectation.expected_trunk is not None and port_state.trunk is not None and expectation.expected_trunk != port_state.trunk:
            _add_finding(
                findings,
                code="UPLINK_VLAN_MISMATCH",
                severity=FindingSeverity.WARN,
                message="The AP uplink trunk/access state does not match the expected configuration.",
            )
        if expectation.expected_native_vlan is not None and port_state.native_vlan is not None and expectation.expected_native_vlan != port_state.native_vlan:
            _add_finding(
                findings,
                code="UPLINK_VLAN_MISMATCH",
                severity=FindingSeverity.WARN,
                message="The AP uplink native VLAN does not match the expected configuration.",
            )
    if expectation is not None and expectation.expected_poe_watts is not None and port_state.poe_watts is not None and port_state.poe_watts < expectation.expected_poe_watts * 0.5:
        _add_finding(
            findings,
            code="POE_INSTABILITY",
            severity=FindingSeverity.WARN,
            message="PoE delivery appears low for the expected AP uplink power budget.",
        )

    next_actions = build_next_actions(
        [
            ("net.ap_rf_health", "If the uplink is clean but symptoms persist, validate RF conditions next.", not findings),
        ]
    )
    raw_refs = _provider_refs(switch, "resolve_ap_to_switch_port", "get_switch_port_state", "get_interface_counters")
    if inventory is not None:
        raw_refs.extend(_provider_refs(inventory, "get_expected_ap_uplink_characteristics"))

    return _build_result(
        skill_name="net.ap_uplink_health",
        scope_type=ScopeType.SWITCH_PORT,
        scope_id=f"{port_state.switch_id or 'unknown'}:{port_state.port or 'unknown'}",
        ok_summary="The AP uplink does not show material speed, error, or VLAN issues.",
        time_window=skill_input.time_window,
        evidence=evidence,
        findings=findings,
        next_actions=next_actions,
        raw_refs=raw_refs,
    )


def evaluate_stp_loop_anomaly(skill_input: StpLoopAnomalyInput, adapters: AdapterBundle) -> SkillResult:
    if adapters.switch is None:
        raise DependencyUnavailableError("Switch adapter is not configured.")
    switch = adapters.switch
    context = build_adapter_context(skill_input)
    stp_summaries = switch.get_topology_change_summaries(site_id=skill_input.site_id, switch_id=skill_input.switch_id, context=context)
    mac_flaps = switch.get_mac_flap_events(site_id=skill_input.site_id, switch_id=skill_input.switch_id, port=skill_input.switch_port, context=context)
    if not stp_summaries and not mac_flaps:
        raise InsufficientEvidenceError("Unable to locate STP or MAC-flap telemetry for the requested scope.")

    topology_changes = sum(summary.topology_changes or 0 for summary in stp_summaries)
    root_bridge_changes = sum(summary.root_bridge_changes or 0 for summary in stp_summaries)
    suspect_ports = sorted({port for summary in stp_summaries for port in summary.suspect_ports})
    mac_flap_count = sum(summary.mac_flap_events or 0 for summary in stp_summaries) + len(mac_flaps)
    thresholds = default_threshold_config().wired
    findings: list[Finding] = []

    if topology_changes >= thresholds.topology_change_churn:
        _add_finding(
            findings,
            code="TOPOLOGY_CHURN",
            severity=FindingSeverity.WARN,
            message="Topology change churn is above the configured threshold.",
            metric="topology_changes",
            value=topology_changes,
            threshold=thresholds.topology_change_churn,
        )
    if root_bridge_changes > 0:
        _add_finding(
            findings,
            code="ROOT_BRIDGE_CHANGES",
            severity=FindingSeverity.WARN,
            message="Root bridge changes were observed in the requested time window.",
            metric="root_bridge_changes",
            value=root_bridge_changes,
            threshold=0,
        )
    if mac_flap_count >= HIGH_MAC_FLAP_EVENTS:
        _add_finding(
            findings,
            code="MAC_FLAP_LOOP_SIGNATURE",
            severity=FindingSeverity.CRITICAL,
            message="MAC flap activity strongly suggests L2 instability or a switching loop.",
            metric="mac_flap_events",
            value=mac_flap_count,
            threshold=HIGH_MAC_FLAP_EVENTS,
        )
    if any(summary.broadcast_storm_detected or summary.multicast_storm_detected for summary in stp_summaries):
        _add_finding(
            findings,
            code="STORM_INDICATORS",
            severity=FindingSeverity.CRITICAL,
            message="Storm indicators were observed alongside STP instability.",
        )

    next_actions = build_next_actions(
        [
            ("net.change_detection", "Recent switching changes should be reviewed alongside the STP anomaly.", bool(findings)),
            ("net.ap_uplink_health", "Investigate AP-connected suspect ports where relevant.", bool(suspect_ports)),
        ]
    )
    raw_refs = _provider_refs(switch, "get_topology_change_summaries", "get_mac_flap_events")
    evidence = {
        "topology_changes": topology_changes,
        "root_bridge_changes": root_bridge_changes,
        "mac_flap_events": mac_flap_count,
        "suspect_ports": suspect_ports,
    }
    return _build_result(
        skill_name="net.stp_loop_anomaly",
        scope_type=ScopeType.SITE,
        scope_id=skill_input.scope_id,
        ok_summary="No significant STP instability or loop indicators were observed.",
        time_window=skill_input.time_window,
        evidence=evidence,
        findings=findings,
        next_actions=next_actions,
        raw_refs=raw_refs,
    )


def build_priority1_parser(skill_name: str, description: str) -> argparse.ArgumentParser:
    parser = build_common_parser(skill_name, description)
    parser.add_argument("--fixture-file", default=os.environ.get("NETTOOLS_FIXTURE_FILE"))
    return parser


def _parse_input(arguments: argparse.Namespace, model_type: type[SkillInputType]) -> SkillInputType:
    payload = {
        key: value
        for key, value in vars(arguments).items()
        if key in model_type.model_fields and value is not None
    }
    return model_type.model_validate(payload)


def _emit_result(result: SkillResult) -> None:
    print(result.model_dump_json(indent=2))


def run_priority1_cli(
    *,
    argv: Sequence[str] | None,
    skill_name: str,
    description: str,
    scope_type: ScopeType,
    input_model: type[SkillInputType],
    handler: Callable[[SkillInputType, AdapterBundle], SkillResult],
    configure_parser: Callable[[argparse.ArgumentParser], None] | None = None,
) -> int:
    logger = configure_logging(skill_name)
    parser = build_priority1_parser(skill_name, description)
    if configure_parser is not None:
        configure_parser(parser)
    arguments = parser.parse_args(list(argv) if argv is not None else None)

    try:
        skill_input = _parse_input(arguments, input_model)
    except ValidationError as exc:
        result = error_to_skill_result(
            error=BadInputError(str(exc)),
            skill_name=skill_name,
            scope_type=scope_type,
            scope_id="unscoped",
            time_window=SharedInputBase().time_window,
        )
        _emit_result(result)
        return 2

    try:
        adapters = load_stub_adapter_bundle(getattr(arguments, "fixture_file", None))
        result = handler(skill_input, adapters)
    except NettoolsError as exc:
        result = error_to_skill_result(
            error=exc,
            skill_name=skill_name,
            scope_type=scope_type,
            scope_id=skill_input.scope_id,
            time_window=skill_input.time_window,
        )
        logger.warning(
            "skill execution produced a structured error result",
            skill_name=skill_name,
            scope_type=scope_type.value,
            scope_id=skill_input.scope_id,
            result_status=result.status.value,
            finding_codes=[finding.code for finding in result.findings],
        )
        _emit_result(result)
        return 1

    logger.info(
        "priority skill executed",
        skill_name=skill_name,
        scope_type=scope_type.value,
        scope_id=result.scope_id,
        result_status=result.status.value,
        finding_codes=[finding.code for finding in result.findings],
        next_actions=[action.skill for action in result.next_actions],
        inputs=skill_input.to_input_summary(),
    )
    _emit_result(result)
    return 0


def configure_dns_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--query", action="append", dest="queries")


def main_client_health(argv: Sequence[str] | None = None) -> int:
    return run_priority1_cli(
        argv=argv,
        skill_name="net.client_health",
        description="Assess Wi-Fi client session health using normalized RF and retry telemetry.",
        scope_type=ScopeType.CLIENT,
        input_model=ClientHealthInput,
        handler=evaluate_client_health,
    )


def main_ap_rf_health(argv: Sequence[str] | None = None) -> int:
    return run_priority1_cli(
        argv=argv,
        skill_name="net.ap_rf_health",
        description="Evaluate AP radio conditions and wireless health.",
        scope_type=ScopeType.AP,
        input_model=ApRfHealthInput,
        handler=evaluate_ap_rf_health,
    )


def main_dhcp_path(argv: Sequence[str] | None = None) -> int:
    return run_priority1_cli(
        argv=argv,
        skill_name="net.dhcp_path",
        description="Assess DHCP latency, failures, and relay-path issues.",
        scope_type=ScopeType.SERVICE,
        input_model=DhcpPathInput,
        handler=evaluate_dhcp_path,
    )


def main_dns_latency(argv: Sequence[str] | None = None) -> int:
    return run_priority1_cli(
        argv=argv,
        skill_name="net.dns_latency",
        description="Measure DNS latency and timeout behavior.",
        scope_type=ScopeType.SERVICE,
        input_model=DnsLatencyInput,
        handler=evaluate_dns_latency,
        configure_parser=configure_dns_parser,
    )


def main_ap_uplink_health(argv: Sequence[str] | None = None) -> int:
    return run_priority1_cli(
        argv=argv,
        skill_name="net.ap_uplink_health",
        description="Validate the wired path behind an access point.",
        scope_type=ScopeType.SWITCH_PORT,
        input_model=ApUplinkHealthInput,
        handler=evaluate_ap_uplink_health,
    )


def main_stp_loop_anomaly(argv: Sequence[str] | None = None) -> int:
    return run_priority1_cli(
        argv=argv,
        skill_name="net.stp_loop_anomaly",
        description="Detect STP instability and switching-loop symptoms.",
        scope_type=ScopeType.SITE,
        input_model=StpLoopAnomalyInput,
        handler=evaluate_stp_loop_anomaly,
    )