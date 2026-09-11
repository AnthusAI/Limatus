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

def test_reworded_sentence_with_added_citation_is_not_a_deleted_claim():
    original = "He had never spat in a tube."
    working = (
        "He had never spat in a tube, according to court records from the case."
    )

    result = verify_revision(original, working, style_profile=PROFILE)

    kinds = {f["kind"] for f in result["findings"]}
    assert "deleted_claim" not in kinds, result["findings"]


def test_adding_a_citation_to_an_existing_number_is_not_a_new_risk():
    original = "The study found an 85% recall rate."
    working = "The study found an [85% recall rate](https://example.com/study)."

    result = verify_revision(original, working, style_profile=PROFILE)

    kinds = {f["kind"] for f in result["findings"]}
    assert "factual_change_risk" not in kinds, result["findings"]
    assert result["penalties"]["factual_change_risk"]["working"] == 0.0


def test_genuinely_different_claim_is_still_a_deleted_claim():
    original = "The report found a 68% recall rate at 90% precision."
    working = "The team declined to publish a recall figure."

    result = verify_revision(original, working, style_profile=PROFILE)

    kinds = {f["kind"] for f in result["findings"]}
    assert "deleted_claim" in kinds, result["findings"]

