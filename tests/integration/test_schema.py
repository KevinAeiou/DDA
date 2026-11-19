"""Migrações, constraints e integridade referencial do esquema SQLite."""

from datetime import UTC, datetime

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from dungeon_drop_analyzer.core.database import (
    create_db_engine,
    downgrade_database,
    upgrade_database,
)
from dungeon_drop_analyzer.models import Base, Dungeon, Item, Run
from dungeon_drop_analyzer.models.base import UTCDateTime

AGORA = datetime(2026, 1, 1, tzinfo=UTC)


def test_migracao_gera_esquema_identico_aos_modelos(engine):
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diff == []


def test_upgrade_e_idempotente_e_downgrade_remove_tudo(engine):
    upgrade_database(engine)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar() == "0004"
    downgrade_database(engine, "base")
    assert set(inspect(engine).get_table_names()) <= {"alembic_version"}


def test_foreign_keys_habilitadas(engine):
    with engine.connect() as conn:
        assert conn.execute(text("PRAGMA foreign_keys")).scalar() == 1


def test_indices_exigidos(engine):
    nomes = {i["name"] for i in inspect(engine).get_indexes("runs")}
    assert {"ix_runs_completed_at", "ix_runs_dungeon_id", "ix_runs_item_id"} <= nomes


def _inserir_run(conn, dungeon_id, item_id, **extra):
    campos = {
        "dungeon_id": dungeon_id,
        "item_id": item_id,
        "completed_at": "2026-01-01 00:00:00",
        "created_at": "2026-01-01 00:00:00",
        "updated_at": "2026-01-01 00:00:00",
        **extra,
    }
    conn.execute(
        text(
            f"INSERT INTO runs ({', '.join(campos)}) VALUES ({', '.join(':' + k for k in campos)})"
        ),
        campos,
    )


def test_fk_invalida_e_rejeitada(engine):
    with pytest.raises(IntegrityError), engine.begin() as conn:
        _inserir_run(conn, 999, 999)


def test_nao_exclui_masmorra_ou_item_referenciados(factory):
    with factory() as s:
        d, i = (
            Dungeon(name="D", difficulty=1, created_at=AGORA, updated_at=AGORA),
            Item(name="I", category="weapons", created_at=AGORA, updated_at=AGORA),
        )
        s.add(Run(dungeon=d, item=i, completed_at=AGORA, created_at=AGORA, updated_at=AGORA))
        s.commit()
        s.delete(d)
        with pytest.raises(IntegrityError):
            s.commit()
        s.rollback()
        s.delete(i)
        with pytest.raises(IntegrityError):
            s.commit()


@pytest.mark.parametrize("dificuldade", [0, 6, -1])
def test_dificuldade_fora_do_intervalo_rejeitada(engine, dificuldade):
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO dungeons (name, difficulty, created_at, updated_at) "
                "VALUES ('X', :d, '2026-01-01', '2026-01-01')"
            ),
            {"d": dificuldade},
        )


@pytest.mark.parametrize(
    "extra",
    [{"duration_seconds": -1}, {"bonus_status": "talvez"}, {"event_status": "talvez"}],
)
def test_checks_de_incursao(engine, extra):
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO dungeons (name, difficulty, created_at, updated_at) "
                "VALUES ('D', 1, '2026-01-01', '2026-01-01')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO items (name, category, created_at, updated_at) "
                "VALUES ('I', 'weapons', '2026-01-01', '2026-01-01')"
            )
        )
    with pytest.raises(IntegrityError), engine.begin() as conn:
        _inserir_run(conn, 1, 1, **extra)


def test_nome_unico_sem_diferenciar_maiusculas(factory):
    with factory() as s:
        s.add(Dungeon(name="Caverna", difficulty=1, created_at=AGORA, updated_at=AGORA))
        s.commit()
        s.add(Dungeon(name="CAVERNA", difficulty=2, created_at=AGORA, updated_at=AGORA))
        with pytest.raises(IntegrityError):
            s.commit()


