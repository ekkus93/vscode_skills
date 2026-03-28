from __future__ import annotations

import argparse
from datetime import datetime, timezone

from pydantic import ValidationError

from .errors import BadInputError, error_to_skill_result
from .findings import NOT_IMPLEMENTED
from .logging import configure_logging
from .models import (
    Confidence,
    Finding,
    FindingSeverity,
    ScopeType,
    SharedInputBase,
    SkillResult,
    Status,
)


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


def build_placeholder_result(
    *,
    skill_name: str,
    scope_type: ScopeType,
    shared_input: SharedInputBase,
) -> SkillResult:
    return SkillResult(
        status=Status.UNKNOWN,
        skill_name=skill_name,
        scope_type=scope_type,
        scope_id=shared_input.scope_id,
        summary=f"{skill_name} is scaffolded but not implemented yet.",
        confidence=Confidence.LOW,
        observed_at=utc_now(),
        time_window=shared_input.time_window,
        evidence={
            "scaffold": True,
            "inputs": shared_input.to_input_summary(),
        },
        findings=[
            Finding(
                code=NOT_IMPLEMENTED,
                severity=FindingSeverity.INFO,
                message=(
                    "Phase 1 shared contracts are in place, but the skill "
                    "analysis logic is not implemented yet."
                ),
            )
        ],
        next_actions=[],
        raw_refs=[],
    )


def run_placeholder_skill(skill_name: str, scope_type: str, description: str) -> int:
    logger = configure_logging(skill_name)
    parser = build_common_parser(skill_name, description)
    arguments = parser.parse_args()
    requested_scope_type = ScopeType(scope_type)

    try:
        shared_input = SharedInputBase.model_validate(
            {
                key: value
                for key, value in vars(arguments).items()
                if key not in {"skill_name", "scope_type"}
            }
        )
    except ValidationError as exc:
        error_result = error_to_skill_result(
            error=BadInputError(str(exc)),
            skill_name=skill_name,
            scope_type=requested_scope_type,
            scope_id="unscoped",
            time_window=SharedInputBase().time_window,
        )
        print(error_result.model_dump_json(indent=2))
        return 2

    result = build_placeholder_result(
        skill_name=skill_name,
        scope_type=requested_scope_type,
        shared_input=shared_input,
    )

    logger.info(
        "placeholder skill invoked",
        skill_name=skill_name,
        scope_type=requested_scope_type.value,
        scope_id=result.scope_id,
        inputs=shared_input.to_input_summary(),
    )
    print(result.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(
        run_placeholder_skill(
            skill_name="nettools.scaffold",
            scope_type="service",
            description="Run the generic NETTOOLS scaffold helper.",
        )
    )
