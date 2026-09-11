from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_FORBIDDEN_KEY_PATTERN = re.compile(
    r"(detector|detectorscore|ai_detector|aidetector|perplexity_score|burstiness|ai_score|human_score)",
    re.IGNORECASE,
)

# When checks is omitted from a style profile, every diagnose check is enabled.
DEFAULT_DIAGNOSE_CHECKS: dict[str, bool] = {
    "emptyLeadin": True,
    "listShapedProse": True,
    "vagueClaim": True,
    "unsupportedCertainty": True,
    "uniformCadence": True,
    "redundancy": True,
    "voiceMismatch": True,
    "missingAttribution": True,
    "informationDensity": True,
    "overusedWords": True,
    "uncontractedForms": True,
}

DEFAULT_DENSITY_THRESHOLDS = {
    "minWords": 400,
    "minLexicalDensity": 0.45,
    "maxGzipRatio": 0.35,
}

RULES_FIELD_NAMES = frozenset(
    {
        "bannedPhrases",
        "bannedIntensifiers",
        "bannedPatterns",
        "preferredPhrasing",
        "contrastCap",
        "noEmojis",
        "bySurface",
    }
)

STANDFIRST_FIELD_NAMES = frozenset(
    {
        "maxSentences",
        "minWords",
        "maxWords",
        "maxSentenceWords",
        "allowedProperNouns",
        "insiderTerms",
        "insiderPatterns",
        "maxDescriptionOverlap",
    }
)

HEADLINE_FIELD_NAMES = frozenset({"when", "order", "title", "subtitle"})
HEADLINE_TITLE_FIELD_NAMES = frozenset({"key"})
HEADLINE_SUBTITLE_FIELD_NAMES = frozenset({"key", "role"})
ALLOWED_HEADLINE_WHEN = frozenset({"afterBody", "never"})
ALLOWED_HEADLINE_JOBS = frozenset({"title", "subtitle"})
ALLOWED_HEADLINE_SUBTITLE_ROLES = frozenset({"articleSummary"})
DEFAULT_HEADLINE_ORDER = ("title", "subtitle")

COMPARE_SECTION_FIELD_NAMES = frozenset({"hardConstraints"})

COMPARE_HARD_CONSTRAINT_UNSUPPORTED_CLAIMS_INCREASE = "unsupported_claims_increase"

ALLOWED_COMPARE_HARD_CONSTRAINT_NAMES = frozenset({COMPARE_HARD_CONSTRAINT_UNSUPPORTED_CLAIMS_INCREASE})

DEFAULT_COMPARE_HARD_CONSTRAINTS: tuple[str, ...] = (COMPARE_HARD_CONSTRAINT_UNSUPPORTED_CLAIMS_INCREASE,)


class StyleProfileValidationError(ValueError):
    """Raised when a style profile document or linked samples fail validation."""


@dataclass(frozen=True)
class EditorialRules:
    banned_phrases: tuple[str, ...]
    banned_intensifiers: tuple[str, ...]
    banned_patterns: tuple[tuple[str, str], ...]
    preferred_phrasing: tuple[tuple[str, str], ...]
    contrast_cap: int | None
    no_emojis: bool
    # Surface name -> contrast cap override for that surface (None means "off
    # for this surface"). A surface absent from this mapping falls back to
    # contrast_cap. Lets one profile say "marketing copy gets a looser cap,
    # legal pages get none" without forking the whole profile per surface.
    by_surface: dict[str, int | None]


@dataclass(frozen=True)
class DensityThresholds:
    min_words: int
    min_lexical_density: float
    max_gzip_ratio: float


@dataclass(frozen=True)
class StandfirstRules:
    max_sentences: int
    min_words: int
    max_words: int
    max_sentence_words: int
    allowed_proper_nouns: tuple[str, ...]
    insider_terms: tuple[str, ...]
    insider_patterns: tuple[tuple[str, str], ...]
    max_description_overlap: float


@dataclass(frozen=True)
class HeadlineTitleConfig:
    key: str


@dataclass(frozen=True)
class HeadlineSubtitleConfig:
    key: str
    role: str


