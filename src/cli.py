from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from .audio import combine_mp3_chunks, resolve_ffmpeg
from .chunker import chunk_paragraphs
from .engines.base import SynthesisOptions, TTSEngine
from .engines.edge import EdgeTTSEngine
from .engines.kokoro import KokoroTTSEngine
from .parser import parse_markdown_file

DEFAULT_ENGINE = "kokoro"
DEFAULT_EDGE_VOICE = "es-CL-LorenzoNeural"
DEFAULT_KOKORO_VOICE = "em_santa"
DEFAULT_EDGE_MAX_CHARS = 1800
DEFAULT_KOKORO_MAX_CHARS = 900
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_INPUT_DIR = PROJECT_ROOT / "input"


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "convert":
        asyncio.run(convert_command(args))
    elif args.command == "voices":
        asyncio.run(voices_command(args))
    else:
        parser.print_help()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="md2audio",
        description="Convierte archivos Markdown en pistas MP3 para estudio.",
    )
    subparsers = parser.add_subparsers(dest="command")

    convert = subparsers.add_parser("convert", help="Convierte un archivo o carpeta Markdown.")
    convert.add_argument(
        "input",
        nargs="?",
        default=str(PROJECT_ROOT / "input"),
        help="Archivo .md o carpeta. Por defecto usa ./input.",
    )
    convert.add_argument(
        "--out",
        default=str(PROJECT_ROOT / "output"),
        help="Carpeta de salida. Por defecto usa ./output.",
    )
    convert.add_argument(
        "--engine", default=DEFAULT_ENGINE, choices=["kokoro", "edge"], help="Motor TTS."
    )
    convert.add_argument("--voice", default=None, help="Voz TTS. Por defecto depende del motor.")
    convert.add_argument("--rate", default="+0%", help='Velocidad, por ejemplo "+0%%" o "-10%%".')
    convert.add_argument("--volume", default="+0%", help='Volumen, por ejemplo "+0%%".')
    convert.add_argument("--pitch", default="+0Hz", help='Tono, por ejemplo "+0Hz".')
    convert.add_argument(
        "--speed", type=float, default=1.0, help="Velocidad Kokoro, por ejemplo 0.9, 1.0 o 1.15."
    )
    convert.add_argument("--lang", default="es", help='Idioma Kokoro, por defecto "es".')
    convert.add_argument(
        "--max-chars", type=int, default=None, help="Maximo de caracteres por chunk."
    )
    convert.add_argument(
        "--ffmpeg",
        default=None,
        help="Ruta opcional a ffmpeg.exe si no esta en PATH.",
    )
    convert.add_argument(
        "--recursive", action="store_true", help="Busca .md recursivamente en carpetas."
    )
    convert.add_argument(
        "--clean-temp",
        action="store_true",
        help="Elimina chunks temporales tras crear el MP3 final.",
    )
    convert.add_argument(
        "--force",
        action="store_true",
        help="Regenera chunks aunque ya existan.",
    )

    voices = subparsers.add_parser("voices", help="Lista voces disponibles.")
    voices.add_argument(
        "--engine", default=DEFAULT_ENGINE, choices=["kokoro", "edge"], help="Motor TTS."
    )
    voices.add_argument(
        "--locale", default="es", help='Filtro de idioma, por ejemplo "es" o "es-CL".'
    )

    return parser


async def convert_command(args: argparse.Namespace) -> None:
    batch_started = time.perf_counter()
    input_path = Path(args.input).expanduser().resolve()
    output_base_dir = Path(args.out).expanduser().resolve()
    output_base_dir.mkdir(parents=True, exist_ok=True)

    markdown_files = discover_markdown_files(input_path, recursive=args.recursive)
    if not markdown_files:
        raise SystemExit(f"No encontre archivos .md en: {input_path}")

    engine = get_engine(args.engine)
    voice = args.voice or default_voice_for_engine(args.engine)
    max_chars = args.max_chars or default_max_chars_for_engine(args.engine)
    options = SynthesisOptions(
        voice=voice,
        rate=args.rate,
        volume=args.volume,
        pitch=args.pitch,
        speed=args.speed,
        language=args.lang,
        ffmpeg_path=args.ffmpeg,
    )

    print(f"Entrada: {input_path}")
    print(f"Salida:  {output_base_dir}")
    if input_path.is_dir():
        print(f"Espejo:  {output_root_for_input(input_path, output_base_dir)}")
    print(f"Motor:   {engine.name}")
    print(f"Voz:     {options.voice}")
    if engine.name == "kokoro":
        print(f"Idioma:  {options.language}")
        print(f"Speed:   {options.speed}")
    print(f"FFmpeg:  {resolve_ffmpeg(args.ffmpeg) or 'no detectado'}")
    print(f"Chunks:  max {max_chars} caracteres")
    print("")

    for file_index, markdown_file in enumerate(markdown_files, start=1):
        file_output_dir = output_dir_for_markdown(markdown_file, input_path, output_base_dir)
        relative_name = relative_display_name(markdown_file, input_path)
        print(f"[{file_index}/{len(markdown_files)}] {relative_name}")
        await convert_file(
            markdown_file=markdown_file,
            output_dir=file_output_dir,
            engine=engine,
            options=options,
            max_chars=max_chars,
            ffmpeg_path=args.ffmpeg,
            force=args.force,
            clean_temp=args.clean_temp,
        )
        print("")

    batch_elapsed = time.perf_counter() - batch_started
    print(f"Tiempo total del lote: {format_duration(batch_elapsed)}")


