from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from nettools.models import (
    Confidence,
    Finding,
    FindingSeverity,
    IncidentRecord,
    ScopeType,
    SkillResult,
    Status,
    TimeWindow,
)
from nettools.orchestrator import SkillExecutionRecord
from nettools.orchestrator.diagnose_incident import (
    DiagnoseIncidentInput,
    evaluate_diagnose_incident,
)
from nettools.priority1 import AdapterBundle


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _skill_record(
    skill_name: str,
    *,
    scope_type: ScopeType = ScopeType.SERVICE,
    scope_id: str = "scope-1",
    status: Status = Status.OK,
    findings: list[Finding] | None = None,
    evidence: dict[str, Any] | None = None,
    error_type: str | None = None,
) -> SkillExecutionRecord:
    observed_at = _now()
    result = SkillResult(
        status=status,
        skill_name=skill_name,
        scope_type=scope_type,
        scope_id=scope_id,
        summary=f"{skill_name} summary",
        confidence=Confidence.MEDIUM,
        observed_at=observed_at,
        time_window=TimeWindow(start=observed_at, end=observed_at),
        evidence=evidence or {},
        findings=findings or [],
        next_actions=[],
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
        error_type=error_type,
    )


def _finding(code: str, *, severity: FindingSeverity = FindingSeverity.WARN) -> Finding:
    return Finding(code=code, severity=severity, message=code)


def _fake_invoke(
    records: dict[str, list[SkillExecutionRecord]],
    calls: list[str],
    payloads: list[tuple[str, dict[str, Any]]] | None = None,
) -> Callable[..., SkillExecutionRecord]:
    def fake_invoke(
        skill_name: str,
        payload: Any,
        adapters: AdapterBundle,
        *,
        resolver: Any = None,
        logger: Any = None,
    ) -> SkillExecutionRecord:
        captured_payload = dict(payload)
        del adapters, resolver, logger
        calls.append(skill_name)
        if payloads is not None:
            payloads.append((skill_name, captured_payload))
        return records[skill_name].pop(0)

    return fake_invoke


def _payload_subset(
    payloads: list[tuple[str, dict[str, Any]]],
    skill_name: str,
    *keys: str,
) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for current_skill, payload in payloads:
        if current_skill != skill_name:
            continue
        filtered.append({key: payload[key] for key in keys if key in payload})
    return filtered


def test_diagnose_incident_runs_intake_then_high_confidence_auth_path(
    monkeypatch: Any,
) -> None:
    calls: list[str] = []
    records = {
        "net.incident_intake": [
            _skill_record(
                "net.incident_intake",
                scope_type=ScopeType.CLIENT,
                scope_id="client-1",
                evidence={
                    "incident_record": {
                        "incident_id": "inc-auth-1",
                        "summary": "Laptop cannot connect and reconnect helps",
                        "site_id": "hq-1",
                        "client_id": "client-1",
                        "reconnect_helps": True,
                    }
                },
            )
        ],
        "net.auth_8021x_radius": [
            _skill_record(
                "net.auth_8021x_radius",
                scope_type=ScopeType.CLIENT,
                scope_id="client-1",
                status=Status.WARN,
                findings=[
                    _finding("LOW_AUTH_SUCCESS_RATE"),
                    _finding("AUTH_TIMEOUTS"),
                    _finding("RADIUS_UNREACHABLE", severity=FindingSeverity.CRITICAL),
                ],
            )
        ],
    }
    monkeypatch.setattr(
        "nettools.orchestrator.diagnose_incident.invoke_skill",
        _fake_invoke(records, calls),
    )

    result = evaluate_diagnose_incident(
        DiagnoseIncidentInput(
            site_id="hq-1",
            client_id="client-1",
            complaint="My laptop cannot connect to CorpWiFi and reconnect helps",
        ),
        AdapterBundle(),
    )

    report = result.evidence["diagnosis_report"]

    assert calls == ["net.incident_intake", "net.auth_8021x_radius"]
    assert result.skill_name == "net.diagnose_incident"
    assert result.status is Status.WARN
    assert report["incident_type"] == "auth_or_onboarding"
    assert report["playbook_used"] == "auth_or_onboarding_issue"
    assert report["stop_reason"]["code"] == "high_confidence_diagnosis"
    assert report["ranked_causes"][0]["domain"] == "auth_issue"
    assert report["recommended_followup_skills"] == []


