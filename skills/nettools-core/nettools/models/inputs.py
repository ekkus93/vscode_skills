from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .common import ScopeType, TimeWindow


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


class SharedInputBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    site_id: str | None = None
    client_id: str | None = None
    client_mac: str | None = None
    ap_id: str | None = None
    ap_name: str | None = None
    ssid: str | None = None
    switch_id: str | None = None
    switch_port: str | None = None
    vlan_id: str | int | None = None
    subnet_cidr: str | None = None
    gateway_ip: str | None = None
    device_id: str | None = None
    device_name: str | None = None
    hostname: str | None = None
    ip_address: str | None = None
    time_window_minutes: int = Field(default=15, ge=1)
    start_time: datetime | None = None
    end_time: datetime | None = None
    include_raw: bool = False

    @model_validator(mode="after")
    def normalize_time_window(self) -> SharedInputBase:
        if (self.start_time is None) != (self.end_time is None):
            raise ValueError("start_time and end_time must be provided together")

        if self.start_time is None and self.end_time is None:
            end_time = utc_now()
            start_time = end_time - timedelta(minutes=self.time_window_minutes)
            object.__setattr__(self, "start_time", start_time)
            object.__setattr__(self, "end_time", end_time)

        if (
            self.start_time is not None
            and self.end_time is not None
            and self.start_time > self.end_time
        ):
            raise ValueError("start_time must be earlier than or equal to end_time")

        return self

    @property
    def time_window(self) -> TimeWindow:
        assert self.start_time is not None
        assert self.end_time is not None
        return TimeWindow(start=self.start_time, end=self.end_time)

    @property
    def scope_id(self) -> str:
        for candidate in (
            self.client_id,
            self.client_mac,
            self.ap_id,
            self.ap_name,
            self.switch_port,
            self.switch_id,
            self.ssid,
            self.vlan_id,
            self.subnet_cidr,
            self.gateway_ip,
            self.device_id,
            self.device_name,
            self.hostname,
            self.ip_address,
            self.site_id,
        ):
            if candidate is not None:
                return str(candidate)
        return "unscoped"

    def resolution_candidates(self) -> dict[str, str]:
        candidates: dict[str, str] = {}
        if self.client_id:
            candidates["client_id"] = self.client_id
        if self.client_mac:
            candidates["client_mac"] = self.client_mac
        if self.ap_id:
            candidates["ap_id"] = self.ap_id
        if self.ap_name:
            candidates["ap_name"] = self.ap_name
        if self.switch_id:
            candidates["switch_id"] = self.switch_id
        if self.switch_port:
            candidates["switch_port"] = self.switch_port
        if self.subnet_cidr:
            candidates["subnet_cidr"] = self.subnet_cidr
        if self.gateway_ip:
            candidates["gateway_ip"] = self.gateway_ip
        if self.device_id:
            candidates["device_id"] = self.device_id
        if self.device_name:
            candidates["device_name"] = self.device_name
        if self.hostname:
            candidates["hostname"] = self.hostname
        if self.ip_address:
            candidates["ip_address"] = self.ip_address
        return candidates

    def to_input_summary(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)

    def default_scope_type(self) -> ScopeType:
        if self.client_id or self.client_mac:
            return ScopeType.CLIENT
        if self.ap_id or self.ap_name:
            return ScopeType.AP
        if self.switch_port:
            return ScopeType.SWITCH_PORT
        if self.vlan_id is not None:
            return ScopeType.VLAN
        if self.subnet_cidr:
            return ScopeType.SUBNET
        if self.gateway_ip:
            return ScopeType.GATEWAY
        if self.ssid:
            return ScopeType.SSID
        if self.site_id:
            return ScopeType.SITE
        return ScopeType.SERVICE
