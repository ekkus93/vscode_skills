from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from nettools.adapters import (
    StubAuthAdapter,
    StubDhcpAdapter,
    StubDnsAdapter,
    StubInventoryConfigAdapter,
    StubProbeAdapter,
    StubSwitchAdapter,
    StubSyslogEventAdapter,
    StubWirelessControllerAdapter,
)
from nettools.models import SkillResult
from nettools.orchestrator import invoke_skill
from nettools.priority1 import AdapterBundle


def build_bundle(
    fixtures: dict[str, object], *, auth_unavailable: set[str] | None = None
) -> AdapterBundle:
    return AdapterBundle(
        wireless=StubWirelessControllerAdapter(fixtures=fixtures),
        switch=StubSwitchAdapter(fixtures=fixtures),
        dhcp=StubDhcpAdapter(fixtures=fixtures),
        dns=StubDnsAdapter(fixtures=fixtures),
        auth=StubAuthAdapter(fixtures=fixtures, unavailable_operations=auth_unavailable),
        probe=StubProbeAdapter(fixtures=fixtures),
        inventory=StubInventoryConfigAdapter(fixtures=fixtures),
        syslog=StubSyslogEventAdapter(fixtures=fixtures),
    )


def load_phase4_scenarios() -> dict[str, dict[str, dict[str, object]]]:
    path = Path("tests/fixtures/nettools/phase4_scenarios.json")
    scenarios: dict[str, dict[str, dict[str, object]]] = json.loads(
        path.read_text(encoding="utf-8")
    )
    return scenarios


def test_partial_client_history_without_current_session_still_returns_skill_result() -> None:
    record = invoke_skill(
        "net.client_health",
        {"client_id": "client-1"},
        build_bundle(
            {
                "get_client_history": [{"client_id": "client-1", "ap_name": "AP-1"}],
                "get_roam_events": [],
                "get_ap_state": {"ap_id": "ap-1", "ap_name": "AP-1"},
                "get_neighboring_ap_data": [],
            }
        ),
    )

    assert record.error_type is None

    result = SkillResult.model_validate(record.result)
    assert result.status.value == "ok"
    assert result.findings == []
    assert result.evidence["connected_ap"] == "AP-1"
    assert result.evidence["recent_roams"] == 0


def test_partial_expected_mapping_without_observed_client_data_still_returns_skill_result() -> None:
    record = invoke_skill(
        "net.segmentation_policy",
        {"client_id": "client-1"},
        build_bundle(
            {
                "get_expected_policy_mappings": {
                    "site_id": "hq-1",
                    "ssid": "CorpWiFi",
                    "expected_vlan": 120,
                    "expected_policy_group": "corp",
                    "expected_gateway": "10.0.120.1",
                }
            }
        ),
    )

    assert record.error_type is None

    result = SkillResult.model_validate(record.result)
    assert result.status.value == "ok"
    assert result.findings == []
    assert result.evidence["expected_policy_mapping"]["expected_vlan"] == 120
    assert result.evidence["expected_policy_mapping"]["expected_policy_group"] == "corp"


def test_dependency_failure_scenario_fixture_yields_dependency_unavailable_result() -> None:
    scenario = load_phase4_scenarios()["dependency_failure_scenario"]
    controls = scenario["controls"]

    record = invoke_skill(
        cast(str, controls["skill_name"]),
        cast(dict[str, object], controls["payload"]),
        build_bundle(
            scenario["stub_fixtures"],
            auth_unavailable=set(cast(list[str], controls["unavailable_operations"])),
        ),
    )

    assert record.error_type == "DependencyUnavailableError"

    result = SkillResult.model_validate(record.result)
    assert result.status.value == "unknown"
    assert result.findings[0].code == "DEPENDENCY_UNAVAILABLE"
    assert result.raw_refs == ["adapter:stub-auth:get_auth_event_summaries"]