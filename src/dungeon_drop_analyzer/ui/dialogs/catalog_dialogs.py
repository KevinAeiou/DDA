"""Diálogos de cadastro e edição de masmorras e itens."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QLineEdit,
    QPlainTextEdit,
    QSpinBox,
    QWidget,
)

from dungeon_drop_analyzer.models import Dungeon, Item
from dungeon_drop_analyzer.services import DungeonService, ItemService
from dungeon_drop_analyzer.ui.widgets.category_combo import make_category_combo, select_category

from .form_dialog import FormDialog


class DungeonDialog(FormDialog):
    def __init__(
        self, service: DungeonService, dungeon: Dungeon | None = None, parent: QWidget | None = None
    ) -> None:
        self._service = service
        self._dungeon = dungeon
        content = QWidget()
        form = QFormLayout(content)
        self.name = QLineEdit()
        self.difficulty = QSpinBox()
        self.difficulty.setRange(1, 5)
        self.description = QPlainTextEdit()
        self.description.setFixedHeight(80)
        self.active = QCheckBox("Ativa")
        self.active.setChecked(True)
        form.addRow("Nome *", self.name)
        form.addRow("Dificuldade (1 a 5) *", self.difficulty)
        form.addRow("Descrição", self.description)
        form.addRow("", self.active)
        if dungeon is not None:
            self.name.setText(dungeon.name)
            self.difficulty.setValue(dungeon.difficulty)
            self.description.setPlainText(dungeon.description or "")
            self.active.setChecked(dungeon.is_active)
        title = "Nova masmorra" if dungeon is None else "Editar masmorra"
        super().__init__(title, content, self._submit, parent)

    def _submit(self) -> None:
        values = {
            "name": self.name.text(),
            "difficulty": self.difficulty.value(),
            "description": self.description.toPlainText(),
            "is_active": self.active.isChecked(),
        }
        if self._dungeon is None:
            self._service.create(**values)
        else:
            self._service.update(self._dungeon.id, **values)


class ItemDialog(FormDialog):
    def __init__(
        self, service: ItemService, item: Item | None = None, parent: QWidget | None = None
    ) -> None:
        self._service = service
        self._item = item
        content = QWidget()
        form = QFormLayout(content)
        self.name = QLineEdit()
        self.category = make_category_combo("Sem categoria")
        self.description = QPlainTextEdit()
        self.description.setFixedHeight(80)
        self.active = QCheckBox("Ativo")
        self.active.setChecked(True)
        form.addRow("Nome *", self.name)
        form.addRow("Categoria", self.category)
        form.addRow("Descrição", self.description)
        form.addRow("", self.active)
        if item is not None:
            self.name.setText(item.name)
            select_category(self.category, item.category)
            self.description.setPlainText(item.description or "")
            self.active.setChecked(item.is_active)
        title = "Novo item" if item is None else "Editar item"
        super().__init__(title, content, self._submit, parent)

    def _submit(self) -> None:
        values = {
            "name": self.name.text(),
            "category": self.category.currentData(),
            "description": self.description.toPlainText(),
            "is_active": self.active.isChecked(),
        }
        if self._item is None:
            self._service.create(**values)
        else:
            self._service.update(self._item.id, **values)
