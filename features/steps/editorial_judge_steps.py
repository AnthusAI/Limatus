from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from behave import given, then, when

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
SCAN_FIXTURE_ROOT = REPO_ROOT / "features" / "fixtures" / "editorial-scan"
VOICE_PROMPT_FIXTURE_ROOT = REPO_ROOT / "features" / "fixtures" / "editorial-judge"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from limatus.editorial_diagnosis_schema import FINDING_SOURCE_JUDGE, FINDING_SOURCE_PROFILE  # noqa: E402
from limatus.editorial_judge import (  # noqa: E402
    JUDGE_PROMPT_VERSION,
    build_judge_user_prompt,
    judge_system_prompt,
    make_judge_finding,
    resolved_judge_model,
)
from limatus.editorial_style import DEFAULT_JUDGE_MODEL, load_style_profile  # noqa: E402
from features.steps.editorial_scan_steps import _collect_leaf_findings  # noqa: E402


@given("a profile that enables the OpenAI judge without naming a model")
def step_given_judge_profile_default_model(context):
    context.profile_path = SCAN_FIXTURE_ROOT / "judge-default-model-profile.yml"
    assert context.profile_path.is_file()


@when("I inspect the scan configuration")
def step_when_inspect_scan_configuration(context):
    loaded = load_style_profile(context.profile_path)
    assert loaded.profile.judge is not None
    context.resolved_judge_model = resolved_judge_model(loaded.profile.judge)


@then("the judge model is the documented Terra default")
def step_then_judge_model_is_terra_default(context):
    assert context.resolved_judge_model == DEFAULT_JUDGE_MODEL


@given("a draft and a fake judge resolver that emits one clarity finding")
def step_given_fake_clarity_judge(context):
    context.draft_path = SCAN_FIXTURE_ROOT / "banned-phrase-draft.md"
    context.profile_path = SCAN_FIXTURE_ROOT / "judge-enabled-profile.yml"

    def fake_judge(draft_text, style_profile, judge_config):
        model = resolved_judge_model(judge_config)
        return [
            make_judge_finding(
                "vague_claim",
                draft_text,
                0,
                min(len(draft_text), 20),
                "Clarity: opening lacks a concrete stake for the reader.",
                model=model,
                prompt_version=JUDGE_PROMPT_VERSION,
            )
        ]

    context.judge_resolver = fake_judge


@then("the output includes that judge finding")
def step_then_output_includes_judge_finding(context):
    findings = _collect_leaf_findings(context.diagnosis)
    judge_findings = [f for f in findings if f.get("source") == FINDING_SOURCE_JUDGE]
    assert judge_findings, findings
    assert any("clarity" in f.get("rationale", "").lower() for f in judge_findings)


@then("production code has no LIMATUS_TEST environment hook")
def step_then_no_limatus_test_hooks(context):
    src_root = REPO_ROOT / "src"
    for path in src_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "LIMATUS_TEST" not in text, path


@given("a profile with the OpenAI judge enabled")
def step_given_judge_enabled_profile(context):
    context.profile_path = SCAN_FIXTURE_ROOT / "judge-enabled-profile.yml"
    context.draft_path = SCAN_FIXTURE_ROOT / "banned-phrase-draft.md"


@given("OPENAI_API_KEY is unset")
def step_given_openai_key_unset(context):
    context.unset_openai_key = True


