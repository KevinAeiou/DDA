"""Dashboard e análise estatística na interface (dados SINTÉTICOS)."""

from datetime import datetime

import pytest
from PySide6.QtCore import QDateTime

from dungeon_drop_analyzer.statistics import homogeneity_test
from dungeon_drop_analyzer.ui.pages import AnalysisPage, DashboardPage
from dungeon_drop_analyzer.ui.pages.analysis_page import NOT_ANALYZABLE
from dungeon_drop_analyzer.ui.widgets.analysis_format import (
    fmt_ci,
    fmt_num,
    fmt_pct,
    fmt_pp,
    fmt_pvalue,
)
from dungeon_drop_analyzer.ui.windows import MainWindow


def registrar(services, dungeon, item, quantidade, dia, **extra):
    for k in range(quantidade):
        services.runs.register(
            dungeon.id, item.id, completed_at=datetime(2026, 3, dia, 10, k % 60), **extra
        )


@pytest.fixture
def cenario(services, seeded):
    ds, its = seeded
    registrar(services, ds[0], its[0], 30, 1)
    registrar(services, ds[0], its[1], 10, 2)
    registrar(services, ds[1], its[0], 10, 2)
    registrar(services, ds[1], its[1], 30, 3)
    registrar(services, ds[2], its[0], 20, 3, bonus_status="yes")
    registrar(services, ds[2], its[1], 20, 4, bonus_status="yes")
    return ds, its


def cell(table, row, column):
    return table.item(row, column).text()


def test_formatacao_numerica_pt_br():
    assert fmt_num(1.23456) == "1,235" and fmt_num(None) == "—"
    assert fmt_pvalue(0.00001) == "< 0,001" and fmt_pvalue(0.0123) == "0,0123"
    assert fmt_pvalue(None) == "—"
    assert fmt_pct(0.1234) == "12,3%" and fmt_pct(None) == "—"
    assert fmt_ci((0.1, 0.25)) == "[10,0%; 25,0%]" and fmt_ci(None) == "—"
    assert fmt_pp(10.04) == "10,0 p.p."


def test_dashboard_vazio_informa_ausencia_de_dados(qapp, services, seeded):
    page = DashboardPage(services)
    page.refresh()
    assert "Nenhuma incursão" in page.notice.text()
    assert "n):</b> 0" in page.kpis.text()
    assert page.item_chart.is_empty and page.timeline_chart.is_empty
    assert page.dungeon_table.rowCount() == 5


def test_dashboard_mostra_totais_distribuicao_e_empates(qapp, services, cenario):
    page = DashboardPage(services)
    page.refresh()
    assert "120" in page.kpis.text() and "Itens distintos obtidos:</b> 2" in page.kpis.text()
    assert page.notice.text() == ""
    assert "(n = 120)" in page.dungeon_box.title()
    linhas = {cell(page.dungeon_table, r, 0): cell(page.dungeon_table, r, 2) for r in range(5)}
    assert linhas["Masmorra 1"] == "40" and linhas["Masmorra 5"] == "0"
    assert cell(page.dungeon_table, 0, 3) == "33,3%"
    texto = page.frequency_label.text()
    assert "Escudo, Espada (empate)" in texto and "Anel" in texto
    assert "nunca obtido" in texto
    assert [cell(page.item_table, r, 0) for r in range(3)] == ["Escudo", "Espada", "Anel"]
    assert cell(page.item_table, 0, 2) == "60" and cell(page.item_table, 0, 3) == "50,0%"
    assert not page.item_chart.is_empty and not page.category_chart.is_empty
    assert not page.timeline_chart.is_empty


def test_dashboard_comparacao_por_masmorra(qapp, services, cenario):
    page = DashboardPage(services)
    page.refresh()
    tabela = page.comparison_table
    assert tabela.columnCount() == 4
    assert tabela.horizontalHeaderItem(1).text() == "Masmorra 1 (n=40)"
    assert cell(tabela, 0, 0) == "Escudo" and cell(tabela, 0, 1) == "10 (25,0%)"
    assert cell(tabela, 1, 1) == "30 (75,0%)" and cell(tabela, 0, 2) == "30 (75,0%)"


def test_dashboard_filtros_alteram_a_amostra(qapp, services, cenario):
    page = DashboardPage(services)
    page.refresh()
    page.filters.dungeon_combo.setCurrentIndex(page.filters.dungeon_combo.findText("Masmorra 2"))
    page.filters.apply()
    assert "(n = 40)" in page.dungeon_box.title()
    assert "Itens distintos obtidos:</b> 2" in page.kpis.text()
    page.filters.clear()
    assert "(n = 120)" in page.dungeon_box.title()
    page.filters.bonus_combo.setCurrentIndex(page.filters.bonus_combo.findData("yes"))
    page.filters.apply()
    assert "(n = 40)" in page.item_box.title()


def test_dashboard_valida_periodo(qapp, services, cenario, dialogs):
    page = DashboardPage(services)
    page.refresh()
    page.filters.use_from.setChecked(True)
    page.filters.use_to.setChecked(True)
    page.filters.date_from.setDateTime(QDateTime(2026, 5, 1, 0, 0, 0))
    page.filters.date_to.setDateTime(QDateTime(2026, 4, 1, 0, 0, 0))
    page.filters.apply()
    assert "anterior" in dialogs.errors[-1]


