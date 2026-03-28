from __future__ import annotations

import argparse
import os
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

from pydantic import Field, ValidationError, model_validator

from ..cli import build_common_parser
from ..errors import BadInputError, NettoolsError, error_to_skill_result
from ..logging import StructuredLogger, configure_logging
from ..models import (
    Confidence,
    IncidentRecord,
    NextAction,
    ScopeType,
    SharedInputBase,
    SkillResult,
    Status,
)
from ..priority1 import AdapterBundle, load_stub_adapter_bundle
from ..priority3 import IncidentIntakeInput
from .branch_rules import BranchSelectionDecision, select_next_branch
from .classification import classify_and_select_playbook, intake_input_to_incident_record
from .execution import get_skill_definition, invoke_skill
from .playbooks import PlaybookDefinition
from .sampling import build_sampling_plan
from .scoring import score_incident_hypotheses
from .state import (
    DiagnoseIncidentReport,
    IncidentState,
    InvestigationStatus,
    RankedCause,
    StopReason,
    StopReasonCode,
)
from .stop_conditions import StopConditionConfig, evaluate_stop_conditions


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


class DiagnoseIncidentInput(SharedInputBase):
    complaint: str | None = None
    reporter: str | None = None
    incident_id: str | None = None
    location: str | None = None
    device_type: str | None = None
    movement_state: str | None = None
    wired_also_affected: bool | None = None
    reconnect_helps: bool | None = None
    occurred_at: datetime | None = None
    impacted_apps: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    candidate_client_ids: list[str] = Field(default_factory=list)
    candidate_client_macs: list[str] = Field(default_factory=list)
    candidate_ap_ids: list[str] = Field(default_factory=list)
    candidate_ap_names: list[str] = Field(default_factory=list)
    comparison_ap_ids: list[str] = Field(default_factory=list)
    comparison_ap_names: list[str] = Field(default_factory=list)
    candidate_areas: list[str] = Field(default_factory=list)
    comparison_areas: list[str] = Field(default_factory=list)
    incident_record: IncidentRecord | None = None
    playbook_override: str | None = None
    max_steps: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_incident_source(self) -> DiagnoseIncidentInput:
        if self.incident_record is None and not self.complaint:
            raise ValueError("either complaint or incident_record is required")
        return self


def _emit_result(result: SkillResult) -> None:
    print(result.model_dump_json(indent=2))


def _generated_incident_id() -> str:
    return f"incident-{utc_now().strftime('%Y%m%d%H%M%S')}"


def _state_incident_id(skill_input: DiagnoseIncidentInput) -> str:
    if skill_input.incident_record is not None and skill_input.incident_record.incident_id:
        return skill_input.incident_record.incident_id
    if skill_input.incident_id:
        return skill_input.incident_id
    return _generated_incident_id()


def _merge_scope_value(primary: Any, fallback: Any) -> Any:
    return primary if primary is not None else fallback


def _incident_record_from_input(skill_input: DiagnoseIncidentInput) -> IncidentRecord:
    if skill_input.incident_record is not None:
        record = skill_input.incident_record
    else:
        record = intake_input_to_incident_record(
            IncidentIntakeInput.model_validate(
                {
                    key: value
                    for key, value in skill_input.model_dump(mode="python").items()
                    if key in IncidentIntakeInput.model_fields and value is not None
                }
            )
        )

    return record.model_copy(
        update={
            "incident_id": _merge_scope_value(record.incident_id, skill_input.incident_id),
            "reporter": _merge_scope_value(record.reporter, skill_input.reporter),
            "summary": _merge_scope_value(record.summary, skill_input.complaint),
            "location": _merge_scope_value(record.location, skill_input.location),
            "site_id": _merge_scope_value(record.site_id, skill_input.site_id),
            "device_type": _merge_scope_value(record.device_type, skill_input.device_type),
            "client_id": _merge_scope_value(record.client_id, skill_input.client_id),
            "client_mac": _merge_scope_value(record.client_mac, skill_input.client_mac),
            "ssid": _merge_scope_value(record.ssid, skill_input.ssid),
            "movement_state": _merge_scope_value(record.movement_state, skill_input.movement_state),
            "wired_also_affected": _merge_scope_value(
                record.wired_also_affected,
                skill_input.wired_also_affected,
            ),
            "reconnect_helps": _merge_scope_value(
                record.reconnect_helps,
                skill_input.reconnect_helps,
            ),
            "impacted_apps": record.impacted_apps or list(skill_input.impacted_apps),
            "occurred_at": _merge_scope_value(record.occurred_at, skill_input.occurred_at),
            "notes": record.notes or list(skill_input.notes),
        }
    )


