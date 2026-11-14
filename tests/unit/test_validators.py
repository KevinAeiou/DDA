"""Validadores de entrada."""

from datetime import UTC, datetime

import pytest

from dungeon_drop_analyzer.services.errors import ValidationError
from dungeon_drop_analyzer.services.validators import (
    clean_name,
    clean_optional_text,
    normalize_datetime,
    validate_bool,
    validate_difficulty,
    validate_duration,
    validate_id,
    validate_tristate,
)


def test_clean_name():
    assert clean_name("  Olá  ") == "Olá"
    for ruim in ("", " ", None, 3, "x" * 101):
        with pytest.raises(ValidationError):
            clean_name(ruim)


def test_clean_optional_text():
    assert clean_optional_text(None, "x") is None
    assert clean_optional_text("   ", "x") is None
    assert clean_optional_text(" a ", "x") == "a"
    with pytest.raises(ValidationError):
        clean_optional_text(5, "x")
    with pytest.raises(ValidationError):
        clean_optional_text("abcd", "x", max_length=3)


def test_validate_difficulty_duration_bool_id():
    assert [validate_difficulty(n) for n in range(1, 6)] == [1, 2, 3, 4, 5]
    assert validate_duration(None) is None and validate_duration(0) == 0
    assert validate_bool(False, "x") is False
    assert validate_id(7, "x") == 7
    for ruim, fn in [
        (0, validate_difficulty),
        (-1, validate_duration),
        (1, lambda v: validate_bool(v, "x")),
        (True, lambda v: validate_id(v, "x")),
        ([1], lambda v: validate_id(v, "x")),
    ]:
        with pytest.raises(ValidationError):
            fn(ruim)


def test_validate_tristate_e_datetime():
    assert validate_tristate("yes", "x") == "yes"
    with pytest.raises(ValidationError):
        validate_tristate("sim", "x")
    assert normalize_datetime(datetime(2026, 1, 1, tzinfo=UTC)).tzinfo is UTC
    with pytest.raises(ValidationError):
        normalize_datetime("ontem")
