from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..models import IncidentRecord, SkillResult
from ..priority3 import IncidentIntakeInput
from .playbooks import DEFAULT_PLAYBOOKS, PlaybookDefinition, get_playbook_definition
from .state import IncidentState, IncidentType, ScopeSummary

AUTH_HINTS = (
    "auth",
    "authenticate",
    "authentication",
    "onboard",
    "onboarding",
    "cannot connect",
    "can't connect",
    "unable to connect",
    "radius",
    "certificate",
    "eap",
    "ssid",
)
SITE_WIDE_HINTS = (
    "site-wide",
    "site wide",
    "all users",
    "everyone",
    "across the site",
    "multiple areas",
    "multiple floors",
    "entire office",
)
MULTI_USER_HINTS = (
    "users",
    "multiple",
    "several",
    "many",
    "team",
    "people",
)
INTERMITTENT_HINTS = (
    "intermittent",
    "sometimes",
    "occasionally",
    "comes and goes",
    "random",
    "sporadic",
)

DEFAULT_PLAYBOOK_BY_INCIDENT_TYPE: dict[IncidentType, str] = {
    IncidentType.SINGLE_CLIENT: "single_client_wifi_issue",
    IncidentType.SINGLE_AREA: "area_based_wifi_issue",
    IncidentType.SITE_WIDE: "site_wide_internal_slowdown",
    IncidentType.AUTH_OR_ONBOARDING: "auth_or_onboarding_issue",
    IncidentType.INTERMITTENT_UNCLEAR: "unclear_general_network_issue",
    IncidentType.UNKNOWN_SCOPE: "unclear_general_network_issue",
}


def _normalized_text(value: str | None) -> str:
    return (value or "").strip().lower()


def _contains_any(text: str, tokens: tuple[str, ...]) -> bool:
    return any(token in text for token in tokens)


class ClassificationDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    incident_type: IncidentType
    scope_summary: ScopeSummary
    rationale: list[str] = Field(default_factory=list)


class PlaybookSelectionDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    playbook_name: str
    playbook: PlaybookDefinition
    rationale: list[str] = Field(default_factory=list)
    override_used: bool = False


def _incident_record_from_input(
    value: IncidentRecord | SkillResult | Mapping[str, Any],
) -> IncidentRecord:
    if isinstance(value, IncidentRecord):
        return value
    if isinstance(value, SkillResult):
        incident_record = value.evidence.get("incident_record")
        if not isinstance(incident_record, Mapping):
            raise ValueError("SkillResult must contain an incident_record mapping in evidence")
        return IncidentRecord.model_validate(dict(incident_record))
    return IncidentRecord.model_validate(dict(value))


def _infer_affected_users_estimate(record: IncidentRecord, text: str) -> int | None:
    if record.client_id or record.client_mac:
        return 1
    if _contains_any(text, SITE_WIDE_HINTS):
        return 10
    if _contains_any(text, MULTI_USER_HINTS):
        return 3
    if text.startswith("my ") or text.startswith("i ") or text.startswith("one user"):
        return 1
    return None


def classify_incident(
    intake: IncidentRecord | SkillResult | Mapping[str, Any],
) -> ClassificationDecision:
    record = _incident_record_from_input(intake)
    text = " ".join(
        part
        for part in (
            _normalized_text(record.summary),
            " ".join(_normalized_text(note) for note in record.notes),
            " ".join(_normalized_text(app) for app in record.impacted_apps),
        )
        if part
    )

    known_clients = [item for item in (record.client_id, record.client_mac) if item is not None]
    affected_areas = [record.location] if record.location is not None else []
    scope_summary = ScopeSummary(
        site_id=record.site_id,
        ssid=record.ssid,
        affected_users_estimate=_infer_affected_users_estimate(record, text),
        affected_areas=affected_areas,
        known_clients=known_clients,
        known_aps=[],
    )
    rationale: list[str] = []

    if record.reconnect_helps or _contains_any(text, AUTH_HINTS):
        rationale.append("Reconnect or authentication/onboarding symptoms are present.")
        return ClassificationDecision(
            incident_type=IncidentType.AUTH_OR_ONBOARDING,
            scope_summary=scope_summary,
            rationale=rationale,
        )

    if record.wired_also_affected is True or _contains_any(text, SITE_WIDE_HINTS):
        rationale.append("Wired impact or broad site-wide language suggests a larger scope.")
        return ClassificationDecision(
            incident_type=IncidentType.SITE_WIDE,
            scope_summary=scope_summary,
            rationale=rationale,
        )

    if record.location and _contains_any(text, MULTI_USER_HINTS):
        rationale.append("Multiple affected users appear co-located in a single area.")
        return ClassificationDecision(
            incident_type=IncidentType.SINGLE_AREA,
            scope_summary=scope_summary,
            rationale=rationale,
        )

    if known_clients or record.device_type is not None or record.movement_state is not None:
        rationale.append("The complaint is scoped to a single client or device context.")
        return ClassificationDecision(
            incident_type=IncidentType.SINGLE_CLIENT,
            scope_summary=scope_summary,
            rationale=rationale,
        )

    if _contains_any(text, INTERMITTENT_HINTS):
        rationale.append("The complaint is intermittent but lacks enough scope detail.")
        return ClassificationDecision(
            incident_type=IncidentType.INTERMITTENT_UNCLEAR,
            scope_summary=scope_summary,
            rationale=rationale,
        )

    rationale.append("The intake data is too sparse to determine a tighter scope.")
    return ClassificationDecision(
        incident_type=IncidentType.UNKNOWN_SCOPE,
        scope_summary=scope_summary,
        rationale=rationale,
    )


