from __future__ import annotations

from datetime import datetime

from pydantic import ConfigDict, Field

from .common import NormalizedModel


class SwitchPortState(NormalizedModel):
    model_config = ConfigDict(extra="forbid")

    switch_id: str | None = None
    port: str | None = None
    description: str | None = None
    link_state: str | None = None
    speed_mbps: int | None = None
    duplex: str | None = None
    poe_watts: float | None = None
    native_vlan: int | None = None
    access_vlan: int | None = None
    allowed_vlans: list[int] = Field(default_factory=list)
    trunk: bool | None = None
    crc_errors: int | None = None
    frame_errors: int | None = None
    input_errors: int | None = None
    output_errors: int | None = None
    input_drops: int | None = None
    output_drops: int | None = None
    flaps_last_24h: int | None = None
    utilization_pct: float | None = None
    ap_id: str | None = None
    ap_name: str | None = None


class MacFlapEvent(NormalizedModel):
    model_config = ConfigDict(extra="forbid")

    mac_address: str | None = None
    vlan_id: int | None = None
    switch_id: str | None = None
    from_port: str | None = None
    to_port: str | None = None
    move_count: int | None = None
    event_time: datetime | None = None
