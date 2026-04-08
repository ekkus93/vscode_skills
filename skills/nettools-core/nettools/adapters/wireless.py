from __future__ import annotations

from abc import abstractmethod

from ..models import (
    AccessPointState,
    AuthSummary,
    ClientSession,
    NeighborRecord,
    RoamEvent,
    SwitchPortState,
)
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

    @abstractmethod
    def get_ap_uplink_identity(
        self,
        *,
        ap_id: str | None = None,
        ap_name: str | None = None,
        context: AdapterContext | None = None,
    ) -> SwitchPortState | None:
        raise NotImplementedError

    @abstractmethod
    def get_connected_client_inventory(
        self,
        *,
        ap_id: str | None = None,
        ap_name: str | None = None,
        site_id: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[ClientSession]:
        raise NotImplementedError

    @abstractmethod
    def get_ssid_vlan_mapping(
        self,
        *,
        site_id: str | None = None,
        ssid: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[NeighborRecord]:
        raise NotImplementedError

    @abstractmethod
    def get_topology_hints(
        self,
        *,
        site_id: str | None = None,
        ap_id: str | None = None,
        ap_name: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[NeighborRecord]:
        raise NotImplementedError
