from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, TypeVar

from pydantic import ConfigDict, Field, PositiveInt, field_validator

from ..errors import (
    BadInputError,
    DependencyTimeoutError,
    DependencyUnavailableError,
    UnsupportedProviderOperationError,
)
from ..models import NormalizedModel, SourceMetadata, TimeWindow

ModelType = TypeVar("ModelType", bound=NormalizedModel)


class AdapterContext(NormalizedModel):
    model_config = ConfigDict(extra="forbid")

    time_window: TimeWindow | None = None
    timeout_seconds: float = 30.0
    include_raw: bool = False
    max_records: PositiveInt | None = None
    correlation_id: str | None = None

    @field_validator("timeout_seconds")
    @classmethod
    def validate_timeout_seconds(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("timeout_seconds must be greater than zero")
        return value


class AdapterEvent(NormalizedModel):
    model_config = ConfigDict(extra="forbid")

    event_type: str
    severity: str | None = None
    summary: str | None = None
    site_id: str | None = None
    device_id: str | None = None
    happened_at: datetime | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class InterfaceCounters(NormalizedModel):
    model_config = ConfigDict(extra="forbid")

    switch_id: str | None = None
    port: str | None = None
    input_octets: int | None = None
    output_octets: int | None = None
    input_packets: int | None = None
    output_packets: int | None = None
    input_errors: int | None = None
    output_errors: int | None = None
    crc_errors: int | None = None
    input_drops: int | None = None
    output_drops: int | None = None
    utilization_pct: float | None = None


class RelayPathMetadata(NormalizedModel):
    model_config = ConfigDict(extra="forbid")

    site_id: str | None = None
    vlan_id: int | None = None
    relay_ip: str | None = None
    relay_interface: str | None = None
    dhcp_server: str | None = None
    gateway_ip: str | None = None


class AuthFailureCategory(NormalizedModel):
    model_config = ConfigDict(extra="forbid")

    category: str
    count: int
    examples: list[str] = Field(default_factory=list)


class ProbeTarget(NormalizedModel):
    model_config = ConfigDict(extra="forbid")

    target: str
    protocol: str = "icmp"
    port: int | None = None
    labels: list[str] = Field(default_factory=list)


class ProbeRequest(NormalizedModel):
    model_config = ConfigDict(extra="forbid")

    source_probe_id: str
    source_role: str | None = None
    targets: list[ProbeTarget] = Field(default_factory=list)
    sample_count: PositiveInt = 4
    timeout_seconds: float = 5.0

    @field_validator("timeout_seconds")
    @classmethod
    def validate_probe_timeout_seconds(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("timeout_seconds must be greater than zero")
        return value


class UplinkExpectation(NormalizedModel):
    model_config = ConfigDict(extra="forbid")

    ap_id: str | None = None
    ap_name: str | None = None
    expected_switch_id: str | None = None
    expected_port: str | None = None
    expected_speed_mbps: int | None = None
    expected_poe_watts: float | None = None
    expected_native_vlan: int | None = None
    expected_allowed_vlans: list[int] = Field(default_factory=list)
    expected_trunk: bool | None = None


class PolicyMapping(NormalizedModel):
    model_config = ConfigDict(extra="forbid")

    site_id: str | None = None
    ssid: str | None = None
    client_role: str | None = None
    expected_vlan: int | None = None
    expected_policy_group: str | None = None
    expected_gateway: str | None = None


class BaseAdapter:
    def __init__(
        self,
        *,
        provider_name: str,
        default_timeout_seconds: float = 30.0,
        fixture_data: dict[str, Any] | None = None,
        timeout_operations: set[str] | None = None,
        unavailable_operations: set[str] | None = None,
    ) -> None:
        if default_timeout_seconds <= 0:
            raise BadInputError("Adapter default timeout must be greater than zero.")
        self.provider_name = provider_name
        self.default_timeout_seconds = default_timeout_seconds
        self.fixture_data = fixture_data or {}
        self.timeout_operations = timeout_operations or set()
        self.unavailable_operations = unavailable_operations or set()

    def resolve_context(self, context: AdapterContext | None = None) -> AdapterContext:
        if context is not None:
            return context
        return AdapterContext(timeout_seconds=self.default_timeout_seconds)

    def raise_for_operation(
        self, operation: str, context: AdapterContext | None = None
    ) -> AdapterContext:
        resolved_context = self.resolve_context(context)
        if operation in self.timeout_operations:
            raise DependencyTimeoutError(
                f"{self.provider_name} adapter timed out during {operation}",
                raw_refs=[f"adapter:{self.provider_name}:{operation}"],
            )
        if operation in self.unavailable_operations:
            raise DependencyUnavailableError(
                f"{self.provider_name} adapter is unavailable during {operation}",
                raw_refs=[f"adapter:{self.provider_name}:{operation}"],
            )
        return resolved_context

    def unsupported_operation(self, operation: str) -> UnsupportedProviderOperationError:
        return UnsupportedProviderOperationError(
            f"{self.provider_name} adapter does not support {operation}",
            raw_refs=[f"adapter:{self.provider_name}:{operation}"],
        )

    def load_fixture_payload(self, operation: str, context: AdapterContext | None = None) -> Any:
        self.raise_for_operation(operation, context)
        return self.fixture_data.get(operation)

    def load_model(
        self, operation: str, model_type: type[ModelType], context: AdapterContext | None = None
    ) -> ModelType | None:
        payload = self.load_fixture_payload(operation, context)
        if payload is None:
            return None
        return model_type.model_validate(payload)

    def load_model_list(
        self,
        operation: str,
        model_type: type[ModelType],
        context: AdapterContext | None = None,
    ) -> list[ModelType]:
        payload = self.load_fixture_payload(operation, context)
        if payload is None:
            return []
        return [model_type.model_validate(item) for item in payload]


def load_stub_fixture_file(path: str | Path) -> dict[str, Any]:
    fixture_path = Path(path)
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise BadInputError("Stub fixture file must contain a top-level JSON object.")
    return payload


def build_stub_source_metadata(
    provider_name: str, raw_ref: str, *, collected_at: datetime | None = None
) -> list[SourceMetadata]:
    return [
        SourceMetadata(
            provider=provider_name,
            source_type="stub",
            collected_at=collected_at,
            raw_ref=raw_ref,
        )
    ]
