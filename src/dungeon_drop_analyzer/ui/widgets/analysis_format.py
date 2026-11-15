"""Formatação numérica em português do Brasil para resultados estatísticos."""

from __future__ import annotations


def fmt_num(value: float | None, digits: int = 3) -> str:
    if value is None:
        return "—"
    return f"{value:.{digits}f}".replace(".", ",")


def fmt_pvalue(value: float | None) -> str:
    if value is None:
        return "—"
    if value < 0.001:
        return "< 0,001"
    return fmt_num(value, 4)


def fmt_pct(value: float | None, digits: int = 1) -> str:
    if value is None:
        return "—"
    return f"{fmt_num(value * 100, digits)}%"


def fmt_ci(interval: tuple[float, float] | None) -> str:
    if interval is None:
        return "—"
    return f"[{fmt_pct(interval[0])}; {fmt_pct(interval[1])}]"


def fmt_pp(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{fmt_num(value, 1)} p.p."


METHOD_LABELS = {
    "chi2": "Qui-quadrado de homogeneidade",
    "monte_carlo": "Monte Carlo (permutação, marginais fixas)",
    "fisher_exact": "Teste exato de Fisher",
    "indefinido": "Indefinido",
}


def method_label(method: str) -> str:
    return METHOD_LABELS.get(method, method)
