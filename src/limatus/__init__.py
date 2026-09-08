"""Limatus: a diagnose-and-steer quality loop for AI-generated content."""

__version__ = "0.3.0"

from .sdk import (
    AnnotationFormatError,
    EditorialDiagnosisValidationError,
    EditorialOptionsValidationError,
    LoadedStyleProfile,
    StyleProfileValidationError,
    diagnose,
    verify,
    generate_options,
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
    "verify",
    "generate_options",
    "load_config",
    "record_decision",
    "render_annotations",
]
