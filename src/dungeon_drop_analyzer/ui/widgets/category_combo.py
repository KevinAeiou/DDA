"""Seleção das categorias padrão de itens."""

from __future__ import annotations

from PySide6.QtWidgets import QComboBox

from dungeon_drop_analyzer.models import ItemCategory


def make_category_combo(empty_label: str) -> QComboBox:
    combo = QComboBox()
    combo.addItem(empty_label, None)
    for category in ItemCategory:
        combo.addItem(category.label, category.value)
    return combo


def select_category(combo: QComboBox, value: str | None) -> None:
    combo.setCurrentIndex(max(combo.findData(value), 0))
