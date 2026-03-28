from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any


class TTLCache:
    def __init__(self, *, time_fn: Callable[[], float] | None = None) -> None:
        self._time_fn = time_fn or time.monotonic
        self._entries: dict[str, tuple[float, Any]] = {}

    def set(self, key: str, value: Any, *, ttl_seconds: float) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be greater than zero")
        self._entries[key] = (self._time_fn() + ttl_seconds, value)

    def get(self, key: str) -> Any | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if self._time_fn() >= expires_at:
            self._entries.pop(key, None)
            return None
        return value

    def delete(self, key: str) -> None:
        self._entries.pop(key, None)

    def cleanup(self) -> None:
        now = self._time_fn()
        expired_keys = [key for key, (expires_at, _) in self._entries.items() if now >= expires_at]
        for key in expired_keys:
            self._entries.pop(key, None)


class JsonBaselineStore:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def _read(self) -> dict[str, Any]:
        if not self._path.exists():
            return {}
        payload = json.loads(self._path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Baseline store file must contain a JSON object")
        return payload

    def _write(self, payload: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def set(self, key: str, value: Any) -> None:
        payload = self._read()
        payload[key] = value
        self._write(payload)

    def get(self, key: str) -> Any | None:
        payload = self._read()
        return payload.get(key)
