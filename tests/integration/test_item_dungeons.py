"""Masmorras em que cada item pode ser obtido (dados SINTÉTICOS)."""

import json
from datetime import UTC, datetime

import pandas as pd
import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from openpyxl import load_workbook
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from dungeon_drop_analyzer.core.database import (
    create_db_engine,
    downgrade_database,
    upgrade_database,
)
from dungeon_drop_analyzer.models import Base
from dungeon_drop_analyzer.reports import (
    export_frequencies_csv,
    export_report_xlsx,
    export_statistics_csv,
)
from dungeon_drop_analyzer.services import (
    AnalyticsService,
    NotFoundError,
    Services,
    ValidationError,
)

AGORA = datetime(2026, 11, 19, 12, 0, tzinfo=UTC)


@pytest.fixture
def analytics(factory):
    return AnalyticsService(factory)


@pytest.fixture
def services(factory, clock):
    return Services.create(factory, clock)


@pytest.fixture
def mapa(dungeons, items):
    d = [dungeons.create(f"Masmorra {i}", i) for i in range(1, 4)]
    return d, items


def sql(engine, comando, **parametros):
    with engine.begin() as conn:
        conn.execute(text(comando), parametros)


def nomes(item):
    return [d.name for d in item.dungeons]


@pytest.mark.parametrize("valor", [[], None, "abc", [True], [1.5], ["1"], 7])
def test_item_exige_ao_menos_uma_masmorra_valida(mapa, valor):
    _, items = mapa
    with pytest.raises(ValidationError, match="masmorra"):
        items.create("X", "weapons", valor)
    assert items.list() == []


def test_masmorra_inexistente_e_rejeitada(mapa):
    _, items = mapa
    with pytest.raises(NotFoundError):
        items.create("X", "weapons", [999])
    assert items.list() == []


def test_item_guarda_masmorras_ordenadas_por_dificuldade_e_sem_repeticao(mapa):
    d, items = mapa
    item = items.create("Capa", "armor", [d[2].id, d[0].id, d[0].id])
    assert nomes(item) == ["Masmorra 1", "Masmorra 3"]
    assert nomes(items.get(item.id)) == ["Masmorra 1", "Masmorra 3"]


def test_item_pode_ser_de_todas_ou_de_uma_masmorra(mapa):
    d, items = mapa
    esfera = items.create("Esfera", "amplification_resources", [m.id for m in d])
    capa = items.create("Capa", "armor", [d[1].id])
    assert len(esfera.dungeons) == 3 and nomes(capa) == ["Masmorra 2"]


def test_edicao_das_masmorras_do_item_gera_auditoria(mapa, audit_trail):
    d, items = mapa
    item = items.create("Capa", "armor", [d[0].id])
    items.update(item.id, dungeon_ids=[d[0].id, d[1].id])
    sem_mudanca = items.update(item.id, dungeon_ids=[d[1].id, d[0].id])
    assert nomes(sem_mudanca) == ["Masmorra 1", "Masmorra 2"]
    historico = audit_trail.history("item", item.id)
    assert [h.action for h in historico] == ["create", "update"]
    assert json.loads(historico[0].new_data)["dungeon_ids"] == [d[0].id]
    assert json.loads(historico[1].old_data)["dungeon_ids"] == [d[0].id]
    assert json.loads(historico[1].new_data)["dungeon_ids"] == [d[0].id, d[1].id]


def test_edicao_exige_ao_menos_uma_masmorra_quando_informada(mapa):
    d, items = mapa
    item = items.create("Capa", "armor", [d[0].id])
    with pytest.raises(ValidationError, match="masmorra"):
        items.update(item.id, dungeon_ids=[])
    assert nomes(items.get(item.id)) == ["Masmorra 1"]


def test_nao_remove_masmorra_que_tem_incursoes_do_item(mapa, runs):
    d, items = mapa
    item = items.create("Capa", "armor", [d[0].id, d[1].id])
    runs.register(d[0].id, item.id)
    with pytest.raises(ValidationError, match=r"1 incursão\(ões\).*Masmorra 1"):
        items.update(item.id, dungeon_ids=[d[1].id])
    assert nomes(items.get(item.id)) == ["Masmorra 1", "Masmorra 2"]
    atualizado = items.update(item.id, dungeon_ids=[d[0].id])
    assert nomes(atualizado) == ["Masmorra 1"]


def test_item_legado_sem_masmorras_continua_editavel(mapa, engine):
    d, items = mapa
    item = items.create("Antigo", "weapons", [d[0].id])
    sql(engine, "DELETE FROM item_dungeons")
    assert items.get(item.id).dungeons == []
    assert items.set_active(item.id, False).is_active is False
    assert items.update(item.id, name="Antigo 2").name == "Antigo 2"
    assert items.get(item.id).dungeons == []


