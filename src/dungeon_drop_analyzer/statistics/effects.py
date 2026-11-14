"""Tamanhos de efeito entre duas proporções (a vs b)."""

from __future__ import annotations

import math
from dataclasses import dataclass

from scipy.stats import norm


@dataclass(frozen=True)
class EffectSize:
    diff_pp: float | None  # (p_a - p_b) em pontos percentuais
    ratio: float | None  # p_a / p_b; None se p_b == 0 ou denominador nulo
    odds_ratio: float | None
    odds_ratio_ci: tuple[float, float] | None
    odds_ratio_corrected: bool  # True se aplicada correção de Haldane-Anscombe (+0,5)
    notes: tuple[str, ...]


def effect_size(x_a: int, n_a: int, x_b: int, n_b: int, confidence: float = 0.95) -> EffectSize:
    """Diferença em p.p., razão de proporções e odds ratio (IC de Wald no log).

    Zeros não geram infinitos: razão indefinida vira None com nota; o odds ratio usa
    Haldane-Anscombe (+0,5 em todas as células) quando alguma célula é zero.
    """
    notes: list[str] = []
    if n_a == 0 or n_b == 0:
        return EffectSize(None, None, None, None, False, ("Denominador nulo: efeito indefinido.",))
    p_a, p_b = x_a / n_a, x_b / n_b
    diff = (p_a - p_b) * 100
    if p_b == 0:
        ratio = None
        notes.append("Razão de proporções indefinida: proporção de referência é zero.")
    else:
        ratio = p_a / p_b
    cells = [x_a, n_a - x_a, x_b, n_b - x_b]
    corrected = 0 in cells
    if corrected:
        cells = [c + 0.5 for c in cells]
        notes.append("Odds ratio calculado com correção de Haldane-Anscombe (célula zero).")
    a, b, c, d = cells
    odds = (a * d) / (b * c)
    se = math.sqrt(1 / a + 1 / b + 1 / c + 1 / d)
    z = norm.ppf(0.5 + confidence / 2)
    ci = (math.exp(math.log(odds) - z * se), math.exp(math.log(odds) + z * se))
    return EffectSize(diff, ratio, odds, ci, corrected, tuple(notes))
