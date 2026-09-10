"""Small, importable SDK for Limatus's diagnose-and-steer core.

The SDK is deliberately read-only: it loads local configuration, returns
validated findings and candidate patches, and renders annotations. It never
invokes the CLI, mutates a draft, or applies a patch automatically.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from ._util import DEFAULT_EDITORIAL_REWRITE_MODEL
from .editorial_diagnosis import check_rules_only, diagnose_draft, record_finding_decision
from .editorial_scan import scan_draft
from .editorial_diagnosis_schema import (
    EditorialDiagnosisValidationError,
    validate_diagnosis,
)
from .editorial_markup import render_annotated_markus, render_annotated_xml
from .editorial_options_schema import (
    EditorialOptionsValidationError,
    validate_decisions,
)
from .editorial_rewrite_options import generate_rewrite_options, generate_rewrite_suggestions
from .editorial_standfirst import check_standfirst as _check_standfirst
from .editorial_style import LoadedStyleProfile, StyleProfileValidationError, load_style_profile
from .editorial_verifier import verify_revision


class AnnotationFormatError(ValueError):
    """Raised when an unsupported annotation format is requested."""


def load_config(path: str | Path) -> LoadedStyleProfile:
    """Load and validate a portable YAML or JSON style profile."""

    return load_style_profile(path)


def diagnose(
    draft_text: str, *, config: LoadedStyleProfile, surface: str | None = None
) -> dict[str, Any]:
    """Diagnose draft text with a loaded config, without changing the draft.

    ``surface`` selects a named override from the profile's
    ``rules.bySurface`` (for example ``"marketing"`` or ``"legal"``), letting
    one profile apply a looser or disabled contrast cap to specific surfaces
    without maintaining a separate profile per surface.
    """

    if not isinstance(config, LoadedStyleProfile):
        raise EditorialDiagnosisValidationError("config must be a loaded style profile.")
    if not isinstance(draft_text, str):
        raise EditorialDiagnosisValidationError("draft_text must be a string.")
    return scan_draft(draft_text, style_profile=config, surface=surface)


def scan(
    draft_text: str,
    *,
    config: LoadedStyleProfile,
    surface: str | None = None,
    require_judge: bool = False,
) -> dict[str, Any]:
    """Scan draft text with a loaded config (profile lane plus optional judge lane)."""

    if not isinstance(config, LoadedStyleProfile):
        raise EditorialDiagnosisValidationError("config must be a loaded style profile.")
    if not isinstance(draft_text, str):
        raise EditorialDiagnosisValidationError("draft_text must be a string.")
    return scan_draft(
        draft_text,
        style_profile=config,
        surface=surface,
        require_judge=require_judge,
    )


def check_rules(
    text: str, *, config: LoadedStyleProfile, surface: str | None = None
) -> list[dict[str, Any]]:
    """Check only the explicit ``rules`` (banned phrases/intensifiers/
    patterns, no-emoji, contrast cap) against arbitrary text, skipping the
    prose-heuristic checks. Use this for text that isn't real prose -- a
    component source file, a page-content.ts copy string -- where cadence or
    redundancy checks meant for articles would just misfire on code shape.
    """

    if not isinstance(config, LoadedStyleProfile):
        raise EditorialDiagnosisValidationError("config must be a loaded style profile.")
    if not isinstance(text, str):
        raise EditorialDiagnosisValidationError("text must be a string.")
    return check_rules_only(text, style_profile=config, surface=surface)


def verify(
    original_text: str,
    working_text: str,
    *,
    config: LoadedStyleProfile,
    threshold: float = 0.05,
) -> dict[str, Any]:
    """Return an advisory, read-only comparison of an applied working draft."""

    return verify_revision(
        original_text,
        working_text,
        style_profile=config,
        threshold=threshold,
    )


def generate_options(
    draft_text: str,
    *,
    config: LoadedStyleProfile,
    diagnosis: dict[str, Any],
    decisions: list[dict[str, Any]],
    skill_path: str | Path,
    model: str = DEFAULT_EDITORIAL_REWRITE_MODEL,
    resolver: Callable[..., list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Return validated constrained options for findings marked ``rewrite``.

    ``resolver`` is an optional dependency-injection seam for offline callers
    and tests; when omitted the shared core uses its configured LLM resolver.
    """

    if not isinstance(config, LoadedStyleProfile):
        raise EditorialOptionsValidationError("config must be a loaded style profile.")
    validate_diagnosis(diagnosis)
    validate_decisions(decisions)
    return generate_rewrite_options(
        draft_text,
        style_profile=config,
        diagnosis=diagnosis,
        decisions=decisions,
        skill_path=skill_path,
        model=model,
        llm_resolver=resolver,
    )


