from __future__ import annotations

import json
import sys
from pathlib import Path

from behave import given, then, when

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"


def _apply_module():
    if str(SRC_ROOT) not in sys.path:
        sys.path.insert(0, str(SRC_ROOT))
    from limatus.editorial_apply import apply_patch, render_diff

    return apply_patch, render_diff


@given("an original draft, a separate working copy, and one options payload")
def step_given_apply_bundle(context):
    import tempfile

    context.tempdir = Path(tempfile.mkdtemp(prefix="limatus-apply-"))
    context.original_path = context.tempdir / "original.md"
    context.working_path = context.tempdir / "working.md"
    context.log_path = context.tempdir / "changes.json"
    context.original_text = "The platform will revolutionize workflows.\n"
    context.original_path.write_text(context.original_text, encoding="utf-8")
    context.working_path.write_text(context.original_text, encoding="utf-8")
    context.options = {
        "schemaVersion": 1,
        "findings": [{
            "findingId": "finding-a6b95ac741d27015",
            "options": [{
                "id": "option-0123456789abcdef",
                "patch": {"span": {"start": 18, "end": 31}, "replacement": "improve"},
                "reason": "Use an operational verb.",
                "factVerificationRequired": False,
                "unresolvedQuestions": [],
            }],
        }],
    }


@when("I apply the selected option with its exact anchor")
def step_when_apply_option(context):
    apply_patch, render_diff = _apply_module()
    context.result = apply_patch(
        original_path=context.original_path,
        working_copy_path=context.working_path,
        options=context.options,
        finding_id="finding-a6b95ac741d27015",
        option_id="option-0123456789abcdef",
        anchor="revolutionize",
        change_log_path=context.log_path,
    )
    context.diff = render_diff(context.original_path, context.working_path)


@then("only the selected span changes in the working copy")
def step_then_only_selected_span(context):
    assert context.working_path.read_text(encoding="utf-8") == "The platform will improve workflows.\n"


@then("the original draft is unchanged")
def step_then_original_unchanged(context):
    assert context.original_path.read_text(encoding="utf-8") == context.original_text


@then("a machine-readable change log records the selected option")
def step_then_log_records_option(context):
    payload = json.loads(context.log_path.read_text(encoding="utf-8"))
    assert payload["changes"][0]["optionId"] == "option-0123456789abcdef"
    assert payload["changes"][0]["action"] == "replace"


@then("the original-versus-working diff contains the selected replacement")
def step_then_diff_contains_replacement(context):
    assert "-The platform will revolutionize workflows." in context.diff
    assert "+The platform will improve workflows." in context.diff


@when("I apply the selected option with a stale anchor")
def step_when_apply_stale(context):
    apply_patch, _ = _apply_module()
    context.before = context.working_path.read_bytes()
    try:
        apply_patch(
            original_path=context.original_path,
            working_copy_path=context.working_path,
            options=context.options,
            finding_id="finding-a6b95ac741d27015",
            option_id="option-0123456789abcdef",
            anchor="old-word",
        )
    except ValueError as exc:
        context.error = str(exc)
    else:
        raise AssertionError("stale anchor unexpectedly applied")


@then("the apply fails safely")
def step_then_apply_fails(context):
    assert "anchor" in context.error.lower()


@then("the working copy is unchanged")
def step_then_working_unchanged(context):
    assert context.working_path.read_bytes() == context.before
