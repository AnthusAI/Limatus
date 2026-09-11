from __future__ import annotations

import sys
from pathlib import Path

from behave import given, then, when

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
FIXTURE_ROOT = REPO_ROOT / "features" / "fixtures" / "editorial-headline"
SKILL_PATH = FIXTURE_ROOT / "editorial-rewrite-skill.yml"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from limatus.editorial_headline import generate_headline_options  # noqa: E402
from limatus.editorial_scan import scan_draft  # noqa: E402
from limatus.editorial_style import load_style_profile  # noqa: E402
from limatus.editorial_yaml import frontmatter_block_end, locate_yaml_scalar_span  # noqa: E402


class FakeHeadlineResolver:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        finding = kwargs["finding"]
        span = finding["span"]
        job = kwargs["job"]
        if job == "title":
            replacements = [
                "Latency tradeoffs teams can verify",
                "How to inspect agent rollout risk",
            ]
        else:
            replacements = [
                "A practical summary tied to the revised body.",
                "What changed in the body, in one sentence.",
            ]
        return [
            {
                "patch": {"span": span, "replacement": replacement},
                "reason": f"Fixture {job} option {index + 1}.",
                "factVerificationRequired": False,
                "unresolvedQuestions": [],
            }
            for index, replacement in enumerate(replacements)
        ]


def _collect_leaf_findings(diagnosis: dict) -> list[dict]:
    findings: list[dict] = []
    for key in ("generic_passages", "unsupported_claims", "voice_observations", "required_facts"):
        findings.extend(diagnosis.get(key, []))
    for group in diagnosis.get("repetition_groups", []):
        findings.extend(group.get("members", []))
    return findings


@given("a working copy draft with YAML frontmatter and sloppy body prose")
def step_given_working_copy(context):
    context.working_copy_path = FIXTURE_ROOT / "working-copy.md"
    context.working_copy_snapshot = context.working_copy_path.read_bytes()
    context.working_copy_text = context.working_copy_path.read_text(encoding="utf-8")


@given("a style profile with headline keys for title and standfirst")
def step_given_headline_profile(context):
    context.style_profile_path = FIXTURE_ROOT / "style-profile.yml"
    context.style_profile = load_style_profile(context.style_profile_path)


@when("I scan the working copy for body findings")
def step_when_scan_working_copy(context):
    context.diagnosis = scan_draft(
        context.working_copy_text,
        style_profile=context.style_profile,
    )


@then("no finding span overlaps the frontmatter block")
def step_then_no_frontmatter_findings(context):
    fm_end = frontmatter_block_end(context.working_copy_text)
    assert fm_end > 0
    for finding in _collect_leaf_findings(context.diagnosis):
        span = finding["span"]
        assert span["start"] >= fm_end, finding


@when("I generate headline options for job title on the working copy")
def step_when_title_headline_options(context):
    context.resolver = FakeHeadlineResolver()
    context.options_payload = generate_headline_options(
        context.working_copy_text,
        job="title",
        style_profile=context.style_profile,
        skill_path=SKILL_PATH,
        llm_resolver=context.resolver,
    )
    context.headline_job = "title"


@when("I generate headline options for job subtitle on the working copy")
def step_when_subtitle_headline_options(context):
    context.resolver = FakeHeadlineResolver()
    context.options_payload = generate_headline_options(
        context.working_copy_text,
        job="subtitle",
        style_profile=context.style_profile,
        skill_path=SKILL_PATH,
        llm_resolver=context.resolver,
    )
    context.headline_job = "subtitle"


@then("each title option patch replaces only the title value span")
def step_then_title_patches(context):
    title_span = locate_yaml_scalar_span(context.working_copy_text, "title")
    for option in context.options_payload["findings"][0]["options"]:
        patch = option["patch"]["span"]
        assert patch == {"start": title_span.start, "end": title_span.end}


@then("the subtitle resolver received the current title and article body")
def step_then_subtitle_resolver_context(context):
    assert context.resolver.calls
    call = context.resolver.calls[-1]
    assert call["job"] == "subtitle"
    assert call["current_title"]
    assert "In today's world" in call["body_text"]


@then("each subtitle option patch replaces only the standfirst value span")
def step_then_subtitle_patches(context):
    subtitle_span = locate_yaml_scalar_span(context.working_copy_text, "standfirst")
    for option in context.options_payload["findings"][0]["options"]:
        patch = option["patch"]["span"]
        assert patch == {"start": subtitle_span.start, "end": subtitle_span.end}


@then("the working copy file bytes are unchanged")
def step_then_working_copy_unchanged(context):
    assert context.working_copy_path.read_bytes() == context.working_copy_snapshot
