from __future__ import annotations

from datetime import datetime

from pydantic import ConfigDict, Field

from .common import NormalizedModel


class RadioState(NormalizedModel):
    model_config = ConfigDict(extra="forbid")

    radio_id: str | None = None
    band: str | None = None
    channel: int | None = None
    width_mhz: int | None = None
    transmit_power_dbm: float | None = None
    utilization_pct: float | None = None
    client_count: int | None = None
    noise_floor_dbm: float | None = None
    interference_score: float | None = None
    reset_count: int | None = None
    last_reset_at: datetime | None = None


class AccessPointState(NormalizedModel):
    model_config = ConfigDict(extra="forbid")

    ap_id: str | None = None
    ap_name: str | None = None
    site_id: str | None = None
    management_ip: str | None = None
    model: str | None = None
    serial: str | None = None
    status: str | None = None
    client_count: int | None = None
    radio_resets_last_24h: int | None = None
    neighboring_ap_ids: list[str] = Field(default_factory=list)
    last_seen: datetime | None = None
    radio_2g: RadioState | None = None
    radio_5g: RadioState | None = None
    radio_6g: RadioState | None = None
