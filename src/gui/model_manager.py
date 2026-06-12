from __future__ import annotations

import hashlib
import time
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
    sha256: str

    @property
    def path(self) -> Path:
        return MODEL_DIR / self.name


KOKORO_MODEL_FILES = [
    KokoroModelFile(
        name="kokoro-v1.0.onnx",
        url="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx",
        expected_size=325_532_387,
        sha256="7d5df8ecf7d4b1878015a32686053fd0eebe2bc377234608764cc0ef3636a6c5",
    ),
    KokoroModelFile(
        name="voices-v1.0.bin",
        url="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin",
        expected_size=28_214_398,
        sha256="bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d",
    ),
]


def model_status() -> list[dict]:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for model in KOKORO_MODEL_FILES:
        validation = validate_model_file(model)
        rows.append(
            {
                "name": model.name,
                "path": str(model.path),
                "url": model.url,
                "status": validation["status"],
                "installed": validation["valid"],
                "valid": validation["valid"],
                "size": validation["size"],
                "expectedSize": model.expected_size,
                "sha256": validation["sha256"],
                "expectedSha256": model.sha256,
                "sizeText": format_bytes(
                    validation["size"] if validation["exists"] else model.expected_size
                ),
            }
        )
    return rows


def models_installed() -> bool:
    return all(item["installed"] for item in model_status())


def validate_model_file(model: KokoroModelFile) -> dict:
    if not model.path.exists():
        return {
            "exists": False,
            "valid": False,
            "status": "Falta",
            "size": 0,
            "sha256": "",
        }

    size = model.path.stat().st_size
    if size != model.expected_size:
        return {
            "exists": True,
            "valid": False,
            "status": "Incompleto",
            "size": size,
            "sha256": "",
        }

    digest = sha256_file(model.path)
    valid = digest == model.sha256
    return {
        "exists": True,
        "valid": valid,
        "status": "Instalado" if valid else "Corrupto",
        "size": size,
        "sha256": digest,
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    status = Signal(str)
    finished = Signal()
    error = Signal(str)

    def __init__(self, retries: int = 3) -> None:
        super().__init__()
        self.retries = retries
        self._cancelled = False

    @Slot()
    def run(self) -> None:
        try:
            missing = [
                model for model in KOKORO_MODEL_FILES if not validate_model_file(model)["valid"]
            ]
            if not missing:
                self.log.emit("Modelos Kokoro ya instalados.")
                self.progress.emit(100)
                return

            MODEL_DIR.mkdir(parents=True, exist_ok=True)
            total = sum(model.expected_size for model in missing)
            done = 0

            for model in missing:
                if self._cancelled:
                    self.log.emit("Descarga cancelada.")
                    return

                done = self._download_with_retries(model, total, done)
                validation = validate_model_file(model)
                if not validation["valid"]:
                    model.path.unlink(missing_ok=True)
                    raise RuntimeError(
                        f"Modelo invalido tras descarga: {model.name} ({validation['status']})"
                    )
                self.log.emit(f"Modelo instalado: {model.name}")

            self.progress.emit(100)
            self.status.emit("Descarga completa")
        except Exception as exc:  # pragma: no cover - surfaced in GUI
            self.error.emit(str(exc))
        finally:
            self.finished.emit()

    def _download_with_retries(
        self,
        model: KokoroModelFile,
        total: int,
        done: int,
    ) -> int:
        last_error: Exception | None = None
        temp_path = model.path.with_suffix(model.path.suffix + ".part")

        for attempt in range(1, self.retries + 1):
            if self._cancelled:
                temp_path.unlink(missing_ok=True)
                self.log.emit("Descarga cancelada.")
                return done

            try:
                temp_path.unlink(missing_ok=True)
                self.log.emit(f"Descargando {model.name} (intento {attempt}/{self.retries})...")
                started = time.perf_counter()
                file_done = 0
                with urllib.request.urlopen(model.url, timeout=30) as response:
                    with temp_path.open("wb") as target:
                        while True:
                            if self._cancelled:
                                temp_path.unlink(missing_ok=True)
                                self.log.emit("Descarga cancelada.")
                                return done
                            chunk = response.read(1024 * 1024)
                            if not chunk:
                                break
                            target.write(chunk)
                            file_done += len(chunk)
                            current_done = done + file_done
                            elapsed = max(time.perf_counter() - started, 0.001)
                            speed = file_done / elapsed
                            self.progress.emit(min(100, int(current_done * 100 / total)))
                            self.status.emit(
                                f"{format_bytes(current_done)} / {format_bytes(total)} - "
                                f"{format_bytes(int(speed))}/s"
                            )

                temp_path.replace(model.path)
                return done + file_done
            except Exception as exc:
                last_error = exc
                temp_path.unlink(missing_ok=True)
                self.log.emit(f"Fallo descargando {model.name}: {exc}")

        raise RuntimeError(f"No se pudo descargar {model.name}: {last_error}")

    @Slot()
    def cancel(self) -> None:
        self._cancelled = True
