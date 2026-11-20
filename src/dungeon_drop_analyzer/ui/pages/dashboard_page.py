"""Dashboard: totais, distribuição de itens, comparação entre masmorras e evolução temporal."""

from __future__ import annotations

from PySide6.QtWidgets import QGroupBox, QLabel, QScrollArea, QVBoxLayout, QWidget

from dungeon_drop_analyzer.models import ItemCategory
from dungeon_drop_analyzer.services import Services
from dungeon_drop_analyzer.services.analytics import DashboardData
from dungeon_drop_analyzer.ui.widgets.analysis_format import alert_text, fmt_pct
from dungeon_drop_analyzer.ui.widgets.charts import (
    ChartCanvas,
    draw_bars,
    draw_lines,
    draw_stacked,
)
from dungeon_drop_analyzer.ui.widgets.formatting import format_category
from dungeon_drop_analyzer.ui.widgets.messages import guarded, show_error
from dungeon_drop_analyzer.ui.widgets.run_filter_panel import FilterPanel

from .base import Page, fill_table, fit_table_height, make_table

MAX_BARS = 15


class DashboardPage(Page):
    def __init__(self, services: Services, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.services = services
        self.filters = FilterPanel(show_item=True)
        self.filters.applied.connect(self.reload)

        self.kpis = QLabel()
        self.kpis.setWordWrap(True)
        self.notice = QLabel()
        self.notice.setWordWrap(True)
        self.alerts = QLabel()
        self.alerts.setWordWrap(True)

        self.dungeon_table = make_table(("Masmorra", "Dificuldade", "Incursões", "% do total"))
        self.dungeon_box = self._box("Incursões por masmorra", self.dungeon_table)

        self.frequency_label = QLabel()
        self.frequency_label.setWordWrap(True)
        self.item_chart = ChartCanvas(height=3.2)
        self.item_table = make_table(
            ("Item", "Categoria", "Masmorras", "Obtenções", "% da amostra")
        )
        self.item_box = self._box(
            "Distribuição geral dos itens", self.frequency_label, self.item_chart, self.item_table
        )

        self.category_chart = ChartCanvas(height=3.2)
        self.comparison_table = make_table(("Item",))
        self.comparison_box = self._box(
            "Comparação por masmorra", self.category_chart, self.comparison_table
        )

        self.timeline_chart = ChartCanvas(height=3.0)
        self.timeline_box = self._box("Evolução temporal", self.timeline_chart)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.addWidget(QLabel("<h2>Dashboard</h2>"))
        layout.addWidget(self.filters)
        layout.addWidget(self.kpis)
        layout.addWidget(self.notice)
        layout.addWidget(self.alerts)
        for box in (self.dungeon_box, self.item_box, self.comparison_box, self.timeline_box):
            layout.addWidget(box)
        layout.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    @staticmethod
    def _box(title: str, *widgets: QWidget) -> QGroupBox:
        box = QGroupBox(title)
        layout = QVBoxLayout(box)
        for widget in widgets:
            layout.addWidget(widget)
        return box

    def refresh(self) -> None:
        self.filters.reload_choices(self.services)
        self.reload()

    def reload(self) -> None:
        error = self.filters.validation_error()
        if error:
            show_error(self, error)
            return
        flt = self.filters.current_filter()
        ok, data = guarded(self, lambda: self.services.analytics.dashboard(flt))
        if ok:
            self.render(data)

    def render(self, data: DashboardData) -> None:
        total = data.total_runs
        with_data = sum(1 for c in data.dungeon_counts if c.runs > 0)
        self.kpis.setText(
            f"<b>Amostra (n):</b> {total} incursão(ões) &nbsp;|&nbsp; "
            f"<b>Itens distintos obtidos:</b> {data.distinct_items} &nbsp;|&nbsp; "
            f"<b>Masmorras com dados:</b> {with_data}"
        )
        self.notice.setText("" if total else "Nenhuma incursão encontrada para os filtros atuais.")
        self.alerts.setText(alert_text(data.undefined_items, data.inconsistent_runs))
        self._render_dungeons(data)
        self._render_items(data)
        self._render_comparison(data)
        draw_lines(
            self.timeline_chart, "Incursões acumuladas por masmorra", data.timeline, "Incursões"
        )
        self.timeline_box.setTitle(f"Evolução temporal (n = {total})")

    def _render_dungeons(self, data: DashboardData) -> None:
        total = data.total_runs
        rows = [
            (
                c.dungeon.id,
                (
                    c.dungeon.name,
                    str(c.dungeon.difficulty),
                    str(c.runs),
                    fmt_pct(c.runs / total if total else None),
                ),
            )
            for c in data.dungeon_counts
        ]
        fill_table(self.dungeon_table, rows)
        fit_table_height(self.dungeon_table)
        self.dungeon_box.setTitle(f"Incursões por masmorra (n = {total})")

    @staticmethod
    def _dungeon_text(data: DashboardData, item_id: int) -> str:
        ids = data.availability.get(item_id)
        if not ids:
            return "⚠ Não definidas"
        if len(ids) == len(data.dungeon_counts):
            return f"Todas ({len(ids)})"
        return ", ".join(c.dungeon.name for c in data.dungeon_counts if c.dungeon.id in ids)

    def _render_items(self, data: DashboardData) -> None:
        total = data.total_runs
        rows = [
            (
                c.item.id,
                (
                    c.item.display_name,
                    format_category(c.item.category),
                    self._dungeon_text(data, c.item.id),
                    str(c.count),
                    fmt_pct(c.share),
                ),
            )
            for c in data.item_counts
        ]
        fill_table(self.item_table, rows)
        fit_table_height(self.item_table)
        self.item_box.setTitle(f"Distribuição geral dos itens (n = {total})")
        if total:
            self.frequency_label.setText(self._frequency_text(data))
        else:
            self.frequency_label.setText("")
        top = data.item_counts[:MAX_BARS]
        draw_bars(
            self.item_chart,
            f"Obtenções por item (até {MAX_BARS} mais frequentes)",
            [c.item.display_name for c in top],
            [c.count for c in top],
            "Obtenções",
        )

    @staticmethod
    def _frequency_text(data: DashboardData) -> str:
        def describe(counts) -> str:
            names = ", ".join(c.item.display_name for c in counts)
            tie = " (empate)" if len(counts) > 1 else ""
            return f"{names}{tie} — {counts[0].count} obtenção(ões), {fmt_pct(counts[0].share)}"

        most = describe(data.most_frequent)
        least = describe(data.least_frequent)
        if data.least_frequent and data.least_frequent[0].count == 0:
            least += " — nunca obtido(s) na amostra"
        return f"<b>Mais frequente:</b> {most}<br><b>Menos frequente:</b> {least}"

    def _render_comparison(self, data: DashboardData) -> None:
        total = data.total_runs
        with_data = [c for c in data.dungeon_counts if c.runs > 0]
        self.comparison_box.setTitle(f"Comparação por masmorra (n = {total})")
        groups = [f"{c.dungeon.name} (n={c.runs})" for c in with_data]
        series = {
            category.label: [
                data.category_counts.get(c.dungeon.id, {}).get(category.value, 0) / c.runs
                for c in with_data
            ]
            for category in ItemCategory
        }
        draw_stacked(
            self.category_chart,
            "Proporção de itens por categoria em cada masmorra",
            groups,
            series,
            "Proporção",
        )
        headers = ["Item"] + [f"{c.dungeon.name} (n={c.runs})" for c in with_data]
        self.comparison_table.setColumnCount(len(headers))
        self.comparison_table.setHorizontalHeaderLabels(headers)
        rows = []
        for item_count in data.item_counts:
            cells = [item_count.item.display_name]
            for c in with_data:
                count = data.cells.get((c.dungeon.id, item_count.item.id), 0)
                if count == 0 and not data.is_available(item_count.item.id, c.dungeon.id):
                    cells.append("—")
                else:
                    cells.append(f"{count} ({fmt_pct(count / c.runs)})")
            rows.append((item_count.item.id, tuple(cells)))
        fill_table(self.comparison_table, rows)
        fit_table_height(self.comparison_table)
