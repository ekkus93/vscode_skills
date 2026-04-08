from __future__ import annotations

from abc import abstractmethod

from ..models import (
    MacFlapEvent,
    MacLocationObservation,
    NeighborCacheEntry,
    StpSummary,
    SwitchPortState,
)
from .base import AdapterContext, BaseAdapter, InterfaceCounters


class SwitchAdapter(BaseAdapter):
    @abstractmethod
    def resolve_ap_to_switch_port(
        self,
        *,
        ap_id: str | None = None,
        ap_name: str | None = None,
        context: AdapterContext | None = None,
    ) -> SwitchPortState | None:
        raise NotImplementedError

    @abstractmethod
    def get_switch_port_state(
        self,
        *,
        switch_id: str,
        port: str,
        context: AdapterContext | None = None,
    ) -> SwitchPortState | None:
        raise NotImplementedError

    @abstractmethod
    def get_interface_counters(
        self,
        *,
        switch_id: str,
        port: str,
        context: AdapterContext | None = None,
    ) -> InterfaceCounters | None:
        raise NotImplementedError

    @abstractmethod
    def get_stp_events(
        self,
        *,
        site_id: str | None = None,
        switch_id: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[StpSummary]:
        raise NotImplementedError

    @abstractmethod
    def get_mac_flap_events(
        self,
        *,
        site_id: str | None = None,
        switch_id: str | None = None,
        port: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[MacFlapEvent]:
        raise NotImplementedError

    @abstractmethod
    def get_topology_change_summaries(
        self,
        *,
        site_id: str | None = None,
        switch_id: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[StpSummary]:
        raise NotImplementedError

    @abstractmethod
    def lookup_mac_location(
        self,
        *,
        mac_address: str,
        switch_id: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[MacLocationObservation]:
        raise NotImplementedError

    @abstractmethod
    def list_learned_macs(
        self,
        *,
        switch_id: str | None = None,
        port: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[MacLocationObservation]:
        raise NotImplementedError

    @abstractmethod
    def resolve_interface_vlan_membership(
        self,
        *,
        switch_id: str,
        port: str,
        context: AdapterContext | None = None,
    ) -> SwitchPortState | None:
        raise NotImplementedError

    @abstractmethod
    def get_neighbor_cache(
        self,
        *,
        switch_id: str,
        vlan_id: int | None = None,
        context: AdapterContext | None = None,
    ) -> list[NeighborCacheEntry]:
        raise NotImplementedError

    @abstractmethod
    def identify_interface_mode(
        self,
        *,
        switch_id: str,
        port: str,
        context: AdapterContext | None = None,
    ) -> SwitchPortState | None:
        raise NotImplementedError
