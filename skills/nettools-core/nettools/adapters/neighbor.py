from __future__ import annotations

from abc import abstractmethod

from ..models import NeighborRecord
from .base import AdapterContext, BaseAdapter


class NeighborDiscoveryAdapter(BaseAdapter):
    @abstractmethod
    def get_lldp_neighbors(
        self,
        *,
        site_id: str | None = None,
        device_id: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[NeighborRecord]:
        raise NotImplementedError

    @abstractmethod
    def get_cdp_neighbors(
        self,
        *,
        site_id: str | None = None,
        device_id: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[NeighborRecord]:
        raise NotImplementedError

    @abstractmethod
    def get_bridge_fdb_entries(
        self,
        *,
        site_id: str | None = None,
        device_id: str | None = None,
        vlan_id: int | None = None,
        context: AdapterContext | None = None,
    ) -> list[NeighborRecord]:
        raise NotImplementedError

    @abstractmethod
    def get_interface_descriptions(
        self,
        *,
        site_id: str | None = None,
        device_id: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[NeighborRecord]:
        raise NotImplementedError

    @abstractmethod
    def get_stp_port_states(
        self,
        *,
        site_id: str | None = None,
        device_id: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[NeighborRecord]:
        raise NotImplementedError
