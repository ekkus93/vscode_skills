from __future__ import annotations

import argparse
from collections.abc import Sequence
from typing import Any

from pydantic import Field, model_validator

from .analysis import (
    build_next_actions,
    build_topology_graph,
    classify_host,
    detect_service_name_conflicts,
    group_services_by_host,
    merge_host_observations,
    merge_neighbor_records,
    neighbor_record_to_edge,
    summarize_baseline,
    summarize_gateway_path,
)
from .errors import DependencyUnavailableError, InsufficientEvidenceError
from .models import (
    Confidence,
    EdgeType,
    Finding,
    FindingSeverity,
    GatewayInterfaceSummary,
    HostInventoryObservation,
    MacLocationObservation,
    NeighborCacheEntry,
    NeighborRecord,
    NetworkEdge,
    NetworkNode,
    NodeType,
    ScopeType,
    ServiceAdvertisement,
    SharedInputBase,
    SkillResult,
    TopologyGraph,
)
from .priority1 import (
    AdapterBundle,
    _add_finding,
    _build_result,
    _provider_refs,
    build_adapter_context,
    run_priority1_cli,
)

DEFAULT_MDNS_SERVICE_TYPES = ["_ssh._tcp", "_workstation._tcp", "_http._tcp"]
DEFAULT_TCP_PORTS = [22, 80, 443, 9100]
HIGH_GATEWAY_LATENCY_MS = 20.0
HIGH_GATEWAY_PACKET_LOSS_PCT = 1.0
HIGH_RFID_INTERFERENCE_SCORE = 70.0


class NeighborDiscoveryInput(SharedInputBase):
    protocols: list[str] = Field(default_factory=list)
    include_stale: bool = False

    @model_validator(mode="after")
    def validate_scope(self) -> NeighborDiscoveryInput:
        if not any(
            (
                self.site_id,
                self.device_id,
                self.device_name,
                self.ap_id,
                self.ap_name,
                self.switch_id,
            )
        ):
            raise ValueError(
                "site_id, device_id, device_name, ap_id, ap_name, or switch_id is required"
            )
        return self


class TopologyMapInput(SharedInputBase):
    output_mode: str = "summary"
    include_active_discovery: bool = False

    @model_validator(mode="after")
    def validate_scope(self) -> TopologyMapInput:
        if self.output_mode not in {"summary", "adjacency", "graph", "path"}:
            raise ValueError("output_mode must be one of summary, adjacency, graph, or path")
        if self.scope_id == "unscoped":
            raise ValueError("at least one scope identifier is required")
        return self


class MacPathTraceInput(SharedInputBase):
    mac_address: str | None = None

    @model_validator(mode="after")
    def validate_scope(self) -> MacPathTraceInput:
        if not any(
            (
                self.mac_address,
                self.client_id,
                self.client_mac,
                self.hostname,
                self.ip_address,
            )
        ):
            raise ValueError(
                "mac_address, client_id, client_mac, hostname, or ip_address is required"
            )
        return self


class SubnetInventoryInput(SharedInputBase):
    active_scan_authorized: bool = False
    enable_icmp_sweep: bool = False
    enable_arp_sweep: bool = False
    tcp_ports: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_scope(self) -> SubnetInventoryInput:
        if not any((self.subnet_cidr, self.vlan_id, self.ssid, self.site_id, self.gateway_ip)):
            raise ValueError("subnet_cidr, vlan_id, ssid, site_id, or gateway_ip is required")
        return self


class MdnsServiceDiscoveryInput(SharedInputBase):
    service_types: list[str] = Field(default_factory=lambda: list(DEFAULT_MDNS_SERVICE_TYPES))
    hostname_pattern: str | None = None

    @model_validator(mode="after")
    def validate_scope(self) -> MdnsServiceDiscoveryInput:
        if not any((self.subnet_cidr, self.site_id, self.service_types)):
            raise ValueError("subnet_cidr, site_id, or service_types is required")
        return self


class GatewayHealthInput(SharedInputBase):
    source_probe_id: str | None = None
    source_role: str | None = None

    @model_validator(mode="after")
    def validate_scope(self) -> GatewayHealthInput:
        if not any((self.gateway_ip, self.site_id, self.subnet_cidr)):
            raise ValueError("gateway_ip, site_id, or subnet_cidr is required")
        return self


class RfInterferenceScanInput(SharedInputBase):
    @model_validator(mode="after")
    def validate_scope(self) -> RfInterferenceScanInput:
        if not any((self.ap_id, self.ap_name, self.site_id)):
            raise ValueError("ap_id, ap_name, or site_id is required")
        return self


class SiteBaselineCompareInput(SharedInputBase):
    baseline_key: str | None = None

    @model_validator(mode="after")
    def validate_scope(self) -> SiteBaselineCompareInput:
        if not self.site_id:
            raise ValueError("site_id is required")
        return self


class LocalRouteAnomalyInput(SharedInputBase):
    @model_validator(mode="after")
    def validate_scope(self) -> LocalRouteAnomalyInput:
        if not any((self.site_id, self.gateway_ip, self.subnet_cidr)):
            raise ValueError("site_id, gateway_ip, or subnet_cidr is required")
        return self


def _node(node_id: str, node_type: NodeType, **kwargs: Any) -> NetworkNode:
    return NetworkNode(node_id=node_id, node_type=node_type, **kwargs)


def _device_node_id(prefix: str, identifier: str | None) -> str | None:
    if identifier is None:
        return None
    return f"{prefix}:{identifier}"


def _nodes_from_neighbor_records(records: Sequence[NeighborRecord]) -> list[NetworkNode]:
    nodes: list[NetworkNode] = []
    seen: set[str] = set()
    for record in records:
        for device_id in (record.local_device_id, record.remote_device_id):
            if device_id is None or device_id in seen:
                continue
            seen.add(device_id)
            nodes.append(_node(device_id, NodeType.UNKNOWN, label=device_id))
    return nodes


def _gateway_node_from_interface(interface: GatewayInterfaceSummary) -> NetworkNode | None:
    gateway_id = interface.gateway_id or interface.ip_address
    if gateway_id is None:
        return None
    return _node(
        gateway_id,
        NodeType.GATEWAY,
        management_ip=interface.ip_address,
        label=interface.interface_name,
        attributes={"role": interface.role, "subnet_cidr": interface.subnet_cidr},
    )


def _inventory_node(host: HostInventoryObservation) -> NetworkNode:
    node_type = {
        "gateway": NodeType.GATEWAY,
        "ap": NodeType.ACCESS_POINT,
        "infrastructure": NodeType.SWITCH,
        "workstation": NodeType.CLIENT,
        "host": NodeType.HOST,
    }.get(classify_host(host), NodeType.UNKNOWN)
    return _node(
        host.host_id,
        node_type,
        hostname=host.hostname,
        management_ip=host.ip_address,
        mac_address=host.mac_address,
        attributes={"classification": classify_host(host), **host.attributes},
    )


