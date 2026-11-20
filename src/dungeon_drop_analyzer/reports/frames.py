"""Tabelas (DataFrames) dos relatórios: histórico, frequências e resultados estatísticos."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

import numpy as np
import pandas as pd

from dungeon_drop_analyzer.models import CATEGORY_LABELS, Dungeon, Item, ItemCategory, Run
from dungeon_drop_analyzer.repositories import RunFilter
from dungeon_drop_analyzer.services.analytics import AnalysisReport, interpret
from dungeon_drop_analyzer.statistics import wilson_interval

TRISTATE = {"yes": "Sim", "no": "Não", "unknown": "Desconhecido"}
EXPORT_COLUMN = "exportado_em"

HISTORY_COLUMNS = [
    "id",
    "data_hora_local",
    "data_hora_utc",
    "masmorra",
    "dificuldade",
    "item",
    "categoria",
    "duracao_segundos",
    "versao_jogo",
    "bonus_de_drop",
    "evento_ativo",
    "observacoes",
]
FREQUENCY_COLUMNS = [
    "masmorra",
    "dificuldade",
    "item",
    "categoria",
    "obtencoes",
    "incursoes_masmorra",
    "proporcao",
    "ic95_inferior",
    "ic95_superior",
    "amostra_insuficiente",
    "item_disponivel_na_masmorra",
]
STATISTICS_COLUMNS = [
    "escopo",
    "item",
    "comparacao",
    "masmorras_consideradas",
    "metodo",
    "amostra_n",
    "estatistica",
    "graus_liberdade",
    "p_bruto",
    "p_ajustado_holm",
    "familia_holm",
    "simulacoes",
    "semente",
    "diferenca_pp",
    "razao_proporcoes",
    "odds_ratio",
    "odds_ratio_ic95_inferior",
    "odds_ratio_ic95_superior",
    "interpretacao",
    "notas",
]

METHOD_NAMES = {
    "chi2": "Qui-quadrado de homogeneidade",
    "monte_carlo": "Monte Carlo (permutação, marginais fixas)",
    "fisher_exact": "Teste exato de Fisher",
    "indefinido": "Indefinido",
}


def format_moment(value: datetime) -> str:
    return value.astimezone().strftime("%Y-%m-%d %H:%M:%S")


def category_label(code: str) -> str:
    try:
        return CATEGORY_LABELS[ItemCategory(code)]
    except ValueError:
        return code


def _stamp(frame: pd.DataFrame, exported_at: datetime) -> pd.DataFrame:
    frame[EXPORT_COLUMN] = format_moment(exported_at)
    return frame


def history_frame(runs: Sequence[Run], exported_at: datetime) -> pd.DataFrame:
    rows = [
        {
            "id": run.id,
            "data_hora_local": format_moment(run.completed_at),
            "data_hora_utc": run.completed_at.strftime("%Y-%m-%d %H:%M:%S"),
            "masmorra": run.dungeon.name,
            "dificuldade": run.dungeon.difficulty,
            "item": run.item.display_name,
            "categoria": category_label(run.item.category),
            "duracao_segundos": run.duration_seconds,
            "versao_jogo": run.game_version,
            "bonus_de_drop": TRISTATE.get(run.bonus_status, run.bonus_status),
            "evento_ativo": TRISTATE.get(run.event_status, run.event_status),
            "observacoes": run.notes,
        }
        for run in runs
    ]
    return _stamp(pd.DataFrame(rows, columns=HISTORY_COLUMNS), exported_at)


def frequencies_frame(report: AnalysisReport, exported_at: datetime) -> pd.DataFrame:
    """Uma linha por masmorra × item em que o item pode ser obtido.

    Combinações em que o item não está disponível não entram (zero estrutural), exceto se houver
    incursões registradas nelas; nesse caso a linha aparece com `item_disponivel_na_masmorra` = Não.
    """
    rows = []
    for r, dungeon in enumerate(report.dungeons):
        n = report.runs_per_dungeon[dungeon.id]
        for c, item in enumerate(report.items):
            x = int(report.matrix[r, c])
            available = report.is_available(r, c)
            if not available and x == 0:
                continue
            interval = wilson_interval(x, n)
            rows.append(
                {
                    "masmorra": dungeon.name,
                    "dificuldade": dungeon.difficulty,
                    "item": item.display_name,
                    "categoria": category_label(item.category),
                    "obtencoes": x,
                    "incursoes_masmorra": n,
                    "proporcao": x / n,
                    "ic95_inferior": interval[0],
                    "ic95_superior": interval[1],
                    "amostra_insuficiente": "Sim" if n < report.min_n else "Não",
                    "item_disponivel_na_masmorra": "Sim" if available else "Não",
                }
            )
    return _stamp(pd.DataFrame(rows, columns=FREQUENCY_COLUMNS), exported_at)


def _test_row(scope, item, comparison, method, result=None, **extra) -> dict:
    row = dict.fromkeys(STATISTICS_COLUMNS)
    row.update(
        escopo=scope, item=item, comparacao=comparison, metodo=METHOD_NAMES.get(method, method)
    )
    if result is not None:
        row.update(
            amostra_n=result.n,
            estatistica=result.statistic,
            graus_liberdade=result.dof,
            p_bruto=result.p_value,
            simulacoes=result.n_sim,
            semente=result.seed,
        )
    row.update(extra)
    return row


def statistics_frame(report: AnalysisReport, exported_at: datetime) -> pd.DataFrame:
    rows: list[dict] = []
    if report.analyzable:
        overall = report.overall
        rows.append(
            _test_row(
                "Distribuição completa",
                None,
                f"{len(report.dungeons)} masmorras × {len(report.common_items)} itens comuns",
                overall.method,
                overall,
                masmorras_consideradas=", ".join(d.name for d in report.dungeons),
                interpretacao=interpret(overall.p_value, report.alpha),
                notas=overall.rationale,
            )
        )
        family = f"{len(report.per_item)} itens"
        for analysis in report.per_item:
            result = analysis.global_test
            rows.append(
                _test_row(
                    "Item (global)",
                    analysis.item,
                    f"{len(analysis.dungeons)} masmorras",
                    result.method,
                    result,
                    masmorras_consideradas=", ".join(analysis.dungeons),
                    p_ajustado_holm=analysis.p_holm_across_items,
                    familia_holm=family,
                    interpretacao=interpret(analysis.p_holm_across_items, report.alpha),
                    notas=result.rationale,
                )
            )
        for analysis in report.per_item:
            pair_family = f"{len(analysis.pairwise)} comparações de {analysis.item}"
            for pair in analysis.pairwise:
                effect = analysis.effects[(pair.a, pair.b)]
                odds_ci = effect.odds_ratio_ci or (None, None)
                rows.append(
                    _test_row(
                        "Item (par de masmorras)",
                        analysis.item,
                        f"{pair.a} vs {pair.b}",
                        pair.method,
                        masmorras_consideradas=f"{pair.a}, {pair.b}",
                        p_bruto=pair.p_raw,
                        p_ajustado_holm=pair.p_holm,
                        familia_holm=pair_family,
                        diferenca_pp=effect.diff_pp,
                        razao_proporcoes=effect.ratio,
                        odds_ratio=effect.odds_ratio,
                        odds_ratio_ic95_inferior=odds_ci[0],
                        odds_ratio_ic95_superior=odds_ci[1],
                        notas=" ".join(effect.notes),
                    )
                )
    for trend in report.trends:
        result = trend.result
        rows.append(
            _test_row(
                "Tendência por dificuldade (exploratória)",
                trend.item.display_name,
                f"{result.groups} níveis; direção {result.direction}",
                "Cochran-Armitage",
                masmorras_consideradas=", ".join(
                    name for group in trend.groups for name in group.dungeons
                ),
                amostra_n=result.n,
                estatistica=result.z,
                p_bruto=result.p_value,
                p_ajustado_holm=trend.p_holm,
                familia_holm=f"{len(report.trends)} itens",
                notas=result.rationale,
            )
        )
    return _stamp(pd.DataFrame(rows, columns=STATISTICS_COLUMNS), exported_at)


def distribution_frames(report: AnalysisReport) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Observado (todos os itens; células sem disponibilidade ficam vazias) e esperado.

    O esperado cobre apenas os itens comuns a todas as masmorras analisadas (base do teste).
    """
    labels = [f"{d.name} (n={report.runs_per_dungeon[d.id]})" for d in report.dungeons]
    observed = pd.DataFrame(
        report.matrix,
        index=labels,
        columns=[item.display_name for item in report.items],
        dtype=object,
    )
    for r in range(len(report.dungeons)):
        for c in range(len(report.items)):
            if not report.is_available(r, c) and report.matrix[r, c] == 0:
                observed.iat[r, c] = None
    common_names = [item.display_name for item in report.common_items]
    shape = (len(report.dungeons), len(common_names))
    expected_values = np.full(shape, np.nan)
    if report.analyzable and report.overall.expected is not None:
        if report.overall.expected.shape == shape:
            expected_values = report.overall.expected
    expected = pd.DataFrame(np.round(expected_values, 4), index=labels, columns=common_names)
    observed.index.name = expected.index.name = "masmorra"
    return observed.reset_index(), expected.reset_index()


