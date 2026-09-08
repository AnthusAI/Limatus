"""Standfirst-specific checks: the one or two sentences under a headline.

A standfirst is read by someone who has seen only the headline, so it fails
in ways ordinary body prose doesn't -- a name the reader hasn't met yet, a
term that reads as plain English only inside the trade, a sentence that
just restates the description above it. Those failures are checkable, and
this module checks the checkable half; whether the standfirst actually says
what the idea changes for the reader stays with a human editor.
"""

from __future__ import annotations

import re
from typing import Any

from .editorial_diagnosis_schema import stable_finding_id
from .editorial_style import LoadedStyleProfile, StandfirstRules

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]*")
_CAPITALIZED_WORD_RE = re.compile(r"[A-Z][a-z][A-Za-z'-]*")


def _finding(kind: str, standfirst: str, start: int, end: int, rationale: str) -> dict[str, Any]:
    return {
        "id": stable_finding_id(kind, standfirst, start, end),
        "kind": kind,
        "excerpt": standfirst[start:end],
        "span": {"start": start, "end": end},
        "rationale": rationale,
    }


def _split_sentences(text: str) -> list[str]:
    return [sentence for sentence in re.split(r"(?<=[.!?])\s+", text.strip()) if sentence]


def _check_shape(standfirst: str, sentences: list[str], rules: StandfirstRules) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    word_count = len(standfirst.split())

    if len(sentences) > rules.max_sentences:
        findings.append(
            _finding(
                "standfirst_shape",
                standfirst,
                0,
                len(standfirst),
                f"runs to {len(sentences)} sentences (cap is {rules.max_sentences})",
            )
        )
    if word_count < rules.min_words:
        findings.append(
            _finding(
                "standfirst_shape",
                standfirst,
                0,
                len(standfirst),
                f"is {word_count} words, too short to say what the idea changes "
                f"(minimum {rules.min_words})",
            )
        )
    if word_count > rules.max_words:
        findings.append(
            _finding(
                "standfirst_shape",
                standfirst,
                0,
                len(standfirst),
                f"is {word_count} words (maximum {rules.max_words})",
            )
        )

    cursor = 0
    for sentence in sentences:
        start = standfirst.index(sentence, cursor)
        end = start + len(sentence)
        cursor = end
        length = len(sentence.split())
        if length > rules.max_sentence_words:
            findings.append(
                _finding(
                    "standfirst_shape",
                    standfirst,
                    start,
                    end,
                    f"is a {length}-word sentence (maximum {rules.max_sentence_words})",
                )
            )
    return findings


def _is_proper_noun_in_body(word: str, body_text: str) -> bool:
    """A word capitalized mid-sentence somewhere in the body is a name; an
    ordinary sentence-opener like "Told" or "Give" never is. This is how the
    first word of a sentence gets checked at all, since capitalization alone
    says nothing about it there."""
    for match in re.finditer(rf"\b{re.escape(word)}\b", body_text):
        if not match.group(0)[0].isupper():
            continue
        preceding = body_text[max(0, match.start() - 40) : match.start()]
        if re.search(r"[a-z,]\s+$", preceding):
            return True
    return False


def _check_proper_nouns(
    standfirst: str, sentences: list[str], rules: StandfirstRules, body_text: str
) -> list[dict[str, Any]]:
    allowed = {name.lower() for name in rules.allowed_proper_nouns}
    findings: list[dict[str, Any]] = []
    cursor = 0

    for sentence in sentences:
        sentence_start = standfirst.index(sentence, cursor)
        cursor = sentence_start + len(sentence)
        words = _WORD_RE.findall(sentence)
        if not words:
            continue

        candidates = list(enumerate(words))
        first_index, first_word = candidates[0]
        if _CAPITALIZED_WORD_RE.fullmatch(first_word):
            if first_word.lower() not in allowed and _is_proper_noun_in_body(first_word, body_text):
                offset = sentence_start + sentence.index(first_word)
                findings.append(
                    _finding(
                        "standfirst_proper_noun",
                        standfirst,
                        offset,
                        offset + len(first_word),
                        f"opens on '{first_word}', a name the reader has only the headline to place it by",
                    )
                )

        for _, word in candidates[1:]:
            if not _CAPITALIZED_WORD_RE.fullmatch(word):
                continue
            if word.lower() in allowed:
                continue
            offset = sentence_start + sentence.index(word)
            findings.append(
                _finding(
                    "standfirst_proper_noun",
                    standfirst,
                    offset,
                    offset + len(word),
                    f"names '{word}', which the reader has only the headline to place it by",
                )
            )
    return findings


def _check_insider_terms(standfirst: str, rules: StandfirstRules) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for term in rules.insider_terms:
        for match in re.finditer(rf"\b{re.escape(term)}\b", standfirst, flags=re.IGNORECASE):
            findings.append(
                _finding(
                    "standfirst_insider_term",
                    standfirst,
                    match.start(),
                    match.end(),
                    f"uses '{term}', which reads as plain English only to somebody who already works in this",
                )
            )
    return findings


def _check_insider_patterns(standfirst: str, rules: StandfirstRules) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for pattern, message in rules.insider_patterns:
        match = re.search(pattern, standfirst, flags=re.IGNORECASE)
        if match:
            findings.append(
                _finding(
                    "standfirst_insider_pattern",
                    standfirst,
                    match.start(),
                    match.end(),
                    f"says '{match.group(0)}', which {message}",
                )
            )
    return findings


def _check_description_overlap(
    standfirst: str, description: str, rules: StandfirstRules
) -> list[dict[str, Any]]:
    standfirst_words = set(re.findall(r"[a-z']+", standfirst.lower()))
    description_words = set(re.findall(r"[a-z']+", description.lower()))
    if not standfirst_words or not description:
        return []
    overlap = len(standfirst_words & description_words) / len(standfirst_words)
    if overlap > rules.max_description_overlap:
        return [
            _finding(
                "standfirst_description_overlap",
                standfirst,
                0,
                len(standfirst),
                f"repeats {overlap:.0%} of the description -- one of the two has stopped doing its own job",
            )
        ]
    return []


def check_standfirst(
    standfirst_text: str,
    *,
    style_profile: LoadedStyleProfile,
    body_text: str = "",
    description: str = "",
) -> dict[str, Any]:
    """Check a standfirst candidate against the profile's ``standfirst`` rules.

    Returns validated-shape findings (same ``id``/``kind``/``excerpt``/``span``/
    ``rationale`` shape as ``diagnose``), so a copywriting agent can iterate on
    a candidate sentence without writing it to the file first. Raises
    ``ValueError`` if the profile has no ``standfirst`` rules configured.
    """
    rules = style_profile.profile.standfirst
    if rules is None:
        raise ValueError("Style profile has no 'standfirst' rules configured.")

    standfirst = standfirst_text.strip()
    if not standfirst:
        return {"findings": []}

    sentences = _split_sentences(standfirst)
    findings: list[dict[str, Any]] = []
    findings.extend(_check_shape(standfirst, sentences, rules))
    findings.extend(_check_proper_nouns(standfirst, sentences, rules, body_text))
    findings.extend(_check_insider_terms(standfirst, rules))
    findings.extend(_check_insider_patterns(standfirst, rules))
    findings.extend(_check_description_overlap(standfirst, description, rules))
    return {"findings": findings}