@when("I run limatus scan without require-judge")
def step_when_scan_without_require_judge(context):
    env = os.environ.copy()
    env.pop("OPENAI_API_KEY", None)
    env["PYTHONPATH"] = f"{SRC_ROOT}:{REPO_ROOT}"
    command = [
        sys.executable,
        "-m",
        "limatus",
        "scan",
        "--profile",
        str(context.profile_path),
        "--draft",
        str(context.draft_path),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    context.cli_result = completed
    assert completed.returncode == 0, completed.stderr
    import json

    context.diagnosis = json.loads(completed.stdout)


@then("always-lane findings are present")
def step_then_always_lane_findings_present(context):
    findings = _collect_leaf_findings(context.diagnosis)
    assert any(f.get("source") == FINDING_SOURCE_PROFILE for f in findings), findings


@given("a profile that sets judge provider to anthropic")
def step_given_anthropic_judge_profile(context):
    context.profile_path = SCAN_FIXTURE_ROOT / "judge-anthropic-profile.yml"
    context.draft_path = SCAN_FIXTURE_ROOT / "banned-phrase-draft.md"
    context.expect_scan_failure = True


@then("the command fails with an unsupported-provider error")
def step_then_unsupported_provider_error(context):
    completed = context.cli_result
    assert completed.returncode != 0, completed.stdout
    combined = f"{completed.stdout}\n{completed.stderr}"
    assert "Unsupported judge.provider" in combined or "only openai is supported" in combined


@given("a style profile for judge voice prompt fixtures")
def step_given_judge_voice_prompt_profile(context):
    context.profile_path = VOICE_PROMPT_FIXTURE_ROOT / "voice-prompt-profile.yml"
    assert context.profile_path.is_file()


@when("I build the OpenAI judge user prompt for a short draft")
def step_when_build_judge_user_prompt(context):
    loaded = load_style_profile(context.profile_path)
    context.judge_user_prompt = build_judge_user_prompt("Short draft.", loaded)


@then("the judge user prompt includes the sentence style marker")
def step_then_prompt_includes_sentence_style_marker(context):
    assert "JUDGE_FIXTURE_SENTENCE_STYLE_MARKER" in context.judge_user_prompt


@then("the judge user prompt includes the structure marker")
def step_then_prompt_includes_structure_marker(context):
    assert "JUDGE_FIXTURE_STRUCTURE_MARKER" in context.judge_user_prompt


@then("the judge user prompt includes the voice patterns marker")
def step_then_prompt_includes_voice_patterns_marker(context):
    assert "JUDGE_FIXTURE_VOICE_PATTERNS_MARKER" in context.judge_user_prompt


@then("the judge user prompt includes the short reference sample body")
def step_then_prompt_includes_short_sample(context):
    assert "JUDGE_FIXTURE_SHORT_SAMPLE_BODY_MARKER" in context.judge_user_prompt


@then("the judge user prompt omits the long reference sample tail marker")
def step_then_prompt_omits_long_sample_tail(context):
    assert "JUDGE_FIXTURE_LONG_SAMPLE_TAIL_MARKER" not in context.judge_user_prompt


@when("I read the judge system prompt")
def step_when_read_judge_system_prompt(context):
    context.judge_system_prompt_text = judge_system_prompt()


@then("the judge system prompt forbids rewriting the draft")
def step_then_system_prompt_forbids_rewrite(context):
    assert "Do not rewrite the draft" in context.judge_system_prompt_text


@when('I build the OpenAI judge user prompt for a YAML draft titled "{title}"')
def step_when_build_judge_user_prompt_yaml(context, title):
    loaded = load_style_profile(context.profile_path)
    draft = (
        "---\n"
        f"title: {title}\n"
        "standfirst: A standfirst the judge must not score.\n"
        "---\n\n"
        "Body prose here.\n"
    )
    context.judge_user_prompt = build_judge_user_prompt(draft, loaded)
    context.yaml_title = title


@then('the judge user prompt does not include "{token}"')
def step_then_judge_prompt_omits_token(context, token):
    assert token not in context.judge_user_prompt, context.judge_user_prompt[:500]


@then('the judge user prompt includes the body sentence "{sentence}"')
def step_then_judge_prompt_includes_body(context, sentence):
    assert sentence in context.judge_user_prompt


@then("the judge system prompt says title and subtitle are a later pass")
def step_then_system_prompt_later_headline(context):
    text = context.judge_system_prompt_text.lower()
    assert "later pass" in text
    assert "title" in text
