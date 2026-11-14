"""Utilitários de data/hora: o armazenamento é sempre em UTC."""

from __future__ import annotations

from datetime import UTC, datetime


def utc_now() -> datetime:
    return datetime.now(UTC)


def ensure_aware(value: datetime) -> datetime:
    """Datas sem fuso são interpretadas como horário local da máquina."""
    if value.tzinfo is None:
        return value.astimezone()
    return value


def to_utc(value: datetime) -> datetime:
    return ensure_aware(value).astimezone(UTC)
