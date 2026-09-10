from __future__ import annotations

import sys
from pathlib import Path

from behave import given, then, when

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
FIXTURE_ROOT = REPO_ROOT / "features" / "fixtures" / "editorial-surface-rules"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from limatus.editorial_diagnosis import diagnose_draft  # noqa: E402
from limatus.editorial_style import load_style_profile  # noqa: E402

NO_CONTRACTIONS_PROFILE_PATH = FIXTURE_ROOT / "style-profile-no-contractions.yml"


@given('a draft that says "That is the same family, and it does not change."')
def step_given_uncontracted_draft(context):
    context.draft_text = "That is the same family, and it does not change."


@given('a draft that uses the clarifying phrase "the model, that is, the finetuned version"')
def step_given_clarifying_that_is(context):
    context.draft_text = "Inspect the model, that is, the finetuned version, before shipping it."


@when("I diagnose it with a profile where uncontractedForms is off")
def step_when_diagnose_no_contractions_profile(context):
    style_profile = load_style_profile(NO_CONTRACTIONS_PROFILE_PATH)
    context.diagnosis = diagnose_draft(context.draft_text, style_profile=style_profile)


def _all_findings(diagnosis):
    findings = list(diagnosis.get("generic_passages", []))
    findings += diagnosis.get("unsupported_claims", [])
    findings += diagnosis.get("voice_observations", [])
    findings += diagnosis.get("required_facts", [])
    return findings


@then('diagnosis reports uncontracted-form findings for "{first}" and "{second}"')
def step_then_reports_two_uncontracted_findings(context, first, second):
    findings = [f for f in _all_findings(context.diagnosis) if f["kind"] == "uncontracted_form"]
    excerpts = {f["excerpt"] for f in findings}
    assert first in excerpts, (first, excerpts)
    assert second in excerpts, (second, excerpts)


@then("diagnosis reports no uncontracted-form finding")
def step_then_reports_no_uncontracted_finding(context):
    findings = [f for f in _all_findings(context.diagnosis) if f["kind"] == "uncontracted_form"]
    assert not findings, findings
