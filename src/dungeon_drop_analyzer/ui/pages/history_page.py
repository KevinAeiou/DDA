"""Histórico de incursões com filtros, paginação, correção e exclusão."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QDateTime
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateTimeEdit,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from dungeon_drop_analyzer.repositories import RunFilter
from dungeon_drop_analyzer.services import Services
from dungeon_drop_analyzer.ui.dialogs import RunEditDialog
from dungeon_drop_analyzer.ui.widgets.formatting import (
    QT_DATETIME_FORMAT,
    TRISTATE_LABELS,
    format_datetime,
    format_duration,
    format_tristate,
)
from dungeon_drop_analyzer.ui.widgets.messages import confirm, guarded, show_error

from .base import Page, fill_table, make_table, selected_id

PAGE_SIZE = 200
HEADERS = (
    "Data/hora",
    "Masmorra",
    "Dificuldade",
    "Item",
    "Duração",
    "Versão",
    "Bônus",
    "Evento",
    "Observações",
)


class HistoryPage(Page):
    def __init__(self, services: Services, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.services = services
        self.offset = 0
        self.total = 0

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

        filters = QGroupBox("Filtros")
        grid = QGridLayout(filters)
        grid.addWidget(self.use_from, 0, 0)
        grid.addWidget(self.date_from, 0, 1)
        grid.addWidget(self.use_to, 0, 2)
        grid.addWidget(self.date_to, 0, 3)
        grid.addWidget(QLabel("Masmorra"), 1, 0)
        grid.addWidget(self.dungeon_combo, 1, 1)
        grid.addWidget(QLabel("Item"), 1, 2)
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
        apply_button.clicked.connect(self.apply_filters)
        clear_button.clicked.connect(self.clear_filters)
        actions = QHBoxLayout()
        actions.addStretch()
        actions.addWidget(clear_button)
        actions.addWidget(apply_button)
        grid.addLayout(actions, 4, 0, 1, 4)

        self.table = make_table(HEADERS, stretch_column=len(HEADERS) - 1)
        self.table.doubleClicked.connect(lambda _: self.edit_selected())
        self.summary = QLabel()
        self.prev_button = QPushButton("Anterior")
        self.next_button = QPushButton("Próxima")
        self.prev_button.clicked.connect(self.previous_page)
        self.next_button.clicked.connect(self.next_page)
        edit_button = QPushButton("Corrigir")
        delete_button = QPushButton("Excluir")
        edit_button.clicked.connect(self.edit_selected)
        delete_button.clicked.connect(self.delete_selected)

        footer = QHBoxLayout()
        footer.addWidget(edit_button)
        footer.addWidget(delete_button)
        footer.addStretch()
        footer.addWidget(self.summary)
        footer.addWidget(self.prev_button)
        footer.addWidget(self.next_button)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h2>Histórico</h2>"))
        layout.addWidget(filters)
        layout.addWidget(self.table)
        layout.addLayout(footer)

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

    def _reload_choices(self) -> None:
        keep = {
            "dungeon": self.dungeon_combo.currentData(),
            "item": self.item_combo.currentData(),
            "version": self.version_combo.currentData(),
        }
        self.dungeon_combo.clear()
        self.dungeon_combo.addItem("Todas", None)
        for dungeon in self.services.dungeons.list():
            self.dungeon_combo.addItem(dungeon.name, dungeon.id)
        self.item_combo.clear()
        self.item_combo.addItem("Todos", None)
        for item in self.services.items.list():
            self.item_combo.addItem(item.name, item.id)
        self.version_combo.clear()
        self.version_combo.addItem("Todas", None)
        for version in self.services.runs.game_versions():
            self.version_combo.addItem(version, version)
        for combo, key in (
            (self.dungeon_combo, "dungeon"),
            (self.item_combo, "item"),
            (self.version_combo, "version"),
        ):
            index = combo.findData(keep[key])
            combo.setCurrentIndex(max(index, 0))

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
            item_ids=pick(self.item_combo),
            difficulties=None if difficulty is None else [difficulty],
            bonus_status=self.bonus_combo.currentData(),
            event_status=self.event_combo.currentData(),
            game_version=self.version_combo.currentData(),
        )

    def refresh(self) -> None:
        self._reload_choices()
        self._load()

    def _load(self) -> None:
        flt = self.current_filter()
        if flt.date_from and flt.date_to and flt.date_from > flt.date_to:
            show_error(self, "A data inicial deve ser anterior à data final.")
            return
        ok, result = guarded(
            self,
            lambda: (
                self.services.runs.count(flt),
                self.services.runs.list(flt, limit=PAGE_SIZE, offset=self.offset),
            ),
        )
        if not ok:
            return
        self.total, runs = result
        if self.offset >= self.total and self.offset > 0:
            self.offset = max(0, ((self.total - 1) // PAGE_SIZE) * PAGE_SIZE)
            self._load()
            return
        rows = [
            (
                run.id,
                (
                    format_datetime(run.completed_at),
                    run.dungeon.name,
                    str(run.dungeon.difficulty),
                    run.item.name,
                    format_duration(run.duration_seconds),
                    run.game_version or "",
                    format_tristate(run.bonus_status),
                    format_tristate(run.event_status),
                    run.notes or "",
                ),
            )
            for run in runs
        ]
        fill_table(self.table, rows)
        first = self.offset + 1 if rows else 0
        last = self.offset + len(rows)
        self.summary.setText(f"{first}–{last} de {self.total} incursão(ões)")
        self.prev_button.setEnabled(self.offset > 0)
        self.next_button.setEnabled(last < self.total)

    def apply_filters(self) -> None:
        self.offset = 0
        self._load()

    def clear_filters(self) -> None:
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
        self.apply_filters()

    def previous_page(self) -> None:
        self.offset = max(0, self.offset - PAGE_SIZE)
        self._load()

    def next_page(self) -> None:
        self.offset += PAGE_SIZE
        self._load()

    def _selected_run(self):
        run_id = selected_id(self.table)
        if run_id is None:
            show_error(self, "Selecione uma incursão na lista.")
            return None
        ok, run = guarded(self, lambda: self.services.runs.get(run_id))
        return run if ok else None

    def edit_selected(self) -> None:
        run = self._selected_run()
        if run is None:
            return
        dialog = RunEditDialog(self.services, run, self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            self.refresh()
            self.message.emit("Incursão corrigida com sucesso.")

    def delete_selected(self) -> None:
        run = self._selected_run()
        if run is None:
            return
        question = (
            f"Excluir a incursão de {format_datetime(run.completed_at)} "
            f"({run.item.name} em {run.dungeon.name})? A exclusão fica registrada na auditoria."
        )
        if not confirm(self, question, "Excluir"):
            return
        ok, _ = guarded(self, lambda: self.services.runs.delete(run.id))
        if ok:
            self.refresh()
            self.message.emit("Incursão excluída.")