def _build_intake_payload(skill_input: DiagnoseIncidentInput) -> dict[str, Any]:
    payload = {
        key: value
        for key, value in skill_input.model_dump(mode="python").items()
        if key in IncidentIntakeInput.model_fields and value is not None
    }
    payload["incident_id"] = payload.get("incident_id") or _state_incident_id(skill_input)
    return payload


def _bootstrap_incident_record(
    skill_input: DiagnoseIncidentInput,
    *,
    state: IncidentState,
    adapters: AdapterBundle,
    resolver: Any,
    logger: StructuredLogger | None,
) -> IncidentRecord:
    if skill_input.incident_record is not None:
        return _incident_record_from_input(skill_input)

    intake_record = invoke_skill(
        "net.incident_intake",
        _build_intake_payload(skill_input),
        adapters,
        resolver=resolver,
        logger=logger,
    )
    state.append_execution(intake_record)
    incident_record = intake_record.result.evidence.get("incident_record")
    if not isinstance(incident_record, Mapping):
        raise BadInputError("net.incident_intake did not produce a normalized incident record")
    return IncidentRecord.model_validate(dict(incident_record)).model_copy(
        update={"incident_id": _state_incident_id(skill_input)}
    )


def _scope_payload(
    skill_input: DiagnoseIncidentInput,
    incident_record: IncidentRecord,
) -> dict[str, Any]:
    payload = {
        "site_id": _merge_scope_value(skill_input.site_id, incident_record.site_id),
        "client_id": _merge_scope_value(skill_input.client_id, incident_record.client_id),
        "client_mac": _merge_scope_value(skill_input.client_mac, incident_record.client_mac),
        "ap_id": skill_input.ap_id,
        "ap_name": skill_input.ap_name,
        "ssid": _merge_scope_value(skill_input.ssid, incident_record.ssid),
        "switch_id": skill_input.switch_id,
        "switch_port": skill_input.switch_port,
        "vlan_id": skill_input.vlan_id,
        "time_window_minutes": skill_input.time_window_minutes,
        "start_time": skill_input.start_time,
        "end_time": skill_input.end_time,
        "include_raw": skill_input.include_raw,
    }
    return {key: value for key, value in payload.items() if value is not None}


def _build_skill_payload(
    skill_name: str,
    *,
    skill_input: DiagnoseIncidentInput,
    incident_record: IncidentRecord,
) -> dict[str, Any]:
    payload = _scope_payload(skill_input, incident_record)
    if skill_name == "net.incident_correlation":
        payload["incident_summary"] = incident_record.summary
        payload["reporter"] = incident_record.reporter
    elif skill_name == "net.change_detection":
        payload["incident_summary"] = incident_record.summary
    elif skill_name == "net.capture_trigger":
        payload["reason"] = incident_record.summary or "Automated orchestration follow-up"
    return {key: value for key, value in payload.items() if value is not None}


def _build_skill_payloads(
    skill_name: str,
    *,
    playbook: PlaybookDefinition,
    state: IncidentState,
    skill_input: DiagnoseIncidentInput,
    incident_record: IncidentRecord,
) -> list[dict[str, Any]]:
    definition = get_skill_definition(skill_name)
    if definition is None:
        return []

    base_payload = _build_skill_payload(
        skill_name,
        skill_input=skill_input,
        incident_record=incident_record,
    )
    try:
        definition.input_model.model_validate(base_payload)
    except ValidationError:
        sampling_plan = build_sampling_plan(
            skill_name,
            base_payload,
            state=state,
            skill_input=skill_input,
            incident_record=incident_record,
            playbook=playbook,
        )
        candidate_payloads = sampling_plan.client_payloads or sampling_plan.ap_payloads
        valid_payloads: list[dict[str, Any]] = []
        for payload in candidate_payloads:
            try:
                definition.input_model.model_validate(payload)
            except ValidationError:
                continue
            valid_payloads.append(payload)
        return valid_payloads
    return [base_payload]


