"""Engine SQLite com foreign keys, sessões transacionais e migrações Alembic."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def create_db_engine(db_path: Path | str) -> Engine:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{path.as_posix()}")

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    """Abre uma transação: confirma ao sair sem erro e desfaz em qualquer exceção."""
    session = factory()
    try:
        yield session
        session.commit()
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()


def _alembic_config() -> Config:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    return config


def _run_migration(engine: Engine, action) -> None:
    """Executa a migração com foreign keys desligadas (necessário para recriar tabelas no SQLite).

    Ao final, verifica a integridade referencial e religa as foreign keys.
    """
    config = _alembic_config()
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        connection.commit()
        try:
            with connection.begin():
                config.attributes["connection"] = connection
                action(config)
                violations = connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
                if violations:
                    raise RuntimeError(f"Migração violaria a integridade referencial: {violations}")
        finally:
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            connection.commit()


def upgrade_database(engine: Engine, revision: str = "head") -> None:
    _run_migration(engine, lambda config: command.upgrade(config, revision))


def downgrade_database(engine: Engine, revision: str) -> None:
    _run_migration(engine, lambda config: command.downgrade(config, revision))
