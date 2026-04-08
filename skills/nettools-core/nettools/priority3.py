from __future__ import annotations

import argparse
import re
from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any

from pydantic import Field, model_validator

from .analysis import (
    aggregate_evidence,
    build_next_actions,
    event_correlation_score,
)
from .errors import DependencyUnavailableError, InsufficientEvidenceError
from .models import (
    ChangeRecord,
    Finding,
    FindingSeverity,
    IncidentRecord,
    ScopeType,
    SharedInputBase,
    SkillResult,
    TimeWindow,
)
from .priority1 import (
    AdapterBundle,
    _add_finding,
    _build_result,
    _provider_refs,
    build_adapter_context,
    run_priority1_cli,
    utc_now,
)

MAC_PATTERN = re.compile(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b")
SSID_PATTERN = re.compile(r"ssid\s+[\"']?([A-Za-z0-9_.-]{2,40})[\"']?(?:\b|$)", re.IGNORECASE)
FLOOR_PATTERN = re.compile(r"\b(floor\s+\d+)\b", re.IGNORECASE)
ROOM_PATTERN = re.compile(
    r"\b(conference\s+room\s+[A-Za-z0-9-]+|lobby|warehouse|desk\s+[A-Za-z0-9-]+)\b", re.IGNORECASE
)

CAPTURE_PROTOCOL_FILTERS = {
    "dhcp": "udp port 67 or udp port 68",
    "dns": "udp port 53 or tcp port 53",
    "radius": "udp port 1812 or udp port 1813",
    "eapol": "ether proto 0x888e",
    "icmp": "icmp",
    "tcp": "tcp",
}


class IncidentIntakeInput(SharedInputBase):
    complaint: str
    reporter: str | None = None
    incident_id: str | None = None
    location: str | None = None
    device_type: str | None = None
    movement_state: str | None = None
    wired_also_affected: bool | None = None
    reconnect_helps: bool | None = None
    occurred_at: datetime | None = None
    impacted_apps: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class IncidentCorrelationInput(SharedInputBase):
    incident_summary: str | None = None
    reporter: str | None = None

    @model_validator(mode="after")
    def validate_scope(self) -> IncidentCorrelationInput:
        if not (
            self.incident_summary
            or self.site_id
            or self.client_id
            or self.client_mac
            or self.ap_id
            or self.switch_id
        ):
            raise ValueError("incident_summary or at least one scope identifier is required")
        return self


class ChangeDetectionInput(SharedInputBase):
    device_id: str | None = None
    incident_summary: str | None = None

    @model_validator(mode="after")
    def validate_scope(self) -> ChangeDetectionInput:
        if not (self.site_id or self.device_id or self.ap_id or self.switch_id):
            raise ValueError("site_id, device_id, ap_id, or switch_id is required")
        return self


class CaptureTriggerInput(SharedInputBase):
    reason: str
    protocol: str = "auto"
    target_host: str | None = None
    interface_scope: str | None = None
    authorized: bool = False
    approval_ticket: str | None = None
    capture_duration_seconds: int = Field(default=180, ge=30, le=600)
    packet_count_limit: int = Field(default=2000, ge=100, le=10000)

    @model_validator(mode="after")
    def validate_capture_scope(self) -> CaptureTriggerInput:
        if not (self.site_id or self.client_id or self.client_mac or self.ap_id or self.switch_id):
            raise ValueError("at least one scope identifier is required for capture planning")
        return self


def _normalized_text(value: str | None) -> str:
    return (value or "").strip().lower()


def _extract_location(complaint: str) -> str | None:
    for pattern in (ROOM_PATTERN, FLOOR_PATTERN):
        match = pattern.search(complaint)
        if match is not None:
            return match.group(1)
    return None


def _extract_ssid(complaint: str) -> str | None:
    match = SSID_PATTERN.search(complaint)
    if match is not None:
        return match.group(1).strip()
    return None


def _extract_device_type(complaint: str) -> str | None:
    lowered = complaint.lower()
    device_map = {
        "iphone": "iphone",
        "ipad": "ipad",
        "android": "android",
        "macbook": "macbook",
        "windows laptop": "windows_laptop",
        "laptop": "laptop",
        "phone": "phone",
    }
    for token, normalized in device_map.items():
        if token in lowered:
            return normalized
    return None


def _extract_movement_state(complaint: str) -> str | None:
    lowered = complaint.lower()
    if any(
        token in lowered
        for token in ("walking", "moving", "roaming", "between aps", "while moving")
    ):
        return "moving"
    if any(token in lowered for token in ("desk", "stationary", "sitting")):
        return "stationary"
    return None


def _infer_wired_also_affected(complaint: str) -> bool | None:
    lowered = complaint.lower()
    if any(
        token in lowered
        for token in ("wired also affected", "ethernet also affected", "wired users also")
    ):
        return True
    if any(
        token in lowered
        for token in ("wired works", "ethernet works", "wired is fine", "wired is okay")
    ):
        return False
    return None


def _infer_reconnect_helps(complaint: str) -> bool | None:
    lowered = complaint.lower()
    if any(
        token in lowered
        for token in (
            "reconnect helps",
            "forget network helps",
            "toggle wifi helps",
            "disconnecting fixes",
        )
    ):
        return True
    if any(
        token in lowered for token in ("reconnecting does not help", "forgetting does not help")
    ):
        return False
    return None


def _extract_impacted_apps(complaint: str) -> list[str]:
    lowered = complaint.lower()
    apps = []
    for token, normalized in (
        ("zoom", "zoom"),
        ("teams", "teams"),
        ("slack", "slack"),
        ("vpn", "vpn"),
        ("voice", "voice"),
        ("dns", "dns"),
    ):
        if token in lowered:
            apps.append(normalized)
    return apps


def _incident_scope_type(record: IncidentRecord) -> ScopeType:
    if record.client_id or record.client_mac:
        return ScopeType.CLIENT
    if record.ssid:
        return ScopeType.SSID
    if record.site_id or record.location:
        return ScopeType.SITE
    return ScopeType.SERVICE


def _incident_summary_keywords(text: str | None) -> set[str]:
    if text is None:
        return set()
    return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) > 2}


