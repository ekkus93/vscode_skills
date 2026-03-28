from __future__ import annotations

from pydantic import ConfigDict, Field

from .common import NormalizedModel


class SegmentationSummary(NormalizedModel):
    model_config = ConfigDict(extra="forbid")

    client_id: str | None = None
    client_mac: str | None = None
    observed_ssid: str | None = None
    observed_vlan: int | None = None
    expected_vlan: int | None = None
    policy_group: str | None = None
    expected_policy_group: str | None = None
    dhcp_scope: str | None = None
    default_gateway: str | None = None
    expected_default_gateway: str | None = None
    captive_portal_state: str | None = None
    nac_state: str | None = None
    mismatch_reasons: list[str] = Field(default_factory=list)