def _edge_from_mac_location(mac_observation: MacLocationObservation) -> NetworkEdge | None:
    if not mac_observation.device_id:
        return None
    host_node_id = _device_node_id("host", mac_observation.mac_address)
    if host_node_id is None:
        return None
    return NetworkEdge(
        local_node_id=host_node_id,
        remote_node_id=mac_observation.device_id,
        edge_type=EdgeType.MAC_LEARNING,
        observation_source=mac_observation.learned_via,
        confidence=Confidence.MEDIUM,
        directly_observed=True,
        supporting_evidence_refs=[f"mac:{mac_observation.mac_address}"],
        attributes={
            "interface": mac_observation.interface,
            "vlan_id": mac_observation.vlan_id,
            "ip_address": mac_observation.ip_address,
        },
    )


def _edge_from_neighbor_cache(
    entry: NeighborCacheEntry,
    gateway_id: str | None,
) -> NetworkEdge | None:
    if gateway_id is None or not entry.ip_address:
        return None
    host_node_id = _device_node_id("host", entry.mac_address or entry.ip_address)
    if host_node_id is None:
        return None
    return NetworkEdge(
        local_node_id=host_node_id,
        remote_node_id=gateway_id,
        edge_type=EdgeType.ARP,
        observation_source="neighbor_cache",
        confidence=Confidence.MEDIUM,
        directly_observed=True,
        supporting_evidence_refs=[f"arp:{entry.ip_address}"],
        attributes={"interface": entry.interface_name, "state": entry.state},
    )


def _protocol_selection(selected: Sequence[str]) -> set[str]:
    if not selected:
        return {"lldp", "cdp", "bridge_fdb", "interfaces", "stp"}
    return {value.lower() for value in selected}


def evaluate_l2_neighbor_discovery(
    skill_input: NeighborDiscoveryInput, adapters: AdapterBundle
) -> SkillResult:
    if adapters.neighbor is None:
        raise DependencyUnavailableError("Neighbor-discovery adapter is not configured.")

    neighbor = adapters.neighbor
    context = build_adapter_context(skill_input)
    selected = _protocol_selection(skill_input.protocols)
    raw_records: list[NeighborRecord] = []
    protocol_counts: dict[str, int] = {}
    fetches = {
        "lldp": neighbor.get_lldp_neighbors,
        "cdp": neighbor.get_cdp_neighbors,
        "bridge_fdb": neighbor.get_bridge_fdb_entries,
        "interfaces": neighbor.get_interface_descriptions,
        "stp": neighbor.get_stp_port_states,
    }
    for protocol_name, fetch in fetches.items():
        if protocol_name not in selected:
            continue
        if protocol_name == "bridge_fdb":
            records = fetch(
                site_id=skill_input.site_id,
                device_id=skill_input.device_id or skill_input.switch_id,
                vlan_id=int(skill_input.vlan_id) if skill_input.vlan_id is not None else None,
                context=context,
            )
        else:
            records = fetch(
                site_id=skill_input.site_id,
                device_id=skill_input.device_id or skill_input.switch_id or skill_input.ap_id,
                context=context,
            )
        if not skill_input.include_stale:
            records = [record for record in records if not record.stale]
        protocol_counts[protocol_name] = len(records)
        raw_records.extend(records)

    merged_records = merge_neighbor_records(raw_records)
    findings: list[Finding] = []
    if not merged_records:
        _add_finding(
            findings,
            code="NO_NEIGHBOR_DATA_AVAILABLE",
            severity=FindingSeverity.WARN,
            message="No L2 neighbor data was available for the requested scope.",
        )
    elif any(count == 0 for count in protocol_counts.values()):
        _add_finding(
            findings,
            code="NEIGHBOR_DISCOVERY_PARTIAL",
            severity=FindingSeverity.WARN,
            message=(
                "Neighbor discovery completed with partial visibility "
                "across the selected protocols."
            ),
            metric="visible_protocols",
            value=sum(1 for count in protocol_counts.values() if count > 0),
            threshold=len(protocol_counts),
        )

    evidence = {
        "protocol_counts": protocol_counts,
        "adjacency_count": len(merged_records),
        "adjacencies": [record.model_dump(mode="json") for record in merged_records],
    }
    next_actions = build_next_actions(
        [
            (
                "net.topology_map",
                "Build a merged graph from the discovered L2 adjacencies.",
                bool(merged_records),
            ),
            (
                "net.stp_loop_anomaly",
                (
                    "Inspect switching stability if the discovered topology "
                    "looks incomplete or unstable."
                ),
                any(count == 0 for count in protocol_counts.values()) and bool(merged_records),
            ),
        ]
    )
    raw_refs = _provider_refs(
        neighbor,
        "get_lldp_neighbors",
        "get_cdp_neighbors",
        "get_bridge_fdb_entries",
        "get_interface_descriptions",
        "get_stp_port_states",
    )
    return _build_result(
        skill_name="net.l2_neighbor_discovery",
        scope_type=ScopeType.NEIGHBOR_GRAPH,
        scope_id=skill_input.scope_id,
        ok_summary=(
            "Neighbor discovery returned a consistent adjacency view for the "
            "requested scope."
        ),
        time_window=skill_input.time_window,
        evidence=evidence,
        findings=findings,
        next_actions=next_actions,
        raw_refs=raw_refs,
    )


