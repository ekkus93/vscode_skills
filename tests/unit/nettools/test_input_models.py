from __future__ import annotations

from datetime import datetime, timezone

from nettools.models import ScopeType, SharedInputBase


def test_shared_input_defaults_time_window_when_not_provided() -> None:
    shared_input = SharedInputBase(client_id="client-123")

    assert shared_input.start_time is not None
    assert shared_input.end_time is not None
    assert int((shared_input.end_time - shared_input.start_time).total_seconds()) == 15 * 60
    assert shared_input.scope_id == "client-123"
    assert shared_input.default_scope_type() == ScopeType.CLIENT


def test_shared_input_accepts_explicit_time_window() -> None:
    shared_input = SharedInputBase(
        site_id="hq-1",
        start_time=datetime(2026, 3, 28, 6, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 3, 28, 6, 30, tzinfo=timezone.utc),
    )

    assert shared_input.time_window.start == datetime(2026, 3, 28, 6, 0, tzinfo=timezone.utc)
    assert shared_input.time_window.end == datetime(2026, 3, 28, 6, 30, tzinfo=timezone.utc)
    assert shared_input.default_scope_type() == ScopeType.SITE


def test_shared_input_requires_both_explicit_time_bounds() -> None:
    try:
        SharedInputBase(start_time=datetime(2026, 3, 28, 6, 0, tzinfo=timezone.utc))
    except ValueError as exc:
        assert "provided together" in str(exc)
    else:
        raise AssertionError("Expected validation failure when only one time bound is provided")
