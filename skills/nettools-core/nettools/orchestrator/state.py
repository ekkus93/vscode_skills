from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..models import Confidence, ScopeType, SkillResult, Status
from .execution import SkillExecutionRecord


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


class IncidentType(str, Enum):
    SINGLE_CLIENT = "single_client"
    SINGLE_AREA = "single_area"
    SITE_WIDE = "site_wide"
    AUTH_OR_ONBOARDING = "auth_or_onboarding"
    INTERMITTENT_UNCLEAR = "intermittent_unclear"
    UNKNOWN_SCOPE = "unknown_scope"


class DiagnosticDomain(str, Enum):
    SINGLE_CLIENT_RF = "single_client_rf"
    SINGLE_AP_RF = "single_ap_rf"
    ROAMING_ISSUE = "roaming_issue"
    DHCP_ISSUE = "dhcp_issue"
    DNS_ISSUE = "dns_issue"
    AUTH_ISSUE = "auth_issue"
    AP_UPLINK_ISSUE = "ap_uplink_issue"
    L2_TOPOLOGY_ISSUE = "l2_topology_issue"
    SEGMENTATION_POLICY_ISSUE = "segmentation_policy_issue"
    SITE_WIDE_INTERNAL_LAN_ISSUE = "site_wide_internal_lan_issue"
    WAN_OR_EXTERNAL_ISSUE = "wan_or_external_issue"
    UNKNOWN = "unknown"


class InvestigationStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"


class StopReasonCode(str, Enum):
    HIGH_CONFIDENCE_DIAGNOSIS = "high_confidence_diagnosis"
    TWO_DOMAIN_BOUNDED_AMBIGUITY = "two_domain_bounded_ambiguity"
    INVESTIGATION_BUDGET_EXHAUSTED = "investigation_budget_exhausted"
    DEPENDENCY_BLOCKED = "dependency_blocked"
    HUMAN_ACTION_REQUIRED = "human_action_required"
    NO_NEW_INFORMATION = "no_new_information"


class ScopeSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    site_id: str | None = None
    ssid: str | None = None
    affected_users_estimate: int | None = Field(default=None, ge=0)
    affected_areas: list[str] = Field(default_factory=list)
    known_clients: list[str] = Field(default_factory=list)
    known_aps: list[str] = Field(default_factory=list)
    known_client_ids: list[str] = Field(default_factory=list)
    known_client_macs: list[str] = Field(default_factory=list)
    known_ap_ids: list[str] = Field(default_factory=list)
    known_ap_names: list[str] = Field(default_factory=list)
    sampled_clients: list[str] = Field(default_factory=list)
    sampled_aps: list[str] = Field(default_factory=list)
    sampled_comparison_aps: list[str] = Field(default_factory=list)
    sampled_areas: list[str] = Field(default_factory=list)
    sampled_comparison_areas: list[str] = Field(default_factory=list)
    sampling_rationale: list[str] = Field(default_factory=list)


class SamplingSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sampled_clients: list[str] = Field(default_factory=list)
    sampled_aps: list[str] = Field(default_factory=list)
    sampled_comparison_aps: list[str] = Field(default_factory=list)
    sampled_areas: list[str] = Field(default_factory=list)
    sampled_comparison_areas: list[str] = Field(default_factory=list)
    rationale: list[str] = Field(default_factory=list)

    @classmethod
    def from_scope_summary(cls, scope_summary: ScopeSummary) -> SamplingSummary:
        return cls(
            sampled_clients=list(scope_summary.sampled_clients),
            sampled_aps=list(scope_summary.sampled_aps),
            sampled_comparison_aps=list(scope_summary.sampled_comparison_aps),
            sampled_areas=list(scope_summary.sampled_areas),
            sampled_comparison_areas=list(scope_summary.sampled_comparison_areas),
            rationale=list(scope_summary.sampling_rationale),
        )


class DomainScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain: DiagnosticDomain
    score: float = Field(ge=0.0, le=1.0)
    confidence: Confidence | None = None
    supporting_findings: list[str] = Field(default_factory=list)
    contradicting_findings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def set_confidence(self) -> DomainScore:
        if self.confidence is None:
            if self.score < 0.40:
                self.confidence = Confidence.LOW
            elif self.score < 0.75:
                self.confidence = Confidence.MEDIUM
            else:
                self.confidence = Confidence.HIGH
        return self


class EvidenceEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skill_name: str
    recorded_at: datetime
    status: Status
    scope_type: ScopeType
    scope_id: str
    summary: str
    findings: list[str] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)
    raw_refs: list[Any] = Field(default_factory=list)


class DependencyFailure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skill_name: str
    error_type: str
    summary: str
    recorded_at: datetime
    raw_refs: list[Any] = Field(default_factory=list)


