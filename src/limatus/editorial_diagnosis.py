from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from .editorial_density import analyze_density, density_summary_as_dict
from .editorial_diagnosis_schema import (
    ASD_STE100_FINDING_KINDS,
    FINDING_SOURCE_PROFILE,
    SCHEMA_VERSION,
    stable_finding_id,
    stable_repetition_group_id,
    validate_diagnosis,
)
from .editorial_style import AsdSte100Config, LoadedStyleProfile, OpeningScreenRules
from .editorial_text import (
    line_at_offset,
    paragraphs,
    sentence_spans,
    sentences,
    tokenize,
    word_count,
)
from .emoji import EMOJI_PATTERN as _EMOJI_PATTERN

PROFILE_RULE_PREFIX = "Profile rule:"

_EMPTY_LEADIN_PATTERNS = (
    r"^In today's\b",
    r"^It is important to note\b",
    r"^When it comes to\b",
    r"^At the end of the day\b",
    r"^In conclusion\b",
)

# Self-closing MDX/JSX components (e.g. `<Citation data={{...}}/>`, `<BlogImage .../>`) carry
# structural prop boilerplate (field names like `container-title`, `date-parts`, `accessed`)
# that repeats verbatim across every citation in a piece. Left unmasked, the redundancy shingle
# check treats that shared JSX vocabulary as "repeated phrasing" and buries real findings under
# dozens of false positives on citation-heavy drafts. This masks such components (same character
# length, so spans into the original text stay valid) before shingling only -- sentence
# boundaries and reported excerpts still come from the original text.
_JSX_SELF_CLOSING_COMPONENT_RE = re.compile(r"<[A-Z][\w.]*(?:\s[\s\S]*?)?/>")

# Markus (the other renderer Papyrus content runs through, e.g. Pilobolus) uses colon-fenced
# directives instead of JSX: `::name{attrs}` self-closing on one line, or
# `:::name{attrs}\n...content...\n:::` block-level. Either way the attrs -- src=, alt=,
# credit=, attribution= -- repeat the same field names across every figure/pull-quote/aside
# in a piece, which is the same false-positive-redundancy trap JSX components create. Mask
# only the directive's opening line (name + attrs) and a bare `:::` closing line, not any real
# prose content sitting between them (a pull-quote's actual quoted text should still be
# checked normally).
_MARKUS_DIRECTIVE_OPEN_RE = re.compile(r"^:{2,3}[A-Za-z][\w-]*\{[^}\n]*\}[ \t]*$", re.MULTILINE)
_MARKUS_DIRECTIVE_CLOSE_RE = re.compile(r"^:::[ \t]*$", re.MULTILINE)

# Markdown/HTML image markup repeats alt text and path fragments across figures; mask before
# redundancy shingling (length preserved). Linked images first so inner `![...](...)` is not
# left partially unmasked. Ordinary `[label](url)` links are untouched (no leading `!`).
_MARKDOWN_LINKED_IMAGE_RE = re.compile(r"\[![^\]]*\]\([^)]*\)\]\([^)]*\)")
_MARKDOWN_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_HTML_IMG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)

# A leading YAML frontmatter block (title/date/description/standfirst/...) has its own
# genre conventions -- a standfirst is deliberately terse by design -- that don't belong
# under body-prose rules like cadence or redundancy. Anth.us drafts never had frontmatter,
# so this never mattered until a differently-structured publication (Pilobolus, using
# `---\n...\n---` frontmatter) surfaced it: cadence findings were firing on the standfirst
# field itself. Mask it out (same length, so spans into the original text stay valid) before
# any check runs, for every publication, not just the one that happened to expose the gap.
_YAML_FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)

_PHRASE_CERTAINTY_PATTERN = re.compile(r"\b(everyone knows|undeniably|proven)\b", re.IGNORECASE)
_ALWAYS_NEVER_PATTERN = re.compile(r"\b(always|never)\b", re.IGNORECASE)
_HYPHENATED_ALWAYS_NEVER_PATTERN = re.compile(r"\b(always|never)-\w+", re.IGNORECASE)
_NEVER_AUXILIARY_PATTERN = re.compile(
    r"\bnever\s+(had|would|could|should|might|may|will|can)\b",
    re.IGNORECASE,
)
_CLEARLY_ASSERTIVE_PATTERN = re.compile(
    r"\bclearly\s+(shows|demonstrates|proves|will|is)\b",
    re.IGNORECASE,
)

_CITATION_PATTERN = re.compile(
    r"(https?://|\[[0-9]+\]|according to|\([12][0-9]{3}\)|\b20[0-9]{2}\b)",
    re.IGNORECASE,
)

_LIST_SHAPED_PATTERN = re.compile(
    r"\bFirst,\s+.+\bSecond,\s+.+\bThird,\s+",
    re.IGNORECASE,
)

_INTENSIFIER_VAGUE_PATTERN = re.compile(
    r"\b(very|significantly|dramatically|truly|really)\b.+\b(transform|revolutionize|leverage)\b",
    re.IGNORECASE,
)

_PASSIVE_PATTERN = re.compile(r"\b(is|are|was|were|been|being)\s+\w+ed\b", re.IGNORECASE)

_STAT_PERCENT_PATTERN = re.compile(r"\d+(?:\.\d+)?%")
_STAT_MULTIPLIER_PATTERN = re.compile(r"\d+\s*[×x]\b|\d+\s+times\b", re.IGNORECASE)
_STAT_COUNT_UNIT_PATTERN = re.compile(
    r"\b\d{3,}\s+(users|ms|seconds|minutes|hours|days|requests|tokens)\b",
    re.IGNORECASE,
)
_LIST_ORDINAL_LINE_PATTERN = re.compile(r"^\s*\d+\.\s")
_BLOCKQUOTE_LINE_PATTERN = re.compile(r"^\s*>")
_STICKER_NUMBER_PATTERN = re.compile(r"#\d+\b")

_REFRAIN_MAX_WORDS = 12


def _mask_yaml_frontmatter(text: str) -> str:
    match = _YAML_FRONTMATTER_RE.match(text)
    if not match:
        return text
    blanked = re.sub(r"[^\n]", " ", match.group(0))
    return blanked + text[match.end() :]


def check_rules_only(
    draft_text: str, *, style_profile: LoadedStyleProfile, surface: str | None = None
) -> list[dict[str, Any]]:
    """Run only the explicit ``rules`` checks (banned phrases/intensifiers/
    patterns, no-emoji, contrast cap), skipping the prose-heuristic checks
    (cadence, redundancy, vague claims, density, ...).

    Meant for text that isn't real prose -- raw component source, a
    page-content.ts copy string -- where the heuristic checks would misfire
    on code shape rather than saying anything about the copy's voice.
    """
    text = draft_text.replace("\r\n", "\n")
    text = _mask_yaml_frontmatter(text)
    rules_findings = _check_profile_rules(
        text,
        style_profile,
        generic_passages=[],
        voice_observations=[],
        surface=surface,
    )
    return rules_findings["generic_passages"] + rules_findings["voice_observations"]


