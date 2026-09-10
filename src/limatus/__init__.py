"""Limatus: a diagnose-and-steer quality loop for AI-generated content."""

__version__ = "0.9.0"

from .sdk import (
    AnnotationFormatError,
    EditorialDiagnosisValidationError,
    EditorialOptionsValidationError,
    LoadedStyleProfile,
    StyleProfileValidationError,
    diagnose,
    scan,
    verify,
    check_rules,
    check_standfirst,
    generate_options,
    suggest_rewrite,
    generate_suggestions,
    load_config,
    record_decision,
    render_annotations,
)

__all__ = [
    "AnnotationFormatError",
    "EditorialDiagnosisValidationError",
    "EditorialOptionsValidationError",
    "LoadedStyleProfile",
    "StyleProfileValidationError",
    "__version__",
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