def suggest_rewrite(
    draft_text: str,
    *,
    config: LoadedStyleProfile,
    diagnosis: dict[str, Any],
    skill_path: str | Path,
    guidance: list[dict[str, Any]] | None = None,
    decisions: list[dict[str, Any]] | None = None,
    model: str = DEFAULT_EDITORIAL_REWRITE_MODEL,
    max_output_tokens: int | None = None,
    resolver: Callable[..., list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Return optional, cohesive document-level rewrite candidates, read-only."""
    if not isinstance(config, LoadedStyleProfile):
        raise EditorialOptionsValidationError("config must be a loaded style profile.")
    validate_diagnosis(diagnosis)
    return generate_rewrite_suggestions(
        draft_text,
        style_profile=config,
        diagnosis=diagnosis,
        skill_path=skill_path,
        guidance=guidance,
        decisions=decisions,
        model=model,
        max_output_tokens=max_output_tokens,
        llm_resolver=resolver,
    )


generate_suggestions = suggest_rewrite


def record_decision(
    decisions: list[dict[str, Any]],
    finding_id: str,
    decision: str,
    *,
    note: str = "",
) -> list[dict[str, Any]]:
    """Append one validated human steering decision without applying it."""

    try:
        updated = record_finding_decision(decisions, finding_id, decision, note)
        return validate_decisions(updated)
    except (ValueError, TypeError) as exc:
        if isinstance(exc, EditorialOptionsValidationError):
            raise
        raise EditorialOptionsValidationError(str(exc)) from exc


def check_standfirst(
    standfirst_text: str,
    *,
    config: LoadedStyleProfile,
    body_text: str = "",
    description: str = "",
) -> dict[str, Any]:
    """Check a candidate standfirst against the profile's ``standfirst`` rules.

    Lets a copywriting agent iterate on a standfirst sentence without writing
    it to the file first, the way an editorial gate iterates on prose before
    it ships. Raises ``ValueError`` if the profile has no ``standfirst`` rules.
    """

    if not isinstance(config, LoadedStyleProfile):
        raise EditorialDiagnosisValidationError("config must be a loaded style profile.")
    return _check_standfirst(
        standfirst_text,
        style_profile=config,
        body_text=body_text,
        description=description,
    )


def render_annotations(
    draft_text: str,
    diagnosis: dict[str, Any],
    *,
    format: str = "markus",
) -> str:
    """Render validated findings as ``markus`` or ``xml`` annotation text."""

    validate_diagnosis(diagnosis)
    if format == "markus":
        return render_annotated_markus(draft_text, diagnosis)
    if format == "xml":
        return render_annotated_xml(draft_text, diagnosis)
    raise AnnotationFormatError("format must be 'markus' or 'xml'.")


__all__ = [
    "AnnotationFormatError",
    "EditorialDiagnosisValidationError",
    "EditorialOptionsValidationError",
    "LoadedStyleProfile",
    "StyleProfileValidationError",
    "diagnose",
    "scan",
    "verify",
    "check_rules",
    "check_standfirst",
    "generate_options",
    "suggest_rewrite",
    "generate_suggestions",
    "load_config",
    "record_decision",
    "render_annotations",
]
