"""Orquestração da análise por item e distribuição completa."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

import numpy as np

from .effects import EffectSize, effect_size
from .homogeneity import (
    DEFAULT_N_SIM,
    DEFAULT_SEED,
    PairResult,
    TestResult,
    homogeneity_test,
    pairwise_tests,
)
from .multiplicity import holm_adjust
from .proportions import DEFAULT_MIN_PER_DUNGEON, wilson_interval


@dataclass(frozen=True)
class DungeonProportion:
    dungeon: str
    x: int
    n: int
    p: float | None
    ci: tuple[float, float] | None
    insufficient: bool


@dataclass(frozen=True)
class ItemAnalysis:
    item: str
    proportions: list[DungeonProportion]
    global_test: TestResult
    p_holm_across_items: float | None
    pairwise: list[PairResult]
    effects: dict[tuple[str, str], EffectSize]
    dungeons: list[str] = field(default_factory=list)


def common_columns(availability) -> list[int]:
    """Índices dos itens disponíveis em todas as masmorras analisadas."""
    matrix = np.asarray(availability, dtype=bool)
    return [int(j) for j in np.flatnonzero(matrix.all(axis=0))] if matrix.size else []


def analyze_items(
    counts,
    dungeons: list[str],
    items: list[str],
    min_n: int = DEFAULT_MIN_PER_DUNGEON,
    n_sim: int = DEFAULT_N_SIM,
    seed: int = DEFAULT_SEED,
    availability=None,
) -> tuple[TestResult, list[ItemAnalysis]]:
    """counts: matriz masmorras × itens com contagens de incursões.

    availability: matriz booleana masmorras × itens indicando onde cada item pode ser obtido
    (None = todos em todas). O denominador de cada masmorra é o total de incursões válidas dela
    (inclui outros itens).

    - Cada item é comparado apenas entre as masmorras em que está disponível; um item disponível
      em uma única masmorra não tem comparação (teste indefinido, mas as proporções são mantidas).
    - A distribuição completa usa só os itens disponíveis em todas as masmorras analisadas
      (distribuição condicional), evitando zeros estruturais que forçariam a heterogeneidade.
    """
    c = np.asarray(counts, dtype=np.int64)
    if c.shape != (len(dungeons), len(items)):
        raise ValueError("Formato de counts incompatível com masmorras × itens.")
    if availability is None:
        allowed = np.ones(c.shape, dtype=bool)
    else:
        allowed = np.asarray(availability, dtype=bool)
        if allowed.shape != c.shape:
            raise ValueError("Formato de availability incompatível com masmorras × itens.")
    n = c.sum(axis=1)

    common = common_columns(allowed)
    if common:
        overall = homogeneity_test(c[:, common], n_sim=n_sim, seed=seed)
        if availability is not None:
            note = (
                f"Distribuição condicionada a {len(common)} item(ns) "
                "disponível(is) em todas as masmorras."
            )
            overall = replace(overall, rationale=f"{note} {overall.rationale}".strip())
    else:
        overall = TestResult(
            "indefinido",
            None,
            None,
            None,
            int(c.sum()),
            rationale="Nenhum item pode ser obtido em todas as masmorras analisadas.",
        )

    results: list[ItemAnalysis] = []
    for j, item in enumerate(items):
        rows = [d for d in range(len(dungeons)) if allowed[d, j]]
        names = [dungeons[d] for d in rows]
        x = c[rows, j]
        nd = n[rows]
        props = [
            DungeonProportion(
                names[k],
                int(x[k]),
                int(nd[k]),
                int(x[k]) / int(nd[k]) if nd[k] else None,
                wilson_interval(int(x[k]), int(nd[k])),
                int(nd[k]) < min_n,
            )
            for k in range(len(rows))
        ]
        if len(rows) >= 2:
            table = np.column_stack([x, nd - x])
            g = homogeneity_test(table, n_sim=n_sim, seed=seed)
            pairs = pairwise_tests(x, nd, names)
            effects = {
                (names[a], names[b]): effect_size(int(x[a]), int(nd[a]), int(x[b]), int(nd[b]))
                for a in range(len(rows))
                for b in range(a + 1, len(rows))
            }
        else:
            g = TestResult(
                "indefinido",
                None,
                None,
                None,
                int(nd.sum()),
                rationale="Item disponível em apenas uma masmorra analisada: sem comparação.",
            )
            pairs, effects = [], {}
        results.append(ItemAnalysis(item, props, g, None, pairs, effects, names))

    defined = [i for i, r in enumerate(results) if r.global_test.p_value is not None]
    p_raw = [results[i].global_test.p_value for i in defined]
    adj = dict(zip(defined, holm_adjust(p_raw), strict=True))
    results = [
        ItemAnalysis(
            r.item, r.proportions, r.global_test, adj.get(i), r.pairwise, r.effects, r.dungeons
        )
        for i, r in enumerate(results)
    ]
    return overall, results
