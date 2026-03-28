from __future__ import annotations

from pydantic import ConfigDict

from .common import NormalizedModel


class PathProbeResult(NormalizedModel):
    model_config = ConfigDict(extra="forbid")

    source_probe_id: str | None = None
    source_role: str | None = None
    target: str | None = None
    protocol: str | None = None
    avg_latency_ms: float | None = None
    jitter_ms: float | None = None
    loss_pct: float | None = None
    min_latency_ms: float | None = None
    max_latency_ms: float | None = None
    sample_count: int | None = None
    timeout_count: int | None = None
