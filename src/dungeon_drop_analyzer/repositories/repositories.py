"""Consultas e persistência. Os repositórios recebem uma Session e não confirmam transações."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, joinedload

from dungeon_drop_analyzer.core.timeutils import to_utc
from dungeon_drop_analyzer.models import (
    AuditLog,
    Dungeon,
    Item,
    Run,
    assign_display_names,
    item_dungeons,
)


class DungeonRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, dungeon: Dungeon) -> Dungeon:
        self.session.add(dungeon)
        self.session.flush()
        return dungeon

    def get(self, dungeon_id: int) -> Dungeon | None:
        return self.session.get(Dungeon, dungeon_id)

    def get_by_name(self, name: str) -> Dungeon | None:
        return self.session.scalars(select(Dungeon).where(Dungeon.name == name)).first()

    def list(self, active_only: bool = False) -> list[Dungeon]:
        stmt = select(Dungeon).order_by(Dungeon.difficulty, Dungeon.name)
        if active_only:
            stmt = stmt.where(Dungeon.is_active.is_(True))
        return list(self.session.scalars(stmt))


class ItemRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, item: Item) -> Item:
        self.session.add(item)
        self.session.flush()
        return item

    def get(self, item_id: int) -> Item | None:
        return self.session.get(Item, item_id)

    def get_by_name(self, name: str, category: str) -> Item | None:
        stmt = select(Item).where(Item.name == name, Item.category == category)
        return self.session.scalars(stmt).first()

    def dungeon_map(self) -> dict[int, set[int]]:
        """Masmorras cadastradas para cada item (itens sem masmorras definidas ficam ausentes)."""
        mapping: dict[int, set[int]] = {}
        for item_id, dungeon_id in self.session.execute(
            select(item_dungeons.c.item_id, item_dungeons.c.dungeon_id)
        ):
            mapping.setdefault(item_id, set()).add(dungeon_id)
        return mapping

    def list(self, active_only: bool = False) -> list[Item]:
        items = list(self.session.scalars(select(Item).order_by(Item.name, Item.category)))
        assign_display_names(items)
        return [item for item in items if item.is_active] if active_only else items


@dataclass(frozen=True)
class RunFilter:
    date_from: datetime | None = None
    date_to: datetime | None = None
    dungeon_ids: Sequence[int] | None = None
    item_ids: Sequence[int] | None = None
    difficulties: Sequence[int] | None = None
    bonus_status: str | None = None
    event_status: str | None = None
    game_version: str | None = None


class RunRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, run: Run) -> Run:
        self.session.add(run)
        self.session.flush()
        return run

    def get(self, run_id: int) -> Run | None:
        run = self.session.scalars(
            select(Run)
            .options(joinedload(Run.dungeon), joinedload(Run.item))
            .where(Run.id == run_id)
        ).first()
        if run is not None:
            ItemRepository(self.session).list()
        return run

    def delete(self, run: Run) -> None:
        self.session.delete(run)
        self.session.flush()

    @staticmethod
    def _apply(stmt: Select, flt: RunFilter | None) -> Select:
        if flt is None:
            return stmt
        if flt.date_from is not None:
            stmt = stmt.where(Run.completed_at >= to_utc(flt.date_from))
        if flt.date_to is not None:
            stmt = stmt.where(Run.completed_at <= to_utc(flt.date_to))
        if flt.dungeon_ids is not None:
            stmt = stmt.where(Run.dungeon_id.in_(list(flt.dungeon_ids)))
        if flt.item_ids is not None:
            stmt = stmt.where(Run.item_id.in_(list(flt.item_ids)))
        if flt.difficulties is not None:
            stmt = stmt.where(Run.dungeon.has(Dungeon.difficulty.in_(list(flt.difficulties))))
        if flt.bonus_status is not None:
            stmt = stmt.where(Run.bonus_status == flt.bonus_status)
        if flt.event_status is not None:
            stmt = stmt.where(Run.event_status == flt.event_status)
        if flt.game_version is not None:
            stmt = stmt.where(Run.game_version == flt.game_version)
        return stmt

    def list(
        self,
        flt: RunFilter | None = None,
        descending: bool = True,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Run]:
        stmt = self._apply(select(Run).options(joinedload(Run.dungeon), joinedload(Run.item)), flt)
        order = (
            (Run.completed_at.desc(), Run.id.desc()) if descending else (Run.completed_at, Run.id)
        )
        stmt = stmt.order_by(*order).offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        runs = list(self.session.scalars(stmt).unique())
        ItemRepository(self.session).list()
        return runs

    def count_matrix(self, flt: RunFilter | None = None) -> list[tuple[int, int, int]]:
        stmt = self._apply(
            select(Run.dungeon_id, Run.item_id, func.count(Run.id)).group_by(
                Run.dungeon_id, Run.item_id
            ),
            flt,
        )
        return [(d, i, int(c)) for d, i, c in self.session.execute(stmt)]

    def timeline(self, flt: RunFilter | None = None) -> list[tuple[datetime, int]]:
        stmt = self._apply(select(Run.completed_at, Run.dungeon_id), flt)
        return [(when, dungeon_id) for when, dungeon_id in self.session.execute(stmt)]

    def count_item_in_dungeon(self, item_id: int, dungeon_id: int) -> int:
        stmt = select(func.count(Run.id)).where(
            Run.item_id == item_id, Run.dungeon_id == dungeon_id
        )
        return int(self.session.scalar(stmt) or 0)

    def distinct_game_versions(self) -> list[str]:
        stmt = (
            select(Run.game_version)
            .where(Run.game_version.is_not(None))
            .distinct()
            .order_by(Run.game_version)
        )
        return list(self.session.scalars(stmt))

    def count(self, flt: RunFilter | None = None) -> int:
        stmt = self._apply(select(func.count(Run.id)), flt)
        return int(self.session.scalar(stmt) or 0)


class AuditRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, entry: AuditLog) -> AuditLog:
        self.session.add(entry)
        self.session.flush()
        return entry

    def list_for(self, entity_type: str, entity_id: int) -> list[AuditLog]:
        stmt = (
            select(AuditLog)
            .where(AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id)
            .order_by(AuditLog.id)
        )
        return list(self.session.scalars(stmt))
