"""Formulário de incursão: masmorra e item em destaque, demais campos recolhíveis."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QDateTimeEdit,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QPlainTextEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from dungeon_drop_analyzer.models import Dungeon, Item, Run

from .formatting import (
    QT_DATETIME_FORMAT,
    TRISTATE_LABELS,
    now_qdatetime,
    to_local_naive,
    to_qdatetime,
)

NO_DURATION = -1
MAX_DURATION = 999_999


class RunForm(QWidget):
    def __init__(self, collapsible: bool = True, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.dungeon_combo = QComboBox()
        self.dungeon_combo.setPlaceholderText("Selecione a masmorra")
        self.item_combo = QComboBox()
        self.item_combo.setEditable(True)
        self.item_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.item_combo.lineEdit().setPlaceholderText("Selecione ou digite o item")
        completer = QCompleter(self.item_combo.model(), self.item_combo)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.item_combo.setCompleter(completer)

        self.completed_at = QDateTimeEdit(now_qdatetime())
        self.completed_at.setDisplayFormat(QT_DATETIME_FORMAT)
        self.completed_at.setCalendarPopup(True)
        self.duration = QSpinBox()
        self.duration.setRange(NO_DURATION, MAX_DURATION)
        self.duration.setValue(NO_DURATION)
        self.duration.setSpecialValueText("Não informada")
        self.duration.setSuffix(" s")
        self.game_version = QLineEdit()
        self.bonus_combo = self._tristate_combo()
        self.event_combo = self._tristate_combo()
        self.notes = QPlainTextEdit()
        self.notes.setFixedHeight(70)

        main = QFormLayout()
        main.addRow("Masmorra *", self.dungeon_combo)
        main.addRow("Item obtido *", self.item_combo)

        self.optional = QWidget()
        optional_layout = QFormLayout(self.optional)
        optional_layout.setContentsMargins(0, 0, 0, 0)
        optional_layout.addRow("Data/hora da conclusão", self.completed_at)
        optional_layout.addRow("Duração", self.duration)
        optional_layout.addRow("Versão do jogo", self.game_version)
        optional_layout.addRow("Bônus de drop", self.bonus_combo)
        optional_layout.addRow("Evento ativo", self.event_combo)
        optional_layout.addRow("Observações", self.notes)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(main)
        self.options_box: QGroupBox | None = None
        if collapsible:
            self.options_box = QGroupBox("Mais opções")
            self.options_box.setCheckable(True)
            self.options_box.setChecked(False)
            box_layout = QVBoxLayout(self.options_box)
            box_layout.addWidget(self.optional)
            self.optional.setVisible(False)
            self.options_box.toggled.connect(self.optional.setVisible)
            layout.addWidget(self.options_box)
        else:
            layout.addWidget(self.optional)

    @staticmethod
    def _tristate_combo() -> QComboBox:
        combo = QComboBox()
        for value, label in TRISTATE_LABELS.items():
            combo.addItem(label, value)
        combo.setCurrentIndex(combo.findData("unknown"))
        return combo

    def set_choices(self, dungeons: Sequence[Dungeon], items: Sequence[Item]) -> None:
        dungeon_id, item_id = self.selected_dungeon_id(), self.selected_item_id()
        self.dungeon_combo.clear()
        for dungeon in dungeons:
            self.dungeon_combo.addItem(
                f"{dungeon.name} (dificuldade {dungeon.difficulty})", dungeon.id
            )
        self.item_combo.clear()
        for item in items:
            self.item_combo.addItem(item.name, item.id)
        self._select(self.dungeon_combo, dungeon_id)
        self._select(self.item_combo, item_id)

    def set_item_search_enabled(self, enabled: bool) -> None:
        self.item_combo.setEnabled(enabled)
        self.item_combo.lineEdit().setPlaceholderText(
            "Digite para buscar o item" if enabled else "Selecione a masmorra primeiro"
        )

    def set_items(self, items: Sequence[Item]) -> None:
        item_id = self.selected_item_id()
        self.item_combo.clear()
        for item in items:
            self.item_combo.addItem(item.name, item.id)
        self._select(self.item_combo, item_id)

    @staticmethod
    def _select(combo: QComboBox, data: int | None) -> None:
        index = combo.findData(data) if data is not None else -1
        combo.setCurrentIndex(index)
        if index < 0 and combo.isEditable():
            combo.setEditText("")

    def selected_dungeon_id(self) -> int | None:
        return self.dungeon_combo.currentData()

    def selected_item_id(self) -> int | None:
        text = self.item_combo.currentText().strip()
        if not text:
            return None
        index = self.item_combo.findText(text, Qt.MatchFlag.MatchFixedString)
        return self.item_combo.itemData(index) if index >= 0 else None

    def completed_at_value(self) -> datetime:
        return self.completed_at.dateTime().toPython()

    def values(self) -> dict[str, Any]:
        duration = self.duration.value()
        return {
            "dungeon_id": self.selected_dungeon_id(),
            "item_id": self.selected_item_id(),
            "completed_at": self.completed_at_value(),
            "duration_seconds": None if duration == NO_DURATION else duration,
            "game_version": self.game_version.text(),
            "bonus_status": self.bonus_combo.currentData(),
            "event_status": self.event_combo.currentData(),
            "notes": self.notes.toPlainText(),
        }

    def load_run(self, run: Run) -> None:
        self._select(self.dungeon_combo, run.dungeon_id)
        self._select(self.item_combo, run.item_id)
        self.completed_at.setDateTime(to_qdatetime(to_local_naive(run.completed_at)))
        self.duration.setValue(
            NO_DURATION if run.duration_seconds is None else run.duration_seconds
        )
        self.game_version.setText(run.game_version or "")
        self.bonus_combo.setCurrentIndex(self.bonus_combo.findData(run.bonus_status))
        self.event_combo.setCurrentIndex(self.event_combo.findData(run.event_status))
        self.notes.setPlainText(run.notes or "")

    def reset_after_save(self) -> None:
        self._select(self.item_combo, None)
        self.completed_at.setDateTime(now_qdatetime())
        self.duration.setValue(NO_DURATION)
        self.notes.clear()
        self.item_combo.setFocus()
