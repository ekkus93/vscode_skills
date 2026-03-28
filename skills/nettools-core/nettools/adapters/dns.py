from __future__ import annotations

from abc import abstractmethod
from typing import Sequence

from ..models import DnsSummary, ResolverResult
from .base import AdapterContext, BaseAdapter


class DnsAdapter(BaseAdapter):
    @abstractmethod
    def run_dns_probes(
        self,
        *,
        queries: Sequence[str],
        site_id: str | None = None,
        client_id: str | None = None,
        probe_locations: Sequence[str] | None = None,
        context: AdapterContext | None = None,
    ) -> DnsSummary | None:
        raise NotImplementedError

    @abstractmethod
    def retrieve_dns_telemetry(
        self,
        *,
        site_id: str | None = None,
        client_id: str | None = None,
        context: AdapterContext | None = None,
    ) -> DnsSummary | None:
        raise NotImplementedError

    @abstractmethod
    def compare_resolver_results(
        self,
        *,
        resolvers: Sequence[str],
        queries: Sequence[str] | None = None,
        site_id: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[ResolverResult]:
        raise NotImplementedError