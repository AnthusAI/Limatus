from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from .editorial_diagnosis import _YAML_FRONTMATTER_RE, _mask_yaml_frontmatter
from .editorial_diagnosis_schema import (
    FINDING_SOURCE_JUDGE,
    RUBRIC_DIMENSIONS,
    stable_finding_id,
)
from .editorial_llm import call_structured_responses_api
from .editorial_style import (
    DEFAULT_JUDGE_MODEL,
    JudgeConfig,
    LoadedStyleProfile,
    ReferenceSample,
    StyleProfile,
)

JUDGE_PROMPT_VERSION = "3"

JUDGE_REFERENCE_EXCERPT_CHARS = 500

DEFAULT_JUDGE_OUTPUT_TOKENS = 16384
MAX_JUDGE_OUTPUT_TOKENS = 32768


def _judge_output_budget(draft_text: str) -> int:
    estimated = max(1, (len(draft_text) + 3) // 4)
    return min(
        MAX_JUDGE_OUTPUT_TOKENS,
        max(DEFAULT_JUDGE_OUTPUT_TOKENS, DEFAULT_JUDGE_OUTPUT_TOKENS + estimated // 4),
    )

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
        "required": ["findings", "rubric"],
        "additionalProperties": False,
    }


def _truncate_reference_excerpt(body: str, max_chars: int) -> str:
    text = body.strip()
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}…"


def _reference_excerpts_section(
    samples: tuple[ReferenceSample, ...],
    max_chars: int = JUDGE_REFERENCE_EXCERPT_CHARS,
) -> str:
    if not samples:
        return ""
    lines = [
        "Reference samples (voice/register only; do not copy verbatim):",
    ]
    for sample in samples:
        excerpt = _truncate_reference_excerpt(sample.body, max_chars)
        lines.append(f'From "{sample.title}": {excerpt}')
    return "\n".join(lines) + "\n"


def _voice_config_section(profile: StyleProfile) -> str:
    tone = "\n".join(f"- {item}" for item in profile.tone)
    sentence_style = "\n".join(f"- {item}" for item in profile.sentence_style)
    structure = "\n".join(f"- {item}" for item in profile.structure)
    prefer = ", ".join(profile.lexicon_prefer[:12])
    avoid = ", ".join(profile.lexicon_avoid[:12])
    evidence = "\n".join(f"- {rule}" for rule in profile.evidence_rules)
    lines = [
        f"Publication: {profile.publication_key}",
        f"Voice: {profile.voice_name}",
        f"Audience: {profile.audience}",
        f"Tone:\n{tone}",
        f"Sentence style:\n{sentence_style}",
    ]
    if profile.editorial_aim:
        lines.append(f"Editorial aim: {profile.editorial_aim}")
    if profile.voice_patterns:
        voice_patterns = "\n".join(f"- {item}" for item in profile.voice_patterns)
        lines.append(f"Voice patterns:\n{voice_patterns}")
    lines.extend(
        [
            f"Structure:\n{structure}",
            f"Prefer lexicon: {prefer}",
            f"Avoid lexicon: {avoid}",
            f"Evidence rules:\n{evidence}",
        ]
    )
    return "\n".join(lines) + "\n"


def yaml_frontmatter_end(draft_text: str) -> int:
    """Return the exclusive end offset of a leading YAML block, or 0."""
    match = _YAML_FRONTMATTER_RE.match(draft_text.replace("\r\n", "\n"))
    return match.end() if match else 0


def drop_frontmatter_findings(
    findings: list[dict[str, Any]], draft_text: str
) -> list[dict[str, Any]]:
    yaml_end = yaml_frontmatter_end(draft_text)
    if yaml_end <= 0:
        return findings
    kept: list[dict[str, Any]] = []
    for finding in findings:
        span = finding.get("span") or {}
        start = span.get("start")
        if isinstance(start, int) and start < yaml_end:
            continue
        kept.append(finding)
    return kept


