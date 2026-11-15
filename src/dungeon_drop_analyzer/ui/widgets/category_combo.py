"""Seleção das categorias padrão de itens."""

from __future__ import annotations

from PySide6.QtWidgets import QComboBox

from dungeon_drop_analyzer.models import ItemCategory


def make_category_combo(empty_label: str | None = None) -> QComboBox:
    """Sem rótulo vazio, a lista começa sem seleção (categoria obrigatória)."""
    combo = QComboBox()
    if empty_label is not None:
        combo.addItem(empty_label, None)
    for category in ItemCategory:
        combo.addItem(category.label, category.value)
    if empty_label is None:
        combo.setPlaceholderText("Selecione a categoria")
        combo.setCurrentIndex(-1)
    return combo


def select_category(combo: QComboBox, value: str | None) -> None:
    combo.setCurrentIndex(combo.findData(value))
