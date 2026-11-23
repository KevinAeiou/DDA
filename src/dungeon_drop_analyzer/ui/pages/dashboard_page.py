"""Dashboard: totais, distribuição de itens, comparação entre masmorras e evolução temporal."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from dungeon_drop_analyzer.models import ItemCategory
from dungeon_drop_analyzer.repositories import RunFilter
from dungeon_drop_analyzer.services import Services
from dungeon_drop_analyzer.services.analytics import ConvergenceSeries, DashboardData
from dungeon_drop_analyzer.statistics import wilson_interval
from dungeon_drop_analyzer.ui.widgets.analysis_format import alert_text, fmt_ci, fmt_pct
from dungeon_drop_analyzer.ui.widgets.charts import (
    ChartCanvas,
    draw_bars,
    draw_convergence,
    draw_lines,
    draw_stacked,
)
from dungeon_drop_analyzer.ui.widgets.formatting import format_category
from dungeon_drop_analyzer.ui.widgets.messages import guarded, show_error
from dungeon_drop_analyzer.ui.widgets.run_filter_panel import FilterPanel

from .base import Page, fill_table, fit_table_height, make_table

MAX_BARS = 15
COVERAGE_HEADERS = (
    "Masmorra",
    "Incursões",
    "Itens vistos",
    "Chance de inédito",
    "Limite de ausentes",
    "Faltam (ausentes)",
    "Faltam (precisão)",
)
COVERAGE_NOTE = (
    "<b>Itens vistos:</b> itens já obtidos / itens ativos cadastrados para a masmorra. "
    "<b>Chance de inédito:</b> chance de a próxima incursão dar um item ainda não visto, pela "
    "estimativa de Good-Turing (itens vistos uma única vez ÷ incursões); quanto menor, mais "
    "completa a cobertura. <b>Limite de ausentes:</b> com 95% de confiança, um item cadastrado "
    "que ainda não saiu tem chance de no máximo esse valor. <b>Faltam:</b> incursões adicionais "
    "para atingir as metas acima (a de precisão usa a chance já observada do item mais "
    "frequente). Defina o total de incursões antes de começar e não pare quando um item raro "
    "aparecer, pois isso infla a estimativa dele."
)


class DashboardPage(Page):
    def __init__(self, services: Services, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.services = services
        self.filters = FilterPanel(show_item=True, active_dungeons_only=True)
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
            ("Item", "Categoria", "Masmorras", "Obtenções", "% da amostra", "IC 95%")
        )
        self.item_box = self._box(
            "Distribuição geral dos itens", self.frequency_label, self.item_chart, self.item_table
        )

        self.margin_spin = QDoubleSpinBox()
        self.margin_spin.setRange(0.1, 20.0)
        self.margin_spin.setDecimals(1)
        self.margin_spin.setSingleStep(0.5)
        self.margin_spin.setValue(2.0)
        self.margin_spin.setPrefix("± ")
        self.margin_spin.setSuffix(" p.p.")
        self.limit_spin = QDoubleSpinBox()
        self.limit_spin.setRange(0.1, 20.0)
        self.limit_spin.setDecimals(1)
        self.limit_spin.setSingleStep(0.5)
        self.limit_spin.setValue(1.0)
        self.limit_spin.setSuffix(" %")
        self.margin_spin.valueChanged.connect(lambda _: self._render_coverage())
        self.limit_spin.valueChanged.connect(lambda _: self._render_coverage())
        targets = QHBoxLayout()
        targets.setContentsMargins(0, 0, 0, 0)
        targets.addWidget(QLabel("Meta de margem de erro do item mais frequente:"))
        targets.addWidget(self.margin_spin)
        targets.addSpacing(16)
        targets.addWidget(QLabel("Meta de limite máximo para itens ainda não obtidos:"))
        targets.addWidget(self.limit_spin)
        targets.addStretch()
        targets_box = QWidget()
        targets_box.setLayout(targets)
        self.coverage_note = QLabel(COVERAGE_NOTE)
        self.coverage_note.setWordWrap(True)
        self.coverage_table = make_table(COVERAGE_HEADERS)
        self.coverage_box = self._box(
            "Cobertura e tamanho da amostra", targets_box, self.coverage_table, self.coverage_note
        )

        self.convergence_dungeon = QComboBox()
        self.convergence_item = QComboBox()
        self.convergence_dungeon.currentIndexChanged.connect(self._fill_convergence_items)
        self.convergence_item.currentIndexChanged.connect(self._render_convergence)
        pickers = QHBoxLayout()
        pickers.setContentsMargins(0, 0, 0, 0)
        pickers.addWidget(QLabel("Masmorra"))
        pickers.addWidget(self.convergence_dungeon, 1)
        pickers.addWidget(QLabel("Item"))
        pickers.addWidget(self.convergence_item, 2)
        pickers_box = QWidget()
        pickers_box.setLayout(pickers)
        self.convergence_chart = ChartCanvas(height=3.2)
        self.convergence_label = QLabel()
        self.convergence_label.setWordWrap(True)
        self.convergence_box = self._box(
            "Convergência da estimativa",
            pickers_box,
            self.convergence_chart,
            self.convergence_label,
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
        for box in (
            self.dungeon_box,
            self.coverage_box,
            self.item_box,
            self.convergence_box,
            self.comparison_box,
            self.timeline_box,
        ):
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
            self._flt = flt
            self.render(data)

    def render(self, data: DashboardData) -> None:
        self._data = data
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
        self._render_coverage()
        self._render_items(data)
        self._fill_convergence_dungeons()
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
                    fmt_ci(c.ci) if total else "—",
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
        errors = None
        if total and all(c.ci is not None for c in top):
            errors = (
                [max(0.0, total * (c.share - c.ci[0])) for c in top],
                [max(0.0, total * (c.ci[1] - c.share)) for c in top],
            )
        draw_bars(
            self.item_chart,
            f"Obtenções por item (até {MAX_BARS} mais frequentes, com IC de 95%)",
            [c.item.display_name for c in top],
            [c.count for c in top],
            "Obtenções",
            errors,
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
        for row, item_count in enumerate(data.item_counts):
            for column, c in enumerate(with_data, start=1):
                cell_item = self.comparison_table.item(row, column)
                if cell_item is None or cell_item.text() == "—":
                    continue
                count = data.cells.get((c.dungeon.id, item_count.item.id), 0)
                cell_item.setToolTip(f"IC 95%: {fmt_ci(wilson_interval(count, c.runs))}")

    def _render_coverage(self) -> None:
        data = getattr(self, "_data", None)
        if data is None:
            return
        margin = self.margin_spin.value() / 100
        limit = self.limit_spin.value() / 100
        rows = []
        for row in data.coverage:
            seen = f"{row.seen_registered} / {row.registered_items}"
            if row.seen_total > row.seen_registered:
                seen += f" (+{row.seen_total - row.seen_registered} fora do cadastro)"
            if row.registered_items and row.unseen_registered == 0:
                absent = "Todos vistos"
                missing_absent = "—"
            else:
                absent = fmt_pct(row.absent_upper)
                missing_absent = self._missing_text(row.missing_for_absent_limit(limit))
            missing = row.missing_for_margin(margin)
            rows.append(
                (
                    row.dungeon.id,
                    (
                        row.dungeon.name,
                        str(row.runs),
                        seen,
                        fmt_pct(row.unseen_chance),
                        absent,
                        missing_absent,
                        "—" if missing is None else self._missing_text(missing),
                    ),
                )
            )
        fill_table(self.coverage_table, rows)
        fit_table_height(self.coverage_table)

    @staticmethod
    def _missing_text(missing: int) -> str:
        return "✔ atingida" if missing == 0 else f"{missing:,}".replace(",", ".")

    def _fill_convergence_dungeons(self) -> None:
        data = self._data
        keep = self.convergence_dungeon.currentData()
        self.convergence_dungeon.blockSignals(True)
        self.convergence_dungeon.clear()
        for c in data.dungeon_counts:
            if c.runs > 0:
                self.convergence_dungeon.addItem(f"{c.dungeon.name} (n={c.runs})", c.dungeon.id)
        self.convergence_dungeon.setCurrentIndex(max(self.convergence_dungeon.findData(keep), 0))
        self.convergence_dungeon.blockSignals(False)
        self._fill_convergence_items()

    def _fill_convergence_items(self) -> None:
        data = self._data
        dungeon_id = self.convergence_dungeon.currentData()
        keep = self.convergence_item.currentData()
        self.convergence_item.blockSignals(True)
        self.convergence_item.clear()
        if dungeon_id is not None:
            for c in data.item_counts:
                count = data.cells.get((dungeon_id, c.item.id), 0)
                if count > 0:
                    self.convergence_item.addItem(f"{c.item.display_name} ({count})", c.item.id)
        self.convergence_item.setCurrentIndex(max(self.convergence_item.findData(keep), 0))
        self.convergence_item.blockSignals(False)
        self._render_convergence()

    def _render_convergence(self) -> None:
        title = "Proporção acumulada do item ao longo das incursões"
        dungeon_id = self.convergence_dungeon.currentData()
        item_id = self.convergence_item.currentData()
        if dungeon_id is None or item_id is None:
            self.convergence_chart.show_empty(title)
            self.convergence_label.setText("")
            return
        flt = getattr(self, "_flt", None) or RunFilter()
        ok, series = guarded(
            self, lambda: self.services.analytics.convergence(dungeon_id, item_id, flt)
        )
        if not ok or series is None:
            return
        draw_convergence(
            self.convergence_chart,
            f"{series.item_label} em {series.dungeon_name}: {title.lower()}",
            series.proportion,
            series.lower,
            series.upper,
        )
        self.convergence_label.setText(self._convergence_text(series))

    @staticmethod
    def _convergence_text(series: ConvergenceSeries) -> str:
        if series.runs == 0:
            return ""
        text = (
            f"<b>{series.item_label}</b> em <b>{series.dungeon_name}</b>: {series.final_hits} "
            f"obtenção(ões) em {series.runs} incursões, {fmt_pct(series.final_proportion)} "
            f"(IC 95% {fmt_ci(series.final_interval)}, margem de ± "
            f"{fmt_pct(series.final_margin)})."
        )
        if series.runs >= 4:
            half = series.runs // 2
            text += (
                f" A margem era de ± {fmt_pct(series.margin_at(half))} com {half} incursões; "
                "quando ela deixa de cair de forma perceptível, a estimativa estabilizou."
            )
        if series.runs < 30:
            text += " Amostra pequena: a estimativa ainda oscila bastante."
        return text