def scrub_rubric_frontmatter(rubric: dict[str, Any] | None, draft_text: str) -> dict[str, Any] | None:
    if rubric is None:
        return None
    yaml_end = yaml_frontmatter_end(draft_text)
    if yaml_end <= 0:
        return rubric
    scrubbed: dict[str, Any] = {}
    for name, dimension in rubric.items():
        if not isinstance(dimension, dict):
            scrubbed[name] = dimension
            continue
        evidence = dimension.get("evidence")
        if not isinstance(evidence, list):
            scrubbed[name] = dimension
            continue
        kept_evidence = []
        for item in evidence:
            if not isinstance(item, dict):
                continue
            start = item.get("start")
            if isinstance(start, int) and start < yaml_end:
                continue
            kept_evidence.append(item)
        scrubbed[name] = {**dimension, "evidence": kept_evidence}
    return scrubbed


def build_judge_user_prompt(draft_text: str, style_profile: LoadedStyleProfile) -> str:
    voice_section = _voice_config_section(style_profile.profile)
    references = _reference_excerpts_section(style_profile.samples)
    masked = _mask_yaml_frontmatter(draft_text.replace("\r\n", "\n"))
    return (
        f"{voice_section}"
        f"{references}"
        "---\n"
        f"Draft ({len(draft_text)} characters). Leading YAML frontmatter is blanked; "
        "judge the article body. Character offsets still refer to the original file.\n"
        f"{masked}"
    )


def judge_system_prompt() -> str:
    return _system_prompt()


def _system_prompt() -> str:
    return (
        "You are an editorial judge for draft prose. Identify problems the deterministic "
        "profile lane may miss. Do not rewrite the draft. Return only JSON matching the schema. "
        "Findings must cite exact character spans in the draft (start inclusive, end exclusive). "
        "Use kinds such as vague_claim, unsupported_certainty, voice_mismatch, or generic issues. "
        "When judging voice, use sentence style, voice patterns, structure, and reference sample "
        "excerpts as register anchors only; do not copy reference prose. Do not optimize for "
        "detector scores or synthetic imperfection. "
        "This scan is the article-body pass. Do not score or cite the title, standfirst, "
        "description, or other YAML fields; title and subtitle are a later pass. "
        "Rubric scores are integers from 1 (weak) to 5 (strong) with brief evidence spans."
    )


def _is_word_char(ch: str) -> bool:
    return ch.isalnum() or ch in ("'", "\u2019")


def _index_is_word_boundary(text: str, index: int) -> bool:
    draft_len = len(text)
    if index <= 0 or index >= draft_len:
        return True
    inside = text[index]
    outside = text[index - 1]
    if not _is_word_char(inside):
        return True
    if not _is_word_char(outside):
        return True
    return False


def _span_has_word_boundaries(draft_text: str, start: int, end: int) -> bool:
    return _index_is_word_boundary(draft_text, start) and _index_is_word_boundary(
        draft_text, end
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
        if not _span_has_word_boundaries(draft_text, start, end):
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
    user_prompt = build_judge_user_prompt(draft_text, style_profile)
    payload = call_structured_responses_api(
        model=model,
        system_prompt=_system_prompt(),
        user_prompt=user_prompt,
        schema_name="editorial_judge_scan",
        schema=_judge_output_schema(),
        max_output_tokens=_judge_output_budget(draft_text),
    )
    raw_findings = payload.get("findings")
    if not isinstance(raw_findings, list):
        raw_findings = []
    rubric = payload.get("rubric")
    if rubric is not None and not isinstance(rubric, dict):
        rubric = None
    mapped = _map_openai_findings(raw_findings, draft_text, model=model)
    return JudgeLaneResult(
        findings=drop_frontmatter_findings(mapped, draft_text),
        rubric=scrub_rubric_frontmatter(rubric, draft_text),
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
        print(
            "limatus: judge lane skipped (OPENAI_API_KEY is not set) -- "
            "voice, tone, and other judge-dependent findings were not checked",
            file=sys.stderr,
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
