from __future__ import annotations

from nettools.analysis import (
    build_topology_graph,
    detect_service_name_conflicts,
    find_path,
    group_services_by_host,
    merge_host_observations,
    merge_neighbor_records,
    neighbor_record_to_edge,
    summarize_gateway_path,
)
from nettools.models import (
    HostInventoryObservation,
    NeighborRecord,
    NetworkNode,
    NodeType,
    ServiceAdvertisement,
)


def test_merge_neighbor_records_and_build_graph() -> None:
    merged = merge_neighbor_records(
        [
            NeighborRecord(
                protocol="lldp",
                local_device_id="sw-1",
                local_interface="Gi1/0/1",
                remote_device_id="ap-1",
                remote_interface="eth0",
                evidence_refs=["lldp:1"],
            ),
            NeighborRecord(
                protocol="cdp",
                local_device_id="sw-1",
                local_interface="Gi1/0/1",
                remote_device_id="ap-1",
                remote_interface="eth0",
                evidence_refs=["cdp:1"],
            ),
        ]
    )

    candidate_edges = [neighbor_record_to_edge(item) for item in merged]
    edges = [edge for edge in candidate_edges if edge is not None]
    graph = build_topology_graph(
        nodes=[
            NetworkNode(node_id="sw-1", node_type=NodeType.SWITCH),
            NetworkNode(node_id="ap-1", node_type=NodeType.ACCESS_POINT),
        ],
        edges=edges,
    )

    assert len(merged) == 1
    assert graph.confidence_summary.value in {"medium", "high"}
    assert graph.adjacency_list["sw-1"] == ["ap-1"]


def test_find_path_and_gateway_summary() -> None:
    graph = build_topology_graph(
        nodes=[
            NetworkNode(node_id="client-1", node_type=NodeType.CLIENT),
            NetworkNode(node_id="ap-1", node_type=NodeType.ACCESS_POINT),
            NetworkNode(node_id="gw-1", node_type=NodeType.GATEWAY),
        ],
        edges=[
            neighbor_record_to_edge(
                NeighborRecord(protocol="lldp", local_device_id="client-1", remote_device_id="ap-1")
            ),
            neighbor_record_to_edge(
                NeighborRecord(protocol="lldp", local_device_id="ap-1", remote_device_id="gw-1")
            ),
        ],
    )

    path = find_path(graph.adjacency_list, "client-1", "gw-1")
    summary = summarize_gateway_path(
        graph=graph,
        origin_node_id="client-1",
        gateway_node_id="gw-1",
        origin_scope="client",
    )

    assert path == ["client-1", "ap-1", "gw-1"]
    assert summary.path_node_ids == path


def test_host_merging_and_service_conflicts() -> None:
    hosts = merge_host_observations(
        [
            HostInventoryObservation(host_id="1", ip_address="10.0.0.10", mac_address="aa:bb"),
            HostInventoryObservation(
                host_id="2",
                ip_address="10.0.0.10",
                mac_address="aa:bb",
                hostname="host.local",
            ),
        ]
    )
    services = [
        ServiceAdvertisement(
            service_type="_ssh._tcp",
            instance_name="dup._ssh._tcp.local",
            hostname="host-a.local",
            ips=["10.0.0.10"],
        ),
        ServiceAdvertisement(
            service_type="_ssh._tcp",
            instance_name="dup._ssh._tcp.local",
            hostname="host-b.local",
            ips=["10.0.0.11"],
        ),
    ]

    grouped = group_services_by_host(services)
    conflicts = detect_service_name_conflicts(services)

    assert len(hosts) == 1
    assert set(grouped) == {"host-a.local", "host-b.local"}
    assert conflicts == ["dup._ssh._tcp.local"]