import tempfile
from pathlib import Path

from limatus.editorial_compare import compare_candidates, compare_regression
from limatus.editorial_compare_schema import validate_compare_report
from limatus.editorial_style import StyleProfileValidationError, load_style_profile

ROOT = Path(__file__).resolve().parents[1]
PROFILE = load_style_profile(ROOT / "features/fixtures/editorial-diagnosis/style-profile.yml")
PROFILE_NO_HARD_CONSTRAINTS = load_style_profile(
    ROOT / "features/fixtures/editorial-compare/style-profile-no-hard-constraints.yml"
)
FIXTURE = ROOT / "features/fixtures/editorial-compare"
PORTABLE_PROFILE = ROOT / "features/fixtures/editorial-style-profile/portable-profile.json"


def test_rank_three_candidates_lists_all():
    baseline = (FIXTURE / "baseline.md").read_text(encoding="utf-8")
    candidates = [
        {"id": "best", "text": (FIXTURE / "candidate-best.md").read_text(encoding="utf-8")},
        {"id": "middle", "text": (FIXTURE / "candidate-middle.md").read_text(encoding="utf-8")},
        {"id": "weakest", "text": (FIXTURE / "candidate-weakest.md").read_text(encoding="utf-8")},
    ]
    report = validate_compare_report(
        compare_candidates(baseline, candidates, style_profile=PROFILE, mode="rank")
    )
    assert len(report["candidates"]) == 3
    ranks = sorted(item["rank"] for item in report["candidates"])
    assert ranks == [1, 2, 3]


def test_hard_constraint_demotes_unsupported_candidate():
    baseline = (FIXTURE / "original.md").read_text(encoding="utf-8")
    candidates = [
        {"id": "unsupported", "text": (FIXTURE / "working-unsupported.md").read_text(encoding="utf-8")},
        {"id": "improved", "text": (FIXTURE / "working-improved.md").read_text(encoding="utf-8")},
    ]
    report = compare_candidates(baseline, candidates, style_profile=PROFILE, mode="rank")
    bad = next(item for item in report["candidates"] if item["id"] == "unsupported")
    assert bad["rank"] != 1
    assert bad["hardConstraintViolations"][0]["constraint"] == "unsupported_claims_increase"


def test_regression_compare_mode():
    original = (FIXTURE / "original.md").read_text(encoding="utf-8")
    working = (FIXTURE / "working-improved.md").read_text(encoding="utf-8")
    report = compare_regression(original, working, style_profile=PROFILE)
    assert report["mode"] == "regression"
    assert report["candidates"][0]["id"] == "working"
    assert "arrays" in report["candidates"][0]["alwaysLaneDeltas"]


def test_compare_output_has_no_weights():
    original = (FIXTURE / "original.md").read_text(encoding="utf-8")
    working = (FIXTURE / "working-improved.md").read_text(encoding="utf-8")
    report = compare_regression(original, working, style_profile=PROFILE)
    assert "weights" not in report
    assert "net_improvement" not in report


def test_empty_hard_constraints_allows_unsupported_candidate_for_rank1():
    baseline = (FIXTURE / "original.md").read_text(encoding="utf-8")
    candidates = [
        {"id": "unsupported", "text": (FIXTURE / "working-unsupported.md").read_text(encoding="utf-8")},
        {"id": "improved", "text": (FIXTURE / "working-improved.md").read_text(encoding="utf-8")},
    ]
    report = compare_candidates(
        baseline, candidates, style_profile=PROFILE_NO_HARD_CONSTRAINTS, mode="rank"
    )
    bad = next(item for item in report["candidates"] if item["id"] == "unsupported")
    assert bad["eligibleForRank1"] is True
    assert bad["hardConstraintViolations"] == []


def test_default_profile_compare_hard_constraints():
    assert PROFILE.profile.compare_hard_constraints == ("unsupported_claims_increase",)


def test_unknown_compare_hard_constraint_rejected():
    source = PORTABLE_PROFILE.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "profile.json"
        path.write_text(
            source.replace(
                '"referenceSamples"',
                '"compare": {"hardConstraints": ["unknown_axis"]},\n  "referenceSamples"',
            ),
            encoding="utf-8",
        )
        try:
            load_style_profile(path)
        except StyleProfileValidationError as exc:
            assert "Unknown compare.hardConstraints" in str(exc)
        else:
            raise AssertionError("expected StyleProfileValidationError")


def test_editorial_aim_loaded_from_profile():
    source = PORTABLE_PROFILE.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "profile.json"
        path.write_text(
            source.replace(
                '"publicationKey"',
                '"editorialAim": "Prefer citations over casual certainty.",\n  "publicationKey"',
            ),
            encoding="utf-8",
        )
        loaded = load_style_profile(path)
        assert loaded.profile.editorial_aim == "Prefer citations over casual certainty."


def test_guideline_alignment_from_resolver():
    baseline = (FIXTURE / "original.md").read_text(encoding="utf-8")
    candidates = [
        {"id": "unsupported", "text": (FIXTURE / "working-unsupported.md").read_text(encoding="utf-8")},
        {"id": "improved", "text": (FIXTURE / "working-improved.md").read_text(encoding="utf-8")},
    ]
    candidate_snapshots = [{**entry} for entry in candidates]

    def resolver(base_text, cands, profile):
        assert base_text == baseline
        assert cands == candidates
        assert profile.profile.publication_key == "anthus-blog"
        return {"winnerId": "improved", "rationale": "Better matches the stated editorial aim."}

    report = validate_compare_report(
        compare_candidates(
            baseline,
            candidates,
            style_profile=PROFILE,
            mode="rank",
            alignment_resolver=resolver,
        )
    )
    assert report["guidelineAlignment"]["winnerId"] == "improved"
    assert "audience" in report["guidelineAlignment"]["question"].lower()
    assert candidates == candidate_snapshots


def test_compare_omits_guideline_alignment_without_resolver():
    baseline = (FIXTURE / "original.md").read_text(encoding="utf-8")
    candidates = [
        {"id": "a", "text": (FIXTURE / "working-improved.md").read_text(encoding="utf-8")},
        {"id": "b", "text": (FIXTURE / "working-improved.md").read_text(encoding="utf-8")},
    ]
    report = compare_candidates(baseline, candidates, style_profile=PROFILE, mode="rank")
    assert "guidelineAlignment" not in report
