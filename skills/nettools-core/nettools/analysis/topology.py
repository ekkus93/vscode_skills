from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Iterable
from datetime import datetime, timezone

from ..models import (
    Confidence,
    EdgeType,
    GatewayPathSummary,
    HostInventoryObservation,
    NeighborRecord,
    NetworkEdge,
    NetworkNode,
    NodeType,
    ServiceAdvertisement,
    TopologyBaselineSummary,
    TopologyGraph,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def confidence_for_edge(
    *,
    direct_source_count: int,
    is_direct: bool,
    stale: bool,
    conflicting: bool,
) -> Confidence:
    if conflicting:
        return Confidence.LOW
    if is_direct and direct_source_count >= 2 and not stale:
        return Confidence.HIGH
    if is_direct and not stale:
        return Confidence.MEDIUM
    return Confidence.LOW


def merge_neighbor_records(records: Iterable[NeighborRecord]) -> list[NeighborRecord]:
    merged: dict[tuple[str | None, str | None, str | None, str | None], NeighborRecord] = {}
    for record in records:
        key = (
            record.local_device_id,
            record.local_interface,
            record.remote_device_id,
            record.remote_interface,
        )
        existing = merged.get(key)
        if existing is None:
            merged[key] = record.model_copy(deep=True)
            continue
        existing.protocol = ",".join(sorted({*existing.protocol.split(","), record.protocol}))
        existing.stale = existing.stale and record.stale
        existing.evidence_refs = sorted({*existing.evidence_refs, *record.evidence_refs})
        if existing.vlan_id is None:
            existing.vlan_id = record.vlan_id
        if existing.segment_id is None:
            existing.segment_id = record.segment_id
    return list(merged.values())


def neighbor_record_to_edge(record: NeighborRecord) -> NetworkEdge | None:
    if not record.local_device_id or not record.remote_device_id:
        return None
    protocol_tokens = {token.strip().lower() for token in record.protocol.split(",") if token}
    if "lldp" in protocol_tokens:
        edge_type = EdgeType.LLDP
    elif "cdp" in protocol_tokens:
        edge_type = EdgeType.CDP
    elif "controller_map" in protocol_tokens:
        edge_type = EdgeType.CONTROLLER_MAP
    elif "arp" in protocol_tokens:
        edge_type = EdgeType.ARP
    elif "nd" in protocol_tokens:
        edge_type = EdgeType.ND
    else:
        edge_type = EdgeType.INFERRED
    confidence = confidence_for_edge(
        direct_source_count=len(protocol_tokens),
        is_direct=edge_type != EdgeType.INFERRED,
        stale=record.stale,
        conflicting=False,
    )
    return NetworkEdge(
        local_node_id=record.local_device_id,
        remote_node_id=record.remote_device_id,
        edge_type=edge_type,
        observation_source=record.protocol,
        confidence=confidence,
        directly_observed=edge_type != EdgeType.INFERRED,
        supporting_evidence_refs=list(record.evidence_refs),
        attributes={
            "local_interface": record.local_interface,
            "remote_interface": record.remote_interface,
            "vlan_id": record.vlan_id,
            "segment_id": record.segment_id,
            "stale": record.stale,
        },
    )


def deduplicate_nodes(nodes: Iterable[NetworkNode]) -> list[NetworkNode]:
    deduped: dict[str, NetworkNode] = {}
    aliases: dict[tuple[str, str], str] = {}
    for node in nodes:
        alias_candidates = []
        if node.mac_address:
            alias_candidates.append(("mac", node.mac_address.lower()))
        if node.management_ip:
            alias_candidates.append(("ip", node.management_ip))
        if node.hostname:
            alias_candidates.append(("hostname", node.hostname.lower()))

        canonical_id = node.node_id
        for alias in alias_candidates:
            canonical_id = aliases.get(alias, canonical_id)
            if canonical_id != node.node_id:
                break

        existing = deduped.get(canonical_id)
        if existing is None:
            if canonical_id != node.node_id:
                node = node.model_copy(update={"node_id": canonical_id}, deep=True)
            deduped[canonical_id] = node
            existing = deduped[canonical_id]
        else:
            existing.ip_addresses = sorted({*existing.ip_addresses, *node.ip_addresses})
            existing.attributes = {**node.attributes, **existing.attributes}
            existing.source_metadata = [*existing.source_metadata, *node.source_metadata]
            for field_name in (
                "hostname",
                "label",
                "management_ip",
                "mac_address",
                "vendor",
                "platform",
                "site_id",
                "location",
            ):
                if getattr(existing, field_name) is None:
                    setattr(existing, field_name, getattr(node, field_name))

        for alias in alias_candidates:
            aliases[alias] = canonical_id
    return list(deduped.values())


def merge_edges(edges: Iterable[NetworkEdge]) -> tuple[list[NetworkEdge], list[str]]:
    merged: dict[tuple[str, str, str], NetworkEdge] = {}
    conflicts: list[str] = []
    for edge in edges:
        key = (edge.local_node_id, edge.remote_node_id, edge.edge_type.value)
        reverse_conflict = any(
            existing.local_node_id == edge.remote_node_id
            and existing.remote_node_id == edge.local_node_id
            and existing.edge_type != edge.edge_type
            for existing in merged.values()
        )
        if reverse_conflict:
            conflicts.append(f"{edge.local_node_id}<->{edge.remote_node_id}")
        existing = merged.get(key)
        if existing is None:
            merged[key] = edge.model_copy(deep=True)
            continue
        existing.directly_observed = existing.directly_observed or edge.directly_observed
        existing.supporting_evidence_refs = sorted(
            {*existing.supporting_evidence_refs, *edge.supporting_evidence_refs}
        )
        existing.attributes = {**existing.attributes, **edge.attributes}
        if edge.confidence == Confidence.HIGH or existing.confidence == Confidence.HIGH:
            existing.confidence = Confidence.HIGH
        elif edge.confidence == Confidence.MEDIUM or existing.confidence == Confidence.MEDIUM:
            existing.confidence = Confidence.MEDIUM
    return list(merged.values()), conflicts


def build_adjacency_list(edges: Iterable[NetworkEdge]) -> dict[str, list[str]]:
    adjacency: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        adjacency[edge.local_node_id].add(edge.remote_node_id)
        adjacency[edge.remote_node_id].add(edge.local_node_id)
    return {node_id: sorted(neighbors) for node_id, neighbors in adjacency.items()}


def graph_confidence(edges: Iterable[NetworkEdge], *, unresolved_count: int = 0) -> Confidence:
    edges_list = list(edges)
    if not edges_list:
        return Confidence.LOW
    high_count = sum(1 for edge in edges_list if edge.confidence == Confidence.HIGH)
    direct_count = sum(1 for edge in edges_list if edge.directly_observed)
    if high_count >= 2 and unresolved_count == 0:
        return Confidence.HIGH
    if direct_count >= 1:
        return Confidence.MEDIUM
    return Confidence.LOW


def build_topology_graph(
    *,
    nodes: Iterable[NetworkNode],
    edges: Iterable[NetworkEdge],
    unresolved_references: Iterable[str] | None = None,
) -> TopologyGraph:
    deduped_nodes = deduplicate_nodes(nodes)
    merged_edges, conflicts = merge_edges(edges)
    unresolved = sorted(set(unresolved_references or []))
    unresolved.extend(conflicts)
    adjacency = build_adjacency_list(merged_edges)
    return TopologyGraph(
        nodes=deduped_nodes,
        edges=merged_edges,
        unresolved_references=sorted(set(unresolved)),
        confidence_summary=graph_confidence(merged_edges, unresolved_count=len(unresolved)),
        graph_build_timestamp=utc_now(),
        adjacency_list=adjacency,
    )


def find_path(adjacency: dict[str, list[str]], start: str, goal: str) -> list[str]:
    if start == goal:
        return [start]
    queue: deque[tuple[str, list[str]]] = deque([(start, [start])])
    visited = {start}
    while queue:
        node_id, path = queue.popleft()
        for neighbor in adjacency.get(node_id, []):
            if neighbor in visited:
                continue
            if neighbor == goal:
                return [*path, neighbor]
            visited.add(neighbor)
            queue.append((neighbor, [*path, neighbor]))
    return []


def summarize_gateway_path(
    *,
    graph: TopologyGraph,
    origin_node_id: str,
    gateway_node_id: str | None,
    origin_scope: str,
) -> GatewayPathSummary:
    if gateway_node_id is None:
        return GatewayPathSummary(
            origin_scope=origin_scope,
            origin_id=origin_node_id,
            missing_segments=["gateway_unresolved"],
            confidence=Confidence.LOW,
            summary="No gateway node could be resolved from the available topology evidence.",
        )
    path = find_path(graph.adjacency_list, origin_node_id, gateway_node_id)
    if not path:
        return GatewayPathSummary(
            origin_scope=origin_scope,
            origin_id=origin_node_id,
            resolved_gateway=gateway_node_id,
            missing_segments=["path_unresolved"],
            confidence=Confidence.LOW,
            summary="The topology graph could not reconstruct a full path to the gateway.",
        )
    confidence = (
        Confidence.HIGH
        if len(path) >= 2 and not graph.unresolved_references
        else Confidence.MEDIUM
    )
    return GatewayPathSummary(
        origin_scope=origin_scope,
        origin_id=origin_node_id,
        resolved_gateway=gateway_node_id,
        path_node_ids=path,
        confidence=confidence,
        summary=(
            f"Resolved a likely path with {len(path) - 1} segments "
            f"from {origin_node_id} to {gateway_node_id}."
        ),
    )


def classify_host(observation: HostInventoryObservation) -> str:
    hostname = (observation.hostname or "").lower()
    if observation.attributes.get("is_gateway"):
        return "gateway"
    if "ap" in hostname:
        return "ap"
    if "switch" in hostname or hostname.startswith("sw-"):
        return "infrastructure"
    if observation.source_type == "service_discovery":
        return "host"
    if observation.active:
        return "workstation"
    return observation.classification or "unknown"


def merge_host_observations(
    observations: Iterable[HostInventoryObservation],
) -> list[HostInventoryObservation]:
    merged: dict[str, HostInventoryObservation] = {}
    for observation in observations:
        key = observation.mac_address or observation.ip_address or observation.host_id
        existing = merged.get(key)
        if existing is None:
            merged[key] = observation.model_copy(deep=True)
            if merged[key].classification is None:
                merged[key].classification = classify_host(merged[key])
            continue
        if existing.hostname is None:
            existing.hostname = observation.hostname
        if existing.ip_address is None:
            existing.ip_address = observation.ip_address
        if existing.mac_address is None:
            existing.mac_address = observation.mac_address
        existing.active = existing.active or observation.active
        existing.attributes = {**existing.attributes, **observation.attributes}
        existing.classification = classify_host(existing)
    return list(merged.values())


def group_services_by_host(
    services: Iterable[ServiceAdvertisement],
) -> dict[str, list[ServiceAdvertisement]]:
    grouped: dict[str, list[ServiceAdvertisement]] = defaultdict(list)
    for service in services:
        key = service.hostname or service.instance_name
        grouped[key].append(service)
    return dict(grouped)


def detect_service_name_conflicts(services: Iterable[ServiceAdvertisement]) -> list[str]:
    seen: dict[str, set[str]] = defaultdict(set)
    for service in services:
        seen[service.instance_name].update(service.ips)
    return sorted(name for name, ips in seen.items() if len(ips) > 1)


def summarize_baseline(
    graph: TopologyGraph,
    *,
    host_count: int,
    service_count: int,
) -> TopologyBaselineSummary:
    ap_count = sum(1 for node in graph.nodes if node.node_type == NodeType.ACCESS_POINT)
    gateway_count = sum(
        1 for node in graph.nodes if node.node_type in {NodeType.GATEWAY, NodeType.ROUTER}
    )
    return TopologyBaselineSummary(
        node_count=len(graph.nodes),
        edge_count=len(graph.edges),
        host_count=host_count,
        service_count=service_count,
        gateway_count=gateway_count,
        ap_count=ap_count,
        suspicious_gap_count=len(graph.unresolved_references),
    )