def _time_window_around(timestamp: datetime | None, *, minutes: int = 5) -> TimeWindow | None:
    if timestamp is None:
        return None
    return TimeWindow(
        start=timestamp - timedelta(minutes=minutes), end=timestamp + timedelta(minutes=minutes)
    )


def _device_id_from_input(
    skill_input: SharedInputBase, explicit_device_id: str | None = None
) -> str | None:
    return explicit_device_id or skill_input.ap_id or skill_input.switch_id


def _score_event(
    summary_keywords: set[str], event: Any, time_window: TimeWindow, scope_match: bool
) -> float:
    overlap = 0.0
    event_window = _time_window_around(event.happened_at)
    if event_window is not None:
        overlap = event_correlation_score(
            first_window=time_window,
            second_window=event_window,
            shared_scope=scope_match,
            shared_sources=1,
        )
    severity_bonus = {"critical": 0.35, "warn": 0.2, "info": 0.05}.get(
        _normalized_text(event.severity), 0.1
    )
    shared_keywords = len(summary_keywords.intersection(_incident_summary_keywords(event.summary)))
    return round(min(1.0, overlap + severity_bonus + min(shared_keywords, 3) * 0.08), 4)


def _score_change(
    summary_keywords: set[str], change: ChangeRecord, time_window: TimeWindow, scope_match: bool
) -> float:
    overlap = 0.0
    change_window = _time_window_around(change.changed_at)
    if change_window is not None:
        overlap = event_correlation_score(
            first_window=time_window,
            second_window=change_window,
            shared_scope=scope_match,
            shared_sources=1,
        )
    shared_keywords = len(summary_keywords.intersection(_incident_summary_keywords(change.summary)))
    category_bonus = (
        0.25
        if _normalized_text(change.category) in {"hardware", "firmware", "wireless", "switching"}
        else 0.1
    )
    preset_score = change.relevance_score or 0.0
    return round(
        min(
            1.0,
            overlap
            + category_bonus
            + min(shared_keywords, 3) * 0.08
            + min(preset_score, 1.0) * 0.25,
        ),
        4,
    )


