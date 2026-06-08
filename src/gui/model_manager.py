from __future__ import annotations

import urllib.request
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = PROJECT_ROOT / "models" / "kokoro"


@dataclass(frozen=True)
class KokoroModelFile:
    name: str
    url: str
    expected_size: int

    @property
    def path(self) -> Path:
        return MODEL_DIR / self.name


KOKORO_MODEL_FILES = [
    KokoroModelFile(
        name="kokoro-v1.0.onnx",
        url="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx",
        expected_size=325_532_387,
    ),
    KokoroModelFile(
        name="voices-v1.0.bin",
        url="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin",
        expected_size=28_214_398,
    ),
]


def model_status() -> list[dict]:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for model in KOKORO_MODEL_FILES:
        exists = model.path.is_file()
        size = model.path.stat().st_size if exists else 0
        rows.append(
            {
                "name": model.name,
                "path": str(model.path),
                "url": model.url,
                "status": "Instalado" if exists else "Falta",
                "installed": exists,
                "size": size,
                "expectedSize": model.expected_size,
                "sizeText": format_bytes(size if exists else model.expected_size),
            }
        )
    return rows


def models_installed() -> bool:
    return all(item["installed"] for item in model_status())


def format_bytes(value: int) -> str:
    size = float(value)
    for suffix in ("B", "KB", "MB", "GB"):
        if size < 1024 or suffix == "GB":
            return f"{size:.1f} {suffix}" if suffix != "B" else f"{int(size)} B"
        size /= 1024
    return f"{value} B"


class ModelDownloadWorker(QObject):
    log = Signal(str)
    progress = Signal(int)
    finished = Signal()
    error = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._cancelled = False

    @Slot()
    def run(self) -> None:
        try:
            missing = [model for model in KOKORO_MODEL_FILES if not model.path.exists()]
            if not missing:
                self.log.emit("Modelos Kokoro ya instalados.")
                self.progress.emit(100)
                self.finished.emit()
                return

            MODEL_DIR.mkdir(parents=True, exist_ok=True)
            total = sum(model.expected_size for model in missing)
            done = 0

            for model in missing:
                if self._cancelled:
                    self.log.emit("Descarga cancelada.")
                    self.finished.emit()
                    return

                self.log.emit(f"Descargando {model.name}...")
                temp_path = model.path.with_suffix(model.path.suffix + ".part")
                with urllib.request.urlopen(model.url) as response, temp_path.open("wb") as target:
                    while True:
                        if self._cancelled:
                            temp_path.unlink(missing_ok=True)
                            self.log.emit("Descarga cancelada.")
                            self.finished.emit()
                            return
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        target.write(chunk)
                        done += len(chunk)
                        self.progress.emit(min(100, int(done * 100 / total)))

                temp_path.replace(model.path)
                self.log.emit(f"Modelo instalado: {model.name}")

            self.progress.emit(100)
            self.finished.emit()
        except Exception as exc:  # pragma: no cover - surfaced in GUI
            self.error.emit(str(exc))

    @Slot()
    def cancel(self) -> None:
        self._cancelled = True
