"""Exportação de CSV e XLSX respeitando os filtros e registrando a data/hora da exportação."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

import dungeon_drop_analyzer
from dungeon_drop_analyzer.core.timeutils import utc_now
from dungeon_drop_analyzer.repositories import RunFilter
from dungeon_drop_analyzer.services import ExportError, Services
from dungeon_drop_analyzer.services.analytics import LIMITATION_NOTES

from .frames import (
    METHOD_NAMES,
    describe_filter,
    distribution_frames,
    format_moment,
    frequencies_frame,
    history_frame,
    statistics_frame,
)

logger = logging.getLogger(__name__)

CSV_OPTIONS = {"sep": ";", "decimal": ",", "encoding": "utf-8-sig", "index": False}
PERCENT_COLUMNS = {"proporcao", "ic95_inferior", "ic95_superior"}
PVALUE_COLUMNS = {"p_bruto", "p_ajustado_holm"}


@dataclass(frozen=True)
class ExportResult:
    path: Path
    rows: int
    exported_at: datetime


def _prepare(path: Path | str) -> Path:
    target = Path(path)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise ExportError(f"Não foi possível usar a pasta de destino: {error}") from error
    return target


def _write_csv(frame: pd.DataFrame, path: Path) -> None:
    try:
        frame.to_csv(path, **CSV_OPTIONS)
    except PermissionError:
        raise ExportError(
            "Não foi possível gravar o arquivo. Verifique se ele não está aberto em outro programa."
        ) from None
    except OSError as error:
        raise ExportError(f"Não foi possível gravar o arquivo: {error}") from error


def _all_runs(services: Services, flt: RunFilter | None):
    return services.runs.list(flt, descending=False)


def export_history_csv(
    services: Services, flt: RunFilter | None, path: Path | str, now: datetime | None = None
) -> ExportResult:
    exported_at = now or utc_now()
    target = _prepare(path)
    frame = history_frame(_all_runs(services, flt), exported_at)
    _write_csv(frame, target)
    logger.info("Histórico exportado para %s (%s linhas)", target, len(frame))
    return ExportResult(target, len(frame), exported_at)


def export_frequencies_csv(
    services: Services, flt: RunFilter | None, path: Path | str, now: datetime | None = None
) -> ExportResult:
    exported_at = now or utc_now()
    target = _prepare(path)
    frame = frequencies_frame(services.analytics.analyze(flt), exported_at)
    _write_csv(frame, target)
    logger.info("Frequências exportadas para %s (%s linhas)", target, len(frame))
    return ExportResult(target, len(frame), exported_at)


def export_statistics_csv(
    services: Services, flt: RunFilter | None, path: Path | str, now: datetime | None = None
) -> ExportResult:
    exported_at = now or utc_now()
    target = _prepare(path)
    frame = statistics_frame(services.analytics.analyze(flt), exported_at)
    _write_csv(frame, target)
    logger.info("Resultados estatísticos exportados para %s (%s linhas)", target, len(frame))
    return ExportResult(target, len(frame), exported_at)


def _summary_frame(services: Services, flt, report, history_rows, exported_at) -> pd.DataFrame:
    dungeons = services.dungeons.list()
    items = services.items.list()
    filters = describe_filter(flt, dungeons, items)
    rows = [
        ("Aplicativo", f"Dungeon Drop Analyzer {dungeon_drop_analyzer.__version__}"),
        ("Exportado em", format_moment(exported_at)),
        ("Incursões na amostra (n)", str(report.sample_size)),
        ("Linhas do histórico exportadas", str(history_rows)),
        ("Masmorras com dados", str(len(report.dungeons))),
        ("Itens distintos obtidos", str(len(report.items))),
        ("Nível de significância", str(report.alpha).replace(".", ",")),
        ("Amostra mínima por masmorra (piloto)", str(report.min_n)),
    ]
    if report.analyzable:
        overall = report.overall
        rows.append(
            ("Método da distribuição completa", METHOD_NAMES.get(overall.method, overall.method))
        )
        if overall.n_sim is not None:
            rows.append(("Simulações / semente", f"{overall.n_sim} / {overall.seed}"))
    if report.undefined_items:
        names = ", ".join(i.name for i in report.undefined_items)
        rows.append(
            ("Aviso: itens sem masmorras definidas (tratados como disponíveis em todas)", names)
        )
    if report.inconsistent_runs:
        total = sum(r.count for r in report.inconsistent_runs)
        rows.append(
            (
                "Aviso: incursões fora das masmorras do item (excluídas da análise do item)",
                str(total),
            )
        )
    rows.append(("Filtros aplicados", "Nenhum" if not filters else ""))
    rows += [(f"  {label}", value) for label, value in filters]
    rows += [("Limitação", note) for note in LIMITATION_NOTES]
    return pd.DataFrame(rows, columns=["campo", "valor"])


def _format_sheet(worksheet, frame: pd.DataFrame) -> None:
    for cell in worksheet[1]:
        cell.font = Font(bold=True)
    worksheet.freeze_panes = "A2"
    for index, column in enumerate(frame.columns, start=1):
        values = [str(column)] + [str(v) for v in frame[column].head(200).tolist()]
        worksheet.column_dimensions[get_column_letter(index)].width = min(
            max(len(v) for v in values) + 2, 60
        )
        number_format = (
            "0.00%" if column in PERCENT_COLUMNS else "0.0000" if column in PVALUE_COLUMNS else None
        )
        if number_format:
            for cell in worksheet[get_column_letter(index)][1:]:
                cell.number_format = number_format


def export_report_xlsx(
    services: Services, flt: RunFilter | None, path: Path | str, now: datetime | None = None
) -> ExportResult:
    """Relatório consolidado: resumo, histórico, frequências, resultados e distribuições."""
    exported_at = now or utc_now()
    target = _prepare(path)
    runs = _all_runs(services, flt)
    report = services.analytics.analyze(flt)
    observed, expected = distribution_frames(report)
    sheets = {
        "Resumo": _summary_frame(services, flt, report, len(runs), exported_at),
        "Histórico": history_frame(runs, exported_at),
        "Frequências": frequencies_frame(report, exported_at),
        "Resultados estatísticos": statistics_frame(report, exported_at),
        "Distribuição observada": observed,
        "Distribuição esperada": expected,
    }
    try:
        with pd.ExcelWriter(target, engine="openpyxl") as writer:
            for name, frame in sheets.items():
                frame.to_excel(writer, sheet_name=name, index=False)
                _format_sheet(writer.sheets[name], frame)
    except PermissionError:
        raise ExportError(
            "Não foi possível gravar o arquivo. Verifique se ele não está aberto em outro programa."
        ) from None
    except OSError as error:
        raise ExportError(f"Não foi possível gravar o arquivo: {error}") from error
    logger.info("Relatório XLSX exportado para %s", target)
    return ExportResult(target, len(runs), exported_at)
