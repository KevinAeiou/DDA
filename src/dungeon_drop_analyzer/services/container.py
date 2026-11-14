"""Agrupa os serviços de aplicação sobre uma mesma fábrica de sessões."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker

from dungeon_drop_analyzer.core.timeutils import utc_now

from .audit import AuditTrailService
from .catalog import Clock, DungeonService, ItemService
from .runs import RunService


@dataclass(frozen=True)
class Services:
    dungeons: DungeonService
    items: ItemService
    runs: RunService
    audit: AuditTrailService

    @classmethod
    def create(cls, session_factory: sessionmaker[Session], clock: Clock = utc_now) -> Services:
        return cls(
            dungeons=DungeonService(session_factory, clock),
            items=ItemService(session_factory, clock),
            runs=RunService(session_factory, clock),
            audit=AuditTrailService(session_factory),
        )
