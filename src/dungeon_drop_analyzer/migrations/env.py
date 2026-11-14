"""Ambiente do Alembic: usa a conexão fornecida por upgrade_database/downgrade_database."""

from alembic import context

from dungeon_drop_analyzer.models import Base

config = context.config
target_metadata = Base.metadata


def run_migrations_online() -> None:
    connection = config.attributes.get("connection")
    if connection is None:
        raise RuntimeError("Use upgrade_database() para executar as migrações.")
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


run_migrations_online()
