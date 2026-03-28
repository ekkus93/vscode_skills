from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from pydantic import BaseModel, ValidationError

from ..errors import BadInputError, NettoolsError, error_to_skill_result
from ..logging import StructuredLogger, configure_logging, generate_invocation_id
from ..models import ScopeType, SharedInputBase, SkillResult
from ..priority1 import (
    AdapterBundle,
    ApRfHealthInput,
    ApUplinkHealthInput,
    ClientHealthInput,
    DhcpPathInput,
    DnsLatencyInput,
    StpLoopAnomalyInput,
    evaluate_ap_rf_health,
    evaluate_ap_uplink_health,
    evaluate_client_health,
    evaluate_dhcp_path,
    evaluate_dns_latency,
    evaluate_stp_loop_anomaly,
)
from ..priority2 import (
    Auth8021xRadiusInput,
    PathProbeInput,
    RoamingAnalysisInput,
    SegmentationPolicyInput,
    evaluate_auth_8021x_radius,
    evaluate_path_probe,
    evaluate_roaming_analysis,
    evaluate_segmentation_policy,
)
from ..priority3 import (
    CaptureTriggerInput,
    ChangeDetectionInput,
    IncidentCorrelationInput,
    IncidentIntakeInput,
    evaluate_capture_trigger,
    evaluate_change_detection,
    evaluate_incident_correlation,
    evaluate_incident_intake,
)
from .resolution import IdentifierResolver

SkillInput = SharedInputBase
SkillHandler = Callable[[Any, AdapterBundle], SkillResult]


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


@dataclass(frozen=True)
class SkillDefinition:
    skill_name: str
    input_model: type[SkillInput]
    scope_type: ScopeType
    handler: SkillHandler


@dataclass(frozen=True)
class SkillExecutionRecord:
    invocation_id: str
    skill_name: str
    started_at: datetime
    finished_at: datetime
    duration_ms: int
    input_summary: dict[str, Any]
    result: SkillResult
    error_type: str | None = None


SKILL_REGISTRY: dict[str, SkillDefinition] = {
    "net.client_health": SkillDefinition(
        "net.client_health", ClientHealthInput, ScopeType.CLIENT, evaluate_client_health
    ),
    "net.ap_rf_health": SkillDefinition(
        "net.ap_rf_health", ApRfHealthInput, ScopeType.AP, evaluate_ap_rf_health
    ),
    "net.dhcp_path": SkillDefinition(
        "net.dhcp_path", DhcpPathInput, ScopeType.SERVICE, evaluate_dhcp_path
    ),
    "net.dns_latency": SkillDefinition(
        "net.dns_latency", DnsLatencyInput, ScopeType.SERVICE, evaluate_dns_latency
    ),
    "net.ap_uplink_health": SkillDefinition(
        "net.ap_uplink_health",
        ApUplinkHealthInput,
        ScopeType.SWITCH_PORT,
        evaluate_ap_uplink_health,
    ),
    "net.stp_loop_anomaly": SkillDefinition(
        "net.stp_loop_anomaly",
        StpLoopAnomalyInput,
        ScopeType.SITE,
        evaluate_stp_loop_anomaly,
    ),
    "net.roaming_analysis": SkillDefinition(
        "net.roaming_analysis",
        RoamingAnalysisInput,
        ScopeType.CLIENT,
        evaluate_roaming_analysis,
    ),
    "net.auth_8021x_radius": SkillDefinition(
        "net.auth_8021x_radius",
        Auth8021xRadiusInput,
        ScopeType.SERVICE,
        evaluate_auth_8021x_radius,
    ),
    "net.path_probe": SkillDefinition(
        "net.path_probe", PathProbeInput, ScopeType.PATH, evaluate_path_probe
    ),
    "net.segmentation_policy": SkillDefinition(
        "net.segmentation_policy",
        SegmentationPolicyInput,
        ScopeType.CLIENT,
        evaluate_segmentation_policy,
    ),
    "net.incident_intake": SkillDefinition(
        "net.incident_intake",
        IncidentIntakeInput,
        ScopeType.SERVICE,
        evaluate_incident_intake,
    ),
    "net.incident_correlation": SkillDefinition(
        "net.incident_correlation",
        IncidentCorrelationInput,
        ScopeType.SERVICE,
        evaluate_incident_correlation,
    ),
    "net.change_detection": SkillDefinition(
        "net.change_detection",
        ChangeDetectionInput,
        ScopeType.SERVICE,
        evaluate_change_detection,
    ),
    "net.capture_trigger": SkillDefinition(
        "net.capture_trigger",
        CaptureTriggerInput,
        ScopeType.SERVICE,
        evaluate_capture_trigger,
    ),
}


def get_skill_definition(skill_name: str) -> SkillDefinition | None:
    return SKILL_REGISTRY.get(skill_name)


def _coerce_payload(payload: Mapping[str, Any] | BaseModel) -> dict[str, Any]:
    if isinstance(payload, BaseModel):
        return payload.model_dump(mode="python", exclude_none=True)
    return {key: value for key, value in payload.items() if value is not None}


def _filter_payload(payload: Mapping[str, Any], input_model: type[SkillInput]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if key in input_model.model_fields and value is not None
    }


def _record_from_result(
    *,
    invocation_id: str,
    skill_name: str,
    started_at: datetime,
    finished_at: datetime,
    duration_ms: int,
    input_summary: dict[str, Any],
    result: SkillResult,
    error_type: str | None = None,
) -> SkillExecutionRecord:
    return SkillExecutionRecord(
        invocation_id=invocation_id,
        skill_name=skill_name,
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=duration_ms,
        input_summary=input_summary,
        result=result,
        error_type=error_type,
    )


