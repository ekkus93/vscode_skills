from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .branch_rules import DEFAULT_BRANCH_RULES, BranchRule
from .classification import DEFAULT_PLAYBOOK_BY_INCIDENT_TYPE
from .execution import SKILL_REGISTRY
from .playbooks import DEFAULT_PLAYBOOKS, PlaybookDefinition, get_playbook_definition
from .scoring import HypothesisScoringConfig
from .state import IncidentType
from .stop_conditions import StopConditionConfig


class StopThresholdConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    high_confidence_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    ambiguity_gap: float | None = Field(default=None, ge=0.0, le=1.0)
    ambiguity_min_score: float | None = Field(default=None, ge=0.0, le=1.0)
    min_supporting_findings_for_high_confidence: int | None = Field(default=None, ge=0)
    no_new_information_delta: float | None = Field(default=None, ge=0.0, le=1.0)
    no_new_information_window: int | None = Field(default=None, ge=1)


class InvestigationBudgetConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_skill_invocations: int | None = Field(default=None, ge=1)
    max_elapsed_seconds: int | None = Field(default=None, ge=1)
    max_branch_depth: int | None = Field(default=None, ge=0)


class SamplingDefaultsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_sampled_clients: int | None = Field(default=None, ge=0)
    max_sampled_aps: int | None = Field(default=None, ge=0)
    allow_client_sampling: bool | None = None
    allow_ap_sampling: bool | None = None


class PolicyControlConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allow_active_probes: bool = True
    allow_capture_triggers: bool = True
    allow_external_resolver_comparisons: bool = True
    allow_optional_expensive_branches: bool = True
    expensive_branch_skills: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_expensive_branch_skills(self) -> PolicyControlConfig:
        unknown_skills = sorted(
            skill_name
            for skill_name in self.expensive_branch_skills
            if skill_name not in SKILL_REGISTRY
        )
        if unknown_skills:
            raise ValueError(
                "policy_controls.expensive_branch_skills references unknown skills: "
                + ", ".join(unknown_skills)
            )
        return self


class OrchestratorConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    playbook_mapping: dict[IncidentType, str] = Field(default_factory=dict)
    branch_rules: dict[str, list[BranchRule]] = Field(default_factory=dict)
    stop_thresholds: StopThresholdConfig = Field(default_factory=StopThresholdConfig)
    domain_score_thresholds: HypothesisScoringConfig = Field(
        default_factory=HypothesisScoringConfig
    )
    investigation_budgets: InvestigationBudgetConfig = Field(
        default_factory=InvestigationBudgetConfig
    )
    sampling_defaults: SamplingDefaultsConfig = Field(default_factory=SamplingDefaultsConfig)
    policy_controls: PolicyControlConfig = Field(default_factory=PolicyControlConfig)
    allowed_optional_branches: dict[str, dict[str, list[str]]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_references(self) -> OrchestratorConfig:
        known_playbooks = set(DEFAULT_PLAYBOOKS)
        configured_playbooks = set(self.playbook_mapping.values())
        unknown_playbooks = sorted(configured_playbooks - known_playbooks)
        if unknown_playbooks:
            raise ValueError(
                "playbook_mapping references unknown playbooks: "
                + ", ".join(unknown_playbooks)
            )

        known_skills = set(SKILL_REGISTRY)
        for source_skill, rules in self.branch_rules.items():
            if source_skill not in known_skills:
                raise ValueError(
                    f"branch_rules references unknown source skill: {source_skill}"
                )
            for rule in rules:
                if rule.source_skill != source_skill:
                    raise ValueError(
                        "branch_rules keys must match each rule's source_skill: "
                        f"{source_skill} != {rule.source_skill}"
                    )
                unknown_targets = sorted(
                    skill_name
                    for skill_name in rule.candidate_next_skills
                    if skill_name not in known_skills
                )
                if unknown_targets:
                    raise ValueError(
                        f"branch_rules for {source_skill} reference unknown target skills: "
                        + ", ".join(unknown_targets)
                    )

        for playbook_name, transitions in self.allowed_optional_branches.items():
            playbook = DEFAULT_PLAYBOOKS.get(playbook_name)
            if playbook is None:
                raise ValueError(
                    "allowed_optional_branches references unknown playbook: "
                    f"{playbook_name}"
                )
            known_playbook_skills = set(playbook.default_sequence)
            known_playbook_skills.update(playbook.optional_skills)
            known_playbook_skills.update(playbook.required_skills)
            for source_skill, targets in transitions.items():
                if source_skill not in known_playbook_skills:
                    raise ValueError(
                        "allowed_optional_branches references unknown source skill "
                        f"{source_skill} for playbook {playbook_name}"
                    )
                unknown_targets = sorted(
                    target for target in targets if target not in known_playbook_skills
                )
                if unknown_targets:
                    raise ValueError(
                        f"allowed_optional_branches for {playbook_name}/{source_skill} "
                        "reference unknown target skills: "
                        + ", ".join(unknown_targets)
                    )

        return self

    def resolved_playbook_mapping(self) -> dict[IncidentType, str]:
        mapping = dict(DEFAULT_PLAYBOOK_BY_INCIDENT_TYPE)
        mapping.update(self.playbook_mapping)
        return mapping

    def merged_branch_rules(self) -> dict[str, list[BranchRule]]:
        merged = {
            source_skill: [rule.model_copy(deep=True) for rule in rules]
            for source_skill, rules in DEFAULT_BRANCH_RULES.items()
        }
        for source_skill, rules in self.branch_rules.items():
            merged[source_skill] = [rule.model_copy(deep=True) for rule in rules]
        return merged

    def resolve_playbook_definition(self, playbook_name: str) -> PlaybookDefinition:
        playbook = get_playbook_definition(playbook_name)
        if playbook is None:
            raise ValueError(f"Unknown playbook: {playbook_name}")

        resolved_playbook = playbook.model_copy(deep=True)

        stop_updates = {
            key: value
            for key, value in {
                "max_skill_invocations": self.investigation_budgets.max_skill_invocations,
                "max_elapsed_seconds": self.investigation_budgets.max_elapsed_seconds,
                "max_branch_depth": self.investigation_budgets.max_branch_depth,
                "high_confidence_threshold": self.stop_thresholds.high_confidence_threshold,
            }.items()
            if value is not None
        }
        if stop_updates:
            resolved_playbook.stop_settings = resolved_playbook.stop_settings.model_copy(
                update=stop_updates
            )

        sampling_updates = {
            key: value
            for key, value in {
                "max_sampled_clients": self.sampling_defaults.max_sampled_clients,
                "max_sampled_aps": self.sampling_defaults.max_sampled_aps,
                "allow_client_sampling": self.sampling_defaults.allow_client_sampling,
                "allow_ap_sampling": self.sampling_defaults.allow_ap_sampling,
            }.items()
            if value is not None
        }
        if sampling_updates:
            resolved_playbook.sampling_settings = (
                resolved_playbook.sampling_settings.model_copy(update=sampling_updates)
            )

        if playbook_name in self.allowed_optional_branches:
            transitions = {
                source_skill: list(targets)
                for source_skill, targets in resolved_playbook.allowed_branch_transitions.items()
            }
            transitions.update(
                {
                    source_skill: list(targets)
                    for source_skill, targets in self.allowed_optional_branches[
                        playbook_name
                    ].items()
                }
            )
            resolved_playbook.allowed_branch_transitions = transitions

        return resolved_playbook

    def resolved_scoring_config(self) -> HypothesisScoringConfig:
        return self.domain_score_thresholds.model_copy(deep=True)

    def build_stop_condition_config(self) -> StopConditionConfig:
        defaults = StopConditionConfig()
        return StopConditionConfig(
            ambiguity_gap=(
                self.stop_thresholds.ambiguity_gap
                if self.stop_thresholds.ambiguity_gap is not None
                else defaults.ambiguity_gap
            ),
            ambiguity_min_score=(
                self.stop_thresholds.ambiguity_min_score
                if self.stop_thresholds.ambiguity_min_score is not None
                else defaults.ambiguity_min_score
            ),
            min_supporting_findings_for_high_confidence=(
                self.stop_thresholds.min_supporting_findings_for_high_confidence
                if self.stop_thresholds.min_supporting_findings_for_high_confidence is not None
                else defaults.min_supporting_findings_for_high_confidence
            ),
            no_new_information_delta=(
                self.stop_thresholds.no_new_information_delta
                if self.stop_thresholds.no_new_information_delta is not None
                else defaults.no_new_information_delta
            ),
            no_new_information_window=(
                self.stop_thresholds.no_new_information_window
                if self.stop_thresholds.no_new_information_window is not None
                else defaults.no_new_information_window
            ),
            scoring=self.resolved_scoring_config(),
        )

    def allows_active_probe_skill(self, skill_name: str) -> bool:
        if skill_name != "net.path_probe":
            return True
        return self.policy_controls.allow_active_probes

    def allows_capture_triggers(self) -> bool:
        return self.policy_controls.allow_capture_triggers

    def allows_external_resolver_comparisons(self) -> bool:
        return self.policy_controls.allow_external_resolver_comparisons

    def allows_optional_expensive_branch(
        self,
        skill_name: str,
        *,
        playbook: PlaybookDefinition,
    ) -> bool:
        if self.policy_controls.allow_optional_expensive_branches:
            return True
        if skill_name not in self.policy_controls.expensive_branch_skills:
            return True
        return skill_name not in playbook.optional_skills