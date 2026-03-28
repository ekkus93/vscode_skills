from __future__ import annotations

import json
from pathlib import Path

import pytest
from nettools.adapters import (
    StubDhcpAdapter,
    StubDnsAdapter,
    StubInventoryConfigAdapter,
    StubSwitchAdapter,
    StubSyslogEventAdapter,
    StubWirelessControllerAdapter,
)
from nettools.errors import (
    DependencyTimeoutError,
    DependencyUnavailableError,
    InsufficientEvidenceError,
)
from nettools.priority1 import (
    AdapterBundle,
    ApRfHealthInput,
    ApUplinkHealthInput,
    ClientHealthInput,
    DhcpPathInput,
    DnsLatencyInput,
    StpLoopAnomalyInput,
    evaluate_ap_rf_health,
    evaluate_ap_uplink_health,
    evaluate_client_health,
    evaluate_dhcp_path,
    evaluate_dns_latency,
    evaluate_stp_loop_anomaly,
    main_client_health,
)


def build_bundle(
    fixtures: dict[str, object],
    *,
    wireless_timeouts: set[str] | None = None,
    dns_unavailable: set[str] | None = None,
) -> AdapterBundle:
    return AdapterBundle(
        wireless=StubWirelessControllerAdapter(
            fixtures=fixtures, timeout_operations=wireless_timeouts
        ),
        switch=StubSwitchAdapter(fixtures=fixtures),
        dhcp=StubDhcpAdapter(fixtures=fixtures),
        dns=StubDnsAdapter(fixtures=fixtures, unavailable_operations=dns_unavailable),
        inventory=StubInventoryConfigAdapter(fixtures=fixtures),
        syslog=StubSyslogEventAdapter(fixtures=fixtures),
    )


