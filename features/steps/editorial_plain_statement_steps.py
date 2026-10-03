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

OPENING_SCREEN_PROFILE_PATH = FIXTURE_ROOT / "style-profile-opening-screen.yml"
NO_PUNCHLINE_PROFILE_PATH = FIXTURE_ROOT / "style-profile-no-punchline.yml"

LONG_SENTENCE_ABOUT_REVIEW = (
    "We put the model in front of eight thousand labelled items and had reviewers agree or disagree "
    "with its verdicts one at a time."
)
LONG_SENTENCE_ABOUT_CALIBRATION = (
    "Out of the box it was about fifteen points overconfident, and after eighty-seven rounds of "
    "feedback the gap was down to three."
)
LONG_SENTENCE_ABOUT_APPROVAL = (
    "At one hundred forty rounds the system proposed one extra question, a person approved it, "
    "and accuracy went from seventy-seven to eighty-seven percent."
)


def _all_findings(diagnosis):
    findings = list(diagnosis.get("generic_passages", []))
    findings += diagnosis.get("unsupported_claims", [])
    findings += diagnosis.get("voice_observations", [])
    findings += diagnosis.get("required_facts", [])
    return findings


def _findings_of_kind(context, kind):
    return [finding for finding in _all_findings(context.diagnosis) if finding["kind"] == kind]


@given("a paragraph where two very short sentences each follow a long sentence")
def step_given_two_drops(context):
    context.draft_text = " ".join(
        [
            LONG_SENTENCE_ABOUT_REVIEW,
            "Its confidence got better fast.",
            LONG_SENTENCE_ABOUT_CALIBRATION,
            "Its accuracy didn't move.",
            "Through those same rounds it sat at seventy-seven percent because the rule the reviewers "
            "followed was never in the questions.",
        ]
    )


@given("a paragraph that ends on a very short sentence after a long one")
def step_given_closing_drop(context):
    context.draft_text = " ".join(
        [
            "The reviewers kept disagreeing with the same kind of verdict.",
            LONG_SENTENCE_ABOUT_APPROVAL,
            "Nobody trained anything.",
        ]
    )


@given("a paragraph that ends on a short sentence with a number in it after a long one")
def step_given_closing_numeric_statement(context):
    context.draft_text = " ".join(
        [
            "The reviewers kept disagreeing with the same kind of verdict.",
            LONG_SENTENCE_ABOUT_APPROVAL,
            "A coin flip gets 0.5.",
        ]
    )


@given("a paragraph that ends on a stand-alone ellipsis after a long sentence")
def step_given_closing_ellipsis(context):
    context.draft_text = " ".join(
        [
            "The reviewers kept disagreeing with the same kind of verdict.",
            LONG_SENTENCE_ABOUT_APPROVAL,
            "...",
        ]
    )


@given("a draft whose opening paragraph starts with an inline emphasis tag")
def step_given_inline_markup_opener(context):
    context.draft_text = "\n".join(
        [
            "<em>Plexus</em> is the platform we run the whole loop on.",
            "",
            "The second paragraph says more about it.",
        ]
    )


@given("a paragraph with a single short sentence between two long ones")
def step_given_single_mid_paragraph_short(context):
    context.draft_text = " ".join(
        [LONG_SENTENCE_ABOUT_REVIEW, "That took a week.", LONG_SENTENCE_ABOUT_CALIBRATION]
    )


@given("a draft whose short lines are headings, list items, and table rows")
def step_given_structural_short_lines(context):
    context.draft_text = "\n\n".join(
        [
            "## The loop",
            LONG_SENTENCE_ABOUT_REVIEW,
            "- Seed it.\n- Score it.",
            "| Version | Accuracy |\n|---|---|\n| v1 | 0.77 |",
            LONG_SENTENCE_ABOUT_CALIBRATION + " " + LONG_SENTENCE_ABOUT_APPROVAL,
        ]
    )


@when("I diagnose it with a profile where punchlineCadence is off")
def step_when_diagnose_without_punchline(context):
    style_profile = load_style_profile(NO_PUNCHLINE_PROFILE_PATH)
    context.diagnosis = diagnose_draft(context.draft_text, style_profile=style_profile)


@then('diagnosis reports punch-line cadence findings for "{first}" and "{second}"')
def step_then_two_punchline_findings(context, first, second):
    excerpts = {finding["excerpt"] for finding in _findings_of_kind(context, "punchline_cadence")}
    assert excerpts == {first, second}, excerpts


@then('diagnosis reports punch-line cadence findings for "{only}"')
def step_then_one_punchline_finding(context, only):
    excerpts = {finding["excerpt"] for finding in _findings_of_kind(context, "punchline_cadence")}
    assert excerpts == {only}, excerpts


@then('the document intent is "{expected}"')
def step_then_document_intent(context, expected):
    assert context.diagnosis["document_intent"] == expected, context.diagnosis["document_intent"]


@then("diagnosis reports no punch-line cadence finding")
def step_then_no_punchline_finding(context):
    findings = _findings_of_kind(context, "punchline_cadence")
    assert not findings, findings


