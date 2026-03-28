from __future__ import annotations

import json
from pathlib import Path

import pytest
from nettools.adapters import (
    StubAuthAdapter,
    StubDhcpAdapter,
    StubInventoryConfigAdapter,
    StubProbeAdapter,
    StubSwitchAdapter,
    StubSyslogEventAdapter,
    StubWirelessControllerAdapter,
)
from nettools.errors import DependencyUnavailableError, InsufficientEvidenceError
from nettools.priority1 import AdapterBundle
from nettools.priority2 import (
    Auth8021xRadiusInput,
    PathProbeInput,
    RoamingAnalysisInput,
    SegmentationPolicyInput,
    evaluate_auth_8021x_radius,
    evaluate_path_probe,
    evaluate_roaming_analysis,
    evaluate_segmentation_policy,
    main_path_probe,
)


def build_bundle(
    fixtures: dict[str, object], *, auth_unavailable: set[str] | None = None
) -> AdapterBundle:
    return AdapterBundle(
        wireless=StubWirelessControllerAdapter(fixtures=fixtures),
        switch=StubSwitchAdapter(fixtures=fixtures),
        dhcp=StubDhcpAdapter(fixtures=fixtures),
        dns=None,
        auth=StubAuthAdapter(fixtures=fixtures, unavailable_operations=auth_unavailable),
        probe=StubProbeAdapter(fixtures=fixtures),
        inventory=StubInventoryConfigAdapter(fixtures=fixtures),
        syslog=StubSyslogEventAdapter(fixtures=fixtures),
    )


def test_roaming_analysis_healthy_roaming() -> None:
    bundle = build_bundle(
        {
            "get_client_session": {"client_id": "client-1", "ap_name": "AP-1", "rssi_dbm": -61},
            "get_client_history": [{"client_id": "client-1", "ap_name": "AP-1"}],
            "get_roam_events": [
                {
                    "client_id": "client-1",
                    "from_ap_name": "AP-1",
                    "to_ap_name": "AP-2",
                    "latency_ms": 90.0,
                    "success": True,
                }
            ],
        }
    )

    result = evaluate_roaming_analysis(RoamingAnalysisInput(client_id="client-1"), bundle)

    assert result.status.value == "ok"
    assert result.findings == []


def test_roaming_analysis_failed_roam() -> None:
    bundle = build_bundle(
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
                },
                {
                    "client_id": "client-1",
                    "from_ap_name": "AP-2",
                    "to_ap_name": "AP-3",
                    "latency_ms": 360.0,
                    "success": False,
                },
            ],
        }
    )

    result = evaluate_roaming_analysis(RoamingAnalysisInput(client_id="client-1"), bundle)

    assert result.status.value == "fail"
    assert {finding.code for finding in result.findings} >= {"FAILED_ROAMS", "HIGH_ROAM_LATENCY"}


def test_roaming_analysis_sticky_client() -> None:
    bundle = build_bundle(
        {
            "get_client_session": {
                "client_id": "client-1",
                "ap_name": "AP-1",
                "rssi_dbm": -78,
                "disconnect_count": 2,
            },
            "get_client_history": [{"client_id": "client-1", "ap_name": "AP-1"}],
            "get_roam_events": [
                {
                    "client_id": "client-1",
                    "from_ap_name": "AP-1",
                    "to_ap_name": "AP-2",
                    "latency_ms": 180.0,
                    "success": True,
                    "sticky_candidate": True,
                }
            ],
        }
    )

    result = evaluate_roaming_analysis(RoamingAnalysisInput(client_id="client-1"), bundle)

    assert any(finding.code == "STICKY_CLIENT_PATTERN" for finding in result.findings)