def test_registro_so_e_permitido_nas_masmorras_do_item(mapa, runs):
    d, items = mapa
    capa = items.create("Capa", "armor", [d[0].id])
    runs.register(d[0].id, capa.id)
    with pytest.raises(ValidationError, match="Masmorras do item: Masmorra 1"):
        runs.register(d[1].id, capa.id)
    assert runs.count() == 1


def test_item_sem_masmorras_definidas_pode_ser_registrado_em_qualquer_uma(mapa, runs, engine):
    d, items = mapa
    antigo = items.create("Antigo", "weapons", [d[0].id])
    sql(engine, "DELETE FROM item_dungeons")
    runs.register(d[2].id, antigo.id)
    assert runs.count() == 1


def test_correcao_valida_a_combinacao_masmorra_item(mapa, runs):
    d, items = mapa
    capa = items.create("Capa", "armor", [d[0].id])
    esfera = items.create("Esfera", "consumables", [m.id for m in d])
    run = runs.register(d[1].id, esfera.id)
    with pytest.raises(ValidationError, match="não pode ser obtido"):
        runs.update(run.id, item_id=capa.id)
    with pytest.raises(ValidationError, match="não pode ser obtido"):
        runs.update(run.id, item_id=capa.id, dungeon_id=d[1].id)
    assert runs.get(run.id).item.id == esfera.id
    corrigida = runs.update(run.id, dungeon_id=d[0].id, item_id=capa.id)
    assert (corrigida.dungeon.id, corrigida.item.id) == (d[0].id, capa.id)


def test_correcao_de_outros_campos_nao_revalida_incursao_antiga(mapa, runs, engine):
    d, items = mapa
    capa = items.create("Capa", "armor", [d[0].id, d[1].id])
    run = runs.register(d[1].id, capa.id)
    sql(engine, "DELETE FROM item_dungeons WHERE dungeon_id = :d", d=d[1].id)
    assert runs.update(run.id, notes="ajuste").notes == "ajuste"


def test_tabela_de_associacao_tem_chave_composta_e_restricoes(mapa, engine):
    d, items = mapa
    item = items.create("Capa", "armor", [d[0].id])
    with pytest.raises(IntegrityError):
        sql(engine, "INSERT INTO item_dungeons VALUES (:i, :d)", i=item.id, d=d[0].id)
    with pytest.raises(IntegrityError):
        sql(engine, "INSERT INTO item_dungeons VALUES (999, :d)", d=d[0].id)
    with pytest.raises(IntegrityError):
        sql(engine, "DELETE FROM dungeons WHERE id = :d", d=d[0].id)
    with pytest.raises(IntegrityError):
        sql(engine, "DELETE FROM items WHERE id = :i", i=item.id)


def test_migracao_0004_cria_tabela_sem_associar_itens_existentes(tmp_path):
    engine = create_db_engine(tmp_path / "legado.db")
    upgrade_database(engine, "0003")
    sql(
        engine,
        "INSERT INTO items (name, category, created_at, updated_at) "
        "VALUES ('Antigo', 'weapons', '2026-01-01', '2026-01-01')",
    )
    upgrade_database(engine)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar() == "0004"
        assert conn.execute(text("SELECT count(*) FROM items")).scalar() == 1
        assert conn.execute(text("SELECT count(*) FROM item_dungeons")).scalar() == 0
        assert compare_metadata(MigrationContext.configure(conn), Base.metadata) == []
    downgrade_database(engine, "0003")
    with engine.connect() as conn:
        tabelas = {r[0] for r in conn.execute(text("SELECT name FROM sqlite_master"))}
    assert "item_dungeons" not in tabelas
    engine.dispose()


def registrar(runs, dungeon, item, quantidade):
    for k in range(quantidade):
        runs.register(
            dungeon.id, item.id, completed_at=datetime(2026, 3, 1 + k % 20, 10, k, tzinfo=UTC)
        )


@pytest.fixture
def restrito(mapa, runs):
    d, items = mapa
    a = items.create("A", "weapons", [m.id for m in d])
    a2 = items.create("A2", "armor", [m.id for m in d])
    b = items.create("B", "relics", [d[0].id, d[1].id])
    c = items.create("C", "consumables", [d[2].id])
    registrar(runs, d[0], a, 10)
    registrar(runs, d[0], a2, 10)
    registrar(runs, d[0], b, 30)
    registrar(runs, d[1], a, 11)
    registrar(runs, d[1], a2, 9)
    registrar(runs, d[1], b, 30)
    registrar(runs, d[2], a, 10)
    registrar(runs, d[2], a2, 10)
    registrar(runs, d[2], c, 30)
    return d, (a, a2, b, c)


