from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class MetricComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric: str
    value: float
    threshold: float
    direction: str
    breached: bool
    delta: float
    delta_pct: float | None = None


class BaselineComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric: str
    current: float
    baseline: float
    higher_is_worse: bool = True
    regression: bool
    delta: float
    delta_pct: float | None = None


class SuspectedCause(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    score: float
    reason: str
    evidence_refs: list[str] = Field(default_factory=list)
