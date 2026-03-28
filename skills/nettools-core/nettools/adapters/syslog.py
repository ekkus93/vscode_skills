from __future__ import annotations

from abc import abstractmethod

from .base import AdapterContext, AdapterEvent, BaseAdapter


class SyslogEventAdapter(BaseAdapter):
    @abstractmethod
    def fetch_events_by_time_window(
        self,
        *,
        context: AdapterContext,
        site_id: str | None = None,
        device_id: str | None = None,
    ) -> list[AdapterEvent]:
        raise NotImplementedError

    @abstractmethod
    def fetch_stp_related_events(
        self,
        *,
        site_id: str | None = None,
        switch_id: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[AdapterEvent]:
        raise NotImplementedError

    @abstractmethod
    def fetch_ap_controller_events(
        self,
        *,
        site_id: str | None = None,
        ap_id: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[AdapterEvent]:
        raise NotImplementedError

    @abstractmethod
    def fetch_auth_dhcp_dns_related_events(
        self,
        *,
        site_id: str | None = None,
        client_id: str | None = None,
        client_mac: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[AdapterEvent]:
        raise NotImplementedError
