"""Relatórios, configurações e backup na interface (dados SINTÉTICOS)."""

from datetime import datetime

import pandas as pd
import pytest
from PySide6.QtCore import QDateTime

from dungeon_drop_analyzer.core.config import Settings, saved_data_dir
from dungeon_drop_analyzer.ui.pages import ReportsPage, SettingsPage
from dungeon_drop_analyzer.ui.windows import MainWindow


def registrar(services, dungeon, item, quantidade, dia):
    for k in range(quantidade):
        services.runs.register(
            dungeon.id, item.id, completed_at=datetime(2026, 3, dia, 10, k % 60), notes="x"
        )


@pytest.fixture
def cenario(services, seeded):
    ds, its = seeded
    registrar(services, ds[0], its[0], 12, 1)
    registrar(services, ds[0], its[1], 8, 2)
    registrar(services, ds[1], its[0], 6, 2)
    registrar(services, ds[1], its[1], 14, 3)
    return ds, its


def ler(caminho):
    return pd.read_csv(caminho, sep=";", decimal=",", encoding="utf-8-sig")


@pytest.fixture
def pagina_relatorios(qapp, services, settings, seeded):
    page = ReportsPage(services, settings)
    page.refresh()
    return page


def test_nome_padrao_dos_arquivos_de_exportacao():
    nome = ReportsPage.default_name("historico", "csv", datetime(2026, 11, 14, 9, 5, 7))
    assert nome == "dda-historico-20261114-090507.csv"


def test_exporta_historico_csv_e_informa_o_usuario(pagina_relatorios, cenario, dialogs, tmp_path):
    mensagens = []
    pagina_relatorios.message.connect(mensagens.append)
    dialogs.save_path = tmp_path / "meu_historico"
    pagina_relatorios.history_button.click()
    arquivo = tmp_path / "meu_historico.csv"
    assert arquivo.exists() and len(ler(arquivo)) == 40
    assert "40 linha(s)" in pagina_relatorios.result_label.text()
    assert mensagens and dialogs.infos and not dialogs.errors


def test_exportacao_respeita_filtros_da_pagina(pagina_relatorios, cenario, dialogs, tmp_path):
    filtros = pagina_relatorios.filters
    filtros.dungeon_combo.setCurrentIndex(filtros.dungeon_combo.findText("Masmorra 2"))
    dialogs.save_path = tmp_path / "filtrado.csv"
    pagina_relatorios.history_button.click()
    df = ler(tmp_path / "filtrado.csv")
    assert len(df) == 20 and set(df["masmorra"]) == {"Masmorra 2"}


def test_cancelar_a_selecao_de_arquivo_nao_exporta(pagina_relatorios, cenario, dialogs, tmp_path):
    dialogs.save_path = None
    pagina_relatorios.history_button.click()
    assert dialogs.infos == [] and dialogs.errors == []
    assert pagina_relatorios.result_label.text() == ""


def test_exporta_frequencias_resultados_e_xlsx(pagina_relatorios, cenario, dialogs, tmp_path):
    dialogs.save_path = tmp_path / "freq.csv"
    pagina_relatorios.frequencies_button.click()
    assert len(ler(tmp_path / "freq.csv")) == 4
    dialogs.save_path = tmp_path / "estat.csv"
    pagina_relatorios.statistics_button.click()
    assert "escopo" in ler(tmp_path / "estat.csv").columns
    dialogs.save_path = tmp_path / "relatorio"
    pagina_relatorios.report_button.click()
    assert (tmp_path / "relatorio.xlsx").exists()
    assert len(dialogs.infos) == 3


def test_exportacao_valida_periodo_e_mostra_erros_de_gravacao(
    pagina_relatorios, cenario, dialogs, tmp_path
):
    filtros = pagina_relatorios.filters
    filtros.use_from.setChecked(True)
    filtros.use_to.setChecked(True)
    filtros.date_from.setDateTime(QDateTime(2026, 5, 1, 0, 0, 0))
    filtros.date_to.setDateTime(QDateTime(2026, 4, 1, 0, 0, 0))
    dialogs.save_path = tmp_path / "x.csv"
    pagina_relatorios.history_button.click()
    assert "anterior" in dialogs.errors[-1] and not (tmp_path / "x.csv").exists()

    filtros.clear()
    arquivo = tmp_path / "arquivo"
    arquivo.write_text("x")
    dialogs.save_path = arquivo / "dentro.csv"
    pagina_relatorios.history_button.click()
    assert "Não foi possível" in dialogs.errors[-1]


