from __future__ import annotations

from ..models import Confidence, FindingSeverity
from .common import MetricComparison


def severity_from_comparisons(comparisons: list[MetricComparison]) -> FindingSeverity:
    breached = [comparison for comparison in comparisons if comparison.breached]
    if not breached:
        return FindingSeverity.INFO
    max_delta_pct = max(abs(comparison.delta_pct or 0.0) for comparison in breached)
    if len(breached) >= 3 or max_delta_pct >= 100.0:
        return FindingSeverity.CRITICAL
    return FindingSeverity.WARN


def confidence_from_evidence(
    *,
    evidence_count: int,
    source_count: int,
    partial_failure_count: int = 0,
    baseline_present: bool = False,
) -> Confidence:
    score = evidence_count + source_count + (1 if baseline_present else 0) - partial_failure_count
    if score >= 5:
        return Confidence.HIGH
    if score >= 3:
        return Confidence.MEDIUM
    return Confidence.LOW
