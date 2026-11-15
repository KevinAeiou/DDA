"""Teste de tendência de Cochran-Armitage e Monte Carlo vetorizado (dados sintéticos)."""

import numpy as np
import pytest

from dungeon_drop_analyzer.statistics import homogeneity_test, trend_test


def test_exemplo_de_referencia_de_agresti():
    r = trend_test([48, 38, 5, 1, 1], [17066, 14464, 788, 126, 37], [0, 0.5, 1.5, 4, 7])
    assert r.z**2 == pytest.approx(6.6, abs=0.1)
    assert r.p_value == pytest.approx(0.01, abs=0.001)
    assert r.direction == "crescente" and r.groups == 5 and r.n == 17066 + 14464 + 788 + 126 + 37


def test_direcao_decrescente_e_invariancia_a_escala_dos_escores():
    x, n = [30, 20, 10, 5], [100, 100, 100, 100]
    a = trend_test(x, n, [1, 2, 3, 4])
    b = trend_test(x, n, [10, 20, 30, 40])
    c = trend_test(x, n, [5, 6, 7, 8])
    assert a.direction == "decrescente" and a.z < 0
    assert a.z == pytest.approx(b.z) and a.z == pytest.approx(c.z)
    inv = trend_test(x[::-1], n[::-1], [1, 2, 3, 4])
    assert inv.z == pytest.approx(-a.z)
    assert inv.p_value == pytest.approx(a.p_value)


def test_sem_tendencia_p_proximo_de_um():
    r = trend_test([10, 10, 10, 10], [100, 100, 100, 100], [1, 2, 3, 4])
    assert r.z == pytest.approx(0.0)
    assert r.p_value == pytest.approx(1.0)


def test_grupos_vazios_sao_descartados_e_casos_indefinidos():
    r = trend_test([5, 0, 20], [50, 0, 50], [1, 2, 3])
    assert r.groups == 2 and r.p_value is not None
    for x, n, s in [([5], [50], [1]), ([5, 6], [50, 60], [2, 2]), ([0, 0], [50, 60], [1, 2])]:
        indef = trend_test(x, n, s)
        assert indef.p_value is None and indef.direction == "indefinida" and indef.rationale
    assert trend_test([50, 60], [50, 60], [1, 2]).p_value is None


def test_entradas_invalidas():
    with pytest.raises(ValueError):
        trend_test([1, 2], [10], [1, 2])
    with pytest.raises(ValueError):
        trend_test([11], [10], [1])


def test_monte_carlo_vetorizado_e_reprodutivel_e_aproxima_chi2():
    tabela = np.array([[40, 35, 25], [30, 40, 30], [50, 30, 20], [35, 35, 30], [20, 50, 30]])
    a = homogeneity_test(tabela, method="monte_carlo", n_sim=20000, seed=11)
    b = homogeneity_test(tabela, method="monte_carlo", n_sim=20000, seed=11)
    qui = homogeneity_test(tabela)
    assert a.p_value == b.p_value
    assert a.n_sim == 20000 and a.seed == 11
    assert a.p_value == pytest.approx(qui.p_value, abs=0.02)


def test_monte_carlo_limites_do_valor_p():
    iguais = np.array([[3, 2], [3, 2], [3, 2]])
    r = homogeneity_test(iguais, method="monte_carlo", n_sim=500, seed=1)
    assert r.p_value == pytest.approx(1.0)
    r2 = homogeneity_test(np.array([[9, 0], [0, 9]]), method="monte_carlo", n_sim=500, seed=1)
    assert 1 / 501 <= r2.p_value < 0.01
