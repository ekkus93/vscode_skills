from __future__ import annotations

import json
import logging

from nettools.config import default_threshold_config
from nettools.logging import JsonFormatter, generate_invocation_id, redact_mapping


def test_generate_invocation_id_returns_nonempty_hex_string() -> None:
    invocation_id = generate_invocation_id()

    assert invocation_id
    assert len(invocation_id) == 32


def test_redact_mapping_redacts_sensitive_fields() -> None:
    redacted = redact_mapping(
        {
            "password": "secret-value",
            "api_key": "token-value",
            "safe": "kept",
        }
    )

    assert redacted["password"] == "[REDACTED]"
    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["safe"] == "kept"


def test_json_formatter_includes_standardized_fields() -> None:
    formatter = JsonFormatter()
    record = logging.makeLogRecord(
        {
            "name": "net.client_health",
            "levelno": logging.INFO,
            "levelname": "INFO",
            "msg": "test message",
            "args": (),
            "skill_name": "net.client_health",
            "scope_type": "client",
            "scope_id": "client-123",
            "invocation_id": "abc123",
            "fields": {"password": "secret-value"},
        }
    )

    payload = json.loads(formatter.format(record))

    assert payload["skill_name"] == "net.client_health"
    assert payload["scope_type"] == "client"
    assert payload["scope_id"] == "client-123"
    assert payload["invocation_id"] == "abc123"
    assert payload["fields"]["password"] == "[REDACTED]"


def test_default_threshold_config_exposes_expected_defaults() -> None:
    config = default_threshold_config()

    assert config.wireless.low_rssi_dbm == -70
    assert config.wireless.high_retry_pct == 15.0
    assert config.service.high_dhcp_latency_ms == 1500
    assert config.wired.high_crc_errors == 100
