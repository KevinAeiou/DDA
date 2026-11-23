"""Dashboard e análise estatística sobre o histórico (dados SINTÉTICOS)."""

from datetime import UTC, datetime

import pytest

from dungeon_drop_analyzer.repositories import RunFilter
from dungeon_drop_analyzer.services.analytics import interpret
from dungeon_drop_analyzer.statistics import homogeneity_test, wilson_interval


@pytest.fixture
def analytics(factory):
    from dungeon_drop_analyzer.services import AnalyticsService

    return AnalyticsService(factory)


def registrar(runs, dungeon, item, quantidade, dia=1, **extra):
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
    registrar(runs, ds[0], its[0], 30, dia=1)
    registrar(runs, ds[0], its[1], 10, dia=2)
    registrar(runs, ds[1], its[0], 10, dia=2)
    registrar(runs, ds[1], its[1], 30, dia=3)
    registrar(runs, ds[2], its[0], 20, dia=3, bonus_status="yes")
    registrar(runs, ds[2], its[1], 20, dia=4, bonus_status="yes")
    return ds, its


def test_dashboard_vazio(analytics, seeded):
    dados = analytics.dashboard()
    assert dados.total_runs == 0 and dados.distinct_items == 0
    assert dados.most_frequent == [] and dados.least_frequent == []
    assert all(c.runs == 0 for c in dados.dungeon_counts) and dados.timeline == {}
    assert {c.count for c in dados.item_counts} == {0}


def test_dashboard_totais_distribuicao_e_empates(analytics, cenario):
    ds, its = cenario
    dados = analytics.dashboard()
    assert dados.total_runs == 120 and dados.distinct_items == 2
    por_masmorra = {c.dungeon.name: c.runs for c in dados.dungeon_counts}
    assert por_masmorra["Masmorra 1"] == 40 and por_masmorra["Masmorra 4"] == 0
    contagens = {c.item.name: c.count for c in dados.item_counts}
    assert contagens == {"Item A": 60, "Item B": 60, "Item C": 0}
    assert sum(c.share for c in dados.item_counts) == pytest.approx(1.0)
    assert {c.item.name for c in dados.most_frequent} == {"Item A", "Item B"}
    assert [c.item.name for c in dados.least_frequent] == ["Item C"]
    assert dados.least_frequent[0].count == 0


def test_dashboard_categorias_e_evolucao_temporal(analytics, cenario):
    ds, _ = cenario
    dados = analytics.dashboard()
    assert dados.category_counts[ds[0].id] == {"weapons": 40}
    serie = dados.timeline["Masmorra 1"]
    assert [total for _, total in serie] == [30, 40]
    assert serie[0][0] <= serie[1][0]


def test_dashboard_respeita_filtros(analytics, cenario):
    ds, its = cenario
    assert analytics.dashboard(RunFilter(dungeon_ids=[ds[0].id])).total_runs == 40
    assert analytics.dashboard(RunFilter(bonus_status="yes")).total_runs == 40
    assert analytics.dashboard(RunFilter(difficulties=[2])).total_runs == 40
    so_a = analytics.dashboard(RunFilter(item_ids=[its[0].id]))
    assert so_a.total_runs == 60 and so_a.distinct_items == 1


def test_item_inativo_com_registros_continua_no_dashboard(analytics, cenario, items):
    _, its = cenario
    items.set_active(its[0].id, False)
    items.set_active(its[2].id, False)
    nomes = {c.item.name for c in analytics.dashboard().item_counts}
    assert nomes == {"Item A", "Item B"}


def test_analise_confere_com_o_nucleo_estatistico(analytics, cenario):
    ds, its = cenario
    r = analytics.analyze(n_sim=500)
    assert r.analyzable and r.sample_size == 120
    assert [d.name for d in r.dungeons] == ["Masmorra 1", "Masmorra 2", "Masmorra 3"]
    assert [i.name for i in r.items] == ["Item A", "Item B"]
    assert r.matrix.tolist() == [[30, 10], [10, 30], [20, 20]]
    esperado = homogeneity_test(r.matrix)
    assert r.overall.p_value == pytest.approx(esperado.p_value)
    assert r.overall.method == "chi2"
    item_a = next(a for a in r.per_item if a.item == "Item A")
    prop = item_a.proportions[0]
    assert (prop.x, prop.n) == (30, 40)
    assert prop.ci == pytest.approx(wilson_interval(30, 40))
    assert prop.insufficient is True
    assert item_a.p_holm_across_items is not None