@dataclass(frozen=True)
class HeadlineConfig:
    when: str
    order: tuple[str, ...]
    title: HeadlineTitleConfig
    subtitle: HeadlineSubtitleConfig


@dataclass(frozen=True)
class JudgeConfig:
    provider: str
    model: str


DEFAULT_JUDGE_MODEL = "gpt-5.6-terra"


@dataclass(frozen=True)
class StyleProfile:
    publication_key: str
    voice_name: str
    audience: str
    tone: tuple[str, ...]
    sentence_style: tuple[str, ...]
    voice_patterns: tuple[str, ...]
    structure: tuple[str, ...]
    lexicon_prefer: tuple[str, ...]
    lexicon_avoid: tuple[str, ...]
    evidence_rules: tuple[str, ...]
    reference_sample_refs: tuple[dict[str, str], ...]
    checks: dict[str, bool]
    rules: EditorialRules
    density: DensityThresholds
    standfirst: StandfirstRules | None
    headline: HeadlineConfig | None
    judge: JudgeConfig | None
    editorial_aim: str | None
    compare_hard_constraints: tuple[str, ...]


@dataclass(frozen=True)
class ReferenceSample:
    id: str
    title: str
    url: str
    path: Path
    body: str


@dataclass(frozen=True)
class LoadedStyleProfile:
    profile: StyleProfile
    samples: tuple[ReferenceSample, ...]


def load_style_profile(path: str | Path) -> LoadedStyleProfile:
    profile_path = Path(path).resolve()
    try:
        source = profile_path.read_text(encoding="utf-8")
        if profile_path.suffix.lower() == ".json":
            raw = json.loads(source)
        else:
            raw = yaml.safe_load(source)
    except (json.JSONDecodeError, yaml.YAMLError, UnicodeDecodeError) as exc:
        raise StyleProfileValidationError(
            f"Could not parse style profile configuration {profile_path}: {exc}"
        ) from exc
    if not isinstance(raw, dict):
        raise StyleProfileValidationError(f"Style profile must be a mapping: {profile_path}")

    _assert_no_forbidden_keys(raw, profile_path)
    profile = _parse_profile(raw, profile_path)
    samples = _load_reference_samples(profile, profile_path.parent)
    return LoadedStyleProfile(profile=profile, samples=samples)


def _assert_no_forbidden_keys(value: Any, location: str | Path, key_path: str = "") -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            key_text = str(key)
            current_path = f"{key_path}.{key_text}" if key_path else key_text
            normalized = re.sub(r"[^a-z0-9]", "", key_text.lower())
            if _FORBIDDEN_KEY_PATTERN.search(normalized):
                raise StyleProfileValidationError(
                    f"Style profile contains forbidden detector-score field '{current_path}' in {location}"
                )
            _assert_no_forbidden_keys(nested, location, current_path)
        return
    if isinstance(value, list):
        for index, nested in enumerate(value):
            _assert_no_forbidden_keys(nested, location, f"{key_path}[{index}]")