def _build_graph_inputs(
    skill_input: SharedInputBase,
    adapters: AdapterBundle,
) -> tuple[TopologyGraph, str | None, list[Finding], list[str]]:
    context = build_adapter_context(skill_input)
    findings: list[Finding] = []
    nodes: list[NetworkNode] = []
    edges: list[NetworkEdge] = []
    raw_refs: list[str] = []

    merged_neighbors: list[NeighborRecord] = []
    if adapters.neighbor is not None:
        neighbor_records = merge_neighbor_records(
            [
                *adapters.neighbor.get_lldp_neighbors(
                    site_id=skill_input.site_id,
                    device_id=skill_input.device_id or skill_input.switch_id,
                    context=context,
                ),
                *adapters.neighbor.get_cdp_neighbors(
                    site_id=skill_input.site_id,
                    device_id=skill_input.device_id or skill_input.switch_id,
                    context=context,
                ),
                *adapters.neighbor.get_interface_descriptions(
                    site_id=skill_input.site_id,
                    device_id=skill_input.device_id or skill_input.switch_id,
                    context=context,
                ),
            ]
        )
        merged_neighbors.extend(neighbor_records)
        nodes.extend(_nodes_from_neighbor_records(neighbor_records))
        for record in neighbor_records:
            edge = neighbor_record_to_edge(record)
            if edge is not None:
                edges.append(edge)
        raw_refs.extend(
            _provider_refs(
                adapters.neighbor,
                "get_lldp_neighbors",
                "get_cdp_neighbors",
                "get_interface_descriptions",
            )
        )

    if adapters.wireless is not None and (skill_input.client_id or skill_input.client_mac):
        session = adapters.wireless.get_client_session(
            client_id=skill_input.client_id,
            client_mac=skill_input.client_mac,
            context=context,
        )
        if session is not None:
            client_node_id = _device_node_id("client", session.client_id or session.client_mac)
            ap_node_id = _device_node_id("ap", session.ap_id or session.ap_name)
            if client_node_id is not None:
                nodes.append(
                    _node(
                        client_node_id,
                        NodeType.CLIENT,
                        hostname=skill_input.hostname,
                        management_ip=skill_input.ip_address,
                        mac_address=session.client_mac,
                    )
                )
            if ap_node_id is not None:
                nodes.append(_node(ap_node_id, NodeType.ACCESS_POINT, label=session.ap_name))
            if client_node_id and ap_node_id:
                edges.append(
                    NetworkEdge(
                        local_node_id=client_node_id,
                        remote_node_id=ap_node_id,
                        edge_type=EdgeType.CONTROLLER_MAP,
                        observation_source="wireless_controller",
                        confidence=Confidence.HIGH,
                        directly_observed=True,
                        supporting_evidence_refs=[
                            f"client:{session.client_id or session.client_mac}"
                        ],
                    )
                )
            uplink = adapters.wireless.get_ap_uplink_identity(
                ap_id=session.ap_id,
                ap_name=session.ap_name,
                context=context,
            )
            if uplink is not None and ap_node_id is not None and uplink.switch_id is not None:
                nodes.append(_node(uplink.switch_id, NodeType.SWITCH, label=uplink.port))
                edges.append(
                    NetworkEdge(
                        local_node_id=ap_node_id,
                        remote_node_id=uplink.switch_id,
                        edge_type=EdgeType.AP_UPLINK,
                        observation_source="wireless_uplink_identity",
                        confidence=Confidence.HIGH,
                        directly_observed=True,
                        supporting_evidence_refs=[f"ap:{session.ap_id or session.ap_name}"],
                        attributes={"port": uplink.port},
                    )
                )
        raw_refs.extend(
            _provider_refs(
                adapters.wireless,
                "get_client_session",
                "get_ap_uplink_identity",
            )
        )

    if adapters.switch is not None:
        target_mac = getattr(skill_input, "mac_address", None) or skill_input.client_mac
        if target_mac:
            mac_locations = adapters.switch.lookup_mac_location(
                mac_address=target_mac,
                switch_id=skill_input.switch_id,
                context=context,
            )
            for observation in mac_locations:
                host_node_id = _device_node_id("host", observation.mac_address)
                if host_node_id is not None:
                    nodes.append(
                        _node(
                            host_node_id,
                            NodeType.HOST,
                            hostname=observation.hostname,
                            management_ip=observation.ip_address,
                            mac_address=observation.mac_address,
                        )
                    )
                if observation.device_id is not None:
                    nodes.append(_node(observation.device_id, NodeType.SWITCH))
                edge = _edge_from_mac_location(observation)
                if edge is not None:
                    edges.append(edge)
            raw_refs.extend(_provider_refs(adapters.switch, "lookup_mac_location"))

    gateway_node_id: str | None = None
    if adapters.gateway is not None:
        interfaces = adapters.gateway.get_interface_mappings(
            site_id=skill_input.site_id,
            gateway_id=skill_input.gateway_ip,
            context=context,
        )
        neighbor_cache = adapters.gateway.get_neighbor_cache(
            site_id=skill_input.site_id,
            gateway_id=skill_input.gateway_ip,
            subnet_cidr=skill_input.subnet_cidr,
            context=context,
        )
        for interface in interfaces:
            gateway_node = _gateway_node_from_interface(interface)
            if gateway_node is not None:
                nodes.append(gateway_node)
                gateway_node_id = gateway_node.node_id
                if interface.subnet_cidr is not None:
                    subnet_node = _node(
                        interface.subnet_cidr,
                        NodeType.SUBNET,
                        label=interface.subnet_cidr,
                    )
                    nodes.append(subnet_node)
                    edges.append(
                        NetworkEdge(
                            local_node_id=gateway_node.node_id,
                            remote_node_id=subnet_node.node_id,
                            edge_type=EdgeType.ROUTE,
                            observation_source="gateway_interface",
                            confidence=Confidence.HIGH,
                            directly_observed=True,
                            supporting_evidence_refs=[f"gateway:{gateway_node.node_id}"],
                            attributes={"interface": interface.interface_name},
                        )
                    )
        for entry in neighbor_cache:
            host_node_id = _device_node_id("host", entry.mac_address or entry.ip_address)
            if host_node_id is not None:
                nodes.append(
                    _node(
                        host_node_id,
                        NodeType.HOST,
                        hostname=entry.hostname,
                        management_ip=entry.ip_address,
                        mac_address=entry.mac_address,
                    )
                )
            edge = _edge_from_neighbor_cache(entry, gateway_node_id)
            if edge is not None:
                edges.append(edge)
        raw_refs.extend(
            _provider_refs(
                adapters.gateway,
                "get_interface_mappings",
                "get_gateway_neighbor_cache",
            )
        )

    graph = build_topology_graph(nodes=nodes, edges=edges, unresolved_references=[])
    if graph.unresolved_references:
        _add_finding(
            findings,
            code="TOPOLOGY_EDGE_CONFLICT",
            severity=FindingSeverity.WARN,
            message="Topology reconstruction found unresolved or conflicting edge evidence.",
            metric="unresolved_edges",
            value=len(graph.unresolved_references),
            threshold=0,
        )
    if any(edge.confidence == Confidence.LOW for edge in graph.edges):
        _add_finding(
            findings,
            code="TOPOLOGY_EDGE_INFERRED",
            severity=FindingSeverity.WARN,
            message="One or more topology edges are inferred rather than directly observed.",
        )
    return graph, gateway_node_id, findings, raw_refs


