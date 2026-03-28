"""Normalized data models for NETTOOLS shared support code."""

from .ap import AccessPointState, RadioState
from .auth import AuthSummary, RadiusServerResult
from .change import ChangeRecord
from .client import ClientSession, RoamEvent
from .common import (
	Confidence,
	Finding,
	FindingSeverity,
	NormalizedModel,
	NextAction,
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
	"NextAction",
	"NormalizedModel",
	"PathProbeResult",
	"RadioState",
	"RadiusServerResult",
	"ResolverResult",
	"RoamEvent",
	"ScopeType",
	"SegmentationSummary",
	"SharedInputBase",
	"SkillResult",
	"SourceMetadata",
	"Status",
	"StpSummary",
	"SwitchPortState",
	"TimeWindow",
]

