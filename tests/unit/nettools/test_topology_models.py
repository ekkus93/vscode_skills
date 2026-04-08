from __future__ import annotations

from nettools.models import (
    Confidence,
    EdgeType,
    GatewayHealthSnapshot,
    GatewayPathSummary,
    HostInventoryObservation,
    NeighborRecord,
    NetworkEdge,
    NetworkNode,
    NodeType,
    ServiceAdvertisement,
    SubnetInventorySummary,
    TopologyBaselineSummary,
    TopologyGraph,
)


def test_topology_models_accept_partial_data() -> None:
    node = NetworkNode(node_id="ap-1", node_type=NodeType.ACCESS_POINT)
    edge = NetworkEdge(local_node_id="ap-1", remote_node_id="sw-1", edge_type=EdgeType.AP_UPLINK)
    graph = TopologyGraph(nodes=[node], edges=[edge])
    path = GatewayPathSummary(origin_scope="client", origin_id="client-1")
    service = ServiceAdvertisement(service_type="_ssh._tcp", instance_name="host._ssh._tcp.local")
    inventory = SubnetInventorySummary(subnet_cidr="10.0.120.0/24")
    snapshot = GatewayHealthSnapshot(gateway_id="gw-1")
    baseline = TopologyBaselineSummary(site_id="site-1")
    observation = HostInventoryObservation(host_id="host-1")
    neighbor = NeighborRecord(protocol="lldp")

    assert graph.confidence_summary == Confidence.LOW
    assert service.instance_name == "host._ssh._tcp.local"
    assert inventory.passive_only is True
    assert snapshot.gateway_id == "gw-1"
    assert baseline.site_id == "site-1"
    assert observation.host_id == "host-1"
    assert neighbor.protocol == "lldp"
    assert path.origin_id == "client-1"


def test_topology_graph_serializes_cleanly() -> None:
    graph = TopologyGraph(
        nodes=[NetworkNode(node_id="ap-1", node_type=NodeType.ACCESS_POINT)],
        edges=[
            NetworkEdge(
                local_node_id="ap-1",
                remote_node_id="sw-1",
                edge_type=EdgeType.AP_UPLINK,
            )
        ],
        adjacency_list={"ap-1": ["sw-1"]},
    )

    payload = graph.model_dump(mode="json")

    assert payload["nodes"][0]["node_type"] == "access_point"
    assert payload["edges"][0]["edge_type"] == "ap_uplink"
    assert payload["adjacency_list"]["ap-1"] == ["sw-1"]