def diagnose_draft(
    draft_text: str, *, style_profile: LoadedStyleProfile, surface: str | None = None
) -> dict[str, Any]:
    text = draft_text.replace("\r\n", "\n")
    text = _mask_yaml_frontmatter(text)
    profile = style_profile.profile
    checks = profile.checks

    ste_config = profile.asd_ste100
    ste_enabled = bool(checks["asdSte100"]) and ste_config is not None and ste_config.enabled
    ste_only = ste_enabled and ste_config.exclusive

    generic_passages: list[dict[str, Any]] = []
    unsupported_claims: list[dict[str, Any]] = []
    voice_observations: list[dict[str, Any]] = []
    required_facts: list[dict[str, Any]] = []
    repetition_groups: list[dict[str, Any]] = []
    density_summary: dict[str, Any] | None = None

    if not ste_only:
        if checks["emptyLeadin"]:
            generic_passages.extend(_check_empty_leadins(text))
        if checks["listShapedProse"]:
            generic_passages.extend(_check_list_shaped_prose(text))
        if checks["vagueClaim"]:
            generic_passages.extend(_check_vague_claims(text, profile.lexicon_avoid))
            generic_passages.extend(_check_intensifier_vague_claims(text))
        if checks["overusedWords"]:
            generic_passages.extend(_check_overused_words(text))
        if checks["uncontractedForms"]:
            voice_observations.extend(_check_uncontracted_forms(text))

        if checks["unsupportedCertainty"]:
            unsupported_claims.extend(_check_unsupported_certainty(text))
        if checks["uniformCadence"]:
            voice_observations.extend(_check_uniform_cadence(text))
        if checks["punchlineCadence"]:
            voice_observations.extend(_check_punchline_cadence(text))
        if checks["openingScreen"] and profile.opening_screen is not None:
            generic_passages.extend(_check_opening_screen(text, profile.opening_screen))
        if checks["voiceMismatch"]:
            voice_observations.extend(_check_voice_mismatch(text, style_profile))

        repetition_groups = _check_redundancy(text) if checks["redundancy"] else []
        if checks["missingAttribution"]:
            required_facts.extend(_check_required_facts(text))

        if checks["informationDensity"]:
            density_analysis = analyze_density(text, style_profile.profile.density)
            density_summary = density_summary_as_dict(
                density_analysis.summary,
                thresholds=style_profile.profile.density,
                findings=density_analysis.findings,
            )
            generic_passages.extend(density_analysis.findings)

        rules_findings = _check_profile_rules(
            text,
            style_profile,
            generic_passages=generic_passages,
            voice_observations=voice_observations,
            surface=surface,
        )
        generic_passages.extend(rules_findings["generic_passages"])
        voice_observations.extend(rules_findings["voice_observations"])

    ste_summary: dict[str, Any] | None = None
    if ste_enabled:
        ste_findings = _check_asd_ste100(text, ste_config)
        generic_passages.extend(ste_findings)
        topic_modes = _asd_topic_modes(text, ste_config, _asd_word_classes(ste_config)[0])
        ste_summary = _asd_ste100_summary(
            ste_config, ste_findings, _asd_document_mode(text, ste_config, topic_modes)
        )

    result = {
        "schemaVersion": SCHEMA_VERSION,
        "document_intent": _extract_document_intent(text),
        "audience": profile.audience,
        "generic_passages": generic_passages,
        "unsupported_claims": unsupported_claims,
        "repetition_groups": repetition_groups,
        "voice_observations": voice_observations,
        "required_facts": required_facts,
    }
    if density_summary is not None:
        result["density"] = density_summary
    if ste_summary is not None:
        result["asdSte100"] = ste_summary
    return validate_diagnosis(result)


def _asd_ste100_summary(
    config: AsdSte100Config, findings: list[dict[str, Any]], detected_mode: str | None = None
) -> dict[str, Any]:
    kinds = sorted({finding["kind"] for finding in findings if finding["kind"] in ASD_STE100_FINDING_KINDS})
    summary: dict[str, Any] = {
        "mode": config.mode,
        "maxWordsProcedure": config.max_words_procedure,
        "maxWordsDescription": config.max_words_description,
        "exclusive": config.exclusive,
        "disabledRules": list(config.disabled_rules),
        "kinds": kinds,
    }
    if config.mode == "auto" and detected_mode is not None:
        summary["detectedMode"] = detected_mode
    return summary


def _check_asd_ste100(text: str, config: AsdSte100Config) -> list[dict[str, Any]]:
    """Run the ASD-STE100 rule-set checks over the draft."""
    findings: list[dict[str, Any]] = []
    if "approvedWords" not in config.disabled_rules:
        findings.extend(_check_asd_vocabulary(text, config))
    if "oneMeaningPerWord" not in config.disabled_rules:
        findings.extend(_check_asd_multi_meaning(text, config))
    verbs, nouns = _asd_word_classes(config)
    topic_modes = _asd_topic_modes(text, config, verbs)
    disabled = set(config.disabled_rules)
    if "sentenceLength" not in disabled:
        findings.extend(_check_asd_sentence_length(text, config, topic_modes))
    if "oneInstructionPerSentence" not in disabled:
        findings.extend(_check_asd_multiple_instructions(text, config, topic_modes, verbs))
    if "activeVoice" not in disabled:
        findings.extend(_check_asd_passive_voice(text, config))
    if "imperativeProcedures" not in disabled:
        findings.extend(_check_asd_non_imperative(text, config, topic_modes))
    if "noIngForms" not in disabled:
        findings.extend(_check_asd_ing_forms(text, config))
    if "articles" not in disabled:
        findings.extend(_check_asd_missing_article(text, config, nouns))
    return findings


_ASD_STE100_WRITING_RULE_TO_KIND = {
    "sentenceLength": "asd_sentence_too_long",
    "oneInstructionPerSentence": "asd_multiple_instructions",
    "activeVoice": "asd_passive_voice",
    "imperativeProcedures": "asd_non_imperative_step",
    "noIngForms": "asd_ing_form",
    "articles": "asd_missing_article",
}

_ASD_LIST_MARKER_PATTERN = re.compile(r"^\s*(?:\d+[.)]\s*|[-*+]\s+)")

_ASD_PASSIVE_PATTERN = re.compile(
    r"\b(?:is|are|was|were|been|being)\s+(?:\w+ed|made|done|given|taken|held|kept|put|set|sent|shown)\b",
    re.IGNORECASE,
)

_ASD_INSTRUCTION_CONNECTOR_PATTERN = re.compile(r"\b(?:and then|then|and|or)\b", re.IGNORECASE)

_ASD_SUBJECT_OPENER_TOKENS = {
    "you",
    "we",
    "the",
    "a",
    "an",
    "it",
    "they",
    "he",
    "she",
    "there",
    "user",
    "users",
    "operator",
    "operators",
    "person",
    "people",
}

_ASD_ING_TOKEN_PATTERN = re.compile(r"\b\w+ing\b")

_ASD_FIRST_WORD_PATTERN = re.compile(r"[A-Za-z0-9']+")


