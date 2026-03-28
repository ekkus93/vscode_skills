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
from nettools.orchestrator import (
    DiagnoseIncidentAuditTrail,
    DiagnosticDomain,
    IncidentState,
    IncidentType,
    InvestigationStatus,
    InvestigationTraceEventType,
    OrchestratorConfig,
    PolicyControlConfig,
    ScopeSummary,
    SkillExecutionRecord,
    StopReason,
    StopReasonCode,
)
from nettools.orchestrator.diagnose_incident import (
    DiagnoseIncidentInput,
    _parse_input,
    build_diagnose_incident_parser,
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
    assert len(report["recommended_human_actions"]) == 1
    assert report["recommended_human_actions"][0].startswith(
        "Check 802.1X and RADIUS authentication failures for site hq-1, client client-1"
    )
    assert "LOW_AUTH_SUCCESS_RATE" in report["recommended_human_actions"][0]
    assert "AUTH_TIMEOUTS" in report["recommended_human_actions"][0]
    assert "RADIUS_UNREACHABLE" in report["recommended_human_actions"][0]
    assert (
        result.evidence["audit_trail"]["incident_id"]
        == result.evidence["incident_state"]["incident_id"]
    )
    assert (
        result.evidence["audit_trail"]["execution_records"][0]["skill_name"]
        == "net.incident_intake"
    )
    assert (
        result.evidence["audit_trail"]["investigation_trace"][0]["event_type"]
        == "playbook_selection"
    )
    assert result.evidence["investigation_metrics"] == {
        "playbook_invocations": {"auth_or_onboarding_issue": 1},
        "stop_reason_counts": {"high_confidence_diagnosis": 1},
        "diagnosis_domains_by_outcome": {"warn": {"auth_issue": 1}},
        "average_skill_count_per_investigation": 2.0,
    }


def test_diagnose_incident_uses_orchestrator_config_playbook_mapping(
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
                        "incident_id": "inc-config-1",
                        "summary": "Laptop sees weak Wi-Fi near the lobby",
                        "site_id": "hq-1",
                        "client_id": "client-1",
                    }
                },
            )
        ],
        "net.auth_8021x_radius": [
            _skill_record(
                "net.auth_8021x_radius",
                scope_type=ScopeType.CLIENT,
                scope_id="client-1",
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
            complaint="My laptop has weak Wi-Fi near the lobby",
            max_steps=1,
            orchestrator_config=OrchestratorConfig(
                playbook_mapping={IncidentType.SINGLE_CLIENT: "auth_or_onboarding_issue"}
            ),
        ),
        AdapterBundle(),
    )

    assert calls == ["net.incident_intake", "net.auth_8021x_radius"]
    assert result.evidence["incident_state"]["playbook_used"] == "auth_or_onboarding_issue"
    assert result.evidence["diagnosis_report"]["playbook_used"] == "auth_or_onboarding_issue"