def _parse_profile(raw: dict[str, Any], profile_path: Path) -> StyleProfile:
    if raw.get("schemaVersion") != 1:
        raise StyleProfileValidationError(f"Unsupported schemaVersion in {profile_path}")

    publication_key = _require_non_empty_string(raw.get("publicationKey"), "publicationKey", profile_path)
    voice = raw.get("voice")
    if not isinstance(voice, dict):
        raise StyleProfileValidationError(f"Missing voice mapping in {profile_path}")
    voice_name = _require_non_empty_string(voice.get("name"), "voice.name", profile_path)
    audience = _require_non_empty_string(raw.get("audience"), "audience", profile_path)
    tone = _require_string_list(raw.get("tone"), "tone", profile_path)
    sentence_style = _require_string_list(raw.get("sentenceStyle"), "sentenceStyle", profile_path)
    voice_patterns = _optional_string_list(raw.get("voicePatterns"), "voicePatterns", profile_path)
    structure = _require_string_list(raw.get("structure"), "structure", profile_path)

    lexicon = raw.get("lexicon")
    if not isinstance(lexicon, dict):
        raise StyleProfileValidationError(f"Missing lexicon mapping in {profile_path}")
    lexicon_prefer = _require_string_list(lexicon.get("prefer"), "lexicon.prefer", profile_path)
    lexicon_avoid = _require_string_list(lexicon.get("avoid"), "lexicon.avoid", profile_path)
    evidence_rules = _require_string_list(raw.get("evidenceRules"), "evidenceRules", profile_path)

    reference_samples = raw.get("referenceSamples")
    if not isinstance(reference_samples, list):
        raise StyleProfileValidationError(f"Missing referenceSamples list in {profile_path}")
    if not 5 <= len(reference_samples) <= 10:
        raise StyleProfileValidationError(
            f"referenceSamples must contain 5 to 10 entries in {profile_path}; found {len(reference_samples)}"
        )

    refs: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    for index, entry in enumerate(reference_samples):
        if not isinstance(entry, dict):
            raise StyleProfileValidationError(f"referenceSamples[{index}] must be a mapping in {profile_path}")
        sample_id = _require_non_empty_string(entry.get("id"), f"referenceSamples[{index}].id", profile_path)
        if sample_id in seen_ids:
            raise StyleProfileValidationError(f"Duplicate reference sample id '{sample_id}' in {profile_path}")
        seen_ids.add(sample_id)
        title = _require_non_empty_string(entry.get("title"), f"referenceSamples[{index}].title", profile_path)
        url = _require_non_empty_string(entry.get("url"), f"referenceSamples[{index}].url", profile_path)
        rel_path = _require_non_empty_string(entry.get("path"), f"referenceSamples[{index}].path", profile_path)
        refs.append({"id": sample_id, "title": title, "url": url, "path": rel_path})

    checks = _parse_checks(raw.get("checks"), profile_path)
    rules = _parse_rules(raw.get("rules"), profile_path)
    density = _parse_density(raw.get("density"), profile_path)
    standfirst = _parse_standfirst(raw.get("standfirst"), profile_path)
    headline = _parse_headline(raw.get("headline"), profile_path)
    judge = _parse_judge(raw.get("judge"), profile_path)
    editorial_aim = _parse_editorial_aim(raw.get("editorialAim"), profile_path)
    compare_hard_constraints = _parse_compare_section(raw.get("compare"), profile_path)

    return StyleProfile(
        publication_key=publication_key,
        voice_name=voice_name,
        audience=audience,
        tone=tuple(tone),
        sentence_style=tuple(sentence_style),
        voice_patterns=tuple(voice_patterns),
        structure=tuple(structure),
        lexicon_prefer=tuple(lexicon_prefer),
        lexicon_avoid=tuple(lexicon_avoid),
        evidence_rules=tuple(evidence_rules),
        reference_sample_refs=tuple(refs),
        checks=checks,
        rules=rules,
        density=density,
        standfirst=standfirst,
        headline=headline,
        judge=judge,
        editorial_aim=editorial_aim,
        compare_hard_constraints=compare_hard_constraints,
    )


def _parse_editorial_aim(value: Any, profile_path: Path) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise StyleProfileValidationError(
            f"editorialAim must be a non-empty string when set in {profile_path}"
        )
    return value.strip()


def _parse_compare_section(value: Any, profile_path: Path) -> tuple[str, ...]:
    if value is None:
        return DEFAULT_COMPARE_HARD_CONSTRAINTS
    if not isinstance(value, dict):
        raise StyleProfileValidationError(f"compare must be a mapping in {profile_path}")
    unknown = set(value) - COMPARE_SECTION_FIELD_NAMES
    if unknown:
        joined = ", ".join(sorted(str(key) for key in unknown))
        raise StyleProfileValidationError(f"Unknown compare keys in {profile_path}: {joined}")
    hard_constraints = value.get("hardConstraints")
    if hard_constraints is None:
        return DEFAULT_COMPARE_HARD_CONSTRAINTS
    if not isinstance(hard_constraints, list):
        raise StyleProfileValidationError(f"compare.hardConstraints must be a list in {profile_path}")
    names: list[str] = []
    for index, entry in enumerate(hard_constraints):
        if not isinstance(entry, str) or not entry.strip():
            raise StyleProfileValidationError(
                f"compare.hardConstraints[{index}] must be a non-empty string in {profile_path}"
            )
        name = entry.strip()
        if name not in ALLOWED_COMPARE_HARD_CONSTRAINT_NAMES:
            raise StyleProfileValidationError(
                f"Unknown compare.hardConstraints name '{name}' in {profile_path}; "
                f"allowed: {', '.join(sorted(ALLOWED_COMPARE_HARD_CONSTRAINT_NAMES))}"
            )
        names.append(name)
    return tuple(names)


