"""Páginas de cadastro de masmorras e itens."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from dungeon_drop_analyzer.services import Services
from dungeon_drop_analyzer.ui.dialogs import DungeonDialog, ItemDialog
from dungeon_drop_analyzer.ui.widgets.formatting import format_bool
from dungeon_drop_analyzer.ui.widgets.messages import guarded, show_error

from .base import Page, fill_table, make_table, selected_id


class _CatalogPage(Page):
    title: str
    headers: tuple[str, ...]
    singular: str
    new_label: str

    def __init__(self, services: Services, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.services = services
        self.heading = QLabel(f"<h2>{self.title}</h2>")
        self.table = make_table(self.headers, stretch_column=len(self.headers) - 2)
        self.table.doubleClicked.connect(lambda _: self.edit_selected())
        self.new_button = QPushButton(self.new_label)
        self.edit_button = QPushButton("Editar")
        self.toggle_button = QPushButton("Ativar/Inativar")
        self.new_button.clicked.connect(self.create_new)
        self.edit_button.clicked.connect(self.edit_selected)
        self.toggle_button.clicked.connect(self.toggle_selected)
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Filtrar por nome")
        self.filter_edit.setClearButtonEnabled(True)
        self.filter_edit.textChanged.connect(lambda _: self.refresh())
        self.summary = QLabel()

        buttons = QHBoxLayout()
        for button in (self.new_button, self.edit_button, self.toggle_button):
            buttons.addWidget(button)
        buttons.addStretch()
        buttons.addWidget(self.filter_edit)
        layout = QVBoxLayout(self)
        layout.addWidget(self.heading)
        layout.addLayout(buttons)
        layout.addWidget(self.table)
        layout.addWidget(self.summary)

    def _entities(self) -> list:
        raise NotImplementedError

    def _row(self, entity) -> tuple[str, ...]:
        raise NotImplementedError

    def _dialog(self, entity=None):
        raise NotImplementedError

    def _service(self):
        raise NotImplementedError

    def refresh(self) -> None:
        text = self.filter_edit.text().strip().casefold()
        entities = [e for e in self._entities() if text in e.name.casefold()]
        fill_table(self.table, [(e.id, self._row(e)) for e in entities])
        total = len(self._entities())
        self.summary.setText(f"{len(entities)} de {total} registro(s) exibido(s).")

    def _open_dialog(self, entity=None) -> bool:
        dialog = self._dialog(entity)
        return dialog.exec() == dialog.DialogCode.Accepted

    def create_new(self) -> None:
        if self._open_dialog():
            self.refresh()
            self.message.emit(f"{self.singular} cadastrado(a) com sucesso.")

    def _selected_entity(self):
        entity_id = selected_id(self.table)
        if entity_id is None:
            show_error(self, f"Selecione {self.singular.lower()} na lista.")
            return None
        ok, entity = guarded(self, lambda: self._service().get(entity_id))
        return entity if ok else None

    def edit_selected(self) -> None:
        entity = self._selected_entity()
        if entity is not None and self._open_dialog(entity):
            self.refresh()
            self.message.emit(f"{self.singular} atualizado(a) com sucesso.")

    def toggle_selected(self) -> None:
        entity = self._selected_entity()
        if entity is None:
            return
        ok, _ = guarded(self, lambda: self._service().set_active(entity.id, not entity.is_active))
        if ok:
            self.refresh()
            state = "inativado(a)" if entity.is_active else "ativado(a)"
            self.message.emit(f"{self.singular} {state}.")


class DungeonsPage(_CatalogPage):
    title = "Masmorras"
    headers = ("Nome", "Dificuldade", "Descrição", "Ativa")
    singular = "Masmorra"
    new_label = "Nova masmorra"

    def _entities(self) -> list:
        return self.services.dungeons.list()

    def _row(self, d) -> tuple[str, ...]:
        return (d.name, str(d.difficulty), d.description or "", format_bool(d.is_active))

    def _dialog(self, entity=None):
        return DungeonDialog(self.services.dungeons, entity, self)

    def _service(self):
        return self.services.dungeons


class ItemsPage(_CatalogPage):
    title = "Itens"
    headers = ("Nome", "Categoria", "Descrição", "Ativo")
    singular = "Item"
    new_label = "Novo item"

    def _entities(self) -> list:
        return self.services.items.list()

    def _row(self, i) -> tuple[str, ...]:
        return (i.name, i.category or "", i.description or "", format_bool(i.is_active))

    def _dialog(self, entity=None):
        return ItemDialog(self.services.items, entity, self)

    def _service(self):
        return self.services.items
