from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication

from .bridge import AppBridge


PROJECT_ROOT = Path(__file__).resolve().parents[2]
QML_DIR = PROJECT_ROOT / "src" / "qml"


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("md2audio")
    app.setOrganizationName("md2audio")

    engine = QQmlApplicationEngine()
    bridge = AppBridge()
    engine.rootContext().setContextProperty("bridge", bridge)
    engine.addImportPath(str(QML_DIR))
    engine.load(str(QML_DIR / "Main.qml"))

    if not engine.rootObjects():
        return 1

    return app.exec()
