"""Registro de auditoria na mesma transação da alteração auditada."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from dungeon_drop_analyzer.core.database import session_scope
from dungeon_drop_analyzer.models import AuditAction, AuditLog
from dungeon_drop_analyzer.models.base import Base
from dungeon_drop_analyzer.repositories import AuditRepository


def snapshot(entity: Base) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for column in inspect(entity).mapper.column_attrs:
        value = getattr(entity, column.key)
        data[column.key] = value.isoformat() if isinstance(value, datetime) else value
    return data


def record(
    session: Session,
    entity_type: str,
    entity_id: int,
    action: AuditAction,
    old: dict[str, Any] | None,
    new: dict[str, Any] | None,
    at: datetime,
) -> None:
    AuditRepository(session).add(
        AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action.value,
            old_data=json.dumps(old, ensure_ascii=False) if old is not None else None,
            new_data=json.dumps(new, ensure_ascii=False) if new is not None else None,
            changed_at=at,
        )
    )


class AuditTrailService:
    """Consulta da trilha de auditoria de uma entidade."""

    def __init__(self, session_factory) -> None:
        self._factory = session_factory

    def history(self, entity_type: str, entity_id: int) -> list[AuditLog]:
        with session_scope(self._factory) as session:
            return AuditRepository(session).list_for(entity_type, entity_id)