def _protocol_from_reason(reason: str, explicit_protocol: str) -> str:
    if explicit_protocol != "auto":
        return explicit_protocol.lower()
    lowered = reason.lower()
    if "dhcp" in lowered or "address" in lowered:
        return "dhcp"
    if "dns" in lowered:
        return "dns"
    if "radius" in lowered or "802.1x" in lowered or "eap" in lowered or "auth" in lowered:
        return "radius"
    if "icmp" in lowered or "ping" in lowered:
        return "icmp"
    return "tcp"


def _recommended_vantage(skill_input: CaptureTriggerInput) -> str:
    if skill_input.client_id or skill_input.client_mac:
        return "client-edge"
    if skill_input.ap_id:
        return "ap-uplink"
    if skill_input.switch_id:
        return "switch-port"
    return "site-aggregation"


def evaluate_incident_intake(
    skill_input: IncidentIntakeInput, adapters: AdapterBundle
) -> SkillResult:
    complaint = skill_input.complaint.strip()
    mac_match = MAC_PATTERN.search(complaint)
    incident_record = IncidentRecord(
        incident_id=skill_input.incident_id or f"incident-{utc_now().strftime('%Y%m%dT%H%M%SZ')}",
        reporter=skill_input.reporter,
        summary=complaint,
        location=skill_input.location or _extract_location(complaint),
        site_id=skill_input.site_id,
        device_type=skill_input.device_type or _extract_device_type(complaint),
        client_id=skill_input.client_id,
        client_mac=skill_input.client_mac
        or (mac_match.group(0) if mac_match is not None else None),
        ssid=skill_input.ssid or _extract_ssid(complaint),
        movement_state=skill_input.movement_state or _extract_movement_state(complaint),
        wired_also_affected=skill_input.wired_also_affected
        if skill_input.wired_also_affected is not None
        else _infer_wired_also_affected(complaint),
        reconnect_helps=skill_input.reconnect_helps
        if skill_input.reconnect_helps is not None
        else _infer_reconnect_helps(complaint),
        impacted_apps=sorted(set(skill_input.impacted_apps + _extract_impacted_apps(complaint))),
        occurred_at=skill_input.occurred_at or skill_input.time_window.end,
        reported_at=utc_now(),
        notes=skill_input.notes,
    )

    findings: list[Finding] = []
    if not any(
        (
            incident_record.site_id,
            incident_record.location,
            incident_record.client_id,
            incident_record.client_mac,
            incident_record.ssid,
        )
    ):
        _add_finding(
            findings,
            code="INTAKE_INCOMPLETE_SCOPE",
            severity=FindingSeverity.WARN,
            message=(
                "The complaint is missing enough scope detail that follow-up "
                "diagnosis may stay broad."
            ),
        )

    complaint_lower = complaint.lower()
    next_actions = build_next_actions(
        [
            (
                "net.roaming_analysis",
                "The complaint suggests movement-related Wi-Fi symptoms.",
                incident_record.movement_state == "moving",
            ),
            (
                "net.mac_path_trace",
                "The complaint suggests an unknown or changing attachment point.",
                any(
                    token in complaint_lower
                    for token in (
                        "which ap",
                        "which switch",
                        "where is",
                        "wrong port",
                        "wrong vlan",
                    )
                ),
            ),
            (
                "net.auth_8021x_radius",
                "The complaint suggests auth, onboarding, or certificate symptoms.",
                any(
                    token in complaint_lower
                    for token in (
                        "can't connect",
                        "cannot connect",
                        "certificate",
                        "password",
                        "802.1x",
                        "radius",
                        "auth",
                    )
                ),
            ),
            (
                "net.dhcp_path",
                "The complaint suggests address assignment or reconnect issues.",
                any(
                    token in complaint_lower
                    for token in ("self-assigned", "169.254", "ip address", "no address", "dhcp")
                ),
            ),
            (
                "net.path_probe",
                "The complaint suggests broad slowness or application reachability issues.",
                any(
                    token in complaint_lower
                    for token in ("slow", "latency", "lag", "timeout", "internet")
                ),
            ),
            (
                "net.topology_map",
                "The complaint suggests local path or topology uncertainty.",
                any(
                    token in complaint_lower
                    for token in (
                        "gateway",
                        "topology",
                        "path",
                        "uplink",
                        "switch",
                        "vlan",
                        "subnet",
                    )
                ),
            ),
            (
                "net.mdns_service_discovery",
                "The complaint suggests a local-name or .local service-discovery problem.",
                any(
                    token in complaint_lower
                    for token in ("mdns", "bonjour", ".local", "airprint")
                ),
            ),
        ]
    )

    return _build_result(
        skill_name="net.incident_intake",
        scope_type=_incident_scope_type(incident_record),
        scope_id=incident_record.client_id
        or incident_record.client_mac
        or incident_record.site_id
        or incident_record.location
        or "unscoped",
        ok_summary="The complaint was normalized into a structured incident record.",
        time_window=skill_input.time_window,
        evidence={"incident_record": incident_record.model_dump(mode="json", exclude_none=True)},
        findings=findings,
        next_actions=next_actions,
        raw_refs=["intake:user-complaint"],
    )


