from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest
from nettools.models import (
    Confidence,
    NextAction,
    ScopeType,
    SkillResult,
    Status,
    TimeWindow,
)
from nettools.orchestrator import (
    IncidentState,
    IncidentType,
    SkillExecutionRecord,
    classify_and_select_playbook,
    classify_incident,
    intake_input_to_incident_record,
    select_playbook,
)
from nettools.priority3 import IncidentIntakeInput


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _record(
    skill_name: str,
    *,
    incident_record: dict[str, Any] | None = None,
) -> SkillExecutionRecord:
    observed_at = _now()
    result = SkillResult(
        status=Status.OK,
        skill_name=skill_name,
        scope_type=ScopeType.SERVICE,
        scope_id="scope-1",
        summary=f"{skill_name} ok",
        confidence=Confidence.MEDIUM,
        observed_at=observed_at,
        time_window=TimeWindow(start=observed_at, end=observed_at),
        evidence={"incident_record": incident_record} if incident_record is not None else {},
        findings=[],
        next_actions=[NextAction(skill="net.incident_correlation", reason="follow-up")],
        raw_refs=[],
    )
    return SkillExecutionRecord(
        invocation_id=f"inv-{skill_name}",
        skill_name=skill_name,
        started_at=observed_at,
        finished_at=observed_at,
        duration_ms=1,
        input_summary={},
        result=result,
    )


def test_classify_single_user_complaint() -> None:
    decision = classify_incident(
        {
            "summary": "My laptop drops Zoom while moving between APs",
            "device_type": "laptop",
            "movement_state": "moving",
            "site_id": "hq-1",
        }
    )

    assert decision.incident_type == IncidentType.SINGLE_CLIENT
    assert decision.scope_summary.site_id == "hq-1"
    assert decision.rationale


def test_classify_single_area_complaint() -> None:
    decision = classify_incident(
        {
            "summary": "Users in conference room b cannot stay connected",
            "location": "conference room b",
            "site_id": "hq-1",
        }
    )

    assert decision.incident_type == IncidentType.SINGLE_AREA
    assert decision.scope_summary.affected_areas == ["conference room b"]
    assert decision.scope_summary.affected_users_estimate == 3


def test_classify_site_wide_complaint() -> None:
    decision = classify_incident(
        {
            "summary": "All users across the site are slow and wired is affected too",
            "wired_also_affected": True,
            "site_id": "hq-1",
        }
    )

    assert decision.incident_type == IncidentType.SITE_WIDE
    assert decision.scope_summary.affected_users_estimate == 10


def test_classify_auth_onboarding_complaint() -> None:
    decision = classify_incident(
        {
            "summary": "New users cannot connect to SSID CorpWiFi and reconnect helps",
            "ssid": "CorpWiFi",
            "reconnect_helps": True,
        }
    )

    assert decision.incident_type == IncidentType.AUTH_OR_ONBOARDING
    assert decision.scope_summary.ssid == "CorpWiFi"


def test_classify_ambiguous_intermittent_complaint() -> None:
    decision = classify_incident({"summary": "Network is sometimes slow"})

    assert decision.incident_type == IncidentType.INTERMITTENT_UNCLEAR


def test_classify_from_incident_intake_skill_result() -> None:
    skill_result = _record(
        "net.incident_intake",
        incident_record={
            "summary": "Users in conference room b cannot stay connected",
            "location": "conference room b",
            "site_id": "hq-1",
        },
    ).result

    decision = classify_incident(skill_result)

    assert isinstance(skill_result, SkillResult)
    assert decision.incident_type == IncidentType.SINGLE_AREA


def test_select_playbook_for_classification() -> None:
    selection = select_playbook(IncidentType.SITE_WIDE)

    assert selection.playbook_name == "site_wide_internal_slowdown"
    assert selection.playbook.name == selection.playbook_name
    assert selection.override_used is False


def test_select_playbook_override() -> None:
    selection = select_playbook(IncidentType.SINGLE_CLIENT, override="auth_or_onboarding_issue")

    assert selection.playbook_name == "auth_or_onboarding_issue"
    assert selection.override_used is True


def test_classify_and_select_updates_incident_state() -> None:
    state = IncidentState(incident_id="inc-100")

    classification, selection = classify_and_select_playbook(
        {
            "summary": "All users across the site are slow and wired is affected too",
            "wired_also_affected": True,
            "site_id": "hq-1",
        },
        state=state,
    )

    assert classification.incident_type == IncidentType.SITE_WIDE
    assert selection.playbook_name == "site_wide_internal_slowdown"
    assert state.incident_type == IncidentType.SITE_WIDE
    assert state.playbook_used == "site_wide_internal_slowdown"
    assert state.classification_rationale
    assert state.playbook_selection_rationale


def test_intake_input_to_incident_record() -> None:
    record = intake_input_to_incident_record(
        IncidentIntakeInput(
            complaint="My phone cannot connect to SSID CorpWiFi",
            site_id="hq-1",
            ssid="CorpWiFi",
        )
    )

    assert record.summary == "My phone cannot connect to SSID CorpWiFi"
    assert record.site_id == "hq-1"
    assert record.ssid == "CorpWiFi"


def test_select_playbook_rejects_unknown_override() -> None:
    with pytest.raises(ValueError, match="Unknown playbook override"):
        select_playbook(IncidentType.UNKNOWN_SCOPE, override="not_real")