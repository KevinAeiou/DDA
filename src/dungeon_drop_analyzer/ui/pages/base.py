"""Base das páginas e utilitários de tabela."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)


class Page(QWidget):
    message = Signal(str)

    def refresh(self) -> None:
        raise NotImplementedError


def make_table(headers: Sequence[str], stretch_column: int | None = None) -> QTableWidget:
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(list(headers))
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setAlternatingRowColors(True)
    table.verticalHeader().setVisible(False)
    header = table.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    if stretch_column is not None:
        header.setSectionResizeMode(stretch_column, QHeaderView.ResizeMode.Stretch)
    return table


def fill_table(table: QTableWidget, rows: Sequence[tuple[int, Sequence[str]]]) -> None:
    """Preenche a tabela guardando o identificador de cada linha na primeira coluna."""
    table.setRowCount(len(rows))
    for row, (identifier, cells) in enumerate(rows):
        for column, text in enumerate(cells):
            item = QTableWidgetItem(text)
            if column == 0:
                item.setData(Qt.ItemDataRole.UserRole, identifier)
            table.setItem(row, column, item)


def selected_id(table: QTableWidget) -> int | None:
    rows = table.selectionModel().selectedRows()
    if not rows:
        return None
    return table.item(rows[0].row(), 0).data(Qt.ItemDataRole.UserRole)


def fit_table_height(table: QTableWidget, max_rows: int = 12) -> None:
    """Ajusta a altura da tabela ao número de linhas (limitada), para uso em áreas roláveis."""
    rows = min(table.rowCount(), max_rows)
    height = table.horizontalHeader().height() + 2 * table.frameWidth() + 4
    height += sum(table.rowHeight(r) for r in range(rows)) if rows else 24
    table.setFixedHeight(height)
