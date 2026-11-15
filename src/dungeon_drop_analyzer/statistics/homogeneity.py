"""Testes de homogeneidade para tabelas de contingência R×C e comparações pareadas."""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field

import numpy as np
from scipy.stats import chi2, chi2_contingency, fisher_exact, random_table

from .multiplicity import holm_adjust

DEFAULT_N_SIM = 10_000
DEFAULT_SEED = 12345


@dataclass(frozen=True)
class TestResult:
    method: str
    statistic: float | None
    dof: int | None
    p_value: float | None
    n: int
    n_sim: int | None = None
    seed: int | None = None
    expected: np.ndarray | None = field(default=None, repr=False, compare=False)
    rationale: str = ""


def _clean(table) -> np.ndarray:
    t = np.asarray(table, dtype=np.int64)
    if t.ndim != 2 or (t < 0).any():
        raise ValueError("A tabela deve ser 2D com contagens não negativas.")
    t = t[t.sum(axis=1) > 0]
    return t[:, t.sum(axis=0) > 0]


def expected_counts(table: np.ndarray) -> np.ndarray:
    return np.outer(table.sum(axis=1), table.sum(axis=0)) / table.sum()


def chi2_adequate(expected: np.ndarray) -> tuple[bool, str]:
    """Critério de Cochran: nenhuma esperada < 1 e no máximo 20% das células < 5."""
    frac_lt5 = float((expected < 5).mean())
    ok = bool(expected.min() >= 1 and frac_lt5 <= 0.20)
    detail = (
        f"esperada mínima={expected.min():.2f}; células com esperada<5: {frac_lt5:.0%} "
        "(critério de Cochran: mín ≥ 1 e ≤ 20% < 5)"
    )
    return ok, detail


def _chi2_stat(table: np.ndarray, expected: np.ndarray) -> float:
    return float(((table - expected) ** 2 / expected).sum())


def _monte_carlo(table: np.ndarray, n_sim: int, seed: int) -> tuple[float, float]:
    """Teste de permutação (marginais fixas, tabelas de Patefield) com estatística qui-quadrado."""
    expected = expected_counts(table)
    observed = _chi2_stat(table, expected)
    rng = np.random.default_rng(seed)
    sampler = random_table(table.sum(axis=1), table.sum(axis=0), seed=rng)
    sims = sampler.rvs(size=n_sim)
    stats = ((sims - expected) ** 2 / expected).sum(axis=(1, 2))
    tol = 1e-9 * max(1.0, observed)
    extreme = int((stats >= observed - tol).sum())
    return observed, (extreme + 1) / (n_sim + 1)


def homogeneity_test(
    table, method: str = "auto", n_sim: int = DEFAULT_N_SIM, seed: int = DEFAULT_SEED
) -> TestResult:
    """Testa H0: distribuições iguais entre as linhas (masmorras).

    method="auto": qui-quadrado se as esperadas forem adequadas; senão Monte Carlo.
    Linhas/colunas totalmente nulas são removidas antes do teste.
    """
    if method not in {"auto", "chi2", "monte_carlo"}:
        raise ValueError("method deve ser 'auto', 'chi2' ou 'monte_carlo'.")
    total = int(np.asarray(table).sum())
    t = _clean(table)
    if t.shape[0] < 2 or t.shape[1] < 2:
        return TestResult(
            "indefinido",
            None,
            None,
            None,
            total,
            rationale="Menos de 2 masmorras com dados ou menos de 2 itens distintos.",
        )
    expected = expected_counts(t)
    ok, detail = chi2_adequate(expected)
    if method == "chi2" or (method == "auto" and ok):
        stat = _chi2_stat(t, expected)
        dof = (t.shape[0] - 1) * (t.shape[1] - 1)
        p = float(chi2.sf(stat, dof))
        why = "Qui-quadrado de homogeneidade: " + detail
        if not ok:
            why += " — AVISO: aproximação inadequada."
        return TestResult("chi2", stat, dof, p, total, expected=expected, rationale=why)
    stat, p = _monte_carlo(t, n_sim, seed)
    why = "Monte Carlo (permutação, marginais fixas): " + (
        "aproximação qui-quadrado inadequada — " + detail if method == "auto" else "solicitado"
    )
    return TestResult(
        "monte_carlo",
        stat,
        None,
        p,
        total,
        n_sim=n_sim,
        seed=seed,
        expected=expected,
        rationale=why,
    )


@dataclass(frozen=True)
class PairResult:
    a: str
    b: str
    method: str
    p_raw: float | None
    p_holm: float | None


def _two_prop(x1: int, n1: int, x2: int, n2: int) -> tuple[str, float | None]:
    table = np.array([[x1, n1 - x1], [x2, n2 - x2]])
    if n1 == 0 or n2 == 0 or (x1 + x2) in (0, n1 + n2):
        return "indefinido", None
    ok, _ = chi2_adequate(expected_counts(table))
    if ok:
        return "chi2", float(chi2_contingency(table, correction=False).pvalue)
    return "fisher_exact", float(fisher_exact(table).pvalue)


def pairwise_tests(x, n, labels) -> list[PairResult]:
    """Comparações pareadas de proporções; Holm aplicado na família deste item."""
    pairs = list(itertools.combinations(range(len(labels)), 2))
    raw = [_two_prop(int(x[i]), int(n[i]), int(x[j]), int(n[j])) for i, j in pairs]
    defined = [k for k, (_, p) in enumerate(raw) if p is not None]
    adj = holm_adjust([raw[k][1] for k in defined])
    holm: dict[int, float] = dict(zip(defined, adj, strict=True))
    return [
        PairResult(labels[i], labels[j], raw[k][0], raw[k][1], holm.get(k))
        for k, (i, j) in enumerate(pairs)
    ]