def _parse_judge(value: Any, profile_path: Path) -> JudgeConfig | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise StyleProfileValidationError(f"judge must be a mapping in {profile_path}")
    provider_raw = value.get("provider")
    if provider_raw is None or (isinstance(provider_raw, str) and not provider_raw.strip()):
        return None
    provider = str(provider_raw).strip().lower()
    if provider != "openai":
        raise StyleProfileValidationError(
            f"Unsupported judge.provider '{provider_raw}' in {profile_path}; only openai is supported."
        )
    model_raw = value.get("model")
    if model_raw is None or (isinstance(model_raw, str) and not str(model_raw).strip()):
        model = DEFAULT_JUDGE_MODEL
    else:
        model = str(model_raw).strip()
    return JudgeConfig(provider=provider, model=model)


def _parse_checks(value: Any, profile_path: Path) -> dict[str, bool]:
    checks = dict(DEFAULT_DIAGNOSE_CHECKS)
    if value is None:
        return checks
    if not isinstance(value, dict):
        raise StyleProfileValidationError(f"checks must be a mapping in {profile_path}")
    for key, enabled in value.items():
        if key not in DEFAULT_DIAGNOSE_CHECKS:
            raise StyleProfileValidationError(f"Unknown checks key '{key}' in {profile_path}")
        if not isinstance(enabled, bool):
            raise StyleProfileValidationError(f"checks.{key} must be a boolean in {profile_path}")
        checks[key] = enabled
    return checks


def _empty_rules() -> EditorialRules:
    return EditorialRules(
        banned_phrases=(),
        banned_intensifiers=(),
        banned_patterns=(),
        preferred_phrasing=(),
        contrast_cap=None,
        no_emojis=False,
        by_surface={},
    )


def _parse_rules(value: Any, profile_path: Path) -> EditorialRules:
    if value is None:
        return _empty_rules()
    if not isinstance(value, dict):
        raise StyleProfileValidationError(f"rules must be a mapping in {profile_path}")

    unknown = set(value) - RULES_FIELD_NAMES
    if unknown:
        joined = ", ".join(sorted(unknown))
        raise StyleProfileValidationError(f"Unknown rules keys in {profile_path}: {joined}")

    banned_phrases = _optional_string_list(value.get("bannedPhrases"), "rules.bannedPhrases", profile_path)
    banned_intensifiers = _optional_string_list(
        value.get("bannedIntensifiers"), "rules.bannedIntensifiers", profile_path
    )
    banned_patterns = _parse_banned_patterns(value.get("bannedPatterns"), profile_path)
    preferred_phrasing = _parse_preferred_phrasing(value.get("preferredPhrasing"), profile_path)
    contrast_cap = _parse_contrast_cap(value.get("contrastCap"), profile_path)
    no_emojis = _parse_no_emojis(value.get("noEmojis"), profile_path)
    by_surface = _parse_by_surface(value.get("bySurface"), profile_path)

    return EditorialRules(
        banned_phrases=tuple(banned_phrases),
        banned_intensifiers=tuple(banned_intensifiers),
        banned_patterns=tuple(banned_patterns),
        preferred_phrasing=tuple(preferred_phrasing),
        contrast_cap=contrast_cap,
        no_emojis=no_emojis,
        by_surface=by_surface,
    )


def _parse_no_emojis(value: Any, profile_path: Path) -> bool:
    if value is None:
        return False
    if not isinstance(value, bool):
        raise StyleProfileValidationError(f"rules.noEmojis must be a boolean in {profile_path}")
    return value


