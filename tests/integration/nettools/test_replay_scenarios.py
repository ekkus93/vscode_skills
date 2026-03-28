from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import pytest
from nettools.models import (
    Confidence,
    Finding,
    FindingSeverity,
    ScopeType,
    SkillResult,
    Status,
    TimeWindow,
)
from nettools.orchestrator import (
    DiagnoseIncidentAuditTrail,
    DiagnosticDomain,
    IncidentState,
    IncidentType,
    InvestigationStatus,
    InvestigationTraceEventType,
    ScopeSummary,
    SkillExecutionRecord,
    StopReason,
)
from nettools.orchestrator.diagnose_incident import (
    DiagnoseIncidentInput,
    evaluate_diagnose_incident,
)
from nettools.priority1 import AdapterBundle


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_replay_scenarios() -> dict[str, dict[str, Any]]:
    path = Path("tests/fixtures/nettools/replay_scenarios.json")
    return cast(dict[str, dict[str, Any]], json.loads(path.read_text(encoding="utf-8")))


def _finding_from_spec(spec: str | Mapping[str, str]) -> Finding:
    if isinstance(spec, str):
        return Finding(code=spec, severity=FindingSeverity.WARN, message=spec)
    return Finding(
        code=spec["code"],
        severity=FindingSeverity(spec.get("severity", "warn")),
        message=spec.get("message", spec["code"]),
    )


def _execution_from_spec(spec: Mapping[str, Any]) -> SkillExecutionRecord:
    observed_at = _parse_timestamp(cast(str, spec["observed_at"]))
    result = SkillResult(
        status=Status(cast(str, spec["status"])),
        skill_name=cast(str, spec["skill_name"]),
        scope_type=ScopeType(cast(str, spec["scope_type"])),
        scope_id=cast(str, spec["scope_id"]),
        summary=cast(str, spec.get("summary", f"{spec['skill_name']} summary")),
        confidence=Confidence(cast(str, spec.get("confidence", "medium"))),
        observed_at=observed_at,
        time_window=TimeWindow(start=observed_at, end=observed_at),
        evidence=cast(dict[str, Any], spec.get("evidence", {})),
        findings=[
            _finding_from_spec(finding_spec)
            for finding_spec in cast(list[str | Mapping[str, str]], spec.get("finding_codes", []))
        ],
        next_actions=[],
        raw_refs=cast(list[Any], spec.get("raw_refs", [])),
    )
    return SkillExecutionRecord(
        invocation_id=cast(str, spec.get("invocation_id", f"inv-{spec['skill_name']}")),
        skill_name=cast(str, spec["skill_name"]),
        started_at=observed_at,
        finished_at=observed_at,
        duration_ms=cast(int, spec.get("duration_ms", 1)),
        input_summary=cast(dict[str, Any], spec.get("input_summary", {})),
        result=result,
        error_type=cast(str | None, spec.get("error_type")),
    )


def _build_audit_trail(scenario: Mapping[str, Any]) -> DiagnoseIncidentAuditTrail:
    state_spec = cast(dict[str, Any], scenario["state"])
    state = IncidentState(
        incident_id=cast(str, state_spec["incident_id"]),
        created_at=_parse_timestamp(cast(str, state_spec["created_at"])),
        updated_at=_parse_timestamp(cast(str, state_spec["updated_at"])),
        incident_type=IncidentType(cast(str, state_spec["incident_type"])),
        playbook_used=cast(str | None, state_spec.get("playbook_used")),
        status=InvestigationStatus(cast(str, state_spec.get("status", "running"))),
        scope_summary=ScopeSummary.model_validate(state_spec.get("scope_summary", {})),
    )

    for execution_spec in cast(list[dict[str, Any]], scenario.get("executions", [])):
        state.append_execution(_execution_from_spec(execution_spec))

    for trace_spec in cast(list[dict[str, Any]], scenario.get("trace", [])):
        state.append_trace(
            InvestigationTraceEventType(cast(str, trace_spec["event_type"])),
            cast(str, trace_spec["message"]),
            details=cast(dict[str, Any], trace_spec.get("details", {})),
            recorded_at=_parse_timestamp(cast(str, trace_spec["recorded_at"])),
        )

    for score_spec in cast(list[dict[str, Any]], scenario.get("domain_scores", [])):
        state.set_domain_score(
            DiagnosticDomain(cast(str, score_spec["domain"])),
            score=cast(float, score_spec["score"]),
            confidence=Confidence(cast(str, score_spec.get("confidence", "low"))),
            supporting_findings=cast(list[str], score_spec.get("supporting_findings", [])),
            contradicting_findings=cast(list[str], score_spec.get("contradicting_findings", [])),
        )

    if "stop_reason" in scenario:
        state.stop_reason = StopReason.model_validate(scenario["stop_reason"])
    if "recommended_next_skill" in scenario:
        state.recommended_next_skill = cast(str | None, scenario["recommended_next_skill"])

    state.created_at = _parse_timestamp(cast(str, state_spec["created_at"]))
    state.updated_at = _parse_timestamp(cast(str, state_spec["updated_at"]))

    return DiagnoseIncidentAuditTrail.from_incident_state(
        state,
        incident_record=cast(dict[str, Any], scenario["incident_record"]),
        persisted_at=_parse_timestamp(cast(str, scenario["persisted_at"])),
    )


