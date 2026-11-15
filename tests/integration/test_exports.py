"""Exportações CSV/XLSX (dados SINTÉTICOS)."""

from datetime import UTC, datetime

import pandas as pd
import pytest
from openpyxl import load_workbook

from dungeon_drop_analyzer.reports import (
    export_frequencies_csv,
    export_history_csv,
    export_report_xlsx,
    export_statistics_csv,
)
from dungeon_drop_analyzer.repositories import RunFilter
from dungeon_drop_analyzer.services import ExportError, Services

AGORA = datetime(2026, 11, 14, 18, 30, 5, tzinfo=UTC)


@pytest.fixture
def services(factory, clock):
    return Services.create(factory, clock)


def ler(caminho):
    return pd.read_csv(caminho, sep=";", decimal=",", encoding="utf-8-sig")


def registrar(runs, dungeon, item, quantidade, dia, **extra):
    for k in range(quantidade):
        runs.register(
            dungeon.id,
            item.id,
            completed_at=datetime(2026, 3, dia, 10, k % 60, tzinfo=UTC),
            **extra,
        )


@pytest.fixture
def cenario(runs, seeded):
    ds, its = seeded
    registrar(runs, ds[0], its[0], 30, 1, notes="obs; com ponto e vírgula", game_version="1.0")
    registrar(runs, ds[0], its[1], 10, 2)
    registrar(runs, ds[1], its[0], 10, 2, bonus_status="yes")
    registrar(runs, ds[1], its[1], 30, 3)
    registrar(runs, ds[2], its[0], 20, 3)
    registrar(runs, ds[2], its[1], 20, 4)
    return ds, its


def test_csv_do_historico_tem_uma_linha_por_incursao_e_formato_pt_br(services, cenario, tmp_path):
    resultado = export_history_csv(services, None, tmp_path / "hist.csv", AGORA)
    assert resultado.rows == 120 and resultado.exported_at == AGORA
    bruto = (tmp_path / "hist.csv").read_bytes()
    assert bruto.startswith(b"\xef\xbb\xbf")
    assert b";" in bruto.splitlines()[0]
    df = ler(tmp_path / "hist.csv")
    assert len(df) == 120
    assert list(df.columns)[:4] == ["id", "data_hora_local", "data_hora_utc", "masmorra"]
    assert df["exportado_em"].nunique() == 1
    assert set(df["bonus_de_drop"]) == {"Sim", "Desconhecido"}
    assert set(df["categoria"]) == {"Armas"}
    assert "obs; com ponto e vírgula" in set(df["observacoes"].dropna())
    assert df["data_hora_utc"].iloc[0] == "2026-03-01 10:00:00"
    assert df["data_hora_utc"].is_monotonic_increasing


def test_csv_do_historico_respeita_filtros(services, cenario, tmp_path):
    ds, its = cenario
    flt = RunFilter(dungeon_ids=[ds[1].id], bonus_status="yes")
    resultado = export_history_csv(services, flt, tmp_path / "f.csv", AGORA)
    df = ler(tmp_path / "f.csv")
    assert resultado.rows == len(df) == 10
    assert set(df["masmorra"]) == {"Masmorra 2"} and set(df["item"]) == {"Item A"}


def test_csv_de_frequencias_confere_com_o_historico(services, cenario, tmp_path):
    export_frequencies_csv(services, None, tmp_path / "freq.csv", AGORA)
    df = ler(tmp_path / "freq.csv")
    assert len(df) == 6
    linha = df[(df["masmorra"] == "Masmorra 1") & (df["item"] == "Item A")].iloc[0]
    assert (linha["obtencoes"], linha["incursoes_masmorra"]) == (30, 40)
    assert linha["proporcao"] == pytest.approx(0.75)
    assert 0.59 < linha["ic95_inferior"] < 0.75 < linha["ic95_superior"] < 0.87
    assert linha["amostra_insuficiente"] == "Sim"
    assert df["exportado_em"].iloc[0] == "2026-11-14 " + df["exportado_em"].iloc[0][11:]


