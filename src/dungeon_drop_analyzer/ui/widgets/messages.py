"""Caixas de mensagem e execução protegida de casos de uso."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TypeVar

from PySide6.QtWidgets import QMessageBox, QWidget

from dungeon_drop_analyzer.services import DomainError

logger = logging.getLogger(__name__)

T = TypeVar("T")

APP_TITLE = "Dungeon Drop Analyzer"


def show_error(parent: QWidget | None, text: str) -> None:
    QMessageBox.warning(parent, APP_TITLE, text)


def show_info(parent: QWidget | None, text: str) -> None:
    QMessageBox.information(parent, APP_TITLE, text)


def confirm(parent: QWidget | None, text: str, yes_text: str = "Confirmar") -> bool:
    box = QMessageBox(QMessageBox.Icon.Question, APP_TITLE, text, parent=parent)
    yes = box.addButton(yes_text, QMessageBox.ButtonRole.YesRole)
    box.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
    box.exec()
    return box.clickedButton() is yes


def guarded(parent: QWidget | None, action: Callable[[], T]) -> tuple[bool, T | None]:
    """Executa a ação; erros de domínio viram aviso e erros inesperados são registrados em log."""
    try:
        return True, action()
    except DomainError as error:
        show_error(parent, str(error))
    except Exception:
        logger.exception("Erro inesperado")
        show_error(parent, "Ocorreu um erro inesperado. Consulte o log para detalhes.")
    return False, None