def _parse_by_surface(value: Any, profile_path: Path) -> dict[str, int | None]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise StyleProfileValidationError(f"rules.bySurface must be a mapping in {profile_path}")
    resolved: dict[str, int | None] = {}
    for surface, override in value.items():
        if not isinstance(override, dict) or set(override) - {"contrastCap"}:
            raise StyleProfileValidationError(
                f"rules.bySurface.{surface} must be a mapping with only 'contrastCap' in {profile_path}"
            )
        resolved[surface] = _parse_contrast_cap(override.get("contrastCap"), profile_path)
    return resolved


def _parse_headline(value: Any, profile_path: Path) -> HeadlineConfig | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise StyleProfileValidationError(f"headline must be a mapping in {profile_path}")
    unknown = set(value) - HEADLINE_FIELD_NAMES
    if unknown:
        joined = ", ".join(sorted(str(key) for key in unknown))
        raise StyleProfileValidationError(f"Unknown headline keys in {profile_path}: {joined}")
    when = value.get("when", "afterBody")
    if not isinstance(when, str) or when not in ALLOWED_HEADLINE_WHEN:
        raise StyleProfileValidationError(
            f"headline.when must be one of {', '.join(sorted(ALLOWED_HEADLINE_WHEN))} in {profile_path}"
        )
    order_raw = value.get("order")
    if order_raw is None:
        order = DEFAULT_HEADLINE_ORDER
    else:
        if not isinstance(order_raw, list) or not order_raw:
            raise StyleProfileValidationError(f"headline.order must be a non-empty list in {profile_path}")
        order = tuple(str(item).strip() for item in order_raw)
        if len(order) != len(set(order)):
            raise StyleProfileValidationError(f"headline.order entries must be unique in {profile_path}")
        for index, job in enumerate(order):
            if job not in ALLOWED_HEADLINE_JOBS:
                raise StyleProfileValidationError(
                    f"headline.order[{index}] must be one of "
                    f"{', '.join(sorted(ALLOWED_HEADLINE_JOBS))} in {profile_path}"
                )
    title_raw = value.get("title")
    if not isinstance(title_raw, dict):
        raise StyleProfileValidationError(f"headline.title must be a mapping in {profile_path}")
    title_unknown = set(title_raw) - HEADLINE_TITLE_FIELD_NAMES
    if title_unknown:
        joined = ", ".join(sorted(str(key) for key in title_unknown))
        raise StyleProfileValidationError(f"Unknown headline.title keys in {profile_path}: {joined}")
    title_key = _require_non_empty_string(title_raw.get("key"), "headline.title.key", profile_path)
    subtitle_raw = value.get("subtitle")
    if not isinstance(subtitle_raw, dict):
        raise StyleProfileValidationError(f"headline.subtitle must be a mapping in {profile_path}")
    subtitle_unknown = set(subtitle_raw) - HEADLINE_SUBTITLE_FIELD_NAMES
    if subtitle_unknown:
        joined = ", ".join(sorted(str(key) for key in subtitle_unknown))
        raise StyleProfileValidationError(f"Unknown headline.subtitle keys in {profile_path}: {joined}")
    subtitle_key = _require_non_empty_string(subtitle_raw.get("key"), "headline.subtitle.key", profile_path)
    role = _require_non_empty_string(subtitle_raw.get("role"), "headline.subtitle.role", profile_path)
    if role not in ALLOWED_HEADLINE_SUBTITLE_ROLES:
        raise StyleProfileValidationError(
            f"headline.subtitle.role must be one of "
            f"{', '.join(sorted(ALLOWED_HEADLINE_SUBTITLE_ROLES))} in {profile_path}"
        )
    return HeadlineConfig(
        when=when,
        order=order,
        title=HeadlineTitleConfig(key=title_key),
        subtitle=HeadlineSubtitleConfig(key=subtitle_key, role=role),
    )


