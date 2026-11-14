"""Páginas ainda não implementadas e página de configurações com os caminhos de dados."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from dungeon_drop_analyzer.core.config import Settings

from .base import Page


class PlaceholderPage(Page):
    def __init__(self, title: str, detail: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"<h2>{title}</h2>"))
        label = QLabel(detail)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(label)
        layout.addStretch()

    def refresh(self) -> None:
        return None


class SettingsPage(PlaceholderPage):
    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        detail = (
            f"<b>Diretório de dados:</b> {settings.data_dir}<br>"
            f"<b>Banco de dados:</b> {settings.db_path}<br>"
            f"<b>Logs:</b> {settings.log_dir}<br><br>"
            "Backup, restauração e escolha do diretório de dados serão disponibilizados na Fase 5."
        )
        super().__init__("Configurações e backup", detail, parent)
        self.details = detail
