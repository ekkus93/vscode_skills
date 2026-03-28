from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .execution import SKILL_REGISTRY
from .state import IncidentType


class StopSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_skill_invocations: int = Field(default=8, ge=1)
    max_elapsed_seconds: int = Field(default=300, ge=1)
    max_branch_depth: int = Field(default=4, ge=0)
    high_confidence_threshold: float = Field(default=0.75, ge=0.0, le=1.0)


class SamplingSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_sampled_clients: int = Field(default=1, ge=0)
    max_sampled_aps: int = Field(default=1, ge=0)
    allow_client_sampling: bool = False
    allow_ap_sampling: bool = False


class PlaybookDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    incident_types: list[IncidentType] = Field(default_factory=list)
    default_sequence: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    optional_skills: list[str] = Field(default_factory=list)
    allowed_branch_transitions: dict[str, list[str]] = Field(default_factory=dict)
    stop_settings: StopSettings = Field(default_factory=StopSettings)
    sampling_settings: SamplingSettings = Field(default_factory=SamplingSettings)

    @model_validator(mode="after")
    def validate_playbook(self) -> PlaybookDefinition:
        if not self.default_sequence:
            raise ValueError("default_sequence must contain at least one skill")

        known_skills = set(SKILL_REGISTRY)
        referenced_skills = set(self.default_sequence)
        referenced_skills.update(self.required_skills)
        referenced_skills.update(self.optional_skills)
        referenced_skills.update(self.allowed_branch_transitions)
        for targets in self.allowed_branch_transitions.values():
            referenced_skills.update(targets)

        unknown_skills = sorted(skill for skill in referenced_skills if skill not in known_skills)
        if unknown_skills:
            raise ValueError(
                "playbook references unknown skills: " + ", ".join(unknown_skills)
            )

        missing_required = sorted(
            skill for skill in self.required_skills if skill not in self.default_sequence
        )
        if missing_required:
            raise ValueError(
                "required_skills must be included in default_sequence: "
                + ", ".join(missing_required)
            )

        legal_sources = set(self.default_sequence).union(self.optional_skills)
        illegal_sources = sorted(
            source for source in self.allowed_branch_transitions if source not in legal_sources
        )
        if illegal_sources:
            raise ValueError(
                "allowed_branch_transitions contains unknown source skills: "
                + ", ".join(illegal_sources)
            )

        return self