def evaluate_topology_map(skill_input: TopologyMapInput, adapters: AdapterBundle) -> SkillResult:
    graph, gateway_node_id, findings, raw_refs = _build_graph_inputs(skill_input, adapters)
    origin_node_id = graph.nodes[0].node_id if graph.nodes else skill_input.scope_id
    path_summary = summarize_gateway_path(
        graph=graph,
        origin_node_id=origin_node_id,
        gateway_node_id=gateway_node_id,
        origin_scope=skill_input.default_scope_type().value,
    )
    if path_summary.missing_segments:
        _add_finding(
            findings,
            code="GATEWAY_PATH_INCOMPLETE",
            severity=FindingSeverity.WARN,
            message="The likely path to the local gateway is incomplete.",
            metric="missing_segments",
            value=len(path_summary.missing_segments),
            threshold=0,
        )

    evidence: dict[str, Any] = {
        "graph_confidence": graph.confidence_summary.value,
        "node_count": len(graph.nodes),
        "edge_count": len(graph.edges),
        "unresolved_references": list(graph.unresolved_references),
        "gateway_path": path_summary.model_dump(mode="json"),
    }
    if skill_input.output_mode in {"adjacency", "graph"}:
        evidence["adjacency_list"] = graph.adjacency_list
    if skill_input.output_mode == "graph":
        evidence["graph"] = graph.model_dump(mode="json")

    next_actions = build_next_actions(
        [
            (
                "net.ap_uplink_health",
                (
                    "Validate the AP wired path when the graph contains "
                    "incomplete AP uplink segments."
                ),
                any(
                    edge.edge_type == EdgeType.AP_UPLINK
                    and edge.confidence != Confidence.HIGH
                    for edge in graph.edges
                ),
            ),
            (
                "net.local_route_anomaly",
                (
                    "Inspect gateway and local route anomalies when the path "
                    "to the gateway is incomplete."
                ),
                bool(path_summary.missing_segments),
            ),
            (
                "net.stp_loop_anomaly",
                "Inspect for switching instability when topology evidence conflicts.",
                any(finding.code == "TOPOLOGY_EDGE_CONFLICT" for finding in findings),
            ),
        ]
    )
    return _build_result(
        skill_name="net.topology_map",
        scope_type=skill_input.default_scope_type(),
        scope_id=skill_input.scope_id,
        ok_summary="Topology mapping produced a consistent graph for the requested scope.",
        time_window=skill_input.time_window,
        evidence=evidence,
        findings=findings,
        next_actions=next_actions,
        raw_refs=sorted(set(raw_refs)),
    )


def evaluate_mac_path_trace(skill_input: MacPathTraceInput, adapters: AdapterBundle) -> SkillResult:
    if adapters.switch is None and adapters.wireless is None and adapters.gateway is None:
        raise DependencyUnavailableError("No switch, wireless, or gateway adapter is configured.")

    context = build_adapter_context(skill_input)
    target_mac = skill_input.mac_address or skill_input.client_mac
    if (
        target_mac is None
        and adapters.wireless is not None
        and (skill_input.client_id or skill_input.client_mac)
    ):
        session = adapters.wireless.get_client_session(
            client_id=skill_input.client_id,
            client_mac=skill_input.client_mac,
            context=context,
        )
        if session is not None:
            target_mac = session.client_mac

    if (
        target_mac is None
        and adapters.gateway is not None
        and (skill_input.ip_address or skill_input.hostname)
    ):
        for entry in adapters.gateway.get_neighbor_cache(
            site_id=skill_input.site_id,
            gateway_id=skill_input.gateway_ip,
            subnet_cidr=skill_input.subnet_cidr,
            context=context,
        ):
            if skill_input.ip_address and entry.ip_address == skill_input.ip_address:
                target_mac = entry.mac_address
                break
            if skill_input.hostname and entry.hostname == skill_input.hostname:
                target_mac = entry.mac_address
                break

    findings: list[Finding] = []
    observations: list[MacLocationObservation] = []
    if target_mac and adapters.switch is not None:
        observations = adapters.switch.lookup_mac_location(
            mac_address=target_mac,
            switch_id=skill_input.switch_id,
            context=context,
        )
    if target_mac is None:
        raise InsufficientEvidenceError(
            "Unable to resolve a target MAC for the requested path trace."
        )
    if not observations:
        _add_finding(
            findings,
            code="MAC_NOT_OBSERVED",
            severity=FindingSeverity.WARN,
            message="The requested MAC address was not observed in the available switch telemetry.",
        )
    distinct_locations = {(item.device_id, item.interface) for item in observations}
    if len(distinct_locations) == 1 and observations:
        _add_finding(
            findings,
            code="CLIENT_ATTACHMENT_RESOLVED",
            severity=FindingSeverity.INFO,
            message="The client attachment point was resolved from MAC location evidence.",
        )
    elif len(distinct_locations) > 1:
        _add_finding(
            findings,
            code="CLIENT_ATTACHMENT_AMBIGUOUS",
            severity=FindingSeverity.WARN,
            message="MAC location evidence points to multiple candidate attachment points.",
            metric="candidate_locations",
            value=len(distinct_locations),
            threshold=1,
        )
    if observations and len(distinct_locations) >= 1 and len(observations) == 1:
        _add_finding(
            findings,
            code="MAC_PATH_PARTIAL",
            severity=FindingSeverity.WARN,
            message="MAC path trace resolved an attachment point but not a full end-to-end path.",
        )

    evidence = {
        "target_mac": target_mac,
        "observations": [item.model_dump(mode="json") for item in observations],
        "candidate_locations": len(distinct_locations),
    }
    next_actions = build_next_actions(
        [
            (
                "net.roaming_analysis",
                (
                    "Inspect client movement across APs if the same MAC appears "
                    "to move through the wireless estate."
                ),
                bool(skill_input.client_id or skill_input.client_mac),
            ),
            (
                "net.stp_loop_anomaly",
                "Inspect switching instability when a MAC appears on conflicting interfaces.",
                len(distinct_locations) > 1,
            ),
            (
                "net.topology_map",
                "Map the surrounding topology once the attachment point is known.",
                bool(observations),
            ),
        ]
    )
    raw_refs = []
    if adapters.switch is not None:
        raw_refs.extend(_provider_refs(adapters.switch, "lookup_mac_location"))
    if adapters.wireless is not None:
        raw_refs.extend(_provider_refs(adapters.wireless, "get_client_session"))
    if adapters.gateway is not None:
        raw_refs.extend(_provider_refs(adapters.gateway, "get_gateway_neighbor_cache"))
    return _build_result(
        skill_name="net.mac_path_trace",
        scope_type=(
            ScopeType.CLIENT
            if skill_input.client_id or skill_input.client_mac
            else ScopeType.PATH
        ),
        scope_id=skill_input.scope_id,
        ok_summary="MAC path tracing resolved a stable attachment point.",
        time_window=skill_input.time_window,
        evidence=evidence,
        findings=findings,
        next_actions=next_actions,
        raw_refs=sorted(set(raw_refs)),
    )


def _hosts_from_neighbor_cache(
    entries: Sequence[NeighborCacheEntry],
) -> list[HostInventoryObservation]:
    hosts: list[HostInventoryObservation] = []
    for entry in entries:
        host_id = entry.mac_address or entry.ip_address
        if host_id is None:
            continue
        hosts.append(
            HostInventoryObservation(
                host_id=host_id,
                hostname=entry.hostname,
                ip_address=entry.ip_address,
                mac_address=entry.mac_address,
                source="gateway_neighbor_cache",
                source_type="neighbor_cache",
                active=False,
            )
        )
    return hosts


