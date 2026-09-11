"""Optional OpenAI resolver for compare guideline-alignment (read-only)."""
from __future__ import annotations

import os
import sys
from typing import Any

from .editorial_compare import AlignmentResolver, _guideline_alignment_question
from .editorial_judge import _voice_config_section
from .editorial_llm import call_structured_responses_api
from .editorial_style import DEFAULT_JUDGE_MODEL, LoadedStyleProfile

_ALIGNMENT_SCHEMA_NAME = "editorial_guideline_alignment"
_ALIGNMENT_MAX_OUTPUT_TOKENS = 1200


def _openai_api_key() -> str:
    return os.environ.get("OPENAI_API_KEY", "").strip()


def _alignment_output_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "winnerId": {"type": ["string", "null"]},
            "rationale": {"type": "string"},
        },
        "required": ["winnerId", "rationale"],
        "additionalProperties": False,
    }


def _build_alignment_user_prompt(
    baseline_text: str,
    candidates: list[dict[str, str]],
    style_profile: LoadedStyleProfile,
) -> str:
    voice_section = _voice_config_section(style_profile.profile)
    question = _guideline_alignment_question(style_profile.profile)
    blocks = [
        voice_section,
        f"Alignment question: {question}",
        f"---\nBaseline ({len(baseline_text)} characters):\n{baseline_text}",
    ]
    for entry in candidates:
        text = entry["text"]
        blocks.append(f"---\nCandidate id={entry['id']} ({len(text)} characters):\n{text}")
    return "\n".join(blocks)


def _coerce_winner_id(winner_id: Any, valid_ids: set[str]) -> str | None:
    if winner_id is None:
        return None
    if isinstance(winner_id, str) and winner_id.strip() and winner_id in valid_ids:
        return winner_id
    return None


def openai_guideline_alignment(
    baseline_text: str,
    candidates: list[dict[str, str]],
    style_profile: LoadedStyleProfile,
    *,
    model: str = DEFAULT_JUDGE_MODEL,
) -> dict[str, Any]:
    """Return ``{winnerId, rationale}`` for compare guideline alignment."""
    valid_ids = {entry["id"] for entry in candidates}
    user_prompt = _build_alignment_user_prompt(baseline_text, candidates, style_profile)
    payload = call_structured_responses_api(
        model=model,
        system_prompt=(
            "You compare draft candidates against a style profile. Pick the single candidate "
            "that best matches the profile's audience, tone, and editorial aim relative to the "
            "baseline. winnerId must be exactly one of the provided candidate ids, or null if "
            "none clearly wins. Do not invent scoring weights. Return only JSON matching the schema."
        ),
        user_prompt=user_prompt,
        schema_name=_ALIGNMENT_SCHEMA_NAME,
        schema=_alignment_output_schema(),
        max_output_tokens=_ALIGNMENT_MAX_OUTPUT_TOKENS,
    )
    return {
        "winnerId": _coerce_winner_id(payload.get("winnerId"), valid_ids),
        "rationale": str(payload.get("rationale") or ""),
    }


def _default_alignment_resolver_impl(
    baseline_text: str,
    candidates: list[dict[str, str]],
    style_profile: LoadedStyleProfile,
) -> dict[str, Any]:
    try:
        return openai_guideline_alignment(baseline_text, candidates, style_profile)
    except Exception as exc:
        print(f"limatus: guideline alignment omitted ({exc})", file=sys.stderr)
        return {"winnerId": None, "rationale": ""}


def default_alignment_resolver() -> AlignmentResolver | None:
    """Return the OpenAI alignment resolver when ``OPENAI_API_KEY`` is set."""
    if not _openai_api_key():
        return None
    return _default_alignment_resolver_impl


__all__ = [
    "default_alignment_resolver",
    "openai_guideline_alignment",
]
