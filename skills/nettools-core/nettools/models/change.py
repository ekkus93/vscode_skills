from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field

from .common import NormalizedModel


class ChangeRecord(NormalizedModel):
    model_config = ConfigDict(extra="forbid")

    change_id: str | None = None
    category: str | None = None
    summary: str | None = None
    site_id: str | None = None
    device_id: str | None = None
    device_type: str | None = None
    changed_at: datetime | None = None
    actor: str | None = None
    before: dict[str, Any] = Field(default_factory=dict)
    after: dict[str, Any] = Field(default_factory=dict)
    relevance_score: float | None = None
    raw_change_ref: str | None = None
