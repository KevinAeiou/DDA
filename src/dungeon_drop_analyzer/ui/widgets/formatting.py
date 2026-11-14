"""Formatação de valores para exibição em português do Brasil."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QDateTime

TRISTATE_LABELS = {"yes": "Sim", "no": "Não", "unknown": "Desconhecido"}
DATETIME_FORMAT = "%d/%m/%Y %H:%M:%S"
QT_DATETIME_FORMAT = "dd/MM/yyyy HH:mm:ss"


def to_local_naive(value: datetime) -> datetime:
    return value.astimezone().replace(tzinfo=None)


def format_datetime(value: datetime) -> str:
    return to_local_naive(value).strftime(DATETIME_FORMAT)


def format_duration(seconds: int | None) -> str:
    if seconds is None:
        return ""
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def format_tristate(value: str) -> str:
    return TRISTATE_LABELS.get(value, value)


def format_bool(value: bool) -> str:
    return "Sim" if value else "Não"


def to_qdatetime(value: datetime) -> QDateTime:
    return QDateTime(value.year, value.month, value.day, value.hour, value.minute, value.second)


def now_qdatetime() -> QDateTime:
    return QDateTime.currentDateTime()
