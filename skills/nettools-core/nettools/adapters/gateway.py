from __future__ import annotations

from abc import abstractmethod

from ..models import (
    GatewayHealthSnapshot,
    GatewayInterfaceSummary,
    HostInventoryObservation,
    NeighborCacheEntry,
    RouteEntry,
)
from .base import AdapterContext, BaseAdapter


class GatewayAdapter(BaseAdapter):
    @abstractmethod
    def get_local_routes(
        self,
        *,
        site_id: str | None = None,
        gateway_id: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[RouteEntry]:
        raise NotImplementedError

    @abstractmethod
    def get_interface_mappings(
        self,
        *,
        site_id: str | None = None,
        gateway_id: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[GatewayInterfaceSummary]:
        raise NotImplementedError

    @abstractmethod
    def get_neighbor_cache(
        self,
        *,
        site_id: str | None = None,
        gateway_id: str | None = None,
        subnet_cidr: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[NeighborCacheEntry]:
        raise NotImplementedError

    @abstractmethod
    def get_gateway_health_snapshot(
        self,
        *,
        site_id: str | None = None,
        gateway_id: str | None = None,
        context: AdapterContext | None = None,
    ) -> GatewayHealthSnapshot | None:
        raise NotImplementedError

    @abstractmethod
    def enumerate_passive_hosts(
        self,
        *,
        site_id: str | None = None,
        subnet_cidr: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[HostInventoryObservation]:
        raise NotImplementedError
