from __future__ import annotations

import re
from typing import Any

from .editorial_density import analyze_density, density_summary_as_dict
from .editorial_diagnosis_schema import (
    FINDING_SOURCE_PROFILE,
    SCHEMA_VERSION,
    stable_finding_id,
    stable_repetition_group_id,
    validate_diagnosis,
)
from .editorial_style import LoadedStyleProfile, OpeningScreenRules
from .editorial_text import line_at_offset, paragraphs, sentence_spans, sentences, word_count
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

    generic_passages: list[dict[str, Any]] = []
    unsupported_claims: list[dict[str, Any]] = []
    voice_observations: list[dict[str, Any]] = []
    required_facts: list[dict[str, Any]] = []

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

    density_summary: dict[str, Any] | None = None
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
    return validate_diagnosis(result)


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
    r"^(?:#|\||>|\{|```|---|import\s|export\s|[-*+]\s|\d+[.)]\s)"
)
# A paragraph that opens with an inline tag is still prose when words remain
# once the tags are taken out, as with an opening sentence that starts on an
# emphasised product name. A paragraph that opens with a block element
# (figure, div, p, a component) or with an image is markup, caption included.
_MARKUP_LED_PARAGRAPH_PATTERN = re.compile(r"^(?:<|!\[)")
_INLINE_TAG_LED_PARAGRAPH_PATTERN = re.compile(r"^<(?:em|strong|a|mark|code|i|b|span|abbr|cite|q|s|u)\b", re.IGNORECASE)
_HTML_TAG_PATTERN = re.compile(r"<[^>]*>")
_MINIMUM_WORDS_FOR_PROSE_AFTER_MARKUP = 3
# A paragraph that is one emphasised run and nothing else, right after an
# image or a block of markup, is a caption, not an opening paragraph. The same
# run with prose before it is an italic lede and stays prose.
_CAPTION_PARAGRAPH_PATTERN = re.compile(r"(?:\*[^*\n]+\*|_[^_\n]+_)")


def _markup_led_paragraph_is_prose(paragraph: str) -> bool:
    if not _INLINE_TAG_LED_PARAGRAPH_PATTERN.match(paragraph):
        return False
    without_markup = _HTML_TAG_PATTERN.sub(" ", paragraph)
    return len(re.findall(r"[A-Za-z]+", without_markup)) >= _MINIMUM_WORDS_FOR_PROSE_AFTER_MARKUP


def _prose_paragraph_spans(text: str) -> list[tuple[str, int, int]]:
    spans: list[tuple[str, int, int]] = []
    cursor = 0
    previous_paragraph_was_markup = False
    for paragraph in paragraphs(text):
        paragraph_start = text.find(paragraph, cursor)
        if paragraph_start < 0:
            paragraph_start = cursor
        cursor = paragraph_start + len(paragraph)
        paragraph_text = paragraph.strip()
        follows_markup = previous_paragraph_was_markup
        is_markup = bool(_MARKUP_LED_PARAGRAPH_PATTERN.match(paragraph_text)) and not _markup_led_paragraph_is_prose(
            paragraph_text
        )
        previous_paragraph_was_markup = is_markup
        if is_markup or _NON_PROSE_PARAGRAPH_PATTERN.match(paragraph_text):
            continue
        if follows_markup and _CAPTION_PARAGRAPH_PATTERN.fullmatch(paragraph_text):
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
    if _NUMERIC_STATEMENT_PATTERN.search(stripped_sentence) or word_count(stripped_sentence) == 0:
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
            and 0 < sentence_word_counts[last_index] <= _TERSE_CLOSING_TAG_MAXIMUM_WORDS
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
_DEFINITION_AFTER_TERM_PATTERN = re.compile(
    r"^(?:\s*[,(:\u2014\u2013](?!\s*(?:and|but|or|so|then)\b)|\s+-\s|\s+(?:is|are|means)\s+(?:a|an|the)\b)"
)
_DEFINITION_BEFORE_TERM_PATTERN = re.compile(r"\b(?:called|named|known as)\s+(?:an?\s+|the\s+)?$", re.IGNORECASE)
_DIGIT_PATTERN = re.compile(r"\d")
_MARKDOWN_LINK_ADDRESS_PATTERN = re.compile(r"\]\([^)]*\)")


def _prose_has_number(paragraph: str) -> bool:
    without_markup = _HTML_TAG_PATTERN.sub(" ", _MARKDOWN_LINK_ADDRESS_PATTERN.sub("]", paragraph))
    return bool(_DIGIT_PATTERN.search(without_markup))


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

    if rules.require_number and not _prose_has_number(opening_paragraph):
        later_prose_has_number = any(_prose_has_number(paragraph) for paragraph, _, _ in prose_paragraphs[1:])
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