def _parse_standfirst(value: Any, profile_path: Path) -> StandfirstRules | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise StyleProfileValidationError(f"standfirst must be a mapping in {profile_path}")

    unknown = set(value) - STANDFIRST_FIELD_NAMES
    if unknown:
        joined = ", ".join(sorted(unknown))
        raise StyleProfileValidationError(f"Unknown standfirst keys in {profile_path}: {joined}")

    max_sentences = _require_positive_int(value.get("maxSentences"), "standfirst.maxSentences", profile_path)
    min_words = _require_positive_int(value.get("minWords"), "standfirst.minWords", profile_path)
    max_words = _require_positive_int(value.get("maxWords"), "standfirst.maxWords", profile_path)
    max_sentence_words = _require_positive_int(
        value.get("maxSentenceWords"), "standfirst.maxSentenceWords", profile_path
    )
    allowed_proper_nouns = _optional_string_list(
        value.get("allowedProperNouns"), "standfirst.allowedProperNouns", profile_path
    )
    insider_terms = _optional_string_list(value.get("insiderTerms"), "standfirst.insiderTerms", profile_path)
    insider_patterns = _parse_banned_patterns(value.get("insiderPatterns"), profile_path)
    max_description_overlap = value.get("maxDescriptionOverlap")
    if not isinstance(max_description_overlap, (int, float)) or isinstance(max_description_overlap, bool):
        raise StyleProfileValidationError(f"standfirst.maxDescriptionOverlap must be a number in {profile_path}")

    return StandfirstRules(
        max_sentences=max_sentences,
        min_words=min_words,
        max_words=max_words,
        max_sentence_words=max_sentence_words,
        allowed_proper_nouns=tuple(allowed_proper_nouns),
        insider_terms=tuple(insider_terms),
        insider_patterns=tuple(insider_patterns),
        max_description_overlap=float(max_description_overlap),
    )


def _require_positive_int(value: Any, field_name: str, profile_path: Path) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise StyleProfileValidationError(f"{field_name} must be a positive integer in {profile_path}")
    return value


def _optional_string_list(value: Any, field_name: str, profile_path: Path) -> list[str]:
    if value is None:
        return []
    return _require_string_list(value, field_name, profile_path)


