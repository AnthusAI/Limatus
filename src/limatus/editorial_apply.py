"""Explicit, anchored application of one human-selected editorial patch.

This module is intentionally separate from diagnosis and option generation.  The
caller must name the working copy, finding, option (or deletion), and exact
anchor.  No operation ever writes the original draft.
"""

from __future__ import annotations

import difflib
import hashlib
import json
from pathlib import Path
from typing import Any

from .editorial_options_schema import validate_options


SCHEMA_VERSION = 1


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _selected_option(options: dict[str, Any], finding_id: str, option_id: str) -> dict[str, Any]:
    validated = validate_options(options)
    for finding in validated["findings"]:
        if finding["findingId"] != finding_id:
            continue
        for option in finding["options"]:
            if option["id"] == option_id:
                return option
        raise ValueError(f"Option {option_id!r} is not present for finding {finding_id!r}.")
    raise ValueError(f"Finding {finding_id!r} is not present in options.")


def apply_patch(
    *,
    original_path: str | Path,
    working_copy_path: str | Path,
    options: dict[str, Any],
    finding_id: str,
    anchor: str,
    option_id: str | None = None,
    delete: bool = False,
    change_log_path: str | Path | None = None,
) -> dict[str, Any]:
    """Apply one selected replacement or deletion to an explicit working copy.

    The exact anchor must match the patch span in the current working copy.  A
    mismatch (including a stale offset or conflicting prior edit) fails before
    any write occurs.  ``delete`` is an explicit human choice and cannot be
    combined with ``option_id``.
    """

    original = Path(original_path).resolve()
    working = Path(working_copy_path).resolve()
    if original == working:
        raise ValueError("Original draft and working copy must be different paths.")
    if change_log_path is not None:
        log_path = Path(change_log_path).resolve()
        if log_path in {original, working}:
            raise ValueError("Change log must be a separate path from the draft and working copy.")
    if not original.is_file():
        raise ValueError(f"Original draft not found: {original}")
    if not working.is_file():
        raise ValueError(f"Working copy not found: {working}")
    if not isinstance(anchor, str) or not anchor:
        raise ValueError("An exact non-empty anchor is required.")
    if option_id is None:
        raise ValueError("An explicit option_id is required for the selected finding.")

    original_bytes = original.read_bytes()
    working_bytes = working.read_bytes()
    original_text = original_bytes.decode("utf-8")
    working_text = working_bytes.decode("utf-8")
    option = _selected_option(options, finding_id, option_id or "")
    span = option["patch"]["span"]
    start, end = span["start"], span["end"]
    if end > len(working_text):
        raise ValueError("Patch anchor is stale: span is outside the current working copy.")
    if working_text[start:end] != anchor:
        raise ValueError("Patch anchor is stale or conflicting with the current working copy.")

    replacement = option["patch"]["replacement"]
    if delete and replacement != "":
        raise ValueError("The selected deletion option must have an empty replacement.")
    updated_text = working_text[:start] + replacement + working_text[end:]
    updated_bytes = updated_text.encode("utf-8")
    entry = {
        "findingId": finding_id,
        "optionId": option_id,
        "action": "delete" if replacement == "" else "replace",
        "span": {"start": start, "end": end},
        "anchor": anchor,
        "replacement": replacement,
        "workingCopySha256Before": _sha256(working_bytes),
        "workingCopySha256After": _sha256(updated_bytes),
    }
    # All checks and log serialization happen before touching the working copy.
    log = {
        "schemaVersion": SCHEMA_VERSION,
        "originalPath": str(original),
        "workingCopyPath": str(working),
        "originalSha256": _sha256(original_bytes),
        "changes": [entry],
    }
    if change_log_path is not None:
        log_path.write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")
    working.write_bytes(updated_bytes)
    return log


def render_diff(original_path: str | Path, working_copy_path: str | Path) -> str:
    """Return a stable unified diff without changing either file."""

    original = Path(original_path).resolve()
    working = Path(working_copy_path).resolve()
    original_lines = original.read_text(encoding="utf-8").splitlines(keepends=True)
    working_lines = working.read_text(encoding="utf-8").splitlines(keepends=True)
    return "".join(
        difflib.unified_diff(
            original_lines,
            working_lines,
            fromfile=str(original),
            tofile=str(working),
        )
    )
