"""Dados do dashboard e análise estatística sobre o histórico filtrado."""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field, replace
from datetime import date, datetime

import numpy as np
from sqlalchemy.orm import Session, sessionmaker

from dungeon_drop_analyzer.core.database import session_scope
from dungeon_drop_analyzer.models import Dungeon, Item, ItemCategory
from dungeon_drop_analyzer.repositories import (
    DungeonRepository,
    ItemRepository,
    RunFilter,
    RunRepository,
)
from dungeon_drop_analyzer.statistics import (
    ItemAnalysis,
    TestResult,
    TrendResult,
    absent_upper_bound,
    analyze_items,
    holm_adjust,
    runs_for_absent_limit,
    runs_for_margin,
    trend_test,
    unseen_probability,
    wilson_interval,
    wilson_series,
)
from dungeon_drop_analyzer.statistics.analysis import common_columns
from dungeon_drop_analyzer.statistics.homogeneity import DEFAULT_N_SIM, DEFAULT_SEED
from dungeon_drop_analyzer.statistics.proportions import DEFAULT_MIN_PER_DUNGEON

logger = logging.getLogger(__name__)

ALPHA = 0.05
LIMITATION_NOTES = (
    "Masmorra e dificuldade estão confundidas: associações não indicam que a dificuldade, "
    "isoladamente, causa a diferença.",
    "O teste supõe incursões independentes; sistemas de pity, recompensas rotativas, bônus "
    "temporários e atualizações podem violar essa hipótese.",
    "Resultado não significativo não prova igualdade entre as masmorras.",
    "Cada item é comparado apenas entre as masmorras em que pode ser obtido; a distribuição "
    "completa considera somente os itens disponíveis em todas as masmorras analisadas.",
)


@dataclass(frozen=True)
class DungeonCount:
    dungeon: Dungeon
    runs: int


@dataclass(frozen=True)
class ItemCount:
    item: Item
    count: int
    share: float
    ci: tuple[float, float] | None = None


@dataclass(frozen=True)
class CoverageRow:
    """Quanto a amostra de uma masmorra já cobre o catálogo de itens dela."""

    dungeon: Dungeon
    runs: int
    registered_items: int
    seen_registered: int
    seen_total: int
    singletons: int
    top_item: Item | None
    top_share: float | None

    @property
    def unseen_registered(self) -> int:
        return self.registered_items - self.seen_registered

    @property
    def unseen_chance(self) -> float | None:
        """Good-Turing: chance de a próxima incursão dar um item ainda não visto."""
        return unseen_probability(self.singletons, self.runs)

    @property
    def absent_upper(self) -> float | None:
        """Limite superior (95%) da chance de cada item cadastrado que ainda não saiu."""
        return absent_upper_bound(self.runs)

    def missing_for_absent_limit(self, limit: float) -> int:
        """Incursões que faltam para o limite dos itens ausentes cair até `limit` (0 a 1)."""
        return max(0, runs_for_absent_limit(limit) - self.runs)

    def missing_for_margin(self, margin: float) -> int | None:
        """Incursões que faltam para o item mais frequente ter margem de até `margin` (0 a 1)."""
        if self.top_share is None:
            return None
        return max(0, runs_for_margin(self.top_share, margin) - self.runs)


@dataclass(frozen=True)
class ConvergenceSeries:
    """Proporção acumulada de um item ao longo das incursões de uma masmorra."""

    dungeon_name: str
    item_label: str
    hits: np.ndarray = field(repr=False)
    proportion: np.ndarray = field(repr=False)
    lower: np.ndarray = field(repr=False)
    upper: np.ndarray = field(repr=False)

    @property
    def runs(self) -> int:
        return len(self.hits)

    @property
    def final_hits(self) -> int:
        return int(self.hits[-1]) if self.runs else 0

    @property
    def final_proportion(self) -> float | None:
        return float(self.proportion[-1]) if self.runs else None

    @property
    def final_interval(self) -> tuple[float, float] | None:
        return (float(self.lower[-1]), float(self.upper[-1])) if self.runs else None

    @property
    def final_margin(self) -> float | None:
        interval = self.final_interval
        return None if interval is None else (interval[1] - interval[0]) / 2

    def margin_at(self, runs: int) -> float:
        """Meia-largura do intervalo após as primeiras `runs` incursões."""
        return float((self.upper[runs - 1] - self.lower[runs - 1]) / 2)


