from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"
SETTINGS_PATH = CONFIG_DIR / "gui_settings.json"
PROFILES_PATH = CONFIG_DIR / "profiles.json"


PRESETS: dict[str, dict[str, Any]] = {
    "Apuntes tecnicos": {
        "voice": "em_santa",
        "speed": 1.0,
        "max_chars": 900,
        "recursive": False,
        "force": False,
        "normalize_loudness": False,
    },
    "Libro narrativo": {
        "voice": "em_santa",
        "speed": 0.95,
        "max_chars": 1200,
        "recursive": True,
        "force": False,
        "normalize_loudness": True,
    },
    "Rapido": {
        "voice": "em_santa",
        "speed": 1.12,
        "max_chars": 850,
        "recursive": False,
        "force": False,
        "normalize_loudness": False,
    },
    "Calidad alta": {
        "voice": "em_santa",
        "speed": 0.92,
        "max_chars": 700,
        "recursive": True,
        "force": False,
        "normalize_loudness": True,
    },
}


DEFAULT_SETTINGS: dict[str, Any] = {
    "input_path": str(PROJECT_ROOT / "input"),
    "output_path": str(PROJECT_ROOT / "output"),
    "voice": "em_santa",
    "speed": 1.0,
    "max_chars": 900,
    "recursive": False,
    "force": False,
    "clean_temp": False,
    "normalize_loudness": False,
    "selected_preset": "Apuntes tecnicos",
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


class ProfileStore:
    def __init__(self, path: Path = PROFILES_PATH) -> None:
        self.path = path

    def names(self) -> list[str]:
        return sorted(self._load().keys())

    def save_profile(self, name: str, values: dict[str, Any]) -> None:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("El perfil necesita un nombre.")

        profiles = self._load()
        profiles[clean_name] = values
        self._save(profiles)

    def load_profile(self, name: str) -> dict[str, Any]:
        profiles = self._load()
        profile = profiles.get(name)
        if not isinstance(profile, dict):
            raise ValueError(f"No existe el perfil: {name}")
        return profile

    def _load(self) -> dict[str, dict[str, Any]]:
        if not self.path.exists():
            return {}

        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

        if not isinstance(data, dict):
            return {}

        profiles: dict[str, dict[str, Any]] = {}
        for name, values in data.items():
            if isinstance(name, str) and isinstance(values, dict):
                profiles[name] = values
        return profiles

    def _save(self, profiles: dict[str, dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(profiles, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