def test_analise_tendencia_por_nivel_de_dificuldade(analytics, cenario):
    r = analytics.analyze(n_sim=200)
    assert [row.difficulty for row in r.levels] == [1, 2, 3]
    assert [row.runs for row in r.levels] == [40, 40, 40]
    assert r.levels[0].counts == {r.items[0].id: 30, r.items[1].id: 10}
    por_item = {t.item.name: t for t in r.trends}
    assert por_item["Item A"].result.direction == "decrescente"
    assert por_item["Item B"].result.direction == "crescente"
    assert por_item["Item A"].p_holm >= por_item["Item A"].result.p_value


def test_analise_agrupa_masmorras_com_mesma_dificuldade(analytics, runs, seeded, dungeons):
    ds, its = seeded
    dungeons.update(ds[1].id, difficulty=1)
    registrar(runs, ds[0], its[0], 5)
    registrar(runs, ds[1], its[1], 7)
    registrar(runs, ds[2], its[0], 3)
    r = analytics.analyze(n_sim=100)
    nivel1 = r.levels[0]
    assert nivel1.difficulty == 1 and nivel1.runs == 12
    assert set(nivel1.dungeons) == {"Masmorra 1", "Masmorra 2"}


def test_analise_sem_dados_suficientes(analytics, seeded, runs):
    ds, its = seeded
    assert analytics.analyze().analyzable is False
    registrar(runs, ds[0], its[0], 5)
    r = analytics.analyze()
    assert r.analyzable is False and r.sample_size == 5
    assert r.trends[0].result.p_value is None


def test_analise_com_amostra_esparsa_usa_monte_carlo_reprodutivel(analytics, runs, seeded):
    ds, its = seeded
    registrar(runs, ds[0], its[0], 3)
    registrar(runs, ds[0], its[1], 1)
    registrar(runs, ds[1], its[1], 3)
    registrar(runs, ds[1], its[2], 1)
    registrar(runs, ds[2], its[2], 2)
    registrar(runs, ds[2], its[0], 1)
    a = analytics.analyze(n_sim=2000, seed=5)
    b = analytics.analyze(n_sim=2000, seed=5)
    assert a.overall.method == "monte_carlo" and a.overall.p_value == b.overall.p_value
    assert a.overall.n_sim == 2000 and a.overall.seed == 5


def test_interpretacao():
    assert "Não foi detectada" in interpret(0.2) and "não prova" in interpret(0.2)
    assert "Foi detectada" in interpret(0.01) and "causalidade" in interpret(0.01)
    assert "indefinido" in interpret(None)
    assert "Foi detectada" in interpret(0.04, alpha=0.05)
    assert "Não foi detectada" in interpret(0.04, alpha=0.01)


def test_dashboard_mostra_apenas_masmorras_ativas(analytics, cenario, dungeons):
    ds, its = cenario
    dungeons.set_active(ds[1].id, False)
    dados = analytics.dashboard()
    assert [c.dungeon.id for c in dados.dungeon_counts] == [d.id for d in ds if d.id != ds[1].id]
    assert dados.total_runs == 40 + 40
    assert set(dados.timeline) == {ds[0].name, ds[2].name}
    assert ds[1].name not in {c.dungeon.name for c in dados.dungeon_counts}
    assert all(d != ds[1].id for d, _ in dados.cells)
    assert {c.item.id: c.count for c in dados.item_counts}[its[0].id] == 30 + 20
    assert analytics.dashboard(RunFilter(dungeon_ids=[ds[1].id])).total_runs == 0
    dungeons.set_active(ds[1].id, True)
    assert analytics.dashboard().total_runs == 120