def _parse_preferred_phrasing(value: Any, profile_path: Path) -> list[tuple[str, str]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise StyleProfileValidationError(f"rules.preferredPhrasing must be a list in {profile_path}")

    pairs: list[tuple[str, str]] = []
    for index, entry in enumerate(value):
        if not isinstance(entry, dict):
            raise StyleProfileValidationError(
                f"rules.preferredPhrasing[{index}] must be a mapping in {profile_path}"
            )
        from_phrase = entry.get("from")
        to_phrase = entry.get("to")
        if not isinstance(from_phrase, str) or not from_phrase.strip():
            raise StyleProfileValidationError(
                f"rules.preferredPhrasing[{index}].from must be a non-empty string in {profile_path}"
            )
        if not isinstance(to_phrase, str) or not to_phrase.strip():
            raise StyleProfileValidationError(
                f"rules.preferredPhrasing[{index}].to must be a non-empty string in {profile_path}"
            )
        pairs.append((from_phrase.strip(), to_phrase.strip()))
    return pairs


def _parse_banned_patterns(value: Any, profile_path: Path) -> list[tuple[str, str]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise StyleProfileValidationError(f"rules.bannedPatterns must be a list in {profile_path}")

    patterns: list[tuple[str, str]] = []
    for index, entry in enumerate(value):
        if not isinstance(entry, dict):
            raise StyleProfileValidationError(f"rules.bannedPatterns[{index}] must be a mapping in {profile_path}")
        pattern = entry.get("pattern")
        message = entry.get("message")
        if not isinstance(pattern, str) or not pattern.strip():
            raise StyleProfileValidationError(
                f"rules.bannedPatterns[{index}].pattern must be a non-empty string in {profile_path}"
            )
        if not isinstance(message, str) or not message.strip():
            raise StyleProfileValidationError(
                f"rules.bannedPatterns[{index}].message must be a non-empty string in {profile_path}"
            )
        try:
            re.compile(pattern)
        except re.error as exc:
            raise StyleProfileValidationError(
                f"rules.bannedPatterns[{index}].pattern is not a valid regex in {profile_path}: {exc}"
            ) from exc
        patterns.append((pattern.strip(), message.strip()))
    return patterns


def _parse_contrast_cap(value: Any, profile_path: Path) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or value < 0:
        raise StyleProfileValidationError(f"rules.contrastCap must be a non-negative integer in {profile_path}")
    return value


def _default_density_thresholds() -> DensityThresholds:
    return DensityThresholds(
        min_words=int(DEFAULT_DENSITY_THRESHOLDS["minWords"]),
        min_lexical_density=float(DEFAULT_DENSITY_THRESHOLDS["minLexicalDensity"]),
        max_gzip_ratio=float(DEFAULT_DENSITY_THRESHOLDS["maxGzipRatio"]),
    )


def _parse_density(value: Any, profile_path: Path) -> DensityThresholds:
    defaults = _default_density_thresholds()
    if value is None:
        return defaults
    if not isinstance(value, dict):
        raise StyleProfileValidationError(f"density must be a mapping in {profile_path}")

    unknown = set(value) - {"minWords", "minLexicalDensity", "maxGzipRatio"}
    if unknown:
        joined = ", ".join(sorted(str(key) for key in unknown))
        raise StyleProfileValidationError(f"Unknown density keys in {profile_path}: {joined}")

    min_words = value.get("minWords", defaults.min_words)
    min_lexical_density = value.get("minLexicalDensity", defaults.min_lexical_density)
    max_gzip_ratio = value.get("maxGzipRatio", defaults.max_gzip_ratio)

    if isinstance(min_words, bool) or not isinstance(min_words, int) or min_words < 1:
        raise StyleProfileValidationError(f"density.minWords must be a positive integer in {profile_path}")
    if isinstance(min_lexical_density, bool) or not isinstance(min_lexical_density, (int, float)) or not 0 < min_lexical_density < 1:
        raise StyleProfileValidationError(
            f"density.minLexicalDensity must be between 0 and 1 in {profile_path}"
        )
    if isinstance(max_gzip_ratio, bool) or not isinstance(max_gzip_ratio, (int, float)) or not 0 < max_gzip_ratio < 1:
        raise StyleProfileValidationError(f"density.maxGzipRatio must be between 0 and 1 in {profile_path}")

    return DensityThresholds(
        min_words=min_words,
        min_lexical_density=float(min_lexical_density),
        max_gzip_ratio=float(max_gzip_ratio),
    )


def _load_reference_samples(profile: StyleProfile, profile_root: Path) -> tuple[ReferenceSample, ...]:
    loaded: list[ReferenceSample] = []
    for ref in profile.reference_sample_refs:
        sample_path = (profile_root / ref["path"]).resolve()
        if not sample_path.is_file():
            raise StyleProfileValidationError(f"Reference sample file not found: {sample_path}")
        body = _read_sample_body(sample_path)
        loaded.append(
            ReferenceSample(
                id=ref["id"],
                title=ref["title"],
                url=ref["url"],
                path=sample_path,
                body=body,
            )
        )
    return tuple(loaded)


def _read_sample_body(sample_path: Path) -> str:
    text = sample_path.read_text(encoding="utf-8")
    if text.startswith("---\n"):
        parts = text.split("---\n", 2)
        if len(parts) >= 3:
            body = parts[2].strip()
            if body:
                return body
    body = text.strip()
    if not body:
        raise StyleProfileValidationError(f"Reference sample body is empty: {sample_path}")
    return body


def _require_non_empty_string(value: Any, field_name: str, profile_path: Path) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StyleProfileValidationError(f"Missing or empty {field_name} in {profile_path}")
    return value.strip()


def _require_string_list(value: Any, field_name: str, profile_path: Path) -> list[str]:
    if not isinstance(value, list) or not value:
        raise StyleProfileValidationError(f"Missing or empty {field_name} in {profile_path}")
    normalized: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise StyleProfileValidationError(f"{field_name}[{index}] must be a non-empty string in {profile_path}")
        normalized.append(item.strip())
    return normalized
