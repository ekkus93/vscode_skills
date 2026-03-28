from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ..priority1 import AdapterBundle
from .execution import SkillExecutionRecord, invoke_skill
from .resolution import IdentifierResolver

POLICY_HINT_TOKENS = (
    "policy",
    "vlan",
    "guest",
    "access denied",
    "wrong network",
)
ADDRESS_HINT_TOKENS = ("reconnect", "dhcp", "ip address", "renew", "self-assigned")


def _normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def _merge_working_payload(working_payload: dict[str, Any], record: SkillExecutionRecord) -> None:
    for key, value in record.input_summary.items():
        if value is not None and working_payload.get(key) is None:
            working_payload[key] = value

    incident_record = record.result.evidence.get("incident_record")
    if isinstance(incident_record, dict):
        for key, value in incident_record.items():
            if value is not None and working_payload.get(key) is None:
                working_payload[key] = value

    if working_payload.get("incident_summary") is None:
        complaint = working_payload.get("complaint")
        if complaint is not None:
            working_payload["incident_summary"] = complaint


def _unique_skill_order(records: list[SkillExecutionRecord]) -> list[str]:
    ordered: list[str] = []
    for record in records:
        for action in record.result.next_actions:
            if action.skill not in ordered:
                ordered.append(action.skill)
    return ordered


@dataclass(frozen=True)
class SkillChainRun:
    chain_name: str
    records: list[SkillExecutionRecord]
    suggested_next_skills: list[str]


def _run_candidate_skills(
    *,
    chain_name: str,
    initial_payload: Mapping[str, Any],
    adapters: AdapterBundle,
    candidate_skills: list[tuple[str, bool]],
    resolver: IdentifierResolver,
) -> SkillChainRun:
    working_payload = {key: value for key, value in initial_payload.items() if value is not None}
    records: list[SkillExecutionRecord] = []

    for skill_name, should_run in candidate_skills:
        if not should_run:
            continue
        record = invoke_skill(skill_name, working_payload, adapters, resolver=resolver)
        records.append(record)
        _merge_working_payload(working_payload, record)

    return SkillChainRun(
        chain_name=chain_name,
        records=records,
        suggested_next_skills=_unique_skill_order(records),
    )


def _has_switch_port_scope(payload: Mapping[str, Any]) -> bool:
    return bool(payload.get("switch_id") and payload.get("switch_port"))


def run_single_user_complaint_chain(
    payload: Mapping[str, Any],
    adapters: AdapterBundle,
    *,
    resolver: IdentifierResolver | None = None,
) -> SkillChainRun:
    active_resolver = resolver or IdentifierResolver()
    resolved_payload = active_resolver.resolve_payload(payload, adapters)
    complaint = _normalize_text(resolved_payload.get("complaint"))
    mobility_suspected = _normalize_text(resolved_payload.get("movement_state")) == "moving" or any(
        token in complaint for token in ("walking", "moving", "roaming", "between aps")
    )
    address_suspected = bool(resolved_payload.get("reconnect_helps")) or any(
        token in complaint for token in ADDRESS_HINT_TOKENS
    )
    policy_suspected = any(token in complaint for token in POLICY_HINT_TOKENS)
    has_client_scope = bool(
        resolved_payload.get("client_id") or resolved_payload.get("client_mac")
    )
    has_ap_scope = bool(
        resolved_payload.get("ap_id")
        or resolved_payload.get("ap_name")
        or resolved_payload.get("client_id")
        or resolved_payload.get("client_mac")
    )
    has_service_scope = bool(
        resolved_payload.get("site_id")
        or resolved_payload.get("client_id")
        or resolved_payload.get("client_mac")
        or resolved_payload.get("ssid")
        or resolved_payload.get("vlan_id")
    )

    return _run_candidate_skills(
        chain_name="single_user_complaint",
        initial_payload=resolved_payload,
        adapters=adapters,
        resolver=active_resolver,
        candidate_skills=[
            ("net.incident_intake", bool(payload.get("complaint"))),
            ("net.client_health", has_client_scope),
            ("net.roaming_analysis", has_client_scope and mobility_suspected),
            ("net.ap_rf_health", has_ap_scope),
            (
                "net.ap_uplink_health",
                has_ap_scope or _has_switch_port_scope(resolved_payload),
            ),
            ("net.dns_latency", has_service_scope),
            ("net.dhcp_path", has_service_scope and address_suspected),
            ("net.segmentation_policy", has_client_scope and policy_suspected),
            (
                "net.incident_correlation",
                bool(
                    payload.get("complaint")
                    or resolved_payload.get("site_id")
                    or resolved_payload.get("client_id")
                    or resolved_payload.get("client_mac")
                    or resolved_payload.get("ap_id")
                    or resolved_payload.get("switch_id")
                ),
            ),
        ],
    )


def run_site_wide_slowdown_chain(
    payload: Mapping[str, Any],
    adapters: AdapterBundle,
    *,
    resolver: IdentifierResolver | None = None,
) -> SkillChainRun:
    active_resolver = resolver or IdentifierResolver()
    resolved_payload = active_resolver.resolve_payload(payload, adapters)
    has_site_scope = bool(
        resolved_payload.get("site_id") or resolved_payload.get("source_probe_id")
    )
    has_ap_scope = bool(resolved_payload.get("ap_id") or resolved_payload.get("ap_name"))
    has_client_scope = bool(
        resolved_payload.get("client_id") or resolved_payload.get("client_mac")
    )

    return _run_candidate_skills(
        chain_name="site_wide_slowdown",
        initial_payload=resolved_payload,
        adapters=adapters,
        resolver=active_resolver,
        candidate_skills=[
            ("net.incident_intake", bool(payload.get("complaint"))),
            (
                "net.change_detection",
                bool(
                    resolved_payload.get("site_id")
                    or resolved_payload.get("ap_id")
                    or resolved_payload.get("switch_id")
                ),
            ),
            ("net.path_probe", has_site_scope),
            (
                "net.stp_loop_anomaly",
                bool(resolved_payload.get("site_id") or resolved_payload.get("switch_id")),
            ),
            (
                "net.ap_uplink_health",
                has_ap_scope or _has_switch_port_scope(resolved_payload),
            ),
            ("net.dns_latency", bool(resolved_payload.get("site_id") or has_client_scope)),
            (
                "net.dhcp_path",
                bool(
                    resolved_payload.get("site_id")
                    or resolved_payload.get("ssid")
                    or has_client_scope
                ),
            ),
            ("net.ap_rf_health", has_ap_scope),
            ("net.client_health", has_client_scope),
            (
                "net.incident_correlation",
                bool(
                    payload.get("complaint")
                    or resolved_payload.get("site_id")
                    or resolved_payload.get("client_id")
                    or resolved_payload.get("ap_id")
                    or resolved_payload.get("switch_id")
                ),
            ),
        ],
    )