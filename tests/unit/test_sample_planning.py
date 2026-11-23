"""Intervalos em série e metas de tamanho de amostra (valores SINTÉTICOS)."""

import numpy as np
import pytest

from dungeon_drop_analyzer.statistics import (
    absent_upper_bound,
    runs_for_absent_limit,
    runs_for_margin,
    unseen_probability,
    wilson_half_width,
    wilson_interval,
    wilson_series,
)


def test_serie_de_wilson_confere_com_o_intervalo_pontual():
    x = np.array([0, 1, 5, 12, 30])
    n = np.array([1, 10, 20, 40, 60])
    lower, upper = wilson_series(x, n)
    for k in range(len(x)):
        esperado = wilson_interval(int(x[k]), int(n[k]))
        assert lower[k] == pytest.approx(esperado[0])
        assert upper[k] == pytest.approx(esperado[1])


def test_serie_de_wilson_rejeita_entradas_invalidas():
    with pytest.raises(ValueError):
        wilson_series(np.array([1]), np.array([0]))
    with pytest.raises(ValueError):
        wilson_series(np.array([3]), np.array([2]))


@pytest.mark.parametrize(("p", "margem"), [(0.05, 0.01), (0.5, 0.02), (0.17, 0.05), (0.013, 0.005)])
def test_incursoes_para_margem_e_minimo(p, margem):
    n = runs_for_margin(p, margem)
    assert wilson_half_width(p, n) <= margem
    assert wilson_half_width(p, n - 1) > margem


def test_incursoes_para_margem_valores_conhecidos():
    assert 1800 <= runs_for_margin(0.05, 0.01) <= 1850
    assert 2350 <= runs_for_margin(0.5, 0.02) <= 2450


def test_incursoes_para_margem_valida_argumentos():
    with pytest.raises(ValueError):
        runs_for_margin(1.5, 0.01)
    with pytest.raises(ValueError):
        runs_for_margin(0.1, 0)


@pytest.mark.parametrize("limite", [0.005, 0.01, 0.02, 0.05])
def test_incursoes_para_limite_de_item_ausente_e_minimo(limite):
    n = runs_for_absent_limit(limite)
    assert absent_upper_bound(n) <= limite
    assert absent_upper_bound(n - 1) > limite


def test_limite_de_item_ausente_sem_incursoes():
    assert absent_upper_bound(0) is None
    assert absent_upper_bound(300) == pytest.approx(0.01264, abs=1e-4)
    with pytest.raises(ValueError):
        runs_for_absent_limit(0)


def test_good_turing():
    assert unseen_probability(9, 24) == pytest.approx(0.375)
    assert unseen_probability(0, 50) == 0.0
    assert unseen_probability(0, 0) is None
    with pytest.raises(ValueError):
        unseen_probability(5, 3)
