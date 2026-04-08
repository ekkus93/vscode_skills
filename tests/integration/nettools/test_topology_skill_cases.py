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
from nettools.orchestrator import invoke_skill
from nettools.priority1 import AdapterBundle


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


def test_invoke_topology_map_returns_contract_result() -> None:
    record = invoke_skill(
        "net.topology_map",
        {"client_id": "client-1", "site_id": "site-1", "output_mode": "adjacency"},
        adapters=build_bundle(),
    )

    assert record.result.skill_name == "net.topology_map"
    assert record.result.evidence["adjacency_list"]


def test_invoke_subnet_inventory_returns_contract_result() -> None:
    record = invoke_skill(
        "net.subnet_inventory",
        {
            "subnet_cidr": "10.0.120.0/24",
            "active_scan_authorized": True,
            "enable_icmp_sweep": True,
        },
        adapters=build_bundle(),
    )

    assert record.result.skill_name == "net.subnet_inventory"
    assert record.result.status.value in {"ok", "warn", "fail"}