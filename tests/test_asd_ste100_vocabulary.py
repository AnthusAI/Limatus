from __future__ import annotations

from pathlib import Path

from limatus.editorial_diagnosis import (
    _load_asd_dictionary,
    diagnose_draft,
)
from limatus.editorial_style import load_style_profile

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "features" / "fixtures" / "asd-ste100"


def _load(name: str):
    return load_style_profile(FIXTURE_ROOT / name)


def _asd_findings(diagnosis: dict) -> list[dict]:
    return [f for f in diagnosis["generic_passages"] if f["kind"].startswith("asd_")]


def _kinds(diagnosis: dict) -> set[str]:
    return {f["kind"] for f in _asd_findings(diagnosis)}


def _diagnose(draft: str, profile_name: str = "asd-ste100-profile.yml") -> dict:
    return diagnose_draft(draft, style_profile=_load(profile_name))


def test_packaged_dictionary_is_a_synthetic_starter_seed():
    dictionary = _load_asd_dictionary()
    assert dictionary["approvedWords"]
    assert dictionary["technicalNames"]
    assert dictionary["unapprovedWords"]
    assert dictionary["oneMeaningRules"]
    # The licensed ASD-STE100 word list is not bundled; the seed is synthetic.
    assert dictionary["description"].strip()


def test_unapproved_word_is_flagged_with_its_approved_alternative():
    diagnosis = _diagnose("Utilize the indicator lamp.")
    findings = _asd_findings(diagnosis)
    assert [f["kind"] for f in findings] == ["asd_unapproved_word"]
    assert findings[0]["excerpt"] == "Utilize"
    assert "Approved alternative: 'use'." in findings[0]["rationale"]


def test_approved_words_and_technical_names_pass_clean():
    diagnosis = _diagnose("Remove the filter cover.\nInsert the new filter.\nCheck the oil level.")
    assert _asd_findings(diagnosis) == []


def test_verb_only_word_used_as_a_noun_is_flagged():
    diagnosis = _diagnose("Keep the check in the file.")
    findings = _asd_findings(diagnosis)
    assert [f["kind"] for f in findings] == ["asd_multi_meaning"]
    assert findings[0]["excerpt"] == "check"


def test_verb_usage_of_a_verb_only_word_passes_clean():
    assert _asd_findings(_diagnose("Check the oil level.")) == []


def test_noun_only_word_used_as_an_imperative_verb_is_flagged():
    diagnosis = _diagnose("Power the unit before servicing.")
    kinds = _kinds(diagnosis)
    assert "asd_multi_meaning" in kinds


def test_noun_usage_of_a_noun_only_word_passes_clean():
    assert _asd_findings(_diagnose("The filter housing is a plastic enclosure.")) == []


def test_profile_approved_words_override_the_packaged_dictionary():
    assert _asd_findings(_diagnose("Utilize the service hatch.", "asd-ste100-overrides-profile.yml")) == []


def test_profile_unapproved_words_extend_the_packaged_dictionary():
    diagnosis = _diagnose("Hover over the panel.", "asd-ste100-overrides-profile.yml")
    findings = _asd_findings(diagnosis)
    assert [f["kind"] for f in findings] == ["asd_unapproved_word"]
    assert findings[0]["excerpt"] == "Hover"
    assert "Approved alternative: 'hold'." in findings[0]["rationale"]


def test_disabling_the_approved_words_rule_suppresses_vocabulary_findings(tmp_path):
    source = (FIXTURE_ROOT / "asd-ste100-profile.yml").read_text(encoding="utf-8")
    source = source.replace(
        "asdSte100:\n  enabled: true",
        "asdSte100:\n  enabled: true\n  disableRules: [approvedWords]",
    )
    path = tmp_path / "profile.yml"
    path.write_text(source, encoding="utf-8")
    import shutil

    shutil.copytree(FIXTURE_ROOT / "reference-samples", tmp_path / "reference-samples")
    diagnosis = diagnose_draft("Utilize the indicator lamp.", style_profile=load_style_profile(path))
    assert "asd_unapproved_word" not in _kinds(diagnosis)


def test_disabling_the_one_meaning_rule_suppresses_multi_meaning_findings(tmp_path):
    source = (FIXTURE_ROOT / "asd-ste100-profile.yml").read_text(encoding="utf-8")
    source = source.replace(
        "asdSte100:\n  enabled: true",
        "asdSte100:\n  enabled: true\n  disableRules: [oneMeaningPerWord]",
    )
    path = tmp_path / "profile.yml"
    path.write_text(source, encoding="utf-8")
    import shutil

    shutil.copytree(FIXTURE_ROOT / "reference-samples", tmp_path / "reference-samples")
    diagnosis = diagnose_draft("Keep the check in the file.", style_profile=load_style_profile(path))
    assert "asd_multi_meaning" not in _kinds(diagnosis)


def test_unapproved_word_inside_a_technical_name_is_not_flagged():
    diagnosis = _diagnose("Utilize the power button housing.")
    kinds = _kinds(diagnosis)
    assert "asd_unapproved_word" in kinds
    # 'housing' itself is approved; the phrase 'power button' occupies its span.
    assert _asd_findings(diagnosis)[0]["excerpt"] == "Utilize"


def test_vocabulary_findings_carry_stable_ids_and_valid_spans():
    diagnosis = _diagnose("Utilize the indicator lamp.\nUtilize the service tray.")
    findings = _asd_findings(diagnosis)
    assert len(findings) == 2
    assert findings[0]["id"] != findings[1]["id"]
    for finding in findings:
        assert finding["span"]["end"] > finding["span"]["start"]


def test_unknown_unapproved_word_entry_shape_fails_validation(tmp_path):
    source = (FIXTURE_ROOT / "asd-ste100-profile.yml").read_text(encoding="utf-8")
    source = source.replace(
        "asdSte100:\n  enabled: true",
        "asdSte100:\n  enabled: true\n  unapprovedWords:\n    - word: hover",
    )
    path = tmp_path / "profile.yml"
    path.write_text(source, encoding="utf-8")
    import shutil

    shutil.copytree(FIXTURE_ROOT / "reference-samples", tmp_path / "reference-samples")
    from limatus.editorial_style import StyleProfileValidationError

    import pytest

    with pytest.raises(StyleProfileValidationError):
        load_style_profile(path)