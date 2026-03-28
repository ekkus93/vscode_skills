from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ..models import IncidentRecord, ScopeType
from .playbooks import PlaybookDefinition
from .state import IncidentState

CLIENT_SCOPED_SKILLS = {
    "net.client_health",
    "net.roaming_analysis",
    "net.segmentation_policy",
}
AP_SCOPED_SKILLS = {
    "net.ap_rf_health",
    "net.ap_uplink_health",
}
_WIRELESS_TOKENS = ("wireless", "ap", "radio", "rf", "channel", "ssid")
_MAC_RE = re.compile(r"^[0-9a-f]{2}([:-][0-9a-f]{2}){5}$", re.IGNORECASE)


@dataclass(order=True)
class _Candidate:
    sort_key: tuple[int, str, str] = field(init=False, repr=False)
    priority: int
    key: str
    value: str
    reason: str
    is_control: bool = False

    def __post_init__(self) -> None:
        self.sort_key = (-self.priority, self.key, self.value)


def _ascending_candidate_sort_key(candidate: _Candidate) -> tuple[int, str, str]:
    return (candidate.priority, candidate.key, candidate.value)


@dataclass
class SamplingPlan:
    client_payloads: list[dict[str, Any]]
    ap_payloads: list[dict[str, Any]]
    rationale: list[str]


@dataclass
class _SamplingPools:
    primary_pool: dict[tuple[str, str], _Candidate] = field(default_factory=dict)
    explicit_control_pool: dict[tuple[str, str], _Candidate] = field(default_factory=dict)
    implicit_control_pool: dict[tuple[str, str], _Candidate] = field(default_factory=dict)


@dataclass
class AreaSamplingSelection:
    sampled_areas: list[str]
    comparison_areas: list[str]
    rationale: list[str]


def _looks_like_mac(value: str | None) -> bool:
    return bool(value and _MAC_RE.match(value))


def _normalized_tokens(*values: Any) -> str:
    return " ".join(str(value).strip().lower() for value in values if value)


def _append_unique(target: list[str], *values: str | None) -> None:
    for value in values:
        if value is None:
            continue
        normalized = str(value).strip()
        if not normalized or normalized in target:
            continue
        target.append(normalized)


def _append_area_values(target: list[str], values: Any) -> None:
    if isinstance(values, list):
        for value in values:
            if isinstance(value, str):
                _append_unique(target, value)
        return
    if isinstance(values, str):
        _append_unique(target, values)


def _candidate_attr(skill_input: Any, attribute: str) -> list[str]:
    raw_value = getattr(skill_input, attribute, None)
    if raw_value is None:
        return []
    return [str(value).strip() for value in raw_value if str(value).strip()]


def _ap_like_from_change(
    payload: dict[str, Any],
    category: str | None,
    summary: str | None,
) -> str | None:
    if not isinstance(payload, dict):
        return None
    device_id = payload.get("device_id")
    tokens = _normalized_tokens(payload.get("device_type"), category, summary)
    if device_id and any(token in tokens for token in _WIRELESS_TOKENS):
        return str(device_id)
    return None


def _merge_candidate(pool: dict[tuple[str, str], _Candidate], candidate: _Candidate) -> None:
    key = (candidate.key, candidate.value)
    existing = pool.get(key)
    if existing is None or candidate.priority > existing.priority:
        pool[key] = candidate
        return
    if candidate.reason != existing.reason and candidate.reason not in existing.reason:
        existing.reason = f"{existing.reason}; {candidate.reason}"


def _add_candidates(
    pool: dict[tuple[str, str], _Candidate],
    *,
    key: str,
    values: list[str],
    priority: int,
    reason: str,
    is_control: bool = False,
) -> None:
    for value in values:
        _merge_candidate(
            pool,
            _Candidate(
                priority=priority,
                key=key,
                value=value,
                reason=reason,
                is_control=is_control,
            ),
        )