def test_client_health_healthy_client() -> None:
    bundle = build_bundle(
        {
            "get_client_session": {
                "client_id": "client-1",
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

    result = evaluate_client_health(ClientHealthInput(client_id="client-1"), bundle)

    assert result.status.value == "ok"
    assert result.findings == []


def test_client_health_weak_signal() -> None:
    bundle = build_bundle(
        {
            "get_client_session": {
                "client_id": "client-1",
                "ap_id": "ap-1",
                "rssi_dbm": -81,
                "snr_db": 14,
                "retry_pct": 8.0,
            },
            "get_client_history": [{"client_id": "client-1"}],
            "get_roam_events": [],
            "get_ap_state": {"ap_id": "ap-1", "ap_name": "AP-1"},
            "get_neighboring_ap_data": [{"ap_id": "ap-2", "ap_name": "AP-2"}],
        }
    )

    result = evaluate_client_health(ClientHealthInput(client_id="client-1"), bundle)

    assert result.status.value == "warn"
    assert {finding.code for finding in result.findings} >= {"LOW_RSSI", "LOW_SNR", "STICKY_CLIENT"}


def test_client_health_high_retry() -> None:
    bundle = build_bundle(
        {
            "get_client_session": {
                "client_id": "client-1",
                "retry_pct": 28.0,
                "packet_loss_pct": 0.4,
            },
            "get_client_history": [{"client_id": "client-1"}],
            "get_roam_events": [],
        }
    )

    result = evaluate_client_health(ClientHealthInput(client_id="client-1"), bundle)

    assert any(finding.code == "HIGH_RETRY_RATE" for finding in result.findings)
    assert "net.ap_uplink_health" in [action.skill for action in result.next_actions]


def test_client_health_missing_client() -> None:
    with pytest.raises(InsufficientEvidenceError, match="Unable to locate client session"):
        evaluate_client_health(ClientHealthInput(client_id="client-1"), build_bundle({}))


def test_client_health_adapter_timeout() -> None:
    bundle = build_bundle({}, wireless_timeouts={"get_client_session"})
    with pytest.raises(DependencyTimeoutError, match="get_client_session"):
        evaluate_client_health(ClientHealthInput(client_id="client-1"), bundle)


def test_ap_rf_health_healthy_ap() -> None:
    bundle = build_bundle(
        {
            "get_ap_state": {
                "ap_id": "ap-1",
                "ap_name": "AP-1",
                "radio_5g": {
                    "band": "5GHz",
                    "channel": 36,
                    "width_mhz": 40,
                    "utilization_pct": 42.0,
                    "client_count": 11,
                },
            },
            "get_neighboring_ap_data": [{"ap_id": "ap-2"}],
        }
    )
    result = evaluate_ap_rf_health(ApRfHealthInput(ap_id="ap-1"), bundle)
    assert result.status.value == "ok"


def test_ap_rf_health_high_utilization() -> None:
    bundle = build_bundle(
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
            "get_neighboring_ap_data": [{"ap_id": "ap-2"}, {"ap_id": "ap-3"}, {"ap_id": "ap-4"}],
        }
    )
    result = evaluate_ap_rf_health(ApRfHealthInput(ap_id="ap-1"), bundle)
    assert {finding.code for finding in result.findings} >= {
        "HIGH_CHANNEL_UTILIZATION",
        "HIGH_AP_CLIENT_LOAD",
        "POTENTIAL_CO_CHANNEL_INTERFERENCE",
    }


def test_ap_rf_health_radio_reset() -> None:
    bundle = build_bundle(
        {
            "get_ap_state": {
                "ap_id": "ap-1",
                "ap_name": "AP-1",
                "radio_resets_last_24h": 3,
                "radio_5g": {"band": "5GHz", "reset_count": 2},
            },
            "get_neighboring_ap_data": [],
        }
    )
    result = evaluate_ap_rf_health(ApRfHealthInput(ap_id="ap-1"), bundle)
    assert any(finding.code == "RADIO_RESETS" for finding in result.findings)


def test_ap_rf_health_missing_ap() -> None:
    with pytest.raises(InsufficientEvidenceError, match="Unable to locate AP state"):
        evaluate_ap_rf_health(ApRfHealthInput(ap_id="ap-1"), build_bundle({}))


def test_dhcp_path_healthy() -> None:
    bundle = build_bundle(
        {
            "get_dhcp_transaction_summaries": [
                {
                    "client_id": "client-1",
                    "success_rate_pct": 100.0,
                    "avg_offer_latency_ms": 120.0,
                    "avg_ack_latency_ms": 110.0,
                }
            ]
        }
    )
    result = evaluate_dhcp_path(DhcpPathInput(client_id="client-1"), bundle)
    assert result.status.value == "ok"


def test_dhcp_path_slow_offer() -> None:
    bundle = build_bundle(
        {
            "get_dhcp_transaction_summaries": [
                {
                    "client_id": "client-1",
                    "avg_offer_latency_ms": 1800.0,
                    "avg_ack_latency_ms": 200.0,
                }
            ]
        }
    )
    result = evaluate_dhcp_path(DhcpPathInput(client_id="client-1"), bundle)
    assert any(finding.code == "HIGH_DHCP_OFFER_LATENCY" for finding in result.findings)


def test_dhcp_path_missing_ack() -> None:
    bundle = build_bundle(
        {"get_dhcp_transaction_summaries": [{"client_id": "client-1", "missing_acks": 2}]}
    )
    result = evaluate_dhcp_path(DhcpPathInput(client_id="client-1"), bundle)
    assert result.status.value == "fail"
    assert any(finding.code == "MISSING_DHCP_ACK" for finding in result.findings)


def test_dhcp_path_scope_exhaustion_warning() -> None:
    bundle = build_bundle(
        {
            "get_dhcp_transaction_summaries": [
                {"client_id": "client-1", "scope_utilization_pct": 94.0}
            ]
        }
    )
    result = evaluate_dhcp_path(DhcpPathInput(client_id="client-1"), bundle)
    assert any(finding.code == "SCOPE_UTILIZATION_HIGH" for finding in result.findings)


def test_dns_latency_healthy() -> None:
    bundle = build_bundle(
        {
            "retrieve_dns_telemetry": {
                "client_id": "client-1",
                "overall_avg_latency_ms": 18.0,
                "overall_timeout_pct": 0.0,
                "resolver_results": [
                    {"resolver": "10.0.0.53", "avg_latency_ms": 18.0, "timeout_pct": 0.0}
                ],
            }
        }
    )
    result = evaluate_dns_latency(DnsLatencyInput(client_id="client-1"), bundle)
    assert result.status.value == "ok"


def test_dns_latency_slow_dns() -> None:
    bundle = build_bundle(
        {
            "retrieve_dns_telemetry": {
                "client_id": "client-1",
                "overall_avg_latency_ms": 340.0,
                "resolver_results": [
                    {"resolver": "10.0.0.53", "avg_latency_ms": 340.0, "timeout_pct": 0.0}
                ],
            }
        }
    )
    result = evaluate_dns_latency(DnsLatencyInput(client_id="client-1"), bundle)
    assert any(finding.code == "HIGH_DNS_LATENCY" for finding in result.findings)


def test_dns_latency_timeout_heavy() -> None:
    bundle = build_bundle(
        {
            "retrieve_dns_telemetry": {
                "client_id": "client-1",
                "overall_avg_latency_ms": 320.0,
                "overall_timeout_pct": 12.0,
                "resolver_results": [
                    {"resolver": "10.0.0.53", "avg_latency_ms": 320.0, "timeout_pct": 12.0}
                ],
            }
        }
    )
    result = evaluate_dns_latency(DnsLatencyInput(client_id="client-1"), bundle)
    assert result.status.value == "fail"
    assert any(finding.code == "DNS_TIMEOUT_RATE" for finding in result.findings)


def test_dns_latency_resolver_unavailable() -> None:
    bundle = build_bundle({}, dns_unavailable={"retrieve_dns_telemetry", "run_dns_probes"})
    with pytest.raises(DependencyUnavailableError, match="unavailable"):
        evaluate_dns_latency(DnsLatencyInput(client_id="client-1"), bundle)


def test_ap_uplink_health_healthy() -> None:
    bundle = build_bundle(
        {
            "resolve_ap_to_switch_port": {
                "switch_id": "sw-1",
                "port": "Gi1/0/24",
                "speed_mbps": 1000,
                "flaps_last_24h": 0,
                "trunk": True,
                "native_vlan": 120,
            },
            "get_interface_counters": {
                "switch_id": "sw-1",
                "port": "Gi1/0/24",
                "crc_errors": 1,
                "input_errors": 1,
                "output_errors": 0,
            },
            "get_expected_ap_uplink_characteristics": {
                "expected_switch_id": "sw-1",
                "expected_port": "Gi1/0/24",
                "expected_speed_mbps": 1000,
                "expected_trunk": True,
                "expected_native_vlan": 120,
            },
        }
    )
    result = evaluate_ap_uplink_health(ApUplinkHealthInput(ap_id="ap-1"), bundle)
    assert result.status.value == "ok"


def test_ap_uplink_health_100mb_mismatch() -> None:
    bundle = build_bundle(
        {
            "resolve_ap_to_switch_port": {
                "switch_id": "sw-1",
                "port": "Gi1/0/24",
                "speed_mbps": 100,
            },
            "get_expected_ap_uplink_characteristics": {"expected_speed_mbps": 1000},
        }
    )
    result = evaluate_ap_uplink_health(ApUplinkHealthInput(ap_id="ap-1"), bundle)
    assert any(finding.code == "UPLINK_SPEED_MISMATCH" for finding in result.findings)


def test_ap_uplink_health_crc_heavy() -> None:
    bundle = build_bundle(
        {
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
        }
    )
    result = evaluate_ap_uplink_health(ApUplinkHealthInput(ap_id="ap-1"), bundle)
    assert result.status.value == "fail"
    assert any(finding.code == "UPLINK_ERROR_RATE" for finding in result.findings)


def test_ap_uplink_health_flapping() -> None:
    bundle = build_bundle(
        {
            "resolve_ap_to_switch_port": {
                "switch_id": "sw-1",
                "port": "Gi1/0/24",
                "speed_mbps": 1000,
                "flaps_last_24h": 6,
            }
        }
    )
    result = evaluate_ap_uplink_health(ApUplinkHealthInput(ap_id="ap-1"), bundle)
    assert any(finding.code == "UPLINK_FLAPPING" for finding in result.findings)


def test_ap_uplink_health_resolution_failure() -> None:
    with pytest.raises(InsufficientEvidenceError, match="resolve the AP to a switch port"):
        evaluate_ap_uplink_health(ApUplinkHealthInput(ap_id="ap-1"), build_bundle({}))


def test_stp_loop_anomaly_stable_topology() -> None:
    bundle = build_bundle(
        {
            "get_topology_change_summaries": [
                {
                    "site_id": "site-1",
                    "topology_changes": 2,
                    "root_bridge_changes": 0,
                    "mac_flap_events": 0,
                    "suspect_ports": [],
                }
            ],
            "get_mac_flap_events": [],
        }
    )
    result = evaluate_stp_loop_anomaly(StpLoopAnomalyInput(site_id="site-1"), bundle)
    assert result.status.value == "ok"


def test_stp_loop_anomaly_topology_churn_warning() -> None:
    bundle = build_bundle(
        {
            "get_topology_change_summaries": [
                {
                    "site_id": "site-1",
                    "topology_changes": 18,
                    "root_bridge_changes": 1,
                    "mac_flap_events": 2,
                    "suspect_ports": ["Gi1/0/11"],
                }
            ],
            "get_mac_flap_events": [],
        }
    )
    result = evaluate_stp_loop_anomaly(StpLoopAnomalyInput(site_id="site-1"), bundle)
    assert {finding.code for finding in result.findings} >= {
        "TOPOLOGY_CHURN",
        "ROOT_BRIDGE_CHANGES",
    }


def test_stp_loop_anomaly_mac_flap_failure() -> None:
    bundle = build_bundle(
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
        }
    )
    result = evaluate_stp_loop_anomaly(StpLoopAnomalyInput(site_id="site-1"), bundle)
    assert result.status.value == "fail"
    assert any(finding.code == "MAC_FLAP_LOOP_SIGNATURE" for finding in result.findings)


def test_stp_loop_anomaly_missing_switch_data() -> None:
    with pytest.raises(
        InsufficientEvidenceError, match="Unable to locate STP or MAC-flap telemetry"
    ):
        evaluate_stp_loop_anomaly(StpLoopAnomalyInput(site_id="site-1"), build_bundle({}))


def test_priority1_cli_smoke_with_fixture_file(tmp_path: Path) -> None:
    fixture_path = tmp_path / "client.json"
    fixture_path.write_text(
        json.dumps(
            {
                "get_client_session": {"client_id": "client-1", "retry_pct": 4.0},
                "get_client_history": [{"client_id": "client-1"}],
                "get_roam_events": [],
            }
        ),
        encoding="utf-8",
    )

    exit_code = main_client_health(["--client-id", "client-1", "--fixture-file", str(fixture_path)])

    assert exit_code == 0
