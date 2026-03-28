from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from ..analysis import TTLCache
from ..models import SharedInputBase
from ..priority1 import AdapterBundle, build_adapter_context

CLIENT_FIELDS = ("client_id", "client_mac", "ap_id", "ap_name", "site_id", "ssid")
AP_FIELDS = ("ap_id", "ap_name", "site_id")
PORT_FIELDS = ("switch_id", "switch_port", "ap_id", "ap_name")


def _shared_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if key in SharedInputBase.model_fields and value is not None
    }


def _cache_first(cache: TTLCache, keys: list[str]) -> dict[str, Any] | None:
    for key in keys:
        cached = cache.get(key)
        if isinstance(cached, dict):
            return dict(cached)
    return None


def _set_aliases(
    cache: TTLCache,
    keys: list[str],
    value: dict[str, Any],
    ttl_seconds: float,
) -> None:
    filtered_value = {key: item for key, item in value.items() if item is not None}
    for key in keys:
        cache.set(key, dict(filtered_value), ttl_seconds=ttl_seconds)


def _merge_missing(target: dict[str, Any], additions: Mapping[str, Any]) -> None:
    for key, value in additions.items():
        if value is None:
            continue
        if target.get(key) is None:
            target[key] = value


class IdentifierResolver:
    def __init__(self, *, cache: TTLCache | None = None, ttl_seconds: float = 300.0) -> None:
        self._cache = cache or TTLCache()
        self._ttl_seconds = ttl_seconds

    def _build_context(self, payload: Mapping[str, Any]) -> Any:
        try:
            return build_adapter_context(SharedInputBase.model_validate(_shared_payload(payload)))
        except ValidationError:
            return build_adapter_context(SharedInputBase())

    def resolve_payload(
        self, payload: Mapping[str, Any], adapters: AdapterBundle
    ) -> dict[str, Any]:
        resolved = {key: value for key, value in payload.items() if value is not None}
        context = self._build_context(resolved)

        self._resolve_client(resolved, adapters, context)
        self._resolve_ap(resolved, adapters, context)
        self._resolve_port(resolved, adapters, context)
        return resolved

    def _resolve_client(
        self,
        payload: dict[str, Any],
        adapters: AdapterBundle,
        context: Any,
    ) -> None:
        if adapters.wireless is None:
            return
        client_id = payload.get("client_id")
        client_mac = payload.get("client_mac")
        if not (client_id or client_mac):
            return

        cache_keys = []
        if client_id:
            cache_keys.append(f"client_id:{client_id}")
        if client_mac:
            cache_keys.append(f"client_mac:{client_mac}")

        cached = _cache_first(self._cache, cache_keys)
        if cached is not None:
            _merge_missing(payload, cached)
            return

        session = adapters.wireless.get_client_session(
            client_id=client_id, client_mac=client_mac, context=context
        )
        if session is None:
            history = adapters.wireless.get_client_history(
                client_id=client_id, client_mac=client_mac, context=context
            )
            session = history[0] if history else None
        if session is None:
            return

        resolved = {
            field: getattr(session, field)
            for field in CLIENT_FIELDS
            if getattr(session, field) is not None
        }
        if not resolved:
            return

        alias_keys = list(cache_keys)
        if resolved.get("client_id"):
            alias_keys.append(f"client_id:{resolved['client_id']}")
        if resolved.get("client_mac"):
            alias_keys.append(f"client_mac:{resolved['client_mac']}")
        _set_aliases(self._cache, alias_keys, resolved, self._ttl_seconds)
        _merge_missing(payload, resolved)

    def _resolve_ap(self, payload: dict[str, Any], adapters: AdapterBundle, context: Any) -> None:
        if adapters.wireless is None:
            return
        ap_id = payload.get("ap_id")
        ap_name = payload.get("ap_name")
        if not (ap_id or ap_name):
            return

        cache_keys = []
        if ap_id:
            cache_keys.append(f"ap_id:{ap_id}")
        if ap_name:
            cache_keys.append(f"ap_name:{ap_name}")

        cached = _cache_first(self._cache, cache_keys)
        if cached is not None:
            _merge_missing(payload, cached)
            return

        ap_state = adapters.wireless.get_ap_state(ap_id=ap_id, ap_name=ap_name, context=context)
        if ap_state is None:
            return

        resolved = {
            field: getattr(ap_state, field)
            for field in AP_FIELDS
            if getattr(ap_state, field) is not None
        }
        if not resolved:
            return

        alias_keys = list(cache_keys)
        if resolved.get("ap_id"):
            alias_keys.append(f"ap_id:{resolved['ap_id']}")
        if resolved.get("ap_name"):
            alias_keys.append(f"ap_name:{resolved['ap_name']}")
        _set_aliases(self._cache, alias_keys, resolved, self._ttl_seconds)
        _merge_missing(payload, resolved)

    def _resolve_port(self, payload: dict[str, Any], adapters: AdapterBundle, context: Any) -> None:
        if adapters.switch is None:
            return
        switch_id = payload.get("switch_id")
        switch_port = payload.get("switch_port")
        ap_id = payload.get("ap_id")
        ap_name = payload.get("ap_name")

        cache_keys: list[str] = []
        if switch_id and switch_port:
            cache_keys.append(f"switch_port:{switch_id}:{switch_port}")
        if ap_id:
            cache_keys.append(f"ap_port:ap_id:{ap_id}")
        if ap_name:
            cache_keys.append(f"ap_port:ap_name:{ap_name}")

        cached = _cache_first(self._cache, cache_keys)
        if cached is not None:
            _merge_missing(payload, cached)
            return

        port_state = None
        if switch_id and switch_port:
            port_state = adapters.switch.get_switch_port_state(
                switch_id=switch_id, port=switch_port, context=context
            )
        elif ap_id or ap_name:
            port_state = adapters.switch.resolve_ap_to_switch_port(
                ap_id=ap_id, ap_name=ap_name, context=context
            )
        if port_state is None:
            return

        resolved = {
            "switch_id": port_state.switch_id,
            "switch_port": port_state.port,
            "ap_id": port_state.ap_id,
            "ap_name": port_state.ap_name,
        }
        filtered = {key: value for key, value in resolved.items() if value is not None}
        if not filtered:
            return

        alias_keys = list(cache_keys)
        if filtered.get("switch_id") and filtered.get("switch_port"):
            alias_keys.append(f"switch_port:{filtered['switch_id']}:{filtered['switch_port']}")
        if filtered.get("ap_id"):
            alias_keys.append(f"ap_port:ap_id:{filtered['ap_id']}")
        if filtered.get("ap_name"):
            alias_keys.append(f"ap_port:ap_name:{filtered['ap_name']}")
        _set_aliases(self._cache, alias_keys, filtered, self._ttl_seconds)
        _merge_missing(payload, filtered)