def refresh_scope_candidates(
    state: IncidentState,
    *,
    skill_input: Any,
    incident_record: IncidentRecord,
) -> None:
    scope = state.scope_summary
    scope.site_id = (
        scope.site_id
        or getattr(skill_input, "site_id", None)
        or incident_record.site_id
    )
    scope.ssid = scope.ssid or getattr(skill_input, "ssid", None) or incident_record.ssid
    _append_unique(
        scope.affected_areas,
        incident_record.location,
        getattr(skill_input, "location", None),
    )
    _append_unique(scope.affected_areas, *_candidate_attr(skill_input, "candidate_areas"))
    _append_unique(scope.affected_areas, *_candidate_attr(skill_input, "comparison_areas"))

    _append_unique(
        scope.known_client_ids,
        incident_record.client_id,
        getattr(skill_input, "client_id", None),
    )
    _append_unique(
        scope.known_client_macs,
        incident_record.client_mac,
        getattr(skill_input, "client_mac", None),
    )
    _append_unique(scope.known_client_ids, *_candidate_attr(skill_input, "candidate_client_ids"))
    _append_unique(scope.known_client_macs, *_candidate_attr(skill_input, "candidate_client_macs"))
    _append_unique(scope.known_ap_ids, getattr(skill_input, "ap_id", None))
    _append_unique(scope.known_ap_names, getattr(skill_input, "ap_name", None))
    _append_unique(scope.known_ap_ids, *_candidate_attr(skill_input, "candidate_ap_ids"))
    _append_unique(scope.known_ap_names, *_candidate_attr(skill_input, "candidate_ap_names"))
    _append_unique(scope.known_ap_ids, *_candidate_attr(skill_input, "comparison_ap_ids"))
    _append_unique(scope.known_ap_names, *_candidate_attr(skill_input, "comparison_ap_names"))

    for entry in state.evidence_log:
        if entry.scope_type is ScopeType.CLIENT:
            if _looks_like_mac(entry.scope_id):
                _append_unique(scope.known_client_macs, entry.scope_id)
            else:
                _append_unique(scope.known_client_ids, entry.scope_id)
        elif entry.scope_type is ScopeType.AP:
            ap_id = entry.evidence.get("ap_id") if isinstance(entry.evidence, dict) else None
            ap_name = entry.evidence.get("ap_name") if isinstance(entry.evidence, dict) else None
            if ap_id or ap_name:
                _append_unique(scope.known_ap_ids, ap_id)
                _append_unique(scope.known_ap_names, ap_name)
            elif entry.scope_id:
                _append_unique(scope.known_ap_names, entry.scope_id)

        if not isinstance(entry.evidence, dict):
            continue
        _append_unique(scope.known_ap_ids, entry.evidence.get("ap_id"))
        _append_unique(
            scope.known_ap_names,
            entry.evidence.get("ap_name"),
            entry.evidence.get("connected_ap"),
            entry.evidence.get("current_ap"),
        )
        _append_area_values(scope.affected_areas, entry.evidence.get("probe_locations"))
        _append_area_values(scope.affected_areas, entry.evidence.get("source_location"))

        resolver_results = entry.evidence.get("resolver_results")
        if isinstance(resolver_results, list):
            for resolver in resolver_results:
                if not isinstance(resolver, dict):
                    continue
                _append_area_values(scope.affected_areas, resolver.get("source_location"))

        transitions = entry.evidence.get("ap_transitions")
        if isinstance(transitions, list):
            for transition in transitions:
                if not isinstance(transition, str):
                    continue
                for candidate in transition.split("->"):
                    _append_unique(scope.known_ap_names, candidate.strip())

        ranked_changes = entry.evidence.get("ranked_changes")
        if isinstance(ranked_changes, list):
            for item in ranked_changes:
                if not isinstance(item, dict):
                    continue
                payload = item.get("payload")
                ap_id = _ap_like_from_change(
                    payload if isinstance(payload, dict) else {},
                    item.get("category"),
                    item.get("summary"),
                )
                _append_unique(scope.known_ap_ids, ap_id)

        aggregate = entry.evidence.get("aggregated_evidence")
        if isinstance(aggregate, dict):
            for collection_name in ("events", "changes"):
                collection = aggregate.get(collection_name)
                if not isinstance(collection, list):
                    continue
                for item in collection:
                    if not isinstance(item, dict):
                        continue
                    ap_id = _ap_like_from_change(
                        item,
                        item.get("event_type") or item.get("category"),
                        item.get("summary"),
                    )
                    _append_unique(scope.known_ap_ids, ap_id)

    scope.known_clients = list(dict.fromkeys(scope.known_client_ids + scope.known_client_macs))
    scope.known_aps = list(dict.fromkeys(scope.known_ap_ids + scope.known_ap_names))