async def convert_file(
    markdown_file: Path,
    output_dir: Path,
    engine: TTSEngine,
    options: SynthesisOptions,
    max_chars: int,
    ffmpeg_path: str | None,
    force: bool,
    clean_temp: bool,
) -> None:
    file_started = time.perf_counter()
    paragraphs = parse_markdown_file(markdown_file)
    if not paragraphs:
        print("  Omitido: no hay texto legible tras limpiar Markdown.")
        return

    chunks = chunk_paragraphs(paragraphs, max_chars=max_chars)
    stem = safe_stem(markdown_file.stem)
    temp_dir = output_dir / ".chunks" / stem
    temp_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = temp_dir / "manifest.json"
    final_path = output_dir / f"{stem}.mp3"

    previous_manifest = read_manifest(manifest_path)
    previous_chunks = {
        item.get("index"): item
        for item in previous_manifest.get("chunks", [])
        if isinstance(item, dict)
    }

    manifest: dict[str, Any] = {
        "source": str(markdown_file),
        "output": str(final_path),
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
    print(f"  Parrafos: {len(paragraphs)} | Chunks: {len(chunks)}")

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
            print(f"  Chunk {index}/{len(chunks)}: generando...", end="", flush=True)
            chunk_started = time.perf_counter()
            await engine.synthesize_to_file(chunk, chunk_path, options)
            chunk_elapsed = time.perf_counter() - chunk_started
            print(f" ok ({format_duration(chunk_elapsed)})")
        else:
            print(f"  Chunk {index}/{len(chunks)}: reutilizado")

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

    combine_started = time.perf_counter()
    method = combine_mp3_chunks(chunk_paths, final_path, ffmpeg_path=ffmpeg_path)
    combine_elapsed = time.perf_counter() - combine_started
    total_elapsed = time.perf_counter() - file_started
    generated_chunks = [chunk for chunk in manifest["chunks"] if chunk.get("status") == "generated"]
    generated_elapsed = sum(chunk.get("elapsed_seconds", 0.0) for chunk in generated_chunks)
    avg_generated_chunk_elapsed = (
        generated_elapsed / len(generated_chunks) if generated_chunks else 0.0
    )

    manifest["combine_method"] = method
    manifest["combine_elapsed_seconds"] = round(combine_elapsed, 3)
    manifest["total_elapsed_seconds"] = round(total_elapsed, 3)
    manifest["generated_chunk_count"] = len(generated_chunks)
    manifest["reused_chunk_count"] = len(chunks) - len(generated_chunks)
    manifest["avg_generated_chunk_elapsed_seconds"] = round(avg_generated_chunk_elapsed, 3)
    manifest["completed_at"] = datetime.now().isoformat(timespec="seconds")
    write_manifest(manifest_path, manifest)

    print(f"  MP3: {final_path}")
    print(
        "  Tiempo: "
        f"{format_duration(total_elapsed)} total | "
        f"{format_duration(combine_elapsed)} union | "
        f"{format_duration(avg_generated_chunk_elapsed)} promedio/chunk generado"
    )
    if method == "binary-fallback":
        print("  Aviso: ffmpeg no esta instalado; use union MP3 basica.")

    if clean_temp:
        shutil.rmtree(temp_dir, ignore_errors=True)
        print("  Temporales eliminados.")


async def voices_command(args: argparse.Namespace) -> None:
    engine = get_engine(args.engine)
    voices = await engine.list_voices()
    locale = args.locale.lower()
    filtered = [voice for voice in voices if locale in voice.get("Locale", "").lower()]

    for voice in filtered:
        short_name = voice.get("ShortName", "")
        locale_name = voice.get("Locale", "")
        gender = voice.get("Gender", "")
        friendly = voice.get("FriendlyName", "")
        print(f"{short_name:32} {locale_name:8} {gender:8} {friendly}")

    print(f"\nTotal: {len(filtered)} voces")


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


def relative_display_name(markdown_file: Path, input_path: Path) -> str:
    if input_path.is_file():
        return markdown_file.name
    return str(markdown_file.relative_to(input_path))


def get_engine(name: str) -> TTSEngine:
    if name == "kokoro":
        return KokoroTTSEngine()
    if name == "edge":
        return EdgeTTSEngine()
    raise SystemExit(f"Motor no soportado: {name}")


def default_voice_for_engine(name: str) -> str:
    if name == "kokoro":
        return DEFAULT_KOKORO_VOICE
    if name == "edge":
        return DEFAULT_EDGE_VOICE
    raise SystemExit(f"Motor no soportado: {name}")


def default_max_chars_for_engine(name: str) -> int:
    if name == "kokoro":
        return DEFAULT_KOKORO_MAX_CHARS
    if name == "edge":
        return DEFAULT_EDGE_MAX_CHARS
    raise SystemExit(f"Motor no soportado: {name}")


def safe_stem(value: str) -> str:
    value = re.sub(r"[^\w.-]+", "_", value, flags=re.UNICODE)
    value = value.strip(".")
    return value or "audio"


def safe_relative_path(path: Path) -> Path:
    safe_parts = [safe_stem(part) for part in path.parts if part not in ("", ".")]
    return Path(*safe_parts) if safe_parts else Path()


def write_manifest(path: Path, manifest: dict) -> None:
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
