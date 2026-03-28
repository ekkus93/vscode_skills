from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class WirelessThresholds(BaseModel):
    model_config = ConfigDict(extra="forbid")

    low_rssi_dbm: int = -70
    low_snr_db: int = 20
    high_retry_pct: float = 15.0
    high_channel_utilization_pct: float = 75.0


class ServiceThresholds(BaseModel):
    model_config = ConfigDict(extra="forbid")

    high_dhcp_latency_ms: int = 1500
    high_dns_latency_ms: int = 250
    auth_timeout_ms: int = 3000


class WiredThresholds(BaseModel):
    model_config = ConfigDict(extra="forbid")

    high_crc_errors: int = 100
    topology_change_churn: int = 10


class ThresholdConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    wireless: WirelessThresholds = Field(default_factory=WirelessThresholds)
    service: ServiceThresholds = Field(default_factory=ServiceThresholds)
    wired: WiredThresholds = Field(default_factory=WiredThresholds)


def default_threshold_config() -> ThresholdConfig:
    return ThresholdConfig()
