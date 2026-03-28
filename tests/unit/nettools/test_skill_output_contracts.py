from __future__ import annotations

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
from nettools.findings import validate_finding_code
from nettools.models import SkillResult
from nettools.orchestrator import SKILL_REGISTRY, IdentifierResolver, invoke_skill
from nettools.orchestrator.diagnose_incident import (
    DiagnoseIncidentInput,
    evaluate_diagnose_incident,
)
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


def assert_skill_result_contract(result: SkillResult) -> None:
    validated = SkillResult.model_validate(result)
    payload = validated.model_dump(mode="json")

    assert payload["observed_at"].endswith("Z")
    assert payload["time_window"]["start"].endswith("Z")
    assert payload["time_window"]["end"].endswith("Z")

    for finding in validated.findings:
        assert validate_finding_code(finding.code) == finding.code

    for action in validated.next_actions:
        assert action.skill in SKILL_REGISTRY


RAW_CONTRACT_CASES: list[tuple[str, dict[str, object], dict[str, object]]] = [
    (
        "net.client_health",
        {"client_id": "client-1"},
        {
            "get_client_session": {
                "client_id": "client-1",
                "ap_id": "ap-1",
                "ap_name": "AP-1",
                "retry_pct": 28.0,
                "packet_loss_pct": 0.4,
            },
            "get_client_history": [{"client_id": "client-1"}],
            "get_roam_events": [],
        },
    ),
    (
        "net.ap_rf_health",
        {"ap_id": "ap-1"},
        {
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
            "get_neighboring_ap_data": [{"ap_id": "ap-2"}, {"ap_id": "ap-3"}],
        },
    ),
    (
        "net.dhcp_path",
        {"client_id": "client-1"},
        {
            "get_dhcp_transaction_summaries": [
                {
                    "client_id": "client-1",
                    "avg_offer_latency_ms": 1800.0,
                    "avg_ack_latency_ms": 200.0,
                }
            ]
        },
    ),
    (
        "net.dns_latency",
        {"client_id": "client-1"},
        {
            "retrieve_dns_telemetry": {
                "client_id": "client-1",
                "overall_avg_latency_ms": 320.0,
                "overall_timeout_pct": 12.0,
                "resolver_results": [
                    {"resolver": "10.0.0.53", "avg_latency_ms": 320.0, "timeout_pct": 12.0}
                ],
            }
        },
    ),
    (
        "net.ap_uplink_health",
        {"ap_id": "ap-1"},
        {
            "resolve_ap_to_switch_port": {
                "switch_id": "sw-1",
                "port": "Gi1/0/24",
                "speed_mbps": 100,
            },
            "get_switch_port_state": {
                "switch_id": "sw-1",
                "port": "Gi1/0/24",
                "speed_mbps": 100,
            },
            "get_interface_counters": {
                "switch_id": "sw-1",
                "port": "Gi1/0/24",
                "crc_errors": 0,
                "input_errors": 0,
                "output_errors": 0,
            },
            "get_expected_ap_uplink_characteristics": {"expected_speed_mbps": 1000},
        },
    ),
    (
        "net.stp_loop_anomaly",
        {"site_id": "site-1"},
        {
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
    ),
    (
        "net.roaming_analysis",
        {"client_id": "client-1"},
        {
            "get_client_session": {"client_id": "client-1", "ap_name": "AP-1", "rssi_dbm": -67},
            "get_client_history": [{"client_id": "client-1", "ap_name": "AP-1"}],
            "get_roam_events": [
                {
                    "client_id": "client-1",
                    "from_ap_name": "AP-1",
                    "to_ap_name": "AP-2",
                    "latency_ms": 410.0,
                    "success": False,
                }
            ],
        },
    ),
    (
        "net.auth_8021x_radius",
        {"client_id": "client-1"},
        {
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
                {
                    "server": "radius-a",
                    "avg_rtt_ms": 3400.0,
                    "reachable": True,
                }
            ],
            "retrieve_categorized_auth_failures": [{"category": "timeout", "count": 8}],
        },
    ),
    (
        "net.path_probe",
        {"site_id": "hq-1", "source_role": "wireless"},
        {
            "run_path_probes": [
                {
                    "target": "default-gateway",
                    "avg_latency_ms": 5.0,
                    "jitter_ms": 1.0,
                    "loss_pct": 0.0,
                },
                {
                    "target": "dns-service",
                    "avg_latency_ms": 240.0,
                    "jitter_ms": 25.0,
                    "loss_pct": 1.0,
                },
                {
                    "target": "radius-service",
                    "avg_latency_ms": 15.0,
                    "jitter_ms": 2.0,
                    "loss_pct": 0.0,
                },
            ]
        },
    ),
    (
        "net.segmentation_policy",
        {"client_id": "client-1"},
        {
            "get_client_session": {"client_id": "client-1", "site_id": "hq-1", "ssid": "CorpWiFi"},
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
    ),
    (
        "net.incident_intake",
        {
            "site_id": "hq-1",
            "complaint": (
                "Users in conference room B say Zoom drops while walking "
                "between APs and wired is fine"
            ),
        },
        {},
    ),
    (
        "net.incident_correlation",
        {
            "site_id": "hq-1",
            "switch_id": "sw-1",
            "incident_summary": "DNS problems started after the switch work",
        },
        {
            "fetch_events_by_time_window": [
                {
                    "event_type": "switch_reload",
                    "severity": "warn",
                    "summary": "Switch reload after maintenance",
                    "site_id": "hq-1",
                    "device_id": "sw-1",
                    "happened_at": "2026-03-28T08:40:00Z",
                }
            ],
            "fetch_auth_dhcp_dns_related_events": [
                {
                    "event_type": "dns_latency",
                    "severity": "warn",
                    "summary": "DNS latency spiked after switch reload",
                    "site_id": "hq-1",
                    "happened_at": "2026-03-28T08:41:00Z",
                }
            ],
            "fetch_ap_controller_events": [],
            "get_recent_config_changes": [
                {
                    "change_id": "chg-1",
                    "category": "hardware",
                    "summary": "Core switch linecard replacement",
                    "site_id": "hq-1",
                    "device_id": "sw-1",
                    "changed_at": "2026-03-28T08:39:00Z",
                    "relevance_score": 0.9,
                }
            ],
        },
    ),
    (
        "net.change_detection",
        {
            "site_id": "hq-1",
            "ap_id": "ap-1",
            "incident_summary": "Problems began after the AP hardware swap",
        },
        {
            "get_recent_config_changes": [
                {
                    "change_id": "chg-2",
                    "category": "hardware",
                    "summary": "AP uplink module replaced",
                    "site_id": "hq-1",
                    "device_id": "ap-1",
                    "changed_at": "2026-03-28T08:42:00Z",
                    "relevance_score": 0.95,
                }
            ],
            "fetch_events_by_time_window": [
                {
                    "event_type": "firmware_reload",
                    "severity": "info",
                    "summary": "Firmware reload completed",
                    "site_id": "hq-1",
                    "device_id": "ap-1",
                    "happened_at": "2026-03-28T08:43:00Z",
                }
            ],
        },
    ),
    (
        "net.capture_trigger",
        {
            "site_id": "hq-1",
            "client_id": "client-1",
            "reason": "Capture DNS failures",
            "authorized": True,
            "approval_ticket": "CHG-1234",
        },
        {},
    ),
]


CONTRACT_CASES = [
    pytest.param(
        skill_name,
        payload,
        fixtures,
        id=skill_name.replace("net.", "").replace("_", "-"),
    )
    for skill_name, payload, fixtures in RAW_CONTRACT_CASES
]


@pytest.mark.parametrize(
    ("skill_name", "payload", "fixtures"),
    CONTRACT_CASES,
)
def test_all_primitive_skills_emit_valid_skill_result_contracts(
    skill_name: str,
    payload: dict[str, object],
    fixtures: dict[str, object],
) -> None:
    record = invoke_skill(
        skill_name,
        payload,
        build_bundle(fixtures),
        resolver=IdentifierResolver(),
    )

    assert record.error_type is None
    assert record.result.skill_name == skill_name
    assert_skill_result_contract(record.result)


def test_diagnose_incident_emits_valid_skill_result_contract() -> None:
    result = evaluate_diagnose_incident(
        DiagnoseIncidentInput(
            site_id="hq-1",
            client_id="client-1",
            complaint="My iPhone cannot connect to SSID CorpWiFi and reconnect helps",
        ),
        build_bundle(
            {
                "get_auth_event_summaries": {
                    "client_id": "client-1",
                    "auth_success_rate_pct": 73.0,
                    "timeouts": 8,
                    "radius_servers": [
                        {"server": "radius-a", "avg_rtt_ms": 3400.0, "reachable": True}
                    ],
                },
                "get_radius_reachability": [
                    {"server": "radius-a", "avg_rtt_ms": 3400.0, "reachable": True}
                ],
                "retrieve_categorized_auth_failures": [{"category": "timeout", "count": 8}],
            }
        ),
    )

    assert result.skill_name == "net.diagnose_incident"
    assert_skill_result_contract(result)
    assert "diagnosis_report" in result.evidence


def test_output_contract_next_actions_only_reference_known_skills() -> None:
    referenced_skills: set[str] = set()

    for skill_name, payload, fixtures in RAW_CONTRACT_CASES:
        record = invoke_skill(
            skill_name,
            payload,
            build_bundle(fixtures),
            resolver=IdentifierResolver(),
        )
        referenced_skills.update(action.skill for action in record.result.next_actions)

    assert referenced_skills
    assert referenced_skills.issubset(set(SKILL_REGISTRY))