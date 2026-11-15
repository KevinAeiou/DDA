"""Relatórios: exportação de histórico, frequências, resultados estatísticos e relatório XLSX."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import QGroupBox, QLabel, QPushButton, QVBoxLayout, QWidget

from dungeon_drop_analyzer.core.config import Settings
from dungeon_drop_analyzer.reports import (
    ExportResult,
    export_frequencies_csv,
    export_history_csv,
    export_report_xlsx,
    export_statistics_csv,
)
from dungeon_drop_analyzer.services import Services
from dungeon_drop_analyzer.ui.widgets.files import choose_save_path
from dungeon_drop_analyzer.ui.widgets.messages import guarded, show_error, show_info
from dungeon_drop_analyzer.ui.widgets.run_filter_panel import FilterPanel

from .base import Page

CSV_FILTER = "Arquivos CSV (*.csv)"
XLSX_FILTER = "Planilhas do Excel (*.xlsx)"


class ReportsPage(Page):
    def __init__(
        self, services: Services, settings: Settings, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.services = services
        self.settings = settings
        self.filters = FilterPanel(show_item=True)

        self.history_button = QPushButton("Exportar histórico (CSV)")
        self.frequencies_button = QPushButton("Exportar frequências e proporções (CSV)")
        self.statistics_button = QPushButton("Exportar resultados estatísticos (CSV)")
        self.report_button = QPushButton("Gerar relatório consolidado (XLSX)")
        self.history_button.clicked.connect(
            lambda: self._export("historico", export_history_csv, CSV_FILTER)
        )
        self.frequencies_button.clicked.connect(
            lambda: self._export("frequencias", export_frequencies_csv, CSV_FILTER)
        )
        self.statistics_button.clicked.connect(
            lambda: self._export("resultados-estatisticos", export_statistics_csv, CSV_FILTER)
        )
        self.report_button.clicked.connect(
            lambda: self._export("relatorio", export_report_xlsx, XLSX_FILTER)
        )

        help_label = QLabel(
            "As exportações respeitam os filtros acima e registram a data/hora da exportação. "
            "Os arquivos CSV usam ponto e vírgula como separador, vírgula decimal e codificação "
            "UTF-8 com BOM, para abrir corretamente no Excel em português."
        )
        help_label.setWordWrap(True)
        self.result_label = QLabel()
        self.result_label.setWordWrap(True)

        box = QGroupBox("Exportar")
        box_layout = QVBoxLayout(box)
        for button in (
            self.history_button,
            self.frequencies_button,
            self.statistics_button,
            self.report_button,
        ):
            box_layout.addWidget(button)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h2>Relatórios</h2>"))
        layout.addWidget(self.filters)
        layout.addWidget(help_label)
        layout.addWidget(box)
        layout.addWidget(self.result_label)
        layout.addStretch()

    def refresh(self) -> None:
        self.filters.reload_choices(self.services)

    @staticmethod
    def default_name(prefix: str, extension: str, now: datetime | None = None) -> str:
        moment = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
        return f"dda-{prefix}-{moment}.{extension}"

    def _export(self, prefix: str, exporter: Callable[..., ExportResult], name_filter: str) -> None:
        error = self.filters.validation_error()
        if error:
            show_error(self, error)
            return
        extension = "xlsx" if name_filter == XLSX_FILTER else "csv"
        default = self.settings.export_dir / self.default_name(prefix, extension)
        path = choose_save_path(self, "Salvar exportação", default, name_filter)
        if path is None:
            return
        if path.suffix.lower() != f".{extension}":
            path = Path(f"{path}.{extension}")
        flt = self.filters.current_filter()
        ok, result = guarded(self, lambda: exporter(self.services, flt, path))
        if not ok:
            return
        text = f"Exportação concluída: {result.path} ({result.rows} linha(s))."
        self.result_label.setText(text)
        self.message.emit(text)
        show_info(self, text)
