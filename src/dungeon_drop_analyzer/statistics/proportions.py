"""Proporções observadas e intervalo de Wilson."""

from __future__ import annotations

import math

import numpy as np
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


def wilson_series(
    successes: np.ndarray, trials: np.ndarray, confidence: float = 0.95
) -> tuple[np.ndarray, np.ndarray]:
    """Limites inferior e superior de Wilson para vários pares (x, n) de uma vez (n >= 1)."""
    x = np.asarray(successes, dtype=float)
    n = np.asarray(trials, dtype=float)
    if np.any(n < 1) or np.any(x < 0) or np.any(x > n):
        raise ValueError("Requer n >= 1 e 0 <= x <= n.")
    z = norm.ppf(0.5 + confidence / 2)
    z2 = z * z
    p = x / n
    denom = 1 + z2 / n
    center = (p + z2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / denom
    return np.clip(center - half, 0.0, 1.0), np.clip(center + half, 0.0, 1.0)


def wilson_half_width(p: float, n: int, confidence: float = 0.95) -> float:
    """Meia-largura do intervalo de Wilson para a proporção p com n tentativas."""
    if n < 1:
        raise ValueError("n deve ser >= 1.")
    z = norm.ppf(0.5 + confidence / 2)
    z2 = z * z
    return z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / (1 + z2 / n)


def runs_for_margin(
    p: float, margin: float, confidence: float = 0.95, max_n: int = 10_000_000
) -> int:
    """Menor n para o qual a meia-largura de Wilson em p é no máximo `margin` (ambos em 0-1)."""
    if not 0 <= p <= 1:
        raise ValueError("p deve estar em [0, 1].")
    if margin <= 0:
        raise ValueError("margin deve ser positiva.")
    if wilson_half_width(p, max_n, confidence) > margin:
        return max_n
    low, high = 1, max_n
    while low < high:
        mid = (low + high) // 2
        if wilson_half_width(p, mid, confidence) <= margin:
            high = mid
        else:
            low = mid + 1
    return low


def absent_upper_bound(n: int, confidence: float = 0.95) -> float | None:
    """Limite superior de Wilson para um item que não saiu em n incursões (None se n == 0)."""
    interval = wilson_interval(0, n, confidence)
    return None if interval is None else interval[1]


def runs_for_absent_limit(limit: float, confidence: float = 0.95) -> int:
    """Menor n para que um item ausente tenha limite superior de Wilson de no máximo `limit`."""
    if not 0 < limit < 1:
        raise ValueError("limit deve estar em (0, 1).")
    z = norm.ppf(0.5 + confidence / 2)
    return math.ceil(z * z * (1 / limit - 1))


def unseen_probability(singletons: int, n: int) -> float | None:
    """Estimativa de Good-Turing da chance de a próxima incursão dar um item ainda não visto."""
    if n <= 0:
        return None
    if singletons < 0 or singletons > n:
        raise ValueError("Requer 0 <= singletons <= n.")
    return singletons / n
