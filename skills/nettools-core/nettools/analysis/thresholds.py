from __future__ import annotations

from .common import BaselineComparison, MetricComparison


def compare_to_threshold(
    metric: str, value: float, threshold: float, *, direction: str
) -> MetricComparison:
    if direction not in {"gte", "lte"}:
        raise ValueError("direction must be either 'gte' or 'lte'")
    breached = value >= threshold if direction == "gte" else value <= threshold
    delta = value - threshold
    delta_pct = None if threshold == 0 else (delta / threshold) * 100.0
    return MetricComparison(
        metric=metric,
        value=value,
        threshold=threshold,
        direction=direction,
        breached=breached,
        delta=delta,
        delta_pct=delta_pct,
    )


def compare_to_baseline(
    metric: str, current: float, baseline: float, *, higher_is_worse: bool = True
) -> BaselineComparison:
    delta = current - baseline
    delta_pct = None if baseline == 0 else (delta / baseline) * 100.0
    regression = current > baseline if higher_is_worse else current < baseline
    return BaselineComparison(
        metric=metric,
        current=current,
        baseline=baseline,
        higher_is_worse=higher_is_worse,
        regression=regression,
        delta=delta,
        delta_pct=delta_pct,
    )
