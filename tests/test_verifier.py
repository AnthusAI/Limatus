from pathlib import Path

from limatus.editorial_style import load_style_profile
from limatus.editorial_verifier import verify_revision


ROOT = Path(__file__).resolve().parents[1]
PROFILE = load_style_profile(ROOT / "features/fixtures/editorial-diagnosis/style-profile.yml")


def test_verifier_recommends_a_clearer_revision_without_mutating_inputs():
    original = "In today's tools, everyone knows this is transformative."
    working = "Inspect latency and cost before choosing a model."

    result = verify_revision(original, working, style_profile=PROFILE)

    assert result["recommendation"] == "accept"
    assert result["threshold"] == 0.05
    assert result["net_improvement"] >= result["threshold"]
    assert result["unsupported_claims"]["working"] <= result["unsupported_claims"]["original"]
    assert {"specificity", "clarity", "audience_fit", "voice_match"} <= set(result["dimensions"])
    assert original == "In today's tools, everyone knows this is transformative."
    assert working == "Inspect latency and cost before choosing a model."


def test_verifier_rejects_new_unsupported_claim_and_reports_evidence():
    original = "Inspect latency and cost before choosing a model."
    working = "This model is always 10x faster and eliminates every failure."

    result = verify_revision(original, working, style_profile=PROFILE)

    assert result["recommendation"] == "reject"
    assert result["unsupported_claims"]["working"] > result["unsupported_claims"]["original"]
    assert any(f["kind"] == "unsupported_claim" for f in result["findings"])
    assert any(f["kind"] == "factual_change_risk" for f in result["findings"])


def test_factual_change_risk_alone_blocks_acceptance():
    result = verify_revision(
        "Inspect latency and cost before choosing a model.",
        "Inspect latency and cost before choosing a model. It handles 99% of requests.",
        style_profile=PROFILE,
    )

    assert result["recommendation"] == "reject"
    assert result["penalties"]["factual_change_risk"]["working"] > 0


def test_verifier_has_no_detector_scores_in_input_or_output():
    result = verify_revision(
        "Inspect latency and cost before choosing a model.",
        "Inspect latency, cost, and failure modes before choosing a model.",
        style_profile=PROFILE,
    )

    rendered = repr(result).lower()
    assert "detector" not in rendered
    assert "ai_score" not in rendered
