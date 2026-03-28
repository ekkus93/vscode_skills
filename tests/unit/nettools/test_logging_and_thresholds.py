from __future__ import annotations

import io
import json
import logging

from nettools.config import default_threshold_config
from nettools.logging import (
    JsonFormatter,
    StructuredLogger,
    generate_invocation_id,
    redact_mapping,
)


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


def test_structured_logger_redacts_nested_sensitive_fields() -> None:
    stream = io.StringIO()
    logger = logging.getLogger(f"nettools.test.logging.redaction.{generate_invocation_id()}")
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    try:
        structured_logger = StructuredLogger(logger, invocation_id="redaction-test")
        structured_logger.info(
            "skill invocation started",
            skill_name="net.capture_trigger",
            scope_type="service",
            scope_id="hq-1",
            inputs={
                "authorization": "Bearer super-secret-token",
                "password": "super-secret-password",
                "site_id": "hq-1",
                "nested": {"api_key": "token-value", "safe": "kept"},
            },
        )
    finally:
        logger.removeHandler(handler)

    rendered = stream.getvalue().strip()
    payload = json.loads(rendered)

    assert payload["fields"]["inputs"]["authorization"] == "[REDACTED]"
    assert payload["fields"]["inputs"]["password"] == "[REDACTED]"
    assert payload["fields"]["inputs"]["nested"]["api_key"] == "[REDACTED]"
    assert payload["fields"]["inputs"]["site_id"] == "hq-1"
    assert payload["fields"]["inputs"]["nested"]["safe"] == "kept"
    assert "super-secret-token" not in rendered
    assert "super-secret-password" not in rendered
    assert "token-value" not in rendered


def test_default_threshold_config_exposes_expected_defaults() -> None:
    config = default_threshold_config()

    assert config.wireless.low_rssi_dbm == -70
    assert config.wireless.high_retry_pct == 15.0
    assert config.service.high_dhcp_latency_ms == 1500
    assert config.wired.high_crc_errors == 100
