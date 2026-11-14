"""Registro de incursão: poucos cliques (masmorra, item, salvar)."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from dungeon_drop_analyzer.services import Services
from dungeon_drop_analyzer.ui.widgets.messages import guarded, show_error
from dungeon_drop_analyzer.ui.widgets.run_form import RunForm

from .base import Page


class RegisterRunPage(Page):
    def __init__(self, services: Services, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.services = services
        self.form = RunForm(collapsible=True)
        self.hint = QLabel()
        self.hint.setWordWrap(True)
        self.save_button = QPushButton("Salvar incursão")
        self.save_button.setDefault(True)
        self.save_button.clicked.connect(self.save)

        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(self.save_button)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h2>Registrar incursão</h2>"))
        layout.addWidget(self.hint)
        layout.addWidget(self.form)
        layout.addLayout(buttons)
        layout.addStretch()

    def refresh(self) -> None:
        dungeons = self.services.dungeons.list(active_only=True)
        items = self.services.items.list(active_only=True)
        self.form.set_choices(dungeons, items)
        missing = []
        if not dungeons:
            missing.append("masmorras")
        if not items:
            missing.append("itens")
        if missing:
            self.hint.setText(
                f"Cadastre {' e '.join(missing)} ativos antes de registrar incursões."
            )
        else:
            self.hint.setText(
                "Selecione a masmorra e o item recebido. Cada incursão rende um único item."
            )
        self.hint.setVisible(True)
        self.save_button.setEnabled(not missing)

    def save(self) -> None:
        values = self.form.values()
        if values["dungeon_id"] is None:
            show_error(self, "Selecione a masmorra.")
            return
        if values["item_id"] is None:
            show_error(self, "Selecione um item da lista.")
            return
        ok, run = guarded(self, lambda: self.services.runs.register(**values))
        if ok:
            self.form.reset_after_save()
            self.message.emit(f"Incursão registrada: {run.item.name} em {run.dungeon.name}.")
