"""Casos de uso de cadastro: masmorras e itens (sem exclusão; apenas inativação)."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from dungeon_drop_analyzer.core.database import session_scope
from dungeon_drop_analyzer.core.timeutils import utc_now
from dungeon_drop_analyzer.models import AuditAction, Dungeon, Item, ItemCategory
from dungeon_drop_analyzer.repositories import DungeonRepository, ItemRepository

from . import audit
from .errors import DuplicateError, NotFoundError, ValidationError
from .validators import (
    clean_name,
    clean_optional_text,
    validate_bool,
    validate_category,
    validate_difficulty,
)

logger = logging.getLogger(__name__)

Clock = Callable[[], datetime]


class _CatalogService:
    entity_type: str
    label: str
    entity_cls: type
    repo_cls: type
    validators: dict[str, Callable[[Any], Any]]

    def __init__(self, session_factory: sessionmaker[Session], clock: Clock = utc_now) -> None:
        self._factory = session_factory
        self._clock = clock

    def _repo(self, session: Session):
        return self.repo_cls(session)

    def _load(self, session: Session, entity_id: int):
        entity = self._repo(session).get(entity_id)
        if entity is None:
            raise NotFoundError(f"{self.label} não encontrado(a).")
        return entity

    def _ensure_unique_name(self, session: Session, name: str, ignore_id: int | None) -> None:
        existing = self._repo(session).get_by_name(name)
        if existing is not None and existing.id != ignore_id:
            raise DuplicateError(f"Já existe {self.label.lower()} com o nome '{name}'.")

    def _create(self, values: dict[str, Any]):
        values = {key: self.validators[key](value) for key, value in values.items()}
        with session_scope(self._factory) as session:
            self._ensure_unique_name(session, values["name"], None)
            now = self._clock()
            entity = self._repo(session).add(
                self.entity_cls(**values, created_at=now, updated_at=now)
            )
            audit.record(
                session,
                self.entity_type,
                entity.id,
                AuditAction.CREATE,
                None,
                audit.snapshot(entity),
                now,
            )
        logger.info("%s criado(a): id=%s", self.label, entity.id)
        return entity

    def update(self, entity_id: int, **changes: Any):
        unknown = set(changes) - set(self.validators)
        if unknown:
            raise ValidationError(f"Campos não editáveis: {', '.join(sorted(unknown))}.")
        cleaned = {key: self.validators[key](value) for key, value in changes.items()}
        with session_scope(self._factory) as session:
            entity = self._load(session, entity_id)
            if "name" in cleaned:
                self._ensure_unique_name(session, cleaned["name"], entity.id)
            old = audit.snapshot(entity)
            changed = {k: v for k, v in cleaned.items() if getattr(entity, k) != v}
            if not changed:
                return entity
            for key, value in changed.items():
                setattr(entity, key, value)
            now = self._clock()
            entity.updated_at = now
            session.flush()
            audit.record(
                session,
                self.entity_type,
                entity.id,
                AuditAction.UPDATE,
                old,
                audit.snapshot(entity),
                now,
            )
        logger.info("%s atualizado(a): id=%s campos=%s", self.label, entity.id, sorted(changed))
        return entity

    def set_active(self, entity_id: int, active: bool):
        return self.update(entity_id, is_active=active)

    def get(self, entity_id: int):
        with session_scope(self._factory) as session:
            return self._load(session, entity_id)

    def list(self, active_only: bool = False) -> list:
        with session_scope(self._factory) as session:
            return self._repo(session).list(active_only=active_only)


class DungeonService(_CatalogService):
    entity_type = "dungeon"
    label = "Masmorra"
    entity_cls = Dungeon
    repo_cls = DungeonRepository
    validators = {
        "name": lambda v: clean_name(v, "Nome da masmorra"),
        "difficulty": validate_difficulty,
        "description": lambda v: clean_optional_text(v, "Descrição"),
        "is_active": lambda v: validate_bool(v, "Ativa"),
    }

    def create(
        self,
        name: str,
        difficulty: int,
        description: str | None = None,
        is_active: bool = True,
    ) -> Dungeon:
        return self._create(
            {
                "name": name,
                "difficulty": difficulty,
                "description": description,
                "is_active": is_active,
            }
        )


class ItemService(_CatalogService):
    entity_type = "item"
    label = "Item"
    entity_cls = Item
    repo_cls = ItemRepository
    validators = {
        "name": lambda v: clean_name(v, "Nome do item"),
        "category": validate_category,
        "description": lambda v: clean_optional_text(v, "Descrição"),
        "is_active": lambda v: validate_bool(v, "Ativo"),
    }

    def create(
        self,
        name: str,
        category: ItemCategory | str,
        description: str | None = None,
        is_active: bool = True,
    ) -> Item:
        return self._create(
            {
                "name": name,
                "category": category,
                "description": description,
                "is_active": is_active,
            }
        )
