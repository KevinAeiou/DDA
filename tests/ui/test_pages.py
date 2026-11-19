"""Páginas e janela principal: fluxo cadastro, registro e histórico (dados SINTÉTICOS)."""

from datetime import datetime

from PySide6.QtCore import QDateTime

from dungeon_drop_analyzer.ui.pages import (
    DungeonsPage,
    HistoryPage,
    ItemsPage,
    RegisterRunPage,
)
from dungeon_drop_analyzer.ui.pages.history_page import PAGE_SIZE
from dungeon_drop_analyzer.ui.windows import MainWindow


def cell(page, row, column):
    return page.table.item(row, column).text()


def test_pagina_de_masmorras_lista_filtra_e_alterna_ativa(qapp, services, seeded, dialogs):
    page = DungeonsPage(services)
    mensagens = []
    page.message.connect(mensagens.append)
    page.refresh()
    assert page.table.rowCount() == 5
    page.filter_edit.setText("masmorra 3")
    assert page.table.rowCount() == 1 and cell(page, 0, 0) == "Masmorra 3"
    assert "1 de 5" in page.summary.text()
    page.table.selectRow(0)
    page.toggle_selected()
    assert cell(page, 0, 3) == "Não"
    assert mensagens and "inativado" in mensagens[-1]


def test_selecao_obrigatoria_para_editar(qapp, services, dialogs):
    page = ItemsPage(services)
    page.refresh()
    page.edit_selected()
    assert dialogs.errors and "Selecione" in dialogs.errors[-1]


def test_pagina_de_itens_mostra_categoria(qapp, services, seeded):
    services.items.create("Zircão", "accessories", [seeded[0][0].id])
    page = ItemsPage(services)
    page.refresh()
    linha = next(r for r in range(page.table.rowCount()) if cell(page, r, 0) == "Zircão")
    assert (cell(page, linha, 1), cell(page, linha, 2), cell(page, linha, 4)) == (
        "Acessórios",
        "Masmorra 1",
        "Sim",
    )


def test_registro_exige_selecao_e_grava_com_feedback(qapp, services, seeded, dialogs):
    dungeons, items = seeded
    page = RegisterRunPage(services)
    mensagens = []
    page.message.connect(mensagens.append)
    page.refresh()
    page.save()
    assert dialogs.errors[-1] == "Selecione a masmorra."
    page.form.dungeon_combo.setCurrentIndex(1)
    page.save()
    assert dialogs.errors[-1] == "Selecione um item da lista."
    assert services.runs.count() == 0

    page.form.item_combo.setCurrentText("Espada")
    page.save()
    assert services.runs.count() == 1
    assert "Espada" in mensagens[-1] and dungeons[1].name in mensagens[-1]
    assert page.form.selected_item_id() is None
    assert page.form.selected_dungeon_id() == dungeons[1].id
    run = services.runs.list()[0]
    assert run.item_id == items[0].id and run.dungeon_id == dungeons[1].id


def test_registro_so_lista_ativos_e_orienta_cadastro(qapp, services, dialogs):
    page = RegisterRunPage(services)
    page.refresh()
    assert not page.save_button.isEnabled()
    assert "masmorras e itens" in page.hint.text()
    d = services.dungeons.create("A", 1)
    i = services.items.create("X", "weapons", [d.id])
    services.items.create("Y", "weapons", [d.id])
    services.items.set_active(i.id, False)
    page.refresh()
    assert page.save_button.isEnabled()
    assert d.name in page.form.dungeon_combo.itemText(0)
    page.form.dungeon_combo.setCurrentIndex(0)
    assert page.form.item_combo.count() == 1


def registrar(services, seeded):
    dungeons, items = seeded
    dados = [
        (0, 0, datetime(2026, 3, 1, 10), "yes", "1.0"),
        (0, 1, datetime(2026, 3, 2, 10), "no", "1.0"),
        (1, 0, datetime(2026, 3, 3, 10), "no", "1.1"),
        (4, 2, datetime(2026, 3, 4, 10), "no", None),
    ]
    for d, i, quando, bonus, versao in dados:
        services.runs.register(
            dungeons[d].id,
            items[i].id,
            completed_at=quando,
            bonus_status=bonus,
            game_version=versao,
        )


def test_historico_lista_em_ordem_e_filtra(qapp, services, seeded, dialogs):
    registrar(services, seeded)
    page = HistoryPage(services)
    page.refresh()
    assert page.table.rowCount() == 4
    assert cell(page, 0, 0).startswith("04/03/2026") and cell(page, 3, 0).startswith("01/03/2026")
    assert cell(page, 0, 2) == "5" and cell(page, 0, 6) == "Não"

    page.filters.dungeon_combo.setCurrentIndex(page.filters.dungeon_combo.findText("Masmorra 1"))
    page.apply_filters()
    assert page.table.rowCount() == 2
    page.clear_filters()
    assert page.table.rowCount() == 4

    page.filters.item_combo.setCurrentIndex(page.filters.item_combo.findText("Espada"))
    page.filters.bonus_combo.setCurrentIndex(page.filters.bonus_combo.findData("no"))
    page.apply_filters()
    assert page.table.rowCount() == 1 and cell(page, 0, 1) == "Masmorra 2"

    page.clear_filters()
    page.filters.difficulty_combo.setCurrentIndex(page.filters.difficulty_combo.findData(5))
    page.apply_filters()
    assert page.table.rowCount() == 1 and cell(page, 0, 3) == "Anel"

    page.clear_filters()
    page.filters.version_combo.setCurrentIndex(page.filters.version_combo.findData("1.1"))
    page.apply_filters()
    assert page.table.rowCount() == 1
    assert "1–1 de 1" in page.summary.text()


