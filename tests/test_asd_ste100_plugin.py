from __future__ import annotations

import copy
import shutil
from pathlib import Path

import pytest

from limatus.editorial_diagnosis import diagnose_draft
from limatus.editorial_diagnosis_schema import (
    ASD_STE100_FINDING_KINDS,
    EditorialDiagnosisValidationError,
    validate_diagnosis,
)
from limatus.editorial_style import (
    DEFAULT_ASD_STE100_MAX_WORDS_DESCRIPTION,
    DEFAULT_ASD_STE100_MAX_WORDS_PROCEDURE,
    DEFAULT_DIAGNOSE_CHECKS,
    StyleProfileValidationError,
    load_style_profile,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "features" / "fixtures" / "asd-ste100"

BOT_SLOP_KINDS = {
    "empty_leadin",
    "list_shaped_prose",
    "vague_claim",
    "overused_word",
    "uncontracted_form",
    "unsupported_certainty",
    "uniform_cadence",
    "punchline_cadence",
    "opening_screen",
    "voice_mismatch",
    "missing_attribution",
    "redundancy",
}

SLOPPY_DRAFT = (FIXTURE_ROOT / "sloppy-draft.md").read_text(encoding="utf-8")
PROCEDURE_DRAFT = (FIXTURE_ROOT / "procedure-draft.md").read_text(encoding="utf-8")


def _load(name: str):
    return load_style_profile(FIXTURE_ROOT / name)


def _kinds(diagnosis: dict) -> set[str]:
    kinds: set[str] = set()
    for key in ("generic_passages", "unsupported_claims", "voice_observations", "required_facts"):
        for finding in diagnosis.get(key, []):
            kinds.add(finding["kind"])
    for group in diagnosis.get("repetition_groups", []):
        kinds.add(group["kind"])
    return kinds


def test_default_checks_leave_the_ste_rule_set_off():
    assert DEFAULT_DIAGNOSE_CHECKS["asdSte100"] is False


def test_default_limit_constants_match_the_spec():
    assert DEFAULT_ASD_STE100_MAX_WORDS_PROCEDURE == 20
    assert DEFAULT_ASD_STE100_MAX_WORDS_DESCRIPTION == 25


def test_ste_profile_parses_defaults():
    profile = _load("asd-ste100-profile.yml").profile
    config = profile.asd_ste100
    assert config is not None
    assert config.enabled is True
    assert config.exclusive is False
    assert config.mode == "auto"
    assert config.max_words_procedure == 20
    assert config.max_words_description == 25
    assert config.disabled_rules == ()


def test_ste_profile_parses_exclusive_and_custom_limits(tmp_path):
    source = (FIXTURE_ROOT / "asd-ste100-profile.yml").read_text(encoding="utf-8")
    source = source.replace(
        "asdSte100:\n  enabled: true",
        "asdSte100:\n  enabled: true\n  exclusive: true\n  mode: procedure\n  maxWordsProcedure: 15\n  disableRules: [articles]\n",
    )
    path = tmp_path / "profile.yml"
    path.write_text(source, encoding="utf-8")
    shutil.copytree(FIXTURE_ROOT / "reference-samples", tmp_path / "reference-samples")
    config = load_style_profile(path).profile.asd_ste100
    assert config.exclusive is True
    assert config.mode == "procedure"
    assert config.max_words_procedure == 15
    assert config.disabled_rules == ("articles",)


@pytest.mark.parametrize(
    "fixture_name",
    [
        "asd-ste100-unknown-option-profile.yml",
        "asd-ste100-invalid-limit-profile.yml",
        "asd-ste100-unknown-checks-key-profile.yml",
    ],
)
def test_invalid_ste_profiles_fail_validation(fixture_name):
    with pytest.raises(StyleProfileValidationError):
        _load(fixture_name)


def test_unknown_disable_rule_name_fails_validation(tmp_path):
    source = (FIXTURE_ROOT / "asd-ste100-profile.yml").read_text(encoding="utf-8")
    source = source.replace(
        "asdSte100:\n  enabled: true",
        "asdSte100:\n  enabled: true\n  disableRules: [emoji]\n",
    )
    path = tmp_path / "profile.yml"
    path.write_text(source, encoding="utf-8")
    shutil.copytree(FIXTURE_ROOT / "reference-samples", tmp_path / "reference-samples")
    with pytest.raises(StyleProfileValidationError):
        load_style_profile(path)


def test_enabled_rule_set_reports_summary_and_no_bot_slop_kinds_for_clean_draft():
    diagnosis = diagnose_draft(PROCEDURE_DRAFT, style_profile=_load("asd-ste100-profile.yml"))
    summary = diagnosis["asdSte100"]
    assert summary["mode"] == "auto"
    assert summary["maxWordsProcedure"] == 20
    assert summary["maxWordsDescription"] == 25
    assert summary["exclusive"] is False
    assert summary["disabledRules"] == []
    assert summary["kinds"] == []
    assert not (_kinds(diagnosis) & BOT_SLOP_KINDS)


def test_exclusive_mode_gates_bot_slop_heuristics_off():
    diagnosis = diagnose_draft(SLOPPY_DRAFT, style_profile=_load("asd-ste100-exclusive-profile.yml"))
    assert "asdSte100" in diagnosis
    assert diagnosis["asdSte100"]["exclusive"] is True
    assert not (_kinds(diagnosis) & BOT_SLOP_KINDS)


def test_beside_mode_keeps_bot_slop_heuristics_available():
    diagnosis = diagnose_draft(SLOPPY_DRAFT, style_profile=_load("asd-ste100-beside-profile.yml"))
    assert "asdSte100" in diagnosis
    assert _kinds(diagnosis) & BOT_SLOP_KINDS


def test_profiles_without_the_ste_rule_set_have_no_summary_block():
    diagnosis = diagnose_draft(
        SLOPPY_DRAFT,
        style_profile=load_style_profile(
            REPO_ROOT / "features" / "fixtures" / "editorial-diagnosis" / "style-profile.yml"
        ),
    )
    assert "asdSte100" not in diagnosis


def test_disabled_checks_key_leaves_no_summary_even_with_section_present(tmp_path):
    source = (FIXTURE_ROOT / "asd-ste100-profile.yml").read_text(encoding="utf-8")
    source = source.replace("  asdSte100: true\n", "  asdSte100: false\n")
    path = tmp_path / "profile.yml"
    path.write_text(source, encoding="utf-8")
    shutil.copytree(FIXTURE_ROOT / "reference-samples", tmp_path / "reference-samples")
    diagnosis = diagnose_draft(PROCEDURE_DRAFT, style_profile=load_style_profile(path))
    assert "asdSte100" not in diagnosis


def test_registered_kinds_cover_every_planned_ste_rule():
    assert ASD_STE100_FINDING_KINDS == {
        "asd_unapproved_word",
        "asd_multi_meaning",
        "asd_sentence_too_long",
        "asd_multiple_instructions",
        "asd_passive_voice",
        "asd_non_imperative_step",
        "asd_ing_form",
        "asd_missing_article",
    }


def test_diagnosis_schema_validates_the_ste_summary():
    diagnosis = diagnose_draft(PROCEDURE_DRAFT, style_profile=_load("asd-ste100-profile.yml"))
    assert validate_diagnosis(copy.deepcopy(diagnosis)) == diagnosis


def test_diagnosis_schema_rejects_unregistered_ste_kinds():
    diagnosis = diagnose_draft(PROCEDURE_DRAFT, style_profile=_load("asd-ste100-profile.yml"))
    diagnosis["asdSte100"]["kinds"] = ["asd_not_a_rule"]
    with pytest.raises(EditorialDiagnosisValidationError):
        validate_diagnosis(diagnosis)


def test_diagnosis_schema_rejects_non_positive_ste_limits():
    diagnosis = diagnose_draft(PROCEDURE_DRAFT, style_profile=_load("asd-ste100-profile.yml"))
    diagnosis["asdSte100"]["maxWordsProcedure"] = 0
    with pytest.raises(EditorialDiagnosisValidationError):
        validate_diagnosis(diagnosis)