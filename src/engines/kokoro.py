from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from ..audio import resolve_ffmpeg
from .base import SynthesisOptions, TTSEngine, VoiceInfo

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_PATH = PROJECT_ROOT / "models" / "kokoro" / "kokoro-v1.0.onnx"
DEFAULT_VOICES_PATH = PROJECT_ROOT / "models" / "kokoro" / "voices-v1.0.bin"


class KokoroTTSEngine(TTSEngine):
    name = "kokoro"

    def __init__(
        self,
        model_path: Path = DEFAULT_MODEL_PATH,
        voices_path: Path = DEFAULT_VOICES_PATH,
    ) -> None:
        self.model_path = model_path
        self.voices_path = voices_path
        self._kokoro: Any = None

    async def synthesize_to_file(
        self,
        text: str,
        output_path: Path,
        options: SynthesisOptions,
    ) -> None:
        try:
            import soundfile as sf
        except ImportError as exc:
            raise RuntimeError(
                "Falta soundfile. Instala dependencias con: pip install -r requirements.txt"
            ) from exc

        kokoro = self._load_model()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        samples, sample_rate = kokoro.create(
            text,
            voice=options.voice,
            speed=options.speed,
            lang=options.language,
        )

        if output_path.suffix.lower() == ".wav":
            sf.write(output_path, samples, sample_rate)
            return

        ffmpeg_exe = resolve_ffmpeg(options.ffmpeg_path)
        if not ffmpeg_exe:
            raise RuntimeError(
                "Kokoro genera audio WAV internamente y necesita ffmpeg para exportar MP3."
            )

        wav_path = output_path.with_suffix(".wav")
        sf.write(wav_path, samples, sample_rate)
        try:
            subprocess.run(
                [
                    ffmpeg_exe,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-i",
                    str(wav_path),
                    "-codec:a",
                    "libmp3lame",
                    "-q:a",
                    "2",
                    str(output_path),
                ],
                check=True,
            )
        finally:
            wav_path.unlink(missing_ok=True)

    async def list_voices(self) -> list[VoiceInfo]:
        voices = self._load_model().get_voices()
        return [voice_info(voice) for voice in voices]

    def _load_model(self):
        if self._kokoro is not None:
            return self._kokoro

        if not self.model_path.exists() or not self.voices_path.exists():
            raise RuntimeError(
                "Faltan modelos Kokoro en models/kokoro. "
                "Debes tener kokoro-v1.0.onnx y voices-v1.0.bin."
            )

        try:
            from kokoro_onnx import Kokoro
        except ImportError as exc:
            raise RuntimeError(
                "Falta kokoro-onnx. Instala dependencias con: pip install -r requirements.txt"
            ) from exc

        self._kokoro = Kokoro(str(self.model_path), str(self.voices_path))
        return self._kokoro


def voice_info(short_name: str) -> VoiceInfo:
    locale = locale_from_voice(short_name)
    gender_code = short_name[1:2]
    gender = "Female" if gender_code == "f" else "Male" if gender_code == "m" else ""
    return {
        "ShortName": short_name,
        "Locale": locale,
        "Gender": gender,
        "FriendlyName": f"Kokoro {short_name}",
    }


def locale_from_voice(short_name: str) -> str:
    prefix = short_name[:1]
    return {
        "a": "en-US",
        "b": "en-GB",
        "e": "es",
        "f": "fr",
        "h": "hi",
        "i": "it",
        "j": "ja",
        "p": "pt-BR",
        "z": "zh",
    }.get(prefix, "")
