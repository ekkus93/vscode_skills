"""Analysis helpers for NETTOOLS shared support code."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS = {
    "BaselineComparison": ("nettools.analysis.common", "BaselineComparison"),
    "JsonBaselineStore": ("nettools.analysis.cache", "JsonBaselineStore"),
    "MetricComparison": ("nettools.analysis.common", "MetricComparison"),
    "SuspectedCause": ("nettools.analysis.common", "SuspectedCause"),
    "TTLCache": ("nettools.analysis.cache", "TTLCache"),
    "aggregate_evidence": ("nettools.analysis.correlation", "aggregate_evidence"),
    "build_next_action": ("nettools.analysis.recommendations", "build_next_action"),
    "build_next_actions": ("nettools.analysis.recommendations", "build_next_actions"),
    "compare_to_baseline": ("nettools.analysis.thresholds", "compare_to_baseline"),
    "compare_to_threshold": ("nettools.analysis.thresholds", "compare_to_threshold"),
    "confidence_from_evidence": ("nettools.analysis.scoring", "confidence_from_evidence"),
    "correlation_score": ("nettools.analysis.correlation", "correlation_score"),
    "event_correlation_score": ("nettools.analysis.correlation", "event_correlation_score"),
    "normalize_access_point_state": (
        "nettools.analysis.normalization",
        "normalize_access_point_state",
    ),
    "normalize_auth_summary": ("nettools.analysis.normalization", "normalize_auth_summary"),
    "normalize_client_session": ("nettools.analysis.normalization", "normalize_client_session"),
    "normalize_dhcp_summary": ("nettools.analysis.normalization", "normalize_dhcp_summary"),
    "normalize_dns_summary": ("nettools.analysis.normalization", "normalize_dns_summary"),
    "normalize_path_probe_result": (
        "nettools.analysis.normalization",
        "normalize_path_probe_result",
    ),
    "normalize_radio_state": ("nettools.analysis.normalization", "normalize_radio_state"),
    "normalize_segmentation_summary": (
        "nettools.analysis.normalization",
        "normalize_segmentation_summary",
    ),
    "normalize_stp_summary": ("nettools.analysis.normalization", "normalize_stp_summary"),
    "normalize_switch_port_state": (
        "nettools.analysis.normalization",
        "normalize_switch_port_state",
    ),
    "build_adjacency_list": ("nettools.analysis.topology", "build_adjacency_list"),
    "build_topology_graph": ("nettools.analysis.topology", "build_topology_graph"),
    "classify_host": ("nettools.analysis.topology", "classify_host"),
    "confidence_for_edge": ("nettools.analysis.topology", "confidence_for_edge"),
    "detect_service_name_conflicts": (
        "nettools.analysis.topology",
        "detect_service_name_conflicts",
    ),
    "find_path": ("nettools.analysis.topology", "find_path"),
    "group_services_by_host": ("nettools.analysis.topology", "group_services_by_host"),
    "merge_edges": ("nettools.analysis.topology", "merge_edges"),
    "merge_host_observations": ("nettools.analysis.topology", "merge_host_observations"),
    "merge_neighbor_records": ("nettools.analysis.topology", "merge_neighbor_records"),
    "neighbor_record_to_edge": ("nettools.analysis.topology", "neighbor_record_to_edge"),
    "rank_suspected_causes": ("nettools.analysis.correlation", "rank_suspected_causes"),
    "severity_from_comparisons": ("nettools.analysis.scoring", "severity_from_comparisons"),
    "summarize_baseline": ("nettools.analysis.topology", "summarize_baseline"),
    "summarize_gateway_path": ("nettools.analysis.topology", "summarize_gateway_path"),
    "time_window_overlap_ratio": ("nettools.analysis.correlation", "time_window_overlap_ratio"),
}


def __getattr__(name: str) -> Any:
    module_name, symbol_name = _EXPORTS[name]
    module = import_module(module_name)
    return getattr(module, symbol_name)


__all__ = [
    "BaselineComparison",
    "JsonBaselineStore",
    "MetricComparison",
    "SuspectedCause",
    "TTLCache",
    "aggregate_evidence",
    "build_next_action",
    "build_next_actions",
    "build_adjacency_list",
    "build_topology_graph",
    "classify_host",
    "compare_to_baseline",
    "compare_to_threshold",
    "confidence_for_edge",
    "confidence_from_evidence",
    "correlation_score",
    "detect_service_name_conflicts",
    "event_correlation_score",
    "find_path",
    "group_services_by_host",
    "merge_edges",
    "merge_host_observations",
    "merge_neighbor_records",
    "neighbor_record_to_edge",
    "normalize_access_point_state",
    "normalize_auth_summary",
    "normalize_client_session",
    "normalize_dhcp_summary",
    "normalize_dns_summary",
    "normalize_path_probe_result",
    "normalize_radio_state",
    "normalize_segmentation_summary",
    "normalize_stp_summary",
    "normalize_switch_port_state",
    "rank_suspected_causes",
    "severity_from_comparisons",
    "summarize_baseline",
    "summarize_gateway_path",
    "time_window_overlap_ratio",
]
