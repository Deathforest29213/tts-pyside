from __future__ import annotations

import hashlib

import src.gui.model_manager as model_manager
from src.gui.model_manager import KokoroModelFile, validate_model_file


def test_validate_model_file_statuses(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(model_manager, "MODEL_DIR", tmp_path)
    model = KokoroModelFile(
        name="model.bin",
        url="https://example.com/model.bin",
        expected_size=3,
        sha256=hashlib.sha256(b"abc").hexdigest(),
    )

    missing = validate_model_file(model)
    assert missing["status"] == "Falta"

    model.path.write_bytes(b"ab")
    incomplete = validate_model_file(model)
    assert incomplete["status"] == "Incompleto"

    model.path.write_bytes(b"xyz")
    corrupt = validate_model_file(model)
    assert corrupt["status"] == "Corrupto"

    model.path.write_bytes(b"abc")
    valid = validate_model_file(model)
    assert valid["status"] == "Instalado"
    assert valid["valid"] is True
