from __future__ import annotations

import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QObject, QThread, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog

from ..audio import resolve_ffmpeg
from ..conversion import validate_preflight
from ..engines.kokoro import DEFAULT_MODEL_PATH
from .file_scanner import mirror_output_path, scan_markdown_files
from .model_manager import ModelDownloadWorker, model_status, models_installed
from .settings import PRESETS, PROJECT_ROOT, GuiSettings, ProfileStore
from .workers import ConversionWorker, VoicePreviewWorker

KOKORO_VOICES = ["ef_dora", "em_alex", "em_santa"]


class AppBridge(QObject):
    inputPathChanged = Signal()
    outputPathChanged = Signal()
    filesChanged = Signal()
    logTextChanged = Signal()
    progressChanged = Signal()
    currentFileChanged = Signal()
    elapsedTextChanged = Signal()
    convertingChanged = Signal()
    settingsChanged = Signal()
    modelsChanged = Signal()
    selectedIndexChanged = Signal()
    downloadProgressChanged = Signal()
    downloadStatusChanged = Signal()
    previewChanged = Signal()
    profilesChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.settings = GuiSettings()
        self.profiles = ProfileStore()
        self._input_path = str(self.settings.get("input_path"))
        self._output_base_path = str(self.settings.get("output_path"))
        self._voice = str(self.settings.get("voice", "em_santa"))
        self._speed = float(self.settings.get("speed", 1.0))
        self._max_chars = int(self.settings.get("max_chars", 900))
        self._recursive = bool(self.settings.get("recursive", False))
        self._force = bool(self.settings.get("force", False))
        self._clean_temp = bool(self.settings.get("clean_temp", False))
        self._normalize_loudness = bool(self.settings.get("normalize_loudness", False))
        self._selected_preset = str(self.settings.get("selected_preset", "Apuntes tecnicos"))
        self._window_width = int(self.settings.get("window_width", 1180))
        self._window_height = int(self.settings.get("window_height", 840))

        self._files: list[dict] = []
        self._log_lines: list[str] = []
        self._progress = 0
        self._download_progress = 0
        self._download_status = ""
        self._current_file = ""
        self._elapsed_text = "0s"
        self._is_converting = False
        self._selected_index = -1
        self._conversion_thread: QThread | None = None
        self._conversion_worker: ConversionWorker | None = None
        self._download_thread: QThread | None = None
        self._download_worker: ModelDownloadWorker | None = None
        self._preview_thread: QThread | None = None
        self._preview_worker: VoicePreviewWorker | None = None
        self._preview_path = ""
        self._is_previewing = False

        self.scanInput()
        self._log_startup_state()

    @Property(str, notify=inputPathChanged)
    def inputPath(self) -> str:
        return self._input_path

    @Property(str, notify=outputPathChanged)
    def outputPath(self) -> str:
        return str(self._resolved_output_path())

    @Property(str, notify=outputPathChanged)
    def outputBasePath(self) -> str:
        return self._output_base_path

    @Property("QVariantList", notify=filesChanged)  # type: ignore[arg-type]
    def files(self) -> list[dict]:
        return self._files

    @Property("QVariantList", constant=True)  # type: ignore[arg-type]
    def voices(self) -> list[str]:
        return KOKORO_VOICES

    @Property(str, notify=settingsChanged)
    def selectedVoice(self) -> str:
        return self._voice

    @Property(float, notify=settingsChanged)
    def speed(self) -> float:
        return self._speed

    @Property(int, notify=settingsChanged)
    def maxChars(self) -> int:
        return self._max_chars

    @Property(bool, notify=settingsChanged)
    def recursive(self) -> bool:
        return self._recursive

    @Property(bool, notify=settingsChanged)
    def force(self) -> bool:
        return self._force

    @Property(bool, notify=settingsChanged)
    def cleanTemp(self) -> bool:
        return self._clean_temp

    @Property(bool, notify=settingsChanged)
    def normalizeLoudness(self) -> bool:
        return self._normalize_loudness

    @Property("QVariantList", constant=True)  # type: ignore[arg-type]
    def presets(self) -> list[str]:
        return list(PRESETS.keys())

    @Property(str, notify=settingsChanged)
    def selectedPreset(self) -> str:
        return self._selected_preset

    @Property(str, notify=logTextChanged)
    def logText(self) -> str:
        return "\n".join(reversed(self._log_lines))

    @Property(int, notify=progressChanged)
    def progress(self) -> int:
        return self._progress

    @Property(int, notify=downloadProgressChanged)
    def downloadProgress(self) -> int:
        return self._download_progress

    @Property(str, notify=downloadStatusChanged)
    def downloadStatusText(self) -> str:
        return self._download_status

    @Property(bool, notify=previewChanged)
    def isPreviewing(self) -> bool:
        return self._is_previewing

    @Property(bool, notify=previewChanged)
    def previewReady(self) -> bool:
        return bool(self._preview_path and Path(self._preview_path).exists())

    @Property(str, notify=previewChanged)
    def previewPath(self) -> str:
        return self._preview_path

    @Property("QVariantList", notify=profilesChanged)  # type: ignore[arg-type]
    def profileNames(self) -> list[str]:
        return self.profiles.names()

    @Property(str, notify=currentFileChanged)
    def currentFile(self) -> str:
        return self._current_file

    @Property(str, notify=elapsedTextChanged)
    def elapsedText(self) -> str:
        return self._elapsed_text

    @Property(bool, notify=convertingChanged)
    def isConverting(self) -> bool:
        return self._is_converting

    @Property(bool, notify=modelsChanged)
    def modelsReady(self) -> bool:
        return models_installed()

    @Property("QVariantList", notify=modelsChanged)  # type: ignore[arg-type]
    def models(self) -> list[dict]:
        return model_status()

    @Property(str, notify=modelsChanged)
    def modelStatusText(self) -> str:
        return "Instalado" if self.modelsReady else "Faltan modelos"

    @Property(str, constant=True)
    def modelDir(self) -> str:
        return str(DEFAULT_MODEL_PATH.parent)

    @Property(str, notify=settingsChanged)
    def ffmpegStatus(self) -> str:
        return resolve_ffmpeg() or "no detectado"

    @Property(bool, notify=settingsChanged)
    def ffmpegReady(self) -> bool:
        return resolve_ffmpeg() is not None

    @Property(int, notify=filesChanged)
    def fileCount(self) -> int:
        return len(self._files)

    @Property(int, notify=filesChanged)
    def selectedFileCount(self) -> int:
        return self._selected_file_count()

    @Property(int, notify=selectedIndexChanged)
    def selectedIndex(self) -> int:
        return self._selected_index

    @Property(int, notify=settingsChanged)
    def windowWidth(self) -> int:
        return self._window_width

    @Property(int, notify=settingsChanged)
    def windowHeight(self) -> int:
        return self._window_height

    @Slot()
    def selectFile(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            None,
            "Seleccionar Markdown",
            str(
                Path(self._input_path)
                if Path(self._input_path).exists()
                else PROJECT_ROOT / "input"
            ),
            "Markdown (*.md)",
        )
        if path:
            self._set_input_path(path)

    @Slot()
    def selectFolder(self) -> None:
        path = QFileDialog.getExistingDirectory(
            None,
            "Seleccionar carpeta con Markdown",
            str(
                Path(self._input_path)
                if Path(self._input_path).exists()
                else PROJECT_ROOT / "input"
            ),
        )
        if path:
            self._set_input_path(path)

    @Slot()
    def openInput(self) -> None:
        self._open_path(Path(self._input_path))

    @Slot()
    def openOutput(self) -> None:
        path = self._resolved_output_path()
        path.mkdir(parents=True, exist_ok=True)
        self._open_path(path)

    @Slot()
    def openSelectedMp3(self) -> None:
        item = self._selected_item()
        if item:
            self._open_path(Path(item["outputPath"]))

    @Slot()
    def openSelectedManifest(self) -> None:
        item = self._selected_item()
        if item:
            self._open_path(Path(item["manifestPath"]))

    @Slot()
    def openModelFolder(self) -> None:
        DEFAULT_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._open_path(DEFAULT_MODEL_PATH.parent)

    @Slot()
    def scanInput(self) -> None:
        input_path = Path(self._input_path)
        output_path = Path(self._output_base_path)
        self._selected_index = -1
        try:
            if not input_path.exists():
                self._files = []
                self._append_log(f"Entrada no existe: {input_path}")
            else:
                self._files = scan_markdown_files(input_path, output_path, self._recursive)
                if self._files:
                    self._append_log(f"Detectados {len(self._files)} archivos Markdown.")
                else:
                    self._append_log("No se encontraron archivos .md en la entrada.")
        except Exception as exc:
            self._files = []
            self._append_log(f"Error escaneando entrada: {exc}")

        self.filesChanged.emit()
        self.selectedIndexChanged.emit()
        self.outputPathChanged.emit()

    @Slot()
    def startConversion(self) -> None:
        if self._is_converting:
            self._append_log("Ya hay una conversion en curso.")
            return

        error = self._validation_error()
        if error:
            self._append_log(error)
            return
        preflight = validate_preflight(
            input_path=Path(self._input_path),
            output_path=self._resolved_output_path(),
            selected_count=self._selected_file_count(),
            ffmpeg_path=resolve_ffmpeg(),
            models_ready=models_installed(),
        )
        for warning in preflight.warnings:
            self._append_log(f"Aviso: {warning}")
        if not preflight.ok:
            for preflight_error in preflight.errors:
                self._append_log(preflight_error)
            return

        self._set_converting(True)
        self._set_progress(0)
        self._current_file = ""
        self.currentFileChanged.emit()
        selected_files = [
            {**dict(item), "rowIndex": index}
            for index, item in enumerate(self._files)
            if item.get("included", False)
        ]

        worker = ConversionWorker(
            files=selected_files,
            voice=self._voice,
            speed=self._speed,
            max_chars=self._max_chars,
            ffmpeg_path=resolve_ffmpeg(),
            force=self._force,
            clean_temp=self._clean_temp,
            normalize_audio=self._normalize_loudness,
        )
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.log.connect(self._append_log)
        worker.progress.connect(self._set_progress)
        worker.fileStarted.connect(self._on_file_started)
        worker.fileFinished.connect(self._on_file_finished)
        worker.fileOmitted.connect(self._on_file_omitted)
        worker.fileError.connect(self._on_file_error)
        worker.fileCancelled.connect(self._on_file_cancelled)
        worker.finished.connect(self._on_conversion_finished)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_conversion_thread)
        thread.start()

        self._conversion_worker = worker
        self._conversion_thread = thread
        self._append_log(f"Conversion iniciada con {len(selected_files)} archivos.")

    @Slot()
    def cancelConversion(self) -> None:
        if self._conversion_worker:
            self._append_log("Cancelando conversion al terminar el chunk actual...")
            self._conversion_worker.cancel()

    @Slot()
    def downloadMissingModels(self) -> None:
        if self._download_thread:
            self._append_log("Ya hay una descarga en curso.")
            return

        self._download_progress = 0
        self._download_status = ""
        self.downloadProgressChanged.emit()
        self.downloadStatusChanged.emit()

        worker = ModelDownloadWorker()
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.log.connect(self._append_log)
        worker.progress.connect(self._set_download_progress)
        worker.status.connect(self._set_download_status)
        worker.error.connect(self._on_download_error)
        worker.finished.connect(self._on_download_finished)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_download_thread)
        thread.start()

        self._download_worker = worker
        self._download_thread = thread

    @Slot(str)
    def setVoice(self, value: str) -> None:
        if value and value != self._voice:
            self._voice = value
            self.settings.set("voice", value)
            self.settingsChanged.emit()

    @Slot(float)
    def setSpeed(self, value: float) -> None:
        value = round(float(value), 2)
        if value != self._speed:
            self._speed = value
            self.settings.set("speed", value)
            self.settingsChanged.emit()

    @Slot(int)
    def setMaxChars(self, value: int) -> None:
        value = max(300, int(value))
        if value != self._max_chars:
            self._max_chars = value
            self.settings.set("max_chars", value)
            self.settingsChanged.emit()

    @Slot(bool)
    def setRecursive(self, value: bool) -> None:
        if value != self._recursive:
            self._recursive = value
            self.settings.set("recursive", value)
            self.settingsChanged.emit()
            self.scanInput()

    @Slot(bool)
    def setForce(self, value: bool) -> None:
        if value != self._force:
            self._force = value
            self.settings.set("force", value)
            self.settingsChanged.emit()

    @Slot(bool)
    def setCleanTemp(self, value: bool) -> None:
        if value != self._clean_temp:
            self._clean_temp = value
            self.settings.set("clean_temp", value)
            self.settingsChanged.emit()

    @Slot(bool)
    def setNormalizeLoudness(self, value: bool) -> None:
        if value != self._normalize_loudness:
            self._normalize_loudness = value
            self.settings.set("normalize_loudness", value)
            self.settingsChanged.emit()

    @Slot(str)
    def applyPreset(self, name: str) -> None:
        preset = PRESETS.get(name)
        if not preset:
            self._append_log(f"Preset no encontrado: {name}")
            return

        self._selected_preset = name
        self._voice = str(preset["voice"])
        self._speed = float(preset["speed"])
        self._max_chars = int(preset["max_chars"])
        self._recursive = bool(preset["recursive"])
        self._force = bool(preset["force"])
        self._normalize_loudness = bool(preset["normalize_loudness"])
        self.settings.update(
            {
                "selected_preset": self._selected_preset,
                "voice": self._voice,
                "speed": self._speed,
                "max_chars": self._max_chars,
                "recursive": self._recursive,
                "force": self._force,
                "normalize_loudness": self._normalize_loudness,
            }
        )
        self.settingsChanged.emit()
        self.scanInput()
        self._append_log(f"Preset aplicado: {name}")

    @Slot(str)
    def saveProfile(self, name: str) -> None:
        try:
            self.profiles.save_profile(name, self._profile_payload())
        except ValueError as exc:
            self._append_log(str(exc))
            return
        self.profilesChanged.emit()
        self._append_log(f"Perfil guardado: {name.strip()}")

    @Slot(str)
    def loadProfile(self, name: str) -> None:
        try:
            profile = self.profiles.load_profile(name)
        except ValueError as exc:
            self._append_log(str(exc))
            return

        self._voice = str(profile.get("voice", self._voice))
        self._input_path = str(profile.get("input_path", self._input_path))
        self._output_base_path = str(profile.get("output_path", self._output_base_path))
        self._speed = float(profile.get("speed", self._speed))
        self._max_chars = int(profile.get("max_chars", self._max_chars))
        self._recursive = bool(profile.get("recursive", self._recursive))
        self._force = bool(profile.get("force", self._force))
        self._clean_temp = bool(profile.get("clean_temp", self._clean_temp))
        self._normalize_loudness = bool(profile.get("normalize_loudness", self._normalize_loudness))
        self._selected_preset = str(profile.get("selected_preset", self._selected_preset))
        self.settings.update(self._profile_payload())
        self.inputPathChanged.emit()
        self.outputPathChanged.emit()
        self.settingsChanged.emit()
        self.scanInput()
        self._append_log(f"Perfil cargado: {name}")

    @Slot()
    def previewVoice(self) -> None:
        if self._preview_thread:
            self._append_log("Ya hay una prueba de voz en curso.")
            return
        if not self.modelsReady:
            self._append_log("Faltan modelos Kokoro validos para probar voz.")
            return
        if not resolve_ffmpeg():
            self._append_log("No se detecto ffmpeg para probar voz.")
            return

        output_path = PROJECT_ROOT / "output" / ".preview" / f"preview_{self._voice}.mp3"
        worker = VoicePreviewWorker(
            output_path=output_path,
            voice=self._voice,
            speed=self._speed,
            ffmpeg_path=resolve_ffmpeg(),
        )
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.log.connect(self._append_log)
        worker.finished.connect(self._on_preview_finished)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.error.connect(self._on_preview_error)
        worker.error.connect(thread.quit)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_preview_thread)
        self._preview_thread = thread
        self._preview_worker = worker
        self._is_previewing = True
        self.previewChanged.emit()
        thread.start()
        self._append_log(f"Generando prueba de voz: {self._voice}")

    @Slot()
    def openPreview(self) -> None:
        if self._preview_path:
            self._open_path(Path(self._preview_path))

    @Slot(int)
    def selectFileRow(self, index: int) -> None:
        if index < -1 or index >= len(self._files):
            return
        self._selected_index = index
        self.selectedIndexChanged.emit()

    @Slot(int)
    def toggleFileForConversion(self, index: int) -> None:
        if index < 0 or index >= len(self._files) or self._is_converting:
            return
        self._selected_index = index
        updated = dict(self._files[index])
        updated["included"] = not bool(updated.get("included", False))
        self._files[index] = updated
        self.selectedIndexChanged.emit()
        self.filesChanged.emit()

    @Slot()
    def toggleAllFiles(self) -> None:
        if self._is_converting:
            return
        include_all = self.selectedFileCount != len(self._files)
        self._files = [{**dict(item), "included": include_all} for item in self._files]
        self.filesChanged.emit()
        if include_all:
            self._append_log(f"Agregados {self._selected_file_count()} archivos a la conversion.")
        else:
            self._append_log("Todos los archivos fueron quitados de la conversion.")

    @Slot(int, int)
    def saveWindowSize(self, width: int, height: int) -> None:
        self._window_width = int(width)
        self._window_height = int(height)
        self.settings.update(
            {"window_width": self._window_width, "window_height": self._window_height}
        )
        self.settingsChanged.emit()

    def _set_input_path(self, path: str) -> None:
        self._input_path = path
        self.settings.set("input_path", path)
        self.inputPathChanged.emit()
        self.scanInput()

    def _resolved_output_path(self) -> Path:
        output_base = Path(self._output_base_path)
        input_path = Path(self._input_path)
        if input_path.is_dir():
            return mirror_output_path(input_path, output_base)
        return output_base

    def _validation_error(self) -> str:
        if not Path(self._input_path).exists():
            return f"No existe la entrada: {self._input_path}"
        if not self._files:
            return "No hay archivos .md para convertir."
        if self.selectedFileCount == 0:
            return "No hay archivos seleccionados para convertir."
        if not self.modelsReady:
            return "Faltan modelos Kokoro. Usa Administrar modelos."
        if not resolve_ffmpeg():
            return "No se detecto ffmpeg. Instala ffmpeg o configura la ruta."
        return ""

    def _on_file_started(self, index: int, relative_path: str) -> None:
        self._update_file(index, status="Generando", message="Generando...")
        self._current_file = relative_path
        self.currentFileChanged.emit()

    def _on_file_finished(self, index: int, output_path: str, elapsed: str) -> None:
        self._update_file(
            index, status="Listo", outputPath=output_path, time=elapsed, message="MP3 generado"
        )
        self._elapsed_text = elapsed
        self.elapsedTextChanged.emit()

    def _on_file_omitted(self, index: int, message: str) -> None:
        self._update_file(index, status="Omitido", message=message)

    def _on_file_error(self, index: int, message: str) -> None:
        self._update_file(index, status="Error", message=message)

    def _on_file_cancelled(self, index: int, message: str) -> None:
        self._update_file(index, status="Cancelado", message=message)

    def _on_conversion_finished(self) -> None:
        self._set_converting(False)
        self._append_log("Conversion finalizada.")

    def _clear_conversion_thread(self) -> None:
        self._conversion_worker = None
        self._conversion_thread = None

    def _on_download_error(self, message: str) -> None:
        self._append_log(f"Error descargando modelos: {message}")
        self.modelsChanged.emit()

    def _on_download_finished(self) -> None:
        self._append_log("Revision de modelos finalizada.")
        self.modelsChanged.emit()

    def _clear_download_thread(self) -> None:
        self._download_worker = None
        self._download_thread = None

    def _on_preview_finished(self, path: str) -> None:
        self._preview_path = path
        self._is_previewing = False
        self.previewChanged.emit()

    def _on_preview_error(self, message: str) -> None:
        self._append_log(f"Error generando prueba de voz: {message}")
        self._is_previewing = False
        self.previewChanged.emit()

    def _clear_preview_thread(self) -> None:
        self._preview_worker = None
        self._preview_thread = None

    def _set_progress(self, value: int) -> None:
        self._progress = max(0, min(100, int(value)))
        self.progressChanged.emit()

    def _set_download_progress(self, value: int) -> None:
        self._download_progress = max(0, min(100, int(value)))
        self.downloadProgressChanged.emit()

    def _set_download_status(self, value: str) -> None:
        self._download_status = value
        self.downloadStatusChanged.emit()

    def _set_converting(self, value: bool) -> None:
        self._is_converting = value
        self.convertingChanged.emit()

    def _update_file(self, index: int, **changes: Any) -> None:
        if index < 0 or index >= len(self._files):
            return
        updated = dict(self._files[index])
        updated.update(changes)
        self._files[index] = updated
        self.filesChanged.emit()

    def _selected_item(self) -> dict | None:
        if 0 <= self._selected_index < len(self._files):
            return self._files[self._selected_index]
        self._append_log("Selecciona un archivo en la tabla primero.")
        return None

    def _selected_file_count(self) -> int:
        return sum(1 for item in self._files if item.get("included", False))

    def _append_log(self, message: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        self._log_lines.append(f"{stamp}  {message}")
        self._log_lines = self._log_lines[-500:]
        self.logTextChanged.emit()

    def _log_startup_state(self) -> None:
        self._append_log(f"Kokoro: {self.modelStatusText}")
        self._append_log(f"Voz: {self._voice}")
        self._append_log(f"FFmpeg: {resolve_ffmpeg() or 'no detectado'}")

    def _profile_payload(self) -> dict[str, Any]:
        return {
            "input_path": self._input_path,
            "output_path": self._output_base_path,
            "voice": self._voice,
            "speed": self._speed,
            "max_chars": self._max_chars,
            "recursive": self._recursive,
            "force": self._force,
            "clean_temp": self._clean_temp,
            "normalize_loudness": self._normalize_loudness,
            "selected_preset": self._selected_preset,
        }

    @staticmethod
    def _open_path(path: Path) -> None:
        if not path.exists():
            return
        if path.is_file():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
            return

        if os.name == "nt":
            subprocess.Popen(["explorer", str(path)])
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
