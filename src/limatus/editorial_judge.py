from __future__ import annotations

import os
from typing import Any, Callable, Protocol

from .editorial_diagnosis_schema import (
    FINDING_SOURCE_JUDGE,
    stable_finding_id,
)
from .editorial_style import DEFAULT_JUDGE_MODEL, JudgeConfig, LoadedStyleProfile

JUDGE_PROMPT_VERSION = "1"

JudgeResolver = Callable[
    [str, LoadedStyleProfile, JudgeConfig],
    list[dict[str, Any]],
]


class JudgeResolverProtocol(Protocol):
    def __call__(
        self,
        draft_text: str,
        style_profile: LoadedStyleProfile,
        judge_config: JudgeConfig,
    ) -> list[dict[str, Any]]:
        ...


def make_judge_finding(
    kind: str,
    draft_text: str,
    start: int,
    end: int,
    rationale: str,
    *,
    model: str,
    prompt_version: str = JUDGE_PROMPT_VERSION,
) -> dict[str, Any]:
    return {
        "id": stable_finding_id(kind, draft_text, start, end),
        "kind": kind,
        "excerpt": draft_text[start:end],
        "span": {"start": start, "end": end},
        "rationale": rationale,
        "source": FINDING_SOURCE_JUDGE,
        "model": model,
        "promptVersion": prompt_version,
    }


def default_judge_resolver(
    draft_text: str,
    style_profile: LoadedStyleProfile,
    judge_config: JudgeConfig,
) -> list[dict[str, Any]]:
    """Stub judge lane: no live OpenAI in this release."""
    _ = draft_text, style_profile, judge_config
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        return []
    return []


def resolved_judge_model(judge_config: JudgeConfig) -> str:
    return judge_config.model or DEFAULT_JUDGE_MODEL
