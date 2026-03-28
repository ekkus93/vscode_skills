from __future__ import annotations

from abc import abstractmethod

from ..models import AccessPointState, AuthSummary, ClientSession, RoamEvent
from .base import AdapterContext, BaseAdapter


class WirelessControllerAdapter(BaseAdapter):
    @abstractmethod
    def get_client_session(
        self,
        *,
        client_id: str | None = None,
        client_mac: str | None = None,
        context: AdapterContext | None = None,
    ) -> ClientSession | None:
        raise NotImplementedError

    @abstractmethod
    def get_client_history(
        self,
        *,
        client_id: str | None = None,
        client_mac: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[ClientSession]:
        raise NotImplementedError

    @abstractmethod
    def get_ap_state(
        self,
        *,
        ap_id: str | None = None,
        ap_name: str | None = None,
        context: AdapterContext | None = None,
    ) -> AccessPointState | None:
        raise NotImplementedError

    @abstractmethod
    def get_neighboring_ap_data(
        self,
        *,
        ap_id: str | None = None,
        ap_name: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[AccessPointState]:
        raise NotImplementedError

    @abstractmethod
    def get_roam_events(
        self,
        *,
        client_id: str | None = None,
        client_mac: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[RoamEvent]:
        raise NotImplementedError

    @abstractmethod
    def get_auth_events(
        self,
        *,
        client_id: str | None = None,
        client_mac: str | None = None,
        context: AdapterContext | None = None,
    ) -> AuthSummary | None:
        raise NotImplementedError