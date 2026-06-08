from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeAlias

VoiceInfo: TypeAlias = dict[str, Any]


@dataclass(frozen=True)
class SynthesisOptions:
    voice: str
    rate: str = "+0%"
    volume: str = "+0%"
    pitch: str = "+0Hz"
    speed: float = 1.0
    language: str = "es"
    ffmpeg_path: str | None = None


class TTSEngine(ABC):
    name: str

    @abstractmethod
    async def synthesize_to_file(
        self,
        text: str,
        output_path: Path,
        options: SynthesisOptions,
    ) -> None:
        raise NotImplementedError

    async def list_voices(self) -> list[VoiceInfo]:
        return []
