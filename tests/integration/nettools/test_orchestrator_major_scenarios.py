from __future__ import annotations

from dataclasses import dataclass, field

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
from nettools.models import Status
from nettools.orchestrator.diagnose_incident import (
    DiagnoseIncidentInput,
    evaluate_diagnose_incident,
)
from nettools.priority1 import AdapterBundle


def build_bundle(
    fixtures: dict[str, object],
    *,
    auth_unavailable: set[str] | None = None,
    syslog_unavailable: set[str] | None = None,
    inventory_unavailable: set[str] | None = None,
) -> AdapterBundle:
    return AdapterBundle(
        wireless=StubWirelessControllerAdapter(fixtures=fixtures),
        switch=StubSwitchAdapter(fixtures=fixtures),
        dhcp=StubDhcpAdapter(fixtures=fixtures),
        dns=StubDnsAdapter(fixtures=fixtures),
        auth=StubAuthAdapter(fixtures=fixtures, unavailable_operations=auth_unavailable),
        probe=StubProbeAdapter(fixtures=fixtures),
        inventory=StubInventoryConfigAdapter(
            fixtures=fixtures,
            unavailable_operations=inventory_unavailable,
        ),
        syslog=StubSyslogEventAdapter(
            fixtures=fixtures,
            unavailable_operations=syslog_unavailable,
        ),
    )


def _low_correlation_change(*, site_id: str) -> list[dict[str, object]]:
    return [
        {
            "change_id": "chg-low-correlation-1",
            "category": "config",
            "summary": "Routine controller configuration sync",
            "site_id": site_id,
            "changed_at": "2026-03-20T00:00:00Z",
        }
    ]


@dataclass(frozen=True)
class OrchestratorIntegrationScenario:
    name: str
    skill_input: DiagnoseIncidentInput
    fixtures: dict[str, object]
    expected_status: Status
    expected_incident_type: str
    expected_playbook: str
    expected_stop_reason: str
    expected_ranked_domains: list[str]
    expected_executed_skills: list[str]
    expected_human_action_fragment: str
    expected_followup_skills: list[str] = field(default_factory=list)
    expected_sampled_aps: list[str] = field(default_factory=list)
    expected_blocked_skill: str | None = None
    auth_unavailable: set[str] | None = None
    syslog_unavailable: set[str] | None = None
    inventory_unavailable: set[str] | None = None


