from __future__ import annotations

import re
from dataclasses import dataclass

_YAML_FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)
_BLOCK_SCALAR_HEADER_RE = re.compile(r"^(?:\||>-|>|\|-)\s*$")


@dataclass(frozen=True)
class YamlScalarSpan:
    key: str
    value: str
    start: int
    end: int


def split_frontmatter(text: str) -> tuple[str | None, str]:
    normalized = text.replace("\r\n", "\n")
    match = _YAML_FRONTMATTER_RE.match(normalized)
    if not match:
        return None, normalized
    return match.group(0), normalized[match.end() :]


def frontmatter_block_end(text: str) -> int:
    normalized = text.replace("\r\n", "\n")
    match = _YAML_FRONTMATTER_RE.match(normalized)
    if not match:
        return 0
    return match.end()


def locate_yaml_scalar_span(text: str, key: str) -> YamlScalarSpan:
    normalized = text.replace("\r\n", "\n")
    frontmatter, _body = split_frontmatter(normalized)
    if frontmatter is None:
        raise ValueError(f"No YAML frontmatter block found for key '{key}'.")
    block = frontmatter[4:-4] if frontmatter.endswith("---\n") else frontmatter[4:]
    lines = block.split("\n")
    offset = 4  # after leading ---\n
    index = 0
    while index < len(lines):
        line = lines[index]
        line_start = offset
        offset += len(line) + 1
        if not line.strip() or line.lstrip().startswith("#"):
            index += 1
            continue
        match = re.match(rf"^({re.escape(key)})\s*:\s*(.*)$", line)
        if not match:
            index += 1
            continue
        inline = match.group(2)
        value_start = line_start + line.index(":") + 1
        while value_start < len(normalized) and normalized[value_start] in " \t":
            value_start += 1
        if inline and not _BLOCK_SCALAR_HEADER_RE.match(inline.strip()):
            return _parse_inline_scalar(normalized, key, inline, value_start)
        header = inline.strip()
        if header and not _BLOCK_SCALAR_HEADER_RE.match(header):
            raise ValueError(f"Unsupported YAML scalar for key '{key}'.")
        block_style = header or "|"
        index += 1
        max_end = len(frontmatter) - len("---\n")
        return _parse_block_scalar(
            normalized, key, lines, index, block_style, max_scalar_end=max_end
        )
    raise ValueError(f"YAML frontmatter key '{key}' was not found.")


def read_yaml_scalar_value(text: str, key: str) -> str:
    return locate_yaml_scalar_span(text, key).value


def _parse_inline_scalar(text: str, key: str, inline: str, value_start: int) -> YamlScalarSpan:
    stripped = inline.strip()
    if not stripped:
        raise ValueError(f"YAML frontmatter key '{key}' is empty.")
    if stripped[0] in "\"'":
        quote = stripped[0]
        content_start = value_start + (inline.index(quote) if quote in inline else 0)
        end = content_start + 1
        while end < len(text):
            if text[end] == quote and text[end - 1] != "\\":
                inner_start = content_start + 1
                inner_end = end
                value = text[inner_start:inner_end]
                return YamlScalarSpan(key=key, value=value, start=inner_start, end=inner_end)
            end += 1
        raise ValueError(f"Unterminated quoted scalar for key '{key}'.")
    value_end = value_start + len(inline.rstrip())
    value = text[value_start:value_end].strip()
    if not value:
        raise ValueError(f"YAML frontmatter key '{key}' is empty.")
    trimmed_start = value_start + (len(inline) - len(inline.lstrip()))
    trimmed_end = trimmed_start + len(value)
    return YamlScalarSpan(key=key, value=value, start=trimmed_start, end=trimmed_end)


def _parse_block_scalar(
    text: str,
    key: str,
    lines: list[str],
    start_index: int,
    block_style: str,
    *,
    max_scalar_end: int,
) -> YamlScalarSpan:
    if start_index >= len(lines):
        raise ValueError(f"YAML block scalar for key '{key}' is empty.")
    line_offsets: list[int] = []
    offset = 4
    for line in lines:
        line_offsets.append(offset)
        offset += len(line) + 1
    content_lines: list[str] = []
    index = start_index
    base_indent: int | None = None
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            content_lines.append("")
            index += 1
            continue
        indent = len(line) - len(line.lstrip(" "))
        if base_indent is None:
            base_indent = indent
        if indent < base_indent:
            break
        content_lines.append(line[base_indent:])
        index += 1
    if not content_lines or not any(part.strip() for part in content_lines):
        raise ValueError(f"YAML block scalar for key '{key}' is empty.")
    if block_style.startswith(">"):
        value = " ".join(part.strip() for part in content_lines if part.strip())
    else:
        value = "\n".join(content_lines).rstrip("\n")
    span_start = line_offsets[start_index]
    span_end = line_offsets[index] if index < len(line_offsets) else max_scalar_end
    span_end = min(span_end, max_scalar_end)
    return YamlScalarSpan(key=key, value=value, start=span_start, end=span_end)


def restore_leading_frontmatter(original: str, candidate: str) -> str:
    normalized_original = original.replace("\r\n", "\n")
    normalized_candidate = candidate.replace("\r\n", "\n")
    match = _YAML_FRONTMATTER_RE.match(normalized_original)
    if not match:
        return normalized_candidate
    frontmatter = match.group(0)
    if normalized_candidate.startswith("---\n"):
        candidate_fm = _YAML_FRONTMATTER_RE.match(normalized_candidate)
        if candidate_fm and candidate_fm.group(0) == frontmatter:
            return normalized_candidate
    body = normalized_candidate
    candidate_fm = _YAML_FRONTMATTER_RE.match(body)
    if candidate_fm:
        body = body[candidate_fm.end() :]
    if body.startswith(frontmatter):
        return body
    return frontmatter + body.lstrip("\n")
