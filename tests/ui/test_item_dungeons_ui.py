"""Masmorras do item na interface: cadastro, registro, dashboard e análise (SINTÉTICO)."""

from datetime import datetime

import pytest
from PySide6.QtWidgets import QPushButton
from sqlalchemy import text

from dungeon_drop_analyzer.ui.dialogs import ItemDialog
from dungeon_drop_analyzer.ui.pages import (
    AnalysisPage,
    DashboardPage,
    DungeonsPage,
    ItemsPage,
    RegisterRunPage,
)


def cell(table, row, column):
    return table.item(row, column).text()


def linha(table, nome):
    return next(r for r in range(table.rowCount()) if cell(table, r, 0) == nome)


def registrar(services, dungeon, item, quantidade):
    for k in range(quantidade):
        services.runs.register(
            dungeon.id, item.id, completed_at=datetime(2026, 3, 1 + k % 20, 10, k)
        )


def apagar_associacoes(engine, item_id, dungeon_id=None):
    with engine.begin() as conn:
        if dungeon_id is None:
            conn.execute(text("DELETE FROM item_dungeons WHERE item_id = :i"), {"i": item_id})
        else:
            conn.execute(
                text("DELETE FROM item_dungeons WHERE item_id = :i AND dungeon_id = :d"),
                {"i": item_id, "d": dungeon_id},
            )


@pytest.fixture
def restrito(services):
    d = [services.dungeons.create(f"Masmorra {i}", i) for i in range(1, 4)]
    todas = [m.id for m in d]
    a = services.items.create("A", "weapons", todas)
    a2 = services.items.create("A2", "armor", todas)
    b = services.items.create("B", "relics", [d[0].id, d[1].id])
    c = services.items.create("C", "consumables", [d[2].id])
    registrar(services, d[0], a, 10)
    registrar(services, d[0], a2, 10)
    registrar(services, d[0], b, 30)
    registrar(services, d[1], a, 11)
    registrar(services, d[1], a2, 9)
    registrar(services, d[1], b, 30)
    registrar(services, d[2], a, 10)
    registrar(services, d[2], a2, 10)
    registrar(services, d[2], c, 30)
    return d, (a, a2, b, c)


def botao(dialog, texto):
    return next(b for b in dialog.findChildren(QPushButton) if b.text() == texto)


def test_dialogo_lista_as_masmorras_e_permite_marcar_todas_ou_nenhuma(qapp, services, restrito):
    d, _ = restrito
    dialog = ItemDialog(services.items, services.dungeons.list())
    assert dialog.dungeon_list.count() == 3 and dialog.checked_dungeon_ids() == []
    assert dialog.dungeon_list.item(0).text() == "Masmorra 1 (dificuldade 1)"
    botao(dialog, "Todas").click()
    assert dialog.checked_dungeon_ids() == [m.id for m in d]
    botao(dialog, "Nenhuma").click()
    assert dialog.checked_dungeon_ids() == []


def test_dialogo_exige_masmorra_e_salva_item_em_mais_de_uma(qapp, services, restrito, dialogs):
    d, _ = restrito
    dialog = ItemDialog(services.items, services.dungeons.list())
    dialog.name.setText("Esfera de Aprimoramento de Defesa I")
    dialog.category.setCurrentIndex(dialog.category.findData("amplification_resources"))
    dialog.accept()
    assert "ao menos uma masmorra" in dialogs.errors[-1]
    dialog.set_checked_dungeons({d[0].id, d[2].id})
    dialog.accept()
    novo = next(i for i in services.items.list() if i.name.startswith("Esfera"))
    assert [m.name for m in novo.dungeons] == ["Masmorra 1", "Masmorra 3"]


