from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any

from ._util import hash_short
from .usability_profile import LoadedUsabilityProfile

SCHEMA_VERSION = 1

USABILITY_FORBIDDEN_OUTPUT_KEYS = frozenset(
    {
        "rewrite",
        "patch",
        "patches",
        "options",
        "decisions",
        "revised_text",
        "rewritten_prose",
        "revisedProse",
        "revisedText",
    }
)

# CSS Level 1 color names supported for deterministic parsing (no full named-color table).
CSS_NAMED_COLORS: dict[str, tuple[int, int, int]] = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "red": (255, 0, 0),
    "green": (0, 128, 0),
    "blue": (0, 0, 255),
    "gray": (128, 128, 128),
    "grey": (128, 128, 128),
}

TEXT_CONTAINER_TAGS = frozenset(
    {
        "p",
        "span",
        "div",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "a",
        "li",
        "label",
        "button",
        "td",
        "th",
        "strong",
        "em",
        "small",
    }
)


class UsabilityFindingsValidationError(ValueError):
    """Raised when usability findings JSON fails schema validation."""


@dataclass
class _DomNode:
    tag: str
    attrs: dict[str, str]
    direct_text: list[str] = field(default_factory=list)
    children: list[_DomNode] = field(default_factory=list)


@dataclass(frozen=True)
class _CssRule:
    selectors: tuple[str, ...]
    declarations: dict[str, str]


def scan_html_page(page_html: str, *, profile: LoadedUsabilityProfile) -> dict[str, Any]:
    tree, style_text = _parse_html(page_html)
    css_rules = _parse_stylesheet(style_text)
    findings: list[dict[str, Any]] = []
    findings.extend(_find_missing_alt(tree))
    findings.extend(
        _find_low_contrast(tree, css_rules, min_ratio=profile.profile.contrast.min_ratio)
    )
    payload = {"schemaVersion": SCHEMA_VERSION, "findings": findings}
    return validate_usability_findings(payload)


def stable_usability_finding_id(kind: str, selector: str, detail: str = "") -> str:
    return f"finding-{hash_short([SCHEMA_VERSION, kind, selector, detail])}"


def assert_no_forbidden_usability_keys(value: Any, key_path: str = "") -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            key_text = str(key)
            current_path = f"{key_path}.{key_text}" if key_path else key_text
            if key_text in USABILITY_FORBIDDEN_OUTPUT_KEYS:
                raise UsabilityFindingsValidationError(
                    f"Usability findings JSON contains forbidden field '{current_path}'"
                )
            assert_no_forbidden_usability_keys(nested, current_path)
        return
    if isinstance(value, list):
        for index, nested in enumerate(value):
            assert_no_forbidden_usability_keys(nested, f"{key_path}[{index}]")


