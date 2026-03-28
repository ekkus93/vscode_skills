from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from nettools.logging import configure_logging


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def isoformat_utc(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def build_common_parser(skill_name: str, description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--skill-name", default=skill_name)
    parser.add_argument("--scope-type", default="service")
    parser.add_argument("--site-id")
    parser.add_argument("--client-id")
    parser.add_argument("--client-mac")
    parser.add_argument("--ap-id")
    parser.add_argument("--ap-name")
    parser.add_argument("--ssid")
    parser.add_argument("--switch-id")
    parser.add_argument("--switch-port")
    parser.add_argument("--vlan-id")
    parser.add_argument("--time-window-minutes", type=int, default=15)
    parser.add_argument("--start-time")
    parser.add_argument("--end-time")
    parser.add_argument("--include-raw", action="store_true")
    return parser


def detect_scope_id(arguments: argparse.Namespace) -> str:
    for candidate in (
        arguments.client_id,
        arguments.client_mac,
        arguments.ap_id,
        arguments.ap_name,
        arguments.switch_port,
        arguments.switch_id,
        arguments.ssid,
        arguments.vlan_id,
        arguments.site_id,
    ):
        if candidate:
            return str(candidate)
    return "unscoped"


def build_time_window(arguments: argparse.Namespace) -> dict[str, str]:
    end = utc_now()
    if arguments.start_time and arguments.end_time:
        return {
            "start": arguments.start_time,
            "end": arguments.end_time,
        }

    start = end - timedelta(minutes=arguments.time_window_minutes)
    return {
        "start": isoformat_utc(start),
        "end": isoformat_utc(end),
    }


def filtered_inputs(arguments: argparse.Namespace) -> dict[str, Any]:
    return {
        key: value
        for key, value in vars(arguments).items()
        if key not in {"skill_name", "scope_type"} and value not in (None, False)
    }


def build_placeholder_result(
    *,
    skill_name: str,
    scope_type: str,
    arguments: argparse.Namespace,
) -> dict[str, Any]:
    return {
        "status": "unknown",
        "skill_name": skill_name,
        "scope_type": scope_type,
        "scope_id": detect_scope_id(arguments),
        "summary": f"{skill_name} is scaffolded but not implemented yet.",
        "confidence": "low",
        "observed_at": isoformat_utc(utc_now()),
        "time_window": build_time_window(arguments),
        "evidence": {
            "scaffold": True,
            "inputs": filtered_inputs(arguments),
        },
        "findings": [
            {
                "code": "NOT_IMPLEMENTED",
                "severity": "info",
                "message": "Phase 0 scaffold only; analysis logic is not implemented yet.",
                "metric": None,
                "value": None,
                "threshold": None,
            }
        ],
        "next_actions": [],
        "raw_refs": [],
    }


def run_placeholder_skill(skill_name: str, scope_type: str, description: str) -> int:
    logger = configure_logging(skill_name)
    parser = build_common_parser(skill_name, description)
    arguments = parser.parse_args()
    result = build_placeholder_result(
        skill_name=skill_name,
        scope_type=scope_type,
        arguments=arguments,
    )

    logger.info(
        "placeholder skill invoked",
        extra={
            "skill_name": skill_name,
            "scope_type": scope_type,
            "scope_id": result["scope_id"],
        },
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(
        run_placeholder_skill(
            skill_name="nettools.scaffold",
            scope_type="service",
            description="Run the generic NETTOOLS scaffold helper.",
        )
    )
