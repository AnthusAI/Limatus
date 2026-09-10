from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from behave import given, then, when

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
OPTIONS_FIXTURE = REPO_ROOT / "features" / "fixtures" / "editorial-options"
STYLE_PROFILE_PATH = REPO_ROOT / "features" / "fixtures" / "editorial-diagnosis" / "style-profile.yml"
SKILL_PATH = OPTIONS_FIXTURE / "editorial-rewrite-skill.yml"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from limatus import compare, compose_loop_record, generate_options, load_config  # noqa: E402
from limatus.editorial_loop import candidates_from_options  # noqa: E402


class FakeOptionsResolver:
    def __call__(self, *, draft_text, finding, style_profile, skill, model):
        span = finding["span"]
        return [
            {
                "patch": {"span": span, "replacement": ""},
                "reason": "Delete the empty lead-in.",
                "factVerificationRequired": False,
                "unresolvedQuestions": [],
            },
            {
                "patch": {
                    "span": span,
                    "replacement": "Teams are rethinking how they ship agent workflows.",
                },
                "reason": "Concrete opening.",
                "factVerificationRequired": False,
                "unresolvedQuestions": [],
            },
        ]



FORBIDDEN_OUTPUT_KEYS = {
    "revised_text",
    "rewritten_prose",
    "revisedProse",
    "revisedText",
}


@given("a completed agent shortlist pass")
def step_given_shortlist_pass(context):
    context.draft_text = (OPTIONS_FIXTURE / "article.md").read_text(encoding="utf-8")
    context.scan_json = json.loads((OPTIONS_FIXTURE / "diagnosis.json").read_text(encoding="utf-8"))
    context.decisions = json.loads((OPTIONS_FIXTURE / "empty-leadin-decisions.json").read_text(encoding="utf-8"))
    config = load_config(STYLE_PROFILE_PATH)
    context.options_payload = generate_options(
        context.draft_text,
        config=config,
        diagnosis=context.scan_json,
        decisions=context.decisions,
        skill_path=SKILL_PATH,
        resolver=FakeOptionsResolver(),
    )
    candidates = candidates_from_options(context.draft_text, context.options_payload)
    context.compare_report = compare(context.draft_text, candidates, config=config)


@when("I compose a loop provenance record")
def step_when_compose_loop_record(context):
    context.loop_record = compose_loop_record(
        context.scan_json,
        context.decisions,
        context.options_payload,
        context.compare_report,
        options_model="test-model",
        skill_path=str(SKILL_PATH),
    )


@then("the record includes scan decisions options and compare ranking")
def step_then_record_includes_artifacts(context):
    record = context.loop_record
    assert record["schemaVersion"] == 1
    assert record["scan"]["schemaVersion"] == 1
    assert record["decisions"]
    assert record["options"]["findings"]
    assert record["compareReport"]["candidates"]
    assert record["provenance"]["optionsModel"] == "test-model"
    assert record["provenance"]["skillPath"]


@then("the record does not include rewritten prose")
def step_then_record_no_rewritten_prose(context):
    rendered = json.dumps(context.loop_record)
    for forbidden in FORBIDDEN_OUTPUT_KEYS:
        assert f'"{forbidden}"' not in rendered
    normalized = re.sub(r"[^a-z0-9]", "", rendered.lower())
    assert "detectorscore" not in normalized