def test_historico_filtro_de_periodo_e_validacao(qapp, services, seeded, dialogs):
    registrar(services, seeded)
    page = HistoryPage(services)
    page.refresh()
    page.filters.use_from.setChecked(True)
    page.filters.date_from.setDateTime(QDateTime(2026, 3, 2, 0, 0, 0))
    page.filters.use_to.setChecked(True)
    page.filters.date_to.setDateTime(QDateTime(2026, 3, 3, 23, 59, 59))
    page.apply_filters()
    assert page.table.rowCount() == 2

    page.filters.date_from.setDateTime(QDateTime(2026, 4, 1, 0, 0, 0))
    page.apply_filters()
    assert "anterior" in dialogs.errors[-1]


def test_historico_paginacao(qapp, services, seeded, dialogs, monkeypatch):
    registrar(services, seeded)
    from dungeon_drop_analyzer.ui.pages import history_page

    monkeypatch.setattr(history_page, "PAGE_SIZE", 3)
    page = HistoryPage(services)
    page.refresh()
    assert page.table.rowCount() == 3 and not page.prev_button.isEnabled()
    assert page.next_button.isEnabled()
    page.next_page()
    assert page.table.rowCount() == 1 and cell(page, 0, 0).startswith("01/03/2026")
    assert page.next_button.isEnabled() is False and page.prev_button.isEnabled()
    page.previous_page()
    assert page.table.rowCount() == 3
    assert PAGE_SIZE == 200


def test_historico_corrigir_e_excluir(qapp, services, seeded, dialogs, monkeypatch):
    registrar(services, seeded)
    page = HistoryPage(services)
    mensagens = []
    page.message.connect(mensagens.append)
    page.refresh()
    page.edit_selected()
    assert "Selecione" in dialogs.errors[-1]

    page.table.selectRow(0)
    dialogs.confirm_answer = False
    page.delete_selected()
    assert services.runs.count() == 4 and dialogs.confirmations

    dialogs.confirm_answer = True
    page.delete_selected()
    assert services.runs.count() == 3 and page.table.rowCount() == 3
    assert mensagens[-1] == "Incursão excluída."


def test_janela_principal_navega_e_atualiza(qapp, services, settings, seeded):
    janela = MainWindow(services, settings)
    assert janela.nav.count() == 8
    assert janela.nav.currentItem().text() == "Registrar incursão"
    janela.open_page("Histórico")
    assert janela.stack.currentWidget() is janela.pages["Histórico"]
    janela.open_page("Configurações e backup")
    assert str(settings.db_path) in janela.pages["Configurações e backup"].details
    janela.pages["Itens"].message.emit("ok")
    assert janela.statusBar().currentMessage() == "ok"


def test_fluxo_completo_cadastro_registro_historico(qapp, services, settings, dialogs):
    janela = MainWindow(services, settings)
    janela.open_page("Masmorras")
    floresta = services.dungeons.create("Floresta", 2)
    services.items.create("Arco", "weapons", [floresta.id])
    janela.open_page("Registrar incursão")
    registro = janela.pages["Registrar incursão"]
    registro.form.dungeon_combo.setCurrentIndex(0)
    registro.form.item_combo.setCurrentText("Arco")
    registro.save()
    janela.open_page("Histórico")
    historico = janela.pages["Histórico"]
    assert historico.table.rowCount() == 1
    assert cell(historico, 0, 1) == "Floresta" and cell(historico, 0, 3) == "Arco"
    assert janela.statusBar().currentMessage() == "Incursão registrada: Arco em Floresta."


def test_pagina_de_itens_filtra_por_categoria(qapp, services):
    base = services.dungeons.create("Base", 1)
    services.items.create("Espada", "weapons", [base.id])
    services.items.create("Machado", "weapons", [base.id])
    services.items.create("Poção", "consumables", [base.id])
    services.items.create("Anel", "relics", [base.id])
    page = ItemsPage(services)
    page.refresh()
    assert page.table.rowCount() == 4
    page.category_filter.setCurrentIndex(page.category_filter.findData("weapons"))
    assert page.table.rowCount() == 2
    assert {cell(page, r, 1) for r in range(2)} == {"Armas"}
    page.filter_edit.setText("mach")
    assert page.table.rowCount() == 1 and cell(page, 0, 0) == "Machado"
    page.filter_edit.clear()
    page.category_filter.setCurrentIndex(0)
    assert page.table.rowCount() == 4
