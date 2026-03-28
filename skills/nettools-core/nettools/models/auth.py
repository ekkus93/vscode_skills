from __future__ import annotations

from pydantic import ConfigDict, Field

from .common import NormalizedModel


class RadiusServerResult(NormalizedModel):
    model_config = ConfigDict(extra="forbid")

    server: str | None = None
    avg_rtt_ms: float | None = None
    reachable: bool | None = None


class AuthSummary(NormalizedModel):
    model_config = ConfigDict(extra="forbid")

    client_id: str | None = None
    client_mac: str | None = None
    site_id: str | None = None
    ssid: str | None = None
    auth_success_rate_pct: float | None = None
    timeouts: int | None = None
    invalid_credentials: int | None = None
    cert_failures: int | None = None
    eap_failures: list[str] = Field(default_factory=list)
    radius_servers: list[RadiusServerResult] = Field(default_factory=list)
