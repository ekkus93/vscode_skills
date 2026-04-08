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
    GatewayHealthSnapshot,
    GatewayInterfaceSummary,
    HostInventoryObservation,
    MacFlapEvent,
    MacLocationObservation,
    NeighborCacheEntry,
    NeighborRecord,
    PathProbeResult,
    RadiusServerResult,
    ResolverResult,
    RoamEvent,
    RouteEntry,
    ServiceAdvertisement,
    StpSummary,
    SwitchPortState,
    TopologyBaselineSummary,
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
from .gateway import GatewayAdapter
from .inventory import InventoryConfigAdapter
from .neighbor import NeighborDiscoveryAdapter
from .probe import ProbeAdapter
from .service_discovery import ServiceDiscoveryAdapter
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

    def get_ap_uplink_identity(
        self,
        *,
        ap_id: str | None = None,
        ap_name: str | None = None,
        context: AdapterContext | None = None,
    ) -> SwitchPortState | None:
        return self.load_model("get_ap_uplink_identity", SwitchPortState, context)

    def get_connected_client_inventory(
        self,
        *,
        ap_id: str | None = None,
        ap_name: str | None = None,
        site_id: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[ClientSession]:
        return self.load_model_list("get_connected_client_inventory", ClientSession, context)

    def get_ssid_vlan_mapping(
        self,
        *,
        site_id: str | None = None,
        ssid: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[NeighborRecord]:
        return self.load_model_list("get_ssid_vlan_mapping", NeighborRecord, context)

    def get_topology_hints(
        self,
        *,
        site_id: str | None = None,
        ap_id: str | None = None,
        ap_name: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[NeighborRecord]:
        return self.load_model_list("get_topology_hints", NeighborRecord, context)


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

    def lookup_mac_location(
        self,
        *,
        mac_address: str,
        switch_id: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[MacLocationObservation]:
        return self.load_model_list("lookup_mac_location", MacLocationObservation, context)

    def list_learned_macs(
        self,
        *,
        switch_id: str | None = None,
        port: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[MacLocationObservation]:
        return self.load_model_list("list_learned_macs", MacLocationObservation, context)

    def resolve_interface_vlan_membership(
        self,
        *,
        switch_id: str,
        port: str,
        context: AdapterContext | None = None,
    ) -> SwitchPortState | None:
        return self.load_model("resolve_interface_vlan_membership", SwitchPortState, context)

    def get_neighbor_cache(
        self,
        *,
        switch_id: str,
        vlan_id: int | None = None,
        context: AdapterContext | None = None,
    ) -> list[NeighborCacheEntry]:
        return self.load_model_list("get_switch_neighbor_cache", NeighborCacheEntry, context)

    def identify_interface_mode(
        self,
        *,
        switch_id: str,
        port: str,
        context: AdapterContext | None = None,
    ) -> SwitchPortState | None:
        return self.load_model("identify_interface_mode", SwitchPortState, context)


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

    def run_icmp_sweep(
        self,
        *,
        subnet_cidr: str,
        context: AdapterContext | None = None,
    ) -> list[HostInventoryObservation]:
        return self.load_model_list("run_icmp_sweep", HostInventoryObservation, context)

    def run_arp_sweep(
        self,
        *,
        subnet_cidr: str,
        context: AdapterContext | None = None,
    ) -> list[HostInventoryObservation]:
        return self.load_model_list("run_arp_sweep", HostInventoryObservation, context)

    def run_tcp_banner_checks(
        self,
        *,
        subnet_cidr: str,
        ports: list[int],
        context: AdapterContext | None = None,
    ) -> list[HostInventoryObservation]:
        return self.load_model_list("run_tcp_banner_checks", HostInventoryObservation, context)

    def enumerate_passive_hosts(
        self,
        *,
        site_id: str | None = None,
        subnet_cidr: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[HostInventoryObservation]:
        return self.load_model_list("enumerate_passive_hosts", HostInventoryObservation, context)


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

    def get_topology_baseline_snapshot(
        self,
        *,
        site_id: str,
        baseline_key: str | None = None,
        context: AdapterContext | None = None,
    ) -> TopologyBaselineSummary | None:
        return self.load_model("get_topology_baseline_snapshot", TopologyBaselineSummary, context)


class StubNeighborDiscoveryAdapter(NeighborDiscoveryAdapter):
    def __init__(
        self,
        *,
        provider_name: str = "stub-neighbor",
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

    def get_lldp_neighbors(
        self,
        *,
        site_id: str | None = None,
        device_id: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[NeighborRecord]:
        return self.load_model_list("get_lldp_neighbors", NeighborRecord, context)

    def get_cdp_neighbors(
        self,
        *,
        site_id: str | None = None,
        device_id: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[NeighborRecord]:
        return self.load_model_list("get_cdp_neighbors", NeighborRecord, context)

    def get_bridge_fdb_entries(
        self,
        *,
        site_id: str | None = None,
        device_id: str | None = None,
        vlan_id: int | None = None,
        context: AdapterContext | None = None,
    ) -> list[NeighborRecord]:
        return self.load_model_list("get_bridge_fdb_entries", NeighborRecord, context)

    def get_interface_descriptions(
        self,
        *,
        site_id: str | None = None,
        device_id: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[NeighborRecord]:
        return self.load_model_list("get_interface_descriptions", NeighborRecord, context)

    def get_stp_port_states(
        self,
        *,
        site_id: str | None = None,
        device_id: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[NeighborRecord]:
        return self.load_model_list("get_stp_port_states", NeighborRecord, context)


class StubGatewayAdapter(GatewayAdapter):
    def __init__(
        self,
        *,
        provider_name: str = "stub-gateway",
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

    def get_local_routes(
        self,
        *,
        site_id: str | None = None,
        gateway_id: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[RouteEntry]:
        return self.load_model_list("get_local_routes", RouteEntry, context)

    def get_interface_mappings(
        self,
        *,
        site_id: str | None = None,
        gateway_id: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[GatewayInterfaceSummary]:
        return self.load_model_list("get_interface_mappings", GatewayInterfaceSummary, context)

    def get_neighbor_cache(
        self,
        *,
        site_id: str | None = None,
        gateway_id: str | None = None,
        subnet_cidr: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[NeighborCacheEntry]:
        return self.load_model_list("get_gateway_neighbor_cache", NeighborCacheEntry, context)

    def get_gateway_health_snapshot(
        self,
        *,
        site_id: str | None = None,
        gateway_id: str | None = None,
        context: AdapterContext | None = None,
    ) -> GatewayHealthSnapshot | None:
        return self.load_model("get_gateway_health_snapshot", GatewayHealthSnapshot, context)

    def enumerate_passive_hosts(
        self,
        *,
        site_id: str | None = None,
        subnet_cidr: str | None = None,
        context: AdapterContext | None = None,
    ) -> list[HostInventoryObservation]:
        return self.load_model_list(
            "enumerate_gateway_passive_hosts",
            HostInventoryObservation,
            context,
        )


class StubServiceDiscoveryAdapter(ServiceDiscoveryAdapter):
    def __init__(
        self,
        *,
        provider_name: str = "stub-service-discovery",
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

    def browse_mdns_services(
        self,
        *,
        site_id: str | None = None,
        subnet_cidr: str | None = None,
        service_types: list[str] | None = None,
        context: AdapterContext | None = None,
    ) -> list[ServiceAdvertisement]:
        return self.load_model_list("browse_mdns_services", ServiceAdvertisement, context)

    def resolve_mdns_service(
        self,
        *,
        instance_name: str,
        service_type: str,
        context: AdapterContext | None = None,
    ) -> ServiceAdvertisement | None:
        return self.load_model("resolve_mdns_service", ServiceAdvertisement, context)

    def browse_dns_sd_services(
        self,
        *,
        site_id: str | None = None,
        subnet_cidr: str | None = None,
        service_types: list[str] | None = None,
        context: AdapterContext | None = None,
    ) -> list[ServiceAdvertisement]:
        return self.load_model_list("browse_dns_sd_services", ServiceAdvertisement, context)


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