def test_diagnose_incident_uses_pre_normalized_record_without_intake(
    monkeypatch: Any,
) -> None:
    calls: list[str] = []
    records = {
        "net.change_detection": [
            _skill_record(
                "net.change_detection",
                scope_type=ScopeType.SITE,
                scope_id="hq-1",
            )
        ],
        "net.path_probe": [
            _skill_record(
                "net.path_probe",
                scope_type=ScopeType.SITE,
                scope_id="hq-1",
            )
        ],
        "net.stp_loop_anomaly": [
            _skill_record(
                "net.stp_loop_anomaly",
                scope_type=ScopeType.SITE,
                scope_id="hq-1",
            )
        ],
    }
    monkeypatch.setattr(
        "nettools.orchestrator.diagnose_incident.invoke_skill",
        _fake_invoke(records, calls),
    )

    result = evaluate_diagnose_incident(
        DiagnoseIncidentInput(
            incident_record=IncidentRecord(
                incident_id="inc-site-1",
                summary="Everyone on site says the network is slow",
                site_id="hq-1",
                wired_also_affected=True,
            )
        ),
        AdapterBundle(),
    )

    report = result.evidence["diagnosis_report"]

    assert calls == ["net.change_detection", "net.path_probe", "net.stp_loop_anomaly"]
    assert result.status is Status.UNKNOWN
    assert report["incident_type"] == "site_wide"
    assert report["playbook_used"] == "site_wide_internal_slowdown"
    assert report["stop_reason"]["code"] == "no_new_information"
    assert report["recommended_followup_skills"] == []


def test_diagnose_incident_samples_area_playbook_targets_from_candidates(
    monkeypatch: Any,
) -> None:
    calls: list[str] = []
    payloads: list[tuple[str, dict[str, Any]]] = []
    records = {
        "net.ap_rf_health": [
            _skill_record(
                "net.ap_rf_health",
                scope_type=ScopeType.AP,
                scope_id="AP-02",
            ),
            _skill_record(
                "net.ap_rf_health",
                scope_type=ScopeType.AP,
                scope_id="AP-11",
                status=Status.WARN,
                findings=[_finding("HIGH_CHANNEL_UTILIZATION")],
                evidence={"ap_name": "AP-11"},
            ),
        ],
        "net.client_health": [
            _skill_record(
                "net.client_health",
                scope_type=ScopeType.CLIENT,
                scope_id="client-a",
            ),
            _skill_record(
                "net.client_health",
                scope_type=ScopeType.CLIENT,
                scope_id="client-b",
            ),
        ],
    }
    monkeypatch.setattr(
        "nettools.orchestrator.diagnose_incident.invoke_skill",
        _fake_invoke(records, calls, payloads),
    )

    result = evaluate_diagnose_incident(
        DiagnoseIncidentInput(
            incident_record=IncidentRecord(
                incident_id="inc-area-1",
                summary="Users in the east conference area have unstable Wi-Fi",
                site_id="hq-1",
                location="east conference area",
            ),
            candidate_ap_names=["AP-20", "AP-11", "AP-02"],
            candidate_client_ids=["client-b", "client-a"],
            max_steps=2,
        ),
        AdapterBundle(),
    )

    report = result.evidence["diagnosis_report"]

    assert calls == [
        "net.ap_rf_health",
        "net.ap_rf_health",
        "net.client_health",
        "net.client_health",
    ]
    assert _payload_subset(payloads, "net.ap_rf_health", "site_id", "ap_name") == [
        {"site_id": "hq-1", "ap_name": "AP-02"},
        {"site_id": "hq-1", "ap_name": "AP-11"},
    ]
    assert _payload_subset(payloads, "net.client_health", "site_id", "client_id") == [
        {"site_id": "hq-1", "client_id": "client-a"},
        {"site_id": "hq-1", "client_id": "client-b"},
    ]
    assert report["playbook_used"] == "area_based_wifi_issue"
    assert report["sampling_summary"]["sampled_aps"] == ["AP-02", "AP-11"]
    assert report["sampling_summary"]["sampled_clients"] == ["client-a", "client-b"]


