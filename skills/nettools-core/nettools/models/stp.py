from __future__ import annotations

from pydantic import ConfigDict, Field

from .common import NormalizedModel


class StpSummary(NormalizedModel):
    model_config = ConfigDict(extra="forbid")

    site_id: str | None = None
    switch_id: str | None = None
    topology_changes: int | None = None
    root_bridge_id: str | None = None
    root_bridge_changes: int | None = None
    blocked_port_churn: int | None = None
    unblocked_port_churn: int | None = None
    mac_flap_events: int | None = None
    suspect_ports: list[str] = Field(default_factory=list)
    broadcast_storm_detected: bool | None = None
    multicast_storm_detected: bool | None = None
    interface_utilization_spikes: list[str] = Field(default_factory=list)
