"""Páginas da interface."""

from .base import Page
from .catalog_pages import DungeonsPage, ItemsPage
from .history_page import HistoryPage
from .placeholder_page import PlaceholderPage, SettingsPage
from .register_page import RegisterRunPage

__all__ = [
    "DungeonsPage",
    "HistoryPage",
    "ItemsPage",
    "Page",
    "PlaceholderPage",
    "RegisterRunPage",
    "SettingsPage",
]
