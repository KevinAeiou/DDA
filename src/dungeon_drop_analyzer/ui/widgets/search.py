"""Busca tolerante: ignora maiúsculas, acentos e espaços."""

from __future__ import annotations

import unicodedata

from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtWidgets import QComboBox, QCompleter, QWidget

SEARCH_ROLE = Qt.ItemDataRole.UserRole + 100


def normalize_search(text: str) -> str:
    """Minúsculas, sem acentos e sem espaços: 'Reino da Aranha' vira 'reinodaaranha'."""
    decomposed = unicodedata.normalize("NFKD", text)
    letters = (c for c in decomposed if not unicodedata.combining(c) and not c.isspace())
    return "".join(letters).casefold()


def matches_search(query: str, *texts: str) -> bool:
    """Verdadeiro se a busca (normalizada) está contida em algum dos textos (normalizados)."""
    needle = normalize_search(query)
    return not needle or any(needle in normalize_search(text) for text in texts)


class SearchCompleter(QCompleter):
    """Completer que compara a digitação normalizada com a chave normalizada de cada item."""

    def __init__(self, combo: QComboBox, parent: QWidget | None = None) -> None:
        super().__init__(combo.model(), parent or combo)
        self.setFilterMode(Qt.MatchFlag.MatchContains)
        self.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setCompletionRole(SEARCH_ROLE)

    def splitPath(self, path: str) -> list[str]:
        return [normalize_search(path)]

    def pathFromIndex(self, index: QModelIndex) -> str:
        return str(index.data(Qt.ItemDataRole.DisplayRole) or "")


def add_searchable_item(combo: QComboBox, text: str, data: object) -> None:
    combo.addItem(text, data)
    combo.setItemData(combo.count() - 1, normalize_search(text), SEARCH_ROLE)