@pytest.fixture
def pagina_config(qapp, services, settings):
    return SettingsPage(settings, services)


def test_configuracoes_mostram_todos_os_caminhos(pagina_config, settings):
    for caminho in (
        settings.data_dir,
        settings.db_path,
        settings.log_dir,
        settings.backup_dir,
        settings.export_dir,
    ):
        assert str(caminho) in pagina_config.details


def test_cria_backup_pela_interface(pagina_config, cenario, services, dialogs, tmp_path):
    dialogs.save_path = tmp_path / "meus" / "backup.db"
    pagina_config.backup_button.click()
    info = services.backup.validate(tmp_path / "meus" / "backup.db")
    assert (info.dungeons, info.items, info.runs) == (5, 3, 40)
    assert "Backup criado" in dialogs.infos[-1] and "40 incursão(ões)" in dialogs.infos[-1]
    dialogs.save_path = None
    pagina_config.backup_button.click()
    assert len(dialogs.infos) == 1


def test_restaura_backup_apos_confirmacao_com_copia_de_seguranca(
    pagina_config, cenario, services, settings, dialogs, tmp_path
):
    ds, its = cenario
    dialogs.save_path = tmp_path / "bom.db"
    pagina_config.backup_button.click()
    services.runs.delete(services.runs.list()[0].id)
    services.items.create("Extra", "relics")
    assert services.runs.count() == 39

    dialogs.open_path = tmp_path / "bom.db"
    dialogs.confirm_answer = False
    pagina_config.restore_button.click()
    assert services.runs.count() == 39
    assert "substituirá TODOS os dados atuais" in dialogs.confirmations[-1]
    assert "5 masmorra(s), 3 item(ns) e 40 incursão(ões)" in dialogs.confirmations[-1]

    dialogs.confirm_answer = True
    pagina_config.restore_button.click()
    assert services.runs.count() == 40 and len(services.items.list()) == 3
    seguranca = list(settings.backup_dir.glob("pre-restore-*.db"))
    assert len(seguranca) == 1
    assert services.backup.validate(seguranca[0]).runs == 39
    assert "Backup restaurado" in dialogs.infos[-1] and "pre-restore-" in dialogs.infos[-1]


def test_restauracao_de_arquivo_invalido_mostra_erro_e_preserva_dados(
    pagina_config, cenario, services, dialogs, tmp_path
):
    lixo = tmp_path / "lixo.db"
    lixo.write_bytes(b"nao sou um banco" * 400)
    dialogs.open_path = lixo
    pagina_config.restore_button.click()
    assert dialogs.errors and services.runs.count() == 40
    assert dialogs.confirmations == []


def test_altera_e_restaura_diretorio_de_dados(pagina_config, dialogs, tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "perfil"))
    monkeypatch.delenv("DDA_DATA_DIR", raising=False)
    novo = tmp_path / "outra_pasta"
    dialogs.directory = novo
    dialogs.confirm_answer = False
    pagina_config.change_dir_button.click()
    assert saved_data_dir() is None
    assert "NÃO são movidos" in dialogs.confirmations[-1]

    dialogs.confirm_answer = True
    pagina_config.change_dir_button.click()
    assert saved_data_dir() == novo
    assert Settings.load().data_dir == novo
    assert "Reinicie" in dialogs.infos[-1]

    pagina_config.reset_dir_button.click()
    assert saved_data_dir() is None
    assert Settings.load().data_dir == tmp_path / "perfil" / "DungeonDropAnalyzer"

    dialogs.directory = None
    pagina_config.change_dir_button.click()
    assert saved_data_dir() is None


def test_janela_principal_inclui_relatorios_e_configuracoes(qapp, services, settings):
    janela = MainWindow(services, settings)
    assert isinstance(janela.pages["Relatórios"], ReportsPage)
    assert isinstance(janela.pages["Configurações e backup"], SettingsPage)
    janela.open_page("Relatórios")
    assert janela.pages["Relatórios"].filters.dungeon_combo.count() == 1
