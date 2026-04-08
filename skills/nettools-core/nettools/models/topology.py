from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import ConfigDict, Field

from .common import Confidence, NormalizedModel


class NodeType(str, Enum):
    CLIENT = "client"
    ACCESS_POINT = "access_point"
    SWITCH = "switch"
    ROUTER = "router"
    GATEWAY = "gateway"
    SUBNET = "subnet"
    VLAN = "vlan"
    SERVICE = "service"
    HOST = "host"
    UNKNOWN = "unknown"


class EdgeType(str, Enum):
    LLDP = "lldp"
    CDP = "cdp"
    CONTROLLER_MAP = "controller_map"
    AP_UPLINK = "ap_uplink"
    MAC_LEARNING = "mac_learning"
    ARP = "arp"
    ND = "nd"
    ROUTE = "route"
    VLAN_MEMBERSHIP = "vlan_membership"
    SERVICE_ADVERTISEMENT = "service_advertisement"
    INFERRED = "inferred"


class NetworkNode(NormalizedModel):
    model_config = ConfigDict(extra="forbid")

    node_id: str
    node_type: NodeType = NodeType.UNKNOWN
    hostname: str | None = None
    label: str | None = None
    management_ip: str | None = None
    ip_addresses: list[str] = Field(default_factory=list)
    mac_address: str | None = None
    vendor: str | None = None
    platform: str | None = None
    site_id: str | None = None
    location: str | None = None
    attributes: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class NetworkEdge(NormalizedModel):
    model_config = ConfigDict(extra="forbid")

    local_node_id: str
    remote_node_id: str
    edge_type: EdgeType = EdgeType.INFERRED
    observation_source: str | None = None
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    confidence: Confidence = Confidence.LOW
    directly_observed: bool = False
    supporting_evidence_refs: list[str] = Field(default_factory=list)
    attributes: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class TopologyGraph(NormalizedModel):
    model_config = ConfigDict(extra="forbid")

    nodes: list[NetworkNode] = Field(default_factory=list)
    edges: list[NetworkEdge] = Field(default_factory=list)
    unresolved_references: list[str] = Field(default_factory=list)
    confidence_summary: Confidence = Confidence.LOW
    graph_build_timestamp: datetime | None = None
    adjacency_list: dict[str, list[str]] = Field(default_factory=dict)


class NeighborRecord(NormalizedModel):
    model_config = ConfigDict(extra="forbid")

    protocol: str
    local_device_id: str | None = None
    local_interface: str | None = None
    remote_device_id: str | None = None
    remote_interface: str | None = None
    vlan_id: int | None = None
    segment_id: str | None = None
    stale: bool = False
    evidence_refs: list[str] = Field(default_factory=list)


class MacLocationObservation(NormalizedModel):
    model_config = ConfigDict(extra="forbid")

    mac_address: str
    device_id: str | None = None
    interface: str | None = None
    vlan_id: int | None = None
    learned_via: str | None = None
    hostname: str | None = None
    ip_address: str | None = None
    timestamp: datetime | None = None


class GatewayInterfaceSummary(NormalizedModel):
    model_config = ConfigDict(extra="forbid")

    gateway_id: str | None = None
    interface_name: str | None = None
    ip_address: str | None = None
    subnet_cidr: str | None = None
    vlan_id: int | None = None
    mac_address: str | None = None
    role: str | None = None
    status: str | None = None


class RouteEntry(NormalizedModel):
    model_config = ConfigDict(extra="forbid")

    gateway_id: str | None = None
    destination_cidr: str | None = None
    next_hop: str | None = None
    outgoing_interface: str | None = None
    protocol: str | None = None
    metric: int | None = None
    is_local: bool | None = None


class NeighborCacheEntry(NormalizedModel):
    model_config = ConfigDict(extra="forbid")

    ip_address: str | None = None
    mac_address: str | None = None
    interface_name: str | None = None
    state: str | None = None
    hostname: str | None = None
    vlan_id: int | None = None
    last_seen: datetime | None = None


class GatewayHealthSnapshot(NormalizedModel):
    model_config = ConfigDict(extra="forbid")

    gateway_id: str | None = None
    first_hop_latency_ms: float | None = None
    packet_loss_pct: float | None = None
    arp_entry_count: int | None = None
    duplicate_arp_detected: bool | None = None
    route_change_count: int | None = None
    redundancy_state: str | None = None


class GatewayPathSummary(NormalizedModel):
    model_config = ConfigDict(extra="forbid")

    origin_scope: str
    origin_id: str
    resolved_gateway: str | None = None
    path_node_ids: list[str] = Field(default_factory=list)
    missing_segments: list[str] = Field(default_factory=list)
    confidence: Confidence = Confidence.LOW
    summary: str | None = None


class ServiceAdvertisement(NormalizedModel):
    model_config = ConfigDict(extra="forbid")

    service_type: str
    instance_name: str
    hostname: str | None = None
    ips: list[str] = Field(default_factory=list)
    port: int | None = None
    txt_metadata: dict[str, str] = Field(default_factory=dict)
    observed_at: datetime | None = None


class HostInventoryObservation(NormalizedModel):
    model_config = ConfigDict(extra="forbid")

    host_id: str
    hostname: str | None = None
    ip_address: str | None = None
    mac_address: str | None = None
    subnet_cidr: str | None = None
    vlan_id: int | None = None
    source: str | None = None
    source_type: str | None = None
    classification: str | None = None
    active: bool = False
    attributes: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class SubnetInventorySummary(NormalizedModel):
    model_config = ConfigDict(extra="forbid")

    subnet_cidr: str
    observed_hosts: list[HostInventoryObservation] = Field(default_factory=list)
    gateways: list[str] = Field(default_factory=list)
    dhcp_scope_hints: list[str] = Field(default_factory=list)
    services: list[ServiceAdvertisement] = Field(default_factory=list)
    active_scan_used: bool = False
    passive_only: bool = True
    coverage_metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class TopologyBaselineSummary(NormalizedModel):
    model_config = ConfigDict(extra="forbid")

    site_id: str | None = None
    node_count: int | None = None
    edge_count: int | None = None
    host_count: int | None = None
    service_count: int | None = None
    gateway_count: int | None = None
    ap_count: int | None = None
    suspicious_gap_count: int | None = None
