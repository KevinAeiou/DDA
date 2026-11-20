"""Casos de uso de incursões: registro, histórico, correção e exclusão com auditoria."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from dungeon_drop_analyzer.core.database import session_scope
from dungeon_drop_analyzer.core.timeutils import utc_now
from dungeon_drop_analyzer.models import AuditAction, Dungeon, Item, Run, TriState
from dungeon_drop_analyzer.models.entities import NAME_LENGTH
from dungeon_drop_analyzer.repositories import (
    DungeonRepository,
    ItemRepository,
    RunFilter,
    RunRepository,
)

from . import audit
from .errors import NotFoundError, ValidationError
from .validators import (
    clean_optional_text,
    normalize_datetime,
    validate_duration,
    validate_id,
    validate_tristate,
)

logger = logging.getLogger(__name__)

Clock = Callable[[], datetime]

EDITABLE_FIELDS = {
    "dungeon_id",
    "item_id",
    "completed_at",
    "duration_seconds",
    "game_version",
    "bonus_status",
    "event_status",
    "notes",
}


class RunService:
    def __init__(self, session_factory: sessionmaker[Session], clock: Clock = utc_now) -> None:
        self._factory = session_factory
        self._clock = clock

    @staticmethod
    def _active_dungeon(session: Session, dungeon_id: int) -> Dungeon:
        dungeon = DungeonRepository(session).get(dungeon_id)
        if dungeon is None:
            raise NotFoundError("Masmorra não encontrada.")
        if not dungeon.is_active:
            raise ValidationError(f"A masmorra '{dungeon.name}' está inativa.")
        return dungeon

    @staticmethod
    def _active_item(session: Session, item_id: int) -> Item:
        item = ItemRepository(session).get(item_id)
        if item is None:
            raise NotFoundError("Item não encontrado.")
        if not item.is_active:
            raise ValidationError(f"O item '{item.display_name}' está inativo.")
        return item

    @staticmethod
    def _check_availability(item: Item, dungeon: Dungeon) -> None:
        """Itens com masmorras definidas só podem ser registrados nelas (sem definição = livre)."""
        allowed = {d.id for d in item.dungeons}
        if allowed and dungeon.id not in allowed:
            names = ", ".join(d.name for d in item.dungeons)
            raise ValidationError(
                f"O item '{item.display_name}' não pode ser obtido na masmorra '{dungeon.name}'. "
                f"Masmorras do item: {names}."
            )

    def register(
        self,
        dungeon_id: int,
        item_id: int,
        completed_at: datetime | None = None,
        duration_seconds: int | None = None,
        game_version: str | None = None,
        bonus_status: str = TriState.UNKNOWN.value,
        event_status: str = TriState.UNKNOWN.value,
        notes: str | None = None,
    ) -> Run:
        """Registra uma incursão concluída com exatamente um item, em uma transação."""
        dungeon_id = validate_id(dungeon_id, "Masmorra")
        item_id = validate_id(item_id, "Item")
        now = self._clock()
        values = {
            "completed_at": normalize_datetime(completed_at if completed_at is not None else now),
            "duration_seconds": validate_duration(duration_seconds),
            "game_version": clean_optional_text(game_version, "Versão do jogo", NAME_LENGTH),
            "bonus_status": validate_tristate(bonus_status, "Bônus de drop"),
            "event_status": validate_tristate(event_status, "Evento ativo"),
            "notes": clean_optional_text(notes, "Observações"),
        }
        with session_scope(self._factory) as session:
            dungeon = self._active_dungeon(session, dungeon_id)
            item = self._active_item(session, item_id)
            self._check_availability(item, dungeon)
            run = RunRepository(session).add(
                Run(dungeon=dungeon, item=item, created_at=now, updated_at=now, **values)
            )
            audit.record(session, "run", run.id, AuditAction.CREATE, None, audit.snapshot(run), now)
        logger.info("Incursão registrada: id=%s", run.id)
        return run

    def update(self, run_id: int, **changes: Any) -> Run:
        """Corrige uma incursão; apenas campos realmente alterados geram auditoria."""
        unknown = set(changes) - EDITABLE_FIELDS
        if unknown:
            raise ValidationError(f"Campos não editáveis: {', '.join(sorted(unknown))}.")
        cleaners: dict[str, Callable[[Any], Any]] = {
            "dungeon_id": lambda v: validate_id(v, "Masmorra"),
            "item_id": lambda v: validate_id(v, "Item"),
            "completed_at": normalize_datetime,
            "duration_seconds": validate_duration,
            "game_version": lambda v: clean_optional_text(v, "Versão do jogo", NAME_LENGTH),
            "bonus_status": lambda v: validate_tristate(v, "Bônus de drop"),
            "event_status": lambda v: validate_tristate(v, "Evento ativo"),
            "notes": lambda v: clean_optional_text(v, "Observações"),
        }
        cleaned = {key: cleaners[key](value) for key, value in changes.items()}
        with session_scope(self._factory) as session:
            run = RunRepository(session).get(run_id)
            if run is None:
                raise NotFoundError("Incursão não encontrada.")
            old = audit.snapshot(run)
            changed = {k: v for k, v in cleaned.items() if getattr(run, k) != v}
            if not changed:
                return run
            relation_changed = "dungeon_id" in changed or "item_id" in changed
            if "dungeon_id" in changed:
                run.dungeon = self._active_dungeon(session, changed.pop("dungeon_id"))
            if "item_id" in changed:
                run.item = self._active_item(session, changed.pop("item_id"))
            if relation_changed:
                self._check_availability(run.item, run.dungeon)
            for key, value in changed.items():
                setattr(run, key, value)
            now = self._clock()
            run.updated_at = now
            session.flush()
            audit.record(session, "run", run.id, AuditAction.UPDATE, old, audit.snapshot(run), now)
        logger.info("Incursão atualizada: id=%s", run.id)
        return run

    def delete(self, run_id: int) -> None:
        with session_scope(self._factory) as session:
            repo = RunRepository(session)
            run = repo.get(run_id)
            if run is None:
                raise NotFoundError("Incursão não encontrada.")
            old = audit.snapshot(run)
            repo.delete(run)
            audit.record(session, "run", run_id, AuditAction.DELETE, old, None, self._clock())
        logger.info("Incursão excluída: id=%s", run_id)

    def get(self, run_id: int) -> Run:
        with session_scope(self._factory) as session:
            run = RunRepository(session).get(run_id)
            if run is None:
                raise NotFoundError("Incursão não encontrada.")
            return run

    def list(
        self,
        flt: RunFilter | None = None,
        descending: bool = True,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Run]:
        with session_scope(self._factory) as session:
            return RunRepository(session).list(flt, descending, limit, offset)

    def game_versions(self) -> list[str]:
        with session_scope(self._factory) as session:
            return RunRepository(session).distinct_game_versions()

    def count(self, flt: RunFilter | None = None) -> int:
        with session_scope(self._factory) as session:
            return RunRepository(session).count(flt)