def test_utc_datetime_exige_fuso_e_devolve_utc(factory):
    with pytest.raises(ValueError):
        UTCDateTime().process_bind_param(datetime(2026, 1, 1), None)
    with factory() as s:
        s.add(Item(name="I", category="weapons", created_at=AGORA, updated_at=AGORA))
        s.commit()
    with factory() as s:
        item = s.query(Item).one()
        assert item.created_at == AGORA and item.created_at.tzinfo is not None


def test_persistencia_apos_reabrir_o_banco(tmp_path):
    caminho = tmp_path / "persistente.db"
    engine = create_db_engine(caminho)
    upgrade_database(engine)
    from sqlalchemy.orm import Session

    with Session(engine) as s:
        s.add(Item(name="Persistente", category="weapons", created_at=AGORA, updated_at=AGORA))
        s.commit()
    engine.dispose()

    reaberto = create_db_engine(caminho)
    upgrade_database(reaberto)
    with Session(reaberto) as s:
        assert [i.name for i in s.query(Item)] == ["Persistente"]
    reaberto.dispose()


def test_check_de_categoria_no_banco(engine):
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO items (name, category, created_at, updated_at) "
                "VALUES ('X', 'invalida', '2026-01-01', '2026-01-01')"
            )
        )
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO items (name, created_at, updated_at) "
                "VALUES ('Sem', '2026-01-01', '2026-01-01')"
            )
        )
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO items (name, category, created_at, updated_at) "
                "VALUES ('Y', 'weapons', '2026-01-01', '2026-01-01')"
            )
        )


def _inserir_legado(engine):
    dados = [("Espada", "Armas"), ("Anel", " acessórios "), ("Estranho", "raro"), ("Livre", None)]
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO dungeons (name, difficulty, created_at, updated_at) "
                "VALUES ('D', 1, '2026-01-01', '2026-01-01')"
            )
        )
        for nome, categoria in dados:
            conn.execute(
                text(
                    "INSERT INTO items (name, category, created_at, updated_at) "
                    "VALUES (:n, :c, '2026-01-01', '2026-01-01')"
                ),
                {"n": nome, "c": categoria},
            )
        conn.execute(
            text(
                "INSERT INTO runs (dungeon_id, item_id, completed_at, created_at, updated_at) "
                "VALUES (1, 1, '2026-01-01', '2026-01-01', '2026-01-01')"
            )
        )


def test_migracoes_0002_e_0003_sobre_dados_existentes(tmp_path):
    engine = create_db_engine(tmp_path / "legado.db")
    upgrade_database(engine, "0001")
    _inserir_legado(engine)

    upgrade_database(engine, "0002")
    with engine.connect() as conn:
        categorias = dict(conn.execute(text("SELECT name, category FROM items")).all())
    assert categorias == {
        "Espada": "weapons",
        "Anel": "accessories",
        "Estranho": None,
        "Livre": None,
    }

    with pytest.raises(RuntimeError, match="Estranho, Livre"):
        upgrade_database(engine)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar() == "0002"
        assert conn.execute(text("SELECT count(*) FROM items")).scalar() == 4
        assert conn.execute(text("PRAGMA foreign_keys")).scalar() == 1

    with engine.begin() as conn:
        conn.execute(text("UPDATE items SET category = 'relics' WHERE category IS NULL"))
    upgrade_database(engine)

    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM runs")).scalar() == 1
        assert conn.execute(text("PRAGMA foreign_keys")).scalar() == 1
        assert conn.execute(text("PRAGMA foreign_key_check")).all() == []
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diff == []

    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO items (name, category, created_at, updated_at) "
                "VALUES ('espada', 'weapons', '2026-01-01', '2026-01-01')"
            )
        )
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(text("DELETE FROM items WHERE name = 'Espada'"))

    downgrade_database(engine, "0002")
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO items (name, created_at, updated_at) "
                "VALUES ('Sem categoria', '2026-01-01', '2026-01-01')"
            )
        )
    engine.dispose()