SCENARIOS: list[OrchestratorIntegrationScenario] = [
    OrchestratorIntegrationScenario(
        name="single-client dns scenario",
        skill_input=DiagnoseIncidentInput(
            site_id="hq-1",
            ssid="CorpWiFi",
            client_id="client-42",
            complaint="One laptop keeps timing out on web lookups and general browsing",
        ),
        fixtures={
            "get_client_session": {
                "client_id": "client-42",
                "site_id": "hq-1",
                "ssid": "CorpWiFi",
                "ap_id": "ap-1",
                "ap_name": "AP-1",
                "rssi_dbm": -62,
                "snr_db": 35,
                "retry_pct": 1.0,
                "packet_loss_pct": 3.2,
            },
            "get_client_history": [
                {
                    "client_id": "client-42",
                    "site_id": "hq-1",
                    "ssid": "CorpWiFi",
                    "ap_id": "ap-1",
                    "ap_name": "AP-1",
                }
            ],
            "get_roam_events": [],
            "get_ap_state": {
                "ap_id": "ap-1",
                "ap_name": "AP-1",
                "site_id": "hq-1",
            },
            "get_neighboring_ap_data": [],
            "retrieve_dns_telemetry": {
                "site_id": "hq-1",
                "client_id": "client-42",
                "overall_avg_latency_ms": 340.0,
                "overall_timeout_pct": 12.0,
                "resolver_results": [
                    {
                        "resolver": "10.0.0.53",
                        "avg_latency_ms": 340.0,
                        "timeout_pct": 12.0,
                    }
                ],
            },
        },
        expected_status=Status.WARN,
        expected_incident_type="single_client",
        expected_playbook="single_client_wifi_issue",
        expected_stop_reason="high_confidence_diagnosis",
        expected_ranked_domains=["dns_issue"],
        expected_executed_skills=[
            "net.incident_intake",
            "net.client_health",
            "net.dns_latency",
        ],
        expected_human_action_fragment="Check DNS resolver latency and timeout path",
    ),
    OrchestratorIntegrationScenario(
        name="area-based rf scenario",
        skill_input=DiagnoseIncidentInput(
            site_id="hq-1",
            location="conference room b",
            complaint="Several users in conference room b cannot stay connected",
            candidate_ap_names=["AP-AREA-1"],
        ),
        fixtures={
            "get_ap_state": {
                "ap_id": "ap-area-1",
                "ap_name": "AP-AREA-1",
                "site_id": "hq-1",
                "radio_5g": {
                    "band": "5GHz",
                    "channel": 36,
                    "utilization_pct": 88.0,
                    "client_count": 38,
                },
            },
            "get_neighboring_ap_data": [
                {"ap_id": "ap-area-2"},
                {"ap_id": "ap-area-3"},
                {"ap_id": "ap-area-4"},
            ],
        },
        expected_status=Status.WARN,
        expected_incident_type="single_area",
        expected_playbook="area_based_wifi_issue",
        expected_stop_reason="high_confidence_diagnosis",
        expected_ranked_domains=["single_ap_rf"],
        expected_executed_skills=["net.incident_intake", "net.ap_rf_health"],
        expected_human_action_fragment="Inspect AP radio utilization and interference",
        expected_sampled_aps=["AP-AREA-1"],
    ),
    OrchestratorIntegrationScenario(
        name="site-wide l2 scenario",
        skill_input=DiagnoseIncidentInput(
            site_id="hq-1",
            complaint="All users across the site are slow and wired is affected too",
            wired_also_affected=True,
        ),
        fixtures={
            "get_recent_config_changes": _low_correlation_change(site_id="hq-1"),
            "run_path_probes": [
                {
                    "source_probe_id": "hq-1",
                    "target": "default-gateway",
                    "avg_latency_ms": 210.0,
                    "jitter_ms": 45.0,
                    "loss_pct": 15.0,
                    "timeout_count": 1,
                },
                {
                    "source_probe_id": "hq-1",
                    "target": "dns-service",
                    "avg_latency_ms": 220.0,
                    "jitter_ms": 50.0,
                    "loss_pct": 14.0,
                    "timeout_count": 1,
                },
                {
                    "source_probe_id": "hq-1",
                    "target": "radius-service",
                    "avg_latency_ms": 240.0,
                    "jitter_ms": 55.0,
                    "loss_pct": 16.0,
                    "timeout_count": 1,
                },
            ],
            "get_topology_change_summaries": [
                {
                    "site_id": "hq-1",
                    "switch_id": "sw-core-1",
                    "topology_changes": 22,
                    "root_bridge_changes": 2,
                    "mac_flap_events": 6,
                    "suspect_ports": ["Gi1/0/11", "Gi1/0/23"],
                }
            ],
            "get_mac_flap_events": [],
        },
        expected_status=Status.WARN,
        expected_incident_type="site_wide",
        expected_playbook="site_wide_internal_slowdown",
        expected_stop_reason="high_confidence_diagnosis",
        expected_ranked_domains=["l2_topology_issue", "site_wide_internal_lan_issue"],
        expected_executed_skills=[
            "net.incident_intake",
            "net.change_detection",
            "net.path_probe",
            "net.stp_loop_anomaly",
        ],
        expected_human_action_fragment="Inspect STP topology changes and MAC flap activity",
    ),
    OrchestratorIntegrationScenario(
        name="auth onboarding scenario",
        skill_input=DiagnoseIncidentInput(
            site_id="hq-1",
            ssid="CorpWiFi",
            client_id="client-auth-1",
            complaint="My laptop cannot connect to CorpWiFi and reconnect helps",
        ),
        fixtures={
            "get_auth_event_summaries": {
                "client_id": "client-auth-1",
                "site_id": "hq-1",
                "ssid": "CorpWiFi",
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
            "retrieve_categorized_auth_failures": [],
        },
        expected_status=Status.WARN,
        expected_incident_type="auth_or_onboarding",
        expected_playbook="auth_or_onboarding_issue",
        expected_stop_reason="high_confidence_diagnosis",
        expected_ranked_domains=["auth_issue"],
        expected_executed_skills=["net.incident_intake", "net.auth_8021x_radius"],
        expected_human_action_fragment="Check 802.1X and RADIUS authentication failures",
    ),
    OrchestratorIntegrationScenario(
        name="bounded ambiguity scenario",
        skill_input=DiagnoseIncidentInput(
            site_id="hq-1",
            ssid="CorpWiFi",
            complaint="Cannot connect sometimes and onboarding fails intermittently",
        ),
        fixtures={
            "get_auth_event_summaries": {
                "site_id": "hq-1",
                "ssid": "CorpWiFi",
                "auth_success_rate_pct": 78.0,
                "timeouts": 6,
                "radius_servers": [
                    {"server": "radius-a", "avg_rtt_ms": 120.0, "reachable": True}
                ],
            },
            "get_radius_reachability": [
                {"server": "radius-a", "avg_rtt_ms": 120.0, "reachable": True}
            ],
            "retrieve_categorized_auth_failures": [],
            "get_dhcp_transaction_summaries": [
                {
                    "site_id": "hq-1",
                    "ssid": "CorpWiFi",
                    "avg_offer_latency_ms": 1700.0,
                    "avg_ack_latency_ms": 1550.0,
                    "success_rate_pct": 86.0,
                    "timeouts": 2,
                }
            ],
            "get_scope_utilization": [],
            "get_relay_path_metadata": [],
            "retrieve_dns_telemetry": {
                "site_id": "hq-1",
                "overall_avg_latency_ms": 18.0,
                "overall_timeout_pct": 0.0,
                "resolver_results": [
                    {"resolver": "10.0.0.53", "avg_latency_ms": 18.0, "timeout_pct": 0.0}
                ],
            },
            "get_recent_config_changes": _low_correlation_change(site_id="hq-1"),
        },
        expected_status=Status.WARN,
        expected_incident_type="auth_or_onboarding",
        expected_playbook="auth_or_onboarding_issue",
        expected_stop_reason="two_domain_bounded_ambiguity",
        expected_ranked_domains=["auth_issue", "dhcp_issue"],
        expected_executed_skills=[
            "net.incident_intake",
            "net.auth_8021x_radius",
            "net.dhcp_path",
            "net.dns_latency",
            "net.incident_correlation",
        ],
        expected_human_action_fragment=(
            "Collect one discriminator between auth_issue and dhcp_issue"
        ),
    ),
    OrchestratorIntegrationScenario(
        name="blocked dependency scenario",
        skill_input=DiagnoseIncidentInput(
            site_id="hq-1",
            ssid="CorpWiFi",
            complaint="Cannot connect sometimes and reconnect helps",
        ),
        fixtures={
            "get_auth_event_summaries": {
                "site_id": "hq-1",
                "ssid": "CorpWiFi",
                "auth_success_rate_pct": 78.0,
                "timeouts": 6,
                "radius_servers": [
                    {"server": "radius-a", "avg_rtt_ms": 120.0, "reachable": True}
                ],
            },
            "get_radius_reachability": [
                {"server": "radius-a", "avg_rtt_ms": 120.0, "reachable": True}
            ],
            "retrieve_categorized_auth_failures": [],
            "get_dhcp_transaction_summaries": [],
            "get_scope_utilization": [
                {
                    "site_id": "hq-1",
                    "ssid": "CorpWiFi",
                    "scope_name": "corp",
                    "scope_utilization_pct": 95.0,
                }
            ],
            "get_relay_path_metadata": [],
            "retrieve_dns_telemetry": {
                "site_id": "hq-1",
                "overall_avg_latency_ms": 320.0,
                "overall_timeout_pct": 12.0,
                "resolver_results": [
                    {
                        "resolver": "10.0.0.53",
                        "avg_latency_ms": 320.0,
                        "timeout_pct": 12.0,
                    }
                ],
            },
        },
        expected_status=Status.FAIL,
        expected_incident_type="auth_or_onboarding",
        expected_playbook="auth_or_onboarding_issue",
        expected_stop_reason="dependency_blocked",
        expected_ranked_domains=["dns_issue", "auth_issue"],
        expected_executed_skills=[
            "net.incident_intake",
            "net.auth_8021x_radius",
            "net.dhcp_path",
            "net.dns_latency",
            "net.incident_correlation",
        ],
        expected_human_action_fragment=(
            "Restore or bypass the dependency behind net.incident_correlation"
        ),
        expected_blocked_skill="net.incident_correlation",
        syslog_unavailable={"fetch_events_by_time_window"},
    ),
]


def test_orchestrator_integration_scenarios_cover_all_major_paths() -> None:
    assert {scenario.name for scenario in SCENARIOS} == {
        "single-client dns scenario",
        "area-based rf scenario",
        "site-wide l2 scenario",
        "auth onboarding scenario",
        "bounded ambiguity scenario",
        "blocked dependency scenario",
    }


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda scenario: scenario.name)
def test_orchestrator_major_scenarios_run_with_live_stubbed_skills(
    scenario: OrchestratorIntegrationScenario,
) -> None:
    result = evaluate_diagnose_incident(
        scenario.skill_input,
        build_bundle(
            scenario.fixtures,
            auth_unavailable=scenario.auth_unavailable,
            syslog_unavailable=scenario.syslog_unavailable,
            inventory_unavailable=scenario.inventory_unavailable,
        ),
    )

    report = result.evidence["diagnosis_report"]
    audit_trail = result.evidence["audit_trail"]
    incident_state = result.evidence["incident_state"]
    executed_skills = [entry["skill_name"] for entry in audit_trail["execution_records"]]
    ranked_domains = [
        cause["domain"]
        for cause in report["ranked_causes"][: len(scenario.expected_ranked_domains)]
    ]

    assert result.status is scenario.expected_status
    assert report["incident_type"] == scenario.expected_incident_type
    assert report["playbook_used"] == scenario.expected_playbook
    assert report["stop_reason"]["code"] == scenario.expected_stop_reason
    assert ranked_domains == scenario.expected_ranked_domains
    assert executed_skills == scenario.expected_executed_skills
    assert report["recommended_followup_skills"] == scenario.expected_followup_skills
    assert scenario.expected_human_action_fragment in report["recommended_human_actions"][0]
    assert audit_trail["incident_id"] == incident_state["incident_id"]
    assert result.evidence["investigation_metrics"]["playbook_invocations"] == {
        scenario.expected_playbook: 1
    }

    if scenario.expected_sampled_aps:
        assert set(scenario.expected_sampled_aps) <= set(report["sampling_summary"]["sampled_aps"])

    if scenario.expected_blocked_skill is not None:
        assert (
            report["dependency_failures"][0]["skill_name"]
            == scenario.expected_blocked_skill
        )