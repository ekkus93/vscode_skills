from __future__ import annotations

from datetime import datetime

from pydantic import ConfigDict, Field

from .common import NormalizedModel


class IncidentRecord(NormalizedModel):
    model_config = ConfigDict(extra="forbid")

    incident_id: str | None = None
    reporter: str | None = None
    summary: str | None = None
    location: str | None = None
    site_id: str | None = None
    device_type: str | None = None
    client_id: str | None = None
    client_mac: str | None = None
    ssid: str | None = None
    movement_state: str | None = None
    wired_also_affected: bool | None = None
    reconnect_helps: bool | None = None
    impacted_apps: list[str] = Field(default_factory=list)
    occurred_at: datetime | None = None
    reported_at: datetime | None = None
    notes: list[str] = Field(default_factory=list)