@given('a draft whose opening paragraph uses "decision model" without defining it')
def step_given_undefined_opening_term(context):
    context.draft_text = (
        "Say you've got a hosted decision model grading 8,801 support tickets for you.\n\n"
        "The rest of the piece explains what it got wrong."
    )


@given('a draft whose opening paragraph defines "decision model" where it first appears')
def step_given_defined_opening_term(context):
    context.draft_text = (
        "Say you've got a decision model, an AI model that returns a verdict instead of prose, "
        "grading 8,801 support tickets for you.\n\n"
        "The rest of the piece explains what it got wrong."
    )


@given('a draft that first uses "decision model" in its second paragraph')
def step_given_term_in_second_paragraph(context):
    context.draft_text = (
        "An AI model graded 8,801 support tickets, and reviewers disagreed with 23 percent of its verdicts.\n\n"
        "That model is what we call a decision model."
    )


@given(
    'an MDX draft with an import, a figure, and a heading before an opening paragraph that uses "scorecard"'
)
def step_given_mdx_preamble(context):
    context.draft_text = "\n".join(
        [
            "---",
            'title: "Fixture"',
            "---",
            'import BlogImage from "../components/blog-image"',
            "",
            '<figure className="center-full-image">',
            '  <BlogImage name="cover.png" alt="Four gauges" />',
            "</figure>",
            "",
            "## Opening",
            "",
            "Every month the client gets a scorecard with 4 rows on it.",
            "",
            "The second paragraph uses scorecard again.",
        ]
    )


@given("a draft whose only later digit is inside a link address")
def step_given_digit_only_in_link(context):
    context.draft_text = "\n".join(
        [
            "Reviewers kept disagreeing about the same case.",
            "",
            "See [the write-up](/posts/2025/loop) for the details.",
        ]
    )


@given("a draft whose first number arrives in its second paragraph")
def step_given_number_arrives_late(context):
    context.draft_text = (
        "Reviewers kept disagreeing with the model about the same kind of case.\n\n"
        "One approved question took accuracy from 77 to 87 percent."
    )


@when("I diagnose it with the opening-screen profile")
def step_when_diagnose_opening_screen(context):
    style_profile = load_style_profile(OPENING_SCREEN_PROFILE_PATH)
    context.diagnosis = diagnose_draft(context.draft_text, style_profile=style_profile)


def _opening_findings_mentioning(context, term):
    return [
        finding
        for finding in _findings_of_kind(context, "opening_screen")
        if term.lower() in finding["excerpt"].lower()
    ]


@then('diagnosis reports an opening-screen finding for "{term}"')
def step_then_opening_finding_for_term(context, term):
    findings = _opening_findings_mentioning(context, term)
    assert len(findings) == 1, _findings_of_kind(context, "opening_screen")


@then('diagnosis reports no opening-screen finding for "{term}"')
def step_then_no_opening_finding_for_term(context, term):
    findings = _opening_findings_mentioning(context, term)
    assert not findings, findings


@then("diagnosis reports no opening-screen finding about a missing number")
def step_then_no_opening_missing_number(context):
    findings = [
        finding
        for finding in _findings_of_kind(context, "opening_screen")
        if "no number" in finding["rationale"]
    ]
    assert findings == [], findings


@then("diagnosis reports an opening-screen finding about a missing number")
def step_then_opening_missing_number(context):
    findings = [
        finding
        for finding in _findings_of_kind(context, "opening_screen")
        if "number" in finding["rationale"].lower()
    ]
    assert len(findings) == 1, _findings_of_kind(context, "opening_screen")


@given("a paragraph whose sentences shorten until a three-word closing line")
def step_given_shortening_paragraph(context):
    context.draft_text = (
        "At one hundred forty rounds the system read the disagreements, wrote the unwritten rule in one plain "
        "sentence, and proposed one extra question for the model. A person read the proposal and approved it. "
        "Accuracy went from 77 to 87 percent. Nobody trained anything."
    )


@given("a draft whose short sentences after long ones are a list lead-in, a question, a quotation, a link, and a code fence")
def step_given_non_punchline_short_sentences(context):
    context.draft_text = "\n\n".join(
        [
            LONG_SENTENCE_ABOUT_REVIEW + " Here is what it wrote:",
            LONG_SENTENCE_ABOUT_CALIBRATION + " What does that mean in practice?",
            LONG_SENTENCE_ABOUT_APPROVAL + ' The reviewer said "Ship it."',
            LONG_SENTENCE_ABOUT_REVIEW + " [Here's how an engagement works](/engage).",
            LONG_SENTENCE_ABOUT_CALIBRATION + "\n```\nlimatus scan --draft draft.md\n```",
        ]
    )


@given('a draft whose opening paragraph uses "hosted decision model" without defining it')
def step_given_overlapping_terms(context):
    context.draft_text = "Say you've got a hosted decision model grading 8,801 support tickets for you."


@then("diagnosis reports exactly one opening-screen finding")
def step_then_exactly_one_opening_finding(context):
    findings = _findings_of_kind(context, "opening_screen")
    assert len(findings) == 1, findings