def _hosts_from_clients(
    clients: Sequence[Any],
    *,
    subnet_cidr: str | None = None,
) -> list[HostInventoryObservation]:
    hosts: list[HostInventoryObservation] = []
    for client in clients:
        host_id = client.client_mac or client.client_id
        if host_id is None:
            continue
        hosts.append(
            HostInventoryObservation(
                host_id=host_id,
                hostname=client.client_id,
                mac_address=client.client_mac,
                subnet_cidr=subnet_cidr,
                source="wireless_controller",
                source_type="client_inventory",
                classification="workstation",
                active=False,
            )
        )
    return hosts


def _hosts_from_services(
    services: Sequence[ServiceAdvertisement],
    *,
    subnet_cidr: str | None = None,
) -> list[HostInventoryObservation]:
    hosts: list[HostInventoryObservation] = []
    for service in services:
        host_id = service.hostname or service.instance_name
        ip_address = service.ips[0] if service.ips else None
        hosts.append(
            HostInventoryObservation(
                host_id=host_id,
                hostname=service.hostname,
                ip_address=ip_address,
                subnet_cidr=subnet_cidr,
                source="service_discovery",
                source_type="service_discovery",
                classification="host",
                active=False,
            )
        )
    return hosts


def evaluate_subnet_inventory(
    skill_input: SubnetInventoryInput,
    adapters: AdapterBundle,
) -> SkillResult:
    if adapters.gateway is None and adapters.probe is None and adapters.wireless is None:
        raise DependencyUnavailableError("No gateway, probe, or wireless adapter is configured.")

    context = build_adapter_context(skill_input)
    hosts: list[HostInventoryObservation] = []
    services: list[ServiceAdvertisement] = []
    findings: list[Finding] = []
    active_scan_used = False
    gateways: list[str] = []

    if adapters.gateway is not None:
        interfaces = adapters.gateway.get_interface_mappings(
            site_id=skill_input.site_id,
            gateway_id=skill_input.gateway_ip,
            context=context,
        )
        neighbor_cache = adapters.gateway.get_neighbor_cache(
            site_id=skill_input.site_id,
            gateway_id=skill_input.gateway_ip,
            subnet_cidr=skill_input.subnet_cidr,
            context=context,
        )
        hosts.extend(_hosts_from_neighbor_cache(neighbor_cache))
        gateways.extend(
            interface.ip_address for interface in interfaces if interface.ip_address is not None
        )
        passive_hosts = adapters.gateway.enumerate_passive_hosts(
            site_id=skill_input.site_id,
            subnet_cidr=skill_input.subnet_cidr,
            context=context,
        )
        hosts.extend(passive_hosts)

    if adapters.wireless is not None:
        clients = adapters.wireless.get_connected_client_inventory(
            ap_id=skill_input.ap_id,
            ap_name=skill_input.ap_name,
            site_id=skill_input.site_id,
            context=context,
        )
        hosts.extend(_hosts_from_clients(clients, subnet_cidr=skill_input.subnet_cidr))

    if adapters.service_discovery is not None:
        services = adapters.service_discovery.browse_mdns_services(
            site_id=skill_input.site_id,
            subnet_cidr=skill_input.subnet_cidr,
            context=context,
        )
        hosts.extend(_hosts_from_services(services, subnet_cidr=skill_input.subnet_cidr))
        if services:
            _add_finding(
                findings,
                code="MDNS_SERVICES_DISCOVERED",
                severity=FindingSeverity.INFO,
                message=(
                    "Local service advertisements were discovered within the "
                    "requested subnet scope."
                ),
                metric="service_count",
                value=len(services),
                threshold=0,
            )

    if adapters.probe is not None:
        passive_hosts = adapters.probe.enumerate_passive_hosts(
            site_id=skill_input.site_id,
            subnet_cidr=skill_input.subnet_cidr,
            context=context,
        )
        hosts.extend(passive_hosts)
        if skill_input.enable_icmp_sweep or skill_input.enable_arp_sweep or skill_input.tcp_ports:
            if not skill_input.active_scan_authorized:
                _add_finding(
                    findings,
                    code="ACTIVE_SCAN_DISABLED",
                    severity=FindingSeverity.WARN,
                    message=(
                        "Active scan options were requested but authorization "
                        "was not supplied."
                    ),
                )
            else:
                if skill_input.subnet_cidr is None:
                    raise InsufficientEvidenceError(
                        "subnet_cidr is required to run active scan operations."
                    )
                active_scan_used = True
                if skill_input.enable_icmp_sweep:
                    hosts.extend(
                        adapters.probe.run_icmp_sweep(
                            subnet_cidr=skill_input.subnet_cidr,
                            context=context,
                        )
                    )
                if skill_input.enable_arp_sweep:
                    hosts.extend(
                        adapters.probe.run_arp_sweep(
                            subnet_cidr=skill_input.subnet_cidr,
                            context=context,
                        )
                    )
                if skill_input.tcp_ports:
                    hosts.extend(
                        adapters.probe.run_tcp_banner_checks(
                            subnet_cidr=skill_input.subnet_cidr,
                            ports=skill_input.tcp_ports,
                            context=context,
                        )
                    )

    merged_hosts = merge_host_observations(hosts)
    if skill_input.subnet_cidr is not None:
        summary_cidr = skill_input.subnet_cidr
    elif skill_input.vlan_id is not None:
        summary_cidr = f"vlan:{skill_input.vlan_id}"
    else:
        summary_cidr = "derived-subnet"
    evidence = {
        "subnet_cidr": summary_cidr,
        "host_count": len(merged_hosts),
        "gateway_count": len(set(gateways)),
        "service_count": len(services),
        "active_scan_used": active_scan_used,
        "hosts": [host.model_dump(mode="json") for host in merged_hosts],
        "gateways": sorted(set(gateways)),
        "services": [service.model_dump(mode="json") for service in services],
    }
    next_actions = build_next_actions(
        [
            (
                "net.mdns_service_discovery",
                (
                    "Expand local service discovery when the subnet inventory "
                    "shows active hosts but little service context."
                ),
                bool(merged_hosts) and not bool(services),
            ),
            (
                "net.topology_map",
                "Map the local graph once host inventory has identified the active devices.",
                bool(merged_hosts),
            ),
        ]
    )
    raw_refs: list[str] = []
    for adapter, operations in (
        (
            adapters.gateway,
            [
                "get_interface_mappings",
                "get_gateway_neighbor_cache",
                "enumerate_gateway_passive_hosts",
            ],
        ),
        (
            adapters.probe,
            [
                "enumerate_passive_hosts",
                "run_icmp_sweep",
                "run_arp_sweep",
                "run_tcp_banner_checks",
            ],
        ),
        (adapters.wireless, ["get_connected_client_inventory"]),
        (adapters.service_discovery, ["browse_mdns_services"]),
    ):
        if adapter is not None:
            raw_refs.extend(_provider_refs(adapter, *operations))
    return _build_result(
        skill_name="net.subnet_inventory",
        scope_type=ScopeType.SUBNET,
        scope_id=summary_cidr,
        ok_summary="Subnet inventory collected a useful passive view of local hosts and services.",
        time_window=skill_input.time_window,
        evidence=evidence,
        findings=findings,
        next_actions=next_actions,
        raw_refs=sorted(set(raw_refs)),
    )