def _select_candidates(
    primary_pool: dict[tuple[str, str], _Candidate],
    control_candidate: _Candidate | None,
    *,
    limit: int,
) -> list[_Candidate]:
    if limit <= 0:
        return []

    primaries = sorted(primary_pool.values(), key=lambda item: item.sort_key)
    selected: list[_Candidate] = []
    selected_keys: set[tuple[str, str]] = set()

    if control_candidate is not None and limit > 1:
        selected.append(control_candidate)
        selected_keys.add((control_candidate.key, control_candidate.value))

    for candidate in primaries:
        key = (candidate.key, candidate.value)
        if key in selected_keys:
            continue
        selected.append(candidate)
        selected_keys.add(key)
        if len(selected) >= limit:
            break

    return selected


def _payloads_from_candidates(
    base_payload: dict[str, Any],
    candidates: list[_Candidate],
) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for candidate in candidates:
        payload = dict(base_payload)
        payload[candidate.key] = candidate.value
        payloads.append(payload)
    return payloads


def _best_control_candidate(
    pools: _SamplingPools,
    *,
    allow_primary_fallback: bool,
) -> _Candidate | None:
    if pools.explicit_control_pool:
        return sorted(pools.explicit_control_pool.values(), key=lambda item: item.sort_key)[0]

    if pools.implicit_control_pool:
        return sorted(
            pools.implicit_control_pool.values(),
            key=_ascending_candidate_sort_key,
        )[0]

    if not allow_primary_fallback or len(pools.primary_pool) < 3:
        return None

    fallback = sorted(pools.primary_pool.values(), key=_ascending_candidate_sort_key)[0]
    return _Candidate(
        priority=fallback.priority,
        key=fallback.key,
        value=fallback.value,
        reason="implicit comparison fallback from least implicated primary candidate",
        is_control=True,
    )


def _ap_control_candidate(
    pools: _SamplingPools,
    *,
    playbook: PlaybookDefinition,
) -> _Candidate | None:
    if playbook.name != "site_wide_internal_slowdown" and not pools.explicit_control_pool:
        return None

    return _best_control_candidate(
        pools,
        allow_primary_fallback=playbook.name == "site_wide_internal_slowdown",
    )


def _build_area_sampling_selection(
    *,
    state: IncidentState,
    skill_input: Any,
    playbook: PlaybookDefinition,
    ap_signal_count: int,
) -> AreaSamplingSelection:
    pools = _SamplingPools()
    explicit_candidate_areas = sorted(
        dict.fromkeys(_candidate_attr(skill_input, "candidate_areas"))
    )
    explicit_comparison_areas = sorted(
        dict.fromkeys(_candidate_attr(skill_input, "comparison_areas"))
    )
    discovered_areas = list(dict.fromkeys(state.scope_summary.affected_areas))

    if explicit_candidate_areas:
        _add_candidates(
            pools.primary_pool,
            key="area",
            values=explicit_candidate_areas,
            priority=95,
            reason="explicit candidate area",
        )
    else:
        _add_candidates(
            pools.primary_pool,
            key="area",
            values=discovered_areas,
            priority=70,
            reason="discovered affected area",
        )

    _add_candidates(
        pools.explicit_control_pool,
        key="area",
        values=explicit_comparison_areas,
        priority=20,
        reason="explicit comparison area",
        is_control=True,
    )

    if playbook.name == "site_wide_internal_slowdown":
        unique_areas = list(dict.fromkeys(discovered_areas))
        if len(unique_areas) > ap_signal_count:
            primary_area = unique_areas[0] if unique_areas else None
            implicit_control_areas = sorted(
                area for area in unique_areas if area and area != primary_area
            )
            _add_candidates(
                pools.implicit_control_pool,
                key="area",
                values=implicit_control_areas,
                priority=30,
                reason="implicit comparison area from area-heavy site-wide evidence",
                is_control=True,
            )

    control_candidate = _best_control_candidate(pools, allow_primary_fallback=False)
    sampled_areas = explicit_candidate_areas or discovered_areas
    comparison_areas = [control_candidate.value] if control_candidate is not None else []

    rationale = [
        f"Included area sample {area} from {pools.primary_pool[('area', area)].reason}."
        for area in sampled_areas
    ]
    if control_candidate is not None:
        rationale.append(
            f"Reserved comparison area {control_candidate.value} from {control_candidate.reason}."
        )

    return AreaSamplingSelection(
        sampled_areas=sampled_areas,
        comparison_areas=comparison_areas,
        rationale=rationale,
    )


