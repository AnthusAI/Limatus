from __future__ import annotations

import json
import sys
from pathlib import Path

from behave import given, then, when

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
DIAGNOSIS_FIXTURE = REPO_ROOT / "features" / "fixtures" / "editorial-diagnosis"
LOOP_FIXTURE = REPO_ROOT / "features" / "fixtures" / "editorial-loop"
OPTIONS_FIXTURE = REPO_ROOT / "features" / "fixtures" / "editorial-options"
STYLE_PROFILE_PATH = DIAGNOSIS_FIXTURE / "style-profile.yml"
SCAN_PROFILE_PATH = LOOP_FIXTURE / "style-profile-with-judge.yml"
SKILL_PATH = OPTIONS_FIXTURE / "editorial-rewrite-skill.yml"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from limatus.editorial_judge import JUDGE_PROMPT_VERSION, make_judge_finding, resolved_judge_model  # noqa: E402
from limatus.editorial_loop import assert_scan_has_no_steering_decisions  # noqa: E402
from limatus.editorial_scan import scan_draft  # noqa: E402
from limatus.editorial_style import load_style_profile  # noqa: E402


class FakeOptionsResolver:
    def __call__(self, *, draft_text, finding, style_profile, skill, model):
        span = finding["span"]
        return [
            {
                "patch": {"span": span, "replacement": "Teams can verify latency tradeoffs directly."},
                "reason": "Use operational language.",
                "factVerificationRequired": False,
                "unresolvedQuestions": [],
            },
            {
                "patch": {"span": span, "replacement": "The claim needs attributable evidence before publication."},
                "reason": "Flag unsupported certainty.",
                "factVerificationRequired": True,
                "unresolvedQuestions": ["Which source supports the original claim?"],
            },
        ]



def _collect_leaf_findings(diagnosis: dict) -> list[dict]:
    findings: list[dict] = []
    for key in ("generic_passages", "unsupported_claims", "voice_observations", "required_facts"):
        findings.extend(diagnosis.get(key, []))
    return findings


def _collect_finding_ids(diagnosis: dict) -> list[str]:
    return [finding["id"] for finding in _collect_leaf_findings(diagnosis)]


def _union_test_judge_resolver(draft_text, style_profile, judge_config):
    model = resolved_judge_model(judge_config)
    return [
        make_judge_finding(
            "vague_claim",
            draft_text,
            0,
            min(len(draft_text), 24),
            "Judge lane clarity signal for union coverage.",
            model=model,
            prompt_version=JUDGE_PROMPT_VERSION,
        )
    ]


@given("scan JSON with profile and optional judge findings")
def step_given_scan_json_with_judge(context):
    context.draft_path = DIAGNOSIS_FIXTURE / "sloppy-draft.md"
    context.draft_snapshot = context.draft_path.read_bytes()
    context.draft_text = context.draft_path.read_text(encoding="utf-8")
    context.style_profile = load_style_profile(SCAN_PROFILE_PATH)
    context.scan_json = scan_draft(
        context.draft_text,
        style_profile=context.style_profile,
        judge_resolver=_union_test_judge_resolver,
    )
    assert_scan_has_no_steering_decisions(context.scan_json)
    context.finding_ids = _collect_finding_ids(context.scan_json)
    assert len(context.finding_ids) >= 2, "need at least two findings for skip/rewrite"
    judge_findings = [
        finding
        for finding in _collect_leaf_findings(context.scan_json)
        if finding.get("source") == "judge"
    ]
    assert judge_findings, "expected optional judge findings in scan JSON"


@when("I record skip on one finding and rewrite on another")
def step_when_record_skip_and_rewrite(context):
    from limatus import record_decision

    context.decisions = []
    context.skip_finding_id = context.finding_ids[0]
    context.rewrite_finding_id = context.finding_ids[1]
    context.decisions = record_decision(context.decisions, context.skip_finding_id, "skip")
    context.decisions = record_decision(
        context.decisions, context.rewrite_finding_id, "rewrite", note="needs options"
    )


@then("later option generation is eligible only for the rewrite finding")
def step_then_options_only_for_rewrite_finding(context):
    from limatus import generate_options, load_config

    config = load_config(STYLE_PROFILE_PATH)
    options = generate_options(
        context.draft_text,
        config=config,
        diagnosis=context.scan_json,
        decisions=context.decisions,
        skill_path=SKILL_PATH,
        resolver=FakeOptionsResolver(),
    )
    context.options_payload = options
    finding_ids = [entry["findingId"] for entry in options["findings"]]
    assert finding_ids == [context.rewrite_finding_id]
    assert context.skip_finding_id not in finding_ids


@then("the draft is unchanged")
def step_then_draft_is_unchanged(context):
    assert context.draft_path.read_bytes() == context.draft_snapshot
