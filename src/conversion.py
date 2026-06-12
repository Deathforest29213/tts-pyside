from __future__ import annotations

import hashlib
import json
import re
import shutil
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .audio import combine_mp3_chunks, normalize_loudness, write_mp3_metadata
from .chunker import chunk_paragraphs
from .engines.base import SynthesisOptions, TTSEngine
from .parser import parse_markdown_file, read_markdown

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_INPUT_DIR = PROJECT_ROOT / "input"


@dataclass(frozen=True)
class ConversionCallbacks:
    log: Callable[[str], None] | None = None
    chunk_done: Callable[[int, int], None] | None = None


@dataclass(frozen=True)
class ConversionResult:
    status: str
    message: str
    output_path: Path
    manifest_path: Path
    elapsed_seconds: float
    chunk_count: int = 0
    combine_method: str = ""
    metadata_written: bool = False
    loudness_normalized: bool = False

    @property
    def elapsed_text(self) -> str:
        return format_duration(self.elapsed_seconds)


@dataclass(frozen=True)
class PreflightResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


async def convert_markdown_file(
    markdown_file: Path,
    output_path: Path,
    engine: TTSEngine,
    options: SynthesisOptions,
    max_chars: int,
    force: bool,
    clean_temp: bool,
    callbacks: ConversionCallbacks | None = None,
    normalize_audio: bool = False,
    metadata: dict[str, Any] | None = None,
) -> ConversionResult:
    callbacks = callbacks or ConversionCallbacks()
    file_started = time.perf_counter()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    stem = safe_stem(markdown_file.stem)
    temp_dir = output_path.parent / ".chunks" / stem
    manifest_path = temp_dir / "manifest.json"

    paragraphs = parse_markdown_file(markdown_file)
    if not paragraphs:
        result = ConversionResult(
            status="omitted",
            message="No hay texto legible tras limpiar Markdown.",
            output_path=output_path,
            manifest_path=manifest_path,
            elapsed_seconds=time.perf_counter() - file_started,
        )
        write_manifest(
            manifest_path,
            omitted_manifest(markdown_file, output_path, result, engine.name, options, max_chars),
        )
        return result

    chunks = chunk_paragraphs(paragraphs, max_chars=max_chars)
    if not chunks:
        result = ConversionResult(
            status="omitted",
            message="No se generaron chunks de texto.",
            output_path=output_path,
            manifest_path=manifest_path,
            elapsed_seconds=time.perf_counter() - file_started,
        )
        write_manifest(
            manifest_path,
            omitted_manifest(markdown_file, output_path, result, engine.name, options, max_chars),
        )
        return result

    temp_dir.mkdir(parents=True, exist_ok=True)
    previous_manifest = read_manifest(manifest_path)
    previous_chunks = {
        item.get("index"): item
        for item in previous_manifest.get("chunks", [])
        if isinstance(item, dict)
    }

    manifest: dict[str, Any] = {
        "source": str(markdown_file),
        "output": str(output_path),
        "status": "running",
        "engine": engine.name,
        "voice": options.voice,
        "rate": options.rate,
        "volume": options.volume,
        "pitch": options.pitch,
        "speed": options.speed,
        "language": options.language,
        "max_chars": max_chars,
        "source_mtime": markdown_file.stat().st_mtime,
        "chunk_count": len(chunks),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "chunks": [],
    }

    chunk_paths: list[Path] = []
    emit(callbacks.log, f"Parrafos: {len(paragraphs)} | Chunks: {len(chunks)}")

    for index, chunk in enumerate(chunks, start=1):
        chunk_path = temp_dir / f"{index:04d}.mp3"
        chunk_paths.append(chunk_path)
        chunk_hash = hash_text(chunk)
        previous_chunk = previous_chunks.get(index, {})
        reusable = can_reuse_chunk(
            chunk_path=chunk_path,
            chunk_hash=chunk_hash,
            previous_chunk=previous_chunk,
            previous_manifest=previous_manifest,
            current_manifest=manifest,
        )
        status = "reused"
        chunk_elapsed = 0.0

        if force or not reusable:
            status = "generated"
            emit(callbacks.log, f"Chunk {index}/{len(chunks)}: generando...")
            chunk_started = time.perf_counter()
            await engine.synthesize_to_file(chunk, chunk_path, options)
            chunk_elapsed = time.perf_counter() - chunk_started
            emit(
                callbacks.log, f"Chunk {index}/{len(chunks)}: ok ({format_duration(chunk_elapsed)})"
            )
        else:
            emit(callbacks.log, f"Chunk {index}/{len(chunks)}: reutilizado")

        manifest["chunks"].append(
            {
                "index": index,
                "path": str(chunk_path),
                "chars": len(chunk),
                "hash": chunk_hash,
                "status": status,
                "elapsed_seconds": round(chunk_elapsed, 3),
            }
        )
        write_manifest(manifest_path, manifest)
        if callbacks.chunk_done:
            callbacks.chunk_done(index, len(chunks))

    combine_started = time.perf_counter()
    method = combine_mp3_chunks(chunk_paths, output_path, ffmpeg_path=options.ffmpeg_path)
    combine_elapsed = time.perf_counter() - combine_started
    loudness_normalized = (
        normalize_loudness(output_path, options.ffmpeg_path) if normalize_audio else False
    )
    metadata_payload = build_metadata(markdown_file, engine.name, options.voice, metadata)
    metadata_written = write_mp3_metadata(output_path, metadata_payload)
    total_elapsed = time.perf_counter() - file_started

    generated_chunks = [chunk for chunk in manifest["chunks"] if chunk.get("status") == "generated"]
    generated_elapsed = sum(chunk.get("elapsed_seconds", 0.0) for chunk in generated_chunks)
    avg_generated_chunk_elapsed = (
        generated_elapsed / len(generated_chunks) if generated_chunks else 0.0
    )

    manifest["status"] = "completed"
    manifest["combine_method"] = method
    manifest["combine_elapsed_seconds"] = round(combine_elapsed, 3)
    manifest["total_elapsed_seconds"] = round(total_elapsed, 3)
    manifest["generated_chunk_count"] = len(generated_chunks)
    manifest["reused_chunk_count"] = len(chunks) - len(generated_chunks)
    manifest["avg_generated_chunk_elapsed_seconds"] = round(avg_generated_chunk_elapsed, 3)
    manifest["loudness_normalized"] = loudness_normalized
    manifest["metadata_written"] = metadata_written
    manifest["metadata"] = metadata_payload
    manifest["completed_at"] = datetime.now().isoformat(timespec="seconds")
    write_manifest(manifest_path, manifest)

    if clean_temp:
        shutil.rmtree(temp_dir, ignore_errors=True)

    return ConversionResult(
        status="completed",
        message="MP3 generado",
        output_path=output_path,
        manifest_path=manifest_path,
        elapsed_seconds=total_elapsed,
        chunk_count=len(chunks),
        combine_method=method,
        metadata_written=metadata_written,
        loudness_normalized=loudness_normalized,
    )


