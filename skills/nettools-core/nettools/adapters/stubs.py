from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from ..models import (
    AccessPointState,
    AuthSummary,
    ChangeRecord,
    ClientSession,
    DhcpSummary,
    DnsSummary,
    MacFlapEvent,
    PathProbeResult,
    RadiusServerResult,
    ResolverResult,
    RoamEvent,
    StpSummary,
    SwitchPortState,
)
from .auth import AuthAdapter
from .base import (
    AdapterContext,
    AdapterEvent,
    AuthFailureCategory,
    InterfaceCounters,
    PolicyMapping,
    ProbeRequest,
    RelayPathMetadata,
    UplinkExpectation,
    load_stub_fixture_file,
)
from .dhcp import DhcpAdapter
from .dns import DnsAdapter
from .inventory import InventoryConfigAdapter
from .probe import ProbeAdapter
from .switch import SwitchAdapter
from .syslog import SyslogEventAdapter
from .wireless import WirelessControllerAdapter


def _fixture_data_from_inputs(
    *,
    fixtures: dict[str, Any] | None,
    fixture_path: str | Path | None,
) -> dict[str, Any]:
    if fixture_path is not None:
        return load_stub_fixture_file(fixture_path)
    return fixtures or {}


class StubWirelessControllerAdapter(WirelessControllerAdapter):
    def __init__(
        self,
        *,
        provider_name: str = "stub-wireless",
        fixtures: dict[str, Any] | None = None,
        fixture_path: str | Path | None = None,
        timeout_operations: set[str] | None = None,
        unavailable_operations: set[str] | None = None,
    ) -> None:
        super().__init__(
            provider_name=provider_name,
            fixture_data=_fixture_data_from_inputs(fixtures=fixtures, fixture_path=fixture_path),
            timeout_operations=timeout_operations,
            unavailable_operations=unavailable_operations,
        )

    def get_client_session(
        self,
        *,
        client_id: str | None = None,
        client_mac: str | None = None,
        context: AdapterContext | None = None,
    ) -> ClientSession | None:
        return self.load_model("get_client_session", ClientSession, context)

    def get_client_history(
        self,
        *,
        client_id: str | None = None,
        client_mac: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[ClientSession]:
        return self.load_model_list("get_client_history", ClientSession, context)

    def get_ap_state(
        self,
        *,
        ap_id: str | None = None,
        ap_name: str | None = None,
        context: AdapterContext | None = None,
    ) -> AccessPointState | None:
        return self.load_model("get_ap_state", AccessPointState, context)

    def get_neighboring_ap_data(
        self,
        *,
        ap_id: str | None = None,
        ap_name: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[AccessPointState]:
        return self.load_model_list("get_neighboring_ap_data", AccessPointState, context)

    def get_roam_events(
        self,
        *,
        client_id: str | None = None,
        client_mac: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[RoamEvent]:
        return self.load_model_list("get_roam_events", RoamEvent, context)

    def get_auth_events(
        self,
        *,
        client_id: str | None = None,
        client_mac: str | None = None,
        context: AdapterContext | None = None,
    ) -> AuthSummary | None:
        return self.load_model("get_auth_events", AuthSummary, context)


class StubSwitchAdapter(SwitchAdapter):
    def __init__(
        self,
        *,
        provider_name: str = "stub-switch",
        fixtures: dict[str, Any] | None = None,
        fixture_path: str | Path | None = None,
        timeout_operations: set[str] | None = None,
        unavailable_operations: set[str] | None = None,
    ) -> None:
        super().__init__(
            provider_name=provider_name,
            fixture_data=_fixture_data_from_inputs(fixtures=fixtures, fixture_path=fixture_path),
            timeout_operations=timeout_operations,
            unavailable_operations=unavailable_operations,
        )

    def resolve_ap_to_switch_port(
        self,
        *,
        ap_id: str | None = None,
        ap_name: str | None = None,
        context: AdapterContext | None = None,
    ) -> SwitchPortState | None:
        return self.load_model("resolve_ap_to_switch_port", SwitchPortState, context)

    def get_switch_port_state(
        self, *, switch_id: str, port: str, context: AdapterContext | None = None
    ) -> SwitchPortState | None:
        return self.load_model("get_switch_port_state", SwitchPortState, context)

    def get_interface_counters(
        self, *, switch_id: str, port: str, context: AdapterContext | None = None
    ) -> InterfaceCounters | None:
        return self.load_model("get_interface_counters", InterfaceCounters, context)

    def get_stp_events(
        self,
        *,
        site_id: str | None = None,
        switch_id: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[StpSummary]:
        return self.load_model_list("get_stp_events", StpSummary, context)

    def get_mac_flap_events(
        self,
        *,
        site_id: str | None = None,
        switch_id: str | None = None,
        port: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[MacFlapEvent]:
        return self.load_model_list("get_mac_flap_events", MacFlapEvent, context)

    def get_topology_change_summaries(
        self,
        *,
        site_id: str | None = None,
        switch_id: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[StpSummary]:
        return self.load_model_list("get_topology_change_summaries", StpSummary, context)


class StubDhcpAdapter(DhcpAdapter):
    def __init__(
        self,
        *,
        provider_name: str = "stub-dhcp",
        fixtures: dict[str, Any] | None = None,
        fixture_path: str | Path | None = None,
        timeout_operations: set[str] | None = None,
        unavailable_operations: set[str] | None = None,
    ) -> None:
        super().__init__(
            provider_name=provider_name,
            fixture_data=_fixture_data_from_inputs(fixtures=fixtures, fixture_path=fixture_path),
            timeout_operations=timeout_operations,
            unavailable_operations=unavailable_operations,
        )

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
        return self.load_model_list("get_dhcp_transaction_summaries", DhcpSummary, context)

    def get_scope_utilization(
        self,
        *,
        site_id: str | None = None,
        vlan_id: int | None = None,
        scope_name: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[DhcpSummary]:
        return self.load_model_list("get_scope_utilization", DhcpSummary, context)

    def get_relay_path_metadata(
        self,
        *,
        site_id: str | None = None,
        vlan_id: int | None = None,
        client_mac: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[RelayPathMetadata]:
        return self.load_model_list("get_relay_path_metadata", RelayPathMetadata, context)


class StubDnsAdapter(DnsAdapter):
    def __init__(
        self,
        *,
        provider_name: str = "stub-dns",
        fixtures: dict[str, Any] | None = None,
        fixture_path: str | Path | None = None,
        timeout_operations: set[str] | None = None,
        unavailable_operations: set[str] | None = None,
    ) -> None:
        super().__init__(
            provider_name=provider_name,
            fixture_data=_fixture_data_from_inputs(fixtures=fixtures, fixture_path=fixture_path),
            timeout_operations=timeout_operations,
            unavailable_operations=unavailable_operations,
        )

    def run_dns_probes(
        self,
        *,
        queries: Sequence[str],
        site_id: str | None = None,
        client_id: str | None = None,
        probe_locations: Sequence[str] | None = None,
        context: AdapterContext | None = None,
    ) -> DnsSummary | None:
        return self.load_model("run_dns_probes", DnsSummary, context)

    def retrieve_dns_telemetry(
        self,
        *,
        site_id: str | None = None,
        client_id: str | None = None,
        context: AdapterContext | None = None,
    ) -> DnsSummary | None:
        return self.load_model("retrieve_dns_telemetry", DnsSummary, context)

    def compare_resolver_results(
        self,
        *,
        resolvers: Sequence[str],
        queries: Sequence[str] | None = None,
        site_id: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[ResolverResult]:
        return self.load_model_list("compare_resolver_results", ResolverResult, context)


class StubAuthAdapter(AuthAdapter):
    def __init__(
        self,
        *,
        provider_name: str = "stub-auth",
        fixtures: dict[str, Any] | None = None,
        fixture_path: str | Path | None = None,
        timeout_operations: set[str] | None = None,
        unavailable_operations: set[str] | None = None,
    ) -> None:
        super().__init__(
            provider_name=provider_name,
            fixture_data=_fixture_data_from_inputs(fixtures=fixtures, fixture_path=fixture_path),
            timeout_operations=timeout_operations,
            unavailable_operations=unavailable_operations,
        )

    def get_auth_event_summaries(
        self,
        *,
        client_id: str | None = None,
        client_mac: str | None = None,
        site_id: str | None = None,
        ssid: str | None = None,
        context: AdapterContext | None = None,
    ) -> AuthSummary | None:
        return self.load_model("get_auth_event_summaries", AuthSummary, context)

    def get_radius_reachability(
        self,
        *,
        site_id: str | None = None,
        ssid: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[RadiusServerResult]:
        return self.load_model_list("get_radius_reachability", RadiusServerResult, context)

    def retrieve_categorized_auth_failures(
        self,
        *,
        client_id: str | None = None,
        client_mac: str | None = None,
        site_id: str | None = None,
        ssid: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[AuthFailureCategory]:
        return self.load_model_list(
            "retrieve_categorized_auth_failures", AuthFailureCategory, context
        )


class StubProbeAdapter(ProbeAdapter):
    def __init__(
        self,
        *,
        provider_name: str = "stub-probe",
        fixtures: dict[str, Any] | None = None,
        fixture_path: str | Path | None = None,
        timeout_operations: set[str] | None = None,
        unavailable_operations: set[str] | None = None,
    ) -> None:
        super().__init__(
            provider_name=provider_name,
            fixture_data=_fixture_data_from_inputs(fixtures=fixtures, fixture_path=fixture_path),
            timeout_operations=timeout_operations,
            unavailable_operations=unavailable_operations,
        )

    def run_path_probes(
        self, *, request: ProbeRequest, context: AdapterContext | None = None
    ) -> list[PathProbeResult]:
        return self.load_model_list("run_path_probes", PathProbeResult, context)


class StubInventoryConfigAdapter(InventoryConfigAdapter):
    def __init__(
        self,
        *,
        provider_name: str = "stub-inventory",
        fixtures: dict[str, Any] | None = None,
        fixture_path: str | Path | None = None,
        timeout_operations: set[str] | None = None,
        unavailable_operations: set[str] | None = None,
    ) -> None:
        super().__init__(
            provider_name=provider_name,
            fixture_data=_fixture_data_from_inputs(fixtures=fixtures, fixture_path=fixture_path),
            timeout_operations=timeout_operations,
            unavailable_operations=unavailable_operations,
        )

    def get_expected_vlan_by_ssid_client_role(
        self, *, site_id: str, ssid: str, client_role: str, context: AdapterContext | None = None
    ) -> PolicyMapping | None:
        return self.load_model("get_expected_vlan_by_ssid_client_role", PolicyMapping, context)

    def get_expected_ap_uplink_characteristics(
        self,
        *,
        ap_id: str | None = None,
        ap_name: str | None = None,
        context: AdapterContext | None = None,
    ) -> UplinkExpectation | None:
        return self.load_model("get_expected_ap_uplink_characteristics", UplinkExpectation, context)

    def get_expected_policy_mappings(
        self,
        *,
        client_id: str | None = None,
        client_mac: str | None = None,
        site_id: str | None = None,
        ssid: str | None = None,
        context: AdapterContext | None = None,
    ) -> PolicyMapping | None:
        return self.load_model("get_expected_policy_mappings", PolicyMapping, context)

    def get_recent_config_changes(
        self,
        *,
        site_id: str | None = None,
        device_id: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[ChangeRecord]:
        return self.load_model_list("get_recent_config_changes", ChangeRecord, context)


class StubSyslogEventAdapter(SyslogEventAdapter):
    def __init__(
        self,
        *,
        provider_name: str = "stub-syslog",
        fixtures: dict[str, Any] | None = None,
        fixture_path: str | Path | None = None,
        timeout_operations: set[str] | None = None,
        unavailable_operations: set[str] | None = None,
    ) -> None:
        super().__init__(
            provider_name=provider_name,
            fixture_data=_fixture_data_from_inputs(fixtures=fixtures, fixture_path=fixture_path),
            timeout_operations=timeout_operations,
            unavailable_operations=unavailable_operations,
        )

    def fetch_events_by_time_window(
        self, *, context: AdapterContext, site_id: str | None = None, device_id: str | None = None
    ) -> list[AdapterEvent]:
        return self.load_model_list("fetch_events_by_time_window", AdapterEvent, context)

    def fetch_stp_related_events(
        self,
        *,
        site_id: str | None = None,
        switch_id: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[AdapterEvent]:
        return self.load_model_list("fetch_stp_related_events", AdapterEvent, context)

    def fetch_ap_controller_events(
        self,
        *,
        site_id: str | None = None,
        ap_id: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[AdapterEvent]:
        return self.load_model_list("fetch_ap_controller_events", AdapterEvent, context)

    def fetch_auth_dhcp_dns_related_events(
        self,
        *,
        site_id: str | None = None,
        client_id: str | None = None,
        client_mac: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[AdapterEvent]:
        return self.load_model_list("fetch_auth_dhcp_dns_related_events", AdapterEvent, context)