SCENARIOS = load_replay_scenarios()


def test_replay_scenarios_cover_all_phase16_cases() -> None:
    assert set(SCENARIOS) == {
        "single_client_scenario",
        "area_based_scenario",
        "site_wide_slowdown_scenario",
        "onboarding_auth_scenario",
        "ambiguous_scenario",
    }


@pytest.mark.parametrize("scenario_name", sorted(SCENARIOS))
def test_replay_scenarios_reconstruct_diagnosis_without_live_execution(
    monkeypatch: pytest.MonkeyPatch,
    scenario_name: str,
) -> None:
    scenario = SCENARIOS[scenario_name]
    audit_trail = _build_audit_trail(scenario)

    def fail_invoke(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("replay scenarios should not invoke primitive skills")

    monkeypatch.setattr("nettools.orchestrator.diagnose_incident.invoke_skill", fail_invoke)

    input_payload = {"replay_audit_trail": audit_trail, **scenario.get("input_overrides", {})}
    result = evaluate_diagnose_incident(
        DiagnoseIncidentInput.model_validate(input_payload),
        AdapterBundle(),
    )

    expected = cast(dict[str, Any], scenario["expected"])
    report = cast(dict[str, Any], result.evidence["diagnosis_report"])
    ranked_domains = [
        cause["domain"]
        for cause in cast(list[dict[str, Any]], report["ranked_causes"])[
            : len(cast(list[str], expected["ranked_domains"]))
        ]
    ]

    assert result.status.value == expected["status"]
    assert report["incident_type"] == expected["incident_type"]
    assert report["playbook_used"] == expected["playbook_used"]
    assert ranked_domains == expected["ranked_domains"]
    assert report["stop_reason"]["code"] == expected["stop_reason"]
    assert report["recommended_followup_skills"] == expected["followup_skills"]
    assert expected["human_action_fragment"] in report["recommended_human_actions"][0]
    assert report["sampling_summary"] == expected["sampling_summary"]
    assert result.evidence["replay_debug"] == {
        "enabled": True,
        "source": "audit_trail",
        "replayed_skill_count": len(cast(list[dict[str, Any]], scenario.get("executions", []))),
    }
    replayed_incident_record = cast(dict[str, Any], result.evidence["incident_record"])
    for key, value in cast(dict[str, Any], scenario["incident_record"]).items():
        assert replayed_incident_record[key] == value
    assert result.evidence["investigation_metrics"]["playbook_invocations"] == {
        expected["playbook_used"]: 1
    }
    assert result.evidence["investigation_metrics"]["stop_reason_counts"] == {
        expected["stop_reason"]: 1
    }
    assert result.evidence["investigation_metrics"]["diagnosis_domains_by_outcome"] == {
        expected["status"]: {expected["metrics_lead_domain"]: 1}
    }
    assert (
        result.evidence["investigation_metrics"]["average_skill_count_per_investigation"]
        == float(len(cast(list[dict[str, Any]], scenario.get("executions", []))))
    )