def omitted_manifest(
    markdown_file: Path,
    output_path: Path,
    result: ConversionResult,
    engine_name: str,
    options: SynthesisOptions,
    max_chars: int,
) -> dict[str, Any]:
    return {
        "source": str(markdown_file),
        "output": str(output_path),
        "status": result.status,
        "message": result.message,
        "engine": engine_name,
        "voice": options.voice,
        "speed": options.speed,
        "language": options.language,
        "max_chars": max_chars,
        "chunk_count": 0,
        "total_elapsed_seconds": round(result.elapsed_seconds, 3),
        "completed_at": datetime.now().isoformat(timespec="seconds"),
        "chunks": [],
    }


def build_metadata(
    markdown_file: Path,
    engine_name: str,
    voice: str,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    overrides = overrides or {}
    title = str(overrides.get("title") or title_from_markdown(markdown_file) or markdown_file.stem)
    return {
        "title": title,
        "author": overrides.get("author", "md2audio"),
        "album": overrides.get("album", markdown_file.parent.name or "md2audio"),
        "chapter": overrides.get("chapter", markdown_file.stem),
        "date": overrides.get("date", datetime.now().date().isoformat()),
        "engine": engine_name,
        "voice": voice,
    }


def title_from_markdown(path: Path) -> str:
    try:
        markdown = read_markdown(path)
    except OSError:
        return ""
    for line in markdown.splitlines():
        match = re.match(r"^\s*#\s+(.+?)\s*$", line)
        if match:
            return match.group(1).strip()
    return ""


def validate_preflight(
    input_path: Path,
    output_path: Path,
    selected_count: int,
    ffmpeg_path: str | None,
    models_ready: bool,
    estimated_bytes: int = 100 * 1024 * 1024,
) -> PreflightResult:
    errors: list[str] = []
    warnings: list[str] = []

    if not input_path.exists():
        errors.append(f"No existe la entrada: {input_path}")
    if selected_count <= 0:
        errors.append("No hay archivos seleccionados para convertir.")
    if not models_ready:
        errors.append("Faltan modelos Kokoro validos.")
    if not ffmpeg_path:
        errors.append("No se detecto ffmpeg.")

    try:
        output_path.mkdir(parents=True, exist_ok=True)
        probe_path = output_path / ".write_test"
        probe_path.write_text("ok", encoding="utf-8")
        probe_path.unlink(missing_ok=True)
    except OSError as exc:
        errors.append(f"No se puede escribir en output: {exc}")

    try:
        free_bytes = shutil.disk_usage(output_path).free
        if free_bytes < estimated_bytes:
            errors.append(f"Espacio insuficiente en disco: {format_bytes(free_bytes)} libres.")
        elif free_bytes < estimated_bytes * 3:
            warnings.append(f"Espacio bajo en disco: {format_bytes(free_bytes)} libres.")
    except OSError as exc:
        warnings.append(f"No pude verificar espacio en disco: {exc}")

    return PreflightResult(ok=not errors, errors=errors, warnings=warnings)


def discover_markdown_files(input_path: Path, recursive: bool) -> list[Path]:
    if input_path.is_file():
        if input_path.suffix.lower() != ".md":
            raise SystemExit(f"El archivo no es Markdown: {input_path}")
        return [input_path]

    if not input_path.exists():
        raise SystemExit(f"La ruta no existe: {input_path}")

    pattern = "**/*.md" if recursive else "*.md"
    return sorted(path for path in input_path.glob(pattern) if path.is_file())


def output_root_for_input(input_path: Path, output_base_dir: Path) -> Path:
    if input_path.is_file():
        return output_base_dir

    try:
        relative_to_input = input_path.relative_to(PROJECT_INPUT_DIR)
    except ValueError:
        relative_to_input = None

    if input_path == PROJECT_INPUT_DIR:
        return output_base_dir

    if relative_to_input and relative_to_input.parts:
        return output_base_dir / safe_relative_path(relative_to_input)

    return output_base_dir / safe_stem(input_path.name)


def output_dir_for_markdown(
    markdown_file: Path,
    input_path: Path,
    output_base_dir: Path,
) -> Path:
    if input_path.is_file():
        return output_base_dir

    root = output_root_for_input(input_path, output_base_dir)
    relative_parent = markdown_file.parent.relative_to(input_path)
    return root / safe_relative_path(relative_parent)


def output_path_for_markdown(
    markdown_file: Path,
    input_path: Path,
    output_base_dir: Path,
) -> Path:
    return output_dir_for_markdown(markdown_file, input_path, output_base_dir) / (
        safe_stem(markdown_file.stem) + ".mp3"
    )


def relative_display_name(markdown_file: Path, input_path: Path) -> str:
    if input_path.is_file():
        return markdown_file.name
    return str(markdown_file.relative_to(input_path))


def safe_stem(value: str) -> str:
    value = re.sub(r"[^\w.-]+", "_", value, flags=re.UNICODE)
    value = value.strip(".")
    return value or "audio"


def safe_relative_path(path: Path) -> Path:
    safe_parts = [safe_stem(part) for part in path.parts if part not in ("", ".")]
    return Path(*safe_parts) if safe_parts else Path()


def write_manifest(path: Path, manifest: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def read_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def format_duration(seconds: float) -> str:
    if seconds < 1:
        return f"{seconds * 1000:.0f} ms"

    minutes, remaining_seconds = divmod(seconds, 60)
    hours, minutes = divmod(int(minutes), 60)

    if hours:
        return f"{hours}h {minutes:02d}m {remaining_seconds:04.1f}s"
    if minutes:
        return f"{minutes}m {remaining_seconds:04.1f}s"
    return f"{remaining_seconds:.1f}s"


def format_bytes(value: int) -> str:
    size = float(value)
    for suffix in ("B", "KB", "MB", "GB"):
        if size < 1024 or suffix == "GB":
            return f"{size:.1f} {suffix}" if suffix != "B" else f"{int(size)} B"
        size /= 1024
    return f"{value} B"


def can_reuse_chunk(
    chunk_path: Path,
    chunk_hash: str,
    previous_chunk: dict,
    previous_manifest: dict,
    current_manifest: dict,
) -> bool:
    if not chunk_path.exists() or chunk_path.stat().st_size == 0:
        return False

    stable_keys = [
        "engine",
        "voice",
        "rate",
        "volume",
        "pitch",
        "speed",
        "language",
        "max_chars",
    ]
    for key in stable_keys:
        if previous_manifest.get(key) != current_manifest.get(key):
            return False

    if previous_manifest.get("chunk_count") != current_manifest.get("chunk_count"):
        return False

    return previous_chunk.get("hash") == chunk_hash


def emit(callback: Callable[[str], None] | None, message: str) -> None:
    if callback:
        callback(message)
