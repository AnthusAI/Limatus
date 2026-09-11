from __future__ import annotations

from typing import Any, Callable

from ._util import DEFAULT_EDITORIAL_REWRITE_MODEL, hash_short
from .editorial_options_schema import SCHEMA_VERSION, stable_option_id, validate_options
from .editorial_rewrite_options import (
    EditorialRewriteSkill,
    _normalize_options_for_finding,
    load_rewrite_skill,
)
from .editorial_style import LoadedStyleProfile
from .editorial_yaml import locate_yaml_scalar_span, read_yaml_scalar_value, split_frontmatter

HeadlineOptionsResolver = Callable[..., list[dict[str, Any]]]

HEADLINE_FINDING_KINDS = {
    "title": "headline_title",
    "subtitle": "headline_subtitle",
}


def require_headline_pass(style_profile: LoadedStyleProfile) -> None:
    headline = style_profile.profile.headline
    if headline is None:
        raise ValueError(
            "Style profile has no headline pass configured (headline block is omitted)."
        )
    if headline.when == "never":
        raise ValueError(
            "Style profile disables headline passes (headline.when is never)."
        )


def stable_headline_finding_id(job: str, text: str, start: int, end: int) -> str:
    return f"finding-{hash_short(['headline', job, text, start, end])}"


def generate_headline_options(
    working_copy_text: str,
    *,
    job: str,
    style_profile: LoadedStyleProfile,
    skill_path: str,
    model: str = DEFAULT_EDITORIAL_REWRITE_MODEL,
    llm_resolver: HeadlineOptionsResolver | None = None,
) -> dict[str, Any]:
    require_headline_pass(style_profile)
    normalized_job = job.strip().lower()
    if normalized_job not in HEADLINE_FINDING_KINDS:
        raise ValueError("headline job must be 'title' or 'subtitle'.")
    headline = style_profile.profile.headline
    assert headline is not None
    if normalized_job not in headline.order:
        raise ValueError(f"headline job '{normalized_job}' is not listed in profile headline.order.")

    if normalized_job == "title":
        key = headline.title.key
    else:
        key = headline.subtitle.key
        title_key = headline.title.key
        try:
            title_value = read_yaml_scalar_value(working_copy_text, title_key)
        except ValueError as exc:
            raise ValueError(
                f"Subtitle headline options require a non-empty '{title_key}' in the working copy."
            ) from exc
        if not title_value.strip():
            raise ValueError(
                f"Subtitle headline options require a non-empty '{title_key}' in the working copy."
            )

    span = locate_yaml_scalar_span(working_copy_text, key)
    _frontmatter, body = split_frontmatter(working_copy_text)
    if _frontmatter is None:
        raise ValueError("Headline options require a leading YAML frontmatter block.")

    kind = HEADLINE_FINDING_KINDS[normalized_job]
    finding = {
        "id": stable_headline_finding_id(normalized_job, working_copy_text, span.start, span.end),
        "kind": kind,
        "source": "headline",
        "rationale": f"Headline pass for {normalized_job} ({key}).",
        "excerpt": working_copy_text[span.start : span.end],
        "span": {"start": span.start, "end": span.end},
    }
    skill = load_rewrite_skill(skill_path)
    resolver = llm_resolver or _generate_headline_options_with_llm
    current_title = None
    if normalized_job == "subtitle":
        current_title = read_yaml_scalar_value(working_copy_text, headline.title.key)
    resolver_kwargs = {
        "working_copy_text": working_copy_text,
        "job": normalized_job,
        "finding": finding,
        "style_profile": style_profile,
        "skill": skill,
        "model": model,
        "body_text": body,
        "yaml_key": key,
        "current_title": current_title,
    }
    raw_options = resolver(**resolver_kwargs)
    options = _normalize_options_for_finding(finding, raw_options)
    return validate_options(
        {
            "schemaVersion": SCHEMA_VERSION,
            "findings": [{"findingId": finding["id"], "options": options}],
        }
    )


def _generate_headline_options_with_llm(
    *,
    working_copy_text: str,
    job: str,
    finding: dict[str, Any],
    style_profile: LoadedStyleProfile,
    skill: EditorialRewriteSkill,
    model: str,
    body_text: str,
    yaml_key: str,
    current_title: str | None,
    **_: Any,
) -> list[dict[str, Any]]:
    from .editorial_llm import call_structured_responses_api
    from .editorial_rewrite_options import _LLM_OPTION_SCHEMA

    profile = style_profile.profile
    span = finding["span"]
    lines = [
        f"Generate {job} options for one YAML frontmatter field.",
        f"Replace only the scalar value for key '{yaml_key}'.",
        "Do not rewrite the article body or other frontmatter keys.",
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
    if job == "title":
        lines.extend(
            [
                "",
                "This field names the piece. Return a title, not a summary paragraph.",
            ]
        )
    if job == "subtitle":
        role = "articleSummary"
        if profile.headline is not None:
            role = profile.headline.subtitle.role
        lines.extend(
            [
                "",
                f"This field is the subtitle ({role}): a short summary of the entire article.",
                "It must sit under the title already chosen. Do not return another title or headline.",
                "Do not copy the title. Summarize the body in a few sentences the reader can use as a dek.",
            ]
        )
    lines.extend(
        [
            "",
            f"Current {yaml_key} excerpt: {finding['excerpt']}",
            f"Span coordinates: start={span['start']}, end={span['end']}",
            "",
            "Article body (after YAML frontmatter):",
            body_text.strip() or "(empty)",
        ]
    )
    if current_title is not None:
        title_key = profile.headline.title.key if profile.headline else "title"
        lines.extend(
            [
                "",
                f"Current title ({title_key}) — already applied; the subtitle must follow it:",
                current_title,
            ]
        )
    lines.extend(
        [
            "",
            (
                f"Return {skill.min_options_per_finding} to {skill.max_options_per_finding} options. "
                "Each replacement must be only the new scalar text for this key, not YAML syntax."
            ),
        ]
    )
    prompt = "\n".join(lines)
    result = call_structured_responses_api(
        model=model,
        system_prompt=f"You are a {skill.role}. Return strict JSON only.",
        user_prompt=prompt,
        schema_name="editorial_headline_options",
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
