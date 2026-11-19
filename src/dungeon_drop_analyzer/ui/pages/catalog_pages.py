"""Páginas de cadastro de masmorras e itens."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from dungeon_drop_analyzer.services import Services
from dungeon_drop_analyzer.ui.dialogs import DungeonDialog, ItemDialog
from dungeon_drop_analyzer.ui.widgets.category_combo import make_category_combo
from dungeon_drop_analyzer.ui.widgets.formatting import (
    format_bool,
    format_category,
    format_item_dungeons,
)
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
        for widget in self._extra_filters():
            buttons.addWidget(widget)
        buttons.addWidget(self.filter_edit)
        layout = QVBoxLayout(self)
        layout.addWidget(self.heading)
        layout.addLayout(buttons)
        layout.addWidget(self.table)
        layout.addWidget(self.summary)

    def _extra_filters(self) -> list[QWidget]:
        return []

    def _extra_match(self, entity) -> bool:
        return True

    def _warning(self) -> str:
        return ""

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
        entities = [
            e for e in self._entities() if text in e.name.casefold() and self._extra_match(e)
        ]
        fill_table(self.table, [(e.id, self._row(e)) for e in entities])
        total = len(self._entities())
        self.summary.setText(f"{len(entities)} de {total} registro(s) exibido(s).{self._warning()}")

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
    headers = ("Nome", "Categoria", "Masmorras", "Descrição", "Ativo")
    singular = "Item"
    new_label = "Novo item"

    def _extra_filters(self) -> list[QWidget]:
        self.category_filter = make_category_combo(empty_label="Todas as categorias")
        self.category_filter.currentIndexChanged.connect(lambda _: self.refresh())
        self.dungeon_filter = QComboBox()
        self.dungeon_filter.addItem("Todas as masmorras", None)
        self.dungeon_filter.currentIndexChanged.connect(lambda _: self.refresh())
        return [self.category_filter, self.dungeon_filter]

    def _reload_dungeon_filter(self) -> None:
        current = self.dungeon_filter.currentData()
        self.dungeon_filter.blockSignals(True)
        self.dungeon_filter.clear()
        self.dungeon_filter.addItem("Todas as masmorras", None)
        for dungeon in self.services.dungeons.list():
            self.dungeon_filter.addItem(dungeon.name, dungeon.id)
        self.dungeon_filter.setCurrentIndex(max(self.dungeon_filter.findData(current), 0))
        self.dungeon_filter.blockSignals(False)

    def refresh(self) -> None:
        self._reload_dungeon_filter()
        super().refresh()

    def _extra_match(self, entity) -> bool:
        selected = self.category_filter.currentData()
        if selected is not None and entity.category != selected:
            return False
        dungeon_id = self.dungeon_filter.currentData()
        return dungeon_id is None or dungeon_id in {d.id for d in entity.dungeons}

    def _entities(self) -> list:
        return self.services.items.list()

    def _warning(self) -> str:
        undefined = sum(1 for i in self._entities() if not i.dungeons)
        if not undefined:
            return ""
        return (
            f" ⚠ {undefined} item(ns) sem masmorras definidas: edite o cadastro para informar "
            "onde cada um pode ser obtido."
        )

    def _row(self, i) -> tuple[str, ...]:
        return (
            i.name,
            format_category(i.category),
            format_item_dungeons(i, len(self.services.dungeons.list())),
            i.description or "",
            format_bool(i.is_active),
        )

    def _dialog(self, entity=None):
        return ItemDialog(
            self.services.items, self.services.dungeons.list(active_only=True), entity, self
        )

    def _service(self):
        return self.services.items
