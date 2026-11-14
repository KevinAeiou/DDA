"""Orquestração da análise por item e distribuição completa."""

from __future__ import annotations

from dataclasses import dataclass

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
    p_holm_across_items: float | None  # Holm sobre os testes globais de todos os itens
    pairwise: list[PairResult]  # Holm dentro da família do item
    effects: dict[tuple[str, str], EffectSize]  # (a, b) -> efeito de a em relação a b


def analyze_items(
    counts,
    dungeons: list[str],
    items: list[str],
    min_n: int = DEFAULT_MIN_PER_DUNGEON,
    n_sim: int = DEFAULT_N_SIM,
    seed: int = DEFAULT_SEED,
) -> tuple[TestResult, list[ItemAnalysis]]:
    """counts: matriz masmorras × itens com contagens de incursões.

    Retorna (teste da distribuição completa 5×K, análise de cada item). O denominador de cada
    masmorra é o total de incursões válidas dela (inclui outros itens).
    """
    c = np.asarray(counts, dtype=np.int64)
    if c.shape != (len(dungeons), len(items)):
        raise ValueError("Formato de counts incompatível com masmorras × itens.")
    n = c.sum(axis=1)
    overall = homogeneity_test(c, n_sim=n_sim, seed=seed)

    results: list[ItemAnalysis] = []
    for j, item in enumerate(items):
        x = c[:, j]
        props = []
        for d, name in enumerate(dungeons):
            nd, xd = int(n[d]), int(x[d])
            props.append(
                DungeonProportion(
                    name, xd, nd, xd / nd if nd else None, wilson_interval(xd, nd), nd < min_n
                )
            )
        table = np.column_stack([x, n - x])  # 5×2: obtido / não obtido
        g = homogeneity_test(table, n_sim=n_sim, seed=seed)
        pairs = pairwise_tests(x, n, dungeons)
        effects = {}
        for a in range(len(dungeons)):
            for b in range(a + 1, len(dungeons)):
                effects[(dungeons[a], dungeons[b])] = effect_size(
                    int(x[a]), int(n[a]), int(x[b]), int(n[b])
                )
        results.append(ItemAnalysis(item, props, g, None, pairs, effects))

    defined = [i for i, r in enumerate(results) if r.global_test.p_value is not None]
    p_raw = [results[i].global_test.p_value for i in defined]
    adj = dict(zip(defined, holm_adjust(p_raw), strict=True))
    results = [
        ItemAnalysis(r.item, r.proportions, r.global_test, adj.get(i), r.pairwise, r.effects)
        for i, r in enumerate(results)
    ]
    return overall, results