def evaluate_incident_correlation(
    skill_input: IncidentCorrelationInput, adapters: AdapterBundle
) -> SkillResult:
    if adapters.syslog is None and adapters.inventory is None:
        raise DependencyUnavailableError(
            "Incident correlation requires syslog or inventory adapters."
        )

    context = build_adapter_context(skill_input)
    device_id = _device_id_from_input(skill_input)
    summary_keywords = _incident_summary_keywords(skill_input.incident_summary)
    candidates = []
    event_payloads: list[dict[str, Any]] = []

    if adapters.syslog is not None:
        events = adapters.syslog.fetch_events_by_time_window(
            context=context, site_id=skill_input.site_id, device_id=device_id
        )
        auth_events = adapters.syslog.fetch_auth_dhcp_dns_related_events(
            site_id=skill_input.site_id,
            client_id=skill_input.client_id,
            client_mac=skill_input.client_mac,
            context=context,
        )
        ap_events = adapters.syslog.fetch_ap_controller_events(
            site_id=skill_input.site_id, ap_id=skill_input.ap_id, context=context
        )
        for event in [*events, *auth_events, *ap_events]:
            scope_match = bool(
                skill_input.site_id and event.site_id == skill_input.site_id
            ) or bool(device_id and event.device_id == device_id)
            score = _score_event(summary_keywords, event, skill_input.time_window, scope_match)
            candidates.append((score, "event", event))
            event_payloads.append(event.model_dump(mode="json", exclude_none=True))

    change_payloads: list[dict[str, Any]] = []
    if adapters.inventory is not None:
        changes = adapters.inventory.get_recent_config_changes(
            site_id=skill_input.site_id, device_id=device_id, context=context
        )
        for change in changes:
            scope_match = bool(
                skill_input.site_id and change.site_id == skill_input.site_id
            ) or bool(device_id and change.device_id == device_id)
            score = _score_change(summary_keywords, change, skill_input.time_window, scope_match)
            candidates.append((score, "change", change))
            change_payloads.append(change.model_dump(mode="json", exclude_none=True))

    if not candidates:
        raise InsufficientEvidenceError(
            "Unable to locate incident-adjacent events or changes for the requested scope."
        )

    suspected_causes = []
    for score, candidate_type, candidate in sorted(
        candidates, key=lambda item: item[0], reverse=True
    )[:5]:
        code = (
            candidate.event_type
            if candidate_type == "event"
            else candidate.change_id or candidate.category or "change"
        )
        reason = candidate.summary or getattr(candidate, "event_type", "correlated evidence")
        suspected_causes.append(
            {
                "code": code,
                "score": score,
                "reason": reason,
                "candidate_type": candidate_type,
            }
        )

    findings: list[Finding] = []
    top_candidate = suspected_causes[0]
    if top_candidate["score"] >= 0.55:
        _add_finding(
            findings,
            code="CORRELATED_NETWORK_EVIDENCE",
            severity=FindingSeverity.WARN,
            message="Recent events or changes correlate strongly with the incident window.",
            metric="top_correlation_score",
            value=top_candidate["score"],
            threshold=0.55,
        )
    if any(
        candidate["candidate_type"] == "change" and candidate["score"] >= 0.6
        for candidate in suspected_causes
    ):
        _add_finding(
            findings,
            code="CORRELATED_CHANGE_WINDOW",
            severity=FindingSeverity.WARN,
            message="Recent infrastructure changes overlap strongly with the incident window.",
        )

    aggregate = aggregate_evidence([{"events": event_payloads}, {"changes": change_payloads}])
    next_actions = build_next_actions(
        [
            (
                "net.change_detection",
                "Correlated changes should be reviewed in more detail.",
                any(candidate["candidate_type"] == "change" for candidate in suspected_causes[:2]),
            ),
            (
                "net.auth_8021x_radius",
                "Authentication-adjacent events were correlated with the incident.",
                any(
                    "auth" in _normalized_text(candidate["reason"])
                    or "radius" in _normalized_text(candidate["reason"])
                    for candidate in suspected_causes
                ),
            ),
            (
                "net.stp_loop_anomaly",
                "Switching or topology events correlate with the incident window.",
                any(
                    token in _normalized_text(candidate["reason"])
                    for candidate in suspected_causes
                    for token in ("stp", "loop", "mac flap", "topology")
                ),
            ),
            (
                "net.topology_map",
                "Correlated switching evidence suggests reconstructing the local path graph.",
                any(
                    token in _normalized_text(candidate["reason"])
                    for candidate in suspected_causes
                    for token in ("stp", "loop", "mac flap", "topology", "gateway")
                ),
            ),
            (
                "net.ap_rf_health",
                "AP or RF controller events correlate with the incident window.",
                any(
                    token in _normalized_text(candidate["reason"])
                    for candidate in suspected_causes
                    for token in ("radio", "ap", "channel", "rf")
                ),
            ),
        ]
    )
    raw_refs: list[str] = []
    if adapters.syslog is not None:
        raw_refs.extend(
            _provider_refs(
                adapters.syslog,
                "fetch_events_by_time_window",
                "fetch_auth_dhcp_dns_related_events",
                "fetch_ap_controller_events",
            )
        )
    if adapters.inventory is not None:
        raw_refs.extend(_provider_refs(adapters.inventory, "get_recent_config_changes"))

    return _build_result(
        skill_name="net.incident_correlation",
        scope_type=skill_input.default_scope_type(),
        scope_id=skill_input.scope_id,
        ok_summary="No strong multi-source correlation was found around the incident window.",
        time_window=skill_input.time_window,
        evidence={
            "incident_summary": skill_input.incident_summary,
            "top_correlated_items": suspected_causes,
            "aggregated_evidence": aggregate,
        },
        findings=findings,
        next_actions=next_actions,
        raw_refs=raw_refs,
    )


