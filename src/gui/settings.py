from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"
SETTINGS_PATH = CONFIG_DIR / "gui_settings.json"


DEFAULT_SETTINGS: dict[str, Any] = {
    "input_path": str(PROJECT_ROOT / "input"),
    "output_path": str(PROJECT_ROOT / "output"),
    "voice": "em_santa",
    "speed": 1.0,
    "max_chars": 900,
    "recursive": False,
    "force": False,
    "clean_temp": False,
    "window_width": 1180,
    "window_height": 840,
}


class GuiSettings:
    def __init__(self, path: Path = SETTINGS_PATH) -> None:
        self.path = path
        self.data = DEFAULT_SETTINGS.copy()
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            return

        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return

        if isinstance(loaded, dict):
            self.data.update(loaded)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value
        self.save()

    def update(self, values: dict[str, Any]) -> None:
        self.data.update(values)
        self.save()
