from __future__ import annotations

from abc import abstractmethod

from ..models import ChangeRecord
from .base import AdapterContext, BaseAdapter, PolicyMapping, UplinkExpectation


class InventoryConfigAdapter(BaseAdapter):
    @abstractmethod
    def get_expected_vlan_by_ssid_client_role(
        self,
        *,
        site_id: str,
        ssid: str,
        client_role: str,
        context: AdapterContext | None = None,
    ) -> PolicyMapping | None:
        raise NotImplementedError

    @abstractmethod
    def get_expected_ap_uplink_characteristics(
        self,
        *,
        ap_id: str | None = None,
        ap_name: str | None = None,
        context: AdapterContext | None = None,
    ) -> UplinkExpectation | None:
        raise NotImplementedError

    @abstractmethod
    def get_expected_policy_mappings(
        self,
        *,
        client_id: str | None = None,
        client_mac: str | None = None,
        site_id: str | None = None,
        ssid: str | None = None,
        context: AdapterContext | None = None,
    ) -> PolicyMapping | None:
        raise NotImplementedError

    @abstractmethod
    def get_recent_config_changes(
        self,
        *,
        site_id: str | None = None,
        device_id: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[ChangeRecord]:
        raise NotImplementedError