def test_salvar_e_cadastrar_outro_mantem_valores_e_limpa_nome_e_descricao(
    qapp, services, restrito, dialogs
):
    d, _ = restrito
    dialog = ItemDialog(services.items, services.dungeons.list())
    dialog.name.setText("Esfera I")
    dialog.description.setPlainText("Primeira")
    dialog.category.setCurrentIndex(dialog.category.findData("amplification_resources"))
    dialog.set_checked_dungeons({d[0].id, d[2].id})
    dialog.active.setChecked(False)
    botao(dialog, "Salvar e cadastrar outro").click()
    assert dialogs.errors == []
    assert dialog.name.text() == "" and dialog.description.toPlainText() == ""
    assert dialog.category.currentData() == "amplification_resources"
    assert dialog.checked_dungeon_ids() == [d[0].id, d[2].id]
    assert not dialog.active.isChecked()
    assert "Esfera I" in dialog.status.text() and dialog.created_count == 1
    dialog.name.setText("Esfera II")
    botao(dialog, "Salvar e cadastrar outro").click()
    segundo = next(i for i in services.items.list() if i.name == "Esfera II")
    assert [m.id for m in segundo.dungeons] == [d[0].id, d[2].id]
    assert segundo.category == "amplification_resources" and not segundo.is_active
    assert dialog.created_count == 2


def test_salvar_e_cadastrar_outro_mantem_formulario_quando_ha_erro(
    qapp, services, restrito, dialogs
):
    dialog = ItemDialog(services.items, services.dungeons.list())
    dialog.name.setText("Sem masmorra")
    dialog.category.setCurrentIndex(dialog.category.findData("weapons"))
    botao(dialog, "Salvar e cadastrar outro").click()
    assert "ao menos uma masmorra" in dialogs.errors[-1]
    assert dialog.name.text() == "Sem masmorra" and dialog.created_count == 0


def test_dialogo_de_edicao_nao_tem_salvar_e_cadastrar_outro(qapp, services, restrito):
    _, (a, *_) = restrito
    dialog = ItemDialog(services.items, services.dungeons.list(), services.items.get(a.id))
    assert not any(b.text() == "Salvar e cadastrar outro" for b in dialog.findChildren(QPushButton))


def test_dialogo_de_edicao_preseleciona_e_altera_as_masmorras(qapp, services, restrito):
    d, (a, a2, b, c) = restrito
    dialog = ItemDialog(services.items, services.dungeons.list(), services.items.get(b.id))
    assert dialog.checked_dungeon_ids() == [d[0].id, d[1].id]
    dialog.set_checked_dungeons({d[0].id, d[1].id, d[2].id})
    dialog.accept()
    assert len(services.items.get(b.id).dungeons) == 3


def test_dialogo_nao_deixa_remover_masmorra_com_incursoes(qapp, services, restrito, dialogs):
    d, (a, a2, b, c) = restrito
    dialog = ItemDialog(services.items, services.dungeons.list(), services.items.get(b.id))
    dialog.set_checked_dungeons({d[0].id})
    dialog.accept()
    assert "incursão" in dialogs.errors[-1] and "Masmorra 2" in dialogs.errors[-1]
    assert len(services.items.get(b.id).dungeons) == 2


def test_pagina_de_itens_mostra_masmorras_filtra_e_avisa_itens_sem_definicao(
    qapp, services, restrito, engine
):
    d, (a, a2, b, c) = restrito
    page = ItemsPage(services)
    page.refresh()
    assert [page.table.horizontalHeaderItem(i).text() for i in range(5)][2] == "Masmorras"
    assert cell(page.table, linha(page.table, "A"), 2) == "Todas (3)"
    assert cell(page.table, linha(page.table, "B"), 2) == "Masmorra 1, Masmorra 2"
    assert cell(page.table, linha(page.table, "C"), 2) == "Masmorra 3"
    assert "⚠" not in page.summary.text()

    page.dungeon_filter.setCurrentIndex(page.dungeon_filter.findData(d[2].id))
    assert {cell(page.table, r, 0) for r in range(page.table.rowCount())} == {"A", "A2", "C"}
    page.dungeon_filter.setCurrentIndex(0)

    apagar_associacoes(engine, a2.id)
    page.refresh()
    assert cell(page.table, linha(page.table, "A2"), 2) == "⚠ Não definidas"
    assert "1 item(ns) sem masmorras definidas" in page.summary.text()
    page.dungeon_filter.setCurrentIndex(page.dungeon_filter.findData(d[0].id))
    assert "A2" not in {cell(page.table, r, 0) for r in range(page.table.rowCount())}


