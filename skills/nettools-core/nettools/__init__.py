"""Shared bootstrap package for NETTOOLS skills."""

from .errors import (
	BadInputError,
	DependencyTimeoutError,
	DependencyUnavailableError,
	InsufficientEvidenceError,
	NettoolsError,
	UnsupportedProviderOperationError,
	error_to_skill_result,
)
from .cli import run_placeholder_skill
from .config import ThresholdConfig, default_threshold_config
from .models import SharedInputBase, SkillResult

__all__ = [
	"BadInputError",
	"DependencyTimeoutError",
	"DependencyUnavailableError",
	"InsufficientEvidenceError",
	"NettoolsError",
	"SharedInputBase",
	"SkillResult",
	"ThresholdConfig",
	"UnsupportedProviderOperationError",
	"default_threshold_config",
	"error_to_skill_result",
	"run_placeholder_skill",
]
