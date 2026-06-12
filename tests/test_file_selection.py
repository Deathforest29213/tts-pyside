from __future__ import annotations

import os
import sys

from PySide6.QtCore import QCoreApplication

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_bridge_file_selection_toggles(monkeypatch) -> None:
    app = QCoreApplication.instance() or QCoreApplication(sys.argv)
    assert app is not None

    import src.gui.bridge as bridge_module

    monkeypatch.setattr(bridge_module, "models_installed", lambda: True)
    monkeypatch.setattr(bridge_module, "model_status", lambda: [])
    monkeypatch.setattr(bridge_module, "resolve_ffmpeg", lambda *_args, **_kwargs: "ffmpeg")

    bridge = bridge_module.AppBridge()
    bridge._files = [
        {"included": True, "relativePath": "a.md"},
        {"included": False, "relativePath": "b.md"},
    ]

    assert bridge.selectedFileCount == 1

    bridge.toggleAllFiles()
    assert bridge.selectedFileCount == 2

    bridge.toggleAllFiles()
    assert bridge.selectedFileCount == 0

    bridge.toggleFileForConversion(1)
    assert bridge.selectedFileCount == 1