def evaluate_change_detection(
    skill_input: ChangeDetectionInput, adapters: AdapterBundle
) -> SkillResult:
    if adapters.inventory is None and adapters.syslog is None:
        raise DependencyUnavailableError("Change detection requires inventory or syslog adapters.")

    context = build_adapter_context(skill_input)
    device_id = _device_id_from_input(skill_input, skill_input.device_id)
    summary_keywords = _incident_summary_keywords(skill_input.incident_summary)
    ranked_changes: list[dict[str, Any]] = []

    if adapters.inventory is not None:
        changes = adapters.inventory.get_recent_config_changes(
            site_id=skill_input.site_id, device_id=device_id, context=context
        )
        for change in changes:
            scope_match = bool(
                skill_input.site_id and change.site_id == skill_input.site_id
            ) or bool(device_id and change.device_id == device_id)
            ranked_changes.append(
                {
                    "kind": "change",
                    "score": _score_change(
                        summary_keywords, change, skill_input.time_window, scope_match
                    ),
                    "payload": change.model_dump(mode="json", exclude_none=True),
                    "category": change.category,
                    "summary": change.summary,
                }
            )

    if adapters.syslog is not None:
        events = adapters.syslog.fetch_events_by_time_window(
            context=context, site_id=skill_input.site_id, device_id=device_id
        )
        for event in events:
            if any(
                token in _normalized_text(event.summary)
                or token in _normalized_text(event.event_type)
                for token in ("reload", "reboot", "firmware", "upgrade", "changed")
            ):
                scope_match = bool(
                    skill_input.site_id and event.site_id == skill_input.site_id
                ) or bool(device_id and event.device_id == device_id)
                ranked_changes.append(
                    {
                        "kind": "event",
                        "score": _score_event(
                            summary_keywords, event, skill_input.time_window, scope_match
                        ),
                        "payload": event.model_dump(mode="json", exclude_none=True),
                        "category": event.event_type,
                        "summary": event.summary,
                    }
                )

    if not ranked_changes:
        raise InsufficientEvidenceError(
            "Unable to locate recent infrastructure changes for the requested scope."
        )

    ranked_changes.sort(key=lambda item: item["score"], reverse=True)
    findings: list[Finding] = []
    if ranked_changes[0]["score"] >= 0.55:
        _add_finding(
            findings,
            code="RECENT_RELEVANT_CHANGE",
            severity=FindingSeverity.WARN,
            message="A recent infrastructure change aligns closely with the incident window.",
            metric="top_change_score",
            value=ranked_changes[0]["score"],
            threshold=0.55,
        )
    if any(
        _normalized_text(item["category"]) in {"hardware", "firmware", "switching", "wireless"}
        and item["score"] >= 0.6
        for item in ranked_changes
    ):
        _add_finding(
            findings,
            code="RECENT_HARDWARE_OR_FIRMWARE_CHANGE",
            severity=FindingSeverity.WARN,
            message=(
                "A recent hardware, firmware, or platform change may explain the complaint timing."
            ),
        )

    next_actions = build_next_actions(
        [
            (
                "net.ap_rf_health",
                "Wireless-related changes should be validated against AP RF state.",
                any(
                    "wireless" in _normalized_text(item["category"]) for item in ranked_changes[:3]
                ),
            ),
            (
                "net.ap_uplink_health",
                "Switching or uplink changes should be validated against wired health.",
                any(
                    token in _normalized_text(item["category"])
                    for item in ranked_changes[:3]
                    for token in ("switch", "hardware", "port")
                ),
            ),
            (
                "net.topology_map",
                "Recent topology-related changes should be compared with the current local graph.",
                any(
                    token in _normalized_text(item["summary"])
                    for item in ranked_changes[:3]
                    for token in ("topology", "uplink", "vlan", "gateway")
                ),
            ),
            (
                "net.stp_loop_anomaly",
                "Topology-related changes should be checked against switching instability.",
                any(
                    token in _normalized_text(item["summary"])
                    for item in ranked_changes[:3]
                    for token in ("stp", "topology", "loop")
                ),
            ),
        ]
    )

    raw_refs: list[str] = []
    if adapters.inventory is not None:
        raw_refs.extend(_provider_refs(adapters.inventory, "get_recent_config_changes"))
    if adapters.syslog is not None:
        raw_refs.extend(_provider_refs(adapters.syslog, "fetch_events_by_time_window"))

    return _build_result(
        skill_name="net.change_detection",
        scope_type=skill_input.default_scope_type(),
        scope_id=device_id or skill_input.scope_id,
        ok_summary=(
            "No recent infrastructure changes stood out as strongly relevant to "
            "the complaint window."
        ),
        time_window=skill_input.time_window,
        evidence={"ranked_changes": ranked_changes[:5]},
        findings=findings,
        next_actions=next_actions,
        raw_refs=raw_refs,
    )