def select_playbook(
    classification: ClassificationDecision | IncidentType,
    *,
    override: str | None = None,
    playbook_map: Mapping[IncidentType, str] | None = None,
) -> PlaybookSelectionDecision:
    incident_type = (
        classification.incident_type
        if isinstance(classification, ClassificationDecision)
        else classification
    )
    rationale = (
        list(classification.rationale)
        if isinstance(classification, ClassificationDecision)
        else []
    )

    if override is not None:
        playbook = get_playbook_definition(override)
        if playbook is None:
            raise ValueError(f"Unknown playbook override: {override}")
        rationale.append(f"Explicit playbook override selected: {override}.")
        return PlaybookSelectionDecision(
            playbook_name=override,
            playbook=playbook,
            rationale=rationale,
            override_used=True,
        )

    selection_map = dict(DEFAULT_PLAYBOOK_BY_INCIDENT_TYPE)
    if playbook_map is not None:
        selection_map.update(playbook_map)

    playbook_name = selection_map.get(incident_type)
    if playbook_name is None:
        raise ValueError(f"No playbook mapping configured for incident type: {incident_type.value}")
    playbook = DEFAULT_PLAYBOOKS[playbook_name]
    rationale.append(
        f"Selected {playbook_name} as the default playbook for {incident_type.value}."
    )
    return PlaybookSelectionDecision(
        playbook_name=playbook_name,
        playbook=playbook,
        rationale=rationale,
    )


def classify_and_select_playbook(
    intake: IncidentRecord | SkillResult | Mapping[str, Any],
    *,
    override: str | None = None,
    playbook_map: Mapping[IncidentType, str] | None = None,
    state: IncidentState | None = None,
) -> tuple[ClassificationDecision, PlaybookSelectionDecision]:
    classification = classify_incident(intake)
    selection = select_playbook(classification, override=override, playbook_map=playbook_map)
    if state is not None:
        state.set_classification(
            classification.incident_type,
            scope_summary=classification.scope_summary,
            rationale=classification.rationale,
        )
        state.set_playbook(selection.playbook_name, rationale=selection.rationale)
    return classification, selection


def intake_input_to_incident_record(
    payload: IncidentIntakeInput | Mapping[str, Any],
) -> IncidentRecord:
    intake_input = (
        payload
        if isinstance(payload, IncidentIntakeInput)
        else IncidentIntakeInput.model_validate(dict(payload))
    )
    return IncidentRecord(
        incident_id=intake_input.incident_id,
        reporter=intake_input.reporter,
        summary=intake_input.complaint,
        location=intake_input.location,
        site_id=intake_input.site_id,
        device_type=intake_input.device_type,
        client_id=intake_input.client_id,
        client_mac=intake_input.client_mac,
        ssid=intake_input.ssid,
        movement_state=intake_input.movement_state,
        wired_also_affected=intake_input.wired_also_affected,
        reconnect_helps=intake_input.reconnect_helps,
        impacted_apps=intake_input.impacted_apps,
        occurred_at=intake_input.occurred_at,
        notes=intake_input.notes,
    )