from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest
from nettools.adapters import (
    StubDhcpAdapter,
    StubInventoryConfigAdapter,
    StubSwitchAdapter,
    StubSyslogEventAdapter,
    StubWirelessControllerAdapter,
)
from nettools.errors import InsufficientEvidenceError
from nettools.priority1 import AdapterBundle
from nettools.priority3 import (
    CaptureTriggerInput,
    ChangeDetectionInput,
    IncidentCorrelationInput,
    IncidentIntakeInput,
    configure_incident_intake_parser,
    evaluate_capture_trigger,
    evaluate_change_detection,
    evaluate_incident_correlation,
    evaluate_incident_intake,
    main_capture_trigger,
)


def build_bundle(fixtures: dict[str, object]) -> AdapterBundle:
    return AdapterBundle(
        wireless=StubWirelessControllerAdapter(fixtures=fixtures),
        switch=StubSwitchAdapter(fixtures=fixtures),
        dhcp=StubDhcpAdapter(fixtures=fixtures),
        dns=None,
        auth=None,
        probe=None,
        inventory=StubInventoryConfigAdapter(fixtures=fixtures),
        syslog=StubSyslogEventAdapter(fixtures=fixtures),
    )


def test_incident_intake_common_mobility_complaint() -> None:
    complaint = (
        "Users in conference room B say Zoom drops while walking between APs and wired is fine"
    )
    result = evaluate_incident_intake(
        IncidentIntakeInput(
            site_id="hq-1",
            complaint=complaint,
        ),
        build_bundle({}),
    )

    record = result.evidence["incident_record"]
    assert record["location"].lower() == "conference room b"
    assert record["movement_state"] == "moving"
    assert record["wired_also_affected"] is False
    assert "zoom" in record["impacted_apps"]
    assert "net.roaming_analysis" in [action.skill for action in result.next_actions]


def test_incident_intake_auth_complaint_format() -> None:
    result = evaluate_incident_intake(
        IncidentIntakeInput(
            complaint="My iPhone cannot connect to SSID CorpWiFi and reconnect helps",
        ),
        build_bundle({}),
    )

    record = result.evidence["incident_record"]
    assert record["device_type"] == "iphone"
    assert record["ssid"] == "CorpWiFi"
    assert record["reconnect_helps"] is True
    assert "net.auth_8021x_radius" in [action.skill for action in result.next_actions]


def test_incident_correlation_multi_source() -> None:
    fixtures = {
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
    }

    result = evaluate_incident_correlation(
        IncidentCorrelationInput(
            site_id="hq-1",
            switch_id="sw-1",
            incident_summary="DNS problems started after the switch work",
        ),
        build_bundle(fixtures),
    )

    assert any(finding.code == "CORRELATED_NETWORK_EVIDENCE" for finding in result.findings)
    assert any(finding.code == "CORRELATED_CHANGE_WINDOW" for finding in result.findings)
    assert result.evidence["top_correlated_items"]


def test_change_detection_recent_hardware_change() -> None:
    fixtures = {
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
    }

    result = evaluate_change_detection(
        ChangeDetectionInput(
            site_id="hq-1",
            ap_id="ap-1",
            incident_summary="Problems began after the AP hardware swap",
        ),
        build_bundle(fixtures),
    )

    assert any(finding.code == "RECENT_RELEVANT_CHANGE" for finding in result.findings)
    assert any(finding.code == "RECENT_HARDWARE_OR_FIRMWARE_CHANGE" for finding in result.findings)


def test_change_detection_missing_data() -> None:
    with pytest.raises(
        InsufficientEvidenceError, match="Unable to locate recent infrastructure changes"
    ):
        evaluate_change_detection(ChangeDetectionInput(site_id="hq-1"), build_bundle({}))


def test_capture_trigger_unauthorized() -> None:
    result = evaluate_capture_trigger(
        CaptureTriggerInput(
            site_id="hq-1", reason="Need to inspect DHCP failures during onboarding"
        ),
        build_bundle({}),
    )

    assert result.status.value == "warn"
    assert any(finding.code == "CAPTURE_AUTHORIZATION_REQUIRED" for finding in result.findings)


def test_capture_trigger_authorized() -> None:
    result = evaluate_capture_trigger(
        CaptureTriggerInput(
            site_id="hq-1",
            client_id="client-1",
            reason="Capture DNS failures",
            authorized=True,
            approval_ticket="CHG-1234",
        ),
        build_bundle({}),
    )

    assert result.status.value == "ok"
    plan = result.evidence["capture_plan"]
    assert plan["protocol"] == "dns"
    assert plan["approval_ticket"] == "CHG-1234"


def test_incident_intake_parser_defaults_do_not_mask_inference() -> None:
    parser = argparse.ArgumentParser()
    configure_incident_intake_parser(parser)

    parsed = parser.parse_args(["--complaint", "wired is also affected and reconnect helps"])

    assert parsed.wired_also_affected is None
    assert parsed.reconnect_helps is None


def test_priority3_cli_smoke_with_capture_fixture(tmp_path: Path) -> None:
    fixture_path = tmp_path / "capture.json"
    fixture_path.write_text(json.dumps({}), encoding="utf-8")

    exit_code = main_capture_trigger(
        [
            "--site-id",
            "hq-1",
            "--reason",
            "Capture DNS failures",
            "--authorized",
            "--approval-ticket",
            "CHG-1234",
            "--fixture-file",
            str(fixture_path),
        ]
    )

    assert exit_code == 0
