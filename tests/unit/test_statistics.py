"""Testes do núcleo estatístico. Todas as tabelas aqui são SINTÉTICAS (não são dados reais)."""

import numpy as np
import pytest
from scipy.stats import chi2_contingency
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.proportion import proportion_confint

from dungeon_drop_analyzer.statistics import (
    analyze_items,
    effect_size,
    holm_adjust,
    homogeneity_test,
    insufficient_sample,
    pairwise_tests,
    wilson_interval,
)
from dungeon_drop_analyzer.statistics.homogeneity import chi2_adequate, expected_counts


@pytest.mark.parametrize("x,n", [(0, 10), (1, 10), (5, 10), (10, 10), (7, 50), (123, 1000)])
def test_wilson_confere_com_statsmodels(x, n):
    low, high = wilson_interval(x, n)
    ref_low, ref_high = proportion_confint(x, n, alpha=0.05, method="wilson")
    assert low == pytest.approx(ref_low, abs=1e-12)
    assert high == pytest.approx(ref_high, abs=1e-12)


def test_wilson_valor_conhecido_zero_de_dez():
    low, high = wilson_interval(0, 10)
    assert low == 0.0
    assert high == pytest.approx(0.2775, abs=1e-4)


def test_wilson_n_zero_e_entradas_invalidas():
    assert wilson_interval(0, 0) is None
    with pytest.raises(ValueError):
        wilson_interval(5, 3)
    with pytest.raises(ValueError):
        wilson_interval(1, 3, confidence=1.0)


def test_amostra_insuficiente():
    assert insufficient_sample([49, 50, 0], min_n=50) == [True, False, True]


def test_holm_confere_com_statsmodels():
    p = [0.01, 0.04, 0.03, 0.005, 0.5, 0.2]
    esperado = multipletests(p, method="holm")[1]
    assert holm_adjust(p) == pytest.approx(list(esperado))


def test_holm_exemplo_manual_e_limite():
    assert holm_adjust([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])
    assert holm_adjust([0.6, 0.9]) == pytest.approx([1.0, 1.0])
    assert holm_adjust([]) == []


TABELA_GRANDE = np.array([[40, 35, 25], [30, 40, 30], [50, 30, 20], [35, 35, 30], [20, 50, 30]])
TABELA_ESPARSA = np.array([[3, 1, 0, 1], [0, 2, 1, 2], [4, 0, 0, 1], [1, 1, 2, 0], [0, 3, 1, 1]])


def test_chi2_confere_com_scipy():
    r = homogeneity_test(TABELA_GRANDE)
    ref = chi2_contingency(TABELA_GRANDE, correction=False)
    assert r.method == "chi2"
    assert r.statistic == pytest.approx(ref.statistic)
    assert r.dof == ref.dof == 8
    assert r.p_value == pytest.approx(ref.pvalue)
    assert r.n == TABELA_GRANDE.sum()


def test_auto_escolhe_monte_carlo_para_tabela_esparsa():
    ok, _ = chi2_adequate(expected_counts(TABELA_ESPARSA))
    assert not ok
    r = homogeneity_test(TABELA_ESPARSA, n_sim=2000, seed=7)
    assert r.method == "monte_carlo"
    assert r.n_sim == 2000 and r.seed == 7
    assert 0 < r.p_value <= 1
    assert "Cochran" in r.rationale


def test_monte_carlo_reprodutivel_e_sensivel_a_semente():
    a = homogeneity_test(TABELA_ESPARSA, n_sim=1000, seed=1)
    b = homogeneity_test(TABELA_ESPARSA, n_sim=1000, seed=1)
    assert a.p_value == b.p_value


def test_monte_carlo_aproxima_chi2_em_tabela_grande():
    mc = homogeneity_test(TABELA_GRANDE, method="monte_carlo", n_sim=5000, seed=3)
    chi = homogeneity_test(TABELA_GRANDE, method="chi2")
    assert mc.statistic == pytest.approx(chi.statistic)
    assert mc.p_value == pytest.approx(chi.p_value, abs=0.03)


def test_distribuicoes_identicas_nao_rejeitam():
    r = homogeneity_test(np.array([[20, 30, 50]] * 5))
    assert r.statistic == pytest.approx(0.0)
    assert r.p_value == pytest.approx(1.0)


