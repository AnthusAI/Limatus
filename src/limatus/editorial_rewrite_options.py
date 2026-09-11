from __future__ import annotations

import re
import difflib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import yaml

from .editorial_diagnosis import findings_marked_rewrite
from .editorial_diagnosis_schema import validate_diagnosis
from .editorial_llm import call_structured_responses_api
from .editorial_options_schema import (
    SCHEMA_VERSION,
    stable_option_id,
    stable_candidate_id,
    validate_decisions,
    validate_options,
    validate_suggestions,
)
from .editorial_apply import _coalesce_span_prefix, _replacement_skips_span_prefix
from .editorial_style import LoadedStyleProfile
from ._util import DEFAULT_EDITORIAL_REWRITE_MODEL

DEFAULT_SUGGESTION_OUTPUT_TOKENS = 8000
MAX_SUGGESTION_OUTPUT_TOKENS = 32000

_CONTRACTION_RE = re.compile(r"\b\w+['’](?:t|s|re|ve|ll|d|m)\b", re.IGNORECASE)


def _contraction_voice_warning(excerpt: str, replacement: str) -> str | None:
    """Flag an option that quietly drops a contraction the flagged text was using.

    This is advisory only: it never blocks an option, it just surfaces a hint so a
    human reviewer can catch a register shift the LLM introduced (e.g. "I don't" ->
    "I no longer") that generic style-profile prose doesn't reliably prevent.
    """
    if not replacement.strip():
        return None
    excerpt_contractions = sorted(set(match.lower() for match in _CONTRACTION_RE.findall(excerpt)))
    if not excerpt_contractions:
        return None
    if _CONTRACTION_RE.search(replacement):
        return None
    return (
        "Flagged text used a contraction (" + ", ".join(excerpt_contractions) + "); "
        "this option has none. Confirm the flatter phrasing still sounds like the author."
    )


# These checks intentionally look for instructions or rationales, rather than
# banning words from candidate prose.  An approved article may quite properly
# contain a colloquialism (for example, ``ngl``); the safety boundary is the
# recommendation to add such language, fabricate experience, or optimize for
# an AI detector.
_EVASION_INSTRUCTION_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE | re.DOTALL)
    for pattern in (
        r"\b(?:add|use|include|insert|inject|sprinkle|introduce)\b.{0,80}\b"
        r"(?:slang|colloquialisms?|informal language|fake typos?|mistakes?|imperfections?)\b",
        r"\b(?:add|use|invent|fabricate|claim|say|pretend|make up|manufacture)\b.{0,100}\b"
        r"(?:fake\s+)?(?:experience|anecdote|story|personal detail|memory)\b",
        r"\b(?:to|in order to|so (?:it|the text|this))\b.{0,30}\b"
        r"(?:evade|avoid|bypass|beat|game|fool|lower)\b.{0,80}\b"
        r"(?:ai\s*)?detect(?:or|ion|ability)\b",
        r"\b(?:optimize|target|get below|beat|game|evade|bypass)\b.{0,50}\b"
        r"(?:ai\s*)?detector(?: score|s)?\b",
        r"\bmake\b.{0,50}\b(?:look|sound)\b.{0,30}\b(?:human|less ai)\b",
    )
)

_PREFIX_SKIP_RETRY_INSTRUCTION = (
    "Each replacement must rewrite the entire excerpt from its first character; "
    "do not start at a later sentence. Previous candidates were dropped because "
    "they skipped the beginning of the flagged span."
)

_LLM_OPTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["options"],
    "properties": {
        "options": {
            "type": "array",
            "minItems": 2,
            "maxItems": 3,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "replacement",
                    "reason",
                    "factVerificationRequired",
                    "unresolvedQuestions",
                ],
                "properties": {
                    "replacement": {"type": "string"},
                    "reason": {"type": "string"},
                    "factVerificationRequired": {"type": "boolean"},
                    "unresolvedQuestions": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            },
        },
    },
}


@dataclass(frozen=True)
class EditorialRewriteSkill:
    role: str
    constraints: tuple[str, ...]
    min_options_per_finding: int
    max_options_per_finding: int


OptionsResolver = Callable[..., list[dict[str, Any]]]


