from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

COMMON_FFMPEG_PATHS = [
    Path(r"C:\ffmpeg\bin\ffmpeg.exe"),
    Path(r"C:\ProgramData\chocolatey\bin\ffmpeg.exe"),
    Path(r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"),
    Path(r"C:\Program Files\Krita (x64)\bin\ffmpeg.exe"),
]


def combine_mp3_chunks(
    chunk_paths: list[Path],
    output_path: Path,
    ffmpeg_path: str | Path | None = None,
) -> str:
    if not chunk_paths:
        raise ValueError("No hay chunks de audio para unir.")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if len(chunk_paths) == 1:
        shutil.copyfile(chunk_paths[0], output_path)
        return "copy"

    ffmpeg_exe = resolve_ffmpeg(ffmpeg_path)
    if ffmpeg_exe:
        try:
            _combine_with_ffmpeg(chunk_paths, output_path, ffmpeg_exe)
            return "ffmpeg"
        except subprocess.CalledProcessError:
            pass

    _combine_binary(chunk_paths, output_path)
    return "binary-fallback"


def normalize_loudness(
    audio_path: Path,
    ffmpeg_path: str | Path | None = None,
) -> bool:
    ffmpeg_exe = resolve_ffmpeg(ffmpeg_path)
    if not ffmpeg_exe or not audio_path.exists():
        return False

    temp_path = audio_path.with_suffix(".normalized.mp3")
    try:
        subprocess.run(
            [
                ffmpeg_exe,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(audio_path),
                "-af",
                "loudnorm=I=-16:TP=-1.5:LRA=11",
                "-codec:a",
                "libmp3lame",
                "-q:a",
                "2",
                str(temp_path),
            ],
            check=True,
        )
        temp_path.replace(audio_path)
        return True
    except subprocess.CalledProcessError:
        temp_path.unlink(missing_ok=True)
        return False


def write_mp3_metadata(audio_path: Path, metadata: dict[str, Any]) -> bool:
    if not audio_path.exists():
        return False

    try:
        from mutagen.easyid3 import EasyID3
        from mutagen.id3 import COMM, ID3, ID3NoHeaderError
    except ImportError:
        return False

    try:
        tags = EasyID3(audio_path)
    except ID3NoHeaderError:
        tags = EasyID3()

    mapping = {
        "title": "title",
        "author": "artist",
        "album": "album",
        "date": "date",
    }
    for source_key, tag_key in mapping.items():
        value = metadata.get(source_key)
        if value:
            tags[tag_key] = [str(value)]

    tags.save(audio_path)

    comment_parts = []
    for key in ("engine", "voice", "chapter"):
        value = metadata.get(key)
        if value:
            comment_parts.append(f"{key}: {value}")
    if comment_parts:
        id3 = ID3(audio_path)
        id3.delall("COMM")
        id3.add(COMM(encoding=3, lang="spa", desc="md2audio", text=" | ".join(comment_parts)))
        id3.save(audio_path)

    return True


def resolve_ffmpeg(ffmpeg_path: str | Path | None = None) -> str | None:
    candidates: list[str | Path | None] = [
        ffmpeg_path,
        os.environ.get("MD2AUDIO_FFMPEG"),
        os.environ.get("FFMPEG_PATH"),
        shutil.which("ffmpeg"),
        *COMMON_FFMPEG_PATHS,
        *_winget_ffmpeg_paths(),
    ]

    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate).expanduser()
        if path.is_file():
            return str(path)

    return None


def _winget_ffmpeg_paths() -> list[Path]:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        return []

    winget_packages = (
        Path(local_app_data)
        / "Microsoft"
        / "WinGet"
        / "Packages"
        / "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
    )
    if not winget_packages.is_dir():
        return []

    return sorted(winget_packages.glob("ffmpeg-*-full_build/bin/ffmpeg.exe"), reverse=True)


def _combine_with_ffmpeg(
    chunk_paths: list[Path],
    output_path: Path,
    ffmpeg_exe: str,
) -> None:
    list_path = output_path.with_suffix(".concat.txt")
    lines = [f"file '{_ffmpeg_path(path)}'" for path in chunk_paths]
    list_path.write_text("\n".join(lines), encoding="utf-8")
    try:
        subprocess.run(
            [
                ffmpeg_exe,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_path),
                "-c",
                "copy",
                str(output_path),
            ],
            check=True,
        )
    finally:
        list_path.unlink(missing_ok=True)


def _combine_binary(chunk_paths: list[Path], output_path: Path) -> None:
    with output_path.open("wb") as target:
        for index, chunk_path in enumerate(chunk_paths):
            data = chunk_path.read_bytes()
            if index > 0:
                data = _strip_id3v2(data)
            if index < len(chunk_paths) - 1:
                data = _strip_id3v1(data)
            target.write(data)


def _strip_id3v2(data: bytes) -> bytes:
    if len(data) < 10 or data[:3] != b"ID3":
        return data

    size = (
        ((data[6] & 0x7F) << 21)
        | ((data[7] & 0x7F) << 14)
        | ((data[8] & 0x7F) << 7)
        | (data[9] & 0x7F)
    )
    offset = 10 + size
    return data[offset:] if offset < len(data) else b""


def _strip_id3v1(data: bytes) -> bytes:
    if len(data) >= 128 and data[-128:-125] == b"TAG":
        return data[:-128]
    return data


def _ffmpeg_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").replace("'", "'\\''")
