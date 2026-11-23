"""Painel de filtros de incursões compartilhado por histórico, dashboard e análise."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QDateTime, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateTimeEdit,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from dungeon_drop_analyzer.repositories import RunFilter
from dungeon_drop_analyzer.services import Services

from .formatting import QT_DATETIME_FORMAT, TRISTATE_LABELS


class FilterPanel(QGroupBox):
    applied = Signal()

    def __init__(
        self,
        show_item: bool = True,
        active_dungeons_only: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("Filtros", parent)
        self._active_dungeons_only = active_dungeons_only
        self.use_from = QCheckBox("De")
        self.date_from = self._date_edit(self.use_from)
        self.use_to = QCheckBox("Até")
        self.date_to = self._date_edit(self.use_to)
        self.dungeon_combo = QComboBox()
        self.item_combo = QComboBox()
        self.difficulty_combo = QComboBox()
        self.difficulty_combo.addItem("Todas", None)
        for level in range(1, 6):
            self.difficulty_combo.addItem(str(level), level)
        self.bonus_combo = self._tristate_filter()
        self.event_combo = self._tristate_filter()
        self.version_combo = QComboBox()
        self._show_item = show_item

        item_label = QLabel("Item")
        grid = QGridLayout(self)
        grid.addWidget(self.use_from, 0, 0)
        grid.addWidget(self.date_from, 0, 1)
        grid.addWidget(self.use_to, 0, 2)
        grid.addWidget(self.date_to, 0, 3)
        grid.addWidget(QLabel("Masmorra"), 1, 0)
        grid.addWidget(self.dungeon_combo, 1, 1)
        grid.addWidget(item_label, 1, 2)
        grid.addWidget(self.item_combo, 1, 3)
        grid.addWidget(QLabel("Dificuldade"), 2, 0)
        grid.addWidget(self.difficulty_combo, 2, 1)
        grid.addWidget(QLabel("Versão do jogo"), 2, 2)
        grid.addWidget(self.version_combo, 2, 3)
        grid.addWidget(QLabel("Bônus de drop"), 3, 0)
        grid.addWidget(self.bonus_combo, 3, 1)
        grid.addWidget(QLabel("Evento ativo"), 3, 2)
        grid.addWidget(self.event_combo, 3, 3)
        apply_button = QPushButton("Aplicar filtros")
        clear_button = QPushButton("Limpar")
        apply_button.clicked.connect(self.apply)
        clear_button.clicked.connect(self.clear)
        actions = QHBoxLayout()
        actions.addStretch()
        actions.addWidget(clear_button)
        actions.addWidget(apply_button)
        grid.addLayout(actions, 4, 0, 1, 4)
        if not show_item:
            item_label.hide()
            self.item_combo.hide()

    @staticmethod
    def _date_edit(check: QCheckBox) -> QDateTimeEdit:
        edit = QDateTimeEdit(QDateTime.currentDateTime())
        edit.setDisplayFormat(QT_DATETIME_FORMAT)
        edit.setCalendarPopup(True)
        edit.setEnabled(False)
        check.toggled.connect(edit.setEnabled)
        return edit

    @staticmethod
    def _tristate_filter() -> QComboBox:
        combo = QComboBox()
        combo.addItem("Todos", None)
        for value, label in TRISTATE_LABELS.items():
            combo.addItem(label, value)
        return combo

    def reload_choices(self, services: Services) -> None:
        keep = {
            "dungeon": self.dungeon_combo.currentData(),
            "item": self.item_combo.currentData(),
            "version": self.version_combo.currentData(),
        }
        self.dungeon_combo.clear()
        self.dungeon_combo.addItem("Todas", None)
        for dungeon in services.dungeons.list(active_only=self._active_dungeons_only):
            self.dungeon_combo.addItem(dungeon.name, dungeon.id)
        self.item_combo.clear()
        self.item_combo.addItem("Todos", None)
        for item in services.items.list():
            self.item_combo.addItem(item.display_name, item.id)
        self.version_combo.clear()
        self.version_combo.addItem("Todas", None)
        for version in services.runs.game_versions():
            self.version_combo.addItem(version, version)
        for combo, key in (
            (self.dungeon_combo, "dungeon"),
            (self.item_combo, "item"),
            (self.version_combo, "version"),
        ):
            combo.setCurrentIndex(max(combo.findData(keep[key]), 0))

    def current_filter(self) -> RunFilter:
        def pick(combo: QComboBox) -> list[int] | None:
            value = combo.currentData()
            return None if value is None else [value]

        def when(check: QCheckBox, edit: QDateTimeEdit) -> datetime | None:
            return edit.dateTime().toPython() if check.isChecked() else None

        difficulty = self.difficulty_combo.currentData()
        return RunFilter(
            date_from=when(self.use_from, self.date_from),
            date_to=when(self.use_to, self.date_to),
            dungeon_ids=pick(self.dungeon_combo),
            item_ids=pick(self.item_combo) if self._show_item else None,
            difficulties=None if difficulty is None else [difficulty],
            bonus_status=self.bonus_combo.currentData(),
            event_status=self.event_combo.currentData(),
            game_version=self.version_combo.currentData(),
        )

    def validation_error(self) -> str | None:
        flt = self.current_filter()
        if flt.date_from and flt.date_to and flt.date_from > flt.date_to:
            return "A data inicial deve ser anterior à data final."
        return None

    def apply(self) -> None:
        self.applied.emit()

    def clear(self) -> None:
        self.use_from.setChecked(False)
        self.use_to.setChecked(False)
        for combo in (
            self.dungeon_combo,
            self.item_combo,
            self.difficulty_combo,
            self.bonus_combo,
            self.event_combo,
            self.version_combo,
        ):
            combo.setCurrentIndex(0)
        self.applied.emit()
