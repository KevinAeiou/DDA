"""Validação e normalização de entradas."""

from __future__ import annotations

from datetime import datetime

from dungeon_drop_analyzer.core.timeutils import to_utc
from dungeon_drop_analyzer.models import TriState
from dungeon_drop_analyzer.models.entities import NAME_LENGTH

from .errors import ValidationError


def clean_name(value: object, label: str = "Nome") -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{label} é obrigatório.")
    name = value.strip()
    if len(name) > NAME_LENGTH:
        raise ValidationError(f"{label} deve ter no máximo {NAME_LENGTH} caracteres.")
    return name


def clean_optional_text(value: object, label: str, max_length: int | None = None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValidationError(f"{label} deve ser texto.")
    text = value.strip()
    if not text:
        return None
    if max_length is not None and len(text) > max_length:
        raise ValidationError(f"{label} deve ter no máximo {max_length} caracteres.")
    return text


def validate_difficulty(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5:
        raise ValidationError("Dificuldade deve ser um inteiro de 1 a 5.")
    return value


def validate_bool(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise ValidationError(f"{label} deve ser verdadeiro ou falso.")
    return value


def validate_duration(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValidationError("Duração deve ser um inteiro não negativo (segundos).")
    return value


def validate_tristate(value: object, label: str) -> str:
    try:
        return TriState(value).value
    except ValueError:
        raise ValidationError(f"{label} deve ser 'yes', 'no' ou 'unknown'.") from None


def normalize_datetime(value: object, label: str = "Data/hora") -> datetime:
    if not isinstance(value, datetime):
        raise ValidationError(f"{label} é obrigatória.")
    return to_utc(value)


def validate_id(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{label} deve ser um único identificador inteiro.")
    return value
