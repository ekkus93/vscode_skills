"""Normalized data models for NETTOOLS shared support code."""

from .ap import AccessPointState, RadioState
from .auth import AuthSummary, RadiusServerResult
from .change import ChangeRecord
from .client import ClientSession, RoamEvent
from .common import (
    Confidence,
    Finding,
    FindingSeverity,
    NextAction,
    NormalizedModel,
    ScopeType,
    SkillResult,
    SourceMetadata,
    Status,
    TimeWindow,
)
from .dhcp import DhcpSummary
from .dns import DnsSummary, ResolverResult
from .incident import IncidentRecord
from .inputs import SharedInputBase
from .path import PathProbeResult
from .segmentation import SegmentationSummary
from .stp import StpSummary
from .switch import MacFlapEvent, SwitchPortState
from .topology import (
    EdgeType,
    GatewayHealthSnapshot,
    GatewayInterfaceSummary,
    GatewayPathSummary,
    HostInventoryObservation,
    MacLocationObservation,
    NeighborCacheEntry,
    NeighborRecord,
    NetworkEdge,
    NetworkNode,
    NodeType,
    RouteEntry,
    ServiceAdvertisement,
    SubnetInventorySummary,
    TopologyBaselineSummary,
    TopologyGraph,
)

__all__ = [
    "AccessPointState",
    "AuthSummary",
    "ChangeRecord",
    "ClientSession",
    "Confidence",
    "DhcpSummary",
    "DnsSummary",
    "Finding",
    "FindingSeverity",
    "IncidentRecord",
    "MacFlapEvent",
    "MacLocationObservation",
    "NextAction",
    "NeighborCacheEntry",
    "NeighborRecord",
    "NormalizedModel",
    "NetworkEdge",
    "NetworkNode",
    "NodeType",
    "PathProbeResult",
    "RadioState",
    "RadiusServerResult",
    "ResolverResult",
    "RoamEvent",
    "RouteEntry",
    "ScopeType",
    "SegmentationSummary",
    "ServiceAdvertisement",
    "SharedInputBase",
    "SkillResult",
    "SourceMetadata",
    "Status",
    "StpSummary",
    "SubnetInventorySummary",
    "SwitchPortState",
    "TopologyBaselineSummary",
    "TopologyGraph",
    "TimeWindow",
    "EdgeType",
    "GatewayHealthSnapshot",
    "GatewayInterfaceSummary",
    "GatewayPathSummary",
    "HostInventoryObservation",
]
