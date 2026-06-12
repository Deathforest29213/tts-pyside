from __future__ import annotations

import pytest

from src.chunker import chunk_paragraphs
from src.parser import markdown_to_paragraphs


def test_markdown_parser_removes_noisy_syntax() -> None:
    markdown = """
---
title: Demo
---

# Titulo principal

Texto con **negrita**, [enlace](https://example.com) y `codigo inline`.

```python
print("esto no debe leerse")
```

![alt descriptivo](image.png)
"""

    paragraphs = markdown_to_paragraphs(markdown)

    assert "Titulo principal." in paragraphs
    assert "Texto con negrita, enlace y codigo inline." in paragraphs
    assert "alt descriptivo." in paragraphs
    assert all("print" not in paragraph for paragraph in paragraphs)


def test_chunker_respects_limit_without_cutting_words() -> None:
    paragraphs = [
        " ".join(f"palabra{i}" for i in range(120)),
        "Este es un segundo parrafo corto.",
    ]

    chunks = chunk_paragraphs(paragraphs, max_chars=300)

    assert len(chunks) > 1
    assert all(len(chunk) <= 300 for chunk in chunks)
    assert all("  " not in chunk for chunk in chunks)


def test_chunker_rejects_too_small_limits() -> None:
    with pytest.raises(ValueError):
        chunk_paragraphs(["texto"], max_chars=100)