def test_diagnose_incident_derives_site_ap_samples_from_change_evidence(
    monkeypatch: Any,
) -> None:
    calls: list[str] = []
    payloads: list[tuple[str, dict[str, Any]]] = []
    records = {
        "net.change_detection": [
            _skill_record(
                "net.change_detection",
                scope_type=ScopeType.SITE,
                scope_id="hq-1",
                status=Status.WARN,
                findings=[_finding("RECENT_RELEVANT_CHANGE")],
                evidence={
                    "ranked_changes": [
                        {
                            "score": 0.9,
                            "category": "wireless",
                            "summary": "AP-9 firmware changed",
                            "payload": {"device_id": "ap-9", "device_type": "wireless_ap"},
                        },
                        {
                            "score": 0.8,
                            "category": "wireless",
                            "summary": "AP-3 radio profile changed",
                            "payload": {"device_id": "ap-3", "device_type": "wireless_ap"},
                        },
                    ]
                },
            )
        ],
        "net.path_probe": [
            _skill_record(
                "net.path_probe",
                scope_type=ScopeType.SITE,
                scope_id="hq-1",
                status=Status.WARN,
                findings=[_finding("SITE_WIDE_PATH_LOSS")],
            )
        ],
        "net.stp_loop_anomaly": [
            _skill_record(
                "net.stp_loop_anomaly",
                scope_type=ScopeType.SITE,
                scope_id="hq-1",
            )
        ],
        "net.ap_uplink_health": [
            _skill_record(
                "net.ap_uplink_health",
                scope_type=ScopeType.AP,
                scope_id="ap-3",
                evidence={"ap_id": "ap-3"},
            ),
            _skill_record(
                "net.ap_uplink_health",
                scope_type=ScopeType.AP,
                scope_id="ap-9",
                evidence={"ap_id": "ap-9"},
            ),
        ],
    }
    monkeypatch.setattr(
        "nettools.orchestrator.diagnose_incident.invoke_skill",
        _fake_invoke(records, calls, payloads),
    )

    result = evaluate_diagnose_incident(
        DiagnoseIncidentInput(
            incident_record=IncidentRecord(
                incident_id="inc-site-sampling",
                summary="Everyone on site says the network is slow",
                site_id="hq-1",
                wired_also_affected=True,
            ),
            max_steps=4,
        ),
        AdapterBundle(),
    )

    report = result.evidence["diagnosis_report"]
    ap_uplink_payloads = _payload_subset(payloads, "net.ap_uplink_health", "site_id", "ap_id")

    assert calls == [
        "net.change_detection",
        "net.path_probe",
        "net.stp_loop_anomaly",
        "net.ap_uplink_health",
        "net.ap_uplink_health",
    ]
    assert ap_uplink_payloads == [
        {"site_id": "hq-1", "ap_id": "ap-3"},
        {"site_id": "hq-1", "ap_id": "ap-9"},
    ]
    assert report["playbook_used"] == "site_wide_internal_slowdown"
    assert report["sampling_summary"]["sampled_aps"] == ["ap-3", "ap-9"]
    assert report["sampling_summary"]["sampled_comparison_aps"] == []


