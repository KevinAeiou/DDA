"""Autoverificação: exercita o aplicativo de ponta a ponta em um diretório temporário.

Usada para validar o executável empacotado (que não tem console): o resultado vai para um arquivo
JSON e o código de saída indica sucesso (0) ou falha (1). Nunca toca nos dados reais do usuário.
"""

from __future__ import annotations

import importlib
import json
import os
import platform
import sys
import tempfile
import traceback
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import dungeon_drop_analyzer

REQUIRED_MODULES = (
    "PySide6.QtWidgets",
    "matplotlib.backends.backend_qtagg",
    "numpy",
    "scipy.stats",
    "pandas",
    "openpyxl",
    "sqlalchemy",
    "alembic",
)


def _check_imports(context: dict) -> str:
    versions = []
    for name in REQUIRED_MODULES:
        module = importlib.import_module(name)
        versions.append(f"{name}={getattr(module, '__version__', 'ok')}")
    return ", ".join(versions)


def _check_database(context: dict) -> str:
    from dungeon_drop_analyzer.core.bootstrap import initialize
    from dungeon_drop_analyzer.core.config import Settings
    from dungeon_drop_analyzer.services import Services

    settings = Settings.load(context["workdir"] / "dados")
    context["settings"] = settings
    session_factory = initialize(settings)
    context["services"] = Services.create(session_factory)
    context["engine"] = session_factory.kw["bind"]
    if not settings.db_path.is_file():
        raise RuntimeError("O banco de dados não foi criado.")
    if getattr(sys, "frozen", False):
        executable_dir = Path(sys.executable).resolve().parent
        if executable_dir in settings.db_path.resolve().parents:
            raise RuntimeError("O banco de dados ficou dentro da pasta do executável.")
    return f"banco em {settings.db_path.name}"


def _check_data(context: dict) -> str:
    from dungeon_drop_analyzer.models import ItemCategory

    services = context["services"]
    dungeons = [services.dungeons.create(f"Masmorra {i}", i) for i in range(1, 6)]
    categories = list(ItemCategory)
    items = [services.items.create(f"Item {k}", categories[k % len(categories)]) for k in range(6)]
    for index, dungeon in enumerate(dungeons):
        for k in range(12):
            item = items[(k * (index + 1)) % len(items)]
            services.runs.register(
                dungeon.id,
                item.id,
                completed_at=datetime(2026, 1, 1 + k, 12, tzinfo=UTC),
            )
    total = services.runs.count()
    if total != 60:
        raise RuntimeError(f"Esperadas 60 incursões, encontradas {total}.")
    return f"{len(dungeons)} masmorras, {len(items)} itens, {total} incursões"


def _check_analysis(context: dict) -> str:
    services = context["services"]
    dashboard = services.analytics.dashboard()
    report = services.analytics.analyze(n_sim=500)
    if dashboard.total_runs != 60 or not report.analyzable:
        raise RuntimeError("Dashboard ou análise estatística inconsistentes.")
    return f"método {report.overall.method}, p = {report.overall.p_value:.4f}"


def _check_exports(context: dict) -> str:
    from openpyxl import load_workbook

    from dungeon_drop_analyzer.reports import (
        export_frequencies_csv,
        export_history_csv,
        export_report_xlsx,
        export_statistics_csv,
    )

    services, folder = context["services"], context["workdir"] / "exports"
    results = [
        export_history_csv(services, None, folder / "historico.csv"),
        export_frequencies_csv(services, None, folder / "frequencias.csv"),
        export_statistics_csv(services, None, folder / "estatisticas.csv"),
        export_report_xlsx(services, None, folder / "relatorio.xlsx"),
    ]
    for result in results:
        if not result.path.is_file() or result.path.stat().st_size == 0:
            raise RuntimeError(f"Exportação vazia: {result.path.name}")
    sheets = load_workbook(folder / "relatorio.xlsx").sheetnames
    if "Resumo" not in sheets:
        raise RuntimeError("O relatório XLSX não tem a aba Resumo.")
    return f"{len(results)} arquivos; abas do XLSX: {len(sheets)}"


def _check_backup(context: dict) -> str:
    services, workdir = context["services"], context["workdir"]
    destination = workdir / "backups" / "teste.db"
    info = services.backup.create_backup(destination)
    services.runs.delete(services.runs.list()[0].id)
    services.backup.restore(destination, workdir / "backups")
    if services.runs.count() != info.runs:
        raise RuntimeError("A restauração não devolveu os dados do backup.")
    return f"backup com {info.runs} incursões restaurado; cópia de segurança criada"


def _check_interface(context: dict) -> str:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    from dungeon_drop_analyzer.ui.pages import AnalysisPage, DashboardPage
    from dungeon_drop_analyzer.ui.windows import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow(context["services"], context["settings"])
    window.show()
    rendered = 0
    for name in window.pages:
        window.open_page(name)
        app.processEvents()
        if window.grab().isNull():
            raise RuntimeError(f"A página '{name}' não renderizou.")
        rendered += 1
    dashboard, analysis = window.pages["Dashboard"], window.pages["Análise estatística"]
    if not isinstance(dashboard, DashboardPage) or dashboard.timeline_chart.is_empty:
        raise RuntimeError("Os gráficos do dashboard não foram desenhados.")
    if not isinstance(analysis, AnalysisPage) or analysis.item_combo.count() == 0:
        raise RuntimeError("A análise estatística não listou itens.")
    dashboard.item_chart.draw()
    window.close()
    return f"{rendered} páginas renderizadas, gráficos desenhados"


STEPS: tuple[tuple[str, Callable[[dict], str]], ...] = (
    ("bibliotecas", _check_imports),
    ("banco de dados", _check_database),
    ("cadastros e incursões", _check_data),
    ("dashboard e análise", _check_analysis),
    ("exportações", _check_exports),
    ("backup e restauração", _check_backup),
    ("interface", _check_interface),
)


def execute() -> dict:
    report: dict = {
        "ok": True,
        "version": dungeon_drop_analyzer.__version__,
        "frozen": bool(getattr(sys, "frozen", False)),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "steps": [],
    }
    with tempfile.TemporaryDirectory(prefix="dda-selfcheck-", ignore_cleanup_errors=True) as tmp:
        context: dict = {"workdir": Path(tmp)}
        for name, step in STEPS:
            try:
                detail = step(context)
                report["steps"].append({"name": name, "ok": True, "detail": detail})
            except Exception as error:
                report["ok"] = False
                report["steps"].append(
                    {
                        "name": name,
                        "ok": False,
                        "detail": f"{type(error).__name__}: {error}",
                        "traceback": traceback.format_exc(),
                    }
                )
                break
        engine = context.get("engine")
        if engine is not None:
            engine.dispose()
    return report


def run_self_check(output: Path | str | None = None) -> int:
    report = execute()
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if output is not None:
        target = Path(output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    if sys.stdout is not None:
        print(text)
    return 0 if report["ok"] else 1
