from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from nettools.analysis import (
    JsonBaselineStore,
    TTLCache,
    aggregate_evidence,
    build_next_actions,
    compare_to_baseline,
    compare_to_threshold,
    confidence_from_evidence,
    event_correlation_score,
    normalize_access_point_state,
    normalize_auth_summary,
    normalize_client_session,
    normalize_dhcp_summary,
    normalize_dns_summary,
    normalize_segmentation_summary,
    normalize_stp_summary,
    normalize_switch_port_state,
    rank_suspected_causes,
    severity_from_comparisons,
    time_window_overlap_ratio,
)
from nettools.analysis.common import SuspectedCause
from nettools.models import Confidence, FindingSeverity, TimeWindow


def load_phase4_scenarios() -> dict[str, dict[str, dict[str, object]]]:
    path = Path("tests/fixtures/nettools/phase4_scenarios.json")
    scenarios: dict[str, dict[str, dict[str, object]]] = json.loads(
        path.read_text(encoding="utf-8")
    )
    return scenarios


def test_phase4_scenarios_cover_phase16_canonical_fixture_inventory() -> None:
    scenarios = load_phase4_scenarios()

    assert {
        "weak_signal_client",
        "overloaded_ap",
        "dhcp_slowness",
        "dns_slowness",
        "auth_timeout",
        "bad_ap_uplink",
        "stp_loop_symptoms",
        "wrong_vlan_policy",
        "mixed_evidence_two_domain_ambiguity",
        "dependency_failure_scenario",
    } <= set(scenarios)


def test_normalization_helpers_preserve_source_metadata_and_aliases() -> None:
    scenarios = load_phase4_scenarios()
    observed_at = datetime(2026, 3, 28, 8, 0, tzinfo=timezone.utc)

    client = normalize_client_session(
        scenarios["weak_signal_client"]["wireless"],
        provider="stub-wireless",
        raw_ref="fixture:weak_signal_client",
        collected_at=observed_at,
    )
    ap = normalize_access_point_state(
        scenarios["overloaded_ap"]["wireless"],
        provider="stub-wireless",
        raw_ref="fixture:overloaded_ap",
        collected_at=observed_at,
    )
    dhcp = normalize_dhcp_summary(
        scenarios["dhcp_slowness"]["dhcp"],
        provider="stub-dhcp",
        raw_ref="fixture:dhcp_slowness",
        collected_at=observed_at,
    )
    dns = normalize_dns_summary(
        scenarios["dns_slowness"]["dns"],
        provider="stub-dns",
        raw_ref="fixture:dns_slowness",
        collected_at=observed_at,
    )
    auth = normalize_auth_summary(
        scenarios["auth_timeout"]["auth"],
        provider="stub-auth",
        raw_ref="fixture:auth_timeout",
        collected_at=observed_at,
    )
    switch = normalize_switch_port_state(
        scenarios["bad_ap_uplink"]["switch"],
        provider="stub-switch",
        raw_ref="fixture:bad_ap_uplink",
        collected_at=observed_at,
    )
    stp = normalize_stp_summary(
        scenarios["stp_loop_symptoms"]["stp"],
        provider="stub-switch",
        raw_ref="fixture:stp_loop_symptoms",
        collected_at=observed_at,
    )
    segmentation = normalize_segmentation_summary(
        scenarios["wrong_vlan_policy"]["segmentation"],
        provider="stub-inventory",
        raw_ref="fixture:wrong_vlan_policy",
        collected_at=observed_at,
    )

    assert client.client_mac == "00:11:22:33:44:55"
    assert client.source_metadata[0].raw_ref == "fixture:weak_signal_client"
    assert ap.ap_id == "ap-77"
    assert dhcp.avg_offer_latency_ms == 2100
    assert dns.overall_avg_latency_ms == 320.0
    assert auth.auth_success_rate_pct == 71.0
    assert switch.speed_mbps == 100
    assert stp.topology_changes == 27
    assert segmentation.expected_vlan == 120


def test_threshold_scoring_and_recommendation_helpers() -> None:
    comparisons = [
        compare_to_threshold("retry_pct", 24.5, 15.0, direction="gte"),
        compare_to_threshold("rssi_dbm", -81.0, -70.0, direction="lte"),
        compare_to_threshold("dns_latency_ms", 320.0, 250.0, direction="gte"),
    ]
    baseline = compare_to_baseline("dns_latency_ms", 320.0, 18.0)
    actions = build_next_actions(
        [
            ("net.ap_rf_health", "RF indicators are degraded.", True),
            ("net.path_probe", "DNS latency is elevated versus baseline.", True),
            ("net.path_probe", "Duplicate should be dropped.", True),
        ]
    )

    assert comparisons[0].breached is True
    assert baseline.regression is True
    assert severity_from_comparisons(comparisons) == FindingSeverity.CRITICAL
    assert (
        confidence_from_evidence(evidence_count=3, source_count=2, baseline_present=True)
        == Confidence.HIGH
    )
    assert [action.skill for action in actions] == ["net.ap_rf_health", "net.path_probe"]


