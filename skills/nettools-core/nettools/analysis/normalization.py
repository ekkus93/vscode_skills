from __future__ import annotations

from datetime import datetime
from typing import Any, TypeVar

from ..models import (
    AccessPointState,
    AuthSummary,
    ClientSession,
    DhcpSummary,
    DnsSummary,
    NormalizedModel,
    PathProbeResult,
    RadioState,
    SegmentationSummary,
    SourceMetadata,
    StpSummary,
    SwitchPortState,
)

ModelType = TypeVar("ModelType", bound=NormalizedModel)


def _build_source_metadata(
    *,
    provider: str,
    source_type: str,
    raw_ref: str | None,
    collected_at: datetime | None,
    attributes: dict[str, Any] | None = None,
) -> list[SourceMetadata]:
    return [
        SourceMetadata(
            provider=provider,
            source_type=source_type,
            collected_at=collected_at,
            raw_ref=raw_ref,
            attributes=attributes or {},
        )
    ]


def _normalize_model(
    model_type: type[ModelType],
    raw_data: dict[str, Any],
    *,
    provider: str,
    source_type: str,
    raw_ref: str | None = None,
    collected_at: datetime | None = None,
    field_aliases: dict[str, str] | None = None,
    extra_attributes: dict[str, Any] | None = None,
) -> ModelType:
    payload = dict(raw_data)
    for alias, canonical in (field_aliases or {}).items():
        if canonical not in payload and alias in payload:
            payload[canonical] = payload[alias]
        if alias != canonical:
            payload.pop(alias, None)
    payload.setdefault("observed_at", collected_at)
    existing_metadata = payload.get("source_metadata")
    normalized_metadata = _build_source_metadata(
        provider=provider,
        source_type=source_type,
        raw_ref=raw_ref,
        collected_at=collected_at,
        attributes=extra_attributes,
    )
    if isinstance(existing_metadata, list):
        payload["source_metadata"] = [*existing_metadata, *normalized_metadata]
    else:
        payload["source_metadata"] = normalized_metadata
    return model_type.model_validate(payload)


def normalize_client_session(raw_data: dict[str, Any], *, provider: str, raw_ref: str | None = None, collected_at: datetime | None = None) -> ClientSession:
    return _normalize_model(
        ClientSession,
        raw_data,
        provider=provider,
        source_type="wireless",
        raw_ref=raw_ref,
        collected_at=collected_at,
        field_aliases={
            "clientMac": "client_mac",
            "clientId": "client_id",
            "apId": "ap_id",
            "apName": "ap_name",
            "phyRateMbps": "phy_rate_mbps",
            "retryPct": "retry_pct",
            "packetLossPct": "packet_loss_pct",
            "rssi": "rssi_dbm",
            "snr": "snr_db",
        },
    )


def normalize_access_point_state(raw_data: dict[str, Any], *, provider: str, raw_ref: str | None = None, collected_at: datetime | None = None) -> AccessPointState:
    payload = dict(raw_data)
    for radio_key in ("radio_2g", "radio_5g", "radio_6g"):
        radio_payload = payload.get(radio_key)
        if isinstance(radio_payload, dict):
            payload[radio_key] = normalize_radio_state(
                radio_payload,
                provider=provider,
                raw_ref=f"{raw_ref}:{radio_key}" if raw_ref else None,
                collected_at=collected_at,
            ).model_dump(mode="python")
    return _normalize_model(
        AccessPointState,
        payload,
        provider=provider,
        source_type="wireless",
        raw_ref=raw_ref,
        collected_at=collected_at,
        field_aliases={"apId": "ap_id", "apName": "ap_name", "managementIp": "management_ip"},
    )


def normalize_radio_state(raw_data: dict[str, Any], *, provider: str, raw_ref: str | None = None, collected_at: datetime | None = None) -> RadioState:
    return _normalize_model(
        RadioState,
        raw_data,
        provider=provider,
        source_type="wireless",
        raw_ref=raw_ref,
        collected_at=collected_at,
        field_aliases={"radioId": "radio_id", "widthMHz": "width_mhz", "utilizationPct": "utilization_pct"},
    )


def normalize_switch_port_state(raw_data: dict[str, Any], *, provider: str, raw_ref: str | None = None, collected_at: datetime | None = None) -> SwitchPortState:
    return _normalize_model(
        SwitchPortState,
        raw_data,
        provider=provider,
        source_type="switch",
        raw_ref=raw_ref,
        collected_at=collected_at,
        field_aliases={"switchId": "switch_id", "allowedVlans": "allowed_vlans", "speedMbps": "speed_mbps"},
    )


def normalize_stp_summary(raw_data: dict[str, Any], *, provider: str, raw_ref: str | None = None, collected_at: datetime | None = None) -> StpSummary:
    return _normalize_model(
        StpSummary,
        raw_data,
        provider=provider,
        source_type="switch",
        raw_ref=raw_ref,
        collected_at=collected_at,
        field_aliases={"switchId": "switch_id", "topologyChanges": "topology_changes"},
    )


def normalize_dhcp_summary(raw_data: dict[str, Any], *, provider: str, raw_ref: str | None = None, collected_at: datetime | None = None) -> DhcpSummary:
    return _normalize_model(
        DhcpSummary,
        raw_data,
        provider=provider,
        source_type="dhcp",
        raw_ref=raw_ref,
        collected_at=collected_at,
        field_aliases={
            "clientMac": "client_mac",
            "offerLatencyMs": "avg_offer_latency_ms",
            "ackLatencyMs": "avg_ack_latency_ms",
            "successRatePct": "success_rate_pct",
        },
    )


def normalize_dns_summary(raw_data: dict[str, Any], *, provider: str, raw_ref: str | None = None, collected_at: datetime | None = None) -> DnsSummary:
    return _normalize_model(
        DnsSummary,
        raw_data,
        provider=provider,
        source_type="dns",
        raw_ref=raw_ref,
        collected_at=collected_at,
        field_aliases={"clientId": "client_id", "overallLatencyMs": "overall_avg_latency_ms", "timeoutPct": "overall_timeout_pct"},
    )


def normalize_auth_summary(raw_data: dict[str, Any], *, provider: str, raw_ref: str | None = None, collected_at: datetime | None = None) -> AuthSummary:
    return _normalize_model(
        AuthSummary,
        raw_data,
        provider=provider,
        source_type="auth",
        raw_ref=raw_ref,
        collected_at=collected_at,
        field_aliases={"clientMac": "client_mac", "successRatePct": "auth_success_rate_pct"},
    )


def normalize_path_probe_result(raw_data: dict[str, Any], *, provider: str, raw_ref: str | None = None, collected_at: datetime | None = None) -> PathProbeResult:
    return _normalize_model(
        PathProbeResult,
        raw_data,
        provider=provider,
        source_type="probe",
        raw_ref=raw_ref,
        collected_at=collected_at,
        field_aliases={"sourceProbeId": "source_probe_id", "avgLatencyMs": "avg_latency_ms", "lossPct": "loss_pct"},
    )


def normalize_segmentation_summary(raw_data: dict[str, Any], *, provider: str, raw_ref: str | None = None, collected_at: datetime | None = None) -> SegmentationSummary:
    return _normalize_model(
        SegmentationSummary,
        raw_data,
        provider=provider,
        source_type="inventory",
        raw_ref=raw_ref,
        collected_at=collected_at,
        field_aliases={"clientMac": "client_mac", "observedVlan": "observed_vlan", "expectedVlan": "expected_vlan"},
    )