def test_auth_8021x_radius_healthy() -> None:
    bundle = build_bundle(
        {
            "get_auth_event_summaries": {
                "client_id": "client-1",
                "auth_success_rate_pct": 99.0,
                "timeouts": 0,
                "radius_servers": [{"server": "radius-a", "avg_rtt_ms": 80.0, "reachable": True}],
            },
            "get_radius_reachability": [
                {"server": "radius-a", "avg_rtt_ms": 80.0, "reachable": True}
            ],
            "retrieve_categorized_auth_failures": [],
        }
    )

    result = evaluate_auth_8021x_radius(Auth8021xRadiusInput(client_id="client-1"), bundle)

    assert result.status.value == "ok"


def test_auth_8021x_radius_timeout_heavy() -> None:
    bundle = build_bundle(
        {
            "get_auth_event_summaries": {
                "client_id": "client-1",
                "auth_success_rate_pct": 73.0,
                "timeouts": 8,
                "radius_servers": [{"server": "radius-a", "avg_rtt_ms": 3400.0, "reachable": True}],
            },
            "get_radius_reachability": [
                {"server": "radius-a", "avg_rtt_ms": 3400.0, "reachable": True}
            ],
            "retrieve_categorized_auth_failures": [{"category": "timeout", "count": 8}],
        }
    )

    result = evaluate_auth_8021x_radius(Auth8021xRadiusInput(client_id="client-1"), bundle)

    assert result.status.value == "fail"
    assert {finding.code for finding in result.findings} >= {
        "AUTH_TIMEOUTS",
        "RADIUS_HIGH_RTT",
        "LOW_AUTH_SUCCESS_RATE",
    }
    assert "net.path_probe" in [action.skill for action in result.next_actions]


def test_auth_8021x_radius_credential_failure() -> None:
    bundle = build_bundle(
        {
            "get_auth_event_summaries": {
                "client_id": "client-1",
                "auth_success_rate_pct": 84.0,
                "timeouts": 0,
                "invalid_credentials": 5,
                "radius_servers": [{"server": "radius-a", "avg_rtt_ms": 120.0, "reachable": True}],
            },
            "get_radius_reachability": [
                {"server": "radius-a", "avg_rtt_ms": 120.0, "reachable": True}
            ],
            "retrieve_categorized_auth_failures": [{"category": "invalid_credentials", "count": 5}],
        }
    )

    result = evaluate_auth_8021x_radius(Auth8021xRadiusInput(client_id="client-1"), bundle)

    assert any(finding.code == "AUTH_CREDENTIAL_FAILURES" for finding in result.findings)
    assert "net.segmentation_policy" in [action.skill for action in result.next_actions]


def test_auth_8021x_radius_radius_unreachable() -> None:
    bundle = build_bundle(
        {
            "get_radius_reachability": [{"server": "radius-a", "reachable": False}],
            "retrieve_categorized_auth_failures": [],
        }
    )

    result = evaluate_auth_8021x_radius(Auth8021xRadiusInput(site_id="hq-1"), bundle)

    assert result.status.value == "fail"
    assert any(finding.code == "RADIUS_UNREACHABLE" for finding in result.findings)


def test_auth_8021x_radius_dependency_unavailable() -> None:
    bundle = build_bundle({}, auth_unavailable={"get_auth_event_summaries"})

    with pytest.raises(DependencyUnavailableError, match="unavailable"):
        evaluate_auth_8021x_radius(Auth8021xRadiusInput(client_id="client-1"), bundle)


def test_path_probe_clean_path() -> None:
    bundle = build_bundle(
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
                    "avg_latency_ms": 12.0,
                    "jitter_ms": 2.0,
                    "loss_pct": 0.0,
                },
                {
                    "target": "internet-edge",
                    "avg_latency_ms": 32.0,
                    "jitter_ms": 5.0,
                    "loss_pct": 0.0,
                },
            ]
        }
    )

    result = evaluate_path_probe(
        PathProbeInput(site_id="hq-1", external_target="internet-edge"), bundle
    )

    assert result.status.value == "ok"


def test_path_probe_internal_service_degradation() -> None:
    bundle = build_bundle(
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
        }
    )

    result = evaluate_path_probe(PathProbeInput(site_id="hq-1", source_role="wireless"), bundle)

    assert any(finding.code == "DNS_PATH_DEGRADATION" for finding in result.findings)
    assert "net.dns_latency" in [action.skill for action in result.next_actions]