def test_busca_de_itens_so_e_habilitada_com_masmorra_selecionada(qapp, services, restrito):
    page = RegisterRunPage(services)
    page.refresh()
    assert page.form.selected_dungeon_id() is None
    assert not page.form.item_combo.isEnabled() and page.form.item_combo.count() == 0
    assert page.form.item_combo.lineEdit().placeholderText() == "Selecione a masmorra primeiro"
    assert "habilitar a busca de itens" in page.hint.text()
    page.form.dungeon_combo.setCurrentIndex(0)
    assert page.form.item_combo.isEnabled()
    assert page.form.item_combo.lineEdit().placeholderText() == "Digite para buscar o item"
    page.form.dungeon_combo.setCurrentIndex(-1)
    assert not page.form.item_combo.isEnabled() and page.form.item_combo.count() == 0


def test_registro_lista_apenas_itens_da_masmorra_escolhida(qapp, services, restrito, dialogs):
    d, (a, a2, b, c) = restrito
    page = RegisterRunPage(services)
    page.refresh()
    combo = page.form.item_combo
    page.form.dungeon_combo.setCurrentIndex(page.form.dungeon_combo.findData(d[0].id))
    assert [combo.itemText(i) for i in range(combo.count())] == ["A", "A2", "B"]
    page.form.dungeon_combo.setCurrentIndex(page.form.dungeon_combo.findData(d[2].id))
    assert [combo.itemText(i) for i in range(combo.count())] == ["A", "A2", "C"]
    page.form.item_combo.setCurrentText("C")
    page.form.dungeon_combo.setCurrentIndex(page.form.dungeon_combo.findData(d[0].id))
    assert page.form.selected_item_id() is None
    page.form.item_combo.setCurrentText("B")
    antes = services.runs.count()
    page.save()
    assert services.runs.count() == antes + 1
    assert dialogs.errors == []
    assert page.form.item_combo.isEnabled()


def test_registro_nao_lista_item_sem_masmorras_definidas(qapp, services, restrito, engine):
    d, (a, a2, b, c) = restrito
    apagar_associacoes(engine, c.id)
    page = RegisterRunPage(services)
    page.refresh()
    for masmorra in d:
        page.form.dungeon_combo.setCurrentIndex(page.form.dungeon_combo.findData(masmorra.id))
        nomes = [page.form.item_combo.itemText(i) for i in range(page.form.item_combo.count())]
        assert "C" not in nomes


def test_registro_exige_item_da_lista_mesmo_digitando_item_de_outra_masmorra(
    qapp, services, restrito, dialogs
):
    d, _ = restrito
    page = RegisterRunPage(services)
    page.refresh()
    page.form.dungeon_combo.setCurrentIndex(page.form.dungeon_combo.findData(d[0].id))
    page.form.item_combo.setCurrentText("C")
    antes = services.runs.count()
    page.save()
    assert dialogs.errors[-1] == "Selecione um item da lista."
    assert services.runs.count() == antes


def test_registro_avisa_quando_nao_ha_itens_para_a_masmorra(qapp, services, restrito):
    d, _ = restrito
    nova = services.dungeons.create("Masmorra Nova", 4)
    page = RegisterRunPage(services)
    page.refresh()
    page.form.dungeon_combo.setCurrentIndex(page.form.dungeon_combo.findData(nova.id))
    assert page.form.item_combo.count() == 0
    assert "Nenhum item ativo está cadastrado para esta masmorra" in page.hint.text()
    page.form.dungeon_combo.setCurrentIndex(page.form.dungeon_combo.findData(d[0].id))
    assert "a lista mostra os itens" in page.hint.text()


def test_dashboard_mostra_masmorras_do_item_e_celulas_indisponiveis(qapp, services, restrito):
    page = DashboardPage(services)
    page.refresh()
    tabela = page.item_table
    assert tabela.horizontalHeaderItem(2).text() == "Masmorras"
    assert cell(tabela, linha(tabela, "A"), 2) == "Todas (3)"
    assert cell(tabela, linha(tabela, "B"), 2) == "Masmorra 1, Masmorra 2"
    comparacao = page.comparison_table
    b, c = linha(comparacao, "B"), linha(comparacao, "C")
    assert cell(comparacao, b, 1) == "30 (60,0%)" and cell(comparacao, b, 3) == "—"
    assert cell(comparacao, c, 1) == "—" and cell(comparacao, c, 3) == "30 (60,0%)"
    assert page.alerts.text() == ""


