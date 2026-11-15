"""Entidades ORM: masmorras, itens, incursões e trilha de auditoria."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, UTCDateTime, utc_default

NAME_LENGTH = 100


class TriState(enum.StrEnum):
    YES = "yes"
    NO = "no"
    UNKNOWN = "unknown"


class ItemCategory(enum.StrEnum):
    WEAPONS = "weapons"
    ARMOR = "armor"
    ACCESSORIES = "accessories"
    RELICS = "relics"
    AMPLIFICATION_RESOURCES = "amplification_resources"
    CRAFTING_RESOURCES = "crafting_resources"
    CONSUMABLES = "consumables"
    PRECIOUS_BARS = "precious_bars"

    @property
    def label(self) -> str:
        return CATEGORY_LABELS[self]


CATEGORY_LABELS = {
    ItemCategory.WEAPONS: "Armas",
    ItemCategory.ARMOR: "Armaduras",
    ItemCategory.ACCESSORIES: "Acessórios",
    ItemCategory.RELICS: "Relíquias",
    ItemCategory.AMPLIFICATION_RESOURCES: "Recursos de amplificação",
    ItemCategory.CRAFTING_RESOURCES: "Recursos de artesanato",
    ItemCategory.CONSUMABLES: "Consumíveis",
    ItemCategory.PRECIOUS_BARS: "Barras preciosas",
}

CATEGORY_CHECK = "category IN ({})".format(", ".join(f"'{c.value}'" for c in ItemCategory))


class AuditAction(enum.StrEnum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class Dungeon(Base):
    __tablename__ = "dungeons"
    __table_args__ = (CheckConstraint("difficulty BETWEEN 1 AND 5", name="difficulty"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(NAME_LENGTH, collation="NOCASE"), unique=True)
    difficulty: Mapped[int]
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True, server_default=text("1"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_default)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_default)

    runs: Mapped[list[Run]] = relationship(back_populates="dungeon")


class Item(Base):
    __tablename__ = "items"
    __table_args__ = (CheckConstraint(CATEGORY_CHECK, name="category"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(NAME_LENGTH, collation="NOCASE"), unique=True)
    category: Mapped[str] = mapped_column(String(NAME_LENGTH))
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True, server_default=text("1"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_default)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_default)

    runs: Mapped[list[Run]] = relationship(back_populates="item")


class Run(Base):
    __tablename__ = "runs"
    __table_args__ = (
        CheckConstraint("duration_seconds IS NULL OR duration_seconds >= 0", name="duration"),
        CheckConstraint("bonus_status IN ('yes', 'no', 'unknown')", name="bonus_status"),
        CheckConstraint("event_status IN ('yes', 'no', 'unknown')", name="event_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    dungeon_id: Mapped[int] = mapped_column(
        ForeignKey("dungeons.id", ondelete="RESTRICT"), index=True
    )
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="RESTRICT"), index=True)
    completed_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    duration_seconds: Mapped[int | None]
    game_version: Mapped[str | None] = mapped_column(String(NAME_LENGTH))
    bonus_status: Mapped[str] = mapped_column(
        String(10), default=TriState.UNKNOWN.value, server_default=TriState.UNKNOWN.value
    )
    event_status: Mapped[str] = mapped_column(
        String(10), default=TriState.UNKNOWN.value, server_default=TriState.UNKNOWN.value
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_default)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_default)

    dungeon: Mapped[Dungeon] = relationship(back_populates="runs")
    item: Mapped[Item] = relationship(back_populates="runs")


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        CheckConstraint("action IN ('create', 'update', 'delete')", name="action"),
        Index("ix_audit_log_entity", "entity_type", "entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(30))
    entity_id: Mapped[int]
    action: Mapped[str] = mapped_column(String(10))
    old_data: Mapped[str | None] = mapped_column(Text)
    new_data: Mapped[str | None] = mapped_column(Text)
    changed_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_default)