def evaluate_mdns_service_discovery(
    skill_input: MdnsServiceDiscoveryInput, adapters: AdapterBundle
) -> SkillResult:
    if adapters.service_discovery is None:
        raise DependencyUnavailableError("Service-discovery adapter is not configured.")

    discovery = adapters.service_discovery
    context = build_adapter_context(skill_input)
    mdns_services = discovery.browse_mdns_services(
        site_id=skill_input.site_id,
        subnet_cidr=skill_input.subnet_cidr,
        service_types=skill_input.service_types,
        context=context,
    )
    dns_sd_services = discovery.browse_dns_sd_services(
        site_id=skill_input.site_id,
        subnet_cidr=skill_input.subnet_cidr,
        service_types=skill_input.service_types,
        context=context,
    )
    services = [*mdns_services, *dns_sd_services]
    if skill_input.hostname_pattern:
        services = [
            service
            for service in services
            if service.hostname and skill_input.hostname_pattern.lower() in service.hostname.lower()
        ]

    findings: list[Finding] = []
    if services:
        _add_finding(
            findings,
            code="MDNS_SERVICES_DISCOVERED",
            severity=FindingSeverity.INFO,
            message="Local mDNS or DNS-SD services were discovered.",
            metric="service_count",
            value=len(services),
            threshold=0,
        )
    conflicts = detect_service_name_conflicts(services)
    grouped = group_services_by_host(services)

    evidence = {
        "service_count": len(services),
        "service_types": sorted({service.service_type for service in services}),
        "services_by_host": {
            host: [service.model_dump(mode="json") for service in host_services]
            for host, host_services in grouped.items()
        },
        "name_conflicts": conflicts,
    }
    next_actions = build_next_actions(
        [
            (
                "net.subnet_inventory",
                "Expand passive host inventory around the discovered service advertisements.",
                bool(services),
            ),
            (
                "net.topology_map",
                "Add path context for discovered local services.",
                bool(services),
            ),
        ]
    )
    raw_refs = _provider_refs(discovery, "browse_mdns_services", "browse_dns_sd_services")
    return _build_result(
        skill_name="net.mdns_service_discovery",
        scope_type=ScopeType.SERVICE_DISCOVERY,
        scope_id=skill_input.scope_id,
        ok_summary="No significant local service advertisements were discovered.",
        time_window=skill_input.time_window,
        evidence=evidence,
        findings=findings,
        next_actions=next_actions,
        raw_refs=raw_refs,
    )


def evaluate_gateway_health(
    skill_input: GatewayHealthInput,
    adapters: AdapterBundle,
) -> SkillResult:
    if adapters.gateway is None:
        raise DependencyUnavailableError("Gateway adapter is not configured.")

    gateway = adapters.gateway
    context = build_adapter_context(skill_input)
    snapshot = gateway.get_gateway_health_snapshot(
        site_id=skill_input.site_id,
        gateway_id=skill_input.gateway_ip,
        context=context,
    )
    routes = gateway.get_local_routes(
        site_id=skill_input.site_id,
        gateway_id=skill_input.gateway_ip,
        context=context,
    )
    interfaces = gateway.get_interface_mappings(
        site_id=skill_input.site_id,
        gateway_id=skill_input.gateway_ip,
        context=context,
    )
    if snapshot is None and not routes and not interfaces:
        raise InsufficientEvidenceError(
            "Unable to locate gateway telemetry for the requested scope."
        )

    findings: list[Finding] = []
    if (
        snapshot is not None
        and snapshot.first_hop_latency_ms is not None
        and snapshot.first_hop_latency_ms >= HIGH_GATEWAY_LATENCY_MS
    ):
        _add_finding(
            findings,
            code="GATEWAY_LATENCY_HIGH",
            severity=FindingSeverity.WARN,
            message="Gateway first-hop latency is elevated.",
            metric="first_hop_latency_ms",
            value=snapshot.first_hop_latency_ms,
            threshold=HIGH_GATEWAY_LATENCY_MS,
        )
    if (
        snapshot is not None
        and snapshot.packet_loss_pct is not None
        and snapshot.packet_loss_pct >= HIGH_GATEWAY_PACKET_LOSS_PCT
    ):
        _add_finding(
            findings,
            code="GATEWAY_PACKET_LOSS",
            severity=FindingSeverity.CRITICAL,
            message="Gateway packet loss exceeds the allowed threshold.",
            metric="packet_loss_pct",
            value=snapshot.packet_loss_pct,
            threshold=HIGH_GATEWAY_PACKET_LOSS_PCT,
        )
    if snapshot is not None and snapshot.duplicate_arp_detected:
        _add_finding(
            findings,
            code="DUPLICATE_ARP_OWNER",
            severity=FindingSeverity.WARN,
            message="Gateway telemetry suggests duplicate ARP ownership on the local network.",
        )

    evidence = {
        "gateway_snapshot": snapshot.model_dump(mode="json") if snapshot is not None else None,
        "route_count": len(routes),
        "interface_count": len(interfaces),
        "routes": [route.model_dump(mode="json") for route in routes],
    }
    next_actions = build_next_actions(
        [
            (
                "net.local_route_anomaly",
                "Inspect route and ARP anomalies when gateway health is degraded.",
                bool(findings),
            ),
            (
                "net.path_probe",
                (
                    "Confirm whether gateway degradation correlates with broader "
                    "internal path problems."
                ),
                bool(findings),
            ),
        ]
    )
    return _build_result(
        skill_name="net.gateway_health",
        scope_type=ScopeType.GATEWAY,
        scope_id=skill_input.scope_id,
        ok_summary="Gateway telemetry does not indicate local first-hop health issues.",
        time_window=skill_input.time_window,
        evidence={key: value for key, value in evidence.items() if value is not None},
        findings=findings,
        next_actions=next_actions,
        raw_refs=_provider_refs(
            gateway,
            "get_gateway_health_snapshot",
            "get_local_routes",
            "get_interface_mappings",
        ),
    )