def describe_filter(
    flt: RunFilter | None, dungeons: Sequence[Dungeon], items: Sequence[Item]
) -> list[tuple[str, str]]:
    if flt is None:
        return []
    lines: list[tuple[str, str]] = []
    if flt.date_from:
        lines.append(("Período: de", format_moment(flt.date_from)))
    if flt.date_to:
        lines.append(("Período: até", format_moment(flt.date_to)))
    if flt.dungeon_ids is not None:
        names = {d.id: d.name for d in dungeons}
        lines.append(("Masmorras", ", ".join(names.get(i, str(i)) for i in flt.dungeon_ids)))
    if flt.item_ids is not None:
        names = {i.id: i.display_name for i in items}
        lines.append(("Itens", ", ".join(names.get(i, str(i)) for i in flt.item_ids)))
    if flt.difficulties is not None:
        lines.append(("Dificuldades", ", ".join(str(d) for d in flt.difficulties)))
    if flt.bonus_status is not None:
        lines.append(("Bônus de drop", TRISTATE.get(flt.bonus_status, flt.bonus_status)))
    if flt.event_status is not None:
        lines.append(("Evento ativo", TRISTATE.get(flt.event_status, flt.event_status)))
    if flt.game_version is not None:
        lines.append(("Versão do jogo", flt.game_version))
    return lines