def test_diferenca_forte_rejeita():
    r = homogeneity_test(np.array([[90, 10], [10, 90], [50, 50], [50, 50], [50, 50]]))
    assert r.p_value < 1e-10


def test_linhas_e_colunas_nulas_sao_removidas():
    tabela = np.array([[10, 20, 0], [15, 15, 0], [0, 0, 0], [12, 18, 0], [20, 10, 0]])
    r = homogeneity_test(tabela)
    assert r.dof == 3
    assert r.n == tabela.sum()


def test_tabela_degenerada_e_indefinida():
    r = homogeneity_test(np.array([[5, 0], [7, 0], [3, 0], [4, 0], [6, 0]]))
    assert r.method == "indefinido" and r.p_value is None


def test_metodo_invalido_e_tabela_negativa():
    with pytest.raises(ValueError):
        homogeneity_test(TABELA_GRANDE, method="xyz")
    with pytest.raises(ValueError):
        homogeneity_test(np.array([[1, -1], [2, 3]]))


def test_pairwise_holm_na_familia_do_item():
    x, n = [30, 10, 12, 11, 10], [100] * 5
    res = pairwise_tests(x, n, list("ABCDE"))
    assert len(res) == 10
    raw = [r.p_raw for r in res]
    assert [r.p_holm for r in res] == pytest.approx(holm_adjust(raw))
    assert all(r.p_holm >= r.p_raw for r in res)
    ab = next(r for r in res if (r.a, r.b) == ("A", "B"))
    assert ab.method == "chi2" and ab.p_holm < 0.01


def test_pairwise_usa_fisher_em_amostra_pequena_e_trata_indefinidos():
    res = pairwise_tests([0, 3, 0], [5, 6, 0], ["A", "B", "C"])
    por_par = {(r.a, r.b): r for r in res}
    assert por_par[("A", "B")].method == "fisher_exact"
    assert por_par[("A", "C")].p_raw is None and por_par[("A", "C")].p_holm is None


def test_effect_size_valores_manuais():
    e = effect_size(20, 100, 10, 100)
    assert e.diff_pp == pytest.approx(10.0)
    assert e.ratio == pytest.approx(2.0)
    assert e.odds_ratio == pytest.approx((20 * 90) / (80 * 10))
    assert not e.odds_ratio_corrected and e.notes == ()
    assert e.odds_ratio_ci[0] < e.odds_ratio < e.odds_ratio_ci[1]


def test_effect_size_zero_nao_gera_infinito():
    e = effect_size(5, 50, 0, 50)
    assert e.ratio is None
    assert e.odds_ratio_corrected and np.isfinite(e.odds_ratio)
    assert all(np.isfinite(e.odds_ratio_ci))
    assert len(e.notes) == 2


def test_effect_size_denominador_nulo():
    e = effect_size(0, 0, 3, 10)
    assert e.diff_pp is None and e.odds_ratio is None and e.notes


def test_analyze_items_estrutura_e_consistencia():
    dungeons = [f"D{i}" for i in range(1, 6)]
    items = ["I1", "I2", "I3"]
    overall, res = analyze_items(TABELA_GRANDE, dungeons, items, n_sim=500)
    assert overall.method == "chi2"
    assert [r.item for r in res] == items
    n = TABELA_GRANDE.sum(axis=1)
    for j, r in enumerate(res):
        for d, prop in enumerate(r.proportions):
            assert (prop.x, prop.n) == (TABELA_GRANDE[d, j], n[d])
            assert prop.p == pytest.approx(prop.x / prop.n)
            assert prop.ci[0] <= prop.p <= prop.ci[1]
            assert not prop.insufficient
        assert r.global_test.dof == 4
        assert len(r.pairwise) == 10 and len(r.effects) == 10
    raw = [r.global_test.p_value for r in res]
    assert [r.p_holm_across_items for r in res] == pytest.approx(holm_adjust(raw))


def test_analyze_items_sinaliza_amostra_insuficiente_e_valida_formato():
    _, res = analyze_items(TABELA_ESPARSA, list("ABCDE"), list("WXYZ"), n_sim=200)
    assert all(p.insufficient for p in res[0].proportions)
    with pytest.raises(ValueError):
        analyze_items(TABELA_ESPARSA, list("ABC"), list("WXYZ"))