def _is_skill_runnable(
    skill_name: str,
    *,
    playbook: PlaybookDefinition,
    state: IncidentState,
    skill_input: DiagnoseIncidentInput,
    incident_record: IncidentRecord,
) -> bool:
    return bool(
        _build_skill_payloads(
            skill_name,
            playbook=playbook,
            state=state,
            skill_input=skill_input,
            incident_record=incident_record,
        )
    )


def _initial_skill(
    playbook: PlaybookDefinition,
    *,
    state: IncidentState,
    skill_input: DiagnoseIncidentInput,
    incident_record: IncidentRecord,
) -> str | None:
    executed = {record.skill_name for record in state.skill_trace}
    blocked = {failure.skill_name for failure in state.dependency_failures}
    for skill_name in playbook.default_sequence:
        if skill_name == "net.incident_intake":
            continue
        if skill_name in executed or skill_name in blocked:
            continue
        if not _is_skill_runnable(
            skill_name,
            playbook=playbook,
            state=state,
            skill_input=skill_input,
            incident_record=incident_record,
        ):
            continue
        return skill_name
    return None


def _expected_default_followup(
    playbook: PlaybookDefinition,
    *,
    state: IncidentState,
    current_source: str | None,
    skill_input: DiagnoseIncidentInput,
    incident_record: IncidentRecord,
) -> str | None:
    if current_source is None:
        return _initial_skill(
            playbook,
            state=state,
            skill_input=skill_input,
            incident_record=incident_record,
        )
    blocked = {failure.skill_name for failure in state.dependency_failures}
    executed = {record.skill_name for record in state.skill_trace}
    try:
        source_index = playbook.default_sequence.index(current_source)
    except ValueError:
        return _initial_skill(
            playbook,
            state=state,
            skill_input=skill_input,
            incident_record=incident_record,
        )

    for skill_name in playbook.default_sequence[source_index + 1 :]:
        if skill_name == "net.incident_intake":
            continue
        if skill_name in executed or skill_name in blocked:
            continue
        if not _is_skill_runnable(
            skill_name,
            playbook=playbook,
            state=state,
            skill_input=skill_input,
            incident_record=incident_record,
        ):
            continue
        return skill_name
    return None


def _select_runnable_branch(
    state: IncidentState,
    *,
    playbook: PlaybookDefinition,
    source_skill: str,
    skill_input: DiagnoseIncidentInput,
    incident_record: IncidentRecord,
) -> BranchSelectionDecision:
    decision = select_next_branch(state, playbook=playbook, source_skill=source_skill)
    if not decision.candidate_scores:
        return decision

    ordered_candidates = sorted(
        decision.candidate_scores.items(),
        key=lambda item: (-item[1], item[0]),
    )
    runnable_rationale = list(decision.rationale)
    for skill_name, _score in ordered_candidates:
        if _is_skill_runnable(
            skill_name,
            playbook=playbook,
            state=state,
            skill_input=skill_input,
            incident_record=incident_record,
        ):
            if skill_name == decision.selected_skill:
                return decision
            if decision.selected_skill is not None:
                runnable_rationale.append(
                    f"Skipped {decision.selected_skill} because required identifiers are missing."
                )
            runnable_rationale.append(
                f"Selected {skill_name} as the highest-ranked runnable branch target."
            )
            amended = BranchSelectionDecision(
                source_skill=decision.source_skill,
                selected_skill=skill_name,
                candidate_scores=decision.candidate_scores,
                rationale=runnable_rationale,
            )
            state.set_branch_recommendation(skill_name, rationale=amended.rationale)
            return amended

    runnable_rationale.append(
        "No branch candidates were runnable with the currently known identifiers."
    )
    amended = BranchSelectionDecision(
        source_skill=decision.source_skill,
        candidate_scores=decision.candidate_scores,
        rationale=runnable_rationale,
    )
    state.set_branch_recommendation(None, rationale=amended.rationale)
    return amended


