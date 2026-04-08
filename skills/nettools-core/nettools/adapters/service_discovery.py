from __future__ import annotations

from abc import abstractmethod

from ..models import ServiceAdvertisement
from .base import AdapterContext, BaseAdapter


class ServiceDiscoveryAdapter(BaseAdapter):
    @abstractmethod
    def browse_mdns_services(
        self,
        *,
        site_id: str | None = None,
        subnet_cidr: str | None = None,
        service_types: list[str] | None = None,
        context: AdapterContext | None = None,
    ) -> list[ServiceAdvertisement]:
        raise NotImplementedError

    @abstractmethod
    def resolve_mdns_service(
        self,
        *,
        instance_name: str,
        service_type: str,
        context: AdapterContext | None = None,
    ) -> ServiceAdvertisement | None:
        raise NotImplementedError

    @abstractmethod
    def browse_dns_sd_services(
        self,
        *,
        site_id: str | None = None,
        subnet_cidr: str | None = None,
        service_types: list[str] | None = None,
        context: AdapterContext | None = None,
    ) -> list[ServiceAdvertisement]:
        raise NotImplementedError
