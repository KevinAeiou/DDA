"""Proporções observadas e intervalo de Wilson."""

from __future__ import annotations

import math

from scipy.stats import norm

DEFAULT_MIN_PER_DUNGEON = 50


def wilson_interval(x: int, n: int, confidence: float = 0.95) -> tuple[float, float] | None:
    """Intervalo de Wilson para uma proporção binomial. Retorna None se n == 0."""
    if n < 0 or x < 0 or x > n:
        raise ValueError("Requer 0 <= x <= n.")
    if not 0 < confidence < 1:
        raise ValueError("confidence deve estar em (0, 1).")
    if n == 0:
        return None
    z = norm.ppf(0.5 + confidence / 2)
    p = x / n
    z2 = z * z
    denom = 1 + z2 / n
    center = (p + z2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / denom
    return max(0.0, center - half), min(1.0, center + half)


def insufficient_sample(n_per_dungeon, min_n: int = DEFAULT_MIN_PER_DUNGEON) -> list[bool]:
    """Sinaliza, para cada masmorra, se n < min_n (amostra insuficiente)."""
    return [int(n) < min_n for n in n_per_dungeon]
