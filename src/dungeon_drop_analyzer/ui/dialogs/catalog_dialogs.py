"""Diálogos de cadastro e edição de masmorras e itens."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
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
    """Cadastro/edição de item.

    A lista de masmorras recebida é a exibida (o chamador passa só as ativas). Vínculos já
    existentes com masmorras que não estão na lista são preservados ao salvar.
    """

    def __init__(
        self,
        service: ItemService,
        dungeons: Sequence[Dungeon],
        item: Item | None = None,
        parent: QWidget | None = None,
    ) -> None:
        self._service = service
        self._item = item
        self._listed_ids = {d.id for d in dungeons}
        content = QWidget()
        form = QFormLayout(content)
        self.name = QLineEdit()
        self.category = make_category_combo()
        self.dungeon_list = QListWidget()
        self.dungeon_list.setMaximumHeight(130)
        for dungeon in dungeons:
            entry = QListWidgetItem(f"{dungeon.name} (dificuldade {dungeon.difficulty})")
            entry.setFlags(entry.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            entry.setCheckState(Qt.CheckState.Unchecked)
            entry.setData(Qt.ItemDataRole.UserRole, dungeon.id)
            self.dungeon_list.addItem(entry)
        select_all = QPushButton("Todas")
        clear_all = QPushButton("Nenhuma")
        select_all.clicked.connect(lambda: self._set_all(Qt.CheckState.Checked))
        clear_all.clicked.connect(lambda: self._set_all(Qt.CheckState.Unchecked))
        dungeon_buttons = QHBoxLayout()
        dungeon_buttons.addWidget(select_all)
        dungeon_buttons.addWidget(clear_all)
        dungeon_buttons.addStretch()
        dungeon_box = QWidget()
        dungeon_layout = QVBoxLayout(dungeon_box)
        dungeon_layout.setContentsMargins(0, 0, 0, 0)
        dungeon_layout.addWidget(self.dungeon_list)
        dungeon_layout.addLayout(dungeon_buttons)
        self.description = QPlainTextEdit()
        self.description.setFixedHeight(80)
        self.active = QCheckBox("Ativo")
        self.active.setChecked(True)
        form.addRow("Nome *", self.name)
        form.addRow("Categoria *", self.category)
        form.addRow("Masmorra(s) *", dungeon_box)
        form.addRow("Descrição", self.description)
        form.addRow("", self.active)
        if item is not None:
            self.name.setText(item.name)
            select_category(self.category, item.category)
            self.set_checked_dungeons({d.id for d in item.dungeons})
            self.description.setPlainText(item.description or "")
            self.active.setChecked(item.is_active)
        title = "Novo item" if item is None else "Editar item"
        super().__init__(title, content, self._submit, parent)

    def _set_all(self, state: Qt.CheckState) -> None:
        for row in range(self.dungeon_list.count()):
            self.dungeon_list.item(row).setCheckState(state)

    def set_checked_dungeons(self, ids: set[int]) -> None:
        for row in range(self.dungeon_list.count()):
            entry = self.dungeon_list.item(row)
            checked = entry.data(Qt.ItemDataRole.UserRole) in ids
            entry.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)

    def checked_dungeon_ids(self) -> list[int]:
        return [
            self.dungeon_list.item(row).data(Qt.ItemDataRole.UserRole)
            for row in range(self.dungeon_list.count())
            if self.dungeon_list.item(row).checkState() == Qt.CheckState.Checked
        ]

    def _submit(self) -> None:
        values = {
            "name": self.name.text(),
            "category": self.category.currentData(),
            "description": self.description.toPlainText(),
            "is_active": self.active.isChecked(),
        }
        dungeon_ids = self.checked_dungeon_ids()
        if self._item is not None:
            hidden = sorted({d.id for d in self._item.dungeons} - self._listed_ids)
            dungeon_ids += hidden
        if self._item is None:
            self._service.create(dungeon_ids=dungeon_ids, **values)
        else:
            self._service.update(self._item.id, dungeon_ids=dungeon_ids, **values)
