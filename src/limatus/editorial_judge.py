from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from .editorial_diagnosis_schema import (
    FINDING_SOURCE_JUDGE,
    RUBRIC_DIMENSIONS,
    stable_finding_id,
)
from .editorial_llm import call_structured_responses_api
from .editorial_style import DEFAULT_JUDGE_MODEL, JudgeConfig, LoadedStyleProfile

JUDGE_PROMPT_VERSION = "1"

JudgeResolver = Callable[
    [str, LoadedStyleProfile, JudgeConfig],
    list[dict[str, Any]],
]


class JudgeUnavailableError(RuntimeError):
    """Judge lane was required but could not run (missing key or API failure)."""


class JudgeResolverProtocol(Protocol):
    def __call__(
        self,
        draft_text: str,
        style_profile: LoadedStyleProfile,
        judge_config: JudgeConfig,
    ) -> list[dict[str, Any]]:
        ...


@dataclass(frozen=True)
class JudgeLaneResult:
    findings: list[dict[str, Any]]
    rubric: dict[str, Any] | None = None


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


def resolved_judge_model(judge_config: JudgeConfig) -> str:
    return judge_config.model or DEFAULT_JUDGE_MODEL


def _openai_api_key() -> str:
    return os.environ.get("OPENAI_API_KEY", "").strip()


def _judge_output_schema() -> dict[str, Any]:
    dimension_schema = {
        "type": "object",
        "properties": {
            "score": {"type": "integer"},
            "evidence": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "start": {"type": "integer"},
                        "end": {"type": "integer"},
                        "note": {"type": "string"},
                    },
                    "required": ["start", "end", "note"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["score", "evidence"],
        "additionalProperties": False,
    }
    rubric_properties = {name: dimension_schema for name in RUBRIC_DIMENSIONS}
    return {
        "type": "object",
        "properties": {
            "findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "kind": {"type": "string"},
                        "start": {"type": "integer"},
                        "end": {"type": "integer"},
                        "rationale": {"type": "string"},
                    },
                    "required": ["kind", "start", "end", "rationale"],
                    "additionalProperties": False,
                },
            },
            "rubric": {
                "type": "object",
                "properties": rubric_properties,
                "required": list(RUBRIC_DIMENSIONS),
                "additionalProperties": False,
            },
        },
        "required": ["findings"],
        "additionalProperties": False,
    }


def _profile_summary(style_profile: LoadedStyleProfile) -> str:
    profile = style_profile.profile
    tone = "\n".join(f"- {item}" for item in profile.tone)
    prefer = ", ".join(profile.lexicon_prefer[:12])
    avoid = ", ".join(profile.lexicon_avoid[:12])
    evidence = "\n".join(f"- {rule}" for rule in profile.evidence_rules)
    return (
        f"Publication: {profile.publication_key}\n"
        f"Voice: {profile.voice_name}\n"
        f"Audience: {profile.audience}\n"
        f"Tone:\n{tone}\n"
        f"Prefer lexicon: {prefer}\n"
        f"Avoid lexicon: {avoid}\n"
        f"Evidence rules:\n{evidence}\n"
    )


def _system_prompt() -> str:
    return (
        "You are an editorial judge for draft prose. Identify problems the deterministic "
        "profile lane may miss. Do not rewrite the draft. Return only JSON matching the schema. "
        "Findings must cite exact character spans in the draft (start inclusive, end exclusive). "
        "Use kinds such as vague_claim, unsupported_certainty, voice_mismatch, or generic issues. "
        "Rubric scores are integers from 1 (weak) to 5 (strong) with brief evidence spans."
    )


def _map_openai_findings(
    raw_findings: list[Any],
    draft_text: str,
    *,
    model: str,
) -> list[dict[str, Any]]:
    mapped: list[dict[str, Any]] = []
    draft_len = len(draft_text)
    for entry in raw_findings:
        if not isinstance(entry, dict):
            continue
        kind = str(entry.get("kind") or "").strip()
        rationale = str(entry.get("rationale") or "").strip()
        start = entry.get("start")
        end = entry.get("end")
        if not kind or not rationale:
            continue
        if not isinstance(start, int) or not isinstance(end, int):
            continue
        if start < 0 or end < start or end > draft_len:
            continue
        if start == end and draft_len:
            continue
        mapped.append(
            make_judge_finding(kind, draft_text, start, end, rationale, model=model)
        )
    return mapped


def _call_openai_judge(
    draft_text: str,
    style_profile: LoadedStyleProfile,
    judge_config: JudgeConfig,
) -> JudgeLaneResult:
    model = resolved_judge_model(judge_config)
    user_prompt = (
        f"{_profile_summary(style_profile)}\n"
        f"---\nDraft ({len(draft_text)} characters):\n{draft_text}"
    )
    payload = call_structured_responses_api(
        model=model,
        system_prompt=_system_prompt(),
        user_prompt=user_prompt,
        schema_name="editorial_judge_scan",
        schema=_judge_output_schema(),
        max_output_tokens=2400,
    )
    raw_findings = payload.get("findings")
    if not isinstance(raw_findings, list):
        raw_findings = []
    rubric = payload.get("rubric")
    if rubric is not None and not isinstance(rubric, dict):
        rubric = None
    return JudgeLaneResult(
        findings=_map_openai_findings(raw_findings, draft_text, model=model),
        rubric=rubric,
    )


def run_default_judge_lane(
    draft_text: str,
    style_profile: LoadedStyleProfile,
    judge_config: JudgeConfig,
    *,
    require_judge: bool = False,
) -> JudgeLaneResult:
    if not _openai_api_key():
        if require_judge:
            raise JudgeUnavailableError(
                "OpenAI judge is configured but OPENAI_API_KEY is not set."
            )
        return JudgeLaneResult(findings=[], rubric=None)
    try:
        return _call_openai_judge(draft_text, style_profile, judge_config)
    except Exception as exc:
        if require_judge:
            raise JudgeUnavailableError(f"OpenAI judge request failed: {exc}") from exc
        print(f"limatus: judge lane omitted ({exc})", file=sys.stderr)
        return JudgeLaneResult(findings=[], rubric=None)


def default_judge_resolver(
    draft_text: str,
    style_profile: LoadedStyleProfile,
    judge_config: JudgeConfig,
) -> list[dict[str, Any]]:
    return run_default_judge_lane(draft_text, style_profile, judge_config).findings


def resolve_judge_lane(
    draft_text: str,
    style_profile: LoadedStyleProfile,
    judge_config: JudgeConfig,
    *,
    judge_resolver: JudgeResolver | None = None,
    require_judge: bool = False,
) -> JudgeLaneResult:
    if judge_resolver is not None:
        return JudgeLaneResult(
            findings=judge_resolver(draft_text, style_profile, judge_config),
            rubric=None,
        )
    return run_default_judge_lane(
        draft_text,
        style_profile,
        judge_config,
        require_judge=require_judge,
    )
