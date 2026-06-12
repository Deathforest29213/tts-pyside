from __future__ import annotations

import asyncio
from pathlib import Path

from src.conversion import (
    convert_markdown_file,
    output_path_for_markdown,
    read_manifest,
    validate_preflight,
)
from src.engines.base import SynthesisOptions, TTSEngine


class FakeEngine(TTSEngine):
    name = "fake"

    async def synthesize_to_file(
        self,
        text: str,
        output_path: Path,
        options: SynthesisOptions,
    ) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"mp3")


def test_conversion_omits_markdown_without_useful_text(tmp_path) -> None:
    markdown = tmp_path / "empty.md"
    markdown.write_text(
        """
```python
print("solo codigo")
```
""",
        encoding="utf-8",
    )
    output_path = tmp_path / "out" / "empty.mp3"

    result = asyncio.run(
        convert_markdown_file(
            markdown_file=markdown,
            output_path=output_path,
            engine=FakeEngine(),
            options=SynthesisOptions(voice="test"),
            max_chars=900,
            force=False,
            clean_temp=False,
        )
    )

    manifest = read_manifest(result.manifest_path)
    assert result.status == "omitted"
    assert result.chunk_count == 0
    assert manifest["status"] == "omitted"
    assert not output_path.exists()


def test_output_path_preserves_input_folder_shape(tmp_path) -> None:
    input_dir = tmp_path / "input" / "Curso"
    markdown = input_dir / "Modulo 1" / "Clase 01.md"
    output_dir = tmp_path / "output"
    markdown.parent.mkdir(parents=True)
    markdown.write_text("# Clase", encoding="utf-8")

    output_path = output_path_for_markdown(markdown, input_dir, output_dir)

    assert output_path == output_dir / "Curso" / "Modulo_1" / "Clase_01.mp3"


def test_preflight_collects_errors(tmp_path) -> None:
    result = validate_preflight(
        input_path=tmp_path / "missing",
        output_path=tmp_path / "out",
        selected_count=0,
        ffmpeg_path=None,
        models_ready=False,
    )

    assert not result.ok
    assert len(result.errors) >= 4