def validate_usability_findings(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise UsabilityFindingsValidationError("Usability findings JSON must be a mapping.")
    assert_no_forbidden_usability_keys(payload)
    if payload.get("schemaVersion") != SCHEMA_VERSION:
        raise UsabilityFindingsValidationError(
            f"Unsupported schemaVersion: expected {SCHEMA_VERSION}."
        )
    findings = payload.get("findings")
    if not isinstance(findings, list):
        raise UsabilityFindingsValidationError("findings must be a list.")
    validated: list[dict[str, Any]] = []
    for index, entry in enumerate(findings):
        validated.append(_validate_finding(entry, f"findings[{index}]"))
    return {"schemaVersion": SCHEMA_VERSION, "findings": validated}


def _validate_finding(entry: Any, location: str) -> dict[str, Any]:
    if not isinstance(entry, dict):
        raise UsabilityFindingsValidationError(f"{location} must be a mapping.")
    assert_no_forbidden_usability_keys(entry, location)
    kind = entry.get("kind")
    if kind not in {"missing_alt", "low_contrast"}:
        raise UsabilityFindingsValidationError(
            f"{location}.kind must be 'missing_alt' or 'low_contrast'."
        )
    finding_id = entry.get("id")
    if not isinstance(finding_id, str) or not re.fullmatch(r"finding-[a-f0-9]{16}", finding_id):
        raise UsabilityFindingsValidationError(f"{location}.id must match finding-<16 hex>.")
    selector = entry.get("selector")
    if not isinstance(selector, str) or not selector.strip():
        raise UsabilityFindingsValidationError(f"{location}.selector must be a non-empty string.")
    rationale = entry.get("rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        raise UsabilityFindingsValidationError(f"{location}.rationale must be a non-empty string.")
    result: dict[str, Any] = {
        "id": finding_id,
        "kind": kind,
        "selector": selector,
        "rationale": rationale,
    }
    if kind == "low_contrast":
        ratio = entry.get("ratio")
        if not isinstance(ratio, (int, float)) or isinstance(ratio, bool):
            raise UsabilityFindingsValidationError(f"{location}.ratio must be a number.")
        result["ratio"] = round(float(ratio), 4)
    elif "ratio" in entry:
        raise UsabilityFindingsValidationError(f"{location} must not include ratio for missing_alt.")
    return result


def _find_missing_alt(node: _DomNode) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if node.tag == "img":
        if "alt" not in node.attrs:
            selector = _element_selector(node)
            src = node.attrs.get("src", "")
            finding_id = stable_usability_finding_id("missing_alt", selector, src)
            findings.append(
                {
                    "id": finding_id,
                    "kind": "missing_alt",
                    "selector": selector,
                    "rationale": "Image element has no alt attribute.",
                }
            )
    for child in node.children:
        findings.extend(_find_missing_alt(child))
    return findings


def _find_low_contrast(
    node: _DomNode,
    css_rules: list[_CssRule],
    *,
    min_ratio: float,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if node.tag in TEXT_CONTAINER_TAGS:
        direct = "".join(node.direct_text).strip()
        if direct:
            fg = _resolve_color(node, "color", css_rules)
            bg = _resolve_color(node, "background-color", css_rules)
            if fg is not None and bg is not None:
                ratio = _contrast_ratio(fg, bg)
                if ratio < min_ratio:
                    selector = _element_selector(node)
                    finding_id = stable_usability_finding_id(
                        "low_contrast", selector, f"{ratio:.4f}"
                    )
                    findings.append(
                        {
                            "id": finding_id,
                            "kind": "low_contrast",
                            "selector": selector,
                            "rationale": (
                                f"Text contrast ratio {ratio:.2f} is below the profile minimum "
                                f"({min_ratio})."
                            ),
                            "ratio": round(ratio, 4),
                        }
                    )
    for child in node.children:
        findings.extend(_find_low_contrast(child, css_rules, min_ratio=min_ratio))
    return findings


def _element_selector(node: _DomNode) -> str:
    parts = [node.tag]
    element_id = node.attrs.get("id")
    if element_id:
        parts.append(f"#{element_id}")
    classes = node.attrs.get("class", "")
    for class_name in classes.split():
        if class_name:
            parts.append(f".{class_name}")
    return "".join(parts)


def _resolve_color(node: _DomNode, property_name: str, css_rules: list[_CssRule]) -> tuple[int, int, int] | None:
    inline = _inline_style_dict(node.attrs.get("style", ""))
    if property_name in inline:
        return parse_css_color(inline[property_name])
    matched_value: str | None = None
    matched_specificity = -1
    matched_order = -1
    for order, rule in enumerate(css_rules):
        if not _selector_matches_node(node, rule.selectors):
            continue
        if property_name not in rule.declarations:
            continue
        specificity = _selector_specificity(rule.selectors, node)
        if specificity > matched_specificity or (
            specificity == matched_specificity and order > matched_order
        ):
            matched_specificity = specificity
            matched_order = order
            matched_value = rule.declarations[property_name]
    if matched_value is None:
        return None
    return parse_css_color(matched_value)


def _inline_style_dict(style_attr: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for chunk in style_attr.split(";"):
        if ":" not in chunk:
            continue
        name, value = chunk.split(":", 1)
        key = name.strip().lower()
        if key:
            result[key] = value.strip()
    return result


def _selector_matches_node(node: _DomNode, selectors: tuple[str, ...]) -> bool:
    return any(_single_selector_matches(node, selector) for selector in selectors)


def _single_selector_matches(node: _DomNode, selector: str) -> bool:
    selector = selector.strip()
    if not selector:
        return False
    tag = node.tag
    element_id = node.attrs.get("id", "")
    classes = set(node.attrs.get("class", "").split())
    if selector.startswith("#"):
        return selector[1:] == element_id
    if selector.startswith("."):
        return selector[1:] in classes
    return selector == tag


def _selector_specificity(selectors: tuple[str, ...], node: _DomNode) -> int:
    best = 0
    for selector in selectors:
        if not _single_selector_matches(node, selector):
            continue
        score = 0
        stripped = selector.strip()
        if stripped.startswith("#"):
            score = 100
        elif stripped.startswith("."):
            score = 10
        else:
            score = 1
        best = max(best, score)
    return best


def _parse_stylesheet(style_text: str) -> list[_CssRule]:
    if not style_text.strip():
        return []
    rules: list[_CssRule] = []
    for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", style_text):
        selector_text = match.group(1).strip()
        block = match.group(2)
        selectors = tuple(part.strip() for part in selector_text.split(",") if part.strip())
        declarations: dict[str, str] = {}
        for decl in block.split(";"):
            if ":" not in decl:
                continue
            name, value = decl.split(":", 1)
            key = name.strip().lower()
            if key:
                declarations[key] = value.strip()
        if selectors:
            rules.append(_CssRule(selectors=selectors, declarations=declarations))
    return rules


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _DomNode(tag="document", attrs={})
        self._stack: list[_DomNode] = [self.root]
        self._style_text: str | None = None
        self._capture_style = False
        self._style_chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized = tag.lower()
        attr_map = {name.lower(): (value if value is not None else "") for name, value in attrs}
        node = _DomNode(tag=normalized, attrs=attr_map)
        self._stack[-1].children.append(node)
        self._stack.append(node)
        if normalized == "style" and self._style_text is None:
            self._capture_style = True
            self._style_chunks = []

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()
        if normalized == "style" and self._capture_style:
            self._capture_style = False
            self._style_text = "".join(self._style_chunks)
        if len(self._stack) > 1 and self._stack[-1].tag == normalized:
            self._stack.pop()

    def handle_data(self, data: str) -> None:
        if self._capture_style:
            self._style_chunks.append(data)
            return
        if len(self._stack) > 1:
            self._stack[-1].direct_text.append(data)


def _parse_html(page_html: str) -> tuple[_DomNode, str]:
    parser = _PageParser()
    parser.feed(page_html)
    parser.close()
    return parser.root, parser._style_text or ""


def parse_css_color(value: str) -> tuple[int, int, int] | None:
    text = value.strip().lower()
    if not text:
        return None
    if text in CSS_NAMED_COLORS:
        return CSS_NAMED_COLORS[text]
    if text.startswith("#"):
        return _parse_hex_color(text)
    rgb_match = re.fullmatch(
        r"rgba?\(\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)\s*(?:,\s*([0-9.]+)\s*)?\)",
        text,
    )
    if rgb_match:
        alpha_text = rgb_match.group(4)
        if alpha_text is not None and float(alpha_text) != 1.0:
            return None
        channels = (
            _clamp_channel(float(rgb_match.group(1))),
            _clamp_channel(float(rgb_match.group(2))),
            _clamp_channel(float(rgb_match.group(3))),
        )
        return channels
    return None


def _parse_hex_color(value: str) -> tuple[int, int, int] | None:
    hex_body = value[1:]
    if len(hex_body) == 3:
        return (
            int(hex_body[0] * 2, 16),
            int(hex_body[1] * 2, 16),
            int(hex_body[2] * 2, 16),
        )
    if len(hex_body) == 6:
        try:
            return (
                int(hex_body[0:2], 16),
                int(hex_body[2:4], 16),
                int(hex_body[4:6], 16),
            )
        except ValueError:
            return None
    return None


def _clamp_channel(value: float) -> int:
    if value <= 1.0:
        value *= 255.0
    return max(0, min(255, int(round(value))))


def _relative_luminance(rgb: tuple[int, int, int]) -> float:
    def channel(value: int) -> float:
        scaled = value / 255.0
        if scaled <= 0.03928:
            return scaled / 12.92
        return ((scaled + 0.055) / 1.055) ** 2.4

    red, green, blue = rgb
    return 0.2126 * channel(red) + 0.7152 * channel(green) + 0.0722 * channel(blue)


def _contrast_ratio(fg: tuple[int, int, int], bg: tuple[int, int, int]) -> float:
    l1 = _relative_luminance(fg)
    l2 = _relative_luminance(bg)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)