@dataclass(frozen=True)
class InconsistentRun:
    """Incursões registradas com um item em masmorra fora do cadastro do item."""

    dungeon: Dungeon
    item: Item
    count: int


@dataclass(frozen=True)
class DashboardData:
    total_runs: int
    distinct_items: int
    dungeon_counts: list[DungeonCount]
    item_counts: list[ItemCount]
    most_frequent: list[ItemCount]
    least_frequent: list[ItemCount]
    category_counts: dict[int, dict[str, int]]
    cells: dict[tuple[int, int], int]
    timeline: dict[str, list[tuple[date, int]]]
    availability: dict[int, set[int]] = field(default_factory=dict)
    undefined_items: list[Item] = field(default_factory=list)
    inconsistent_runs: list[InconsistentRun] = field(default_factory=list)
    coverage: list[CoverageRow] = field(default_factory=list)

    def is_available(self, item_id: int, dungeon_id: int) -> bool:
        allowed = self.availability.get(item_id)
        return not allowed or dungeon_id in allowed


@dataclass(frozen=True)
class LevelGroup:
    difficulty: int
    x: int
    n: int
    dungeons: list[str]


@dataclass(frozen=True)
class ItemTrend:
    item: Item
    result: TrendResult
    p_holm: float | None
    groups: list[LevelGroup] = field(default_factory=list)


@dataclass(frozen=True)
class LevelRow:
    difficulty: int
    dungeons: list[str]
    runs: int
    counts: dict[int, int]


@dataclass(frozen=True)
class AnalysisReport:
    sample_size: int
    dungeons: list[Dungeon]
    items: list[Item]
    matrix: np.ndarray = field(repr=False)
    runs_per_dungeon: dict[int, int]
    overall: TestResult | None
    per_item: list[ItemAnalysis]
    levels: list[LevelRow]
    trends: list[ItemTrend]
    min_n: int
    alpha: float = ALPHA
    availability: np.ndarray | None = field(default=None, repr=False)
    common_items: list[Item] = field(default_factory=list)
    undefined_items: list[Item] = field(default_factory=list)
    inconsistent_runs: list[InconsistentRun] = field(default_factory=list)

    @property
    def analyzable(self) -> bool:
        return self.overall is not None

    def is_available(self, dungeon_index: int, item_index: int) -> bool:
        if self.availability is None:
            return True
        return bool(self.availability[dungeon_index, item_index])


def interpret(p_value: float | None, alpha: float = ALPHA) -> str:
    """Texto de interpretação para um teste de igualdade entre masmorras."""
    if p_value is None:
        return (
            "Teste indefinido: são necessárias ao menos duas masmorras com incursões em que o "
            "item (ou os itens comuns) possa ser obtido, e dois itens distintos obtidos."
        )
    if p_value < alpha:
        return (
            f"Foi detectada diferença estatisticamente significativa (nível de {alpha:.0%}). "
            "Isso indica associação com a masmorra, não causalidade."
        )
    return (
        "Não foi detectada diferença estatisticamente significativa. "
        "Isso não prova que as distribuições sejam iguais."
    )


def _allowed(item: Item, dungeon_id: int) -> bool:
    """Item sem masmorras cadastradas é tratado como disponível em todas (a ser corrigido)."""
    defined = {d.id for d in item.dungeons}
    return not defined or dungeon_id in defined