def _snapshot_scores(state: IncidentState) -> dict[object, float]:
    return {
        domain.value: domain_score.score
        for domain, domain_score in state.domain_scores.items()
    }


def _ranked_causes(state: IncidentState, *, limit: int = 3) -> list[RankedCause]:
    ranked_causes: list[RankedCause] = []
    ordered = sorted(
        state.domain_scores.values(),
        key=lambda item: (-item.score, item.domain.value),
    )
    for domain_score in ordered:
        if len(ranked_causes) >= limit or domain_score.score <= 0.0:
            break
        if domain_score.supporting_findings:
            rationale = (
                f"{domain_score.domain.value} is supported by "
                + ", ".join(domain_score.supporting_findings)
                + "."
            )
        elif domain_score.contradicting_findings:
            rationale = f"{domain_score.domain.value} remains weakly plausible despite "
            rationale += "contradicting signals."
        else:
            rationale = f"{domain_score.domain.value} remains plausible from the current "
            rationale += "evidence mix."
        ranked_causes.append(
            RankedCause(
                domain=domain_score.domain,
                score=domain_score.score,
                confidence=domain_score.confidence or Confidence.LOW,
                rationale=rationale,
                supporting_findings=domain_score.supporting_findings,
            )
        )
    return ranked_causes


def _result_scope(
    skill_input: DiagnoseIncidentInput,
    incident_record: IncidentRecord,
) -> tuple[ScopeType, str]:
    payload = _scope_payload(skill_input, incident_record)
    shared = SharedInputBase.model_validate(payload)
    return shared.default_scope_type(), shared.scope_id


def _result_status(state: IncidentState, ranked_causes: Sequence[RankedCause]) -> Status:
    if state.status is InvestigationStatus.BLOCKED:
        return Status.FAIL
    if ranked_causes and ranked_causes[0].domain.value != "unknown":
        return Status.WARN
    if state.stop_reason and state.stop_reason.code in {
        StopReasonCode.HUMAN_ACTION_REQUIRED,
        StopReasonCode.NO_NEW_INFORMATION,
    }:
        return Status.UNKNOWN
    return Status.UNKNOWN


def _report_summary(
    state: IncidentState,
    ranked_causes: Sequence[RankedCause],
) -> str:
    if ranked_causes:
        lead = ranked_causes[0]
        if state.stop_reason and state.stop_reason.code is StopReasonCode.HIGH_CONFIDENCE_DIAGNOSIS:
            return (
                f"High-confidence diagnosis points to {lead.domain.value} "
                f"with {lead.confidence.value} confidence."
            )
        return (
            f"Investigation narrowed the issue to {lead.domain.value} "
            f"with {lead.confidence.value} confidence."
        )
    if state.stop_reason is not None:
        return state.stop_reason.message
    return "Investigation completed without a strong automated diagnosis."


def _build_report(
    state: IncidentState,
    *,
    ranked_causes: Sequence[RankedCause],
    summary: str,
    result_status: Status,
) -> dict[str, Any]:
    report = DiagnoseIncidentReport.from_incident_state(
        state,
        result_status=result_status,
        summary=summary,
        ranked_causes=list(ranked_causes),
    )
    return report.model_dump(mode="json")


def _manual_stop_reason(message: str, state: IncidentState) -> StopReason:
    return StopReason(
        code=StopReasonCode.HUMAN_ACTION_REQUIRED,
        message=message,
        supporting_context={
            "executed_skills": [record.skill_name for record in state.skill_trace],
        },
        uncertainty_summary=(
            "Automated orchestration has no additional runnable branches with the currently "
            "available identifiers or evidence."
        ),
        recommended_human_actions=[
            "Review the investigation trace and gather new scope-specific evidence.",
        ],
    )


