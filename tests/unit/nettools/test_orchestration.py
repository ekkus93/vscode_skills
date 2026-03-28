from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, cast

import pytest
from nettools.adapters import (
    StubDhcpAdapter,
    StubDnsAdapter,
    StubInventoryConfigAdapter,
    StubSwitchAdapter,
    StubSyslogEventAdapter,
    StubWirelessControllerAdapter,
)
from nettools.models import (
    AccessPointState,
    ClientSession,
    Confidence,
    NextAction,
    ScopeType,
    SkillResult,
    Status,
    SwitchPortState,
    TimeWindow,
)
from nettools.orchestrator import (
    IdentifierResolver,
    SkillExecutionRecord,
    invoke_skill,
    run_single_user_complaint_chain,
    run_site_wide_slowdown_chain,
)
from nettools.priority1 import AdapterBundle


def build_bundle(fixtures: dict[str, object]) -> AdapterBundle:
    return AdapterBundle(
        wireless=StubWirelessControllerAdapter(fixtures=fixtures),
        switch=StubSwitchAdapter(fixtures=fixtures),
        dhcp=StubDhcpAdapter(fixtures=fixtures),
        dns=StubDnsAdapter(fixtures=fixtures),
        inventory=StubInventoryConfigAdapter(fixtures=fixtures),
        syslog=StubSyslogEventAdapter(fixtures=fixtures),
    )


class CountingWirelessAdapter(StubWirelessControllerAdapter):
    def __init__(self, fixtures: dict[str, object]) -> None:
        super().__init__(fixtures=fixtures)
        self.session_calls = 0
        self.ap_calls = 0

    def get_client_session(
        self,
        *,
        client_id: str | None = None,
        client_mac: str | None = None,
        context: Any = None,
    ) -> ClientSession | None:
        self.session_calls += 1
        return cast(
            ClientSession | None,
            super().get_client_session(
                client_id=client_id,
                client_mac=client_mac,
                context=context,
            ),
        )

    def get_ap_state(
        self,
        *,
        ap_id: str | None = None,
        ap_name: str | None = None,
        context: Any = None,
    ) -> AccessPointState | None:
        self.ap_calls += 1
        return cast(
            AccessPointState | None,
            super().get_ap_state(ap_id=ap_id, ap_name=ap_name, context=context),
        )


class CountingSwitchAdapter(StubSwitchAdapter):
    def __init__(self, fixtures: dict[str, object]) -> None:
        super().__init__(fixtures=fixtures)
        self.port_resolution_calls = 0

    def resolve_ap_to_switch_port(
        self,
        *,
        ap_id: str | None = None,
        ap_name: str | None = None,
        context: Any = None,
    ) -> SwitchPortState | None:
        self.port_resolution_calls += 1
        return cast(
            SwitchPortState | None,
            super().resolve_ap_to_switch_port(
                ap_id=ap_id,
                ap_name=ap_name,
                context=context,
            ),
        )


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _record(
    skill_name: str,
    *,
    input_summary: dict[str, Any] | None = None,
    incident_record: dict[str, Any] | None = None,
    next_skills: list[str] | None = None,
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
        next_actions=[
            NextAction(skill=name, reason=f"follow {name}")
            for name in next_skills or []
        ],
        raw_refs=[],
    )
    return SkillExecutionRecord(
        invocation_id=f"inv-{skill_name}",
        skill_name=skill_name,
        started_at=observed_at,
        finished_at=observed_at,
        duration_ms=1,
        input_summary=input_summary or {},
        result=result,
    )


def test_identifier_resolver_caches_client_ap_and_port_lookups() -> None:
    fixtures: dict[str, object] = {
        "get_client_session": {
            "client_id": "client-1",
            "client_mac": "aa:bb:cc:dd:ee:ff",
            "ap_id": "ap-9",
            "ap_name": "AP-9",
            "site_id": "hq-1",
            "ssid": "CorpWiFi",
        },
        "get_ap_state": {"ap_id": "ap-9", "ap_name": "AP-9", "site_id": "hq-1"},
        "resolve_ap_to_switch_port": {
            "switch_id": "sw-1",
            "port": "Gi1/0/24",
            "ap_id": "ap-9",
            "ap_name": "AP-9",
        },
    }
    wireless = CountingWirelessAdapter(fixtures)
    switch = CountingSwitchAdapter(fixtures)
    bundle = AdapterBundle(wireless=wireless, switch=switch)
    resolver = IdentifierResolver()

    first = resolver.resolve_payload({"client_id": "client-1"}, bundle)
    second = resolver.resolve_payload({"client_id": "client-1"}, bundle)

    assert first["client_mac"] == "aa:bb:cc:dd:ee:ff"
    assert first["ap_id"] == "ap-9"
    assert first["switch_port"] == "Gi1/0/24"
    assert second == first
    assert wireless.session_calls == 1
    assert wireless.ap_calls == 1
    assert switch.port_resolution_calls == 1


