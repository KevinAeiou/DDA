"""Janela principal: menu lateral e páginas empilhadas."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QListWidget, QMainWindow, QStackedWidget, QWidget

from dungeon_drop_analyzer.core.config import Settings
from dungeon_drop_analyzer.services import Services
from dungeon_drop_analyzer.ui.pages import (
    DungeonsPage,
    HistoryPage,
    ItemsPage,
    Page,
    PlaceholderPage,
    RegisterRunPage,
    SettingsPage,
)
from dungeon_drop_analyzer.ui.widgets.messages import APP_TITLE

STATUS_TIMEOUT_MS = 6000


class MainWindow(QMainWindow):
    def __init__(self, services: Services, settings: Settings) -> None:
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1100, 700)

        self.pages: dict[str, Page] = {
            "Dashboard": PlaceholderPage(
                "Dashboard", "Totais, distribuição de itens e evolução temporal chegam na Fase 4."
            ),
            "Registrar incursão": RegisterRunPage(services),
            "Histórico": HistoryPage(services),
            "Masmorras": DungeonsPage(services),
            "Itens": ItemsPage(services),
            "Análise estatística": PlaceholderPage(
                "Análise estatística", "Comparações entre masmorras chegam na Fase 4."
            ),
            "Relatórios": PlaceholderPage(
                "Relatórios", "Exportação em CSV e XLSX chega na Fase 5."
            ),
            "Configurações e backup": SettingsPage(settings),
        }
        self.nav = QListWidget()
        self.nav.setFixedWidth(200)
        self.stack = QStackedWidget()
        for name, page in self.pages.items():
            self.nav.addItem(name)
            self.stack.addWidget(page)
            page.message.connect(self.show_message)
        self.nav.currentRowChanged.connect(self._on_page_changed)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.addWidget(self.nav)
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(central)
        self.statusBar()

        self.open_page("Registrar incursão")

    def open_page(self, name: str) -> None:
        row = list(self.pages).index(name)
        if self.nav.currentRow() == row:
            self._on_page_changed(row)
        else:
            self.nav.setCurrentRow(row)

    def _on_page_changed(self, row: int) -> None:
        if row < 0:
            return
        self.stack.setCurrentIndex(row)
        self.stack.currentWidget().refresh()

    def show_message(self, text: str) -> None:
        self.statusBar().showMessage(text, STATUS_TIMEOUT_MS)