def test_analise_considera_a_disponibilidade_dos_itens(analytics, restrito):
    d, (a, a2, b, c) = restrito
    r = analytics.analyze(n_sim=300)
    assert [i.name for i in r.items] == ["A", "A2", "B", "C"]
    assert r.availability.tolist() == [
        [True, True, True, False],
        [True, True, True, False],
        [True, True, False, True],
    ]
    assert [i.name for i in r.common_items] == ["A", "A2"]
    assert r.overall.n == 60 and r.overall.method == "chi2" and r.overall.p_value > 0.5
    por_item = {x.item: x for x in r.per_item}
    assert por_item["A"].dungeons == ["Masmorra 1", "Masmorra 2", "Masmorra 3"]
    assert por_item["B"].dungeons == ["Masmorra 1", "Masmorra 2"]
    assert por_item["B"].global_test.p_value == pytest.approx(1.0)
    assert por_item["C"].global_test.method == "indefinido"
    assert por_item["C"].proportions[0].x == 30
    assert r.undefined_items == [] and r.inconsistent_runs == []


def test_tendencia_por_dificuldade_ignora_niveis_sem_o_item(analytics, restrito):
    r = analytics.analyze(n_sim=100)
    grupos = {t.item.name: [(g.difficulty, g.x, g.n) for g in t.groups] for t in r.trends}
    assert grupos["A"] == [(1, 10, 50), (2, 11, 50), (3, 10, 50)]
    assert grupos["B"] == [(1, 30, 50), (2, 30, 50)]
    assert grupos["C"] == [(3, 30, 50)]
    tendencias = {t.item.name: t for t in r.trends}
    assert tendencias["C"].result.p_value is None
    assert tendencias["B"].result.p_value == pytest.approx(1.0)


def test_dashboard_expoe_disponibilidade(analytics, restrito):
    d, (a, a2, b, c) = restrito
    dados = analytics.dashboard()
    assert dados.availability[b.id] == {d[0].id, d[1].id}
    assert dados.is_available(b.id, d[0].id) and not dados.is_available(b.id, d[2].id)
    assert dados.is_available(a.id, d[2].id)
    assert dados.undefined_items == [] and dados.inconsistent_runs == []


def test_incursoes_fora_das_masmorras_do_item_sao_sinalizadas_e_excluidas(
    analytics, restrito, engine
):
    d, (a, a2, b, c) = restrito
    sql(
        engine,
        "DELETE FROM item_dungeons WHERE item_id = :i AND dungeon_id = :d",
        i=b.id,
        d=d[1].id,
    )
    r = analytics.analyze(n_sim=100)
    (inconsistente,) = r.inconsistent_runs
    assert (inconsistente.dungeon.name, inconsistente.item.name, inconsistente.count) == (
        "Masmorra 2",
        "B",
        30,
    )
    item_b = next(x for x in r.per_item if x.item == "B")
    assert item_b.dungeons == ["Masmorra 1"] and item_b.global_test.method == "indefinido"
    assert analytics.dashboard().inconsistent_runs[0].count == 30


def test_itens_sem_masmorras_definidas_sao_sinalizados_e_tratados_como_disponiveis(
    analytics, restrito, engine
):
    d, (a, a2, b, c) = restrito
    sql(engine, "DELETE FROM item_dungeons WHERE item_id = :i", i=a2.id)
    r = analytics.analyze(n_sim=100)
    assert [i.name for i in r.undefined_items] == ["A2"]
    assert [i.name for i in analytics.dashboard().undefined_items] == ["A2"]
    item = next(x for x in r.per_item if x.item == "A2")
    assert item.dungeons == ["Masmorra 1", "Masmorra 2", "Masmorra 3"]
    assert [i.name for i in r.common_items] == ["A", "A2"]


def ler(caminho):
    return pd.read_csv(caminho, sep=";", decimal=",", encoding="utf-8-sig")


def test_csv_de_frequencias_omite_combinacoes_impossiveis(services, restrito, tmp_path):
    export_frequencies_csv(services, None, tmp_path / "freq.csv", AGORA)
    df = ler(tmp_path / "freq.csv")
    assert len(df) == 9
    assert set(df["item_disponivel_na_masmorra"]) == {"Sim"}
    assert df[(df["item"] == "B") & (df["masmorra"] == "Masmorra 3")].empty
    assert df[(df["item"] == "C") & (df["masmorra"] == "Masmorra 1")].empty
    linha = df[(df["item"] == "B") & (df["masmorra"] == "Masmorra 1")].iloc[0]
    assert linha["obtencoes"] == 30 and linha["incursoes_masmorra"] == 50
    assert linha["proporcao"] == pytest.approx(0.6)


