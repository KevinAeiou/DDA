"""Teste de tendência de Cochran-Armitage (exploratório) para proporções ordenadas."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.stats import norm


@dataclass(frozen=True)
class TrendResult:
    z: float | None
    p_value: float | None
    direction: str
    n: int
    groups: int
    rationale: str = ""


def trend_test(x, n, scores) -> TrendResult:
    """Cochran-Armitage bilateral. Grupos sem observações são descartados.

    direction: "crescente", "decrescente" ou "indefinida". Indefinido quando há menos de
    dois grupos ou os escores são todos iguais, ou quando a proporção global é 0 ou 1.
    """
    x = np.asarray(x, dtype=float)
    n = np.asarray(n, dtype=float)
    s = np.asarray(scores, dtype=float)
    if not (x.shape == n.shape == s.shape) or x.ndim != 1:
        raise ValueError("x, n e scores devem ser vetores do mesmo tamanho.")
    if (x < 0).any() or (x > n).any():
        raise ValueError("Requer 0 <= x <= n.")
    keep = n > 0
    x, n, s = x[keep], n[keep], s[keep]
    total = int(n.sum())
    groups = int(keep.sum())
    if groups < 2 or len(set(s.tolist())) < 2:
        return TrendResult(
            None, None, "indefinida", total, groups, "Menos de dois grupos com escores distintos."
        )
    p_bar = x.sum() / n.sum()
    if p_bar in (0.0, 1.0):
        return TrendResult(
            None,
            None,
            "indefinida",
            total,
            groups,
            "Item ausente ou presente em todas as incursões.",
        )
    t_stat = float((s * (x - n * p_bar)).sum())
    variance = p_bar * (1 - p_bar) * ((n * s**2).sum() - (n * s).sum() ** 2 / n.sum())
    if variance <= 0:
        return TrendResult(None, None, "indefinida", total, groups, "Variância nula.")
    z = t_stat / math.sqrt(variance)
    p = float(2 * norm.sf(abs(z)))
    direction = "crescente" if z > 0 else "decrescente" if z < 0 else "indefinida"
    return TrendResult(z, p, direction, total, groups, "Cochran-Armitage bilateral (exploratório).")
