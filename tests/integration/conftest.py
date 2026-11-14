"""Fixtures de integração: bancos SQLite temporários (dados SINTÉTICOS)."""

from datetime import UTC, datetime, timedelta

import pytest

from dungeon_drop_analyzer.core.database import (
    create_db_engine,
    make_session_factory,
    upgrade_database,
)
from dungeon_drop_analyzer.services import (
    AuditTrailService,
    DungeonService,
    ItemService,
    RunService,
)


class FakeClock:
    def __init__(self) -> None:
        self.current = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        self.current += timedelta(seconds=1)
        return self.current


@pytest.fixture
def engine(tmp_path):
    engine = create_db_engine(tmp_path / "teste.db")
    upgrade_database(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def factory(engine):
    return make_session_factory(engine)


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def dungeons(factory, clock):
    return DungeonService(factory, clock)


@pytest.fixture
def items(factory, clock):
    return ItemService(factory, clock)


@pytest.fixture
def runs(factory, clock):
    return RunService(factory, clock)


@pytest.fixture
def audit_trail(factory):
    return AuditTrailService(factory)


@pytest.fixture
def seeded(dungeons, items):
    d = [dungeons.create(f"Masmorra {i}", i) for i in range(1, 6)]
    it = [items.create(name, category="sintético") for name in ("Item A", "Item B", "Item C")]
    return d, it