def evaluate_diagnose_incident(
    skill_input: DiagnoseIncidentInput,
    adapters: AdapterBundle,
    *,
    resolver: Any = None,
    logger: StructuredLogger | None = None,
    stop_config: StopConditionConfig | None = None,
) -> SkillResult:
    state = IncidentState(incident_id=_state_incident_id(skill_input))
    incident_record = _bootstrap_incident_record(
        skill_input,
        state=state,
        adapters=adapters,
        resolver=resolver,
        logger=logger,
    )
    incident_record = incident_record.model_copy(update={"incident_id": state.incident_id})
    _classification, selection = classify_and_select_playbook(
        incident_record,
        override=skill_input.playbook_override,
        state=state,
    )
    playbook = selection.playbook

    next_skill = _initial_skill(
        playbook,
        state=state,
        skill_input=skill_input,
        incident_record=incident_record,
    )
    state.recommend_next(next_skill)

    branch_depth = 0
    score_snapshots: list[Mapping[object, float]] = []
    step_count = 0
    max_steps = skill_input.max_steps or playbook.stop_settings.max_skill_invocations

    while next_skill is not None and step_count < max_steps:
        payloads = _build_skill_payloads(
            next_skill,
            playbook=playbook,
            state=state,
            skill_input=skill_input,
            incident_record=incident_record,
        )
        if not payloads:
            break

        remaining_invocations = max(
            0,
            playbook.stop_settings.max_skill_invocations - len(state.skill_trace),
        )
        if remaining_invocations == 0:
            break

        for payload in payloads[:remaining_invocations]:
            record = invoke_skill(
                next_skill,
                payload,
                adapters,
                resolver=resolver,
                logger=logger,
            )
            state.append_execution(record)
        step_count += 1

        score_incident_hypotheses(state)
        branch_decision = _select_runnable_branch(
            state,
            playbook=playbook,
            source_skill=next_skill,
            skill_input=skill_input,
            incident_record=incident_record,
        )
        selected_skill = branch_decision.selected_skill
        expected_default = _expected_default_followup(
            playbook,
            state=state,
            current_source=next_skill,
            skill_input=skill_input,
            incident_record=incident_record,
        )
        if (
            selected_skill is not None
            and expected_default is not None
            and selected_skill != expected_default
        ):
            branch_depth += 1

        stop_decision = evaluate_stop_conditions(
            state,
            playbook=playbook,
            branch_depth=branch_depth,
            config=stop_config,
            previous_score_snapshots=score_snapshots,
        )
        if stop_decision.should_stop:
            state.recommend_next(None)
            break

        score_snapshots.append(_snapshot_scores(state))
        next_skill = selected_skill
        state.recommend_next(next_skill)

    if step_count >= max_steps and state.stop_reason is None:
        manual_stop = _manual_stop_reason(
            "The requested max_steps limit was reached before the investigation converged.",
            state,
        )
        state.set_stop_reason(manual_stop)
        state.status = InvestigationStatus.COMPLETED
        state.recommend_next(None)
    elif next_skill is None and state.stop_reason is None:
        manual_stop = _manual_stop_reason(
            "No additional runnable automated follow-up skills remain.",
            state,
        )
        state.set_stop_reason(manual_stop)
        state.status = InvestigationStatus.COMPLETED
        state.recommend_next(None)
    elif state.stop_reason is None:
        state.status = InvestigationStatus.RUNNING

    ranked_causes = _ranked_causes(state)
    result_status = _result_status(state, ranked_causes)
    summary = _report_summary(state, ranked_causes)
    scope_type, scope_id = _result_scope(skill_input, incident_record)
    report = _build_report(
        state,
        ranked_causes=ranked_causes,
        summary=summary,
        result_status=result_status,
    )

    raw_refs: list[Any] = []
    seen_raw_refs: set[str] = set()
    for entry in state.evidence_log:
        for raw_ref in entry.raw_refs:
            raw_ref_key = str(raw_ref)
            if raw_ref_key in seen_raw_refs:
                continue
            seen_raw_refs.add(raw_ref_key)
            raw_refs.append(raw_ref)

    return SkillResult(
        status=result_status,
        skill_name="net.diagnose_incident",
        scope_type=scope_type,
        scope_id=scope_id,
        summary=summary,
        confidence=(ranked_causes[0].confidence if ranked_causes else Confidence.LOW),
        observed_at=utc_now(),
        time_window=skill_input.time_window,
        evidence={
            "incident_record": incident_record.model_dump(mode="json", exclude_none=True),
            "diagnosis_report": report,
            "incident_state": state.model_dump(mode="json", exclude_none=True),
        },
        findings=[],
        next_actions=(
            [
                NextAction(
                    skill=state.recommended_next_skill,
                    reason="Additional automated follow-up remains available.",
                )
            ]
            if state.recommended_next_skill is not None
            else []
        ),
        raw_refs=raw_refs,
    )


