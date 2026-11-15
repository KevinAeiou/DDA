"""Fixtures de UI: Qt em modo offscreen, banco temporário e caixas de mensagem interceptadas."""

import importlib
import os
import sys
from datetime import UTC, datetime, timedelta

import pytest
from PySide6.QtWidgets import QApplication

from dungeon_drop_analyzer.core.config import Settings
from dungeon_drop_analyzer.core.database import (
    create_db_engine,
    make_session_factory,
    upgrade_database,
)
from dungeon_drop_analyzer.services import Services


@pytest.fixture(scope="session")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    return QApplication.instance() or QApplication([])


class Clock:
    def __init__(self) -> None:
        self.current = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        self.current += timedelta(seconds=1)
        return self.current


@pytest.fixture
def services(tmp_path):
    engine = create_db_engine(tmp_path / "ui.db")
    upgrade_database(engine)
    yield Services.create(make_session_factory(engine), Clock())
    engine.dispose()


@pytest.fixture
def settings(tmp_path):
    return Settings.load(tmp_path / "dados")


class Dialogs:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.confirm_answer = True
        self.confirmations: list[str] = []


@pytest.fixture
def dialogs(monkeypatch, qapp):
    """Intercepta avisos e confirmações em todos os módulos da interface."""
    importlib.import_module("dungeon_drop_analyzer.ui.windows")
    state = Dialogs()

    def fake_error(parent, text):
        state.errors.append(text)

    def fake_confirm(parent, text, yes_text="Confirmar"):
        state.confirmations.append(text)
        return state.confirm_answer

    for name, module in list(sys.modules.items()):
        if not name.startswith("dungeon_drop_analyzer.ui") or module is None:
            continue
        if hasattr(module, "show_error"):
            monkeypatch.setattr(module, "show_error", fake_error)
        if hasattr(module, "confirm"):
            monkeypatch.setattr(module, "confirm", fake_confirm)
    return state


@pytest.fixture
def seeded(services):
    dungeons = [services.dungeons.create(f"Masmorra {i}", i) for i in range(1, 6)]
    items = [services.items.create(n, "weapons") for n in ("Espada", "Escudo", "Anel")]
    return dungeons, items
