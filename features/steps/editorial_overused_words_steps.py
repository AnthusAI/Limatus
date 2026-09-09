from __future__ import annotations

from behave import given, then

# The "When I diagnose it with the surface-rules profile" step is shared with
# editorial_surface_rules_steps.py -- behave's step registry is global across
# files, so it isn't redefined here.


@given('a draft that uses "actually" far more than ordinary prose would')
def step_given_overused_actually(context):
    context.draft_text = (
        "This is actually a real technique. It actually works in practice, and "
        "teams actually rely on it. The results are actually checkable, which "
        "actually matters, because the alternative is actually just a guess "
        "dressed up as actually being confident."
    )


@given('a draft that uses "really" only twice')
def step_given_ordinary_use(context):
    context.draft_text = (
        "Inspect latency and cost before choosing a model. This really matters "
        "for production traffic, and the failure modes really do compound over "
        "time if nobody checks them."
    )


def _all_findings(diagnosis):
    findings = list(diagnosis.get("generic_passages", []))
    findings += diagnosis.get("unsupported_claims", [])
    findings += diagnosis.get("voice_observations", [])
    findings += diagnosis.get("required_facts", [])
    return findings


@then('diagnosis reports an overused-word finding for "{word}"')
def step_then_reports_overused_word(context, word):
    findings = _all_findings(context.diagnosis)
    assert any(
        finding["kind"] == "overused_word" and f"'{word}'" in finding["rationale"]
        for finding in findings
    ), findings


@then("diagnosis reports no overused-word finding")
def step_then_reports_no_overused_word(context):
    findings = _all_findings(context.diagnosis)
    assert not any(finding["kind"] == "overused_word" for finding in findings), findings
