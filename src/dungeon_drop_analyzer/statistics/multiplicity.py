"""Correção de múltiplas comparações."""

from __future__ import annotations


def holm_adjust(p_values) -> list[float]:
    """Valores-p ajustados por Holm (step-down), na ordem de entrada."""
    p = [float(v) for v in p_values]
    m = len(p)
    order = sorted(range(m), key=lambda i: p[i])
    adjusted = [0.0] * m
    running = 0.0
    for rank, idx in enumerate(order):
        running = max(running, (m - rank) * p[idx])
        adjusted[idx] = min(1.0, running)
    return adjusted
