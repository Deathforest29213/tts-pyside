from __future__ import annotations

import asyncio
import shutil
import time
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal, Slot

from ..audio import combine_mp3_chunks
from ..chunker import chunk_paragraphs
from ..cli import (
    can_reuse_chunk,
    format_duration,
    hash_text,
    read_manifest,
    safe_stem,
    write_manifest,
)
from ..engines.base import SynthesisOptions
from ..engines.kokoro import KokoroTTSEngine
from ..parser import parse_markdown_file


class ConversionWorker(QObject):
    log = Signal(str)
    progress = Signal(int)
    fileStarted = Signal(int, str)
    fileFinished = Signal(int, str, str)
    fileError = Signal(int, str)
    fileCancelled = Signal(int, str)
    finished = Signal()
    cancelled = Signal()

    def __init__(
        self,
        files: list[dict],
        voice: str,
        speed: float,
        max_chars: int,
        ffmpeg_path: str | None,
        force: bool,
        clean_temp: bool,
    ) -> None:
        super().__init__()
        self.files = files
        self.voice = voice
        self.speed = speed
        self.max_chars = max_chars
        self.ffmpeg_path = ffmpeg_path
        self.force = force
        self.clean_temp = clean_temp
        self._cancelled = False

    @Slot()
    def run(self) -> None:
        try:
            asyncio.run(self._run_async())
        except Exception as exc:  # pragma: no cover - surfaced in GUI
            self.log.emit(f"Error general: {exc}")
        finally:
            self.finished.emit()

    async def _run_async(self) -> None:
        if not self.files:
            self.log.emit("No hay archivos Markdown para convertir.")
            self.progress.emit(0)
            return

        prepared: list[dict] = []
        total_chunks = 0
        for item in self.files:
            if self._cancelled:
                self._emit_cancelled_from(len(prepared))
                return
            try:
                source_path = Path(item["sourcePath"])
                paragraphs = parse_markdown_file(source_path)
                chunks = chunk_paragraphs(paragraphs, max_chars=self.max_chars)
                prepared.append({**item, "paragraphs": paragraphs, "chunks": chunks})
                total_chunks += max(1, len(chunks))
            except Exception as exc:
                prepared.append({**item, "error": str(exc), "chunks": []})
                total_chunks += 1

        engine = KokoroTTSEngine()
        options = SynthesisOptions(
            voice=self.voice,
            speed=self.speed,
            language="es",
            ffmpeg_path=self.ffmpeg_path,
        )

        self.log.emit(f"Motor: kokoro | Voz: {self.voice} | Speed: {self.speed}")
        completed_units = 0
        batch_started = time.perf_counter()

        for index, item in enumerate(prepared):
            row_index = int(item.get("rowIndex", index))
            if self._cancelled:
                self._emit_cancelled_from(index)
                return

            if item.get("error"):
                self.fileError.emit(row_index, item["error"])
                self.log.emit(f"Error preparando {item['relativePath']}: {item['error']}")
                completed_units += 1
                self.progress.emit(int(completed_units * 100 / total_chunks))
                continue

            self.fileStarted.emit(row_index, item["relativePath"])
            self.log.emit(f"Generando archivo {index + 1}/{len(prepared)}: {item['relativePath']}")

            try:
                elapsed = await self._convert_prepared_file(
                    index, item, engine, options, total_chunks, completed_units
                )
                completed_units += max(1, len(item["chunks"]))
                self.progress.emit(int(completed_units * 100 / total_chunks))
                self.fileFinished.emit(row_index, item["outputPath"], format_duration(elapsed))
                self.log.emit(f"MP3 generado: {item['outputPath']}")
            except CancelledConversion:
                self._cleanup_item(item)
                self.fileCancelled.emit(row_index, "Cancelado")
                self._emit_cancelled_from(index + 1)
                self.cancelled.emit()
                return
            except Exception as exc:
                completed_units += max(1, len(item["chunks"]))
                self.fileError.emit(row_index, str(exc))
                self.log.emit(f"Error en {item['relativePath']}: {exc}")
                self.progress.emit(int(completed_units * 100 / total_chunks))

        self.progress.emit(100)
        self.log.emit(
            f"Tiempo total del lote: {format_duration(time.perf_counter() - batch_started)}"
        )

    async def _convert_prepared_file(
        self,
        index: int,
        item: dict,
        engine: KokoroTTSEngine,
        options: SynthesisOptions,
        total_chunks: int,
        completed_units: int,
    ) -> float:
        started = time.perf_counter()
        source_path = Path(item["sourcePath"])
        output_path = Path(item["outputPath"])
        output_dir = output_path.parent
        stem = safe_stem(source_path.stem)
        temp_dir = output_dir / ".chunks" / stem
        temp_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = temp_dir / "manifest.json"

        previous_manifest = read_manifest(manifest_path)
        previous_chunks = {
            chunk.get("index"): chunk for chunk in previous_manifest.get("chunks", [])
        }
        manifest: dict[str, Any] = {
            "source": str(source_path),
            "output": str(output_path),
            "engine": "kokoro",
            "voice": options.voice,
            "speed": options.speed,
            "language": options.language,
            "max_chars": self.max_chars,
            "source_mtime": source_path.stat().st_mtime,
            "chunk_count": len(item["chunks"]),
            "chunks": [],
        }

        chunk_paths: list[Path] = []
        for chunk_index, chunk in enumerate(item["chunks"], start=1):
            if self._cancelled:
                raise CancelledConversion()

            chunk_path = temp_dir / f"{chunk_index:04d}.mp3"
            chunk_paths.append(chunk_path)
            chunk_hash = hash_text(chunk)
            reusable = can_reuse_chunk(
                chunk_path=chunk_path,
                chunk_hash=chunk_hash,
                previous_chunk=previous_chunks.get(chunk_index, {}),
                previous_manifest=previous_manifest,
                current_manifest=manifest,
            )

            elapsed = 0.0
            status = "reused"
            if self.force or not reusable:
                status = "generated"
                self.log.emit(f"Chunk {chunk_index}/{len(item['chunks'])}: generando...")
                chunk_started = time.perf_counter()
                await engine.synthesize_to_file(chunk, chunk_path, options)
                elapsed = time.perf_counter() - chunk_started
                self.log.emit(
                    f"Chunk {chunk_index}/{len(item['chunks'])}: ok ({format_duration(elapsed)})"
                )
            else:
                self.log.emit(f"Chunk {chunk_index}/{len(item['chunks'])}: reutilizado")

            manifest["chunks"].append(
                {
                    "index": chunk_index,
                    "path": str(chunk_path),
                    "chars": len(chunk),
                    "hash": chunk_hash,
                    "status": status,
                    "elapsed_seconds": round(elapsed, 3),
                }
            )
            write_manifest(manifest_path, manifest)
            self.progress.emit(int((completed_units + chunk_index) * 100 / total_chunks))

        if self._cancelled:
            raise CancelledConversion()

        method = combine_mp3_chunks(chunk_paths, output_path, ffmpeg_path=self.ffmpeg_path)
        manifest["combine_method"] = method
        manifest["total_elapsed_seconds"] = round(time.perf_counter() - started, 3)
        write_manifest(manifest_path, manifest)

        if self.clean_temp:
            shutil.rmtree(temp_dir, ignore_errors=True)

        return time.perf_counter() - started

    @Slot()
    def cancel(self) -> None:
        self._cancelled = True

    def _emit_cancelled_from(self, start_index: int) -> None:
        for index in range(start_index, len(self.files)):
            row_index = int(self.files[index].get("rowIndex", index))
            self.fileCancelled.emit(row_index, "Cancelado")
        self.log.emit("Conversion cancelada.")

    @staticmethod
    def _cleanup_item(item: dict) -> None:
        output_path = Path(item["outputPath"])
        source_path = Path(item["sourcePath"])
        stem = safe_stem(source_path.stem)
        shutil.rmtree(output_path.parent / ".chunks" / stem, ignore_errors=True)
        output_path.unlink(missing_ok=True)


class CancelledConversion(Exception):
    pass
