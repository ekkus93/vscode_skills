from __future__ import annotations

from datetime import datetime, timezone

from nettools.models import (
    AccessPointState,
    AuthSummary,
    ChangeRecord,
    ClientSession,
    DhcpSummary,
    DnsSummary,
    IncidentRecord,
    MacFlapEvent,
    PathProbeResult,
    RadioState,
    RoamEvent,
    SegmentationSummary,
    SourceMetadata,
    StpSummary,
    SwitchPortState,
)


def test_phase2_models_accept_partial_data() -> None:
    models = [
        ClientSession(client_id="client-123"),
        AccessPointState(ap_name="AP-1"),
        RadioState(band="5GHz"),
        RoamEvent(client_mac="aa:bb:cc:dd:ee:ff"),
        SwitchPortState(port="Gi1/0/18"),
        StpSummary(site_id="hq-1"),
        MacFlapEvent(mac_address="aa:bb:cc:dd:ee:ff"),
        DhcpSummary(site_id="hq-1"),
        DnsSummary(site_id="hq-1"),
        AuthSummary(site_id="hq-1"),
        SegmentationSummary(client_id="client-123"),
        PathProbeResult(target="10.10.0.1"),
        IncidentRecord(summary="Wi-Fi slow near east wing"),
        ChangeRecord(summary="AP firmware change"),
    ]

    assert all(model.model_version == "1.0" for model in models)


def test_phase2_models_include_source_metadata_and_serialize_cleanly() -> None:
    source = SourceMetadata(
        provider="wireless-controller",
        source_type="api",
        source_id="client/123",
        collected_at=datetime(2026, 3, 28, 7, 0, tzinfo=timezone.utc),
        raw_ref="controller:client/123",
    )
    session = ClientSession(
        client_id="client-123",
        observed_at=datetime(2026, 3, 28, 7, 0, tzinfo=timezone.utc),
        source_metadata=[source],
        rssi_dbm=-67,
    )

    payload = session.model_dump(mode="json")

    assert payload["model_version"] == "1.0"
    assert payload["source_metadata"][0]["provider"] == "wireless-controller"
    assert payload["observed_at"] == "2026-03-28T07:00:00Z"


def test_phase2_nested_models_serialize_as_expected() -> None:
    ap_state = AccessPointState(
        ap_name="AP-2F-EAST-03",
        radio_5g=RadioState(channel=36, width_mhz=80, utilization_pct=76.0, client_count=31),
    )

    payload = ap_state.model_dump(mode="json")

    assert payload["radio_5g"]["channel"] == 36
    assert payload["radio_5g"]["client_count"] == 31