def load_rewrite_skill(path: str | Path) -> EditorialRewriteSkill:
    skill_path = Path(path).resolve()
    raw = yaml.safe_load(skill_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Editorial rewrite skill must be a mapping: {skill_path}")
    role = str(raw.get("role") or "Senior copy editor").strip()
    constraints_raw = raw.get("constraints") or []
    if not isinstance(constraints_raw, list) or not constraints_raw:
        raise ValueError(f"Editorial rewrite skill constraints are required: {skill_path}")
    constraints = tuple(str(item).strip() for item in constraints_raw if str(item).strip())
    output = raw.get("output") or {}
    if not isinstance(output, dict):
        output = {}
    min_options = int(output.get("minOptionsPerFinding") or 2)
    max_options = int(output.get("maxOptionsPerFinding") or 3)
    if min_options < 1 or max_options < min_options:
        raise ValueError("Editorial rewrite skill output option counts are invalid.")
    return EditorialRewriteSkill(
        role=role,
        constraints=constraints,
        min_options_per_finding=min_options,
        max_options_per_finding=max_options,
    )


def generate_rewrite_options(
    draft_text: str,
    *,
    style_profile: LoadedStyleProfile,
    diagnosis: dict[str, Any],
    decisions: list[dict[str, Any]],
    model: str = DEFAULT_EDITORIAL_REWRITE_MODEL,
    skill_path: str | Path,
    llm_resolver: OptionsResolver | None = None,
) -> dict[str, Any]:
    validated_diagnosis = validate_diagnosis(diagnosis)
    validated_decisions = validate_decisions(decisions)
    rewrite_findings = findings_marked_rewrite(validated_diagnosis, validated_decisions)
    skill = load_rewrite_skill(skill_path)
    resolver = llm_resolver or _generate_options_with_llm

    findings_payload: list[dict[str, Any]] = []
    for finding in rewrite_findings:
        resolver_kwargs = {
            "draft_text": draft_text,
            "finding": finding,
            "style_profile": style_profile,
            "skill": skill,
            "model": model,
        }
        options = _resolve_rewrite_options_for_finding(
            finding,
            resolver,
            resolver_kwargs,
            use_llm_retry_instruction=llm_resolver is None,
        )
        findings_payload.append({"findingId": finding["id"], "options": options})

    return validate_options({"schemaVersion": SCHEMA_VERSION, "findings": findings_payload})


def generate_rewrite_suggestions(
    draft_text: str,
    *,
    style_profile: LoadedStyleProfile,
    diagnosis: dict[str, Any],
    skill_path: str | Path,
    guidance: list[dict[str, Any]] | None = None,
    decisions: list[dict[str, Any]] | None = None,
    model: str = DEFAULT_EDITORIAL_REWRITE_MODEL,
    max_output_tokens: int | None = None,
    llm_resolver: OptionsResolver | None = None,
) -> dict[str, Any]:
    """Return cohesive document candidates without changing ``draft_text``.

    Guidance and decisions are optional context only. The resolver always receives
    the complete draft, profile, diagnosis, and reference samples, so it can make a
    document-level revision instead of mechanically applying finding patches.
    """
    validated_diagnosis = validate_diagnosis(diagnosis)
    # Guidance may be finding annotations, prose, or decision records. Only the
    # explicit decisions input has a required schema; focusing context is free-form.
    validated_guidance = validate_decisions(decisions) if decisions is not None else (guidance or [])
    skill = load_rewrite_skill(skill_path)
    resolver = llm_resolver or _generate_suggestions_with_llm
    resolver_kwargs = dict(
        draft_text=draft_text,
        style_profile=style_profile,
        diagnosis=validated_diagnosis,
        reference_samples=style_profile.samples,
        guidance=validated_guidance,
        decisions=validated_guidance,
        skill=skill,
        model=model,
    )
    if llm_resolver is None:
        resolver_kwargs["max_output_tokens"] = _suggestion_output_budget(
            draft_text, max_output_tokens
        )
    raw_candidates = resolver(**resolver_kwargs)
    candidates: list[dict[str, Any]] = []
    for entry in raw_candidates:
        if not isinstance(entry, dict):
            continue
        candidate_text = str(entry.get("candidateText", entry.get("replacement", entry.get("text", ""))))
        rationale = str(entry.get("rationale", entry.get("reason", ""))).strip()
        if not candidate_text or not rationale:
            continue
        warnings = [str(item) for item in (entry.get("factualVerificationWarnings") or []) if str(item).strip()]
        fact_required = bool(entry.get("factVerificationRequired", warnings))
        candidates.append({
            "id": str(entry.get("id") or stable_candidate_id(candidate_text, rationale)),
            "candidateText": candidate_text,
            "patch": {"span": {"start": 0, "end": len(draft_text)}, "replacement": candidate_text},
            "diff": _document_diff(draft_text, candidate_text),
            "rationale": rationale,
            "unresolvedQuestions": [str(item) for item in (entry.get("unresolvedQuestions") or []) if str(item).strip()],
            "factualVerificationWarnings": warnings,
            "factVerificationRequired": fact_required,
        })
    payload = validate_suggestions({"schemaVersion": SCHEMA_VERSION, "candidates": candidates})
    if suggestions_contain_evasion_tactics(payload):
        raise ValueError("Rewrite suggestions contain detector-evasion tactics.")
    return payload


# Short alias for callers that treat suggestions as a composable primitive.
generate_suggestions = generate_rewrite_suggestions


def _suggestion_output_budget(draft_text: str, requested: int | None = None) -> int:
    """Choose a bounded budget large enough for a complete document candidate."""
    if requested is not None:
        if not isinstance(requested, int) or isinstance(requested, bool) or requested < 1:
            raise ValueError("max_output_tokens must be a positive integer.")
        if requested > MAX_SUGGESTION_OUTPUT_TOKENS:
            raise ValueError(
                f"max_output_tokens cannot exceed {MAX_SUGGESTION_OUTPUT_TOKENS}."
            )
        return requested
    estimated_draft_tokens = max(1, (len(draft_text) + 3) // 4)
    return min(MAX_SUGGESTION_OUTPUT_TOKENS, max(DEFAULT_SUGGESTION_OUTPUT_TOKENS, estimated_draft_tokens * 2))


def _document_diff(original: str, candidate: str) -> str:
    return "".join(difflib.unified_diff(
        original.splitlines(keepends=True), candidate.splitlines(keepends=True),
        fromfile="original", tofile="candidate",
    ))


def _generate_suggestions_with_llm(**kwargs: Any) -> list[dict[str, Any]]:
    draft_text = kwargs["draft_text"]
    style_profile = kwargs["style_profile"]
    diagnosis = kwargs["diagnosis"]
    skill = kwargs["skill"]
    model = kwargs["model"]
    max_output_tokens = kwargs.get("max_output_tokens", DEFAULT_SUGGESTION_OUTPUT_TOKENS)
    guidance = kwargs.get("guidance") or []
    profile = style_profile.profile
    references = "\n\n".join(
        f'From "{sample.title}": {sample.body[:700]}' for sample in style_profile.samples
    )
    prompt = "\n".join(
        [
            "Create cohesive, document-level rewrite candidates for editorial review.",
            "Rewrite the whole draft when useful; do not return finding-sized patches.",
            f"Skill constraints: {'; '.join(skill.constraints)}",
            f"Audience: {profile.audience}",
            f"Tone: {'; '.join(profile.tone)}",
            f"Sentence style: {'; '.join(profile.sentence_style)}",
            f"Preferred lexicon: {', '.join(profile.lexicon_prefer)}",
            f"Avoided lexicon: {', '.join(profile.lexicon_avoid)}",
            "Diagnostic annotations (guidance, not a mandatory edit sequence):",
            str(diagnosis),
            f"Selected guidance: {guidance}",
            "Reference samples (voice/register only; do not copy verbatim):",
            references,
            "Full draft:",
            draft_text,
            "Return 1 to 3 complete candidate texts. Preserve factual meaning, flag claims needing verification, and never optimize for detector scores or add fake imperfections.",
        ]
    )
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["candidates"],
        "properties": {
            "candidates": {
                "type": "array", "minItems": 1, "maxItems": 3,
                "items": {
                    "type": "object", "additionalProperties": False,
                    "required": ["candidateText", "rationale", "unresolvedQuestions", "factualVerificationWarnings"],
                    "properties": {
                        "candidateText": {"type": "string"},
                        "rationale": {"type": "string"},
                        "unresolvedQuestions": {"type": "array", "items": {"type": "string"}},
                        "factualVerificationWarnings": {"type": "array", "items": {"type": "string"}},
                    },
                },
            }
        },
    }
    result = call_structured_responses_api(
        model=model,
        system_prompt=f"You are a {skill.role}. Return strict JSON only.",
        user_prompt=prompt,
        schema_name="editorial_rewrite_suggestions",
        schema=schema,
        max_output_tokens=max_output_tokens,
    )
    return list(result.get("candidates") or [])


def _resolve_rewrite_options_for_finding(
    finding: dict[str, Any],
    resolver: OptionsResolver,
    resolver_kwargs: dict[str, Any],
    *,
    use_llm_retry_instruction: bool,
) -> list[dict[str, Any]]:
    raw_options = resolver(**resolver_kwargs)
    try:
        options = _normalize_options_for_finding(finding, raw_options)
    except ValueError as exc:
        if "requires at least two rewrite options" not in str(exc):
            raise
        retry_kwargs = dict(resolver_kwargs)
        if use_llm_retry_instruction:
            retry_kwargs["extra_instruction"] = _PREFIX_SKIP_RETRY_INSTRUCTION
        raw_options = resolver(**retry_kwargs)
        options = _normalize_options_for_finding(finding, raw_options)
    return _ensure_empty_leadin_deletion_option(finding, options)


def _generate_options_with_llm(
    *,
    draft_text: str,
    finding: dict[str, Any],
    style_profile: LoadedStyleProfile,
    skill: EditorialRewriteSkill,
    model: str,
    extra_instruction: str | None = None,
) -> list[dict[str, Any]]:
    span = finding["span"]
    prompt = _build_rewrite_prompt(
        draft_text=draft_text,
        finding=finding,
        style_profile=style_profile,
        skill=skill,
        extra_instruction=extra_instruction,
    )
    system_prompt = (
        f"You are a {skill.role} for a technical publication. "
        "Return strict JSON only. Offer constrained patch replacements for the flagged span."
    )
    result = call_structured_responses_api(
        model=model,
        system_prompt=system_prompt,
        user_prompt=prompt,
        schema_name="editorial_rewrite_options",
        schema=_LLM_OPTION_SCHEMA,
    )
    options = result.get("options") or []
    normalized: list[dict[str, Any]] = []
    for entry in options:
        if not isinstance(entry, dict):
            continue
        replacement = str(entry.get("replacement") or "")
        reason = str(entry.get("reason") or "").strip()
        if not reason:
            continue
        normalized.append(
            {
                "id": stable_option_id(finding["id"], replacement, reason),
                "patch": {
                    "span": {"start": span["start"], "end": span["end"]},
                    "replacement": replacement,
                },
                "reason": reason,
                "factVerificationRequired": bool(entry.get("factVerificationRequired")),
                "unresolvedQuestions": [
                    str(question)
                    for question in (entry.get("unresolvedQuestions") or [])
                    if str(question).strip()
                ],
            }
        )
    return normalized


def _local_register_anchor(draft_text: str, span: dict[str, int], radius: int = 220) -> str:
    """Surrounding text around the flagged span, so the model can match local register
    (contractions, sentence-initial conjunctions, person) instead of inferring voice from
    generic style-profile prose alone."""
    start = max(0, span["start"] - radius)
    end = min(len(draft_text), span["end"] + radius)
    before = draft_text[start : span["start"]]
    flagged = draft_text[span["start"] : span["end"]]
    after = draft_text[span["end"] : end]
    return f"{before}[[{flagged}]]{after}"


def _reference_voice_excerpt(style_profile: LoadedStyleProfile, max_chars: int = 500) -> str | None:
    """A short excerpt from the publication's own reference corpus, used only as a
    register anchor for the model — never as source material to copy from."""
    if not style_profile.samples:
        return None
    sample = style_profile.samples[0]
    excerpt = sample.body.strip()[:max_chars]
    return f'From "{sample.title}": "{excerpt}..."'


def _build_rewrite_prompt(
    *,
    draft_text: str,
    finding: dict[str, Any],
    style_profile: LoadedStyleProfile,
    skill: EditorialRewriteSkill,
    extra_instruction: str | None = None,
) -> str:
    profile = style_profile.profile
    span = finding["span"]
    lines = [
        "Generate patch options for one editorial finding.",
        "",
        "Skill constraints:",
        *[f"- {constraint}" for constraint in skill.constraints],
        "",
        "Style profile:",
        f"- Audience: {profile.audience}",
        f"- Tone: {'; '.join(profile.tone)}",
        f"- Sentence style: {'; '.join(profile.sentence_style)}",
    ]
    if profile.editorial_aim:
        lines.append(f"- Editorial aim: {profile.editorial_aim}")
    if profile.voice_patterns:
        lines.append(f"- Voice patterns: {'; '.join(profile.voice_patterns)}")
    lines.extend(
        [
            f"- Prefer lexicon: {', '.join(profile.lexicon_prefer)}",
            f"- Avoid lexicon: {', '.join(profile.lexicon_avoid)}",
            f"- Evidence rules: {'; '.join(profile.evidence_rules)}",
            "",
            f"Finding kind: {finding['kind']}",
            f"Finding rationale: {finding['rationale']}",
            f"Flagged excerpt: {finding['excerpt']}",
            f"Span coordinates: start={span['start']}, end={span['end']}",
            "",
            "Local register anchor (surrounding text; the flagged span is marked [[ ]]):",
            _local_register_anchor(draft_text, span),
            (
                "Match the contraction density, sentence-initial conjunctions, and grammatical "
                "person already present in this surrounding text unless the finding specifically "
                "requires changing them."
            ),
        ]
    )
    reference_excerpt = _reference_voice_excerpt(style_profile)
    if reference_excerpt:
        lines.extend(
            [
                "",
                "Author voice reference (register only — do not copy sentences verbatim):",
                reference_excerpt,
            ]
        )
    lines.extend(
        [
            "",
            "Draft text:",
            draft_text,
            "",
            (
                f"Return {skill.min_options_per_finding} to {skill.max_options_per_finding} options. "
                "Each option must replace only the flagged span. "
                "Do not return a whole-document rewrite. "
                "At least one option must be a minimal edit that changes only what the finding "
                "requires and keeps the surrounding register intact."
            ),
        ]
    )
    if finding["kind"] == "empty_leadin":
        lines.extend(
            [
                "",
                "At least one option must delete the empty lead-in by using an empty replacement string.",
            ]
        )
    if extra_instruction:
        lines.extend(["", extra_instruction])
    return "\n".join(lines)


def _normalize_options_for_finding(
    finding: dict[str, Any],
    options: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    span = finding["span"]
    normalized: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for entry in options:
        if not isinstance(entry, dict):
            continue
        replacement = _coalesce_span_prefix(
            finding["excerpt"],
            str(entry.get("patch", {}).get("replacement", entry.get("replacement", ""))),
        )
        reason = str(entry.get("reason") or "").strip()
        if not reason:
            continue
        if _replacement_skips_span_prefix(finding["excerpt"], replacement):
            continue
        option_id = str(entry.get("id") or stable_option_id(finding["id"], replacement, reason))
        if option_id in seen_ids:
            continue
        seen_ids.add(option_id)
        normalized.append(
            {
                "id": option_id,
                "patch": {
                    "span": {"start": span["start"], "end": span["end"]},
                    "replacement": replacement,
                },
                "reason": reason,
                "factVerificationRequired": bool(entry.get("factVerificationRequired")),
                "unresolvedQuestions": [
                    str(question)
                    for question in (entry.get("unresolvedQuestions") or [])
                    if str(question).strip()
                ],
                "voiceFidelityWarning": _contraction_voice_warning(finding["excerpt"], replacement),
            }
        )
    if len(normalized) < 2:
        raise ValueError(f"Finding {finding['id']} requires at least two rewrite options.")
    return normalized[:3]


def _ensure_empty_leadin_deletion_option(
    finding: dict[str, Any],
    options: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if finding.get("kind") != "empty_leadin":
        return options
    has_deletion = any(not option["patch"]["replacement"].strip() for option in options)
    if has_deletion:
        return options
    deletion = {
        "id": stable_option_id(finding["id"], "", "Delete the empty lead-in."),
        "patch": {
            "span": {"start": finding["span"]["start"], "end": finding["span"]["end"]},
            "replacement": "",
        },
        "reason": "Delete the empty lead-in and let the next sentence carry the opening.",
        "factVerificationRequired": False,
        "unresolvedQuestions": [],
        "voiceFidelityWarning": None,
    }
    return [deletion, *options[:2]]


def options_contain_evasion_tactics(options_payload: dict[str, Any]) -> bool:
    for finding_entry in options_payload.get("findings", []):
        for option in finding_entry.get("options", []):
            replacement = str(option.get("patch", {}).get("replacement", "")).lower()
            reason = str(option.get("reason", "")).lower()
            if _contains_evasion_instruction(replacement, reason):
                return True
    return False


def suggestions_contain_evasion_tactics(payload: dict[str, Any]) -> bool:
    for candidate in payload.get("candidates", []):
        combined = " ".join(
            [
                str(candidate.get("candidateText", "")),
                str(candidate.get("rationale", "")),
                *[str(item) for item in candidate.get("unresolvedQuestions", [])],
            ]
        ).lower()
        if _contains_evasion_instruction(combined):
            return True
    return False


def _contains_evasion_instruction(*parts: str) -> bool:
    """Return whether text prescribes detector evasion tactics.

    Safety applies to model instructions and rationales, not to incidental
    terms in a candidate draft.  Keeping this distinction here prevents an
    approved colloquial register from being rejected merely because it uses a
    word that is sometimes associated with evasion.
    """
    combined = " ".join(str(part) for part in parts)
    return any(pattern.search(combined) for pattern in _EVASION_INSTRUCTION_PATTERNS)
