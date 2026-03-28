"""Configuration helpers for NETTOOLS shared support code."""

from .thresholds import (
	ServiceThresholds,
	ThresholdConfig,
	WiredThresholds,
	WirelessThresholds,
	default_threshold_config,
)

__all__ = [
	"ServiceThresholds",
	"ThresholdConfig",
	"WiredThresholds",
	"WirelessThresholds",
	"default_threshold_config",
]
