"""Páginas da interface."""

from .analysis_page import AnalysisPage
from .base import Page
from .catalog_pages import DungeonsPage, ItemsPage
from .dashboard_page import DashboardPage
from .history_page import HistoryPage
from .register_page import RegisterRunPage
from .reports_page import ReportsPage
from .settings_page import SettingsPage

__all__ = [
    "AnalysisPage",
    "DashboardPage",
    "DungeonsPage",
    "HistoryPage",
    "ItemsPage",
    "Page",
    "RegisterRunPage",
    "ReportsPage",
    "SettingsPage",
]
