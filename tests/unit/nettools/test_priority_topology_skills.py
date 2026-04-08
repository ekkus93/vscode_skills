from __future__ import annotations

from nettools.adapters import (
    StubGatewayAdapter,
    StubInventoryConfigAdapter,
    StubNeighborDiscoveryAdapter,
    StubProbeAdapter,
    StubServiceDiscoveryAdapter,
    StubSwitchAdapter,
    StubWirelessControllerAdapter,
    load_stub_fixture_file,
)
from nettools.priority1 import AdapterBundle
from nettools.priority_topology import (
    GatewayHealthInput,
    LocalRouteAnomalyInput,
    MacPathTraceInput,
    MdnsServiceDiscoveryInput,
    NeighborDiscoveryInput,
    RfInterferenceScanInput,
    SiteBaselineCompareInput,
    SubnetInventoryInput,
    TopologyMapInput,
    evaluate_gateway_health,
    evaluate_l2_neighbor_discovery,
    evaluate_local_route_anomaly,
    evaluate_mac_path_trace,
    evaluate_mdns_service_discovery,
    evaluate_rf_interference_scan,
    evaluate_site_baseline_compare,
    evaluate_subnet_inventory,
    evaluate_topology_map,
)


def build_bundle() -> AdapterBundle:
    fixtures = load_stub_fixture_file("tests/fixtures/nettools/topology_stub_payloads.json")
    return AdapterBundle(
        wireless=StubWirelessControllerAdapter(fixtures=fixtures),
        switch=StubSwitchAdapter(fixtures=fixtures),
        neighbor=StubNeighborDiscoveryAdapter(fixtures=fixtures),
        gateway=StubGatewayAdapter(fixtures=fixtures),
        probe=StubProbeAdapter(fixtures=fixtures),
        inventory=StubInventoryConfigAdapter(fixtures=fixtures),
        service_discovery=StubServiceDiscoveryAdapter(fixtures=fixtures),
    )


def test_neighbor_discovery_returns_adjacencies() -> None:
    result = evaluate_l2_neighbor_discovery(
        NeighborDiscoveryInput(site_id="site-1"),
        build_bundle(),
    )

    assert result.status.value in {"ok", "warn"}
    assert result.evidence["adjacency_count"] >= 2


def test_topology_map_builds_graph_and_path() -> None:
    result = evaluate_topology_map(
        TopologyMapInput(client_id="client-1", site_id="site-1", output_mode="graph"),
        build_bundle(),
    )

    assert result.evidence["node_count"] >= 3
    assert result.evidence["gateway_path"]["resolved_gateway"] == "gw-core-1"


def test_mac_path_trace_resolves_attachment() -> None:
    result = evaluate_mac_path_trace(
        MacPathTraceInput(mac_address="aa:bb:cc:dd:ee:ff"),
        build_bundle(),
    )

    assert result.evidence["target_mac"] == "aa:bb:cc:dd:ee:ff"
    assert any(finding.code == "CLIENT_ATTACHMENT_RESOLVED" for finding in result.findings)


def test_subnet_inventory_runs_active_scan_when_authorized() -> None:
    result = evaluate_subnet_inventory(
        SubnetInventoryInput(
            subnet_cidr="10.0.120.0/24",
            active_scan_authorized=True,
            enable_icmp_sweep=True,
            enable_arp_sweep=True,
            tcp_ports=[22, 80],
        ),
        build_bundle(),
    )

    assert result.evidence["active_scan_used"] is True
    assert result.evidence["host_count"] >= 4


def test_mdns_service_discovery_groups_services() -> None:
    result = evaluate_mdns_service_discovery(
        MdnsServiceDiscoveryInput(subnet_cidr="10.0.120.0/24"),
        build_bundle(),
    )

    assert result.evidence["service_count"] == 2
    assert "phil-laptop.local" in result.evidence["services_by_host"]


def test_gateway_health_detects_loss_and_latency() -> None:
    result = evaluate_gateway_health(GatewayHealthInput(gateway_ip="10.0.120.1"), build_bundle())

    assert result.status.value == "fail"
    assert {finding.code for finding in result.findings} >= {
        "GATEWAY_LATENCY_HIGH",
        "GATEWAY_PACKET_LOSS",
    }


def test_rf_interference_scan_detects_overlap() -> None:
    result = evaluate_rf_interference_scan(RfInterferenceScanInput(ap_id="ap-42"), build_bundle())

    assert any(finding.code == "POTENTIAL_RF_INTERFERENCE" for finding in result.findings)


def test_site_baseline_compare_detects_regression() -> None:
    result = evaluate_site_baseline_compare(
        SiteBaselineCompareInput(site_id="site-1", client_id="client-1"),
        build_bundle(),
    )

    assert any(finding.code == "BASELINE_NODE_COUNT_REGRESSION" for finding in result.findings)


def test_local_route_anomaly_detects_multiple_default_routes() -> None:
    result = evaluate_local_route_anomaly(
        LocalRouteAnomalyInput(
            site_id="site-1",
            gateway_ip="10.0.120.1",
            subnet_cidr="10.0.120.0/24",
        ),
        build_bundle(),
    )

    assert any(finding.code == "ASYMMETRIC_LOCAL_ROUTE" for finding in result.findings)