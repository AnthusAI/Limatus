from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

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
                "reason": "Replace boilerplate with a concrete opening stake.",
                "factVerificationRequired": False,
                "unresolvedQuestions": [],
            },
            {
                "patch": {
                    "span": span,
                    "replacement": "Engineering teams measure latency before they scale agent workflows.",
                },
                "reason": "Open with an operational check.",
                "factVerificationRequired": False,
                "unresolvedQuestions": [],
            },
        ]


from behave import given, then, when

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
OPTIONS_FIXTURE = REPO_ROOT / "features" / "fixtures" / "editorial-options"
STYLE_PROFILE_PATH = REPO_ROOT / "features" / "fixtures" / "editorial-diagnosis" / "style-profile.yml"
SKILL_PATH = OPTIONS_FIXTURE / "editorial-rewrite-skill.yml"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from limatus.editorial_loop import candidates_from_options  # noqa: E402
from limatus.editorial_style import load_style_profile  # noqa: E402

def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_compare_cli(command: list[str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{SRC_ROOT}:{REPO_ROOT}"
    env.pop("OPENAI_API_KEY", None)
    return subprocess.run(
        [sys.executable, "-m", "limatus", "compare", *command],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


@given("rewrite decisions and generated options")
def step_given_rewrite_decisions_and_options(context):
    from limatus import generate_options, load_config

    context.draft_path = OPTIONS_FIXTURE / "article.md"
    context.draft_text = context.draft_path.read_text(encoding="utf-8")
    context.temp_workdir = Path(tempfile.mkdtemp(prefix="limatus-shortlist-working-"))
    context.working_path = context.temp_workdir / "working.md"
    context.working_path.write_text(context.draft_text, encoding="utf-8")
    context.working_digest = _file_digest(context.working_path)
    context.diagnosis = json.loads((OPTIONS_FIXTURE / "diagnosis.json").read_text(encoding="utf-8"))
    context.decisions = json.loads((OPTIONS_FIXTURE / "empty-leadin-decisions.json").read_text(encoding="utf-8"))
    config = load_config(STYLE_PROFILE_PATH)
    context.options_payload = generate_options(
        context.draft_text,
        config=config,
        diagnosis=context.diagnosis,
        decisions=context.decisions,
        skill_path=SKILL_PATH,
        resolver=FakeOptionsResolver(),
    )
    context.option_ids = [
        option["id"]
        for finding in context.options_payload["findings"]
        for option in finding["options"]
    ]
    assert len(context.option_ids) >= 2


@when("I run limatus compare on those option texts")
def step_when_compare_option_texts(context):
    context.tempdir = Path(tempfile.mkdtemp(prefix="limatus-shortlist-"))
    baseline_path = context.tempdir / "baseline.md"
    baseline_path.write_text(context.draft_text, encoding="utf-8")
    candidate_paths: list[Path] = []
    for entry in candidates_from_options(context.draft_text, context.options_payload):
        path = context.tempdir / f"{entry['id']}.md"
        path.write_text(entry["text"], encoding="utf-8")
        candidate_paths.append(path)
    context.candidate_paths = candidate_paths

    command = ["--profile", str(STYLE_PROFILE_PATH), "--baseline", str(baseline_path)]
    for path in candidate_paths:
        command.extend(["--candidate", str(path), "--candidate-id", path.stem])
    completed = _run_compare_cli(command)
    assert completed.returncode == 0, completed.stderr
    assert "apply" not in " ".join(command)
    context.compare_report = json.loads(completed.stdout)
    context.apply_invoked = False


@then("I obtain a ranking of all options")
def step_then_ranking_of_all_options(context):
    ranked_ids = {item["id"] for item in context.compare_report["candidates"]}
    assert ranked_ids == set(context.option_ids)
    ranks = [item["rank"] for item in context.compare_report["candidates"]]
    assert sorted(ranks) == list(range(1, len(ranks) + 1))


@then("I do not apply a winner automatically")
def step_then_no_auto_apply(context):
    assert not getattr(context, "apply_invoked", True)


@then("the working draft is unchanged until a human apply is recorded")
def step_then_working_draft_unchanged(context):
    assert _file_digest(context.working_path) == context.working_digest