def _asd_topic_modes(text: str, config: AsdSte100Config, verbs: set[str]) -> list[tuple[int, int, str]]:
    """Classify each paragraph topic as procedure or description.

    An explicit config mode applies to every topic. In auto mode, paragraphs
    containing list items or starting with an imperative verb (an approved
    verb token) are procedure topics; everything else is description.
    """
    if config.mode in {"procedure", "description"}:
        return []
    modes: list[tuple[int, int, str]] = []
    cursor = 0
    for paragraph in paragraphs(text):
        start = text.find(paragraph, cursor)
        if start < 0:
            start = cursor
        cursor = start + len(paragraph)
        lines = paragraph.split("\n")
        mode = "description"
        if any(_ASD_LIST_MARKER_PATTERN.match(line) for line in lines):
            mode = "procedure"
        else:
            first_line = next((line for line in lines if line.strip()), "")
            tokens = tokenize(first_line)
            if tokens and tokens[0] in verbs:
                mode = "procedure"
        modes.append((start, start + len(paragraph), mode))
    return modes


def _asd_unit_mode(
    unit_start: int, topic_modes: list[tuple[int, int, str]], fallback: str = "description"
) -> str:
    for start, end, mode in topic_modes:
        if start <= unit_start < end:
            return mode
    return fallback


def _asd_explicit_mode(config: AsdSte100Config) -> str:
    """Collapse the config mode to a concrete topic mode."""
    return config.mode if config.mode in {"procedure", "description"} else "description"


def _asd_document_mode(text: str, config: AsdSte100Config, topic_modes: list[tuple[int, int, str]]) -> str:
    if config.mode != "auto":
        return config.mode
    if any(mode == "procedure" for _, _, mode in topic_modes):
        return "procedure"
    return "description"


def _asd_word_classes(config: AsdSte100Config) -> tuple[set[str], set[str]]:
    dictionary = _load_asd_dictionary()
    approved = set(dictionary.get("approvedWords", [])) | {word.lower() for word in config.approved_words}
    verbs = {str(word).lower() for word in dictionary.get("verbs", [])}
    nouns = approved - verbs
    technical_names = set(dictionary.get("technicalNames", [])) | {name.lower() for name in config.technical_names}
    nouns |= {part.lower() for name in technical_names for part in str(name).split()}
    return verbs, nouns


def _asd_sentence_units(text: str) -> list[tuple[str, int, int]]:
    """Return sentence-like units with list markers stripped.

    Numbered and bulleted list items lose their marker prefix so word counts
    and imperative checks see the step text; prose lines yield their
    sentences. Units carry (text, start, end) offsets into the draft.
    """
    units: list[tuple[str, int, int]] = []
    for line_match in re.finditer(r"[^\n]+", text):
        line = line_match.group(0)
        line_start = line_match.start()
        marker = _ASD_LIST_MARKER_PATTERN.match(line)
        content_offset = marker.end() if marker else 0
        content = line[content_offset:]
        if not content.strip():
            continue
        cursor = 0
        for sentence in sentences(content):
            pos = content.find(sentence, cursor)
            if pos < 0:
                pos = cursor
            cursor = pos + len(sentence)
            start = line_start + content_offset + pos
            units.append((sentence, start, start + len(sentence)))
    return units