def test_diagnose_incident_selects_implicit_site_control_ap_when_available(
    monkeypatch: Any,
) -> None:
    calls: list[str] = []
    payloads: list[tuple[str, dict[str, Any]]] = []
    records = {
        "net.change_detection": [
            _skill_record(
                "net.change_detection",
                scope_type=ScopeType.SITE,
                scope_id="hq-1",
                status=Status.WARN,
                findings=[_finding("RECENT_RELEVANT_CHANGE")],
                evidence={
                    "ranked_changes": [
                        {
                            "score": 0.92,
                            "category": "wireless",
                            "summary": "AP-9 firmware changed",
                            "payload": {"device_id": "ap-9", "device_type": "wireless_ap"},
                        },
                        {
                            "score": 0.85,
                            "category": "wireless",
                            "summary": "AP-3 radio profile changed",
                            "payload": {"device_id": "ap-3", "device_type": "wireless_ap"},
                        },
                    ]
                },
            )
        ],
        "net.path_probe": [
            _skill_record(
                "net.path_probe",
                scope_type=ScopeType.SITE,
                scope_id="hq-1",
                status=Status.WARN,
                findings=[_finding("SITE_WIDE_PATH_LOSS")],
                evidence={"current_ap": "ap-control"},
            )
        ],
        "net.stp_loop_anomaly": [
            _skill_record(
                "net.stp_loop_anomaly",
                scope_type=ScopeType.SITE,
                scope_id="hq-1",
            )
        ],
        "net.ap_uplink_health": [
            _skill_record(
                "net.ap_uplink_health",
                scope_type=ScopeType.AP,
                scope_id="ap-control",
                evidence={"ap_name": "ap-control"},
            ),
            _skill_record(
                "net.ap_uplink_health",
                scope_type=ScopeType.AP,
                scope_id="ap-3",
                evidence={"ap_id": "ap-3"},
            ),
            _skill_record(
                "net.ap_uplink_health",
                scope_type=ScopeType.AP,
                scope_id="ap-9",
                evidence={"ap_id": "ap-9"},
            ),
        ],
    }
    monkeypatch.setattr(
        "nettools.orchestrator.diagnose_incident.invoke_skill",
        _fake_invoke(records, calls, payloads),
    )

    result = evaluate_diagnose_incident(
        DiagnoseIncidentInput(
            incident_record=IncidentRecord(
                incident_id="inc-site-control",
                summary="Everyone on site says the network is slow",
                site_id="hq-1",
                wired_also_affected=True,
            ),
            max_steps=4,
        ),
        AdapterBundle(),
    )

    report = result.evidence["diagnosis_report"]
    ap_uplink_payloads = _payload_subset(
        payloads,
        "net.ap_uplink_health",
        "site_id",
        "ap_id",
        "ap_name",
    )

    assert calls == [
        "net.change_detection",
        "net.path_probe",
        "net.stp_loop_anomaly",
        "net.ap_uplink_health",
        "net.ap_uplink_health",
        "net.ap_uplink_health",
    ]
    assert ap_uplink_payloads == [
        {"site_id": "hq-1", "ap_name": "ap-control"},
        {"site_id": "hq-1", "ap_id": "ap-3"},
        {"site_id": "hq-1", "ap_id": "ap-9"},
    ]
    assert report["sampling_summary"]["sampled_aps"] == ["ap-control", "ap-3", "ap-9"]
    assert report["sampling_summary"]["sampled_comparison_aps"] == ["ap-control"]
    assert report["sampling_summary"]["sampled_comparison_areas"] == []


