"""Histórico de incursões com filtros, paginação, correção e exclusão."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from dungeon_drop_analyzer.services import Services
from dungeon_drop_analyzer.ui.dialogs import RunEditDialog
from dungeon_drop_analyzer.ui.widgets.formatting import (
    format_datetime,
    format_duration,
    format_tristate,
)
from dungeon_drop_analyzer.ui.widgets.messages import confirm, guarded, show_error
from dungeon_drop_analyzer.ui.widgets.run_filter_panel import FilterPanel

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

        self.filters = FilterPanel(show_item=True)
        self.filters.applied.connect(self.apply_filters)

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
        layout.addWidget(self.filters)
        layout.addWidget(self.table)
        layout.addLayout(footer)

    def refresh(self) -> None:
        self.filters.reload_choices(self.services)
        self._load()

    def _load(self) -> None:
        error = self.filters.validation_error()
        if error:
            show_error(self, error)
            return
        flt = self.filters.current_filter()
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
                    run.item.display_name,
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
        self.filters.clear()

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
            f"({run.item.display_name} em {run.dungeon.name})? "
            "A exclusão fica registrada na auditoria."
        )
        if not confirm(self, question, "Excluir"):
            return
        ok, _ = guarded(self, lambda: self.services.runs.delete(run.id))
        if ok:
            self.refresh()
            self.message.emit("Incursão excluída.")
