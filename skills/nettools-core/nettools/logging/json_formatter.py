from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

SENSITIVE_FIELD_NAMES = {
    "api_key",
    "authorization",
    "certificate",
    "cert_pem",
    "key",
    "password",
    "secret",
    "token",
}


def generate_invocation_id() -> str:
    return uuid.uuid4().hex


def redact_sensitive_value(key: str, value: Any) -> Any:
    if key.lower() in SENSITIVE_FIELD_NAMES:
        return "[REDACTED]"

    if isinstance(value, dict):
        return redact_mapping(value)
    if isinstance(value, list):
        return [redact_sensitive_value(key, item) for item in value]
    return value


def redact_mapping(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: redact_sensitive_value(key, value) for key, value in payload.items()}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for key in ("skill_name", "scope_type", "scope_id", "invocation_id"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value

        extra_fields = getattr(record, "fields", None)
        if isinstance(extra_fields, dict):
            payload["fields"] = redact_mapping(extra_fields)

        return json.dumps(payload)


class StructuredLogger:
    def __init__(self, logger: logging.Logger, invocation_id: str) -> None:
        self._logger = logger
        self.invocation_id = invocation_id

    def log(self, level: int, message: str, **fields: Any) -> None:
        redacted_fields = redact_mapping(fields)
        self._logger.log(
            level,
            message,
            extra={
                "invocation_id": self.invocation_id,
                "skill_name": redacted_fields.get("skill_name"),
                "scope_type": redacted_fields.get("scope_type"),
                "scope_id": redacted_fields.get("scope_id"),
                "fields": redacted_fields,
            },
        )

    def info(self, message: str, **fields: Any) -> None:
        self.log(logging.INFO, message, **fields)

    def warning(self, message: str, **fields: Any) -> None:
        self.log(logging.WARNING, message, **fields)

    def error(self, message: str, **fields: Any) -> None:
        self.log(logging.ERROR, message, **fields)


def configure_logging(name: str, invocation_id: str | None = None) -> StructuredLogger:
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)

    level_name = os.environ.get("NETTOOLS_LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, level_name, logging.INFO))
    logger.propagate = False
    return StructuredLogger(logger, invocation_id or generate_invocation_id())