def evaluate_capture_trigger(
    skill_input: CaptureTriggerInput, adapters: AdapterBundle
) -> SkillResult:
    protocol = _protocol_from_reason(skill_input.reason, skill_input.protocol)
    capture_filter = CAPTURE_PROTOCOL_FILTERS.get(protocol, "tcp")
    vantage_point = _recommended_vantage(skill_input)
    plan = {
        "authorized": skill_input.authorized,
        "approval_ticket": skill_input.approval_ticket,
        "protocol": protocol,
        "target_host": skill_input.target_host,
        "interface_scope": skill_input.interface_scope or vantage_point,
        "capture_duration_seconds": skill_input.capture_duration_seconds,
        "packet_count_limit": skill_input.packet_count_limit,
        "recommended_filter": capture_filter,
        "execution_mode": "manual-plan-only",
        "steps": [
            "Confirm policy approval and maintenance window before collecting packets.",
            f"Start capture at the {vantage_point} vantage point using filter: {capture_filter}.",
            "Stop the capture once the symptom is reproduced or the packet budget is reached.",
            "Store the pcap with incident metadata and review it offline.",
        ],
    }

    findings: list[Finding] = []
    if not skill_input.authorized or not skill_input.approval_ticket:
        _add_finding(
            findings,
            code="CAPTURE_AUTHORIZATION_REQUIRED",
            severity=FindingSeverity.WARN,
            message=(
                "A capture plan can be prepared, but authorization and an "
                "approval ticket are required before execution."
            ),
        )
    if skill_input.capture_duration_seconds > 300 or skill_input.packet_count_limit > 5000:
        _add_finding(
            findings,
            code="CAPTURE_SCOPE_TOO_BROAD",
            severity=FindingSeverity.WARN,
            message="The requested capture scope is broad and should be narrowed before execution.",
            metric="capture_duration_seconds",
            value=skill_input.capture_duration_seconds,
            threshold=300,
        )

    next_actions = build_next_actions(
        [
            (
                "net.auth_8021x_radius",
                "The requested capture focuses on authentication traffic.",
                protocol in {"radius", "eapol"},
            ),
            ("net.dns_latency", "The requested capture focuses on DNS traffic.", protocol == "dns"),
            ("net.dhcp_path", "The requested capture focuses on DHCP traffic.", protocol == "dhcp"),
        ]
    )
    return _build_result(
        skill_name="net.capture_trigger",
        scope_type=skill_input.default_scope_type(),
        scope_id=skill_input.scope_id,
        ok_summary="A gated manual capture plan was prepared for the requested scope.",
        time_window=skill_input.time_window,
        evidence={"capture_plan": plan, "reason": skill_input.reason},
        findings=findings,
        next_actions=next_actions,
        raw_refs=["policy:capture-gating", f"plan:protocol:{protocol}"],
    )


