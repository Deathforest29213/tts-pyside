from __future__ import annotations

import asyncio
import shutil
import time
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from ..chunker import chunk_paragraphs
from ..conversion import (
    ConversionCallbacks,
    ConversionResult,
    convert_markdown_file,
    format_duration,
    safe_stem,
)
from ..engines.base import SynthesisOptions
from ..engines.kokoro import KokoroTTSEngine
from ..parser import parse_markdown_file


class ConversionWorker(QObject):
    log = Signal(str)
    progress = Signal(int)
    fileStarted = Signal(int, str)
    fileFinished = Signal(int, str, str)
    fileOmitted = Signal(int, str)
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
        normalize_audio: bool,
    ) -> None:
        super().__init__()
        self.files = files
        self.voice = voice
        self.speed = speed
        self.max_chars = max_chars
        self.ffmpeg_path = ffmpeg_path
        self.force = force
        self.clean_temp = clean_temp
        self.normalize_audio = normalize_audio
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
                result = await self._convert_prepared_file(
                    index, item, engine, options, total_chunks, completed_units
                )
                completed_units += max(1, len(item["chunks"]))
                self.progress.emit(int(completed_units * 100 / total_chunks))
                if result.status == "omitted":
                    self.fileOmitted.emit(row_index, result.message)
                    self.log.emit(f"Omitido {item['relativePath']}: {result.message}")
                else:
                    self.fileFinished.emit(row_index, str(result.output_path), result.elapsed_text)
                    self.log.emit(f"MP3 generado: {result.output_path}")
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
    ) -> ConversionResult:
        source_path = Path(item["sourcePath"])
        output_path = Path(item["outputPath"])
        estimated_chunks = max(1, len(item["chunks"]))

        def chunk_done(chunk_index: int, _chunk_count: int) -> None:
            if self._cancelled:
                return
            self.progress.emit(
                int((completed_units + min(chunk_index, estimated_chunks)) * 100 / total_chunks)
            )

        if self._cancelled:
            raise CancelledConversion()

        result = await convert_markdown_file(
            markdown_file=source_path,
            output_path=output_path,
            engine=engine,
            options=options,
            max_chars=self.max_chars,
            force=self.force,
            clean_temp=self.clean_temp,
            callbacks=ConversionCallbacks(log=self.log.emit, chunk_done=chunk_done),
            normalize_audio=self.normalize_audio,
        )
        if self._cancelled:
            raise CancelledConversion()
        return result

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


class VoicePreviewWorker(QObject):
    log = Signal(str)
    finished = Signal(str)
    error = Signal(str)

    def __init__(
        self,
        output_path: Path,
        voice: str,
        speed: float,
        ffmpeg_path: str | None,
    ) -> None:
        super().__init__()
        self.output_path = output_path
        self.voice = voice
        self.speed = speed
        self.ffmpeg_path = ffmpeg_path

    @Slot()
    def run(self) -> None:
        try:
            asyncio.run(self._run_async())
        except Exception as exc:  # pragma: no cover - surfaced in GUI
            self.error.emit(str(exc))

    async def _run_async(self) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        engine = KokoroTTSEngine()
        options = SynthesisOptions(
            voice=self.voice,
            speed=self.speed,
            language="es",
            ffmpeg_path=self.ffmpeg_path,
        )
        sample = (
            "Esta es una prueba de voz para md2audio. "
            "La lectura debe sonar clara, natural y adecuada para estudiar."
        )
        started = time.perf_counter()
        await engine.synthesize_to_file(sample, self.output_path, options)
        elapsed = format_duration(time.perf_counter() - started)
        self.log.emit(f"Prueba de voz generada en {elapsed}: {self.output_path}")
        self.finished.emit(str(self.output_path))