def test_csv_de_resultados_traz_metodo_amostra_e_valor_p(services, cenario, tmp_path):
    export_statistics_csv(services, None, tmp_path / "estat.csv", AGORA)
    df = ler(tmp_path / "estat.csv")
    assert set(df["escopo"]) == {
        "Distribuição completa",
        "Item (global)",
        "Item (par de masmorras)",
        "Tendência por dificuldade (exploratória)",
    }
    geral = df[df["escopo"] == "Distribuição completa"].iloc[0]
    assert geral["metodo"] == "Qui-quadrado de homogeneidade"
    assert geral["amostra_n"] == 120 and geral["graus_liberdade"] == 2
    assert 0 <= geral["p_bruto"] <= 1
    assert "Foi detectada" in geral["interpretacao"]
    itens = df[df["escopo"] == "Item (global)"]
    assert len(itens) == 2 and itens["p_ajustado_holm"].notna().all()
    assert (itens["p_ajustado_holm"] >= itens["p_bruto"]).all()
    assert set(itens["familia_holm"]) == {"2 itens"}
    pares = df[df["escopo"] == "Item (par de masmorras)"]
    assert len(pares) == 6
    assert pares["odds_ratio"].notna().all() and pares["diferenca_pp"].notna().all()
    assert (pares["p_ajustado_holm"] >= pares["p_bruto"]).all()
    assert pares["familia_holm"].str.startswith("3 comparações de").all()


def test_csvs_sem_dados_geram_apenas_cabecalho(services, seeded, tmp_path):
    for funcao, nome in (
        (export_history_csv, "h"),
        (export_frequencies_csv, "f"),
        (export_statistics_csv, "s"),
    ):
        resultado = funcao(services, None, tmp_path / f"{nome}.csv", AGORA)
        assert resultado.rows == 0
        assert len(ler(tmp_path / f"{nome}.csv")) == 0


def test_xlsx_consolidado_tem_abas_resumo_e_formatacao(services, cenario, tmp_path):
    ds, _ = cenario
    flt = RunFilter(difficulties=[1, 2, 3])
    resultado = export_report_xlsx(services, flt, tmp_path / "relatorio.xlsx", AGORA)
    assert resultado.rows == 120
    wb = load_workbook(tmp_path / "relatorio.xlsx")
    assert wb.sheetnames == [
        "Resumo",
        "Histórico",
        "Frequências",
        "Resultados estatísticos",
        "Distribuição observada",
        "Distribuição esperada",
    ]
    resumo = {row[0].value: row[1].value for row in wb["Resumo"].iter_rows(min_row=2)}
    assert resumo["Incursões na amostra (n)"] == "120"
    assert resumo["Exportado em"].startswith("2026-11-14")
    assert resumo["  Dificuldades"] == "1, 2, 3"
    assert "Limitação" in [row[0].value for row in wb["Resumo"].iter_rows(min_row=2)]
    historico = wb["Histórico"]
    assert historico.max_row == 121 and historico["A1"].font.bold and historico.freeze_panes == "A2"
    freq = wb["Frequências"]
    cabecalho = [c.value for c in freq[1]]
    coluna = cabecalho.index("proporcao") + 1
    assert freq.cell(row=2, column=coluna).number_format == "0.00%"
    esperada = wb["Distribuição esperada"]
    assert esperada["B2"].value == pytest.approx(20.0)


def test_xlsx_resumo_registra_filtros_e_sem_filtros(services, cenario, tmp_path):
    export_report_xlsx(services, None, tmp_path / "a.xlsx", AGORA)
    linhas = {
        r[0].value: r[1].value
        for r in load_workbook(tmp_path / "a.xlsx")["Resumo"].iter_rows(min_row=2)
    }
    assert linhas["Filtros aplicados"] == "Nenhum"
    export_report_xlsx(services, RunFilter(game_version="1.0"), tmp_path / "b.xlsx", AGORA)
    linhas = {
        r[0].value: r[1].value
        for r in load_workbook(tmp_path / "b.xlsx")["Resumo"].iter_rows(min_row=2)
    }
    assert linhas["  Versão do jogo"] == "1.0" and linhas["Incursões na amostra (n)"] == "30"


def test_exportacao_cria_pastas_e_informa_erro_de_destino(services, cenario, tmp_path):
    export_history_csv(services, None, tmp_path / "a" / "b" / "h.csv", AGORA)
    assert (tmp_path / "a" / "b" / "h.csv").exists()
    arquivo = tmp_path / "arquivo"
    arquivo.write_text("x")
    with pytest.raises(ExportError):
        export_history_csv(services, None, arquivo / "h.csv", AGORA)
    with pytest.raises(ExportError):
        export_report_xlsx(services, None, tmp_path, AGORA)