def configure_incident_intake_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--complaint", required=True)
    parser.add_argument("--reporter")
    parser.add_argument("--incident-id")
    parser.add_argument("--location")
    parser.add_argument("--device-type")
    parser.add_argument("--movement-state")
    parser.add_argument("--wired-also-affected", action="store_const", const=True, default=None)
    parser.add_argument("--reconnect-helps", action="store_const", const=True, default=None)
    parser.add_argument("--occurred-at")
    parser.add_argument("--impacted-app", action="append", dest="impacted_apps")
    parser.add_argument("--note", action="append", dest="notes")


def configure_incident_correlation_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--incident-summary")
    parser.add_argument("--reporter")


def configure_change_detection_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--device-id")
    parser.add_argument("--incident-summary")


def configure_capture_trigger_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--reason", required=True)
    parser.add_argument("--protocol", default="auto")
    parser.add_argument("--target-host")
    parser.add_argument("--interface-scope")
    parser.add_argument("--authorized", action="store_true")
    parser.add_argument("--approval-ticket")
    parser.add_argument("--capture-duration-seconds", type=int)
    parser.add_argument("--packet-count-limit", type=int)


def main_incident_intake(argv: Sequence[str] | None = None) -> int:
    return run_priority1_cli(
        argv=argv,
        skill_name="net.incident_intake",
        description="Normalize a freeform complaint into a structured NETTOOLS incident record.",
        scope_type=ScopeType.SITE,
        input_model=IncidentIntakeInput,
        handler=evaluate_incident_intake,
        configure_parser=configure_incident_intake_parser,
    )


def main_incident_correlation(argv: Sequence[str] | None = None) -> int:
    return run_priority1_cli(
        argv=argv,
        skill_name="net.incident_correlation",
        description="Correlate an incident window against recent network events and changes.",
        scope_type=ScopeType.SITE,
        input_model=IncidentCorrelationInput,
        handler=evaluate_incident_correlation,
        configure_parser=configure_incident_correlation_parser,
    )


def main_change_detection(argv: Sequence[str] | None = None) -> int:
    return run_priority1_cli(
        argv=argv,
        skill_name="net.change_detection",
        description="Rank recent infrastructure changes by likely relevance to a complaint window.",
        scope_type=ScopeType.SITE,
        input_model=ChangeDetectionInput,
        handler=evaluate_change_detection,
        configure_parser=configure_change_detection_parser,
    )


def main_capture_trigger(argv: Sequence[str] | None = None) -> int:
    return run_priority1_cli(
        argv=argv,
        skill_name="net.capture_trigger",
        description="Prepare a gated manual packet capture plan without executing a capture.",
        scope_type=ScopeType.SERVICE,
        input_model=CaptureTriggerInput,
        handler=evaluate_capture_trigger,
        configure_parser=configure_capture_trigger_parser,
    )
