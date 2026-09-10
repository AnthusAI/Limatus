from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from behave import given, then, when

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
DIAGNOSIS_FIXTURE_ROOT = REPO_ROOT / "features" / "fixtures" / "editorial-diagnosis"
SCAN_FIXTURE_ROOT = REPO_ROOT / "features" / "fixtures" / "editorial-scan"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from limatus.editorial_diagnosis_schema import FINDING_SOURCE_JUDGE, FINDING_SOURCE_PROFILE  # noqa: E402
from limatus.editorial_judge import JUDGE_PROMPT_VERSION, make_judge_finding, resolved_judge_model  # noqa: E402
from limatus.editorial_scan import scan_draft  # noqa: E402
from limatus.editorial_style import load_style_profile  # noqa: E402

FORBIDDEN_OUTPUT_KEYS = {
    "revised_text",
    "rewritten_prose",
    "revisedProse",
    "revisedText",
    "options",
    "patches",
}


def _run_scan_cli(
    profile_path: Path,
    *,
    draft_path: Path | None = None,
    text: str | None = None,
    output_path: Path | None = None,
    markup_out: Path | None = None,
    xml_out: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    if (draft_path is None) == (text is None):
        raise ValueError("exactly one of draft_path or text is required")

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{SRC_ROOT}:{REPO_ROOT}"
    env.pop("OPENAI_API_KEY", None)
    command = [
        sys.executable,
        "-m",
        "limatus",
        "scan",
        "--profile",
        str(profile_path),
    ]
    if draft_path is not None:
        command.extend(["--draft", str(draft_path)])
    else:
        command.extend(["--text", text])
    if output_path is not None:
        command.extend(["--output", str(output_path)])
    if markup_out is not None:
        command.extend(["--markup-out", str(markup_out)])
    if xml_out is not None:
        command.extend(["--xml-out", str(xml_out)])

    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def _collect_leaf_findings(diagnosis: dict) -> list[dict]:
    findings: list[dict] = []
    for key in ("generic_passages", "unsupported_claims", "voice_observations", "required_facts"):
        findings.extend(diagnosis.get(key, []))
    for group in diagnosis.get("repetition_groups", []):
        findings.extend(group.get("members", []))
    return findings


def _walk_forbidden_keys(value, path=""):
    if isinstance(value, dict):
        for key, nested in value.items():
            current = f"{path}.{key}" if path else key
            assert key not in FORBIDDEN_OUTPUT_KEYS, current
            normalized = re.sub(r"[^a-z0-9]", "", str(key).lower())
            assert not re.search(
                r"(detector|detectorscore|ai_detector|aidetector|perplexity_score|burstiness|ai_score|human_score)",
                normalized,
            ), current
            _walk_forbidden_keys(nested, current)
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _walk_forbidden_keys(nested, f"{path}[{index}]")


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


@given("no judge is configured")
def step_given_no_judge_configured(context):
    context.expect_judge = False


@given("a draft that triggers a profile banned-phrase finding")
def step_given_banned_phrase_draft(context):
    context.draft_path = SCAN_FIXTURE_ROOT / "banned-phrase-draft.md"
    context.profile_path = SCAN_FIXTURE_ROOT / "judge-enabled-profile.yml"
    context.draft_snapshot = context.draft_path.read_bytes()
    context.judge_resolver = _union_test_judge_resolver


@given("a judge is configured that would not flag that phrase")
def step_given_judge_would_not_flag_phrase(context):
    assert context.profile_path.is_file()
    loaded = load_style_profile(context.profile_path)
    assert loaded.profile.judge is not None


@given("a completed scan JSON")
def step_given_completed_scan_json(context):
    profile_path = DIAGNOSIS_FIXTURE_ROOT / "style-profile.yml"
    draft_path = DIAGNOSIS_FIXTURE_ROOT / "sloppy-draft.md"
    completed = _run_scan_cli(profile_path, draft_path=draft_path)
    assert completed.returncode == 0, completed.stderr
    context.diagnosis = json.loads(completed.stdout)


@given("a draft and style profile")
def step_given_draft_and_style_profile_for_markup(context):
    context.draft_path = DIAGNOSIS_FIXTURE_ROOT / "sloppy-draft.md"
    context.profile_path = DIAGNOSIS_FIXTURE_ROOT / "style-profile.yml"
    context.draft_snapshot = context.draft_path.read_bytes()


@when("I run limatus scan")
def step_when_run_limatus_scan(context):
    if getattr(context, "judge_resolver", None) is not None:
        draft_text = context.draft_path.read_text(encoding="utf-8")
        style_profile = load_style_profile(context.profile_path)
        context.diagnosis = scan_draft(
            draft_text,
            style_profile=style_profile,
            judge_resolver=context.judge_resolver,
        )
        context.cli_result = None
        return

    completed = _run_scan_cli(context.profile_path, draft_path=context.draft_path)
    context.cli_result = completed
    if getattr(context, "expect_scan_failure", False):
        return
    assert completed.returncode == 0, completed.stderr
    context.diagnosis = json.loads(completed.stdout)


@when("I run limatus scan with markup-out and xml-out")
def step_when_run_scan_with_markup_exports(context):
    directory = Path(tempfile.mkdtemp(prefix="limatus-scan-markup-"))
    context.markup_path = directory / "annotated.md"
    context.xml_path = directory / "annotated.xml"
    completed = _run_scan_cli(
        context.profile_path,
        draft_path=context.draft_path,
        markup_out=context.markup_path,
        xml_out=context.xml_path,
    )
    context.cli_result = completed
    assert completed.returncode == 0, completed.stderr
    context.markup_text = context.markup_path.read_text(encoding="utf-8")
    context.xml_text = context.xml_path.read_text(encoding="utf-8")


@then("the JSON includes findings with source profile")
def step_then_json_includes_profile_sourced_findings(context):
    findings = _collect_leaf_findings(context.diagnosis)
    assert findings, "expected at least one finding"
    assert any(finding.get("source") == FINDING_SOURCE_PROFILE for finding in findings), findings


@then("the JSON does not include judge findings")
def step_then_json_has_no_judge_findings(context):
    findings = _collect_leaf_findings(context.diagnosis)
    assert not any(finding.get("source") == FINDING_SOURCE_JUDGE for finding in findings), findings


@then("judge findings are absent")
def step_then_judge_findings_are_absent(context):
    step_then_json_has_no_judge_findings(context)


@then("the result does not include revised_text")
def step_then_no_revised_text_in_scan(context):
    _walk_forbidden_keys(context.diagnosis)


@then("the banned-phrase finding is still present with source profile")
def step_then_banned_phrase_still_profile(context):
    findings = _collect_leaf_findings(context.diagnosis)
    matches = [
        finding
        for finding in findings
        if finding.get("source") == FINDING_SOURCE_PROFILE and "seamless" in finding.get("excerpt", "").lower()
    ]
    assert matches, findings


@then("any judge findings are additional")
def step_then_judge_findings_are_additional(context):
    findings = _collect_leaf_findings(context.diagnosis)
    profile_count = sum(1 for finding in findings if finding.get("source") == FINDING_SOURCE_PROFILE)
    judge_count = sum(1 for finding in findings if finding.get("source") == FINDING_SOURCE_JUDGE)
    assert profile_count >= 1
    assert judge_count >= 1


@then("each judge finding records model and promptVersion")
def step_then_judge_findings_have_model_and_prompt_version(context):
    judge_findings = [
        finding
        for finding in _collect_leaf_findings(context.diagnosis)
        if finding.get("source") == FINDING_SOURCE_JUDGE
    ]
    assert judge_findings
    for finding in judge_findings:
        assert isinstance(finding.get("model"), str) and finding["model"].strip()
        assert isinstance(finding.get("promptVersion"), str) and finding["promptVersion"].strip()


@then("every finding has source equal to profile or judge")
def step_then_every_finding_has_valid_source(context):
    for finding in _collect_leaf_findings(context.diagnosis):
        assert finding.get("source") in {FINDING_SOURCE_PROFILE, FINDING_SOURCE_JUDGE}, finding


@then("judge findings have model and promptVersion")
def step_then_judge_findings_have_provenance_fields(context):
    judge_findings = [
        finding
        for finding in _collect_leaf_findings(context.diagnosis)
        if finding.get("source") == FINDING_SOURCE_JUDGE
    ]
    for finding in judge_findings:
        assert finding.get("model")
        assert finding.get("promptVersion")


@then("profile findings do not require a model field")
def step_then_profile_findings_have_no_model(context):
    for finding in _collect_leaf_findings(context.diagnosis):
        if finding.get("source") != FINDING_SOURCE_PROFILE:
            continue
        assert "model" not in finding, finding
        assert "promptVersion" not in finding, finding


@then("the Markdown contains editorial-finding directives")
def step_then_markdown_contains_directives(context):
    assert "editorial-finding" in context.markup_text


@then("the XML lists findings with ids and spans")
def step_then_xml_lists_findings(context):
    assert "<finding" in context.xml_text
    assert 'id="finding-' in context.xml_text
    assert 'start="' in context.xml_text and 'end="' in context.xml_text