class StopReason(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: StopReasonCode
    message: str
    related_domains: list[DiagnosticDomain] = Field(default_factory=list)
    supporting_context: dict[str, Any] = Field(default_factory=dict)
    uncertainty_summary: str | None = None
    recommended_human_actions: list[str] = Field(default_factory=list)


class RankedCause(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain: DiagnosticDomain
    score: float = Field(ge=0.0, le=1.0)
    confidence: Confidence
    rationale: str
    supporting_findings: list[str] = Field(default_factory=list)


class ExecutionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    invocation_id: str
    skill_name: str
    started_at: datetime
    finished_at: datetime
    duration_ms: int = Field(ge=0)
    input_summary: dict[str, Any] = Field(default_factory=dict)
    result: SkillResult
    error_type: str | None = None

    @classmethod
    def from_skill_execution_record(cls, record: SkillExecutionRecord) -> ExecutionRecord:
        return cls(
            invocation_id=record.invocation_id,
            skill_name=record.skill_name,
            started_at=record.started_at,
            finished_at=record.finished_at,
            duration_ms=record.duration_ms,
            input_summary=record.input_summary,
            result=record.result,
            error_type=record.error_type,
        )


class IncidentStateReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    incident_id: str
    status: InvestigationStatus
    playbook_used: str | None = None
    summary: str
    top_causes: list[RankedCause] = Field(default_factory=list)
    recommended_next_skill: str | None = None
    stop_reason: StopReason | None = None
    executed_skills: list[str] = Field(default_factory=list)
    dependency_failures: list[DependencyFailure] = Field(default_factory=list)
    sampling_summary: SamplingSummary = Field(default_factory=SamplingSummary)


class StopReasonSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: StopReasonCode
    message: str

    @classmethod
    def from_stop_reason(cls, stop_reason: StopReason) -> StopReasonSummary:
        return cls(code=stop_reason.code, message=stop_reason.message)


class SkillTraceSummaryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skill_name: str
    status: Status
    summary: str
    duration_ms: int = Field(ge=0)
    error_type: str | None = None

    @classmethod
    def from_execution_record(cls, record: ExecutionRecord) -> SkillTraceSummaryEntry:
        return cls(
            skill_name=record.skill_name,
            status=record.result.status,
            summary=record.result.summary,
            duration_ms=record.duration_ms,
            error_type=record.error_type,
        )


class EvidenceSummaryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skill_name: str
    status: Status
    summary: str
    findings: list[str] = Field(default_factory=list)

    @classmethod
    def from_evidence_entry(cls, entry: EvidenceEntry) -> EvidenceSummaryEntry:
        return cls(
            skill_name=entry.skill_name,
            status=entry.status,
            summary=entry.summary,
            findings=list(entry.findings),
        )


class DiagnoseIncidentReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Status
    incident_id: str
    incident_type: IncidentType
    playbook_used: str | None = None
    summary: str
    ranked_causes: list[RankedCause] = Field(default_factory=list)
    eliminated_domains: list[DiagnosticDomain] = Field(default_factory=list)
    skill_trace: list[SkillTraceSummaryEntry] = Field(default_factory=list)
    evidence_summary: list[EvidenceSummaryEntry] = Field(default_factory=list)
    dependency_failures: list[DependencyFailure] = Field(default_factory=list)
    stop_reason: StopReasonSummary | None = None
    recommended_human_actions: list[str] = Field(default_factory=list)
    recommended_followup_skills: list[str] = Field(default_factory=list)
    sampling_summary: SamplingSummary = Field(default_factory=SamplingSummary)
    confidence: Confidence = Confidence.LOW

    @classmethod
    def from_incident_state(
        cls,
        state: IncidentState,
        *,
        result_status: Status,
        summary: str,
        ranked_causes: list[RankedCause] | None = None,
    ) -> DiagnoseIncidentReport:
        ranked = list(ranked_causes or [])
        return cls(
            status=result_status,
            incident_id=state.incident_id,
            incident_type=state.incident_type,
            playbook_used=state.playbook_used,
            summary=summary,
            ranked_causes=ranked,
            eliminated_domains=list(state.eliminated_domains),
            skill_trace=[
                SkillTraceSummaryEntry.from_execution_record(record)
                for record in state.skill_trace
            ],
            evidence_summary=[
                EvidenceSummaryEntry.from_evidence_entry(entry)
                for entry in state.evidence_log
            ],
            dependency_failures=list(state.dependency_failures),
            stop_reason=(
                StopReasonSummary.from_stop_reason(state.stop_reason)
                if state.stop_reason is not None
                else None
            ),
            recommended_human_actions=(
                list(state.stop_reason.recommended_human_actions)
                if state.stop_reason is not None
                else []
            ),
            recommended_followup_skills=(
                [state.recommended_next_skill]
                if state.recommended_next_skill is not None
                else []
            ),
            sampling_summary=SamplingSummary.from_scope_summary(state.scope_summary),
            confidence=(ranked[0].confidence if ranked else Confidence.LOW),
        )


class IncidentState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    incident_id: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    incident_type: IncidentType = IncidentType.UNKNOWN_SCOPE
    classification_rationale: list[str] = Field(default_factory=list)
    playbook_used: str | None = None
    playbook_selection_rationale: list[str] = Field(default_factory=list)
    branch_selection_rationale: list[str] = Field(default_factory=list)
    status: InvestigationStatus = InvestigationStatus.RUNNING
    scope_summary: ScopeSummary = Field(default_factory=ScopeSummary)
    suspected_domains: list[DiagnosticDomain] = Field(default_factory=list)
    eliminated_domains: list[DiagnosticDomain] = Field(default_factory=list)
    domain_scores: dict[DiagnosticDomain, DomainScore] = Field(default_factory=dict)
    evidence_log: list[EvidenceEntry] = Field(default_factory=list)
    skill_trace: list[ExecutionRecord] = Field(default_factory=list)
    dependency_failures: list[DependencyFailure] = Field(default_factory=list)
    recommended_next_skill: str | None = None
    stop_reason: StopReason | None = None

    @model_validator(mode="after")
    def validate_domain_sets(self) -> IncidentState:
        overlap = set(self.suspected_domains).intersection(self.eliminated_domains)
        if overlap:
            overlap_list = ", ".join(
                domain.value for domain in sorted(overlap, key=lambda item: item.value)
            )
            raise ValueError(
                "suspected_domains and eliminated_domains must be disjoint: "
                f"{overlap_list}"
            )
        return self

    def append_execution(self, record: SkillExecutionRecord) -> ExecutionRecord:
        execution_record = ExecutionRecord.from_skill_execution_record(record)
        self.skill_trace.append(execution_record)
        self.evidence_log.append(
            EvidenceEntry(
                skill_name=record.skill_name,
                recorded_at=record.finished_at,
                status=record.result.status,
                scope_type=record.result.scope_type,
                scope_id=record.result.scope_id,
                summary=record.result.summary,
                findings=[finding.code for finding in record.result.findings],
                evidence=record.result.evidence,
                raw_refs=record.result.raw_refs,
            )
        )
        if record.error_type is not None:
            self.dependency_failures.append(
                DependencyFailure(
                    skill_name=record.skill_name,
                    error_type=record.error_type,
                    summary=record.result.summary,
                    recorded_at=record.finished_at,
                    raw_refs=record.result.raw_refs,
                )
            )
        self.updated_at = record.finished_at
        return execution_record

    def set_domain_score(
        self,
        domain: DiagnosticDomain,
        *,
        score: float,
        confidence: Confidence | None = None,
        supporting_findings: list[str] | None = None,
        contradicting_findings: list[str] | None = None,
    ) -> DomainScore:
        domain_score = DomainScore(
            domain=domain,
            score=score,
            confidence=confidence,
            supporting_findings=supporting_findings or [],
            contradicting_findings=contradicting_findings or [],
        )
        self.domain_scores[domain] = domain_score
        if domain not in self.suspected_domains:
            self.suspected_domains.append(domain)
        if domain in self.eliminated_domains:
            self.eliminated_domains.remove(domain)
        self.updated_at = utc_now()
        return domain_score

    def eliminate_domain(self, domain: DiagnosticDomain) -> None:
        if domain not in self.eliminated_domains:
            self.eliminated_domains.append(domain)
        if domain in self.suspected_domains:
            self.suspected_domains.remove(domain)
        self.updated_at = utc_now()

    def recommend_next(self, skill_name: str | None) -> None:
        self.recommended_next_skill = skill_name
        self.updated_at = utc_now()

    def set_classification(
        self,
        incident_type: IncidentType,
        *,
        scope_summary: ScopeSummary | None = None,
        rationale: list[str] | None = None,
    ) -> None:
        self.incident_type = incident_type
        if scope_summary is not None:
            self.scope_summary = scope_summary
        if rationale is not None:
            self.classification_rationale = list(rationale)
        self.updated_at = utc_now()

    def set_playbook(
        self,
        playbook_name: str,
        *,
        rationale: list[str] | None = None,
    ) -> None:
        self.playbook_used = playbook_name
        if rationale is not None:
            self.playbook_selection_rationale = list(rationale)
        self.updated_at = utc_now()

    def set_branch_recommendation(
        self,
        skill_name: str | None,
        *,
        rationale: list[str] | None = None,
    ) -> None:
        self.recommended_next_skill = skill_name
        if rationale is not None:
            self.branch_selection_rationale = list(rationale)
        self.updated_at = utc_now()

    def set_stop_reason(self, stop_reason: StopReason) -> None:
        self.stop_reason = stop_reason
        self.updated_at = utc_now()

    def build_report(
        self,
        *,
        summary: str,
        top_causes: list[RankedCause] | None = None,
    ) -> IncidentStateReport:
        return IncidentStateReport(
            incident_id=self.incident_id,
            status=self.status,
            playbook_used=self.playbook_used,
            summary=summary,
            top_causes=top_causes or [],
            recommended_next_skill=self.recommended_next_skill,
            stop_reason=self.stop_reason,
            executed_skills=[record.skill_name for record in self.skill_trace],
            dependency_failures=self.dependency_failures,
            sampling_summary=SamplingSummary.from_scope_summary(self.scope_summary),
        )