def _check_asd_sentence_length(
    text: str, config: AsdSte100Config, topic_modes: list[tuple[int, int, str]]
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for unit, start, end in _asd_sentence_units(text):
        mode = _asd_unit_mode(start, topic_modes, _asd_explicit_mode(config))
        limit = config.max_words_procedure if mode == "procedure" else config.max_words_description
        words = tokenize(unit)
        if len(words) > limit:
            rationale = (
                f"Sentence has {len(words)} words; the {mode} limit is {limit} words."
            )
            findings.append(_make_finding("asd_sentence_too_long", text, start, end, rationale))
    return findings


def _check_asd_multiple_instructions(
    text: str, config: AsdSte100Config, topic_modes: list[tuple[int, int, str]], verbs: set[str]
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for unit, start, end in _asd_sentence_units(text):
        if _asd_unit_mode(start, topic_modes, _asd_explicit_mode(config)) != "procedure":
            continue
        segments = [part for part in _ASD_INSTRUCTION_CONNECTOR_PATTERN.split(unit) if part.strip()]
        imperative_segments = [
            segment
            for segment in segments
            if (tokenize(segment) or [""])[0] in verbs
        ]
        if len(imperative_segments) >= 2:
            rationale = (
                "Procedure sentence contains multiple instructions; keep one instruction per sentence."
            )
            findings.append(_make_finding("asd_multiple_instructions", text, start, end, rationale))
    return findings


def _check_asd_passive_voice(text: str, config: AsdSte100Config) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for unit, start, _ in _asd_sentence_units(text):
        for match in _ASD_PASSIVE_PATTERN.finditer(unit):
            rationale = "Passive voice detected; write the sentence in active voice."
            findings.append(
                _make_finding("asd_passive_voice", text, start + match.start(), start + match.end(), rationale)
            )
    return findings


def _check_asd_non_imperative(
    text: str, config: AsdSte100Config, topic_modes: list[tuple[int, int, str]]
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for unit, start, end in _asd_sentence_units(text):
        if _asd_unit_mode(start, topic_modes, _asd_explicit_mode(config)) != "procedure":
            continue
        tokens = tokenize(unit)
        if tokens and tokens[0] in _ASD_SUBJECT_OPENER_TOKENS:
            rationale = "Procedure step does not start with an imperative verb."
            findings.append(_make_finding("asd_non_imperative_step", text, start, end, rationale))
    return findings


def _check_asd_ing_forms(text: str, config: AsdSte100Config) -> list[dict[str, Any]]:
    dictionary = _load_asd_dictionary()
    allowlist = {str(word).lower() for word in dictionary.get("ingNouns", [])}
    allowlist |= {str(word).lower() for word in dictionary.get("approvedWords", [])}
    allowlist |= {word.lower() for word in config.approved_words}
    allowlist |= {name.lower() for name in config.technical_names}
    technical_names = set(dictionary.get("technicalNames", [])) | {name.lower() for name in config.technical_names}
    occupied = _asd_technical_name_spans(text.lower(), technical_names)
    findings: list[dict[str, Any]] = []
    for unit, start, _ in _asd_sentence_units(text):
        for match in _ASD_ING_TOKEN_PATTERN.finditer(unit.lower()):
            word = match.group(0)
            if word in allowlist:
                continue
            abs_start = start + match.start()
            abs_end = start + match.end()
            if _spans_overlap(abs_start, abs_end, occupied):
                continue
            rationale = f"'{word}' uses the -ing verb form; rewrite without the -ing form."
            findings.append(_make_finding("asd_ing_form", text, abs_start, abs_end, rationale))
    return findings


def _check_asd_missing_article(text: str, config: AsdSte100Config, nouns: set[str]) -> list[dict[str, Any]]:
    dictionary = _load_asd_dictionary()
    unknown_pos = {str(entry["word"]).lower() for entry in dictionary.get("unapprovedWords", [])}
    unknown_pos |= {str(entry["word"]).lower() for entry in config.unapproved_words}
    findings: list[dict[str, Any]] = []
    for unit, start, _ in _asd_sentence_units(text):
        first_word = _ASD_FIRST_WORD_PATTERN.match(unit)
        if first_word is None:
            continue
        first_token = first_word.group(0).lower()
        if first_token not in nouns or first_token in unknown_pos:
            continue
        rationale = f"Singular noun '{first_word.group(0)}' starts the sentence without 'a', 'an', or 'the'."
        abs_start = start + first_word.start()
        abs_end = start + first_word.end()
        findings.append(_make_finding("asd_missing_article", text, abs_start, abs_end, rationale))
    return findings


_ASD_STE100_DICTIONARY: dict[str, Any] | None = None


def _load_asd_dictionary() -> dict[str, Any]:
    global _ASD_STE100_DICTIONARY
    if _ASD_STE100_DICTIONARY is None:
        path = Path(__file__).parent / "data" / "asd-ste100-dictionary.yml"
        _ASD_STE100_DICTIONARY = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return _ASD_STE100_DICTIONARY


def _asd_technical_name_spans(lowered_text: str, technical_names: set[str]) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    for phrase in sorted(technical_names, key=len, reverse=True):
        if not phrase:
            continue
        for match in re.finditer(r"\b" + re.escape(phrase) + r"\b", lowered_text):
            spans.append((match.start(), match.end()))
    return spans


def _check_asd_vocabulary(text: str, config: AsdSte100Config) -> list[dict[str, Any]]:
    dictionary = _load_asd_dictionary()
    lowered = text.lower()
    technical_names = set(dictionary.get("technicalNames", [])) | {
        name.lower() for name in config.technical_names
    }
    occupied = _asd_technical_name_spans(lowered, technical_names)
    approved = set(dictionary.get("approvedWords", [])) | {word.lower() for word in config.approved_words}
    unapproved: dict[str, str] = {
        str(entry["word"]).lower(): str(entry.get("approvedAlternative", "")).strip()
        for entry in dictionary.get("unapprovedWords", [])
    }
    unapproved.update(
        {str(entry["word"]).lower(): str(entry["approvedAlternative"]).strip() for entry in config.unapproved_words}
    )
    unapproved = {word: alt for word, alt in unapproved.items() if word not in approved}
    findings: list[dict[str, Any]] = []
    for word, alternative in sorted(unapproved.items()):
        if not word:
            continue
        for match in re.finditer(r"\b" + re.escape(word) + r"\b", lowered):
            if _spans_overlap(match.start(), match.end(), occupied):
                continue
            rationale = f"'{word}' is not on the approved word list."
            if alternative:
                rationale += f" Approved alternative: '{alternative}'."
            findings.append(_make_finding("asd_unapproved_word", text, match.start(), match.end(), rationale))
    return findings


_ASD_MODAL_OR_INFINITIVE_MARKERS = {"to", "will", "must", "can", "should", "do", "does", "did", "please", "not"}


def _check_asd_multi_meaning(text: str, config: AsdSte100Config) -> list[dict[str, Any]]:
    dictionary = _load_asd_dictionary()
    lowered = text.lower()
    technical_names = set(dictionary.get("technicalNames", [])) | {
        name.lower() for name in config.technical_names
    }
    occupied = _asd_technical_name_spans(lowered, technical_names)
    findings: list[dict[str, Any]] = []
    sentence_list = sentence_spans(text)
    for rule in dictionary.get("oneMeaningRules", []):
        word = str(rule["word"]).lower()
        allowed = str(rule.get("allowedMeaning", "")).lower()
        for match in re.finditer(r"\b" + re.escape(word) + r"\b", lowered):
            if _spans_overlap(match.start(), match.end(), occupied):
                continue
            before = lowered[: match.start()].split()
            previous_word = before[-1] if before else ""
            used_as_noun = previous_word in {"a", "an", "the"}
            sentence_initial = any(
                sentence_start + (len(sentence) - len(sentence.lstrip())) == match.start()
                for sentence, sentence_start, _ in sentence_list
            )
            used_as_verb = previous_word in _ASD_MODAL_OR_INFINITIVE_MARKERS
            if not used_as_verb and sentence_initial:
                _, nouns = _asd_word_classes(config)
                following = re.search(r"[a-z0-9']+", lowered[match.end() :])
                next_word = following.group(0) if following else ""
                used_as_verb = next_word not in nouns
            violated = (allowed == "verb" and used_as_noun) or (allowed == "noun" and used_as_verb)
            if not violated:
                continue
            rationale = (
                f"'{word}' has one approved meaning ({allowed}); this usage reads as the "
                f"{'noun' if allowed == 'verb' else 'verb'} form."
            )
            findings.append(_make_finding("asd_multi_meaning", text, match.start(), match.end(), rationale))
    return findings


def normalize_finding_decision(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized not in {"skip", "rewrite", "delete", "keep", "add"}:
        raise ValueError("Finding decision must be skip, rewrite, delete, keep, or add.")
    return normalized


def record_finding_decision(
    decisions: list[dict[str, Any]],
    finding_id: str,
    decision: str,
    note: str = "",
) -> list[dict[str, Any]]:
    if not finding_id.strip():
        raise ValueError("finding_id is required.")
    normalized = normalize_finding_decision(decision)
    fid = finding_id.strip()
    row = {
        "schemaVersion": SCHEMA_VERSION,
        "finding_id": fid,
        "decision": normalized,
        "note": note.strip(),
    }
    updated = list(decisions)
    for index, entry in enumerate(updated):
        if isinstance(entry, dict) and entry.get("finding_id") == fid:
            updated[index] = row
            return updated
    updated.append(row)
    return updated


def findings_marked_rewrite(
    diagnosis: dict[str, Any],
    decisions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    validated = validate_diagnosis(diagnosis)
    rewrite_ids = {
        entry["finding_id"]
        for entry in decisions
        if isinstance(entry, dict) and entry.get("decision") == "rewrite" and entry.get("finding_id")
    }
    if not rewrite_ids:
        return []

    findings_by_id: dict[str, dict[str, Any]] = {}
    for array_key in ("generic_passages", "unsupported_claims", "voice_observations", "required_facts"):
        for finding in validated.get(array_key, []):
            findings_by_id[finding["id"]] = finding
    for group in validated.get("repetition_groups", []):
        findings_by_id[group["id"]] = group
        for member in group.get("members", []):
            findings_by_id[member["id"]] = member

    return [findings_by_id[finding_id] for finding_id in sorted(rewrite_ids) if finding_id in findings_by_id]


def _extract_document_intent(text: str) -> str:
    prose_paragraphs = [paragraph for paragraph, _, _ in _prose_paragraph_spans(text)]
    for paragraph in prose_paragraphs or paragraphs(text):
        for sentence in sentences(paragraph):
            cleaned = sentence.strip()
            if cleaned:
                return cleaned
    raise ValueError("Draft must contain at least one sentence for document_intent.")


def _make_finding(kind: str, draft_text: str, start: int, end: int, rationale: str) -> dict[str, Any]:
    return {
        "id": stable_finding_id(kind, draft_text, start, end),
        "kind": kind,
        "excerpt": draft_text[start:end],
        "span": {"start": start, "end": end},
        "rationale": rationale,
        "source": FINDING_SOURCE_PROFILE,
    }


def _check_empty_leadins(text: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for sentence, start, end in sentence_spans(text):
        for pattern in _EMPTY_LEADIN_PATTERNS:
            if re.search(pattern, sentence, re.IGNORECASE):
                findings.append(
                    _make_finding(
                        "empty_leadin",
                        text,
                        start,
                        end,
                        "Sentence opens with empty boilerplate instead of a concrete stake.",
                    )
                )
                break
    return findings


def _check_list_shaped_prose(text: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for paragraph in paragraphs(text):
        match = _LIST_SHAPED_PATTERN.search(paragraph)
        if not match:
            continue
        paragraph_start = text.find(paragraph)
        if paragraph_start < 0:
            continue
        start = paragraph_start
        end = paragraph_start + len(paragraph)
        findings.append(
            _make_finding(
                "list_shaped_prose",
                text,
                start,
                end,
                "Paragraph reads like an inline list without substantive development.",
            )
        )
    return findings


def _check_vague_claims(text: str, lexicon_avoid: tuple[str, ...]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    lowered_text = text.lower()
    for term in lexicon_avoid:
        normalized = term.strip().lower()
        if not normalized or normalized == "empty intensifiers without evidence":
            continue
        search_from = 0
        while True:
            index = lowered_text.find(normalized, search_from)
            if index < 0:
                break
            start = index
            end = index + len(normalized)
            findings.append(
                _make_finding(
                    "vague_claim",
                    text,
                    start,
                    end,
                    f"Passage uses avoided lexicon '{term}' without operational detail.",
                )
            )
            search_from = end
    return findings


def _check_intensifier_vague_claims(text: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for sentence, start, end in sentence_spans(text):
        if _INTENSIFIER_VAGUE_PATTERN.search(sentence):
            findings.append(
                _make_finding(
                    "vague_claim",
                    text,
                    start,
                    end,
                    "Sentence pairs empty intensifiers with vague transformation language.",
                )
            )
    return findings


# Hedges and crutch words: not banned outright by any profile (they're
# ordinary English, useful in moderation), but a tell of AI-generated prose
# when a piece leans on the same one repeatedly instead of varying emphasis
# or, more often, just not needing the emphasis at all.
_CRUTCH_WORDS = (
    "actually",
    "really",
    "very",
    "basically",
    "essentially",
    "literally",
    "simply",
    "clearly",
    "obviously",
)


def _check_overused_words(text: str) -> list[dict[str, Any]]:
    word_total = max(len(text.split()), 1)
    findings: list[dict[str, Any]] = []
    for word in _CRUTCH_WORDS:
        matches = list(re.finditer(rf"\b{re.escape(word)}\b", text, re.IGNORECASE))
        if not matches:
            continue
        # Scales with length so a short piece isn't held to the same raw
        # count as a long one, but never drops below 3: a couple of uses of
        # an ordinary word like "really" is just English, not a tell.
        threshold = max(3, round(word_total / 250))
        if len(matches) <= threshold:
            continue
        first = matches[0]
        findings.append(
            _make_finding(
                "overused_word",
                text,
                first.start(),
                first.end(),
                f"'{word}' appears {len(matches)} times across {word_total} words -- "
                "a crutch word, not a banned one, but still worth cutting most instances.",
            )
        )
    return findings


# Formal two-word constructions and their contraction, for profiles whose
# sentenceStyle says to use contractions. A style rule stated in prose
# ("use contractions") is easy to state and easy to violate by default,
# since uncontracted phrasing is exactly what a careful, formal draft
# reaches for without anyone noticing.
_CONTRACTION_PAIRS = (
    ("that is", "that's"),
    ("it is", "it's"),
    ("there is", "there's"),
    ("who is", "who's"),
    ("what is", "what's"),
    ("do not", "don't"),
    ("does not", "doesn't"),
    ("did not", "didn't"),
    ("cannot", "can't"),
    ("can not", "can't"),
    ("will not", "won't"),
    ("would not", "wouldn't"),
    ("should not", "shouldn't"),
    ("could not", "couldn't"),
    ("is not", "isn't"),
    ("are not", "aren't"),
    ("was not", "wasn't"),
    ("were not", "weren't"),
    ("have not", "haven't"),
    ("has not", "hasn't"),
    ("had not", "hadn't"),
    ("they are", "they're"),
    ("we are", "we're"),
    ("you are", "you're"),
    ("i am", "I'm"),
    ("let us", "let's"),
)


def _check_uncontracted_forms(text: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    occupied: list[tuple[int, int]] = []
    for formal, contracted in _CONTRACTION_PAIRS:
        pattern = re.compile(rf"\b{re.escape(formal)}\b", re.IGNORECASE)
        for match in pattern.finditer(text):
            start, end = match.start(), match.end()
            if _spans_overlap(start, end, occupied):
                continue
            # Skip the appositive/clarifying use of "that is," (the "i.e."
            # sense) -- contracting that one changes what the sentence means.
            if formal == "that is" and text[end : end + 1] == ",":
                continue
            matched_text = text[start:end]
            suggestion = contracted[0].upper() + contracted[1:] if matched_text[0].isupper() else contracted
            findings.append(
                _make_finding(
                    "uncontracted_form",
                    text,
                    start,
                    end,
                    f"'{matched_text}' could contract to '{suggestion}' -- the profile favors contractions.",
                )
            )
            occupied.append((start, end))
    return findings


def _sentence_has_unsupported_certainty(sentence: str) -> bool:
    if _PHRASE_CERTAINTY_PATTERN.search(sentence):
        return True
    if _CLEARLY_ASSERTIVE_PATTERN.search(sentence):
        return True

    if not _ALWAYS_NEVER_PATTERN.search(sentence):
        return False

    stripped = _HYPHENATED_ALWAYS_NEVER_PATTERN.sub(" ", sentence)
    if not _ALWAYS_NEVER_PATTERN.search(stripped):
        return False

    if _NEVER_AUXILIARY_PATTERN.search(sentence):
        return False

    trimmed = sentence.strip()
    if re.match(r"^Never\s+\w", trimmed):
        return False

    return True


def _check_unsupported_certainty(text: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for sentence, start, end in sentence_spans(text):
        if not _sentence_has_unsupported_certainty(sentence):
            continue
        if _is_blockquote_line(text, start):
            continue
        if _CITATION_PATTERN.search(sentence):
            continue
        findings.append(
            _make_finding(
                "unsupported_certainty",
                text,
                start,
                end,
                "Sentence states certainty without attributable evidence.",
            )
        )
    return findings


def _check_uniform_cadence(text: str) -> list[dict[str, Any]]:
    spans = sentence_spans(text)
    if len(spans) < 5:
        return []

    findings: list[dict[str, Any]] = []
    run_start = 0
    while run_start < len(spans):
        anchor_len = len(spans[run_start][0].split())
        run_end = run_start + 1
        while run_end < len(spans):
            length = len(spans[run_end][0].split())
            if abs(length - anchor_len) > 3:
                break
            run_end += 1
        if run_end - run_start >= 5:
            start = spans[run_start][1]
            end = spans[run_end - 1][2]
            findings.append(
                _make_finding(
                    "uniform_cadence",
                    text,
                    start,
                    end,
                    "Five or more consecutive sentences share nearly identical length.",
                )
            )
            run_start = run_end
            continue
        run_start += 1
    return findings


# A punch line is a very short sentence landing right after a long one. Once
# in a while that rhythm is emphasis. When it closes a paragraph, or happens
# twice in one, it reads as a performed mic-drop rather than a statement, and
# it is one of the clearest tells of machine-drafted prose. Equal-length runs
# are a different tell, caught by the uniform-cadence check.
_PUNCHLINE_MAXIMUM_WORDS = 6
_PUNCHLINE_PRECEDING_MINIMUM_WORDS = 14

_NON_PROSE_PARAGRAPH_PATTERN = re.compile(
    r"^(?:#|\||<|>|\{|```|---|!\[|import\s|export\s|[-*+]\s|\d+[.)]\s)"
)


def _prose_paragraph_spans(text: str) -> list[tuple[str, int, int]]:
    spans: list[tuple[str, int, int]] = []
    cursor = 0
    for paragraph in paragraphs(text):
        paragraph_start = text.find(paragraph, cursor)
        if paragraph_start < 0:
            paragraph_start = cursor
        cursor = paragraph_start + len(paragraph)
        if _NON_PROSE_PARAGRAPH_PATTERN.match(paragraph):
            continue
        spans.append((paragraph, paragraph_start, paragraph_start + len(paragraph)))
    return spans


def _sentence_spans_within(paragraph: str, paragraph_start: int) -> list[tuple[str, int, int]]:
    spans: list[tuple[str, int, int]] = []
    local_offset = 0
    for sentence in sentences(paragraph):
        local_start = paragraph.find(sentence, local_offset)
        spans.append((sentence, paragraph_start + local_start, paragraph_start + local_start + len(sentence)))
        local_offset = local_start + len(sentence)
    return spans


_TERSE_CLOSING_TAG_MAXIMUM_WORDS = 4
_TERSE_CLOSING_TAG_MINIMUM_PARAGRAPH_SENTENCES = 3
_MARKDOWN_LINK_ONLY_SENTENCE_PATTERN = re.compile(r"^\[[^\]]*\]\([^)]*\)[.!]?$")


# A short sentence that carries a number states a measurement; it is not a
# line the reader has to decode.
_NUMERIC_STATEMENT_PATTERN = re.compile(r"\d|%")


def _sentence_can_be_punchline(sentence: str) -> bool:
    stripped_sentence = sentence.strip().strip("*_")
    if not stripped_sentence or stripped_sentence[-1] in ":?\"\u201d'" or "```" in stripped_sentence:
        return False
    if _NUMERIC_STATEMENT_PATTERN.search(stripped_sentence):
        return False
    return not _MARKDOWN_LINK_ONLY_SENTENCE_PATTERN.match(stripped_sentence)


def _check_punchline_cadence(text: str) -> list[dict[str, Any]]:
    masked_text = _mask_for_redundancy_shingling(text)
    findings: list[dict[str, Any]] = []
    for paragraph, paragraph_start, _ in _prose_paragraph_spans(masked_text):
        sentence_spans_in_paragraph = _sentence_spans_within(paragraph, paragraph_start)
        sentence_word_counts = [word_count(sentence) for sentence, _, _ in sentence_spans_in_paragraph]
        last_index = len(sentence_spans_in_paragraph) - 1
        drop_indexes = [
            index
            for index in range(1, len(sentence_spans_in_paragraph))
            if sentence_word_counts[index] <= _PUNCHLINE_MAXIMUM_WORDS
            and sentence_word_counts[index - 1] >= _PUNCHLINE_PRECEDING_MINIMUM_WORDS
            and _sentence_can_be_punchline(sentence_spans_in_paragraph[index][0])
        ]
        flagged_indexes = drop_indexes if len(drop_indexes) >= 2 else [i for i in drop_indexes if i == last_index]
        closes_with_terse_tag = (
            last_index + 1 >= _TERSE_CLOSING_TAG_MINIMUM_PARAGRAPH_SENTENCES
            and sentence_word_counts[last_index] <= _TERSE_CLOSING_TAG_MAXIMUM_WORDS
            and sentence_word_counts[last_index - 1] >= 2 * sentence_word_counts[last_index]
            and _sentence_can_be_punchline(sentence_spans_in_paragraph[last_index][0])
        )
        if closes_with_terse_tag and last_index not in flagged_indexes:
            flagged_indexes.append(last_index)
        for index in flagged_indexes:
            _, start, end = sentence_spans_in_paragraph[index]
            placement = "more than once in this paragraph" if len(drop_indexes) >= 2 else "to close the paragraph"
            findings.append(
                _make_finding(
                    "punchline_cadence",
                    text,
                    start,
                    end,
                    f"A very short sentence lands after a longer one {placement}. It reads as a performed "
                    "punch line. Fold the point into the sentence before it, or state it plainly.",
                )
            )
    return findings


# The opening paragraph is the only one every reader sees. Terms a profile
# lists as insider vocabulary must be defined in the sentence where they first
# appear there, and a profile can require a concrete number on the first screen.
_DEFINITION_AFTER_TERM_PATTERN = re.compile(r"^(?:\s*[,(:\u2014\u2013]|\s+-\s|\s+(?:is|are|means)\s+(?:a|an|the)\b)")
_DEFINITION_BEFORE_TERM_PATTERN = re.compile(r"\b(?:called|named|known as)\s+(?:an?\s+|the\s+)?$", re.IGNORECASE)
_DIGIT_PATTERN = re.compile(r"\d")


def _check_opening_screen(text: str, rules: OpeningScreenRules) -> list[dict[str, Any]]:
    prose_paragraphs = _prose_paragraph_spans(text)
    if not prose_paragraphs:
        return []
    opening_paragraph, opening_start, _ = prose_paragraphs[0]
    opening_sentences = _sentence_spans_within(opening_paragraph, opening_start)
    findings: list[dict[str, Any]] = []

    reported_term_spans: list[tuple[int, int]] = []
    for term in sorted(rules.insider_terms, key=len, reverse=True):
        term_pattern = re.compile(rf"\b{re.escape(term)}(?:e?s)?\b", re.IGNORECASE)
        for sentence, sentence_start, _ in opening_sentences:
            match = term_pattern.search(sentence)
            if not match:
                continue
            term_start, term_end = sentence_start + match.start(), sentence_start + match.end()
            if _spans_overlap(term_start, term_end, reported_term_spans):
                break
            reported_term_spans.append((term_start, term_end))
            defined_after = _DEFINITION_AFTER_TERM_PATTERN.match(sentence[match.end() :])
            defined_before = _DEFINITION_BEFORE_TERM_PATTERN.search(sentence[: match.start()])
            if not defined_after and not defined_before:
                findings.append(
                    _make_finding(
                        "opening_screen",
                        text,
                        term_start,
                        term_end,
                        f"'{match.group(0)}' is insider vocabulary in the opening paragraph and isn't defined "
                        "where it first appears. Say what it is in the same sentence, or move it after the plain picture.",
                    )
                )
            break

    if rules.require_number and not _DIGIT_PATTERN.search(opening_paragraph):
        later_prose_has_number = any(_DIGIT_PATTERN.search(paragraph) for paragraph, _, _ in prose_paragraphs[1:])
        if later_prose_has_number and opening_sentences:
            _, first_sentence_start, first_sentence_end = opening_sentences[0]
            findings.append(
                _make_finding(
                    "opening_screen",
                    text,
                    first_sentence_start,
                    first_sentence_end,
                    "The opening paragraph carries no number, but later paragraphs do. "
                    "Bring the one figure that shows what's at stake onto the first screen.",
                )
            )
    return findings


def _check_voice_mismatch(text: str, style_profile: LoadedStyleProfile) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    profile = style_profile.profile
    style_text = " ".join(profile.sentence_style).lower()
    prefers_active = "active voice" in style_text

    if prefers_active:
        for sentence, start, end in sentence_spans(text):
            if not _PASSIVE_PATTERN.search(sentence):
                continue
            findings.append(
                _make_finding(
                    "voice_mismatch",
                    text,
                    start,
                    end,
                    "Sentence uses passive voice where the profile prefers active voice.",
                )
            )

    for term in profile.lexicon_avoid:
        normalized = term.strip().lower()
        if not normalized or normalized == "empty intensifiers without evidence":
            continue
        index = text.lower().find(normalized)
        if index < 0:
            continue
        finding = _make_finding(
            "voice_mismatch",
            text,
            index,
            index + len(normalized),
            f"Passage conflicts with profile avoid lexicon '{term}'.",
        )
        if finding["id"] not in {entry["id"] for entry in findings}:
            findings.append(finding)
    return findings


def _is_rhetorical_refrain(members: list[dict[str, Any]]) -> bool:
    excerpts = [member["excerpt"].strip() for member in members]
    normalized = {excerpt.lower() for excerpt in excerpts}
    if len(normalized) != 1:
        return False
    excerpt = excerpts[0]
    if re.match(r"^#+\s", excerpt):
        return True
    if word_count(excerpt) <= _REFRAIN_MAX_WORDS:
        return True
    return False


def _blank_match(match: re.Match[str]) -> str:
    return re.sub(r"[^\n]", " ", match.group(0))


def _mask_jsx_components(text: str) -> str:
    """Blank out self-closing JSX component markup, preserving length and newlines so
    character offsets computed against the result stay valid against the original text."""
    text = _JSX_SELF_CLOSING_COMPONENT_RE.sub(_blank_match, text)
    text = _MARKUS_DIRECTIVE_OPEN_RE.sub(_blank_match, text)
    text = _MARKUS_DIRECTIVE_CLOSE_RE.sub(_blank_match, text)
    return text


def _mask_image_markup(text: str) -> str:
    """Blank image alt/url markup before redundancy shingling; spans stay aligned with original."""
    text = _MARKDOWN_LINKED_IMAGE_RE.sub(_blank_match, text)
    text = _MARKDOWN_IMAGE_RE.sub(_blank_match, text)
    text = _HTML_IMG_RE.sub(_blank_match, text)
    return text


def _mask_for_redundancy_shingling(text: str) -> str:
    return _mask_image_markup(_mask_jsx_components(text))


def _range_within_spans(spans: list[tuple[int, int]], start: int, end: int) -> bool:
    return any(span_start <= start and end <= span_end for span_start, span_end in spans)


def _markdown_emphasis_spans(text: str) -> list[tuple[int, int]]:
    """Character spans of text wrapped in single *...* or _..._ emphasis (not ** bold)."""
    spans: list[tuple[int, int]] = []
    for delimiter in ("*", "_"):
        index = 0
        while index < len(text):
            if text[index] != delimiter:
                index += 1
                continue
            if index + 1 < len(text) and text[index + 1] == delimiter:
                index += 2
                continue
            close = index + 1
            while close < len(text):
                if text[close] != delimiter:
                    close += 1
                    continue
                if close + 1 < len(text) and text[close + 1] == delimiter:
                    close += 1
                    continue
                break
            if close >= len(text) or text[close] != delimiter:
                index += 1
                continue
            if close > index + 1:
                spans.append((index + 1, close))
            index = close + 1
    return spans


def _markus_directive_body_spans(text: str) -> list[tuple[int, int]]:
    """Inner prose between a Markus block directive open line and its closing `:::`."""
    spans: list[tuple[int, int]] = []
    line_start = 0
    body_start: int | None = None
    while line_start <= len(text):
        line_end = text.find("\n", line_start)
        if line_end < 0:
            line_end = len(text)
        line = text[line_start:line_end]
        if body_start is not None:
            if _MARKUS_DIRECTIVE_CLOSE_RE.match(line):
                if body_start < line_start:
                    spans.append((body_start, line_start))
                body_start = None
        elif _MARKUS_DIRECTIVE_OPEN_RE.match(line):
            body_start = line_end + 1 if line_end < len(text) else line_end
        if line_end == len(text):
            break
        line_start = line_end + 1
    return spans


def _is_quoted_redundancy_ngram(
    text: str,
    gram_start: int,
    gram_end: int,
    emphasis_spans: list[tuple[int, int]],
    markus_body_spans: list[tuple[int, int]],
) -> bool:
    """True when a four-gram's character range sits in quoted material (redundancy only)."""
    if _is_blockquote_line(text, gram_start) and _is_blockquote_line(text, max(gram_start, gram_end - 1)):
        return True
    if _range_within_spans(emphasis_spans, gram_start, gram_end):
        return True
    if _range_within_spans(markus_body_spans, gram_start, gram_end):
        return True
    return False


def _check_redundancy(text: str) -> list[dict[str, Any]]:
    masked = _mask_for_redundancy_shingling(text)
    emphasis_spans = _markdown_emphasis_spans(text)
    markus_body_spans = _markus_directive_body_spans(text)
    shingles: dict[str, list[tuple[int, int, int, int]]] = {}
    token_pattern = re.compile(r"[A-Za-z0-9']+")
    for _masked_sentence, start, end in sentence_spans(masked):
        token_spans = [
            (match.group().lower(), start + match.start(), start + match.end())
            for match in token_pattern.finditer(masked[start:end])
        ]
        for index in range(len(token_spans) - 3):
            shingle = " ".join(token[0] for token in token_spans[index : index + 4])
            gram_start = token_spans[index][1]
            gram_end = token_spans[index + 3][2]
            shingles.setdefault(shingle, []).append((start, end, gram_start, gram_end))

    groups: list[dict[str, Any]] = []
    seen_group_ids: set[str] = set()
    for occurrences in shingles.values():
        if len(occurrences) < 2:
            continue
        if all(
            _is_quoted_redundancy_ngram(text, gram_start, gram_end, emphasis_spans, markus_body_spans)
            for _, _, gram_start, gram_end in occurrences
        ):
            continue
        unique_spans = list(dict.fromkeys((start, end) for start, end, _, _ in occurrences))
        if len(unique_spans) < 2:
            continue
        members = []
        for start, end in unique_spans:
            member_id = stable_finding_id("redundancy", text, start, end)
            members.append(
                {
                    "id": member_id,
                    "kind": "redundancy",
                    "excerpt": text[start:end],
                    "span": {"start": start, "end": end},
                    "rationale": "Repeated phrasing across the draft.",
                    "source": FINDING_SOURCE_PROFILE,
                }
            )
        if _is_rhetorical_refrain(members):
            continue
        group_id = stable_repetition_group_id([member["id"] for member in members])
        if group_id in seen_group_ids:
            continue
        seen_group_ids.add(group_id)
        groups.append(
            {
                "id": group_id,
                "kind": "redundancy",
                "members": members,
                "rationale": "Multiple passages repeat the same four-word phrase.",
            }
        )
    return groups


def _sentence_has_statistical_claim(sentence: str) -> bool:
    if _STAT_PERCENT_PATTERN.search(sentence):
        return True
    if _STAT_MULTIPLIER_PATTERN.search(sentence):
        return True
    if _STAT_COUNT_UNIT_PATTERN.search(sentence):
        return True
    return False


def _is_blockquote_line(text: str, start: int) -> bool:
    """A Markdown blockquote is quoted material -- someone else's words, not
    the narrator's own claim -- so it should never be checked as if the
    narrator asserted it."""
    return bool(_BLOCKQUOTE_LINE_PATTERN.match(line_at_offset(text, start)))


def _sentence_excluded_from_attribution(text: str, sentence: str, start: int) -> bool:
    line = line_at_offset(text, start)
    if _LIST_ORDINAL_LINE_PATTERN.match(line):
        return True
    if _BLOCKQUOTE_LINE_PATTERN.match(line):
        return True
    if _STICKER_NUMBER_PATTERN.search(sentence) and not _STAT_PERCENT_PATTERN.search(sentence):
        return True
    return False


def _normalized_lexicon_avoid(lexicon_avoid: tuple[str, ...]) -> set[str]:
    normalized: set[str] = set()
    for term in lexicon_avoid:
        cleaned = term.strip().lower()
        if cleaned and cleaned != "empty intensifiers without evidence":
            normalized.add(cleaned)
    return normalized


def _occupied_spans(findings: list[dict[str, Any]]) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    for finding in findings:
        span = finding.get("span")
        if not isinstance(span, dict):
            continue
        start = span.get("start")
        end = span.get("end")
        if isinstance(start, int) and isinstance(end, int):
            spans.append((start, end))
    return spans


def _spans_overlap(start: int, end: int, occupied: list[tuple[int, int]]) -> bool:
    return any(start < occupied_end and end > occupied_start for occupied_start, occupied_end in occupied)


def _rules_term_conflicts_with_lexicon(term: str, lexicon_avoid: set[str]) -> bool:
    return term.strip().lower() in lexicon_avoid


def _profile_rule_finding(
    text: str,
    start: int,
    end: int,
    rationale: str,
    *,
    kind: str = "vague_claim",
) -> dict[str, Any]:
    return _make_finding(kind, text, start, end, f"{PROFILE_RULE_PREFIX} {rationale}")


def _check_profile_rules(
    text: str,
    style_profile: LoadedStyleProfile,
    *,
    generic_passages: list[dict[str, Any]],
    voice_observations: list[dict[str, Any]],
    surface: str | None = None,
) -> dict[str, list[dict[str, Any]]]:
    rules = style_profile.profile.rules
    effective_contrast_cap = rules.contrast_cap
    if surface is not None and surface in rules.by_surface:
        effective_contrast_cap = rules.by_surface[surface]

    if not any(
        (
            rules.banned_phrases,
            rules.banned_intensifiers,
            rules.banned_patterns,
            rules.preferred_phrasing,
            effective_contrast_cap is not None,
            rules.no_emojis,
        )
    ):
        return {"generic_passages": [], "voice_observations": []}

    lexicon_avoid = _normalized_lexicon_avoid(style_profile.profile.lexicon_avoid)
    occupied = _occupied_spans(generic_passages) + _occupied_spans(voice_observations)
    profile_generic: list[dict[str, Any]] = []
    profile_voice: list[dict[str, Any]] = []
    lowered_text = text.lower()

    for phrase in rules.banned_phrases:
        normalized_phrase = phrase.lower()
        if normalized_phrase in lexicon_avoid:
            continue
        search_from = 0
        while True:
            index = lowered_text.find(normalized_phrase, search_from)
            if index < 0:
                break
            start = index
            end = index + len(normalized_phrase)
            if _spans_overlap(start, end, occupied):
                search_from = end
                continue
            finding = _profile_rule_finding(
                text,
                start,
                end,
                f"banned phrase '{phrase}'",
            )
            profile_generic.append(finding)
            occupied.append((start, end))
            search_from = end

    for from_phrase, to_phrase in rules.preferred_phrasing:
        normalized_from = from_phrase.lower()
        if normalized_from in lexicon_avoid:
            continue
        search_from = 0
        while True:
            index = lowered_text.find(normalized_from, search_from)
            if index < 0:
                break
            start = index
            end = index + len(normalized_from)
            if _spans_overlap(start, end, occupied):
                search_from = end
                continue
            profile_generic.append(
                _profile_rule_finding(
                    text,
                    start,
                    end,
                    f'prefer "{to_phrase}" over "{from_phrase}"',
                )
            )
            occupied.append((start, end))
            search_from = end

    for intensifier in rules.banned_intensifiers:
        if _rules_term_conflicts_with_lexicon(intensifier, lexicon_avoid):
            continue
        pattern = re.compile(rf"\b{re.escape(intensifier)}\b", re.IGNORECASE)
        for match in pattern.finditer(text):
            start = match.start()
            end = match.end()
            if _spans_overlap(start, end, occupied):
                continue
            profile_generic.append(
                _profile_rule_finding(
                    text,
                    start,
                    end,
                    f"banned intensifier '{intensifier}'",
                )
            )
            occupied.append((start, end))

    for pattern, message in rules.banned_patterns:
        compiled = re.compile(pattern)
        for match in compiled.finditer(text):
            start = match.start()
            end = match.end()
            if _spans_overlap(start, end, occupied):
                continue
            profile_generic.append(_profile_rule_finding(text, start, end, message))
            occupied.append((start, end))

    if effective_contrast_cap is not None:
        contrast_count = len(re.findall(r",\s*not\b", text, flags=re.IGNORECASE))
        if contrast_count > effective_contrast_cap:
            profile_voice.append(
                _profile_rule_finding(
                    text,
                    0,
                    len(text),
                    (
                        f"{contrast_count} 'X, not Y' contrast constructions "
                        f"(cap is {effective_contrast_cap})"
                    ),
                    kind="voice_mismatch",
                )
            )

    if rules.no_emojis:
        for match in _EMOJI_PATTERN.finditer(text):
            start, end = match.start(), match.end()
            if _spans_overlap(start, end, occupied):
                continue
            profile_generic.append(_profile_rule_finding(text, start, end, "contains an emoji character"))
            occupied.append((start, end))

    return {"generic_passages": profile_generic, "voice_observations": profile_voice}


def _check_required_facts(text: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for sentence, start, end in sentence_spans(text):
        if not _sentence_has_statistical_claim(sentence):
            continue
        if _sentence_excluded_from_attribution(text, sentence, start):
            continue
        if _CITATION_PATTERN.search(sentence):
            continue
        findings.append(
            _make_finding(
                "missing_attribution",
                text,
                start,
                end,
                "Numeric or statistical claim lacks attributable evidence.",
            )
        )
    return findings
