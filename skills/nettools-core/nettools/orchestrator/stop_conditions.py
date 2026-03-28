from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field

from ..models import Confidence
from .playbooks import PlaybookDefinition, get_playbook_definition
from .scoring import HypothesisScoringConfig
from .state import (
    DiagnosticDomain,
    DomainScore,
    IncidentState,
    InvestigationStatus,
    InvestigationTraceEventType,
    StopReason,
    StopReasonCode,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


class StopConditionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ambiguity_gap: float = Field(default=0.12, ge=0.0, le=1.0)
    ambiguity_min_score: float = Field(default=0.40, ge=0.0, le=1.0)
    min_supporting_findings_for_high_confidence: int = Field(default=1, ge=0)
    no_new_information_delta: float = Field(default=0.03, ge=0.0, le=1.0)
    no_new_information_window: int = Field(default=2, ge=1)
    scoring: HypothesisScoringConfig = Field(default_factory=HypothesisScoringConfig)


class StopConditionDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    should_stop: bool
    stop_reason: StopReason | None = None
    rationale: list[str] = Field(default_factory=list)


def _choose_playbook(
    playbook: PlaybookDefinition | str | None,
    state: IncidentState,
) -> PlaybookDefinition | None:
    if isinstance(playbook, PlaybookDefinition):
        return playbook
    if isinstance(playbook, str):
        return get_playbook_definition(playbook)
    if state.playbook_used is not None:
        return get_playbook_definition(state.playbook_used)
    return None


def _ranked_domains(state: IncidentState) -> list[DomainScore]:
    return sorted(
        state.domain_scores.values(),
        key=lambda item: (-item.score, item.domain.value),
    )


def _high_confidence_reason(
    state: IncidentState,
    *,
    config: StopConditionConfig,
    high_confidence_threshold: float,
) -> StopReason | None:
    ranked = _ranked_domains(state)
    if not ranked:
        return None
    top = ranked[0]
    if top.score < high_confidence_threshold or top.confidence is not Confidence.HIGH:
        return None
    if len(top.supporting_findings) < config.min_supporting_findings_for_high_confidence:
        return None
    return StopReason(
        code=StopReasonCode.HIGH_CONFIDENCE_DIAGNOSIS,
        message=f"{top.domain.value} reached high confidence with sufficient supporting evidence.",
        related_domains=[top.domain],
        supporting_context={
            "score": top.score,
            "supporting_findings": top.supporting_findings,
        },
        uncertainty_summary=(
            "Residual ambiguity is low enough that further automated narrowing "
            "is unnecessary."
        ),
        recommended_human_actions=[
            f"Review evidence for {top.domain.value} and prepare operator remediation.",
        ],
    )


def _bounded_ambiguity_reason(
    state: IncidentState,
    *,
    config: StopConditionConfig,
) -> StopReason | None:
    plausible = [
        score
        for score in _ranked_domains(state)
        if score.score >= config.ambiguity_min_score
    ]
    if len(plausible) != 2:
        return None
    if abs(plausible[0].score - plausible[1].score) > config.ambiguity_gap:
        return None
    if state.recommended_next_skill is not None:
        return None
    return StopReason(
        code=StopReasonCode.TWO_DOMAIN_BOUNDED_AMBIGUITY,
        message="Two plausible domains remain and automated narrowing is unlikely to help further.",
        related_domains=[plausible[0].domain, plausible[1].domain],
        supporting_context={
            "domain_scores": {
                plausible[0].domain.value: plausible[0].score,
                plausible[1].domain.value: plausible[1].score,
            }
        },
        uncertainty_summary=(
            f"{plausible[0].domain.value} and {plausible[1].domain.value} remain close in score."
        ),
        recommended_human_actions=[
            "Review both candidate domains and collect targeted operator evidence.",
        ],
    )


def _budget_reason(
    state: IncidentState,
    *,
    playbook: PlaybookDefinition | None,
    branch_depth: int,
    now: datetime,
) -> StopReason | None:
    if playbook is None:
        return None
    settings = playbook.stop_settings
    if len(state.skill_trace) >= settings.max_skill_invocations:
        return StopReason(
            code=StopReasonCode.INVESTIGATION_BUDGET_EXHAUSTED,
            message="The investigation reached the maximum configured skill budget.",
            supporting_context={
                "skill_invocations": len(state.skill_trace),
                "max_skill_invocations": settings.max_skill_invocations,
            },
            uncertainty_summary=(
                "Additional automated steps would exceed the configured "
                "investigation budget."
            ),
            recommended_human_actions=[
                "Review collected evidence and decide the next manual diagnostic step.",
            ],
        )
    elapsed_seconds = int((now - state.created_at).total_seconds())
    if elapsed_seconds >= settings.max_elapsed_seconds:
        return StopReason(
            code=StopReasonCode.INVESTIGATION_BUDGET_EXHAUSTED,
            message="The investigation exceeded the maximum configured elapsed time.",
            supporting_context={
                "elapsed_seconds": elapsed_seconds,
                "max_elapsed_seconds": settings.max_elapsed_seconds,
            },
            uncertainty_summary="Automated investigation time budget is exhausted.",
            recommended_human_actions=[
                "Escalate with the current evidence timeline and diagnostics summary.",
            ],
        )
    if branch_depth >= settings.max_branch_depth:
        return StopReason(
            code=StopReasonCode.INVESTIGATION_BUDGET_EXHAUSTED,
            message="The investigation reached the maximum configured branch depth.",
            supporting_context={
                "branch_depth": branch_depth,
                "max_branch_depth": settings.max_branch_depth,
            },
            uncertainty_summary=(
                "Further automated branching would exceed the configured "
                "investigation depth."
            ),
            recommended_human_actions=[
                "Review branch history and choose a targeted manual follow-up.",
            ],
        )
    return None


def _dependency_block_reason(state: IncidentState) -> StopReason | None:
    if not state.dependency_failures or state.recommended_next_skill is not None:
        return None
    failure = state.dependency_failures[-1]
    return StopReason(
        code=StopReasonCode.DEPENDENCY_BLOCKED,
        message=f"Investigation is blocked by dependency failures in {failure.skill_name}.",
        supporting_context={
            "skill_name": failure.skill_name,
            "error_type": failure.error_type,
            "summary": failure.summary,
        },
        uncertainty_summary=(
            "Critical upstream data is unavailable for further automated progress."
        ),
        recommended_human_actions=[
            f"Restore or bypass the dependency used by {failure.skill_name} before retrying.",
        ],
    )


def _score_delta(
    previous_snapshot: Mapping[object, float],
    current_scores: Mapping[DiagnosticDomain, DomainScore],
) -> float:
    max_delta = 0.0
    for domain, current_score in current_scores.items():
        previous_value = previous_snapshot.get(domain)
        if previous_value is None:
            previous_value = previous_snapshot.get(domain.value, 0.0)
        max_delta = max(max_delta, abs(float(previous_value) - current_score.score))
    return max_delta


def _no_new_information_reason(
    state: IncidentState,
    *,
    config: StopConditionConfig,
    previous_score_snapshots: Sequence[Mapping[object, float]],
) -> StopReason | None:
    if len(previous_score_snapshots) < config.no_new_information_window:
        return None
    recent_snapshots = previous_score_snapshots[-config.no_new_information_window :]
    deltas = [_score_delta(snapshot, state.domain_scores) for snapshot in recent_snapshots]
    if any(delta > config.no_new_information_delta for delta in deltas):
        return None
    return StopReason(
        code=StopReasonCode.NO_NEW_INFORMATION,
        message="Recent skill outputs are not materially changing domain scores.",
        related_domains=[score.domain for score in _ranked_domains(state)[:2]],
        supporting_context={
            "max_recent_score_delta": max(deltas) if deltas else 0.0,
            "delta_threshold": config.no_new_information_delta,
        },
        uncertainty_summary=(
            "The current evidence set is stable and further automated steps "
            "are not reducing uncertainty."
        ),
        recommended_human_actions=[
            "Pause automation and gather new external evidence before continuing.",
        ],
    )


def evaluate_stop_conditions(
    state: IncidentState,
    *,
    playbook: PlaybookDefinition | str | None = None,
    branch_depth: int = 0,
    now: datetime | None = None,
    config: StopConditionConfig | None = None,
    previous_score_snapshots: Sequence[Mapping[object, float]] | None = None,
    mutate_state: bool = True,
) -> StopConditionDecision:
    resolved_playbook = _choose_playbook(playbook, state)
    resolved_now = now or utc_now()
    resolved_config = config or StopConditionConfig()
    rationale: list[str] = []

    stop_reason = _high_confidence_reason(
        state,
        config=resolved_config,
        high_confidence_threshold=(
            resolved_playbook.stop_settings.high_confidence_threshold
            if resolved_playbook is not None
            else resolved_config.scoring.confidence_thresholds.high_min
        ),
    )
    if stop_reason is None:
        stop_reason = _bounded_ambiguity_reason(state, config=resolved_config)
    if stop_reason is None:
        stop_reason = _budget_reason(
            state,
            playbook=resolved_playbook,
            branch_depth=branch_depth,
            now=resolved_now,
        )
    if stop_reason is None:
        stop_reason = _dependency_block_reason(state)
    if stop_reason is None and previous_score_snapshots is not None:
        stop_reason = _no_new_information_reason(
            state,
            config=resolved_config,
            previous_score_snapshots=previous_score_snapshots,
        )

    if stop_reason is None:
        rationale.append("No stop condition matched; investigation can continue.")
        if mutate_state:
            state.append_trace(
                InvestigationTraceEventType.STOP_CONDITION_CHECK,
                "Stop conditions evaluated without triggering a stop.",
                details={
                    "should_stop": False,
                    "branch_depth": branch_depth,
                    "rationale": list(rationale),
                },
                recorded_at=resolved_now,
            )
        return StopConditionDecision(should_stop=False, rationale=rationale)

    rationale.append(f"Stop triggered: {stop_reason.code.value}.")
    if mutate_state:
        state.append_trace(
            InvestigationTraceEventType.STOP_CONDITION_CHECK,
            f"Stop conditions matched {stop_reason.code.value}.",
            details={
                "should_stop": True,
                "branch_depth": branch_depth,
                "stop_reason_code": stop_reason.code.value,
                "rationale": list(rationale),
            },
            recorded_at=resolved_now,
        )
        state.set_stop_reason(stop_reason)
        if stop_reason.code is StopReasonCode.DEPENDENCY_BLOCKED:
            state.status = InvestigationStatus.BLOCKED
        else:
            state.status = InvestigationStatus.COMPLETED
        state.updated_at = resolved_now
        state.append_trace(
            InvestigationTraceEventType.FINAL_STOP_RATIONALE,
            stop_reason.message,
            details={
                "stop_reason_code": stop_reason.code.value,
                "related_domains": [domain.value for domain in stop_reason.related_domains],
                "supporting_context": dict(stop_reason.supporting_context),
                "uncertainty_summary": stop_reason.uncertainty_summary,
            },
            recorded_at=resolved_now,
        )
    return StopConditionDecision(
        should_stop=True,
        stop_reason=stop_reason,
        rationale=rationale,
    )