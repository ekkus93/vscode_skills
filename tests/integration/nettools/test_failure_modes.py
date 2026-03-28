from __future__ import annotations

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


def build_bundle(fixtures: dict[str, object]) -> AdapterBundle:
    return AdapterBundle(
        wireless=StubWirelessControllerAdapter(fixtures=fixtures),
        switch=StubSwitchAdapter(fixtures=fixtures),
        dhcp=StubDhcpAdapter(fixtures=fixtures),
        dns=StubDnsAdapter(fixtures=fixtures),
        auth=StubAuthAdapter(fixtures=fixtures),
        probe=StubProbeAdapter(fixtures=fixtures),
        inventory=StubInventoryConfigAdapter(fixtures=fixtures),
        syslog=StubSyslogEventAdapter(fixtures=fixtures),
    )


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