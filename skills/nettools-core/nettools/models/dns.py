from __future__ import annotations

from pydantic import ConfigDict, Field

from .common import NormalizedModel


class ResolverResult(NormalizedModel):
    model_config = ConfigDict(extra="forbid")

    resolver: str | None = None
    avg_latency_ms: float | None = None
    timeout_pct: float | None = None
    nxdomain_pct: float | None = None
    source_location: str | None = None


class DnsSummary(NormalizedModel):
    model_config = ConfigDict(extra="forbid")

    site_id: str | None = None
    ssid: str | None = None
    client_id: str | None = None
    sample_queries: list[str] = Field(default_factory=list)
    resolver_results: list[ResolverResult] = Field(default_factory=list)
    overall_avg_latency_ms: float | None = None
    overall_timeout_pct: float | None = None
    probe_locations: list[str] = Field(default_factory=list)
