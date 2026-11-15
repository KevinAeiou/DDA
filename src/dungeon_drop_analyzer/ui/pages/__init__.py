"""Páginas da interface."""

from .analysis_page import AnalysisPage
from .base import Page
from .catalog_pages import DungeonsPage, ItemsPage
from .dashboard_page import DashboardPage
from .history_page import HistoryPage
from .placeholder_page import PlaceholderPage, SettingsPage
from .register_page import RegisterRunPage

__all__ = [
    "AnalysisPage",
    "DashboardPage",
    "DungeonsPage",
    "HistoryPage",
    "ItemsPage",
    "Page",
    "PlaceholderPage",
    "RegisterRunPage",
    "SettingsPage",
]
