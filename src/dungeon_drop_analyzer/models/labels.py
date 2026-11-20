"""Nomes de exibição de itens: a categoria é acrescentada quando o nome se repete."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from .entities import CATEGORY_LABELS, Item, ItemCategory


def assign_display_names(items: Iterable[Item]) -> None:
    """Define `display_name`; só nomes repetidos recebem a categoria entre parênteses."""
    items = list(items)
    counts = Counter(item.name.casefold() for item in items)
    for item in items:
        if counts[item.name.casefold()] > 1:
            label = CATEGORY_LABELS[ItemCategory(item.category)]
            item._display_name = f"{item.name} ({label})"
        else:
            item._display_name = item.name