def test_analise_continua_considerando_masmorras_inativas(analytics, cenario, dungeons):
    ds, _ = cenario
    dungeons.set_active(ds[1].id, False)
    assert ds[1].name in [d.name for d in analytics.analyze().dungeons]


def test_dashboard_traz_intervalo_de_wilson_por_item(analytics, cenario):
    from dungeon_drop_analyzer.statistics import wilson_interval

    dados = analytics.dashboard()
    por_item = {c.item.name: c for c in dados.item_counts}
    contagem = por_item["Item A"]
    assert contagem.count == 60 and contagem.ci == wilson_interval(60, 120)
    assert por_item["Item C"].ci == wilson_interval(0, 120)
    assert analytics.dashboard(RunFilter(dungeon_ids=[99999])).item_counts[0].ci is None


def test_cobertura_por_masmorra(analytics, cenario, runs):
    from dungeon_drop_analyzer.statistics import runs_for_absent_limit, runs_for_margin

    ds, its = cenario
    registrar(runs, ds[3], its[0], 1, dia=5)
    registrar(runs, ds[3], its[1], 1, dia=5)
    registrar(runs, ds[3], its[0], 2, dia=6)
    linhas = {c.dungeon.id: c for c in analytics.dashboard().coverage}
    primeira = linhas[ds[0].id]
    assert primeira.runs == 40 and primeira.registered_items == 3
    assert primeira.seen_registered == 2 and primeira.unseen_registered == 1
    assert primeira.singletons == 0 and primeira.unseen_chance == 0.0
    assert primeira.top_item.name == "Item A" and primeira.top_share == pytest.approx(0.75)
    assert primeira.absent_upper == pytest.approx(3.8415 / (40 + 3.8415), abs=1e-3)
    assert primeira.missing_for_absent_limit(0.01) == runs_for_absent_limit(0.01) - 40
    assert primeira.missing_for_margin(0.02) == runs_for_margin(0.75, 0.02) - 40
    assert primeira.missing_for_absent_limit(0.5) == 0
    esparsa = linhas[ds[3].id]
    assert esparsa.runs == 4 and esparsa.singletons == 1
    assert esparsa.unseen_chance == pytest.approx(0.25)
    vazia = linhas[ds[4].id]
    assert vazia.runs == 0 and vazia.unseen_chance is None and vazia.absent_upper is None
    assert vazia.top_share is None and vazia.missing_for_margin(0.02) is None
    assert vazia.missing_for_absent_limit(0.01) == runs_for_absent_limit(0.01)


def test_cobertura_considera_so_itens_ativos_e_disponiveis(analytics, cenario, items):
    ds, its = cenario
    items.set_active(its[2].id, False)
    linha = next(c for c in analytics.dashboard().coverage if c.dungeon.id == ds[0].id)
    assert linha.registered_items == 2 and linha.unseen_registered == 0


def test_convergencia_acumula_na_ordem_cronologica(analytics, cenario):
    from dungeon_drop_analyzer.statistics import wilson_interval

    ds, its = cenario
    serie = analytics.convergence(ds[0].id, its[0].id)
    assert serie.runs == 40 and serie.final_hits == 30
    assert serie.final_proportion == pytest.approx(0.75)
    assert list(serie.hits[:3]) == [1, 2, 3]
    assert serie.final_interval == pytest.approx(wilson_interval(30, 40))
    assert serie.margin_at(10) > serie.final_margin
    assert serie.dungeon_name == ds[0].name and serie.item_label == its[0].name


def test_convergencia_respeita_filtros_e_trata_serie_vazia(analytics, cenario):
    ds, its = cenario
    so_bonus = analytics.convergence(ds[2].id, its[0].id, RunFilter(bonus_status="yes"))
    assert so_bonus.runs == 40 and so_bonus.final_hits == 20
    vazia = analytics.convergence(ds[0].id, its[0].id, RunFilter(bonus_status="yes"))
    assert vazia.runs == 0 and vazia.final_proportion is None and vazia.final_margin is None
