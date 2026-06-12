from __future__ import annotations

import argparse
import asyncio
import time
from pathlib import Path

from .audio import resolve_ffmpeg
from .conversion import (
    PROJECT_ROOT,
    ConversionCallbacks,
    convert_markdown_file,
    discover_markdown_files,
    format_duration,
    output_path_for_markdown,
    output_root_for_input,
    relative_display_name,
    validate_preflight,
)
from .engines.base import SynthesisOptions, TTSEngine
from .engines.edge import EdgeTTSEngine
from .engines.kokoro import KokoroTTSEngine
from .gui.model_manager import models_installed

DEFAULT_ENGINE = "kokoro"
DEFAULT_EDGE_VOICE = "es-CL-LorenzoNeural"
DEFAULT_KOKORO_VOICE = "em_santa"
DEFAULT_EDGE_MAX_CHARS = 1800
DEFAULT_KOKORO_MAX_CHARS = 900


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
    convert.add_argument(
        "--normalize-loudness",
        action="store_true",
        help="Normaliza loudness del MP3 final con ffmpeg.",
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
    ffmpeg_path = resolve_ffmpeg(args.ffmpeg)
    preflight = validate_preflight(
        input_path=input_path,
        output_path=output_base_dir,
        selected_count=len(markdown_files),
        ffmpeg_path=ffmpeg_path,
        models_ready=models_installed() if args.engine == "kokoro" else True,
    )
    if not preflight.ok:
        for error in preflight.errors:
            print(f"Error: {error}")
        raise SystemExit(1)
    for warning in preflight.warnings:
        print(f"Aviso: {warning}")

    print(f"Entrada: {input_path}")
    print(f"Salida:  {output_base_dir}")
    if input_path.is_dir():
        print(f"Espejo:  {output_root_for_input(input_path, output_base_dir)}")
    print(f"Motor:   {engine.name}")
    print(f"Voz:     {options.voice}")
    if engine.name == "kokoro":
        print(f"Idioma:  {options.language}")
        print(f"Speed:   {options.speed}")
    print(f"FFmpeg:  {ffmpeg_path or 'no detectado'}")
    print(f"Chunks:  max {max_chars} caracteres")
    print("")

    for file_index, markdown_file in enumerate(markdown_files, start=1):
        relative_name = relative_display_name(markdown_file, input_path)
        output_path = output_path_for_markdown(markdown_file, input_path, output_base_dir)
        print(f"[{file_index}/{len(markdown_files)}] {relative_name}")
        result = await convert_markdown_file(
            markdown_file=markdown_file,
            output_path=output_path,
            engine=engine,
            options=options,
            max_chars=max_chars,
            force=args.force,
            clean_temp=args.clean_temp,
            normalize_audio=args.normalize_loudness,
            callbacks=ConversionCallbacks(log=lambda message: print(f"  {message}")),
        )
        if result.status == "omitted":
            print(f"  Omitido: {result.message}")
        else:
            print(f"  MP3: {result.output_path}")
            print(f"  Tiempo: {result.elapsed_text} total | metodo: {result.combine_method}")
            if result.loudness_normalized:
                print("  Loudness normalizado")
            if result.metadata_written:
                print("  Metadatos ID3 escritos")
        print("")

    batch_elapsed = time.perf_counter() - batch_started
    print(f"Tiempo total del lote: {format_duration(batch_elapsed)}")


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
