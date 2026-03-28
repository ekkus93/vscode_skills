from __future__ import annotations

from abc import abstractmethod

from ..models import AuthSummary, RadiusServerResult
from .base import AdapterContext, AuthFailureCategory, BaseAdapter


class AuthAdapter(BaseAdapter):
    @abstractmethod
    def get_auth_event_summaries(
        self,
        *,
        client_id: str | None = None,
        client_mac: str | None = None,
        site_id: str | None = None,
        ssid: str | None = None,
        context: AdapterContext | None = None,
    ) -> AuthSummary | None:
        raise NotImplementedError

    @abstractmethod
    def get_radius_reachability(
        self,
        *,
        site_id: str | None = None,
        ssid: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[RadiusServerResult]:
        raise NotImplementedError

    @abstractmethod
    def retrieve_categorized_auth_failures(
        self,
        *,
        client_id: str | None = None,
        client_mac: str | None = None,
        site_id: str | None = None,
        ssid: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[AuthFailureCategory]:
        raise NotImplementedError