class AnalyticsService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._factory = session_factory

    def _load(self, flt: RunFilter | None):
        with session_scope(self._factory) as session:
            runs = RunRepository(session)
            return (
                DungeonRepository(session).list(),
                ItemRepository(session).list(),
                runs.count_matrix(flt),
                runs.timeline(flt),
            )

    @staticmethod
    def _inconsistent(dungeons, items, counts) -> list[InconsistentRun]:
        dungeon_by_id = {d.id: d for d in dungeons}
        item_by_id = {i.id: i for i in items}
        found = [
            InconsistentRun(dungeon_by_id[d], item_by_id[i], count)
            for (d, i), count in counts.items()
            if count > 0 and not _allowed(item_by_id[i], d)
        ]
        return sorted(
            found, key=lambda r: (r.item.display_name.casefold(), r.dungeon.name.casefold())
        )

    def dashboard(self, flt: RunFilter | None = None) -> DashboardData:
        """Painel apenas com masmorras ativas: as inativas não entram em listas nem em totais."""
        dungeons, items, cells, timeline = self._load(flt)
        dungeons = [d for d in dungeons if d.is_active]
        active_ids = {d.id for d in dungeons}
        cells = [cell for cell in cells if cell[0] in active_ids]
        timeline = [point for point in timeline if point[1] in active_ids]
        counts = {(d, i): c for d, i, c in cells}
        by_dungeon: dict[int, int] = defaultdict(int)
        by_item: dict[int, int] = defaultdict(int)
        category_counts: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        item_by_id = {i.id: i for i in items}
        for dungeon_id, item_id, count in cells:
            by_dungeon[dungeon_id] += count
            by_item[item_id] += count
            category_counts[dungeon_id][item_by_id[item_id].category] += count
        total = sum(by_dungeon.values())

        shown = [item for item in items if item.is_active or by_item.get(item.id, 0) > 0]
        item_counts = [
            ItemCount(
                item,
                by_item.get(item.id, 0),
                by_item.get(item.id, 0) / total if total else 0.0,
                wilson_interval(by_item.get(item.id, 0), total),
            )
            for item in shown
        ]
        item_counts.sort(key=lambda c: (-c.count, c.item.display_name.casefold()))
        most: list[ItemCount] = []
        least: list[ItemCount] = []
        if total and item_counts:
            top, bottom = item_counts[0].count, item_counts[-1].count
            most = [c for c in item_counts if c.count == top]
            least = [c for c in item_counts if c.count == bottom]

        dungeon_name = {d.id: d.name for d in dungeons}
        daily: dict[int, dict[date, int]] = defaultdict(lambda: defaultdict(int))
        for completed_at, dungeon_id in timeline:
            daily[dungeon_id][_local_date(completed_at)] += 1
        series: dict[str, list[tuple[date, int]]] = {}
        for dungeon_id, days in daily.items():
            cumulative = 0
            points = []
            for day in sorted(days):
                cumulative += days[day]
                points.append((day, cumulative))
            series[dungeon_name[dungeon_id]] = points

        return DashboardData(
            total_runs=total,
            distinct_items=sum(1 for count in by_item.values() if count > 0),
            dungeon_counts=[DungeonCount(d, by_dungeon.get(d.id, 0)) for d in dungeons],
            item_counts=item_counts,
            most_frequent=most,
            least_frequent=least,
            category_counts={k: dict(v) for k, v in category_counts.items()},
            cells=counts,
            timeline=series,
            availability={i.id: {d.id for d in i.dungeons} for i in items if i.dungeons},
            undefined_items=[i for i in shown if not i.dungeons],
            inconsistent_runs=self._inconsistent(dungeons, items, counts),
            coverage=self._coverage(dungeons, items, counts, by_dungeon),
        )

    @staticmethod
    def _coverage(dungeons, items, counts, by_dungeon) -> list[CoverageRow]:
        rows = []
        for dungeon in dungeons:
            per_item = {
                item_id: count
                for (dungeon_id, item_id), count in counts.items()
                if dungeon_id == dungeon.id and count > 0
            }
            registered = [i for i in items if i.is_active and _allowed(i, dungeon.id)]
            item_by_id = {i.id: i for i in items}
            top_id = max(per_item, key=lambda k: (per_item[k], -k), default=None)
            runs = by_dungeon.get(dungeon.id, 0)
            rows.append(
                CoverageRow(
                    dungeon=dungeon,
                    runs=runs,
                    registered_items=len(registered),
                    seen_registered=sum(1 for i in registered if per_item.get(i.id, 0) > 0),
                    seen_total=len(per_item),
                    singletons=sum(1 for c in per_item.values() if c == 1),
                    top_item=item_by_id[top_id] if top_id is not None else None,
                    top_share=per_item[top_id] / runs if top_id is not None and runs else None,
                )
            )
        return rows

    def convergence(
        self, dungeon_id: int, item_id: int, flt: RunFilter | None = None
    ) -> ConvergenceSeries:
        """Proporção acumulada do item nas incursões da masmorra, em ordem cronológica."""
        base = flt or RunFilter()
        scoped = replace(base, dungeon_ids=[dungeon_id], item_ids=None)
        with session_scope(self._factory) as session:
            dungeon = DungeonRepository(session).get(dungeon_id)
            items = {i.id: i for i in ItemRepository(session).list()}
            runs = RunRepository(session).list(scoped, descending=False)
            sequence = np.array([1 if r.item_id == item_id else 0 for r in runs], dtype=np.int64)
            dungeon_name = dungeon.name if dungeon else str(dungeon_id)
            item = items.get(item_id)
            label = item.display_name if item else str(item_id)
        hits = np.cumsum(sequence)
        if len(hits) == 0:
            empty = np.array([], dtype=float)
            return ConvergenceSeries(dungeon_name, label, hits, empty, empty, empty)
        trials = np.arange(1, len(hits) + 1)
        lower, upper = wilson_series(hits, trials)
        return ConvergenceSeries(dungeon_name, label, hits, hits / trials, lower, upper)

    def analyze(
        self,
        flt: RunFilter | None = None,
        min_n: int = DEFAULT_MIN_PER_DUNGEON,
        n_sim: int = DEFAULT_N_SIM,
        seed: int = DEFAULT_SEED,
        alpha: float = ALPHA,
    ) -> AnalysisReport:
        all_dungeons, all_items, cells, _ = self._load(flt)
        counts = {(d, i): c for d, i, c in cells}
        runs_per_dungeon = {
            d.id: sum(c for (di, _), c in counts.items() if di == d.id) for d in all_dungeons
        }
        dungeons = [d for d in all_dungeons if runs_per_dungeon[d.id] > 0]
        item_totals = {
            i.id: sum(c for (_, ii), c in counts.items() if ii == i.id) for i in all_items
        }
        items = [i for i in all_items if item_totals[i.id] > 0]
        sample = sum(runs_per_dungeon.values())
        matrix = np.array(
            [[counts.get((d.id, i.id), 0) for i in items] for d in dungeons], dtype=np.int64
        ).reshape(len(dungeons), len(items))
        availability = np.array(
            [[_allowed(i, d.id) for i in items] for d in dungeons], dtype=bool
        ).reshape(len(dungeons), len(items))

        overall = None
        per_item: list[ItemAnalysis] = []
        common: list[Item] = []
        if len(dungeons) >= 2 and len(items) >= 1:
            overall, per_item = analyze_items(
                matrix,
                [d.name for d in dungeons],
                [i.display_name for i in items],
                min_n=min_n,
                n_sim=n_sim,
                seed=seed,
                availability=availability,
            )
            common = [items[j] for j in common_columns(availability)]
        levels, trends = self._trends(dungeons, items, counts, runs_per_dungeon)
        logger.info(
            "Análise executada: n=%s masmorras=%s itens=%s", sample, len(dungeons), len(items)
        )
        return AnalysisReport(
            sample_size=sample,
            dungeons=dungeons,
            items=items,
            matrix=matrix,
            runs_per_dungeon=runs_per_dungeon,
            overall=overall,
            per_item=per_item,
            levels=levels,
            trends=trends,
            min_n=min_n,
            alpha=alpha,
            availability=availability,
            common_items=common,
            undefined_items=[i for i in items if not i.dungeons],
            inconsistent_runs=self._inconsistent(all_dungeons, all_items, counts),
        )

    @staticmethod
    def _trends(dungeons, items, counts, runs_per_dungeon):
        grouped: dict[int, list[Dungeon]] = defaultdict(list)
        for dungeon in dungeons:
            grouped[dungeon.difficulty].append(dungeon)
        levels = [
            LevelRow(
                difficulty=level,
                dungeons=[d.name for d in members],
                runs=sum(runs_per_dungeon[d.id] for d in members),
                counts={i.id: sum(counts.get((d.id, i.id), 0) for d in members) for i in items},
            )
            for level, members in sorted(grouped.items())
        ]
        trends = []
        for item in items:
            groups = []
            for level, members in sorted(grouped.items()):
                allowed = [d for d in members if _allowed(item, d.id)]
                if allowed:
                    groups.append(
                        LevelGroup(
                            level,
                            sum(counts.get((d.id, item.id), 0) for d in allowed),
                            sum(runs_per_dungeon[d.id] for d in allowed),
                            [d.name for d in allowed],
                        )
                    )
            result = trend_test(
                [g.x for g in groups], [g.n for g in groups], [g.difficulty for g in groups]
            )
            trends.append(ItemTrend(item, result, None, groups))
        defined = [k for k, t in enumerate(trends) if t.result.p_value is not None]
        adjusted = dict(
            zip(defined, holm_adjust([trends[k].result.p_value for k in defined]), strict=True)
        )
        trends = [
            ItemTrend(t.item, t.result, adjusted.get(k), t.groups) for k, t in enumerate(trends)
        ]
        return levels, trends


def _local_date(value: datetime) -> date:
    return value.astimezone().date()


CATEGORY_ORDER = [category.value for category in ItemCategory]
