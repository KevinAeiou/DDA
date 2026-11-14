"""Inicialização: diretórios, logging e banco migrado até a versão mais recente."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session, sessionmaker

from .config import Settings
from .database import create_db_engine, make_session_factory, upgrade_database
from .logging_setup import setup_logging


def initialize(settings: Settings) -> sessionmaker[Session]:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    setup_logging(settings.log_dir)
    engine = create_db_engine(settings.db_path)
    upgrade_database(engine)
    logging.getLogger(__name__).info("Banco inicializado em %s", settings.db_path)
    return make_session_factory(engine)