def _client_sampling_plan(
    base_payload: dict[str, Any],
    *,
    state: IncidentState,
    skill_input: Any,
    playbook: PlaybookDefinition,
) -> tuple[list[dict[str, Any]], list[str]]:
    settings = playbook.sampling_settings
    if not settings.allow_client_sampling:
        return [], []

    pools = _SamplingPools()
    _add_candidates(
        pools.primary_pool,
        key="client_id",
        values=_candidate_attr(skill_input, "candidate_client_ids"),
        priority=95,
        reason="input candidate client",
    )
    _add_candidates(
        pools.primary_pool,
        key="client_mac",
        values=_candidate_attr(skill_input, "candidate_client_macs"),
        priority=95,
        reason="input candidate client MAC",
    )
    _add_candidates(
        pools.primary_pool,
        key="client_id",
        values=state.scope_summary.known_client_ids,
        priority=70,
        reason="discovered client identifier",
    )
    _add_candidates(
        pools.primary_pool,
        key="client_mac",
        values=state.scope_summary.known_client_macs,
        priority=70,
        reason="discovered client MAC",
    )

    selected = _select_candidates(pools.primary_pool, None, limit=settings.max_sampled_clients)
    state.scope_summary.sampled_clients = [candidate.value for candidate in selected]
    rationale = [
        f"Selected client sample {candidate.value} from {candidate.reason}."
        for candidate in selected
    ]
    return _payloads_from_candidates(base_payload, selected), rationale


