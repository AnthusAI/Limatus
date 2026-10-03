"""Unit tests for ASD-STE100 writing rules (sentence length, voice, structure)."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from limatus.editorial_diagnosis import (
    _asd_sentence_units,
    _load_asd_dictionary,
    diagnose_draft,
)
from limatus.editorial_style import AsdSte100Config, LoadedStyleProfile, load_style_profile

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "features" / "fixtures" / "asd-ste100"
DEFAULT_PROFILE_PATH = FIXTURE_ROOT / "asd-ste100-profile.yml"


def _config(**overrides) -> AsdSte100Config:
    defaults = dict(
        enabled=True,
        exclusive=True,
        mode="auto",
        max_words_procedure=20,
        max_words_description=25,
        disabled_rules=(),
        approved_words=(),
        technical_names=(),
        unapproved_words=(),
    )
    defaults.update(overrides)
    return AsdSte100Config(**defaults)


def _diagnose(text: str, config: AsdSte100Config):
    loaded = load_style_profile(DEFAULT_PROFILE_PATH)
    profile = replace(loaded.profile, asd_ste100=config)
    return diagnose_draft(text, style_profile=LoadedStyleProfile(profile=profile, samples=loaded.samples))


def _asd_kinds(diagnosis) -> list[str]:
    return [f["kind"] for f in diagnosis["generic_passages"] if f["kind"].startswith("asd_")]


def test_sentence_units_strip_list_markers():
    text = "1. Press the power button.\n2. Wait for the indicator."
    units = _asd_sentence_units(text)
    assert [unit for unit, _, _ in units] == [
        "Press the power button.",
        "Wait for the indicator.",
    ]


def test_sentence_units_offset_into_draft():
    text = "# Title\n\n1. Press the power button."
    units = _asd_sentence_units(text)
    unit, start, end = units[0]
    assert text[start:end] == unit


def test_procedure_sentence_over_limit_is_flagged():
    long_step = "Insert the new filter into the filter housing of the tray enclosure of the plastic panel surface of the unit level"
    diagnosis = _diagnose(f"1. {long_step}", _config(mode="procedure"))
    kinds = _asd_kinds(diagnosis)
    assert kinds == ["asd_sentence_too_long"]
    finding = diagnosis["generic_passages"][0]
    assert "20" in finding["rationale"]
    assert "procedure" in finding["rationale"]


def test_procedure_sentence_at_limit_is_clean():
    step = "Insert the new filter into the filter housing of the tray enclosure of the plastic panel surface of the unit"
    diagnosis = _diagnose(f"1. {step}", _config(mode="procedure"))
    assert _asd_kinds(diagnosis) == []


def test_description_sentence_over_limit_is_flagged():
    sentence = (
        "The indicator lamp is a small lamp and the oil level is the level of oil inside"
        " the filter housing of the plastic tray enclosure panel"
    )
    diagnosis = _diagnose(f"{sentence}.", _config(mode="description"))
    kinds = _asd_kinds(diagnosis)
    assert "asd_sentence_too_long" in kinds
    finding = [f for f in diagnosis["generic_passages"] if f["kind"] == "asd_sentence_too_long"][0]
    assert "25" in finding["rationale"]
    assert "description" in finding["rationale"]


def test_auto_mode_falls_back_to_description_limit():
    sentence = (
        "The indicator lamp is a small lamp and the oil level is the level of oil inside"
        " the filter housing of the plastic tray enclosure panel"
    )
    diagnosis = _diagnose(f"{sentence}.", _config(mode="auto"))
    assert "asd_sentence_too_long" in _asd_kinds(diagnosis)


def test_multiple_instructions_are_flagged_in_procedure_mode():
    diagnosis = _diagnose(
        "Press the power button and wait for the indicator.",
        _config(mode="procedure"),
    )
    assert "asd_multiple_instructions" in _asd_kinds(diagnosis)


def test_multiple_instructions_are_not_flagged_in_description_mode():
    diagnosis = _diagnose(
        "Press the power button and wait for the indicator.",
        _config(mode="description"),
    )
    assert _asd_kinds(diagnosis) == []


def test_single_instruction_is_clean():
    diagnosis = _diagnose(
        "1. Insert the new filter.\n2. Wait for the indicator.",
        _config(mode="procedure"),
    )
    assert _asd_kinds(diagnosis) == []


def test_non_imperative_step_is_flagged():
    diagnosis = _diagnose(
        "The operator should press the power button.",
        _config(mode="procedure"),
    )
    assert "asd_non_imperative_step" in _asd_kinds(diagnosis)


def test_non_imperative_check_ignores_descriptions():
    diagnosis = _diagnose(
        "The operator should press the power button.",
        _config(mode="description"),
    )
    assert _asd_kinds(diagnosis) == []


def test_passive_voice_is_flagged():
    diagnosis = _diagnose("The filter is replaced by the operator.", _config(mode="auto"))
    assert "asd_passive_voice" in _asd_kinds(diagnosis)


def test_active_sentence_is_clean():
    diagnosis = _diagnose("The operator replaces the filter.", _config(mode="auto"))
    assert _asd_kinds(diagnosis) == []


def test_ing_form_outside_technical_nouns_is_flagged():
    diagnosis = _diagnose("Inserting the filter requires care.", _config(mode="auto"))
    kinds = _asd_kinds(diagnosis)
    assert "asd_ing_form" in kinds
    finding = [f for f in diagnosis["generic_passages"] if f["kind"] == "asd_ing_form"][0]
    assert finding["excerpt"].lower() == "inserting"


def test_technical_ing_nouns_are_clean():
    diagnosis = _diagnose("The fitting is inside the housing.", _config(mode="auto"))
    assert _asd_kinds(diagnosis) == []


def test_missing_article_is_flagged():
    diagnosis = _diagnose("Filter housing is plastic.", _config(mode="auto"))
    assert "asd_missing_article" in _asd_kinds(diagnosis)


def test_article_keeps_sentence_clean():
    diagnosis = _diagnose("The filter housing is plastic.", _config(mode="auto"))
    assert _asd_kinds(diagnosis) == []


def test_disabled_rules_skip_writing_checks():
    config = _config(
        mode="procedure",
        disabled_rules=(
            "sentenceLength",
            "oneInstructionPerSentence",
            "activeVoice",
            "imperativeProcedures",
            "noIngForms",
            "articles",
        ),
    )
    diagnosis = _diagnose(
        "The filter is replaced by the operator and the operator replaced the filter",
        config,
    )
    assert _asd_kinds(diagnosis) == []


def test_word_classes_split_verbs_and_nouns():
    from limatus.editorial_diagnosis import _asd_word_classes

    verbs, nouns = _asd_word_classes(_config())
    assert "press" in verbs
    assert "filter" in nouns
    assert "power" in nouns
    assert "press" not in nouns


def test_dictionary_carries_verbs_and_ing_nouns():
    dictionary = _load_asd_dictionary()
    assert "verbs" in dictionary
    assert "ingNouns" in dictionary
    assert "housing" in dictionary["ingNouns"]