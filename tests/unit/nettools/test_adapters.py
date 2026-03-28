from __future__ import annotations

from datetime import datetime, timezone

import pytest

from nettools import DependencyTimeoutError
from nettools.adapters import (
    AdapterContext,
    ProbeRequest,
    ProbeTarget,
    StubAuthAdapter,
    StubDhcpAdapter,
    StubDnsAdapter,
    StubInventoryConfigAdapter,
    StubProbeAdapter,
    StubSwitchAdapter,
    StubSyslogEventAdapter,
    StubWirelessControllerAdapter,
    load_stub_fixture_file,
)
from nettools.models import TimeWindow


def test_adapter_context_validates_positive_timeout() -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        AdapterContext(timeout_seconds=0)


def test_wireless_stub_returns_fixture_backed_models() -> None:
    fixtures = load_stub_fixture_file("tests/fixtures/nettools/adapter_stub_payloads.json")
    adapter = StubWirelessControllerAdapter(fixtures=fixtures)

    session = adapter.get_client_session(client_id="client-123")
    roam_events = adapter.get_roam_events(client_id="client-123")

    assert session is not None
    assert session.client_mac == "aa:bb:cc:dd:ee:ff"
    assert session.retry_pct == 8.5
    assert len(roam_events) == 1
    assert roam_events[0].to_ap_id == "ap-42"


def test_switch_stub_can_raise_timeout_for_selected_operation() -> None:
    fixtures = load_stub_fixture_file("tests/fixtures/nettools/adapter_stub_payloads.json")
    adapter = StubSwitchAdapter(
        fixtures=fixtures,
        timeout_operations={"get_interface_counters"},
    )

    with pytest.raises(DependencyTimeoutError, match="timed out during get_interface_counters"):
        adapter.get_interface_counters(switch_id="sw-core-1", port="Gi1/0/24")


def test_service_stubs_return_normalized_models() -> None:
    fixtures = load_stub_fixture_file("tests/fixtures/nettools/adapter_stub_payloads.json")

    dhcp_adapter = StubDhcpAdapter(fixtures=fixtures)
    dns_adapter = StubDnsAdapter(fixtures=fixtures)
    auth_adapter = StubAuthAdapter(fixtures=fixtures)

    dhcp_summaries = dhcp_adapter.get_dhcp_transaction_summaries(client_id="client-123")
    relay_metadata = dhcp_adapter.get_relay_path_metadata(client_mac="aa:bb:cc:dd:ee:ff")
    dns_summary = dns_adapter.run_dns_probes(queries=["example.com"])
    resolver_results = dns_adapter.compare_resolver_results(resolvers=["10.0.0.53", "10.0.0.54"])
    auth_summary = auth_adapter.get_auth_event_summaries(client_id="client-123")
    auth_failures = auth_adapter.retrieve_categorized_auth_failures(client_id="client-123")

    assert dhcp_summaries[0].avg_ack_latency_ms == 41.8
    assert relay_metadata[0].relay_ip == "10.0.120.1"
    assert dns_summary is not None
    assert dns_summary.overall_avg_latency_ms == 12.3
    assert len(resolver_results) == 2
    assert auth_summary is not None
    assert auth_summary.auth_success_rate_pct == 98.0
    assert auth_failures[0].category == "timeout"


def test_probe_inventory_and_syslog_stubs_support_fixture_path_loading() -> None:
    fixture_path = "tests/fixtures/nettools/adapter_stub_payloads.json"

    probe_adapter = StubProbeAdapter(fixture_path=fixture_path)
    inventory_adapter = StubInventoryConfigAdapter(fixture_path=fixture_path)
    syslog_adapter = StubSyslogEventAdapter(fixture_path=fixture_path)

    probe_results = probe_adapter.run_path_probes(
        request=ProbeRequest(
            source_probe_id="probe-1",
            targets=[ProbeTarget(target="10.0.0.1")],
        )
    )
    policy = inventory_adapter.get_expected_vlan_by_ssid_client_role(
        site_id="site-1",
        ssid="corp-wifi",
        client_role="employee",
    )
    uplink = inventory_adapter.get_expected_ap_uplink_characteristics(ap_id="ap-42")
    changes = inventory_adapter.get_recent_config_changes(device_id="sw-core-1")
    events = syslog_adapter.fetch_events_by_time_window(
        context=AdapterContext(
            time_window=TimeWindow(
                start=datetime(2026, 3, 28, 7, 0, tzinfo=timezone.utc),
                end=datetime(2026, 3, 28, 7, 15, tzinfo=timezone.utc),
            )
        )
    )

    assert probe_results[0].avg_latency_ms == 3.8
    assert policy is not None
    assert policy.expected_vlan == 120
    assert uplink is not None
    assert uplink.expected_port == "Gi1/0/24"
    assert changes[0].change_id == "chg-77"
    assert events[0].summary == "STP topology change detected"