def _error_record(
    *,
    invocation_id: str,
    skill_name: str,
    definition: SkillDefinition | None,
    payload: Mapping[str, Any],
    started_at: datetime,
    duration_ms: int,
    error: NettoolsError,
) -> SkillExecutionRecord:
    filtered_payload = (
        _filter_payload(payload, definition.input_model) if definition is not None else {}
    )
    time_window = (
        SharedInputBase.model_validate(filtered_payload).time_window
        if filtered_payload
        else SharedInputBase().time_window
    )
    finished_at = utc_now()
    scope_id = (
        str(
            payload.get("client_id")
            or payload.get("ap_id")
            or payload.get("site_id")
            or "unscoped"
        )
    )
    result = error_to_skill_result(
        error=error,
        skill_name=skill_name,
        scope_type=definition.scope_type if definition is not None else ScopeType.SERVICE,
        scope_id=scope_id,
        time_window=time_window,
        observed_at=finished_at,
    )
    return _record_from_result(
        invocation_id=invocation_id,
        skill_name=skill_name,
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=duration_ms,
        input_summary=dict(filtered_payload),
        result=result,
        error_type=type(error).__name__,
    )


def invoke_skill(
    skill_name: str,
    payload: Mapping[str, Any] | BaseModel,
    adapters: AdapterBundle,
    *,
    resolver: IdentifierResolver | None = None,
    logger: StructuredLogger | None = None,
) -> SkillExecutionRecord:
    invocation_id = generate_invocation_id()
    skill_logger = logger or configure_logging(skill_name, invocation_id=invocation_id)
    started_at = utc_now()
    started_perf = perf_counter()
    raw_payload = _coerce_payload(payload)
    definition = get_skill_definition(skill_name)

    if definition is None:
        duration_ms = int((perf_counter() - started_perf) * 1000)
        error = BadInputError(f"Unsupported NETTOOLS skill: {skill_name}")
        record = _error_record(
            invocation_id=invocation_id,
            skill_name=skill_name,
            definition=None,
            payload=raw_payload,
            started_at=started_at,
            duration_ms=duration_ms,
            error=error,
        )
        skill_logger.warning(
            "skill invocation rejected",
            skill_name=skill_name,
            scope_type=record.result.scope_type.value,
            scope_id=record.result.scope_id,
            error_type=record.error_type,
            duration_ms=record.duration_ms,
        )
        return record

    resolved_payload = (
        resolver.resolve_payload(raw_payload, adapters)
        if resolver is not None
        else dict(raw_payload)
    )
    filtered_payload = _filter_payload(resolved_payload, definition.input_model)
    scope_id = str(
        filtered_payload.get("client_id")
        or filtered_payload.get("ap_id")
        or filtered_payload.get("site_id")
        or "unscoped"
    )
    skill_logger.info(
        "skill invocation started",
        skill_name=skill_name,
        scope_type=definition.scope_type.value,
        scope_id=scope_id,
        inputs=filtered_payload,
    )

    try:
        skill_input = definition.input_model.model_validate(filtered_payload)
        raw_result = definition.handler(skill_input, adapters)
        result = SkillResult.model_validate(raw_result)
    except ValidationError as exc:
        duration_ms = int((perf_counter() - started_perf) * 1000)
        record = _error_record(
            invocation_id=invocation_id,
            skill_name=skill_name,
            definition=definition,
            payload=filtered_payload,
            started_at=started_at,
            duration_ms=duration_ms,
            error=BadInputError(str(exc)),
        )
        skill_logger.warning(
            "skill invocation produced a validation error",
            skill_name=skill_name,
            scope_type=record.result.scope_type.value,
            scope_id=record.result.scope_id,
            error_type=record.error_type,
            duration_ms=record.duration_ms,
        )
        return record
    except NettoolsError as exc:
        duration_ms = int((perf_counter() - started_perf) * 1000)
        record = _error_record(
            invocation_id=invocation_id,
            skill_name=skill_name,
            definition=definition,
            payload=filtered_payload,
            started_at=started_at,
            duration_ms=duration_ms,
            error=exc,
        )
        skill_logger.warning(
            "skill invocation produced a structured error",
            skill_name=skill_name,
            scope_type=record.result.scope_type.value,
            scope_id=record.result.scope_id,
            error_type=record.error_type,
            duration_ms=record.duration_ms,
            finding_codes=[finding.code for finding in record.result.findings],
        )
        return record
    except Exception as exc:
        duration_ms = int((perf_counter() - started_perf) * 1000)
        record = _error_record(
            invocation_id=invocation_id,
            skill_name=skill_name,
            definition=definition,
            payload=filtered_payload,
            started_at=started_at,
            duration_ms=duration_ms,
            error=NettoolsError(f"Unhandled exception during {skill_name}: {exc}"),
        )
        skill_logger.error(
            "skill invocation raised an unhandled exception",
            skill_name=skill_name,
            scope_type=record.result.scope_type.value,
            scope_id=record.result.scope_id,
            error_type=record.error_type,
            duration_ms=record.duration_ms,
        )
        return record

    finished_at = utc_now()
    duration_ms = int((perf_counter() - started_perf) * 1000)
    record = _record_from_result(
        invocation_id=invocation_id,
        skill_name=skill_name,
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=duration_ms,
        input_summary=skill_input.to_input_summary(),
        result=result,
    )
    skill_logger.info(
        "skill invocation completed",
        skill_name=skill_name,
        scope_type=result.scope_type.value,
        scope_id=result.scope_id,
        duration_ms=record.duration_ms,
        result_status=result.status.value,
        finding_codes=[finding.code for finding in result.findings],
        next_actions=[action.skill for action in result.next_actions],
    )
    return record