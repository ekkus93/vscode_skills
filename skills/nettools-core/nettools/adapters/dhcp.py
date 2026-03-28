from __future__ import annotations

from abc import abstractmethod

from ..models import DhcpSummary
from .base import AdapterContext, BaseAdapter, RelayPathMetadata


class DhcpAdapter(BaseAdapter):
    @abstractmethod
    def get_dhcp_transaction_summaries(
        self,
        *,
        client_id: str | None = None,
        client_mac: str | None = None,
        site_id: str | None = None,
        ssid: str | None = None,
        vlan_id: int | None = None,
        context: AdapterContext | None = None,
    ) -> list[DhcpSummary]:
        raise NotImplementedError

    @abstractmethod
    def get_scope_utilization(
        self,
        *,
        site_id: str | None = None,
        vlan_id: int | None = None,
        scope_name: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[DhcpSummary]:
        raise NotImplementedError

    @abstractmethod
    def get_relay_path_metadata(
        self,
        *,
        site_id: str | None = None,
        vlan_id: int | None = None,
        client_mac: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[RelayPathMetadata]:
        raise NotImplementedError