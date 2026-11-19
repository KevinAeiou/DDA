"""Formulário de incursão e diálogos (dados SINTÉTICOS)."""

from datetime import datetime

from PySide6.QtCore import QDateTime

from dungeon_drop_analyzer.ui.dialogs import DungeonDialog, ItemDialog, RunEditDialog
from dungeon_drop_analyzer.ui.widgets.formatting import (
    format_datetime,
    format_duration,
    format_tristate,
)
from dungeon_drop_analyzer.ui.widgets.run_form import RunForm


def test_formatacao():
    assert format_duration(None) == ""
    assert format_duration(75) == "1:15"
    assert format_duration(3725) == "1:02:05"
    assert format_tristate("yes") == "Sim" and format_tristate("unknown") == "Desconhecido"
    assert format_datetime(datetime(2026, 3, 5, 10, 0).astimezone()).startswith("05/03/2026")


def test_run_form_valores_padrao_e_selecao(qapp, seeded):
    dungeons, items = seeded
    form = RunForm()
    form.set_choices(dungeons, items)
    assert form.values()["dungeon_id"] is None and form.values()["item_id"] is None
    assert form.optional.isHidden()
    form.dungeon_combo.setCurrentIndex(2)
    form.item_combo.setCurrentText("escudo")
    values = form.values()
    assert values["dungeon_id"] == dungeons[2].id
    assert values["item_id"] == items[1].id
    assert values["duration_seconds"] is None
    assert (values["bonus_status"], values["event_status"]) == ("unknown", "unknown")


def test_run_form_texto_digitado_invalido_nao_seleciona_item(qapp, seeded):
    form = RunForm()
    form.set_choices(*seeded)
    form.item_combo.setCurrentText("inexistente")
    assert form.selected_item_id() is None


def test_run_form_opcoes_expandem(qapp, seeded):
    form = RunForm()
    form.show()
    form.options_box.setChecked(True)
    assert form.optional.isVisible()
    form.duration.setValue(90)
    form.game_version.setText("1.2")
    form.bonus_combo.setCurrentIndex(form.bonus_combo.findData("yes"))
    form.completed_at.setDateTime(QDateTime(2026, 3, 5, 10, 30, 0))
    values = form.values()
    assert values["duration_seconds"] == 90 and values["game_version"] == "1.2"
    assert values["bonus_status"] == "yes"
    assert values["completed_at"] == datetime(2026, 3, 5, 10, 30)


def test_dialogo_de_masmorra_cria_edita_e_mantem_aberto_em_erro(qapp, services, dialogs):
    dialog = DungeonDialog(services.dungeons)
    dialog.name.setText("Caverna")
    dialog.difficulty.setValue(3)
    dialog.description.setPlainText("  úmida ")
    dialog.accept()
    criada = services.dungeons.list()[0]
    assert (criada.name, criada.difficulty, criada.description) == ("Caverna", 3, "úmida")

    duplicada = DungeonDialog(services.dungeons)
    duplicada.name.setText("caverna")
    duplicada.accept()
    assert dialogs.errors and "Já existe" in dialogs.errors[-1]
    assert duplicada.result() == 0

    edicao = DungeonDialog(services.dungeons, criada)
    assert edicao.name.text() == "Caverna" and edicao.difficulty.value() == 3
    edicao.difficulty.setValue(5)
    edicao.active.setChecked(False)
    edicao.accept()
    atual = services.dungeons.get(criada.id)
    assert atual.difficulty == 5 and atual.is_active is False


def test_dialogo_de_item_nome_vazio_gera_aviso(qapp, services, dialogs):
    masmorra = services.dungeons.create("Base", 1)
    dialog = ItemDialog(services.items, services.dungeons.list())
    dialog.accept()
    assert dialogs.errors and "obrigatório" in dialogs.errors[-1]
    dialog.name.setText("Anel")
    dialog.category.setCurrentIndex(dialog.category.findData("accessories"))
    dialog.set_checked_dungeons({masmorra.id})
    dialog.accept()
    item = services.items.list()[0]
    assert (item.name, item.category) == ("Anel", "accessories")


def test_dialogo_de_correcao_altera_item_e_ignora_data_intocada(qapp, services, seeded):
    dungeons, items = seeded
    run = services.runs.register(dungeons[0].id, items[0].id, notes="a")
    dialog = RunEditDialog(services, run)
    dialog.form.item_combo.setCurrentText("Anel")
    dialog.form.notes.setPlainText("b")
    dialog.accept()
    depois = services.runs.get(run.id)
    assert depois.item.name == "Anel" and depois.notes == "b"
    assert depois.completed_at == run.completed_at
    trilha = services.audit.history("run", run.id)
    assert [h.action for h in trilha] == ["create", "update"]


def test_dialogo_de_correcao_mantem_item_inativo_do_registro(qapp, services, seeded):
    dungeons, items = seeded
    run = services.runs.register(dungeons[0].id, items[0].id)
    services.items.set_active(items[0].id, False)
    dialog = RunEditDialog(services, run)
    assert dialog.form.selected_item_id() == items[0].id
    dialog.form.notes.setPlainText("ajuste")
    dialog.accept()
    assert services.runs.get(run.id).notes == "ajuste"


def test_dialogo_de_item_lista_as_oito_categorias_e_exige_selecao(qapp, services, dialogs):
    masmorra = services.dungeons.create("Base", 1)
    dialog = ItemDialog(services.items, services.dungeons.list())
    rotulos = [dialog.category.itemText(i) for i in range(dialog.category.count())]
    assert rotulos == [
        "Armas",
        "Armaduras",
        "Acessórios",
        "Relíquias",
        "Recursos de amplificação",
        "Recursos de artesanato",
        "Consumíveis",
        "Barras preciosas",
    ]
    assert dialog.category.currentIndex() == -1
    dialog.name.setText("Poção")
    dialog.accept()
    assert "Categoria é obrigatória" in dialogs.errors[-1]
    assert services.items.list() == []
    dialog.category.setCurrentIndex(dialog.category.findData("consumables"))
    dialog.accept()
    assert "masmorra" in dialogs.errors[-1].lower()
    assert services.items.list() == []
    dialog.set_checked_dungeons({masmorra.id})
    dialog.accept()
    assert services.items.list()[0].category == "consumables"


def test_dialogo_de_item_edita_categoria(qapp, services):
    masmorra = services.dungeons.create("Base", 1)
    item = services.items.create("Barra", "crafting_resources", [masmorra.id])
    dialog = ItemDialog(services.items, services.dungeons.list(), item)
    assert dialog.category.currentData() == "crafting_resources"
    dialog.category.setCurrentIndex(dialog.category.findData("precious_bars"))
    dialog.accept()
    assert services.items.get(item.id).category == "precious_bars"
