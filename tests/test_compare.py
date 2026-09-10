from pathlib import Path

from limatus.editorial_compare import compare_candidates, compare_regression
from limatus.editorial_compare_schema import validate_compare_report
from limatus.editorial_style import load_style_profile

ROOT = Path(__file__).resolve().parents[1]
PROFILE = load_style_profile(ROOT / "features/fixtures/editorial-diagnosis/style-profile.yml")
FIXTURE = ROOT / "features/fixtures/editorial-compare"


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
