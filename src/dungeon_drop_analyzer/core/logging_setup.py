"""Logging local com arquivo rotativo."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOGGER_NAME = "dungeon_drop_analyzer"
LOG_FILE_NAME = "dda.log"
MAX_BYTES = 1_000_000
BACKUP_COUNT = 5
_HANDLER_MARK = "_dda_handler"


def setup_logging(log_dir: Path, level: int = logging.INFO) -> logging.Logger:
    """Configura o logger do pacote; chamadas repetidas não duplicam handlers."""
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    target = str((log_dir / LOG_FILE_NAME).resolve())
    for handler in list(logger.handlers):
        if getattr(handler, _HANDLER_MARK, False):
            if getattr(handler, "baseFilename", None) == target:
                return logger
            logger.removeHandler(handler)
            handler.close()
    handler = RotatingFileHandler(
        target, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    setattr(handler, _HANDLER_MARK, True)
    logger.addHandler(handler)
    return logger
