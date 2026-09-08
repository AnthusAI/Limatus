from __future__ import annotations

import sys
from pathlib import Path

from behave import given, then, when

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
FIXTURE_ROOT = REPO_ROOT / "features" / "fixtures" / "editorial-surface-rules"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from limatus.editorial_standfirst import check_standfirst  # noqa: E402
from limatus.editorial_style import load_style_profile  # noqa: E402

PROFILE_PATH = FIXTURE_ROOT / "style-profile.yml"


@given("a standfirst that fits the shape rules and names no strangers")
def step_given_clean_standfirst(context):
    context.standfirst_text = "Chatticus ships with real specifics, not vague promises."
    context.body_text = ""
    context.description = ""


@given("a standfirst with three sentences")
def step_given_three_sentence_standfirst(context):
    context.standfirst_text = "This works. It really works. Everyone loves it."
    context.body_text = ""
    context.description = ""


@given("a standfirst naming a person absent from the article body")
def step_given_standfirst_naming_a_stranger(context):
    context.standfirst_text = "This idea from Harari changes what readers should expect."
    context.body_text = ""
    context.description = ""


@given("a standfirst that uses an insider term")
def step_given_standfirst_with_insider_term(context):
    context.standfirst_text = "This tool checks your API before anything ships."
    context.body_text = ""
    context.description = ""


@given("a standfirst that closely repeats its description")
def step_given_standfirst_repeating_description(context):
    context.standfirst_text = "The tool checks your work before you ship it."
    context.body_text = ""
    context.description = "The tool checks your work before you ship it live."


@when("I check the standfirst against the surface-rules profile")
def step_when_check_standfirst(context):
    style_profile = load_style_profile(PROFILE_PATH)
    context.result = check_standfirst(
        context.standfirst_text,
        style_profile=style_profile,
        body_text=context.body_text,
        description=context.description,
    )


@then("no standfirst findings are reported")
def step_then_no_findings(context):
    assert context.result["findings"] == [], context.result["findings"]


@then("a standfirst finding mentions the sentence cap")
def step_then_finding_mentions_sentence_cap(context):
    findings = context.result["findings"]
    assert any("cap is" in finding["rationale"] and "sentence" in finding["rationale"] for finding in findings), findings


@then("a standfirst finding mentions a name the reader has not met")
def step_then_finding_mentions_stranger_name(context):
    findings = context.result["findings"]
    assert any("only the headline to place it by" in finding["rationale"] for finding in findings), findings


@then("a standfirst finding mentions insider vocabulary")
def step_then_finding_mentions_insider_term(context):
    findings = context.result["findings"]
    assert any("plain English only to somebody who already works in this" in finding["rationale"] for finding in findings), findings


@then("a standfirst finding mentions the description overlap")
def step_then_finding_mentions_description_overlap(context):
    findings = context.result["findings"]
    assert any("stopped doing its own job" in finding["rationale"] for finding in findings), findings
