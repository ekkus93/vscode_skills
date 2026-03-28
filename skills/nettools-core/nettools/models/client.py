from __future__ import annotations

from datetime import datetime

from pydantic import ConfigDict

from .common import NormalizedModel


class RoamEvent(NormalizedModel):
    model_config = ConfigDict(extra="forbid")

    client_id: str | None = None
    client_mac: str | None = None
    from_ap_id: str | None = None
    from_ap_name: str | None = None
    to_ap_id: str | None = None
    to_ap_name: str | None = None
    latency_ms: float | None = None
    success: bool | None = None
    sticky_candidate: bool | None = None
    reason: str | None = None
    event_time: datetime | None = None


class ClientSession(NormalizedModel):
    model_config = ConfigDict(extra="forbid")

    client_id: str | None = None
    client_mac: str | None = None
    hostname: str | None = None
    username: str | None = None
    device_type: str | None = None
    operating_system: str | None = None
    site_id: str | None = None
    ssid: str | None = None
    ap_id: str | None = None
    ap_name: str | None = None
    channel: int | None = None
    band: str | None = None
    rssi_dbm: float | None = None
    snr_db: float | None = None
    retry_pct: float | None = None
    packet_loss_pct: float | None = None
    phy_rate_mbps: float | None = None
    mcs_index: int | None = None
    connected: bool | None = None
    connection_start: datetime | None = None
    last_seen: datetime | None = None
    disconnect_count: int | None = None
    reassociation_count: int | None = None
    roam_count: int | None = None
