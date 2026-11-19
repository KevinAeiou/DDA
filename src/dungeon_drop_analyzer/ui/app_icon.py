"""Ícone do aplicativo, carregado dos PNGs distribuídos com o pacote."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon

RESOURCES_DIR = Path(__file__).resolve().parents[1] / "resources"
ICON_SIZES = (16, 32, 256)
APP_USER_MODEL_ID = "DungeonDropAnalyzer.App"


def load_app_icon() -> QIcon:
    icon = QIcon()
    for size in ICON_SIZES:
        path = RESOURCES_DIR / f"icon-{size}.png"
        if path.is_file():
            icon.addFile(str(path))
    return icon


def set_windows_app_id() -> None:
    """Agrupa a janela sob o ícone do aplicativo na barra de tarefas do Windows."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        return
