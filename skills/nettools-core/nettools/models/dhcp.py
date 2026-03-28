from __future__ import annotations

from pydantic import ConfigDict, Field

from .common import NormalizedModel


class DhcpSummary(NormalizedModel):
    model_config = ConfigDict(extra="forbid")

    client_id: str | None = None
    client_mac: str | None = None
    site_id: str | None = None
    ssid: str | None = None
    vlan_id: int | None = None
    success_rate_pct: float | None = None
    avg_offer_latency_ms: float | None = None
    avg_ack_latency_ms: float | None = None
    timeouts: int | None = None
    missing_offers: int | None = None
    missing_acks: int | None = None
    duplicate_offers: int | None = None
    dhcp_server: str | None = None
    relay_ip: str | None = None
    scope_name: str | None = None
    scope_utilization_pct: float | None = None
    failure_reasons: list[str] = Field(default_factory=list)
