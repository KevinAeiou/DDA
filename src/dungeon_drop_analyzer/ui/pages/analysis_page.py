"""Análise estatística: por item, distribuição completa e dificuldade (exploratória)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from dungeon_drop_analyzer.services import Services
from dungeon_drop_analyzer.services.analytics import LIMITATION_NOTES, AnalysisReport, interpret
from dungeon_drop_analyzer.statistics import TestResult
from dungeon_drop_analyzer.ui.widgets.analysis_format import (
    fmt_ci,
    fmt_num,
    fmt_pct,
    fmt_pp,
    fmt_pvalue,
    method_label,
)
from dungeon_drop_analyzer.ui.widgets.messages import guarded, show_error
from dungeon_drop_analyzer.ui.widgets.run_filter_panel import FilterPanel

from .base import Page, fill_table, fit_table_height, make_table

NOT_ANALYZABLE = (
    "Dados insuficientes para a análise: são necessárias incursões em ao menos duas masmorras e "
    "ao menos um item obtido nos filtros atuais."
)


def _label() -> QLabel:
    label = QLabel()
    label.setWordWrap(True)
    label.setOpenExternalLinks(False)
    return label


def test_summary(result: TestResult, adjusted: float | None = None, alpha: float = 0.05) -> str:
    lines = [
        f"<b>Método:</b> {method_label(result.method)}",
        f"<b>Amostra (n):</b> {result.n}",
    ]
    if result.statistic is not None:
        lines.append(f"<b>Estatística:</b> {fmt_num(result.statistic)}")
    if result.dof is not None:
        lines.append(f"<b>Graus de liberdade:</b> {result.dof}")
    if result.n_sim is not None:
        lines.append(f"<b>Simulações:</b> {result.n_sim} &nbsp; <b>Semente:</b> {result.seed}")
    lines.append(f"<b>Valor-p bruto:</b> {fmt_pvalue(result.p_value)}")
    decisive = result.p_value
    if adjusted is not None:
        lines.append(f"<b>Valor-p ajustado (Holm, entre itens):</b> {fmt_pvalue(adjusted)}")
        decisive = adjusted
    if result.rationale:
        lines.append(f"<i>{result.rationale}</i>")
    lines.append(f"<b>Interpretação:</b> {interpret(decisive, alpha)}")
    return "<br>".join(lines)


class AnalysisPage(Page):
    def __init__(self, services: Services, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.services = services
        self.report: AnalysisReport | None = None

        self.filters = FilterPanel(show_item=False)
        self.filters.applied.connect(self.reload)
        self.status = _label()
        notes = _label()
        notes.setText("<b>Limitações:</b><br>" + "<br>".join(f"• {n}" for n in LIMITATION_NOTES))

        self.item_combo = QComboBox()
        self.item_combo.currentIndexChanged.connect(lambda _: self.render_item())
        self.item_summary = _label()
        self.item_table = make_table(
            ("Masmorra", "Dificuldade", "x/n", "Proporção", "IC de Wilson 95%", "Amostra")
        )
        self.pair_note = _label()
        self.pair_table = make_table(
            (
                "Comparação",
                "Método",
                "p bruto",
                "p ajustado (Holm)",
                "Diferença",
                "Razão",
                "Odds ratio (IC 95%)",
                "Notas",
            ),
            stretch_column=7,
        )
        item_tab = self._scroll(
            self._row("Item:", self.item_combo),
            self.item_summary,
            self.item_table,
            self.pair_note,
            self.pair_table,
        )

        self.distribution_summary = _label()
        self.distribution_table = make_table(("Masmorra",))
        distribution_tab = self._scroll(self.distribution_summary, self.distribution_table)

        self.difficulty_note = _label()
        self.difficulty_table = make_table(("Item",))
        difficulty_tab = self._scroll(self.difficulty_note, self.difficulty_table)

        self.tabs = QTabWidget()
        self.tabs.addTab(item_tab, "Por item")
        self.tabs.addTab(distribution_tab, "Distribuição completa")
        self.tabs.addTab(difficulty_tab, "Dificuldade (exploratória)")

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h2>Análise estatística</h2>"))
        layout.addWidget(self.filters)
        layout.addWidget(self.status)
        layout.addWidget(self.tabs, 1)
        layout.addWidget(notes)

    @staticmethod
    def _row(text: str, widget: QWidget) -> QWidget:
        holder = QWidget()
        layout = QHBoxLayout(holder)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel(text))
        layout.addWidget(widget, 1)
        return holder

    @staticmethod
    def _scroll(*widgets: QWidget) -> QScrollArea:
        content = QWidget()
        layout = QVBoxLayout(content)
        for widget in widgets:
            layout.addWidget(widget)
        layout.addStretch()
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setWidget(content)
        return area

    def refresh(self) -> None:
        self.filters.reload_choices(self.services)
        self.reload()

    def reload(self) -> None:
        error = self.filters.validation_error()
        if error:
            show_error(self, error)
            return
        flt = self.filters.current_filter()
        ok, report = guarded(self, lambda: self.services.analytics.analyze(flt))
        if not ok:
            return
        self.report = report
        self.render()

    def render(self) -> None:
        report = self.report
        self.status.setText(
            f"<b>Amostra (n):</b> {report.sample_size} incursão(ões) em "
            f"{len(report.dungeons)} masmorra(s); {len(report.items)} item(ns) obtido(s). "
            f"Amostras abaixo de {report.min_n} incursões por masmorra são sinalizadas como "
            "insuficientes (valor de piloto, sem garantia de poder)."
        )
        current = self.item_combo.currentData()
        self.item_combo.blockSignals(True)
        self.item_combo.clear()
        for item in report.items:
            self.item_combo.addItem(item.name, item.id)
        self.item_combo.setCurrentIndex(max(self.item_combo.findData(current), 0))
        self.item_combo.blockSignals(False)
        self.render_item()
        self.render_distribution()
        self.render_difficulty()

    def render_item(self) -> None:
        report = self.report
        if report is None or not report.analyzable or self.item_combo.currentIndex() < 0:
            self.item_summary.setText(NOT_ANALYZABLE)
            for table in (self.item_table, self.pair_table):
                fill_table(table, [])
            self.pair_note.setText("")
            return
        name = self.item_combo.currentText()
        analysis = next(a for a in report.per_item if a.item == name)
        family = len(report.per_item)
        self.item_summary.setText(
            f"<b>Teste global de igualdade das proporções entre masmorras</b> "
            f"(família de {family} item(ns))<br>"
            + test_summary(analysis.global_test, analysis.p_holm_across_items, report.alpha)
        )
        levels = {d.name: d.difficulty for d in report.dungeons}
        rows = []
        for index, p in enumerate(analysis.proportions):
            cells = (
                p.dungeon,
                str(levels[p.dungeon]),
                f"{p.x}/{p.n}",
                fmt_pct(p.p),
                fmt_ci(p.ci),
                "Insuficiente" if p.insufficient else "Adequada",
            )
            rows.append((index, cells))
        fill_table(self.item_table, rows)
        fit_table_height(self.item_table)

        self.pair_note.setText(
            "<b>Comparações pareadas</b> (valor-p ajustado por Holm dentro da família de "
            f"{len(analysis.pairwise)} comparações deste item). Interprete-as apenas se o teste "
            "global for significativo."
        )
        pair_rows = []
        for index, pair in enumerate(analysis.pairwise):
            effect = analysis.effects[(pair.a, pair.b)]
            odds = (
                "—"
                if effect.odds_ratio is None
                else f"{fmt_num(effect.odds_ratio, 2)} "
                f"[{fmt_num(effect.odds_ratio_ci[0], 2)}; {fmt_num(effect.odds_ratio_ci[1], 2)}]"
            )
            cells = (
                f"{pair.a} vs {pair.b}",
                method_label(pair.method),
                fmt_pvalue(pair.p_raw),
                fmt_pvalue(pair.p_holm),
                fmt_pp(effect.diff_pp),
                fmt_num(effect.ratio, 2),
                odds,
                " ".join(effect.notes),
            )
            pair_rows.append((index, cells))
        fill_table(self.pair_table, pair_rows)
        fit_table_height(self.pair_table, max_rows=10)

    def render_distribution(self) -> None:
        report = self.report
        if report is None or not report.analyzable:
            self.distribution_summary.setText(NOT_ANALYZABLE)
            fill_table(self.distribution_table, [])
            return
        overall = report.overall
        self.distribution_summary.setText(
            "<b>Distribuição completa: masmorras × itens</b> "
            f"(tabela {len(report.dungeons)}×{len(report.items)})<br>"
            "H0: a distribuição dos itens é igual em todas as masmorras.<br>"
            + test_summary(overall, alpha=report.alpha)
        )
        headers = ["Masmorra (n)"] + [item.name for item in report.items]
        self.distribution_table.setColumnCount(len(headers))
        self.distribution_table.setHorizontalHeaderLabels(headers)
        expected = overall.expected
        rows = []
        for r, dungeon in enumerate(report.dungeons):
            cells = [f"{dungeon.name} ({report.runs_per_dungeon[dungeon.id]})"]
            for c in range(len(report.items)):
                observed = int(report.matrix[r, c])
                if expected is not None and expected.shape == report.matrix.shape:
                    cells.append(f"{observed} (esp. {fmt_num(float(expected[r, c]), 1)})")
                else:
                    cells.append(str(observed))
            rows.append((dungeon.id, tuple(cells)))
        fill_table(self.distribution_table, rows)
        fit_table_height(self.distribution_table, max_rows=10)

    def render_difficulty(self) -> None:
        report = self.report
        if report is None or not report.levels:
            self.difficulty_note.setText(NOT_ANALYZABLE)
            fill_table(self.difficulty_table, [])
            return
        self.difficulty_note.setText(
            "<b>Proporção de cada item por nível de dificuldade</b> (masmorras do mesmo nível são "
            "agrupadas) e teste de tendência de Cochran-Armitage, <b>apenas exploratório</b>, com "
            "valor-p ajustado por Holm entre itens. Associação não implica causalidade: masmorra e "
            "dificuldade estão confundidas."
        )
        headers = ["Item"]
        for level in report.levels:
            headers.append(
                f"Nível {level.difficulty} ({', '.join(level.dungeons)}; n={level.runs})"
            )
        headers += ["Direção", "Z", "p bruto", "p ajustado (Holm)"]
        self.difficulty_table.setColumnCount(len(headers))
        self.difficulty_table.setHorizontalHeaderLabels(headers)
        rows = []
        for trend in report.trends:
            cells = [trend.item.name]
            for level in report.levels:
                count = level.counts[trend.item.id]
                cells.append(f"{count}/{level.runs} ({fmt_pct(count / level.runs)})")
            result = trend.result
            cells += [
                result.direction,
                fmt_num(result.z),
                fmt_pvalue(result.p_value),
                fmt_pvalue(trend.p_holm),
            ]
            rows.append((trend.item.id, tuple(cells)))
        fill_table(self.difficulty_table, rows)
        fit_table_height(self.difficulty_table, max_rows=15)