def test_invoke_skill_returns_success_record() -> None:
    bundle = build_bundle(
        {
            "get_client_session": {
                "client_id": "client-1",
                "client_mac": "aa:bb:cc:dd:ee:ff",
                "ap_id": "ap-1",
                "ap_name": "AP-1",
                "rssi_dbm": -61,
                "snr_db": 31,
                "retry_pct": 3.5,
                "packet_loss_pct": 0.2,
            },
            "get_client_history": [{"client_id": "client-1", "rssi_dbm": -61}],
            "get_roam_events": [],
            "get_ap_state": {"ap_id": "ap-1", "ap_name": "AP-1"},
            "get_neighboring_ap_data": [],
        }
    )

    record = invoke_skill(
        "net.client_health",
        {"client_mac": "aa:bb:cc:dd:ee:ff"},
        bundle,
        resolver=IdentifierResolver(),
    )

    assert record.result.status == Status.OK
    assert record.result.skill_name == "net.client_health"
    assert record.input_summary["client_mac"] == "aa:bb:cc:dd:ee:ff"
    assert record.error_type is None


def test_invoke_skill_normalizes_bad_input() -> None:
    record = invoke_skill("net.client_health", {}, AdapterBundle())

    assert record.result.status == Status.FAIL
    assert record.error_type == "BadInputError"
    assert record.result.skill_name == "net.client_health"


def test_invoke_skill_rejects_unknown_skill() -> None:
    record = invoke_skill("net.unknown_skill", {"site_id": "hq-1"}, AdapterBundle())

    assert record.result.status == Status.FAIL
    assert record.error_type == "BadInputError"
    assert record.result.summary == "Unsupported NETTOOLS skill: net.unknown_skill"


def test_single_user_chain_helper_is_deterministic(monkeypatch: pytest.MonkeyPatch) -> None:
    executed: list[str] = []

    def fake_invoke_skill(
        skill_name: str,
        payload: dict[str, Any],
        adapters: AdapterBundle,
        *,
        resolver: IdentifierResolver | None = None,
        logger: Any = None,
    ) -> SkillExecutionRecord:
        executed.append(skill_name)
        if skill_name == "net.incident_intake":
            return _record(
                skill_name,
                incident_record={"movement_state": "moving", "reconnect_helps": True},
                next_skills=["net.roaming_analysis", "net.ap_rf_health"],
            )
        if skill_name == "net.client_health":
            return _record(skill_name, next_skills=["net.ap_rf_health", "net.dns_latency"])
        return _record(skill_name, next_skills=["net.incident_correlation"])

    monkeypatch.setattr("nettools.orchestrator.chains.invoke_skill", fake_invoke_skill)

    run = run_single_user_complaint_chain(
        {
            "site_id": "hq-1",
            "client_id": "client-1",
            "complaint": "Zoom drops while walking and reconnect helps",
        },
        AdapterBundle(),
        resolver=IdentifierResolver(),
    )

    assert executed == [
        "net.incident_intake",
        "net.client_health",
        "net.roaming_analysis",
        "net.ap_rf_health",
        "net.ap_uplink_health",
        "net.dns_latency",
        "net.dhcp_path",
        "net.incident_correlation",
    ]
    assert run.suggested_next_skills == [
        "net.roaming_analysis",
        "net.ap_rf_health",
        "net.dns_latency",
        "net.incident_correlation",
    ]


def test_site_wide_chain_helper_is_deterministic(monkeypatch: pytest.MonkeyPatch) -> None:
    executed: list[str] = []

    def fake_invoke_skill(
        skill_name: str,
        payload: dict[str, Any],
        adapters: AdapterBundle,
        *,
        resolver: IdentifierResolver | None = None,
        logger: Any = None,
    ) -> SkillExecutionRecord:
        executed.append(skill_name)
        return _record(skill_name, next_skills=["net.incident_correlation", "net.change_detection"])

    monkeypatch.setattr("nettools.orchestrator.chains.invoke_skill", fake_invoke_skill)

    run = run_site_wide_slowdown_chain(
        {"site_id": "hq-1", "complaint": "Users across the site report broad slowdown"},
        AdapterBundle(),
        resolver=IdentifierResolver(),
    )

    assert executed == [
        "net.incident_intake",
        "net.change_detection",
        "net.path_probe",
        "net.stp_loop_anomaly",
        "net.dns_latency",
        "net.dhcp_path",
        "net.incident_correlation",
    ]
    assert run.suggested_next_skills == ["net.incident_correlation", "net.change_detection"]