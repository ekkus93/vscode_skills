from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
                "+00:00", "Z"
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for key in ("skill_name", "scope_type", "scope_id"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value

        return json.dumps(payload)


def configure_logging(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)

    level_name = os.environ.get("NETTOOLS_LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, level_name, logging.INFO))
    logger.propagate = False
    return logger