def _ap_sampling_plan(
    base_payload: dict[str, Any],
    *,
    state: IncidentState,
    skill_input: Any,
    playbook: PlaybookDefinition,
) -> tuple[list[dict[str, Any]], list[str]]:
    settings = playbook.sampling_settings
    if not settings.allow_ap_sampling:
        return [], []

    pools = _SamplingPools()
    _add_candidates(
        pools.primary_pool,
        key="ap_id",
        values=_candidate_attr(skill_input, "candidate_ap_ids"),
        priority=95,
        reason="input candidate AP",
    )
    _add_candidates(
        pools.primary_pool,
        key="ap_name",
        values=_candidate_attr(skill_input, "candidate_ap_names"),
        priority=95,
        reason="input candidate AP",
    )
    _add_candidates(
        pools.explicit_control_pool,
        key="ap_id",
        values=_candidate_attr(skill_input, "comparison_ap_ids"),
        priority=20,
        reason="explicit comparison AP",
        is_control=True,
    )
    _add_candidates(
        pools.explicit_control_pool,
        key="ap_name",
        values=_candidate_attr(skill_input, "comparison_ap_names"),
        priority=20,
        reason="explicit comparison AP",
        is_control=True,
    )
    _add_candidates(
        pools.primary_pool,
        key="ap_id",
        values=state.scope_summary.known_ap_ids,
        priority=80,
        reason="evidence-derived AP identifier",
    )
    _add_candidates(
        pools.primary_pool,
        key="ap_name",
        values=state.scope_summary.known_ap_names,
        priority=70,
        reason="evidence-derived AP name",
    )

    impacted_ap_keys: set[tuple[str, str]] = set()
    observed_ap_keys: set[tuple[str, str]] = set()
    for entry in state.evidence_log:
        if not isinstance(entry.evidence, dict):
            continue

        ranked_changes = entry.evidence.get("ranked_changes")
        if isinstance(ranked_changes, list):
            for item in ranked_changes:
                if not isinstance(item, dict):
                    continue
                payload_raw = item.get("payload")
                payload: dict[str, Any] = payload_raw if isinstance(payload_raw, dict) else {}
                ap_id = _ap_like_from_change(payload, item.get("category"), item.get("summary"))
                if ap_id is not None:
                    impacted_ap_keys.add(("ap_id", ap_id))

        for key_name in ("ap_id", "ap_name"):
            value = entry.evidence.get(key_name)
            if value is not None:
                observed_ap_keys.add((key_name, str(value).strip()))
        for key_name in ("connected_ap", "current_ap"):
            value = entry.evidence.get(key_name)
            if value is not None:
                observed_ap_keys.add(("ap_name", str(value).strip()))
        transitions = entry.evidence.get("ap_transitions")
        if isinstance(transitions, list):
            for transition in transitions:
                if not isinstance(transition, str):
                    continue
                for transition_ap in transition.split("->"):
                    normalized = transition_ap.strip()
                    if normalized:
                        observed_ap_keys.add(("ap_name", normalized))

    for candidate_key in observed_ap_keys:
        if candidate_key in impacted_ap_keys:
            continue
        candidate = pools.primary_pool.get(candidate_key)
        if candidate is None:
            continue
        implicit_control_candidate = _Candidate(
            priority=candidate.priority,
            key=candidate.key,
            value=candidate.value,
            reason="implicit comparison AP from observed but not directly implicated scope",
            is_control=True,
        )
        _merge_candidate(pools.implicit_control_pool, implicit_control_candidate)

    control_candidate = _ap_control_candidate(pools, playbook=playbook)
    selected = _select_candidates(
        pools.primary_pool,
        control_candidate,
        limit=settings.max_sampled_aps,
    )
    state.scope_summary.sampled_aps = [candidate.value for candidate in selected]
    state.scope_summary.sampled_comparison_aps = [
        candidate.value for candidate in selected if candidate.is_control
    ]
    area_selection = _build_area_sampling_selection(
        state=state,
        skill_input=skill_input,
        playbook=playbook,
        ap_signal_count=len(pools.primary_pool),
    )
    state.scope_summary.sampled_areas = area_selection.sampled_areas
    state.scope_summary.sampled_comparison_areas = area_selection.comparison_areas
    rationale = [
        (
            f"Selected comparison AP sample {candidate.value} from {candidate.reason}."
            if candidate.is_control
            else f"Selected AP sample {candidate.value} from {candidate.reason}."
        )
        for candidate in selected
    ]
    rationale.extend(area_selection.rationale)
    return _payloads_from_candidates(base_payload, selected), rationale


def build_sampling_plan(
    skill_name: str,
    base_payload: dict[str, Any],
    *,
    state: IncidentState,
    skill_input: Any,
    incident_record: IncidentRecord,
    playbook: PlaybookDefinition,
) -> SamplingPlan:
    refresh_scope_candidates(state, skill_input=skill_input, incident_record=incident_record)

    if skill_name in CLIENT_SCOPED_SKILLS:
        client_payloads, rationale = _client_sampling_plan(
            base_payload,
            state=state,
            skill_input=skill_input,
            playbook=playbook,
        )
        state.scope_summary.sampling_rationale = rationale
        return SamplingPlan(client_payloads=client_payloads, ap_payloads=[], rationale=rationale)
    if skill_name in AP_SCOPED_SKILLS:
        ap_payloads, rationale = _ap_sampling_plan(
            base_payload,
            state=state,
            skill_input=skill_input,
            playbook=playbook,
        )
        state.scope_summary.sampling_rationale = rationale
        return SamplingPlan(client_payloads=[], ap_payloads=ap_payloads, rationale=rationale)
    state.scope_summary.sampling_rationale = []
    return SamplingPlan(client_payloads=[], ap_payloads=[], rationale=[])