def test_dashboard_alerta_itens_sem_masmorras_e_incursoes_inconsistentes(
    qapp, services, restrito, engine
):
    d, (a, a2, b, c) = restrito
    apagar_associacoes(engine, a2.id)
    apagar_associacoes(engine, b.id, d[1].id)
    page = DashboardPage(services)
    page.refresh()
    alerta = page.alerts.text()
    assert "sem masmorras definidas" in alerta and "A2" in alerta
    assert "30 incursão(ões)" in alerta and "B em Masmorra 2 (30)" in alerta


def test_analise_por_item_mostra_masmorras_consideradas(qapp, services, restrito):
    page = AnalysisPage(services)
    page.refresh()
    page.item_combo.setCurrentIndex(page.item_combo.findText("B"))
    assert "Masmorras consideradas:</b> Masmorra 1, Masmorra 2" in page.item_summary.text()
    assert page.item_table.rowCount() == 2 and page.pair_table.rowCount() == 1
    assert cell(page.pair_table, 0, 0) == "Masmorra 1 vs Masmorra 2"
    page.item_combo.setCurrentIndex(page.item_combo.findText("C"))
    assert "Masmorras consideradas:</b> Masmorra 3" in page.item_summary.text()
    assert "Teste indefinido" in page.item_summary.text()
    assert page.item_table.rowCount() == 1 and page.pair_table.rowCount() == 0


def test_analise_distribuicao_marca_itens_comuns_e_celulas_indisponiveis(qapp, services, restrito):
    page = AnalysisPage(services)
    page.refresh()
    resumo = page.distribution_summary.text()
    assert "3 masmorras × 2 itens comuns" in resumo and "Itens comuns:</b> A, A2" in resumo
    assert "condicional" in resumo
    tabela = page.distribution_table
    cabecalhos = [tabela.horizontalHeaderItem(i).text() for i in range(tabela.columnCount())]
    assert cabecalhos == ["Masmorra (n)", "A *", "A2 *", "B", "C"]
    assert cell(tabela, 0, 1) == "10 (esp. 10,3)"
    assert cell(tabela, 0, 3) == "30" and cell(tabela, 0, 4) == "—"
    assert cell(tabela, 2, 3) == "—" and cell(tabela, 2, 4) == "30"


def test_analise_dificuldade_marca_niveis_sem_o_item(qapp, services, restrito):
    page = AnalysisPage(services)
    page.refresh()
    tabela = page.difficulty_table
    b, c = linha(tabela, "B"), linha(tabela, "C")
    assert cell(tabela, b, 1) == "30/50 (60,0%)" and cell(tabela, b, 3) == "—"
    assert cell(tabela, c, 1) == "—" and cell(tabela, c, 2) == "—"
    assert cell(tabela, c, 3) == "30/50 (60,0%)"
    assert "obtido (— indica" in page.difficulty_note.text()


def test_analise_exibe_alertas_de_cadastro(qapp, services, restrito, engine):
    d, (a, a2, b, c) = restrito
    apagar_associacoes(engine, a2.id)
    page = AnalysisPage(services)
    page.refresh()
    assert "sem masmorras definidas" in page.status.text() and "A2" in page.status.text()


def test_dialogo_de_item_lista_apenas_masmorras_ativas(qapp, services, restrito):
    d, _ = restrito
    services.dungeons.set_active(d[1].id, False)
    page = ItemsPage(services)
    dialog = page._dialog()
    listadas = [dialog.dungeon_list.item(i).text() for i in range(dialog.dungeon_list.count())]
    assert listadas == ["Masmorra 1 (dificuldade 1)", "Masmorra 3 (dificuldade 3)"]
    edicao = page._dialog(services.items.get(restrito[1][0].id))
    assert edicao.dungeon_list.count() == 2


def test_edicao_preserva_vinculo_com_masmorra_inativa_que_nao_e_listada(qapp, services, restrito):
    d, (a, a2, b, c) = restrito
    services.dungeons.set_active(d[1].id, False)
    page = ItemsPage(services)
    dialog = page._dialog(services.items.get(b.id))
    assert dialog.checked_dungeon_ids() == [d[0].id]
    dialog.description.setPlainText("nova descrição")
    dialog.accept()
    salvo = services.items.get(b.id)
    assert salvo.description == "nova descrição"
    assert [m.name for m in salvo.dungeons] == ["Masmorra 1", "Masmorra 2"]