def test_diagnose_incident_reserves_implicit_site_control_area_when_area_heavy(
    monkeypatch: Any,
) -> None:
    calls: list[str] = []
    payloads: list[tuple[str, dict[str, Any]]] = []
    records = {
        "net.change_detection": [
            _skill_record(
                "net.change_detection",
                scope_type=ScopeType.SITE,
                scope_id="hq-1",
                status=Status.WARN,
                findings=[_finding("RECENT_RELEVANT_CHANGE")],
                evidence={
                    "ranked_changes": [
                        {
                            "score": 0.92,
                            "category": "wireless",
                            "summary": "AP-9 firmware changed",
                            "payload": {"device_id": "ap-9", "device_type": "wireless_ap"},
                        }
                    ]
                },
            )
        ],
        "net.path_probe": [
            _skill_record(
                "net.path_probe",
                scope_type=ScopeType.SITE,
                scope_id="hq-1",
                status=Status.WARN,
                findings=[_finding("SITE_WIDE_PATH_LOSS")],
                evidence={
                    "probe_locations": ["east wing", "west wing", "north lab"],
                    "current_ap": "ap-control",
                },
            )
        ],
        "net.stp_loop_anomaly": [
            _skill_record(
                "net.stp_loop_anomaly",
                scope_type=ScopeType.SITE,
                scope_id="hq-1",
            )
        ],
        "net.ap_uplink_health": [
            _skill_record(
                "net.ap_uplink_health",
                scope_type=ScopeType.AP,
                scope_id="ap-control",
                evidence={"ap_name": "ap-control"},
            ),
            _skill_record(
                "net.ap_uplink_health",
                scope_type=ScopeType.AP,
                scope_id="ap-9",
                evidence={"ap_id": "ap-9"},
            ),
        ],
    }
    monkeypatch.setattr(
        "nettools.orchestrator.diagnose_incident.invoke_skill",
        _fake_invoke(records, calls, payloads),
    )

    result = evaluate_diagnose_incident(
        DiagnoseIncidentInput(
            incident_record=IncidentRecord(
                incident_id="inc-site-area-control",
                summary="Everyone on site says the network is slow",
                site_id="hq-1",
                wired_also_affected=True,
            ),
            max_steps=4,
        ),
        AdapterBundle(),
    )

    report = result.evidence["diagnosis_report"]
    ap_uplink_payloads = _payload_subset(
        payloads,
        "net.ap_uplink_health",
        "site_id",
        "ap_id",
        "ap_name",
    )

    assert calls == [
        "net.change_detection",
        "net.path_probe",
        "net.stp_loop_anomaly",
        "net.ap_uplink_health",
        "net.ap_uplink_health",
    ]
    assert ap_uplink_payloads == [
        {"site_id": "hq-1", "ap_name": "ap-control"},
        {"site_id": "hq-1", "ap_id": "ap-9"},
    ]
    assert report["sampling_summary"]["sampled_areas"] == ["east wing", "west wing", "north lab"]
    assert report["sampling_summary"]["sampled_comparison_aps"] == ["ap-control"]
    assert report["sampling_summary"]["sampled_comparison_areas"] == ["north lab"]


def test_diagnose_incident_uses_explicit_candidate_and_comparison_areas(
    monkeypatch: Any,
) -> None:
    calls: list[str] = []
    payloads: list[tuple[str, dict[str, Any]]] = []
    records = {
        "net.change_detection": [
            _skill_record(
                "net.change_detection",
                scope_type=ScopeType.SITE,
                scope_id="hq-1",
                status=Status.WARN,
                findings=[_finding("RECENT_RELEVANT_CHANGE")],
                evidence={
                    "ranked_changes": [
                        {
                            "score": 0.91,
                            "category": "wireless",
                            "summary": "AP-1 firmware changed",
                            "payload": {"device_id": "ap-1", "device_type": "wireless_ap"},
                        }
                    ]
                },
            )
        ],
        "net.path_probe": [
            _skill_record(
                "net.path_probe",
                scope_type=ScopeType.SITE,
                scope_id="hq-1",
                status=Status.WARN,
                findings=[_finding("SITE_WIDE_PATH_LOSS")],
            )
        ],
        "net.stp_loop_anomaly": [
            _skill_record(
                "net.stp_loop_anomaly",
                scope_type=ScopeType.SITE,
                scope_id="hq-1",
            )
        ],
        "net.ap_uplink_health": [
            _skill_record(
                "net.ap_uplink_health",
                scope_type=ScopeType.AP,
                scope_id="ap-1",
                evidence={"ap_id": "ap-1"},
            )
        ],
    }
    monkeypatch.setattr(
        "nettools.orchestrator.diagnose_incident.invoke_skill",
        _fake_invoke(records, calls, payloads),
    )

    result = evaluate_diagnose_incident(
        DiagnoseIncidentInput(
            incident_record=IncidentRecord(
                incident_id="inc-site-explicit-areas",
                summary="Everyone on site says the network is slow",
                site_id="hq-1",
                wired_also_affected=True,
            ),
            candidate_areas=["west wing", "east wing"],
            comparison_areas=["south lab"],
            max_steps=4,
        ),
        AdapterBundle(),
    )

    report = result.evidence["diagnosis_report"]

    assert calls == [
        "net.change_detection",
        "net.path_probe",
        "net.stp_loop_anomaly",
        "net.ap_uplink_health",
    ]
    assert report["sampling_summary"]["sampled_areas"] == ["east wing", "west wing"]
    assert report["sampling_summary"]["sampled_comparison_areas"] == ["south lab"]