def build_diagnose_incident_parser() -> argparse.ArgumentParser:
    parser = build_common_parser(
        "net.diagnose_incident",
        "Run the NETTOOLS incident diagnosis orchestrator over the lower-level skills.",
    )
    parser.add_argument("--fixture-file", default=os.environ.get("NETTOOLS_FIXTURE_FILE"))
    parser.add_argument("--complaint")
    parser.add_argument("--reporter")
    parser.add_argument("--incident-id")
    parser.add_argument("--location")
    parser.add_argument("--device-type")
    parser.add_argument("--movement-state")
    parser.add_argument("--wired-also-affected", action="store_const", const=True, default=None)
    parser.add_argument("--reconnect-helps", action="store_const", const=True, default=None)
    parser.add_argument("--occurred-at")
    parser.add_argument("--impacted-app", action="append", dest="impacted_apps")
    parser.add_argument("--note", action="append", dest="notes")
    parser.add_argument("--candidate-client-id", action="append", dest="candidate_client_ids")
    parser.add_argument(
        "--candidate-client-mac",
        action="append",
        dest="candidate_client_macs",
    )
    parser.add_argument("--candidate-ap-id", action="append", dest="candidate_ap_ids")
    parser.add_argument("--candidate-ap-name", action="append", dest="candidate_ap_names")
    parser.add_argument("--comparison-ap-id", action="append", dest="comparison_ap_ids")
    parser.add_argument(
        "--comparison-ap-name",
        action="append",
        dest="comparison_ap_names",
    )
    parser.add_argument("--candidate-area", action="append", dest="candidate_areas")
    parser.add_argument("--comparison-area", action="append", dest="comparison_areas")
    parser.add_argument("--playbook-override")
    parser.add_argument("--max-steps", type=int)
    return parser


def _parse_input(arguments: argparse.Namespace) -> DiagnoseIncidentInput:
    payload = {
        key: value
        for key, value in vars(arguments).items()
        if key in DiagnoseIncidentInput.model_fields and value is not None
    }
    return DiagnoseIncidentInput.model_validate(payload)


def main_diagnose_incident(argv: Sequence[str] | None = None) -> int:
    logger = configure_logging("net.diagnose_incident")
    parser = build_diagnose_incident_parser()
    arguments = parser.parse_args(list(argv) if argv is not None else None)

    try:
        skill_input = _parse_input(arguments)
    except ValidationError as exc:
        result = error_to_skill_result(
            error=BadInputError(str(exc)),
            skill_name="net.diagnose_incident",
            scope_type=ScopeType.SERVICE,
            scope_id="unscoped",
            time_window=SharedInputBase().time_window,
        )
        _emit_result(result)
        return 2

    try:
        adapters = load_stub_adapter_bundle(getattr(arguments, "fixture_file", None))
        result = evaluate_diagnose_incident(skill_input, adapters, logger=logger)
    except NettoolsError as exc:
        result = error_to_skill_result(
            error=exc,
            skill_name="net.diagnose_incident",
            scope_type=skill_input.default_scope_type(),
            scope_id=skill_input.scope_id,
            time_window=skill_input.time_window,
        )
        _emit_result(result)
        return 1

    logger.info(
        "diagnose incident executed",
        skill_name=result.skill_name,
        scope_type=result.scope_type.value,
        scope_id=result.scope_id,
        result_status=result.status.value,
        playbook=result.evidence.get("diagnosis_report", {}).get("playbook_used"),
    )
    _emit_result(result)
    return 0