def test_path_probe_site_wide_loss() -> None:
    bundle = build_bundle(
        {
            "run_path_probes": [
                {
                    "target": "default-gateway",
                    "avg_latency_ms": 180.0,
                    "jitter_ms": 55.0,
                    "loss_pct": 14.0,
                },
                {
                    "target": "dns-service",
                    "avg_latency_ms": 260.0,
                    "jitter_ms": 70.0,
                    "loss_pct": 16.0,
                },
                {
                    "target": "radius-service",
                    "avg_latency_ms": 240.0,
                    "jitter_ms": 60.0,
                    "loss_pct": 12.0,
                },
            ]
        }
    )

    result = evaluate_path_probe(PathProbeInput(site_id="hq-1"), bundle)

    assert result.status.value == "fail"
    assert any(finding.code == "SITE_WIDE_PATH_LOSS" for finding in result.findings)


def test_segmentation_policy_correct_placement() -> None:
    bundle = build_bundle(
        {
            "get_client_session": {"client_id": "client-1", "site_id": "hq-1", "ssid": "CorpWiFi"},
            "get_dhcp_transaction_summaries": [
                {
                    "client_id": "client-1",
                    "site_id": "hq-1",
                    "ssid": "CorpWiFi",
                    "vlan_id": 120,
                    "scope_name": "corp",
                    "relay_ip": "10.0.120.1",
                }
            ],
            "get_expected_policy_mappings": {
                "site_id": "hq-1",
                "ssid": "CorpWiFi",
                "expected_vlan": 120,
                "expected_policy_group": "corp",
                "expected_gateway": "10.0.120.1",
            },
        }
    )

    result = evaluate_segmentation_policy(SegmentationPolicyInput(client_id="client-1"), bundle)

    assert result.status.value == "ok"


def test_segmentation_policy_wrong_vlan() -> None:
    bundle = build_bundle(
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
        }
    )

    result = evaluate_segmentation_policy(SegmentationPolicyInput(client_id="client-1"), bundle)

    assert any(finding.code == "VLAN_MISMATCH" for finding in result.findings)


def test_segmentation_policy_wrong_policy_group() -> None:
    bundle = build_bundle(
        {
            "get_client_session": {"client_id": "client-1", "site_id": "hq-1", "ssid": "CorpWiFi"},
            "get_dhcp_transaction_summaries": [
                {
                    "client_id": "client-1",
                    "site_id": "hq-1",
                    "ssid": "CorpWiFi",
                    "vlan_id": 120,
                    "scope_name": "guest",
                    "relay_ip": "10.0.120.1",
                }
            ],
            "get_expected_policy_mappings": {
                "site_id": "hq-1",
                "ssid": "CorpWiFi",
                "expected_vlan": 120,
                "expected_policy_group": "corp",
                "expected_gateway": "10.0.120.1",
            },
        }
    )

    result = evaluate_segmentation_policy(SegmentationPolicyInput(client_id="client-1"), bundle)

    assert any(finding.code == "POLICY_GROUP_MISMATCH" for finding in result.findings)


def test_segmentation_policy_missing_data() -> None:
    with pytest.raises(
        InsufficientEvidenceError, match="Unable to locate observed or expected segmentation data"
    ):
        evaluate_segmentation_policy(
            SegmentationPolicyInput(client_id="client-1"), build_bundle({})
        )


def test_priority2_cli_smoke_with_fixture_file(tmp_path: Path) -> None:
    fixture_path = tmp_path / "probe.json"
    fixture_path.write_text(
        json.dumps(
            {
                "run_path_probes": [
                    {
                        "target": "dns-service",
                        "avg_latency_ms": 12.0,
                        "jitter_ms": 1.0,
                        "loss_pct": 0.0,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    exit_code = main_path_probe(
        ["--site-id", "hq-1", "--target", "dns-service", "--fixture-file", str(fixture_path)]
    )

    assert exit_code == 0
