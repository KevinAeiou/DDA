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


def alert_text(undefined_items, inconsistent_runs) -> str:
    """Avisos sobre cadastro incompleto e incursões incompatíveis com as masmorras do item."""
    lines: list[str] = []
    if undefined_items:
        names = ", ".join(item.display_name for item in undefined_items)
        lines.append(
            "⚠ Itens sem masmorras definidas (tratados como disponíveis em todas as masmorras; "
            f"edite o cadastro): {names}."
        )
    if inconsistent_runs:
        total = sum(entry.count for entry in inconsistent_runs)
        detail = "; ".join(
            f"{entry.item.display_name} em {entry.dungeon.name} ({entry.count})"
            for entry in inconsistent_runs[:5]
        )
        more = " …" if len(inconsistent_runs) > 5 else ""
        lines.append(
            f"⚠ {total} incursão(ões) registrada(s) com item fora das masmorras do seu cadastro, "
            f"excluídas da análise do item: {detail}{more}."
        )
    return "<br>".join(lines)