def test_diagnose_incident_records_investigation_trace(
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
                        "incident_id": "inc-trace-1",
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

    trace = result.evidence["incident_state"]["investigation_trace"]
    event_types = [entry["event_type"] for entry in trace]

    assert calls == ["net.incident_intake", "net.auth_8021x_radius"]
    assert event_types == [
        InvestigationTraceEventType.PLAYBOOK_SELECTION.value,
        InvestigationTraceEventType.SCORE_UPDATE.value,
        InvestigationTraceEventType.BRANCH_DECISION.value,
        InvestigationTraceEventType.STOP_CONDITION_CHECK.value,
        InvestigationTraceEventType.FINAL_STOP_RATIONALE.value,
    ]
    assert trace[0]["details"]["playbook_name"] == "auth_or_onboarding_issue"
    assert trace[1]["details"]["top_domains"][0] == "auth_issue"
    assert trace[2]["details"]["selected_skill"] == "net.dhcp_path"
    assert trace[3]["details"]["stop_reason_code"] == "high_confidence_diagnosis"
    assert trace[4]["details"]["stop_reason_code"] == "high_confidence_diagnosis"


def test_diagnose_incident_runs_single_client_dns_path_end_to_end(
    monkeypatch: Any,
) -> None:
    calls: list[str] = []
    records = {
        "net.incident_intake": [
            _skill_record(
                "net.incident_intake",
                scope_type=ScopeType.CLIENT,
                scope_id="client-42",
                evidence={
                    "incident_record": {
                        "incident_id": "inc-single-1",
                        "summary": "A single laptop has intermittent access failures",
                        "site_id": "hq-1",
                        "client_id": "client-42",
                    }
                },
            )
        ],
        "net.client_health": [
            _skill_record(
                "net.client_health",
                scope_type=ScopeType.CLIENT,
                scope_id="client-42",
                status=Status.WARN,
                findings=[_finding("HIGH_PACKET_LOSS")],
            )
        ],
        "net.dns_latency": [
            _skill_record(
                "net.dns_latency",
                scope_type=ScopeType.CLIENT,
                scope_id="client-42",
                status=Status.WARN,
                findings=[
                    _finding("HIGH_DNS_LATENCY"),
                    _finding("DNS_TIMEOUT_RATE"),
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
            client_id="client-42",
            complaint="One laptop keeps timing out on web lookups and general browsing",
        ),
        AdapterBundle(),
    )

    report = result.evidence["diagnosis_report"]

    assert calls == ["net.incident_intake", "net.client_health", "net.dns_latency"]
    assert result.skill_name == "net.diagnose_incident"
    assert result.status is Status.WARN
    assert report["incident_type"] == "single_client"
    assert report["playbook_used"] == "single_client_wifi_issue"
    assert report["stop_reason"]["code"] == "high_confidence_diagnosis"
    assert report["ranked_causes"][0]["domain"] == "dns_issue"
    assert report["recommended_followup_skills"] == []
    assert len(report["recommended_human_actions"]) == 1
    assert report["recommended_human_actions"][0].startswith(
        "Check DNS resolver latency and timeout path for site hq-1, client client-42"
    )
    assert "HIGH_DNS_LATENCY" in report["recommended_human_actions"][0]
    assert "DNS_TIMEOUT_RATE" in report["recommended_human_actions"][0]
    assert "HIGH_PACKET_LOSS" not in report["recommended_human_actions"][0]


def test_diagnose_incident_reports_unresolved_two_domain_ambiguity(
    monkeypatch: Any,
) -> None:
    calls: list[str] = []
    records = {
        "net.incident_intake": [
            _skill_record(
                "net.incident_intake",
                scope_type=ScopeType.SERVICE,
                scope_id="hq-1",
                evidence={
                    "incident_record": {
                        "incident_id": "inc-ambiguous-1",
                        "summary": "Cannot connect sometimes and onboarding fails intermittently",
                        "site_id": "hq-1",
                        "ssid": "CorpWiFi",
                        "reconnect_helps": True,
                    }
                },
            )
        ],
        "net.auth_8021x_radius": [
            _skill_record(
                "net.auth_8021x_radius",
                scope_type=ScopeType.SERVICE,
                scope_id="hq-1",
                status=Status.WARN,
                findings=[
                    _finding("LOW_AUTH_SUCCESS_RATE"),
                    _finding("AUTH_TIMEOUTS"),
                ],
            )
        ],
        "net.dhcp_path": [
            _skill_record(
                "net.dhcp_path",
                scope_type=ScopeType.SERVICE,
                scope_id="hq-1",
                status=Status.WARN,
                findings=[
                    _finding("HIGH_DHCP_OFFER_LATENCY"),
                    _finding("HIGH_DHCP_ACK_LATENCY"),
                ],
            )
        ],
        "net.dns_latency": [
            _skill_record(
                "net.dns_latency",
                scope_type=ScopeType.SERVICE,
                scope_id="hq-1",
                status=Status.OK,
            )
        ],
        "net.incident_correlation": [
            _skill_record(
                "net.incident_correlation",
                scope_type=ScopeType.SERVICE,
                scope_id="hq-1",
                status=Status.OK,
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
            ssid="CorpWiFi",
            complaint="Cannot connect sometimes and onboarding fails intermittently",
        ),
        AdapterBundle(),
    )

    report = result.evidence["diagnosis_report"]

    assert calls == [
        "net.incident_intake",
        "net.auth_8021x_radius",
        "net.dhcp_path",
        "net.dns_latency",
        "net.incident_correlation",
    ]
    assert result.status is Status.WARN
    assert report["incident_type"] == "auth_or_onboarding"
    assert report["playbook_used"] == "auth_or_onboarding_issue"
    assert report["stop_reason"]["code"] == "two_domain_bounded_ambiguity"
    assert report["recommended_followup_skills"] == []
    assert report["ranked_causes"][0]["domain"] == "auth_issue"
    assert report["ranked_causes"][1]["domain"] == "dhcp_issue"
    assert "recommended_next_skill" not in result.evidence["incident_state"]
    assert len(report["recommended_human_actions"]) == 1
    assert report["recommended_human_actions"][0].startswith(
        "Collect one discriminator between auth_issue and dhcp_issue for site hq-1, SSID CorpWiFi"
    )
    assert "LOW_AUTH_SUCCESS_RATE" in report["recommended_human_actions"][0]
    assert "AUTH_TIMEOUTS" in report["recommended_human_actions"][0]
    assert "HIGH_DHCP_OFFER_LATENCY" in report["recommended_human_actions"][0]
    assert "HIGH_DHCP_ACK_LATENCY" in report["recommended_human_actions"][0]


def test_diagnose_incident_recommends_capture_trigger_when_authorized_and_useful(
    monkeypatch: Any,
) -> None:
    calls: list[str] = []
    records = {
        "net.incident_intake": [
            _skill_record(
                "net.incident_intake",
                scope_type=ScopeType.SERVICE,
                scope_id="hq-1",
                evidence={
                    "incident_record": {
                        "incident_id": "inc-capture-1",
                        "summary": (
                            "Onboarding intermittently fails and clients stall "
                            "after connect"
                        ),
                        "site_id": "hq-1",
                        "ssid": "CorpWiFi",
                    }
                },
            )
        ],
        "net.auth_8021x_radius": [
            _skill_record(
                "net.auth_8021x_radius",
                scope_type=ScopeType.SERVICE,
                scope_id="hq-1",
                status=Status.WARN,
                findings=[
                    _finding("LOW_AUTH_SUCCESS_RATE"),
                    _finding("AUTH_TIMEOUTS"),
                ],
            )
        ],
        "net.dhcp_path": [
            _skill_record(
                "net.dhcp_path",
                scope_type=ScopeType.SERVICE,
                scope_id="hq-1",
                status=Status.WARN,
                findings=[
                    _finding("HIGH_DHCP_OFFER_LATENCY"),
                    _finding("HIGH_DHCP_ACK_LATENCY"),
                ],
            )
        ],
        "net.dns_latency": [
            _skill_record(
                "net.dns_latency",
                scope_type=ScopeType.SERVICE,
                scope_id="hq-1",
                status=Status.OK,
            )
        ],
        "net.incident_correlation": [
            _skill_record(
                "net.incident_correlation",
                scope_type=ScopeType.SERVICE,
                scope_id="hq-1",
                status=Status.OK,
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
            ssid="CorpWiFi",
            complaint="Onboarding intermittently fails and clients stall after connect",
            capture_authorized=True,
            capture_approval_ticket="CHG-1234",
        ),
        AdapterBundle(),
    )

    report = result.evidence["diagnosis_report"]

    assert calls == [
        "net.incident_intake",
        "net.auth_8021x_radius",
        "net.dhcp_path",
        "net.dns_latency",
        "net.incident_correlation",
    ]
    assert report["stop_reason"]["code"] == "two_domain_bounded_ambiguity"
    assert report["recommended_followup_skills"] == ["net.capture_trigger"]
    assert [action.skill for action in result.next_actions] == ["net.capture_trigger"]
    assert "Authorized packet capture could help discriminate" in result.next_actions[0].reason


def test_diagnose_incident_does_not_recommend_capture_trigger_without_authorization(
    monkeypatch: Any,
) -> None:
    calls: list[str] = []
    records = {
        "net.incident_intake": [
            _skill_record(
                "net.incident_intake",
                scope_type=ScopeType.SERVICE,
                scope_id="hq-1",
                evidence={
                    "incident_record": {
                        "incident_id": "inc-capture-2",
                        "summary": (
                            "Onboarding intermittently fails and clients stall "
                            "after connect"
                        ),
                        "site_id": "hq-1",
                        "ssid": "CorpWiFi",
                    }
                },
            )
        ],
        "net.auth_8021x_radius": [
            _skill_record(
                "net.auth_8021x_radius",
                scope_type=ScopeType.SERVICE,
                scope_id="hq-1",
                status=Status.WARN,
                findings=[
                    _finding("LOW_AUTH_SUCCESS_RATE"),
                    _finding("AUTH_TIMEOUTS"),
                ],
            )
        ],
        "net.dhcp_path": [
            _skill_record(
                "net.dhcp_path",
                scope_type=ScopeType.SERVICE,
                scope_id="hq-1",
                status=Status.WARN,
                findings=[
                    _finding("HIGH_DHCP_OFFER_LATENCY"),
                    _finding("HIGH_DHCP_ACK_LATENCY"),
                ],
            )
        ],
        "net.dns_latency": [
            _skill_record(
                "net.dns_latency",
                scope_type=ScopeType.SERVICE,
                scope_id="hq-1",
                status=Status.OK,
            )
        ],
        "net.incident_correlation": [
            _skill_record(
                "net.incident_correlation",
                scope_type=ScopeType.SERVICE,
                scope_id="hq-1",
                status=Status.OK,
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
            ssid="CorpWiFi",
            complaint="Onboarding intermittently fails and clients stall after connect",
        ),
        AdapterBundle(),
    )

    report = result.evidence["diagnosis_report"]

    assert report["stop_reason"]["code"] == "two_domain_bounded_ambiguity"
    assert report["recommended_followup_skills"] == []
    assert result.next_actions == []


def test_diagnose_incident_policy_disables_capture_trigger_recommendation(
    monkeypatch: Any,
) -> None:
    calls: list[str] = []
    records = {
        "net.incident_intake": [
            _skill_record(
                "net.incident_intake",
                scope_type=ScopeType.SERVICE,
                scope_id="hq-1",
                evidence={
                    "incident_record": {
                        "incident_id": "inc-capture-policy-1",
                        "summary": (
                            "Onboarding intermittently fails and clients stall "
                            "after connect"
                        ),
                        "site_id": "hq-1",
                        "ssid": "CorpWiFi",
                    }
                },
            )
        ],
        "net.auth_8021x_radius": [
            _skill_record(
                "net.auth_8021x_radius",
                scope_type=ScopeType.SERVICE,
                scope_id="hq-1",
                status=Status.WARN,
                findings=[
                    _finding("LOW_AUTH_SUCCESS_RATE"),
                    _finding("AUTH_TIMEOUTS"),
                ],
            )
        ],
        "net.dhcp_path": [
            _skill_record(
                "net.dhcp_path",
                scope_type=ScopeType.SERVICE,
                scope_id="hq-1",
                status=Status.WARN,
                findings=[
                    _finding("HIGH_DHCP_OFFER_LATENCY"),
                    _finding("HIGH_DHCP_ACK_LATENCY"),
                ],
            )
        ],
        "net.dns_latency": [
            _skill_record(
                "net.dns_latency",
                scope_type=ScopeType.SERVICE,
                scope_id="hq-1",
                status=Status.OK,
            )
        ],
        "net.incident_correlation": [
            _skill_record(
                "net.incident_correlation",
                scope_type=ScopeType.SERVICE,
                scope_id="hq-1",
                status=Status.OK,
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
            ssid="CorpWiFi",
            complaint="Onboarding intermittently fails and clients stall after connect",
            capture_authorized=True,
            capture_approval_ticket="CHG-1234",
            orchestrator_config=OrchestratorConfig(
                policy_controls=PolicyControlConfig(allow_capture_triggers=False)
            ),
        ),
        AdapterBundle(),
    )

    report = result.evidence["diagnosis_report"]

    assert calls == [
        "net.incident_intake",
        "net.auth_8021x_radius",
        "net.dhcp_path",
        "net.dns_latency",
        "net.incident_correlation",
    ]
    assert report["stop_reason"]["code"] == "two_domain_bounded_ambiguity"
    assert report["recommended_followup_skills"] == []
    assert result.next_actions == []


def test_diagnose_incident_reports_blocked_dependency_end_to_end(
    monkeypatch: Any,
) -> None:
    calls: list[str] = []
    records = {
        "net.incident_intake": [
            _skill_record(
                "net.incident_intake",
                scope_type=ScopeType.SERVICE,
                scope_id="hq-1",
                evidence={
                    "incident_record": {
                        "incident_id": "inc-blocked-1",
                        "summary": "Cannot connect sometimes and reconnect helps",
                        "site_id": "hq-1",
                        "ssid": "CorpWiFi",
                        "reconnect_helps": True,
                    }
                },
            )
        ],
        "net.auth_8021x_radius": [
            _skill_record(
                "net.auth_8021x_radius",
                scope_type=ScopeType.SERVICE,
                scope_id="hq-1",
                status=Status.WARN,
                findings=[
                    _finding("LOW_AUTH_SUCCESS_RATE"),
                    _finding("AUTH_TIMEOUTS"),
                ],
            )
        ],
        "net.dhcp_path": [
            _skill_record(
                "net.dhcp_path",
                scope_type=ScopeType.SERVICE,
                scope_id="hq-1",
                status=Status.WARN,
                findings=[_finding("SCOPE_UTILIZATION_HIGH")],
            )
        ],
        "net.dns_latency": [
            _skill_record(
                "net.dns_latency",
                scope_type=ScopeType.SERVICE,
                scope_id="hq-1",
                status=Status.WARN,
                findings=[_finding("HIGH_DNS_LATENCY")],
            )
        ],
        "net.incident_correlation": [
            _skill_record(
                "net.incident_correlation",
                scope_type=ScopeType.SERVICE,
                scope_id="hq-1",
                status=Status.UNKNOWN,
                error_type="DependencyUnavailableError",
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
            ssid="CorpWiFi",
            complaint="Cannot connect sometimes and reconnect helps",
        ),
        AdapterBundle(),
    )

    report = result.evidence["diagnosis_report"]
    incident_state = result.evidence["incident_state"]

    assert calls == [
        "net.incident_intake",
        "net.auth_8021x_radius",
        "net.dhcp_path",
        "net.dns_latency",
        "net.incident_correlation",
    ]
    assert result.status is Status.FAIL
    assert report["incident_type"] == "auth_or_onboarding"
    assert report["playbook_used"] == "auth_or_onboarding_issue"
    assert report["stop_reason"]["code"] == "dependency_blocked"
    assert report["recommended_followup_skills"] == []
    assert incident_state["status"] == "blocked"
    assert report["dependency_failures"][0]["skill_name"] == "net.incident_correlation"
    assert report["recommended_human_actions"] == [
        (
            "Restore or bypass the dependency behind net.incident_correlation "
            "(DependencyUnavailableError) for site hq-1, SSID CorpWiFi "
            "and rerun the investigation."
        ),
    ]


def test_diagnose_incident_replays_serialized_state_without_live_execution(
    monkeypatch: Any,
) -> None:
    state = IncidentState(
        incident_id="inc-replay-1",
        incident_type=IncidentType.SINGLE_CLIENT,
        playbook_used="single_client_wifi_issue",
        status=InvestigationStatus.COMPLETED,
        scope_summary=ScopeSummary(
            site_id="hq-1",
            ssid="CorpWiFi",
            known_client_ids=["client-42"],
        ),
    )
    state.append_execution(
        _skill_record(
            "net.client_health",
            scope_type=ScopeType.CLIENT,
            scope_id="client-42",
            status=Status.WARN,
            findings=[_finding("HIGH_PACKET_LOSS")],
        )
    )
    state.append_execution(
        _skill_record(
            "net.dns_latency",
            scope_type=ScopeType.CLIENT,
            scope_id="client-42",
            status=Status.WARN,
            findings=[_finding("HIGH_DNS_LATENCY"), _finding("DNS_TIMEOUT_RATE")],
        )
    )
    state.set_domain_score(
        DiagnosticDomain.DNS_ISSUE,
        score=0.78,
        confidence=Confidence.HIGH,
        supporting_findings=["HIGH_DNS_LATENCY", "DNS_TIMEOUT_RATE"],
    )
    state.set_stop_reason(
        StopReason(
            code=StopReasonCode.HIGH_CONFIDENCE_DIAGNOSIS,
            message="High-confidence diagnosis points to dns_issue with high confidence.",
            related_domains=[DiagnosticDomain.DNS_ISSUE],
            supporting_context={"replay": True},
        )
    )

    def fail_invoke(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("replay mode should not invoke primitive skills")

    monkeypatch.setattr("nettools.orchestrator.diagnose_incident.invoke_skill", fail_invoke)

    result = evaluate_diagnose_incident(
        DiagnoseIncidentInput(replay_state=state, site_id="hq-1"),
        AdapterBundle(),
    )

    report = result.evidence["diagnosis_report"]

    assert result.status is Status.WARN
    assert result.summary == "High-confidence diagnosis points to dns_issue with high confidence."
    assert report["incident_type"] == "single_client"
    assert report["playbook_used"] == "single_client_wifi_issue"
    assert report["ranked_causes"][0]["domain"] == "dns_issue"
    assert report["stop_reason"]["code"] == "high_confidence_diagnosis"
    assert result.evidence["replay_debug"] == {
        "enabled": True,
        "source": "incident_state",
        "replayed_skill_count": 2,
    }
    assert result.evidence["investigation_metrics"] == {
        "playbook_invocations": {"single_client_wifi_issue": 1},
        "stop_reason_counts": {"high_confidence_diagnosis": 1},
        "diagnosis_domains_by_outcome": {"warn": {"dns_issue": 1}},
        "average_skill_count_per_investigation": 2.0,
    }
    assert result.evidence["incident_record"]["incident_id"] == "inc-replay-1"
    assert result.evidence["incident_record"]["site_id"] == "hq-1"


def test_diagnose_incident_replays_from_audit_trail_without_live_execution(
    monkeypatch: Any,
) -> None:
    state = IncidentState(
        incident_id="inc-replay-audit-1",
        incident_type=IncidentType.SINGLE_CLIENT,
        playbook_used="single_client_wifi_issue",
        status=InvestigationStatus.COMPLETED,
        scope_summary=ScopeSummary(
            site_id="hq-1",
            ssid="CorpWiFi",
            known_client_ids=["client-42"],
        ),
    )
    state.append_execution(
        _skill_record(
            "net.client_health",
            scope_type=ScopeType.CLIENT,
            scope_id="client-42",
            status=Status.WARN,
            findings=[_finding("HIGH_PACKET_LOSS")],
        )
    )
    state.append_execution(
        _skill_record(
            "net.dns_latency",
            scope_type=ScopeType.CLIENT,
            scope_id="client-42",
            status=Status.WARN,
            findings=[_finding("HIGH_DNS_LATENCY"), _finding("DNS_TIMEOUT_RATE")],
        )
    )
    state.set_domain_score(
        DiagnosticDomain.DNS_ISSUE,
        score=0.78,
        confidence=Confidence.HIGH,
        supporting_findings=["HIGH_DNS_LATENCY", "DNS_TIMEOUT_RATE"],
    )
    state.append_trace(
        InvestigationTraceEventType.PLAYBOOK_SELECTION,
        "Selected playbook single_client_wifi_issue for single_client.",
        details={"playbook_name": "single_client_wifi_issue"},
    )
    state.set_stop_reason(
        StopReason(
            code=StopReasonCode.HIGH_CONFIDENCE_DIAGNOSIS,
            message="High-confidence diagnosis points to dns_issue with high confidence.",
            related_domains=[DiagnosticDomain.DNS_ISSUE],
            supporting_context={"replay": True},
        )
    )
    audit_trail = DiagnoseIncidentAuditTrail.from_incident_state(
        state,
        incident_record={
            "incident_id": "inc-replay-audit-1",
            "summary": "Replay audit trail",
            "site_id": "hq-1",
            "client_id": "client-42",
        },
    )

    def fail_invoke(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("audit replay mode should not invoke primitive skills")

    monkeypatch.setattr("nettools.orchestrator.diagnose_incident.invoke_skill", fail_invoke)

    result = evaluate_diagnose_incident(
        DiagnoseIncidentInput(replay_audit_trail=audit_trail, site_id="hq-1"),
        AdapterBundle(),
    )

    assert result.evidence["replay_debug"] == {
        "enabled": True,
        "source": "audit_trail",
        "replayed_skill_count": 2,
    }
    assert result.evidence["investigation_metrics"] == {
        "playbook_invocations": {"single_client_wifi_issue": 1},
        "stop_reason_counts": {"high_confidence_diagnosis": 1},
        "diagnosis_domains_by_outcome": {"warn": {"dns_issue": 1}},
        "average_skill_count_per_investigation": 2.0,
    }
    assert result.evidence["audit_trail"]["incident_id"] == "inc-replay-audit-1"
    assert result.evidence["incident_record"]["client_id"] == "client-42"


def test_diagnose_incident_replays_emitted_audit_trail_consistently(
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
                        "incident_id": "inc-replayability-1",
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

    live_result = evaluate_diagnose_incident(
        DiagnoseIncidentInput(
            site_id="hq-1",
            client_id="client-1",
            complaint="My laptop cannot connect to CorpWiFi and reconnect helps",
        ),
        AdapterBundle(),
    )

    emitted_audit_trail = DiagnoseIncidentAuditTrail.model_validate(
        live_result.evidence["audit_trail"]
    )

    def fail_invoke(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("replayed audit trail should not invoke primitive skills")

    monkeypatch.setattr("nettools.orchestrator.diagnose_incident.invoke_skill", fail_invoke)

    replay_result = evaluate_diagnose_incident(
        DiagnoseIncidentInput(replay_audit_trail=emitted_audit_trail, site_id="hq-1"),
        AdapterBundle(),
    )

    assert calls == ["net.incident_intake", "net.auth_8021x_radius"]
    assert replay_result.status is live_result.status
    assert replay_result.summary == live_result.summary
    assert replay_result.confidence is live_result.confidence
    assert replay_result.next_actions == live_result.next_actions
    assert replay_result.raw_refs == live_result.raw_refs
    assert replay_result.evidence["incident_record"] == live_result.evidence["incident_record"]
    assert replay_result.evidence["incident_state"] == live_result.evidence["incident_state"]
    assert replay_result.evidence["diagnosis_report"] == live_result.evidence["diagnosis_report"]
    assert (
        replay_result.evidence["investigation_metrics"]
        == live_result.evidence["investigation_metrics"]
    )
    assert replay_result.evidence["replay_debug"] == {
        "enabled": True,
        "source": "audit_trail",
        "replayed_skill_count": 2,
    }

    live_audit = dict(live_result.evidence["audit_trail"])
    replay_audit = dict(replay_result.evidence["audit_trail"])
    live_persisted_at = live_audit.pop("persisted_at")
    replay_persisted_at = replay_audit.pop("persisted_at")

    assert replay_audit == live_audit
    assert replay_persisted_at >= live_persisted_at


def test_parse_input_loads_replay_state_and_incident_record_files(tmp_path: Any) -> None:
    state = IncidentState(
        incident_id="inc-replay-parse",
        incident_type=IncidentType.SINGLE_CLIENT,
        playbook_used="single_client_wifi_issue",
        scope_summary=ScopeSummary(site_id="hq-1"),
    )
    incident_record = IncidentRecord(
        incident_id="inc-replay-parse",
        summary="Replay me",
        site_id="hq-1",
        client_id="client-88",
    )
    state_path = tmp_path / "state.json"
    record_path = tmp_path / "incident.json"
    state_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
    record_path.write_text(incident_record.model_dump_json(indent=2), encoding="utf-8")

    parser = build_diagnose_incident_parser()
    arguments = parser.parse_args(
        [
            "--replay-state-file",
            str(state_path),
            "--replay-incident-record-file",
            str(record_path),
        ]
    )
    skill_input = _parse_input(arguments)

    assert skill_input.replay_state is not None
    assert skill_input.replay_state.incident_id == "inc-replay-parse"
    assert skill_input.incident_record is not None
    assert skill_input.incident_record.client_id == "client-88"


def test_parse_input_loads_replay_audit_trail_file(tmp_path: Any) -> None:
    state = IncidentState(
        incident_id="inc-replay-audit-parse",
        incident_type=IncidentType.SINGLE_CLIENT,
        playbook_used="single_client_wifi_issue",
        scope_summary=ScopeSummary(site_id="hq-1"),
    )
    audit_trail = DiagnoseIncidentAuditTrail.from_incident_state(
        state,
        incident_record={
            "incident_id": "inc-replay-audit-parse",
            "summary": "Replay audit trail",
            "site_id": "hq-1",
        },
    )
    audit_trail_path = tmp_path / "audit-trail.json"
    audit_trail_path.write_text(audit_trail.model_dump_json(indent=2), encoding="utf-8")

    parser = build_diagnose_incident_parser()
    arguments = parser.parse_args([
        "--replay-audit-trail-file",
        str(audit_trail_path),
    ])
    skill_input = _parse_input(arguments)

    assert skill_input.replay_audit_trail is not None
    assert skill_input.replay_audit_trail.incident_id == "inc-replay-audit-parse"


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


def test_diagnose_incident_policy_disables_active_probes(
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
                incident_id="inc-site-no-probes",
                summary="Everyone on site says the network is slow",
                site_id="hq-1",
                wired_also_affected=True,
            ),
            max_steps=2,
            orchestrator_config=OrchestratorConfig(
                policy_controls=PolicyControlConfig(allow_active_probes=False)
            ),
        ),
        AdapterBundle(),
    )

    report = result.evidence["diagnosis_report"]

    assert calls == ["net.change_detection", "net.stp_loop_anomaly"]
    assert "net.path_probe" not in calls
    assert report["playbook_used"] == "site_wide_internal_slowdown"


def test_diagnose_incident_policy_omits_external_resolver_target(
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
            )
        ],
        "net.path_probe": [
            _skill_record(
                "net.path_probe",
                scope_type=ScopeType.SITE,
                scope_id="hq-1",
            )
        ],
    }
    monkeypatch.setattr(
        "nettools.orchestrator.diagnose_incident.invoke_skill",
        _fake_invoke(records, calls, payloads),
    )

    evaluate_diagnose_incident(
        DiagnoseIncidentInput(
            incident_record=IncidentRecord(
                incident_id="inc-site-no-external",
                summary="Everyone on site says the network is slow",
                site_id="hq-1",
                wired_also_affected=True,
            ),
            path_probe_external_target="1.1.1.1",
            max_steps=2,
            orchestrator_config=OrchestratorConfig(
                policy_controls=PolicyControlConfig(
                    allow_external_resolver_comparisons=False
                )
            ),
        ),
        AdapterBundle(),
    )

    assert calls == ["net.change_detection", "net.path_probe"]
    assert _payload_subset(payloads, "net.path_probe", "external_target") == [{}]


def test_diagnose_incident_policy_disables_optional_expensive_branch(
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
                status=Status.WARN,
                findings=[_finding("SITE_WIDE_PATH_LOSS")],
            )
        ],
        "net.stp_loop_anomaly": [
            _skill_record(
                "net.stp_loop_anomaly",
                scope_type=ScopeType.SITE,
                scope_id="hq-1",
                status=Status.WARN,
                findings=[_finding("TOPOLOGY_CHURN")],
            )
        ],
        "net.incident_correlation": [
            _skill_record(
                "net.incident_correlation",
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
                incident_id="inc-site-expensive-branch",
                summary="Everyone on site says the network is slow",
                site_id="hq-1",
                wired_also_affected=True,
            ),
            max_steps=4,
            orchestrator_config=OrchestratorConfig(
                policy_controls=PolicyControlConfig(
                    allow_optional_expensive_branches=False,
                    expensive_branch_skills=["net.ap_uplink_health"],
                )
            ),
        ),
        AdapterBundle(),
    )

    report = result.evidence["diagnosis_report"]

    assert calls == [
        "net.change_detection",
        "net.path_probe",
        "net.stp_loop_anomaly",
        "net.incident_correlation",
    ]
    assert "net.ap_uplink_health" not in calls
    assert report["playbook_used"] == "site_wide_internal_slowdown"


def test_diagnose_incident_formats_unresolved_report_when_no_runnable_skills_exist(
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
    }
    monkeypatch.setattr(
        "nettools.orchestrator.diagnose_incident.invoke_skill",
        _fake_invoke(records, calls),
    )

    result = evaluate_diagnose_incident(
        DiagnoseIncidentInput(
            incident_record=IncidentRecord(
                incident_id="inc-unresolved-1",
                summary="Everyone on site reports intermittent slowdown",
                site_id="hq-1",
                wired_also_affected=True,
            ),
            max_steps=1,
        ),
        AdapterBundle(),
    )

    report = result.evidence["diagnosis_report"]
    incident_state = result.evidence["incident_state"]

    assert calls == ["net.change_detection"]
    assert result.status is Status.UNKNOWN
    assert result.summary == (
        "Investigation narrowed the issue to unknown with low confidence."
    )
    assert report["incident_type"] == "site_wide"
    assert report["playbook_used"] == "site_wide_internal_slowdown"
    assert report["summary"] == "Investigation narrowed the issue to unknown with low confidence."
    assert report["ranked_causes"][0]["domain"] == "unknown"
    assert report["ranked_causes"][0]["confidence"] == "low"
    assert "single_client_rf" in report["eliminated_domains"]
    assert "unknown" not in report["eliminated_domains"]
    assert report["stop_reason"] == {
        "code": "human_action_required",
        "message": "The requested max_steps limit was reached before the investigation converged.",
    }
    assert report["recommended_followup_skills"] == []
    assert report["recommended_human_actions"] == [
        "Review the strongest remaining evidence for site hq-1.",
    ]
    assert incident_state["status"] == "completed"


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
