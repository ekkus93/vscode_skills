from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from typing import Any

from ..models import TimeWindow
from .common import SuspectedCause


def time_window_overlap_ratio(first: TimeWindow, second: TimeWindow) -> float:
    latest_start = max(first.start, second.start)
    earliest_end = min(first.end, second.end)
    if latest_start >= earliest_end:
        return 0.0
    overlap_seconds = (earliest_end - latest_start).total_seconds()
    max_span = max(
        (first.end - first.start).total_seconds(), (second.end - second.start).total_seconds()
    )
    if max_span <= 0:
        return 0.0
    return overlap_seconds / max_span


def correlation_score(
    *, overlap_ratio: float, shared_scope: bool, shared_sources: int = 0
) -> float:
    score = overlap_ratio
    if shared_scope:
        score += 0.25
    score += min(shared_sources, 3) * 0.1
    return round(min(score, 1.0), 4)


def event_correlation_score(
    *,
    first_window: TimeWindow,
    second_window: TimeWindow,
    shared_scope: bool,
    shared_sources: int = 0,
) -> float:
    return correlation_score(
        overlap_ratio=time_window_overlap_ratio(first_window, second_window),
        shared_scope=shared_scope,
        shared_sources=shared_sources,
    )


def aggregate_evidence(evidence_sets: Iterable[Mapping[str, Any]]) -> dict[str, list[Any]]:
    aggregated: dict[str, list[Any]] = defaultdict(list)
    for evidence in evidence_sets:
        for key, value in evidence.items():
            if value not in aggregated[key]:
                aggregated[key].append(value)
    return dict(aggregated)


def rank_suspected_causes(causes: list[SuspectedCause]) -> list[SuspectedCause]:
    return sorted(causes, key=lambda cause: (-cause.score, cause.code))