def test_analise_sem_dados_orienta_o_usuario(qapp, services, seeded):
    page = AnalysisPage(services)
    page.refresh()
    assert page.item_summary.text() == NOT_ANALYZABLE
    assert page.distribution_summary.text() == NOT_ANALYZABLE
    assert page.item_combo.count() == 0 and page.item_table.rowCount() == 0


def test_analise_por_item_mostra_proporcoes_testes_e_pares(qapp, services, cenario):
    page = AnalysisPage(services)
    page.refresh()
    assert page.item_combo.count() == 2 and page.item_combo.currentText() == "Escudo"
    assert "120 incursão(ões) em 3 masmorra(s)" in page.status.text()
    assert page.item_table.rowCount() == 3
    assert cell(page.item_table, 0, 2) == "10/40" and cell(page.item_table, 0, 3) == "25,0%"
    assert cell(page.item_table, 0, 5) == "Insuficiente"
    assert cell(page.item_table, 0, 4).startswith("[") and ";" in cell(page.item_table, 0, 4)
    resumo = page.item_summary.text()
    assert "Qui-quadrado de homogeneidade" in resumo
    assert "Valor-p bruto" in resumo and "Holm, entre itens" in resumo
    assert "Graus de liberdade:</b> 2" in resumo
    assert "Foi detectada diferença" in resumo
    assert page.pair_table.rowCount() == 3
    assert cell(page.pair_table, 0, 0) == "Masmorra 1 vs Masmorra 2"
    assert cell(page.pair_table, 0, 4) == "-50,0 p.p."
    assert cell(page.pair_table, 0, 6).startswith("0,11 [")
    assert "Holm dentro da família de 3 comparações" in page.pair_note.text()


def test_analise_troca_de_item(qapp, services, cenario):
    page = AnalysisPage(services)
    page.refresh()
    page.item_combo.setCurrentIndex(1)
    assert cell(page.item_table, 0, 2) == "30/40"
    page.filters.dungeon_combo.setCurrentIndex(page.filters.dungeon_combo.findText("Masmorra 1"))
    page.filters.apply()
    assert "Dados insuficientes" in page.item_summary.text()


def test_analise_distribuicao_completa_com_esperados(qapp, services, cenario):
    page = AnalysisPage(services)
    page.refresh()
    resumo = page.distribution_summary.text()
    assert "tabela 3×2" in resumo and "H0:" in resumo
    assert "Qui-quadrado" in resumo and "Interpretação" in resumo
    tabela = page.distribution_table
    assert tabela.columnCount() == 3 and tabela.rowCount() == 3
    assert cell(tabela, 0, 0) == "Masmorra 1 (40)"
    assert cell(tabela, 0, 1) == "10 (esp. 20,0)"
    esperado = homogeneity_test(page.report.matrix)
    assert fmt_pvalue(esperado.p_value) in resumo


def test_analise_dificuldade_exploratoria(qapp, services, cenario):
    page = AnalysisPage(services)
    page.refresh()
    assert "apenas exploratório" in page.difficulty_note.text()
    assert "confundidas" in page.difficulty_note.text()
    tabela = page.difficulty_table
    cabecalhos = [tabela.horizontalHeaderItem(c).text() for c in range(tabela.columnCount())]
    assert cabecalhos[1].startswith("Nível 1 (Masmorra 1; n=40)")
    assert cabecalhos[-4:] == ["Direção", "Z", "p bruto", "p ajustado (Holm)"]
    assert cell(tabela, 0, 0) == "Escudo" and cell(tabela, 0, 1) == "10/40 (25,0%)"
    assert cell(tabela, 0, 4) == "crescente" and cell(tabela, 1, 4) == "decrescente"


def test_analise_exibe_limitacoes_e_metodo_monte_carlo(qapp, services, seeded):
    ds, its = seeded
    registrar(services, ds[0], its[0], 3, 1)
    registrar(services, ds[0], its[1], 1, 1)
    registrar(services, ds[1], its[1], 3, 2)
    registrar(services, ds[1], its[2], 1, 2)
    registrar(services, ds[2], its[2], 2, 3)
    registrar(services, ds[2], its[0], 1, 3)
    page = AnalysisPage(services)
    page.refresh()
    resumo = page.distribution_summary.text()
    assert "Monte Carlo" in resumo and "Simulações:" in resumo and "Semente:" in resumo
    assert "Cochran" in resumo


def test_janela_principal_usa_dashboard_e_analise(qapp, services, settings, cenario):
    janela = MainWindow(services, settings)
    assert isinstance(janela.pages["Dashboard"], DashboardPage)
    assert isinstance(janela.pages["Análise estatística"], AnalysisPage)
    janela.open_page("Dashboard")
    assert "120" in janela.pages["Dashboard"].kpis.text()
    janela.open_page("Análise estatística")
    assert janela.pages["Análise estatística"].item_combo.count() == 2
