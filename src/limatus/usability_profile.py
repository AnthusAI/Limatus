from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONTRAST_MIN_RATIO = 4.5
DEFAULT_TAP_TARGET_MIN_PX = 24

USABILITY_PROFILE_TOP_LEVEL_KEYS = frozenset({"contrast", "tapTarget", "focus"})
CONTRAST_BLOCK_KEYS = frozenset({"minRatio"})
TAP_TARGET_BLOCK_KEYS = frozenset({"minPx"})
FOCUS_BLOCK_KEYS = frozenset({"flagSuppressedOutline"})
DEFAULT_FOCUS_FLAG_SUPPRESSED_OUTLINE = True


class UsabilityProfileValidationError(ValueError):
    """Raised when a usability profile document fails validation."""


@dataclass(frozen=True)
class UsabilityContrastConfig:
    min_ratio: float


@dataclass(frozen=True)
class UsabilityTapTargetConfig:
    min_px: float


@dataclass(frozen=True)
class UsabilityFocusConfig:
    flag_suppressed_outline: bool


@dataclass(frozen=True)
class UsabilityProfile:
    contrast: UsabilityContrastConfig
    tap_target: UsabilityTapTargetConfig
    focus: UsabilityFocusConfig


@dataclass(frozen=True)
class LoadedUsabilityProfile:
    path: Path
    profile: UsabilityProfile


def load_usability_profile(profile_path: Path) -> LoadedUsabilityProfile:
    resolved = profile_path.resolve()
    if not resolved.is_file():
        raise UsabilityProfileValidationError(f"Usability profile not found: {resolved}")
    raw_text = resolved.read_text(encoding="utf-8")
    try:
        raw = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise UsabilityProfileValidationError(f"Invalid YAML in {resolved}: {exc}") from exc
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise UsabilityProfileValidationError(f"Usability profile must be a mapping in {resolved}")
    unknown = set(raw.keys()) - USABILITY_PROFILE_TOP_LEVEL_KEYS
    if unknown:
        joined = ", ".join(sorted(str(key) for key in unknown))
        raise UsabilityProfileValidationError(f"Unknown usability profile keys in {resolved}: {joined}")
    contrast = _parse_contrast(raw.get("contrast"), resolved)
    tap_target = _parse_tap_target(raw.get("tapTarget"), resolved)
    focus = _parse_focus(raw.get("focus"), resolved)
    return LoadedUsabilityProfile(
        path=resolved,
        profile=UsabilityProfile(contrast=contrast, tap_target=tap_target, focus=focus),
    )


def _parse_contrast(value: Any, profile_path: Path) -> UsabilityContrastConfig:
    if value is None:
        return UsabilityContrastConfig(min_ratio=DEFAULT_CONTRAST_MIN_RATIO)
    if not isinstance(value, dict):
        raise UsabilityProfileValidationError(f"contrast must be a mapping in {profile_path}")
    unknown = set(value.keys()) - CONTRAST_BLOCK_KEYS
    if unknown:
        joined = ", ".join(sorted(str(key) for key in unknown))
        raise UsabilityProfileValidationError(f"Unknown contrast keys in {profile_path}: {joined}")
    min_ratio_raw = value.get("minRatio", DEFAULT_CONTRAST_MIN_RATIO)
    if not isinstance(min_ratio_raw, (int, float)) or isinstance(min_ratio_raw, bool):
        raise UsabilityProfileValidationError(f"contrast.minRatio must be a number in {profile_path}")
    min_ratio = float(min_ratio_raw)
    if min_ratio <= 0:
        raise UsabilityProfileValidationError(f"contrast.minRatio must be positive in {profile_path}")
    return UsabilityContrastConfig(min_ratio=min_ratio)


def _parse_tap_target(value: Any, profile_path: Path) -> UsabilityTapTargetConfig:
    if value is None:
        return UsabilityTapTargetConfig(min_px=DEFAULT_TAP_TARGET_MIN_PX)
    if not isinstance(value, dict):
        raise UsabilityProfileValidationError(f"tapTarget must be a mapping in {profile_path}")
    unknown = set(value.keys()) - TAP_TARGET_BLOCK_KEYS
    if unknown:
        joined = ", ".join(sorted(str(key) for key in unknown))
        raise UsabilityProfileValidationError(f"Unknown tapTarget keys in {profile_path}: {joined}")
    min_px_raw = value.get("minPx", DEFAULT_TAP_TARGET_MIN_PX)
    if not isinstance(min_px_raw, (int, float)) or isinstance(min_px_raw, bool):
        raise UsabilityProfileValidationError(f"tapTarget.minPx must be a number in {profile_path}")
    min_px = float(min_px_raw)
    if min_px <= 0:
        raise UsabilityProfileValidationError(f"tapTarget.minPx must be positive in {profile_path}")
    return UsabilityTapTargetConfig(min_px=min_px)


def _parse_focus(value: Any, profile_path: Path) -> UsabilityFocusConfig:
    if value is None:
        return UsabilityFocusConfig(flag_suppressed_outline=DEFAULT_FOCUS_FLAG_SUPPRESSED_OUTLINE)
    if not isinstance(value, dict):
        raise UsabilityProfileValidationError(f"focus must be a mapping in {profile_path}")
    unknown = set(value.keys()) - FOCUS_BLOCK_KEYS
    if unknown:
        joined = ", ".join(sorted(str(key) for key in unknown))
        raise UsabilityProfileValidationError(f"Unknown focus keys in {profile_path}: {joined}")
    flag_raw = value.get("flagSuppressedOutline", DEFAULT_FOCUS_FLAG_SUPPRESSED_OUTLINE)
    if not isinstance(flag_raw, bool):
        raise UsabilityProfileValidationError(
            f"focus.flagSuppressedOutline must be a boolean in {profile_path}"
        )
    return UsabilityFocusConfig(flag_suppressed_outline=flag_raw)
