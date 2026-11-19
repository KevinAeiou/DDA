"""Análise estatística considerando em quais masmorras cada item pode ser obtido (SINTÉTICO)."""

import numpy as np
import pytest

from dungeon_drop_analyzer.statistics import analyze_items, holm_adjust, homogeneity_test
from dungeon_drop_analyzer.statistics.analysis import common_columns

MASMORRAS = ["D1", "D2", "D3"]
ITENS = ["A", "A2", "B", "C"]

CONTAGENS = np.array(
    [
        [20, 20, 60, 0],
        [22, 18, 60, 0],
        [20, 20, 0, 60],
    ]
)
DISPONIBILIDADE = np.array(
    [
        [True, True, True, False],
        [True, True, True, False],
        [True, True, False, True],
    ]
)


def analisar(disponibilidade=DISPONIBILIDADE, **extra):
    return analyze_items(CONTAGENS, MASMORRAS, ITENS, availability=disponibilidade, **extra)


def por_item(resultados, nome):
    return next(r for r in resultados if r.item == nome)


def test_colunas_comuns():
    assert common_columns(DISPONIBILIDADE) == [0, 1]
    assert common_columns(np.ones((3, 2), dtype=bool)) == [0, 1]
    assert common_columns(np.zeros((3, 0), dtype=bool)) == []
    assert common_columns(np.eye(3, dtype=bool)) == []


def test_distribuicao_completa_usa_apenas_itens_comuns():
    geral, _ = analisar()
    esperado = homogeneity_test(CONTAGENS[:, [0, 1]])
    assert geral.statistic == pytest.approx(esperado.statistic)
    assert geral.p_value == pytest.approx(esperado.p_value)
    assert geral.dof == esperado.dof == 2
    assert geral.n == 120 and "condicionada a 2 item(ns)" in geral.rationale


def test_zeros_estruturais_distorcem_o_teste_ingenuo_mas_nao_o_condicional():
    ingenuo, _ = analyze_items(CONTAGENS, MASMORRAS, ITENS)
    condicional, _ = analisar()
    assert ingenuo.p_value < 1e-10
    assert condicional.p_value > 0.5


def test_item_e_comparado_apenas_entre_as_masmorras_onde_esta_disponivel():
    _, resultados = analisar()
    b = por_item(resultados, "B")
    assert b.dungeons == ["D1", "D2"]
    assert [p.dungeon for p in b.proportions] == ["D1", "D2"]
    assert [(p.x, p.n) for p in b.proportions] == [(60, 100), (60, 100)]
    assert b.global_test.p_value == pytest.approx(1.0)
    assert b.global_test.n == 200
    assert [(p.a, p.b) for p in b.pairwise] == [("D1", "D2")]
    assert list(b.effects) == [("D1", "D2")]


def test_item_com_todas_as_masmorras_mantem_o_comportamento_completo():
    _, resultados = analisar()
    a = por_item(resultados, "A")
    assert a.dungeons == MASMORRAS and len(a.pairwise) == 3 and len(a.effects) == 3
    sem_restricao = analyze_items(CONTAGENS, MASMORRAS, ITENS)[1]
    assert por_item(sem_restricao, "A").global_test.p_value == pytest.approx(a.global_test.p_value)


def test_item_exclusivo_de_uma_masmorra_nao_tem_comparacao_mas_tem_proporcao():
    _, resultados = analisar()
    c = por_item(resultados, "C")
    assert c.dungeons == ["D3"]
    assert c.global_test.method == "indefinido" and c.global_test.p_value is None
    assert "apenas uma masmorra" in c.global_test.rationale
    assert c.p_holm_across_items is None and c.pairwise == [] and c.effects == {}
    (proporcao,) = c.proportions
    assert (proporcao.x, proporcao.n, proporcao.p) == (60, 100, 0.6)
    assert proporcao.ci[0] < 0.6 < proporcao.ci[1]


def test_holm_entre_itens_considera_somente_testes_definidos():
    _, resultados = analisar()
    brutos = [por_item(resultados, nome).global_test.p_value for nome in ("A", "A2", "B")]
    ajustados = [por_item(resultados, nome).p_holm_across_items for nome in ("A", "A2", "B")]
    assert ajustados == pytest.approx(holm_adjust(brutos))


def test_sem_itens_comuns_a_distribuicao_completa_e_indefinida():
    sem_comuns = np.array(
        [
            [True, False, True, False],
            [False, True, False, True],
            [False, False, False, True],
        ]
    )
    geral, resultados = analisar(sem_comuns)
    assert geral.method == "indefinido" and geral.p_value is None
    assert "Nenhum item pode ser obtido em todas" in geral.rationale
    assert len(resultados) == 4


def test_disponibilidade_ausente_equivale_a_todos_em_todas():
    padrao, itens_padrao = analyze_items(CONTAGENS, MASMORRAS, ITENS)
    todos, itens_todos = analyze_items(
        CONTAGENS, MASMORRAS, ITENS, availability=np.ones(CONTAGENS.shape, dtype=bool)
    )
    assert padrao.p_value == pytest.approx(todos.p_value)
    assert [r.global_test.p_value for r in itens_padrao] == pytest.approx(
        [r.global_test.p_value for r in itens_todos], nan_ok=True
    )


def test_formato_invalido_da_disponibilidade():
    with pytest.raises(ValueError, match="availability"):
        analisar(np.ones((2, 2), dtype=bool))
