from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONTRAST_MIN_RATIO = 4.5

USABILITY_PROFILE_TOP_LEVEL_KEYS = frozenset({"contrast"})
CONTRAST_BLOCK_KEYS = frozenset({"minRatio"})


class UsabilityProfileValidationError(ValueError):
    """Raised when a usability profile document fails validation."""


@dataclass(frozen=True)
class UsabilityContrastConfig:
    min_ratio: float


@dataclass(frozen=True)
class UsabilityProfile:
    contrast: UsabilityContrastConfig


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
    return LoadedUsabilityProfile(
        path=resolved,
        profile=UsabilityProfile(contrast=contrast),
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