def test_mixed_evidence_fixture_preserves_two_domain_ambiguity_inputs() -> None:
    scenarios = load_phase4_scenarios()
    observed_at = datetime(2026, 3, 28, 8, 30, tzinfo=timezone.utc)
    scenario = scenarios["mixed_evidence_two_domain_ambiguity"]

    auth = normalize_auth_summary(
        scenario["auth"],
        provider="stub-auth",
        raw_ref="fixture:mixed_evidence_two_domain_ambiguity:auth",
        collected_at=observed_at,
    )
    dhcp = normalize_dhcp_summary(
        scenario["dhcp"],
        provider="stub-dhcp",
        raw_ref="fixture:mixed_evidence_two_domain_ambiguity:dhcp",
        collected_at=observed_at,
    )
    dns = normalize_dns_summary(
        scenario["dns"],
        provider="stub-dns",
        raw_ref="fixture:mixed_evidence_two_domain_ambiguity:dns",
        collected_at=observed_at,
    )

    assert scenario["incident"]["siteId"] == "hq-1"
    assert scenario["incident"]["ssid"] == "CorpWiFi"
    assert auth.auth_success_rate_pct == 78.0
    assert auth.timeouts == 6
    assert dhcp.avg_offer_latency_ms == 1700
    assert dhcp.avg_ack_latency_ms == 1550
    assert dns.overall_avg_latency_ms == 18.0


def test_threshold_helpers_treat_equal_boundary_as_breached() -> None:
    gte_boundary = compare_to_threshold(
        "dns_latency_ms",
        250.0,
        250.0,
        direction="gte",
    )
    lte_boundary = compare_to_threshold(
        "rssi_dbm",
        -70.0,
        -70.0,
        direction="lte",
    )

    assert gte_boundary.breached is True
    assert lte_boundary.breached is True


def test_correlation_and_cache_helpers() -> None:
    first_window = TimeWindow(
        start=datetime(2026, 3, 28, 8, 0, tzinfo=timezone.utc),
        end=datetime(2026, 3, 28, 8, 15, tzinfo=timezone.utc),
    )
    second_window = TimeWindow(
        start=datetime(2026, 3, 28, 8, 10, tzinfo=timezone.utc),
        end=datetime(2026, 3, 28, 8, 25, tzinfo=timezone.utc),
    )

    overlap_ratio = time_window_overlap_ratio(first_window, second_window)
    score = event_correlation_score(
        first_window=first_window,
        second_window=second_window,
        shared_scope=True,
        shared_sources=2,
    )
    evidence = aggregate_evidence(
        [
            {"site_id": "site-1", "symptom": "slow_dns"},
            {"site_id": "site-1", "symptom": "slow_dhcp"},
        ]
    )
    ranked = rank_suspected_causes(
        [
            SuspectedCause(code="DNS_SLOW", score=0.7, reason="Resolver RTT elevated."),
            SuspectedCause(code="AP_OVERLOADED", score=0.9, reason="Utilization is high."),
        ]
    )

    clock = {"value": 10.0}
    cache = TTLCache(time_fn=lambda: clock["value"])
    cache.set("dns", {"latency": 320.0}, ttl_seconds=5.0)
    before_expiry = cache.get("dns")
    clock["value"] = 16.0
    after_expiry = cache.get("dns")

    store_path = Path("tests/fixtures/nettools/.tmp-phase4-baseline.json")
    try:
        store = JsonBaselineStore(store_path)
        store.set("dns_latency_ms", {"baseline": 18.0})
        baseline_entry = store.get("dns_latency_ms")
    finally:
        if store_path.exists():
            store_path.unlink()

    assert 0 < overlap_ratio < 1
    assert score > 0.5
    assert evidence["site_id"] == ["site-1"]
    assert [cause.code for cause in ranked] == ["AP_OVERLOADED", "DNS_SLOW"]
    assert before_expiry == {"latency": 320.0}
    assert after_expiry is None
    assert baseline_entry == {"baseline": 18.0}