def test_item_novo_so_pode_ser_vinculado_a_masmorras_listadas(qapp, services, restrito, dialogs):
    d, _ = restrito
    services.dungeons.set_active(d[2].id, False)
    page = ItemsPage(services)
    dialog = page._dialog()
    dialog.name.setText("Novo")
    dialog.category.setCurrentIndex(dialog.category.findData("armor"))
    botao(dialog, "Todas").click()
    dialog.accept()
    novo = next(i for i in services.items.list() if i.name == "Novo")
    assert [m.name for m in novo.dungeons] == ["Masmorra 1", "Masmorra 2"]


def test_dialogo_aceita_mesmo_nome_em_outra_categoria_e_recusa_na_mesma(
    qapp, services, restrito, dialogs
):
    d, _ = restrito
    dialog = ItemDialog(services.items, services.dungeons.list())
    dialog.name.setText("A")
    dialog.category.setCurrentIndex(dialog.category.findData("weapons"))
    dialog.set_checked_dungeons({d[0].id})
    dialog.accept()
    assert "categoria 'Armas'" in dialogs.errors[-1]
    assert dialog.result() == 0
    dialog.category.setCurrentIndex(dialog.category.findData("consumables"))
    dialog.accept()
    assert dialog.result() == 1
    assert sorted(i.display_name for i in services.items.list() if i.name == "A") == [
        "A (Armas)",
        "A (Consumíveis)",
    ]


def test_registro_distingue_itens_de_mesmo_nome_pela_categoria(qapp, services, restrito):
    d, _ = restrito
    services.items.create("A", "consumables", [d[0].id])
    page = RegisterRunPage(services)
    page.refresh()
    page.form.dungeon_combo.setCurrentIndex(page.form.dungeon_combo.findData(d[0].id))
    combo = page.form.item_combo
    nomes = [combo.itemText(i) for i in range(combo.count())]
    assert "A (Armas)" in nomes and "A (Consumíveis)" in nomes and "A2" in nomes


def test_filtro_de_itens_ignora_acentos_e_espacos(qapp, services, restrito):
    d, _ = restrito
    services.items.create("Capa do Mercenário", "accessories", [d[0].id])
    services.items.create("Colar do Mercenário", "accessories", [d[0].id])
    page = ItemsPage(services)
    page.refresh()
    page.filter_edit.setText("mercenario")
    nomes = sorted(cell(page.table, r, 0) for r in range(page.table.rowCount()))
    assert nomes == ["Capa do Mercenário", "Colar do Mercenário"]
    page.filter_edit.setText("capado")
    assert page.table.rowCount() == 1
    page.filter_edit.setText("MERCENÁRIO")
    assert page.table.rowCount() == 2


def test_filtro_de_masmorras_ignora_acentos_e_espacos(qapp, services):
    services.dungeons.create("Reino da Aranha", 1)
    services.dungeons.create("Morada da Serpente", 1)
    page = DungeonsPage(services)
    page.refresh()
    page.filter_edit.setText("reinoda")
    assert [cell(page.table, r, 0) for r in range(page.table.rowCount())] == ["Reino da Aranha"]


def test_busca_de_itens_no_registro_ignora_acentos_e_espacos(qapp, services, restrito):
    d, _ = restrito
    services.items.create("Capa do Mercenário", "accessories", [d[0].id])
    services.items.create("Cinto do Mercenário", "armor", [d[0].id])
    page = RegisterRunPage(services)
    page.refresh()
    page.form.dungeon_combo.setCurrentIndex(page.form.dungeon_combo.findData(d[0].id))
    completer = page.form.item_combo.completer()
    completer.setCompletionPrefix("mercenario")
    assert completer.completionCount() == 2
    completer.setCompletionPrefix("capado")
    assert completer.completionCount() == 1
    assert completer.pathFromIndex(completer.completionModel().index(0, 0)) == "Capa do Mercenário"
    completer.setCompletionPrefix("zzz")
    assert completer.completionCount() == 0
