from pathlib import Path

from .base import SynthesisOptions, TTSEngine


class EdgeTTSEngine(TTSEngine):
    name = "edge"

    async def synthesize_to_file(
        self,
        text: str,
        output_path: Path,
        options: SynthesisOptions,
    ) -> None:
        try:
            import edge_tts
        except ImportError as exc:
            raise RuntimeError(
                "Falta edge-tts. Instala dependencias con: pip install -r requirements.txt"
            ) from exc

        output_path.parent.mkdir(parents=True, exist_ok=True)
        communicate = edge_tts.Communicate(
            text=text,
            voice=options.voice,
            rate=options.rate,
            volume=options.volume,
            pitch=options.pitch,
        )
        await communicate.save(str(output_path))

    async def list_voices(self) -> list[dict]:
        try:
            import edge_tts
        except ImportError as exc:
            raise RuntimeError(
                "Falta edge-tts. Instala dependencias con: pip install -r requirements.txt"
            ) from exc

        return await edge_tts.list_voices()
