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
        self._items: list = []
        self._missing: list[str] = []
        self._loading = False
        self.form = RunForm(collapsible=True)
        self.form.dungeon_combo.currentIndexChanged.connect(lambda _: self._on_dungeon_changed())
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
        self._items = self.services.items.list(active_only=True)
        self._loading = True
        self.form.set_choices(dungeons, self._items)
        self._loading = False
        self._update_item_choices()
        missing = []
        if not dungeons:
            missing.append("masmorras")
        if not self._items:
            missing.append("itens")
        self._missing = missing
        self.save_button.setEnabled(not missing)
        self._update_hint()

    def _items_for(self, dungeon_id: int | None) -> list:
        """Somente os itens cadastrados para a masmorra; sem masmorra escolhida, nenhum."""
        if dungeon_id is None:
            return []
        return [item for item in self._items if dungeon_id in {d.id for d in item.dungeons}]

    def _update_item_choices(self) -> None:
        dungeon_id = self.form.selected_dungeon_id()
        self.form.set_items(self._items_for(dungeon_id))
        self.form.set_item_search_enabled(dungeon_id is not None)

    def _on_dungeon_changed(self) -> None:
        if self._loading:
            return
        self._update_item_choices()
        self._update_hint()

    def _update_hint(self) -> None:
        if self._missing:
            text = f"Cadastre {' e '.join(self._missing)} ativos antes de registrar incursões."
        elif self.form.selected_dungeon_id() is None:
            text = (
                "Selecione a masmorra para habilitar a busca de itens. Cada incursão rende um "
                "único item."
            )
        elif self.form.item_combo.count() == 0:
            text = (
                "Nenhum item ativo está cadastrado para esta masmorra. Edite o cadastro do item "
                "para informar onde ele pode ser obtido."
            )
            if any(not item.dungeons for item in self._items):
                text += " Itens sem masmorras definidas não são listados."
        else:
            text = (
                "Selecione o item recebido (a lista mostra os itens que podem ser obtidos na "
                "masmorra escolhida). Cada incursão rende um único item."
            )
        self.hint.setText(text)
        self.hint.setVisible(True)

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