def evaluate_rf_interference_scan(
    skill_input: RfInterferenceScanInput, adapters: AdapterBundle
) -> SkillResult:
    if adapters.wireless is None:
        raise DependencyUnavailableError("Wireless adapter is not configured.")

    wireless = adapters.wireless
    context = build_adapter_context(skill_input)
    ap_state = wireless.get_ap_state(
        ap_id=skill_input.ap_id,
        ap_name=skill_input.ap_name,
        context=context,
    )
    neighbors = wireless.get_neighboring_ap_data(
        ap_id=skill_input.ap_id,
        ap_name=skill_input.ap_name,
        context=context,
    )
    if ap_state is None and not neighbors:
        raise InsufficientEvidenceError(
            "Unable to locate RF telemetry for the requested AP or site."
        )

    findings: list[Finding] = []
    primary_channel = None
    primary_utilization = None
    if ap_state is not None and ap_state.radio_5g is not None:
        primary_channel = ap_state.radio_5g.channel
        primary_utilization = ap_state.radio_5g.utilization_pct
    same_channel_neighbors = [
        neighbor
        for neighbor in neighbors
        if neighbor.radio_5g and neighbor.radio_5g.channel == primary_channel
    ]
    interference_score = float(
        len(same_channel_neighbors) * 25 + (primary_utilization or 0.0) * 0.5
    )
    if interference_score >= HIGH_RFID_INTERFERENCE_SCORE:
        _add_finding(
            findings,
            code="POTENTIAL_RF_INTERFERENCE",
            severity=FindingSeverity.WARN,
            message="Neighbor overlap and channel utilization suggest RF interference risk.",
            metric="interference_score",
            value=round(interference_score, 1),
            threshold=HIGH_RFID_INTERFERENCE_SCORE,
        )
    evidence = {
        "primary_channel": primary_channel,
        "primary_utilization_pct": primary_utilization,
        "same_channel_neighbors": len(same_channel_neighbors),
        "interference_score": round(interference_score, 1),
    }
    next_actions = build_next_actions(
        [
            (
                "net.ap_rf_health",
                "Inspect AP RF health alongside the interference indicators.",
                bool(findings),
            ),
            (
                "net.topology_map",
                (
                    "Map the local AP and uplink context when RF issues may "
                    "align with placement or wiring."
                ),
                bool(findings),
            ),
        ]
    )
    return _build_result(
        skill_name="net.rf_interference_scan",
        scope_type=ScopeType.AP if skill_input.ap_id or skill_input.ap_name else ScopeType.SITE,
        scope_id=skill_input.scope_id,
        ok_summary="RF scan results do not suggest a major interference issue.",
        time_window=skill_input.time_window,
        evidence={key: value for key, value in evidence.items() if value is not None},
        findings=findings,
        next_actions=next_actions,
        raw_refs=_provider_refs(wireless, "get_ap_state", "get_neighboring_ap_data"),
    )


def evaluate_site_baseline_compare(
    skill_input: SiteBaselineCompareInput, adapters: AdapterBundle
) -> SkillResult:
    if adapters.inventory is None:
        raise DependencyUnavailableError("Inventory adapter is not configured.")

    graph, _, findings, raw_refs = _build_graph_inputs(skill_input, adapters)
    hosts: list[HostInventoryObservation] = []
    services: list[ServiceAdvertisement] = []
    if adapters.gateway is not None:
        hosts.extend(
            adapters.gateway.enumerate_passive_hosts(
                site_id=skill_input.site_id,
                subnet_cidr=skill_input.subnet_cidr,
                context=build_adapter_context(skill_input),
            )
        )
    if adapters.service_discovery is not None:
        services = adapters.service_discovery.browse_mdns_services(
            site_id=skill_input.site_id,
            subnet_cidr=skill_input.subnet_cidr,
            context=build_adapter_context(skill_input),
        )
    current = summarize_baseline(
        graph,
        host_count=len(merge_host_observations(hosts)),
        service_count=len(services),
    )
    baseline = adapters.inventory.get_topology_baseline_snapshot(
        site_id=skill_input.site_id,
        baseline_key=skill_input.baseline_key,
        context=build_adapter_context(skill_input),
    )
    if baseline is None:
        raise InsufficientEvidenceError(
            "No topology baseline snapshot is available for the requested site."
        )

    if (
        baseline.node_count is not None
        and current.node_count is not None
        and current.node_count < baseline.node_count
    ):
        _add_finding(
            findings,
            code="BASELINE_NODE_COUNT_REGRESSION",
            severity=FindingSeverity.WARN,
            message="The current topology graph has fewer nodes than the recorded baseline.",
            metric="node_count",
            value=current.node_count,
            threshold=baseline.node_count,
        )
    if (
        baseline.host_count is not None
        and current.host_count is not None
        and current.host_count < baseline.host_count
    ):
        _add_finding(
            findings,
            code="BASELINE_HOST_VISIBILITY_DROP",
            severity=FindingSeverity.WARN,
            message="Current host visibility is below the recorded site baseline.",
            metric="host_count",
            value=current.host_count,
            threshold=baseline.host_count,
        )
    evidence = {
        "current": current.model_dump(mode="json"),
        "baseline": baseline.model_dump(mode="json"),
    }
    next_actions = build_next_actions(
        [
            (
                "net.topology_map",
                "Inspect current graph changes when the site diverges from baseline.",
                bool(findings),
            ),
            (
                "net.change_detection",
                "Correlate baseline drift with recent infrastructure changes.",
                bool(findings),
            ),
        ]
    )
    if adapters.inventory is not None:
        raw_refs.extend(_provider_refs(adapters.inventory, "get_topology_baseline_snapshot"))
    return _build_result(
        skill_name="net.site_baseline_compare",
        scope_type=ScopeType.SITE,
        scope_id=skill_input.scope_id,
        ok_summary=(
            "Current topology and host visibility are consistent with the "
            "stored site baseline."
        ),
        time_window=skill_input.time_window,
        evidence=evidence,
        findings=findings,
        next_actions=next_actions,
        raw_refs=sorted(set(raw_refs)),
        baseline_present=True,
    )


