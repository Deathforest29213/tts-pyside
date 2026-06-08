from __future__ import annotations

import re
from pathlib import Path

from .normalizer import prepare_paragraph


_FENCED_CODE_RE = re.compile(r"(^|\n)(```|~~~).*?(\n\2)(?=\n|$)", re.DOTALL)
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_YAML_FRONT_MATTER_RE = re.compile(r"\A---\s*\n.*?\n---\s*(?:\n|$)", re.DOTALL)
_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\([^)]+\)")
_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_REFERENCE_LINK_RE = re.compile(r"\[([^\]]+)\]\[[^\]]*\]")
_REFERENCE_DEF_RE = re.compile(r"^\s*\[[^\]]+\]:\s+\S+.*$", re.MULTILINE)
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def read_markdown(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1")


def markdown_to_paragraphs(markdown: str) -> list[str]:
    text = _YAML_FRONT_MATTER_RE.sub("", markdown)
    text = _FENCED_CODE_RE.sub("\n\n", text)
    text = _HTML_COMMENT_RE.sub("", text)
    text = _REFERENCE_DEF_RE.sub("", text)
    text = _IMAGE_RE.sub(lambda match: match.group(1), text)
    text = _LINK_RE.sub(lambda match: match.group(1), text)
    text = _REFERENCE_LINK_RE.sub(lambda match: match.group(1), text)
    text = _HTML_TAG_RE.sub("", text)

    cleaned_lines: list[str] = []
    for raw_line in text.splitlines():
        line = _clean_markdown_line(raw_line)
        if line:
            cleaned_lines.append(line)
        elif cleaned_lines and cleaned_lines[-1] != "":
            cleaned_lines.append("")

    blocks = "\n".join(cleaned_lines).split("\n\n")
    paragraphs = [prepare_paragraph(" ".join(block.split())) for block in blocks]
    return [paragraph for paragraph in paragraphs if paragraph]


def parse_markdown_file(path: Path) -> list[str]:
    return markdown_to_paragraphs(read_markdown(path))


def _clean_markdown_line(line: str) -> str:
    line = line.strip()
    if not line:
        return ""

    if re.fullmatch(r"\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?", line):
        return ""

    line = re.sub(r"^#{1,6}\s+", "", line)
    line = re.sub(r"^>\s?", "", line)
    line = re.sub(r"^\s*[-*+]\s+\[[ xX]\]\s+", "", line)
    line = re.sub(r"^\s*[-*+]\s+", "", line)
    line = re.sub(r"^\s*\d+[.)]\s+", "", line)
    line = line.replace("|", ". ")

    line = re.sub(r"`([^`]+)`", r"\1", line)
    line = re.sub(r"(\*\*|__)(.*?)\1", r"\2", line)
    line = re.sub(r"(\*|_)(.*?)\1", r"\2", line)
    line = re.sub(r"~~(.*?)~~", r"\1", line)
    line = re.sub(r"\s+", " ", line)
    return line.strip(" -*_")
