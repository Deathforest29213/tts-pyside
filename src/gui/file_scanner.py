from __future__ import annotations

from pathlib import Path

from ..cli import (
    discover_markdown_files,
    output_dir_for_markdown,
    output_root_for_input,
    safe_stem,
)


def scan_markdown_files(input_path: Path, output_base_dir: Path, recursive: bool) -> list[dict]:
    markdown_files = discover_markdown_files(input_path, recursive=recursive)
    rows: list[dict] = []

    for markdown_file in markdown_files:
        output_dir = output_dir_for_markdown(markdown_file, input_path, output_base_dir)
        stem = safe_stem(markdown_file.stem)
        output_path = output_dir / f"{stem}.mp3"
        manifest_path = output_dir / ".chunks" / stem / "manifest.json"
        rows.append(
            {
                "status": "Pendiente",
                "file": markdown_file.name,
                "relativePath": relative_display_path(markdown_file, input_path),
                "sourcePath": str(markdown_file),
                "outputPath": str(output_path),
                "manifestPath": str(manifest_path),
                "included": True,
                "time": "",
                "message": "",
            }
        )

    return rows


def mirror_output_path(input_path: Path, output_base_dir: Path) -> Path:
    return output_root_for_input(input_path, output_base_dir)


def relative_display_path(markdown_file: Path, input_path: Path) -> str:
    if input_path.is_file():
        return markdown_file.name
    return str(markdown_file.relative_to(input_path))
