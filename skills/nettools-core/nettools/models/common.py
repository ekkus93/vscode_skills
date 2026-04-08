from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..findings import validate_finding_code


class Status(str, Enum):
    OK = "ok"
    WARN = "warn"
    FAIL = "fail"
    UNKNOWN = "unknown"


class Confidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ScopeType(str, Enum):
    CLIENT = "client"
    AP = "ap"
    SSID = "ssid"
    SWITCH_PORT = "switch_port"
    VLAN = "vlan"
    SUBNET = "subnet"
    GATEWAY = "gateway"
    SITE = "site"
    SERVICE = "service"
    NEIGHBOR_GRAPH = "neighbor_graph"
    SERVICE_DISCOVERY = "service_discovery"
    PATH = "path"


class FindingSeverity(str, Enum):
    INFO = "info"
    WARN = "warn"
    CRITICAL = "critical"


class TimeWindow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start: datetime
    end: datetime

    @model_validator(mode="after")
    def validate_order(self) -> TimeWindow:
        if self.start > self.end:
            raise ValueError("time window start must be earlier than or equal to end")
        return self


class SourceMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    source_type: str
    source_id: str | None = None
    collected_at: datetime | None = None
    raw_ref: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class NormalizedModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_version: str = "1.0"
    observed_at: datetime | None = None
    source_metadata: list[SourceMetadata] = Field(default_factory=list)


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    severity: FindingSeverity
    message: str
    metric: str | None = None
    value: Any | None = None
    threshold: Any | None = None

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        return validate_finding_code(value)


class NextAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skill: str
    reason: str


class SkillResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Status
    skill_name: str
    scope_type: ScopeType
    scope_id: str
    summary: str
    confidence: Confidence
    observed_at: datetime
    time_window: TimeWindow
    evidence: dict[str, Any] = Field(default_factory=dict)
    findings: list[Finding] = Field(default_factory=list)
    next_actions: list[NextAction] = Field(default_factory=list)
    raw_refs: list[Any] = Field(default_factory=list)