def test_csv_de_frequencias_mantem_incursoes_inconsistentes_marcadas(
    services, restrito, engine, tmp_path
):
    d, (a, a2, b, c) = restrito
    sql(
        engine,
        "DELETE FROM item_dungeons WHERE item_id = :i AND dungeon_id = :d",
        i=b.id,
        d=d[1].id,
    )
    export_frequencies_csv(services, None, tmp_path / "freq.csv", AGORA)
    df = ler(tmp_path / "freq.csv")
    fora = df[df["item_disponivel_na_masmorra"] == "Não"]
    assert len(fora) == 1
    assert (fora.iloc[0]["item"], fora.iloc[0]["masmorra"], fora.iloc[0]["obtencoes"]) == (
        "B",
        "Masmorra 2",
        30,
    )


def test_csv_de_resultados_restringe_comparacoes_e_informa_masmorras(services, restrito, tmp_path):
    export_statistics_csv(services, None, tmp_path / "estat.csv", AGORA)
    df = ler(tmp_path / "estat.csv")
    geral = df[df["escopo"] == "Distribuição completa"].iloc[0]
    assert geral["comparacao"] == "3 masmorras × 2 itens comuns"
    b = df[(df["escopo"] == "Item (global)") & (df["item"] == "B")].iloc[0]
    assert b["masmorras_consideradas"] == "Masmorra 1, Masmorra 2"
    c = df[(df["escopo"] == "Item (global)") & (df["item"] == "C")].iloc[0]
    assert pd.isna(c["p_bruto"]) and c["masmorras_consideradas"] == "Masmorra 3"
    pares = df[df["escopo"] == "Item (par de masmorras)"]
    assert len(pares) == 3 + 3 + 1
    assert set(pares[pares["item"] == "B"]["comparacao"]) == {"Masmorra 1 vs Masmorra 2"}
    assert pares[pares["item"] == "C"].empty


def test_xlsx_deixa_celulas_indisponiveis_vazias_e_esperado_so_com_itens_comuns(
    services, restrito, tmp_path
):
    export_report_xlsx(services, None, tmp_path / "r.xlsx", AGORA)
    wb = load_workbook(tmp_path / "r.xlsx")
    observado = wb["Distribuição observada"]
    cabecalho = [c.value for c in observado[1]]
    assert cabecalho == ["masmorra", "A", "A2", "B", "C"]
    primeira = {cabecalho[i]: observado.cell(row=2, column=i + 1).value for i in range(5)}
    assert primeira["B"] == 30 and primeira["C"] is None
    terceira = {cabecalho[i]: observado.cell(row=4, column=i + 1).value for i in range(5)}
    assert terceira["B"] is None and terceira["C"] == 30
    esperado = wb["Distribuição esperada"]
    assert [c.value for c in esperado[1]] == ["masmorra", "A", "A2"]


def test_resumo_do_xlsx_avisa_sobre_itens_sem_masmorras(services, restrito, engine, tmp_path):
    d, (a, a2, b, c) = restrito
    sql(engine, "DELETE FROM item_dungeons WHERE item_id = :i", i=a2.id)
    export_report_xlsx(services, None, tmp_path / "r.xlsx", AGORA)
    linhas = [
        (r[0].value, r[1].value)
        for r in load_workbook(tmp_path / "r.xlsx")["Resumo"].iter_rows(min_row=2)
    ]
    avisos = [valor for campo, valor in linhas if campo and campo.startswith("Aviso: itens sem")]
    assert avisos == ["A2"]


def test_item_nao_pode_ser_criado_com_masmorra_inativa(mapa, dungeons):
    d, items = mapa
    dungeons.set_active(d[1].id, False)
    with pytest.raises(ValidationError, match="Masmorra 2.*inativa"):
        items.create("Capa", "armor", [d[0].id, d[1].id])
    assert items.list() == []


def test_nao_vincula_masmorra_inativa_na_edicao_mas_preserva_vinculos_existentes(mapa, dungeons):
    d, items = mapa
    item = items.create("Capa", "armor", [d[0].id, d[1].id])
    dungeons.set_active(d[1].id, False)
    dungeons.set_active(d[2].id, False)
    with pytest.raises(ValidationError, match="Masmorra 3.*inativa"):
        items.update(item.id, dungeon_ids=[d[0].id, d[1].id, d[2].id])
    assert nomes(items.get(item.id)) == ["Masmorra 1", "Masmorra 2"]
    mantido = items.update(item.id, name="Capa 2", dungeon_ids=[d[0].id, d[1].id])
    assert mantido.name == "Capa 2" and nomes(mantido) == ["Masmorra 1", "Masmorra 2"]
    dungeons.set_active(d[2].id, True)
    ampliado = items.update(item.id, dungeon_ids=[d[0].id, d[1].id, d[2].id])
    assert len(ampliado.dungeons) == 3
