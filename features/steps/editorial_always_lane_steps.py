from __future__ import annotations

import json
import sys
from pathlib import Path

from behave import given, then, when

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
ALWAYS_LANE_FIXTURE_ROOT = REPO_ROOT / "features" / "fixtures" / "editorial-always-lane"
DIAGNOSIS_FIXTURE_ROOT = REPO_ROOT / "features" / "fixtures" / "editorial-diagnosis"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from limatus.editorial_style import load_style_profile  # noqa: E402

# Reuse scan CLI helper from editorial_scan_steps (same behave registry).
from editorial_scan_steps import (  # noqa: E402
    _collect_leaf_findings,
    _run_scan_cli,
)


def _finding_fingerprints(diagnosis: dict) -> set[tuple[str, str, int, int]]:
    fingerprints: set[tuple[str, str, int, int]] = set()
    for finding in _collect_leaf_findings(diagnosis):
        span = finding.get("span") or {}
        fingerprints.add(
            (
                str(finding.get("kind") or ""),
                str(finding.get("excerpt") or ""),
                int(span.get("start", 0)),
                int(span.get("end", 0)),
            )
        )
    return fingerprints


def _banned_terms_for_profile(profile_path: Path) -> tuple[str, ...]:
    loaded = load_style_profile(profile_path)
    rules = loaded.profile.rules
    return tuple(rules.banned_phrases) + tuple(rules.banned_intensifiers)


def _findings_for_banned_terms(diagnosis: dict, terms: tuple[str, ...]) -> list[dict]:
    if not terms:
        return []
    lowered_terms = tuple(term.lower() for term in terms)
    hits: list[dict] = []
    for finding in _collect_leaf_findings(diagnosis):
        excerpt = str(finding.get("excerpt") or "").lower()
        if any(term in excerpt for term in lowered_terms):
            hits.append(finding)
    return hits


@given("one draft and two loadable style profiles with different banned phrases")
def step_given_two_profiles_and_draft(context):
    context.draft_path = ALWAYS_LANE_FIXTURE_ROOT / "two-profile-draft.md"
    context.profile_path_a = ALWAYS_LANE_FIXTURE_ROOT / "profile-ban-seamless.yml"
    context.profile_path_b = ALWAYS_LANE_FIXTURE_ROOT / "profile-ban-widgetify.yml"
    assert context.draft_path.is_file()
    assert context.profile_path_a.is_file()
    assert context.profile_path_b.is_file()
    bans_a = _banned_terms_for_profile(context.profile_path_a)
    bans_b = _banned_terms_for_profile(context.profile_path_b)
    assert bans_a and bans_b
    assert set(bans_a) != set(bans_b)


@when("I run limatus scan with each profile and no judge")
def step_when_scan_with_each_profile(context):
    results: list[dict] = []
    profiles = [context.profile_path_a, context.profile_path_b]
    for profile_path in profiles:
        completed = _run_scan_cli(profile_path, draft_path=context.draft_path)
        assert completed.returncode == 0, completed.stderr
        results.append(json.loads(completed.stdout))
    context.scan_results_by_profile = list(zip(profiles, results, strict=True))


@then("the finding sets differ")
def step_then_finding_sets_differ(context):
    profiles_and_results = context.scan_results_by_profile
    assert len(profiles_and_results) == 2
    fps = [_finding_fingerprints(diagnosis) for _, diagnosis in profiles_and_results]
    assert fps[0] != fps[1], (fps[0], fps[1])


@then("each banned-phrase hit matches the profile that was loaded")
def step_then_banned_hits_match_profile(context):
    for profile_path, diagnosis in context.scan_results_by_profile:
        banned = _banned_terms_for_profile(profile_path)
        other_profile = (
            context.profile_path_b
            if profile_path == context.profile_path_a
            else context.profile_path_a
        )
        other_banned = _banned_terms_for_profile(other_profile)
        hits = _findings_for_banned_terms(diagnosis, banned)
        assert hits, f"expected banned-term findings for {profile_path.name}, got none"
        for finding in hits:
            excerpt = str(finding.get("excerpt") or "").lower()
            assert any(term.lower() in excerpt for term in banned), finding
            for other in other_banned:
                assert other.lower() not in excerpt, finding


@given("an Anth.us reference excerpt longer than minWords")
def step_given_anthus_reference_excerpt(context):
    context.draft_path = DIAGNOSIS_FIXTURE_ROOT / "house-voice-density-excerpt.md"
    assert context.draft_path.is_file()


@given("the Anth.us style profile")
def step_given_anthus_style_profile(context):
    context.profile_path = DIAGNOSIS_FIXTURE_ROOT / "density-enabled-profile.yml"
    assert context.profile_path.is_file()
    loaded = load_style_profile(context.profile_path)
    if getattr(context, "draft_path", None):
        from limatus.editorial_text import word_count

        text = context.draft_path.read_text(encoding="utf-8")
        assert word_count(text) >= loaded.profile.density.min_words


@given("a fluffy draft shorter than minWords")
def step_given_fluffy_short_draft(context):
    context.draft_path = ALWAYS_LANE_FIXTURE_ROOT / "fluffy-short-below-minwords.md"
    context.profile_path = DIAGNOSIS_FIXTURE_ROOT / "density-enabled-profile.yml"
    assert context.draft_path.is_file()
    loaded = load_style_profile(context.profile_path)
    from limatus.editorial_text import word_count

    text = context.draft_path.read_text(encoding="utf-8")
    assert word_count(text) < loaded.profile.density.min_words


@when("I run limatus scan with no judge")
def step_when_scan_with_no_judge(context):
    assert getattr(context, "profile_path", None), "style profile must be set before scan"
    draft_path = getattr(context, "draft_path", None)
    assert draft_path is not None
    completed = _run_scan_cli(context.profile_path, draft_path=draft_path)
    assert completed.returncode == 0, completed.stderr
    context.diagnosis = json.loads(completed.stdout)


@then("there is no low_lexical_density finding")
def step_then_no_low_lexical_density(context):
    kinds = {f.get("kind") for f in _collect_leaf_findings(context.diagnosis)}
    assert "low_lexical_density" not in kinds, kinds


@then("there is no high_compressibility finding")
def step_then_no_high_compressibility(context):
    kinds = {f.get("kind") for f in _collect_leaf_findings(context.diagnosis)}
    assert "high_compressibility" not in kinds, kinds