def evaluate_local_route_anomaly(
    skill_input: LocalRouteAnomalyInput, adapters: AdapterBundle
) -> SkillResult:
    if adapters.gateway is None:
        raise DependencyUnavailableError("Gateway adapter is not configured.")

    gateway = adapters.gateway
    context = build_adapter_context(skill_input)
    routes = gateway.get_local_routes(
        site_id=skill_input.site_id,
        gateway_id=skill_input.gateway_ip,
        context=context,
    )
    interfaces = gateway.get_interface_mappings(
        site_id=skill_input.site_id,
        gateway_id=skill_input.gateway_ip,
        context=context,
    )
    neighbors = gateway.get_neighbor_cache(
        site_id=skill_input.site_id,
        gateway_id=skill_input.gateway_ip,
        subnet_cidr=skill_input.subnet_cidr,
        context=context,
    )
    if not routes and not interfaces and not neighbors:
        raise InsufficientEvidenceError(
            "No route, interface, or ARP evidence is available for the requested scope."
        )

    findings: list[Finding] = []
    ip_to_mac: dict[str, set[str]] = {}
    for entry in neighbors:
        if entry.ip_address is None or entry.mac_address is None:
            continue
        ip_to_mac.setdefault(entry.ip_address, set()).add(entry.mac_address)
    duplicate_owners = sorted(ip for ip, macs in ip_to_mac.items() if len(macs) > 1)
    if duplicate_owners:
        _add_finding(
            findings,
            code="DUPLICATE_ARP_OWNER",
            severity=FindingSeverity.WARN,
            message=(
                "One or more IP addresses map to multiple MAC owners in the "
                "local neighbor cache."
            ),
            metric="duplicate_ips",
            value=len(duplicate_owners),
            threshold=0,
        )
    if (
        skill_input.subnet_cidr is not None
        and interfaces
        and all(
            interface.subnet_cidr != skill_input.subnet_cidr
            for interface in interfaces
        )
    ):
        _add_finding(
            findings,
            code="INTERFACE_SUBNET_MISMATCH",
            severity=FindingSeverity.WARN,
            message="No gateway interface mapping matched the requested subnet.",
        )
    default_routes = [route for route in routes if route.destination_cidr in {"0.0.0.0/0", "::/0"}]
    if len({route.next_hop for route in default_routes if route.next_hop}) > 1:
        _add_finding(
            findings,
            code="ASYMMETRIC_LOCAL_ROUTE",
            severity=FindingSeverity.WARN,
            message="Multiple default next hops are present in the local route summary.",
            metric="default_next_hops",
            value=len({route.next_hop for route in default_routes if route.next_hop}),
            threshold=1,
        )
    evidence = {
        "route_count": len(routes),
        "interface_count": len(interfaces),
        "neighbor_count": len(neighbors),
        "duplicate_arp_ips": duplicate_owners,
    }
    next_actions = build_next_actions(
        [
            (
                "net.gateway_health",
                "Validate gateway health when local route or ARP anomalies are present.",
                bool(findings),
            ),
            (
                "net.path_probe",
                "Correlate route anomalies with measured path degradation.",
                bool(findings),
            ),
        ]
    )
    return _build_result(
        skill_name="net.local_route_anomaly",
        scope_type=(
            ScopeType.GATEWAY
            if skill_input.gateway_ip
            else skill_input.default_scope_type()
        ),
        scope_id=skill_input.scope_id,
        ok_summary="Local route summaries do not show obvious ARP or path-selection anomalies.",
        time_window=skill_input.time_window,
        evidence=evidence,
        findings=findings,
        next_actions=next_actions,
        raw_refs=_provider_refs(
            gateway,
            "get_local_routes",
            "get_interface_mappings",
            "get_gateway_neighbor_cache",
        ),
    )


def configure_neighbor_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--protocol", action="append", dest="protocols")
    parser.add_argument("--include-stale", action="store_true")


def configure_topology_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--output-mode", default="summary")
    parser.add_argument("--include-active-discovery", action="store_true")


def configure_mac_trace_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--mac-address")


def configure_subnet_inventory_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--active-scan-authorized", action="store_true")
    parser.add_argument("--enable-icmp-sweep", action="store_true")
    parser.add_argument("--enable-arp-sweep", action="store_true")
    parser.add_argument("--tcp-port", action="append", dest="tcp_ports", type=int)


def configure_mdns_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--service-type", action="append", dest="service_types")
    parser.add_argument("--hostname-pattern")


def configure_gateway_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source-probe-id")
    parser.add_argument("--source-role")


def configure_baseline_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--baseline-key")


def main_l2_neighbor_discovery(argv: Sequence[str] | None = None) -> int:
    return run_priority1_cli(
        argv=argv,
        skill_name="net.l2_neighbor_discovery",
        description="Collect LLDP, CDP, bridge, and interface neighbor evidence.",
        scope_type=ScopeType.NEIGHBOR_GRAPH,
        input_model=NeighborDiscoveryInput,
        handler=evaluate_l2_neighbor_discovery,
        configure_parser=configure_neighbor_parser,
    )


def main_topology_map(argv: Sequence[str] | None = None) -> int:
    return run_priority1_cli(
        argv=argv,
        skill_name="net.topology_map",
        description="Build a merged local topology graph and likely path to the gateway.",
        scope_type=ScopeType.PATH,
        input_model=TopologyMapInput,
        handler=evaluate_topology_map,
        configure_parser=configure_topology_parser,
    )


def main_mac_path_trace(argv: Sequence[str] | None = None) -> int:
    return run_priority1_cli(
        argv=argv,
        skill_name="net.mac_path_trace",
        description="Trace a MAC address to its likely attachment point and surrounding path.",
        scope_type=ScopeType.PATH,
        input_model=MacPathTraceInput,
        handler=evaluate_mac_path_trace,
        configure_parser=configure_mac_trace_parser,
    )


def main_subnet_inventory(argv: Sequence[str] | None = None) -> int:
    return run_priority1_cli(
        argv=argv,
        skill_name="net.subnet_inventory",
        description=(
            "Enumerate local hosts, gateways, and passive service visibility "
            "inside a subnet scope."
        ),
        scope_type=ScopeType.SUBNET,
        input_model=SubnetInventoryInput,
        handler=evaluate_subnet_inventory,
        configure_parser=configure_subnet_inventory_parser,
    )


def main_mdns_service_discovery(argv: Sequence[str] | None = None) -> int:
    return run_priority1_cli(
        argv=argv,
        skill_name="net.mdns_service_discovery",
        description="Discover mDNS and DNS-SD services on the local network.",
        scope_type=ScopeType.SERVICE_DISCOVERY,
        input_model=MdnsServiceDiscoveryInput,
        handler=evaluate_mdns_service_discovery,
        configure_parser=configure_mdns_parser,
    )


def main_gateway_health(argv: Sequence[str] | None = None) -> int:
    return run_priority1_cli(
        argv=argv,
        skill_name="net.gateway_health",
        description="Validate local gateway latency, packet loss, and ARP health.",
        scope_type=ScopeType.GATEWAY,
        input_model=GatewayHealthInput,
        handler=evaluate_gateway_health,
        configure_parser=configure_gateway_parser,
    )


def main_rf_interference_scan(argv: Sequence[str] | None = None) -> int:
    return run_priority1_cli(
        argv=argv,
        skill_name="net.rf_interference_scan",
        description="Estimate RF interference risk from neighboring AP overlap and utilization.",
        scope_type=ScopeType.AP,
        input_model=RfInterferenceScanInput,
        handler=evaluate_rf_interference_scan,
    )


def main_site_baseline_compare(argv: Sequence[str] | None = None) -> int:
    return run_priority1_cli(
        argv=argv,
        skill_name="net.site_baseline_compare",
        description=(
            "Compare the current topology and host visibility against a saved "
            "site baseline."
        ),
        scope_type=ScopeType.SITE,
        input_model=SiteBaselineCompareInput,
        handler=evaluate_site_baseline_compare,
        configure_parser=configure_baseline_parser,
    )


def main_local_route_anomaly(argv: Sequence[str] | None = None) -> int:
    return run_priority1_cli(
        argv=argv,
        skill_name="net.local_route_anomaly",
        description="Detect duplicate ARP ownership and local route-selection anomalies.",
        scope_type=ScopeType.GATEWAY,
        input_model=LocalRouteAnomalyInput,
        handler=evaluate_local_route_anomaly,
    )