DEFAULT_PLAYBOOKS: dict[str, PlaybookDefinition] = {
    "single_client_wifi_issue": PlaybookDefinition(
        name="single_client_wifi_issue",
        incident_types=[IncidentType.SINGLE_CLIENT],
        default_sequence=[
            "net.incident_intake",
            "net.client_health",
            "net.roaming_analysis",
            "net.ap_rf_health",
            "net.ap_uplink_health",
            "net.dns_latency",
            "net.dhcp_path",
            "net.segmentation_policy",
            "net.incident_correlation",
        ],
        required_skills=[
            "net.incident_intake",
            "net.client_health",
            "net.ap_rf_health",
            "net.dns_latency",
            "net.incident_correlation",
        ],
        optional_skills=[
            "net.roaming_analysis",
            "net.ap_uplink_health",
            "net.dhcp_path",
            "net.segmentation_policy",
        ],
        allowed_branch_transitions={
            "net.client_health": [
                "net.roaming_analysis",
                "net.ap_rf_health",
                "net.ap_uplink_health",
                "net.dns_latency",
            ],
            "net.ap_rf_health": ["net.ap_uplink_health", "net.dns_latency"],
            "net.dns_latency": ["net.dhcp_path", "net.incident_correlation"],
        },
    ),
    "area_based_wifi_issue": PlaybookDefinition(
        name="area_based_wifi_issue",
        incident_types=[IncidentType.SINGLE_AREA],
        default_sequence=[
            "net.incident_intake",
            "net.ap_rf_health",
            "net.ap_uplink_health",
            "net.client_health",
            "net.roaming_analysis",
            "net.dns_latency",
            "net.dhcp_path",
            "net.incident_correlation",
        ],
        required_skills=[
            "net.incident_intake",
            "net.ap_rf_health",
            "net.ap_uplink_health",
            "net.incident_correlation",
        ],
        optional_skills=[
            "net.client_health",
            "net.roaming_analysis",
            "net.dns_latency",
            "net.dhcp_path",
        ],
        allowed_branch_transitions={
            "net.ap_rf_health": ["net.ap_uplink_health", "net.client_health"],
            "net.client_health": ["net.roaming_analysis", "net.dns_latency"],
        },
        sampling_settings=SamplingSettings(
            max_sampled_clients=5,
            max_sampled_aps=2,
            allow_client_sampling=True,
            allow_ap_sampling=True,
        ),
    ),
    "site_wide_internal_slowdown": PlaybookDefinition(
        name="site_wide_internal_slowdown",
        incident_types=[IncidentType.SITE_WIDE],
        default_sequence=[
            "net.incident_intake",
            "net.change_detection",
            "net.path_probe",
            "net.stp_loop_anomaly",
            "net.ap_uplink_health",
            "net.dns_latency",
            "net.dhcp_path",
            "net.ap_rf_health",
            "net.client_health",
            "net.incident_correlation",
        ],
        required_skills=[
            "net.incident_intake",
            "net.change_detection",
            "net.path_probe",
            "net.stp_loop_anomaly",
            "net.incident_correlation",
        ],
        optional_skills=[
            "net.ap_uplink_health",
            "net.dns_latency",
            "net.dhcp_path",
            "net.ap_rf_health",
            "net.client_health",
        ],
        allowed_branch_transitions={
            "net.path_probe": [
                "net.dns_latency",
                "net.dhcp_path",
                "net.stp_loop_anomaly",
            ],
            "net.stp_loop_anomaly": ["net.ap_uplink_health", "net.incident_correlation"],
        },
        stop_settings=StopSettings(max_skill_invocations=10, max_elapsed_seconds=420),
        sampling_settings=SamplingSettings(
            max_sampled_clients=5,
            max_sampled_aps=3,
            allow_client_sampling=True,
            allow_ap_sampling=True,
        ),
    ),
    "auth_or_onboarding_issue": PlaybookDefinition(
        name="auth_or_onboarding_issue",
        incident_types=[IncidentType.AUTH_OR_ONBOARDING],
        default_sequence=[
            "net.incident_intake",
            "net.auth_8021x_radius",
            "net.dhcp_path",
            "net.segmentation_policy",
            "net.dns_latency",
            "net.client_health",
            "net.incident_correlation",
        ],
        required_skills=[
            "net.incident_intake",
            "net.auth_8021x_radius",
            "net.dhcp_path",
            "net.incident_correlation",
        ],
        optional_skills=["net.segmentation_policy", "net.dns_latency", "net.client_health"],
        allowed_branch_transitions={
            "net.auth_8021x_radius": ["net.dhcp_path", "net.segmentation_policy"],
            "net.dhcp_path": ["net.segmentation_policy", "net.dns_latency"],
        },
    ),
    "unclear_general_network_issue": PlaybookDefinition(
        name="unclear_general_network_issue",
        incident_types=[IncidentType.INTERMITTENT_UNCLEAR, IncidentType.UNKNOWN_SCOPE],
        default_sequence=[
            "net.incident_intake",
            "net.path_probe",
            "net.dns_latency",
            "net.dhcp_path",
            "net.client_health",
            "net.ap_rf_health",
            "net.incident_correlation",
        ],
        required_skills=[
            "net.incident_intake",
            "net.path_probe",
            "net.dns_latency",
            "net.dhcp_path",
            "net.incident_correlation",
        ],
        optional_skills=["net.client_health", "net.ap_rf_health"],
        allowed_branch_transitions={
            "net.path_probe": ["net.dns_latency", "net.dhcp_path"],
            "net.dns_latency": ["net.client_health", "net.ap_rf_health"],
        },
    ),
}


def get_playbook_definition(name: str) -> PlaybookDefinition | None:
    return DEFAULT_PLAYBOOKS.get(name)


def list_playbook_definitions() -> list[PlaybookDefinition]:
    return list(DEFAULT_PLAYBOOKS.values())