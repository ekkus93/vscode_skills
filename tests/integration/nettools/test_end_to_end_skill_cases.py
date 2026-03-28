from __future__ import annotations

from dataclasses import dataclass

import pytest
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


@dataclass(frozen=True)
class IntegrationScenario:
    name: str
    skill_name: str
    payload: dict[str, object]
    fixtures: dict[str, object]
    expected_status: str
    expected_findings: set[str]
    expected_next_actions: set[str]


SCENARIOS: list[IntegrationScenario] = [
    IntegrationScenario(
        name="weak client RF case",
        skill_name="net.client_health",
        payload={"client_id": "client-1"},
        fixtures={
            "get_client_session": {
                "client_id": "client-1",
                "ap_id": "ap-1",
                "ap_name": "AP-1",
                "rssi_dbm": -81,
                "snr_db": 14,
                "retry_pct": 8.0,
            },
            "get_client_history": [{"client_id": "client-1"}],
            "get_roam_events": [],
            "get_ap_state": {"ap_id": "ap-1", "ap_name": "AP-1"},
            "get_neighboring_ap_data": [{"ap_id": "ap-2", "ap_name": "AP-2"}],
        },
        expected_status="warn",
        expected_findings={"LOW_RSSI", "LOW_SNR", "STICKY_CLIENT"},
        expected_next_actions={"net.ap_rf_health", "net.roaming_analysis"},
    ),
    IntegrationScenario(
        name="overloaded AP case",
        skill_name="net.ap_rf_health",
        payload={"ap_id": "ap-1"},
        fixtures={
            "get_ap_state": {
                "ap_id": "ap-1",
                "ap_name": "AP-1",
                "radio_5g": {
                    "band": "5GHz",
                    "channel": 36,
                    "width_mhz": 80,
                    "utilization_pct": 88.0,
                    "client_count": 37,
                },
            },
            "get_neighboring_ap_data": [
                {"ap_id": "ap-2"},
                {"ap_id": "ap-3"},
                {"ap_id": "ap-4"},
            ],
        },
        expected_status="warn",
        expected_findings={
            "HIGH_CHANNEL_UTILIZATION",
            "HIGH_AP_CLIENT_LOAD",
            "POTENTIAL_CO_CHANNEL_INTERFERENCE",
        },
        expected_next_actions={"net.client_health"},
    ),
    IntegrationScenario(
        name="slow DHCP case",
        skill_name="net.dhcp_path",
        payload={"client_id": "client-1"},
        fixtures={
            "get_dhcp_transaction_summaries": [
                {
                    "client_id": "client-1",
                    "avg_offer_latency_ms": 1800.0,
                    "avg_ack_latency_ms": 200.0,
                }
            ]
        },
        expected_status="warn",
        expected_findings={"HIGH_DHCP_OFFER_LATENCY"},
        expected_next_actions={"net.path_probe"},
    ),
    IntegrationScenario(
        name="slow DNS case",
        skill_name="net.dns_latency",
        payload={"client_id": "client-1"},
        fixtures={
            "retrieve_dns_telemetry": {
                "client_id": "client-1",
                "overall_avg_latency_ms": 340.0,
                "resolver_results": [
                    {
                        "resolver": "10.0.0.53",
                        "avg_latency_ms": 340.0,
                        "timeout_pct": 0.0,
                    }
                ],
            }
        },
        expected_status="warn",
        expected_findings={"HIGH_DNS_LATENCY"},
        expected_next_actions={"net.path_probe"},
    ),
    IntegrationScenario(
        name="auth timeout case",
        skill_name="net.auth_8021x_radius",
        payload={"client_id": "client-1"},
        fixtures={
            "get_auth_event_summaries": {
                "client_id": "client-1",
                "auth_success_rate_pct": 73.0,
                "timeouts": 8,
                "radius_servers": [
                    {
                        "server": "radius-a",
                        "avg_rtt_ms": 3400.0,
                        "reachable": True,
                    }
                ],
            },
            "get_radius_reachability": [
                {"server": "radius-a", "avg_rtt_ms": 3400.0, "reachable": True}
            ],
            "retrieve_categorized_auth_failures": [{"category": "timeout", "count": 8}],
        },
        expected_status="fail",
        expected_findings={"AUTH_TIMEOUTS", "RADIUS_HIGH_RTT", "LOW_AUTH_SUCCESS_RATE"},
        expected_next_actions={"net.path_probe"},
    ),
    IntegrationScenario(
        name="AP uplink issue case",
        skill_name="net.ap_uplink_health",
        payload={"ap_id": "ap-1"},
        fixtures={
            "resolve_ap_to_switch_port": {
                "switch_id": "sw-1",
                "port": "Gi1/0/24",
                "speed_mbps": 1000,
                "crc_errors": 250,
                "input_errors": 120,
            },
            "get_interface_counters": {
                "switch_id": "sw-1",
                "port": "Gi1/0/24",
                "crc_errors": 200,
                "input_errors": 110,
                "output_errors": 10,
            },
        },
        expected_status="fail",
        expected_findings={"UPLINK_ERROR_RATE"},
        expected_next_actions=set(),
    ),
    IntegrationScenario(
        name="STP loop symptom case",
        skill_name="net.stp_loop_anomaly",
        payload={"site_id": "site-1"},
        fixtures={
            "get_topology_change_summaries": [
                {
                    "site_id": "site-1",
                    "topology_changes": 22,
                    "root_bridge_changes": 2,
                    "mac_flap_events": 6,
                    "suspect_ports": ["Gi1/0/11", "Gi1/0/23"],
                }
            ],
            "get_mac_flap_events": [{"mac_address": "00:11:22:33:44:55"}],
        },
        expected_status="fail",
        expected_findings={"TOPOLOGY_CHURN", "ROOT_BRIDGE_CHANGES", "MAC_FLAP_LOOP_SIGNATURE"},
        expected_next_actions=set(),
    ),
    IntegrationScenario(
        name="wrong VLAN case",
        skill_name="net.segmentation_policy",
        payload={"client_id": "client-1"},
        fixtures={
            "get_client_session": {
                "client_id": "client-1",
                "site_id": "hq-1",
                "ssid": "CorpWiFi",
            },
            "get_dhcp_transaction_summaries": [
                {
                    "client_id": "client-1",
                    "site_id": "hq-1",
                    "ssid": "CorpWiFi",
                    "vlan_id": 220,
                    "scope_name": "corp",
                    "relay_ip": "10.0.220.1",
                }
            ],
            "get_expected_policy_mappings": {
                "site_id": "hq-1",
                "ssid": "CorpWiFi",
                "expected_vlan": 120,
                "expected_policy_group": "corp",
                "expected_gateway": "10.0.120.1",
            },
        },
        expected_status="warn",
        expected_findings={"VLAN_MISMATCH", "GATEWAY_ALIGNMENT_MISMATCH"},
        expected_next_actions={"net.auth_8021x_radius", "net.dhcp_path"},
    ),
]


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda scenario: scenario.name)
def test_end_to_end_skill_scenarios_emit_expected_results(
    scenario: IntegrationScenario,
) -> None:
    record = invoke_skill(scenario.skill_name, scenario.payload, build_bundle(scenario.fixtures))

    assert record.error_type is None

    result = SkillResult.model_validate(record.result)
    finding_codes = {finding.code for finding in result.findings}
    next_actions = {action.skill for action in result.next_actions}

    assert result.skill_name == scenario.skill_name
    assert result.status.value == scenario.expected_status
    assert scenario.expected_findings <= finding_codes
    assert scenario.expected_next_actions <= next_actions
    assert record.duration_ms >= 0
    assert record.finished_at >= record.started_at
    assert result.observed_at.tzinfo is not None
    assert result.time_window.start <= result.time_window.end


def test_end_to_end_skill_scenarios_cover_all_phase9_cases() -> None:
    assert {scenario.name for scenario in SCENARIOS} == {
        "weak client RF case",
        "overloaded AP case",
        "slow DHCP case",
        "slow DNS case",
        "auth timeout case",
        "AP uplink issue case",
        "STP loop symptom case",
        "wrong VLAN case",
    }