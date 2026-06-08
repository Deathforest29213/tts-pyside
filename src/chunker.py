from __future__ import annotations

import re


_SENTENCE_BOUNDARY_RE = re.compile(r"(?<=[.!?:;])\s+")


def chunk_paragraphs(paragraphs: list[str], max_chars: int = 1800) -> list[str]:
    if max_chars < 300:
        raise ValueError("max_chars debe ser al menos 300 para evitar cortes excesivos.")

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for paragraph in paragraphs:
        parts = _split_oversized(paragraph, max_chars)
        for part in parts:
            separator_len = 2 if current else 0
            if current and current_len + separator_len + len(part) > max_chars:
                chunks.append("\n\n".join(current))
                current = [part]
                current_len = len(part)
            else:
                current.append(part)
                current_len += separator_len + len(part)

    if current:
        chunks.append("\n\n".join(current))

    return chunks


def _split_oversized(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    sentences = [part.strip() for part in _SENTENCE_BOUNDARY_RE.split(text) if part.strip()]
    pieces: list[str] = []
    current: list[str] = []
    current_len = 0

    for sentence in sentences:
        if len(sentence) > max_chars:
            if current:
                pieces.append(" ".join(current))
                current = []
                current_len = 0
            pieces.extend(_split_by_words(sentence, max_chars))
            continue

        separator_len = 1 if current else 0
        if current and current_len + separator_len + len(sentence) > max_chars:
            pieces.append(" ".join(current))
            current = [sentence]
            current_len = len(sentence)
        else:
            current.append(sentence)
            current_len += separator_len + len(sentence)

    if current:
        pieces.append(" ".join(current))

    return pieces


def _split_by_words(text: str, max_chars: int) -> list[str]:
    words = text.split()
    pieces: list[str] = []
    current: list[str] = []
    current_len = 0

    for word in words:
        separator_len = 1 if current else 0
        if current and current_len + separator_len + len(word) > max_chars:
            pieces.append(" ".join(current))
            current = [word]
            current_len = len(word)
        else:
            current.append(word)
            current_len += separator_len + len(word)

    if current:
        pieces.append(" ".join(current))

    return pieces
