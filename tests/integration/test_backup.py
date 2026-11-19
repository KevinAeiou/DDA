"""Backup, validação e restauração (dados SINTÉTICOS)."""

import sqlite3
from datetime import UTC, datetime

import pytest
from sqlalchemy import text

from dungeon_drop_analyzer.core.database import create_db_engine, upgrade_database
from dungeon_drop_analyzer.services import BackupError
from dungeon_drop_analyzer.services.backup import (
    BackupService,
    default_backup_name,
    validate_backup,
)


@pytest.fixture
def backup(engine):
    return BackupService(engine)


@pytest.fixture
def populated(runs, seeded):
    ds, its = seeded
    for k in range(4):
        runs.register(ds[k % 5].id, its[k % 3].id, notes=f"n{k}")
    return ds, its


def contar(engine, tabela):
    with engine.connect() as conn:
        return conn.execute(text(f"SELECT count(*) FROM {tabela}")).scalar()


def test_nome_padrao_do_backup():
    nome = default_backup_name(datetime(2026, 11, 14, 15, 30, 5, tzinfo=UTC))
    assert nome.startswith("dda-backup-2026111") and nome.endswith(".db")


def test_cria_backup_valido_com_contagens(backup, populated, tmp_path):
    info = backup.create_backup(tmp_path / "saida" / "b.db")
    assert info.path.exists() and info.size_bytes > 0
    assert (info.dungeons, info.items, info.runs) == (5, 3, 4)
    assert info.revision == "0004" and info.needs_upgrade is False
    assert [p.name for p in (tmp_path / "saida").iterdir()] == ["b.db"]


def test_backup_nao_sobrescreve_sem_permissao(backup, populated, tmp_path):
    destino = tmp_path / "b.db"
    backup.create_backup(destino)
    with pytest.raises(BackupError, match="Já existe"):
        backup.create_backup(destino)
    backup.create_backup(destino, overwrite=True)


def test_backup_e_um_retrato_consistente_do_momento(backup, populated, runs, seeded, tmp_path):
    ds, its = seeded
    info = backup.create_backup(tmp_path / "antes.db")
    runs.register(ds[0].id, its[0].id)
    assert info.runs == 4
    assert validate_backup(tmp_path / "antes.db").runs == 4


def test_valida_rejeita_arquivos_invalidos(backup, populated, engine, tmp_path):
    with pytest.raises(BackupError, match="não existe"):
        validate_backup(tmp_path / "nao_existe.db")
    vazio = tmp_path / "vazio.db"
    vazio.write_bytes(b"")
    with pytest.raises(BackupError, match="vazio"):
        validate_backup(vazio)
    lixo = tmp_path / "lixo.db"
    lixo.write_bytes(b"isto nao e um banco sqlite" * 100)
    with pytest.raises(BackupError, match="SQLite válido|corrompido"):
        validate_backup(lixo)

    outro = tmp_path / "outro.db"
    conexao = sqlite3.connect(outro)
    conexao.execute("CREATE TABLE coisa (x INTEGER)")
    conexao.commit()
    conexao.close()
    with pytest.raises(BackupError, match="não é um backup"):
        validate_backup(outro)


def test_valida_rejeita_esquema_desconhecido(backup, populated, tmp_path):
    caminho = tmp_path / "futuro.db"
    backup.create_backup(caminho)
    conexao = sqlite3.connect(caminho)
    conexao.execute("UPDATE alembic_version SET version_num = '9999'")
    conexao.commit()
    conexao.close()
    with pytest.raises(BackupError, match="desconhecida ou mais nova"):
        validate_backup(caminho)


def test_valida_rejeita_arquivo_corrompido(backup, populated, tmp_path):
    caminho = tmp_path / "corrompido.db"
    backup.create_backup(caminho)
    dados = bytearray(caminho.read_bytes())
    for pos in range(4096, min(len(dados), 4096 * 3)):
        dados[pos] = 0xFF
    caminho.write_bytes(bytes(dados))
    with pytest.raises(BackupError):
        validate_backup(caminho)


def test_valida_rejeita_referencias_invalidas(backup, populated, tmp_path):
    caminho = tmp_path / "fk.db"
    backup.create_backup(caminho)
    conexao = sqlite3.connect(caminho)
    conexao.execute("PRAGMA foreign_keys=OFF")
    conexao.execute("UPDATE runs SET item_id = 9999 WHERE id = 1")
    conexao.commit()
    conexao.close()
    with pytest.raises(BackupError, match="referências inválidas"):
        validate_backup(caminho)


def test_restaura_estado_do_backup_e_guarda_copia_de_seguranca(
    backup, populated, runs, items, seeded, engine, tmp_path
):
    ds, its = seeded
    caminho = tmp_path / "bom.db"
    backup.create_backup(caminho)
    runs.delete(runs.list()[0].id)
    runs.delete(runs.list()[0].id)
    items.create("Novo item", "relics", [ds[0].id])
    assert (contar(engine, "runs"), contar(engine, "items")) == (2, 4)

    resultado = backup.restore(caminho, tmp_path / "seguranca")

    assert (contar(engine, "runs"), contar(engine, "items"), contar(engine, "dungeons")) == (
        4,
        3,
        5,
    )
    assert resultado.info.runs == 4
    assert resultado.safety_backup.parent == tmp_path / "seguranca"
    assert resultado.safety_backup.name.startswith("pre-restore-")
    antes = validate_backup(resultado.safety_backup)
    assert (antes.runs, antes.items) == (2, 4)
    with engine.connect() as conn:
        assert conn.execute(text("PRAGMA foreign_keys")).scalar() == 1
        assert conn.execute(text("PRAGMA integrity_check")).scalar() == "ok"


def test_servicos_continuam_funcionando_apos_restaurar(backup, populated, runs, seeded, tmp_path):
    ds, its = seeded
    caminho = tmp_path / "bom.db"
    backup.create_backup(caminho)
    runs.register(ds[0].id, its[0].id)
    backup.restore(caminho, tmp_path / "seg")
    assert runs.count() == 4
    runs.register(ds[1].id, its[1].id)
    assert runs.count() == 5


def test_restauracao_de_arquivo_invalido_nao_altera_dados(backup, populated, engine, tmp_path):
    lixo = tmp_path / "lixo.db"
    lixo.write_bytes(b"x" * 5000)
    with pytest.raises(BackupError):
        backup.restore(lixo, tmp_path / "seg")
    assert contar(engine, "runs") == 4
    assert not (tmp_path / "seg").exists()


def _banco_legado(caminho, categoria):
    legado = create_db_engine(caminho)
    upgrade_database(legado, "0002")
    with legado.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO dungeons (name, difficulty, created_at, updated_at) "
                "VALUES ('Antiga', 2, '2026-01-01', '2026-01-01')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO items (name, category, created_at, updated_at) "
                "VALUES ('Velho', :c, '2026-01-01', '2026-01-01')"
            ),
            {"c": categoria},
        )
        conn.execute(
            text(
                "INSERT INTO runs (dungeon_id, item_id, completed_at, created_at, updated_at) "
                "VALUES (1, 1, '2026-01-01', '2026-01-01', '2026-01-01')"
            )
        )
    legado.dispose()


def test_restaura_backup_de_esquema_antigo_atualizando(backup, populated, engine, tmp_path):
    caminho = tmp_path / "legado.db"
    _banco_legado(caminho, "armor")
    info = validate_backup(caminho)
    assert info.revision == "0002" and info.needs_upgrade is True

    backup.restore(caminho, tmp_path / "seg")

    with engine.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar() == "0004"
        assert conn.execute(text("SELECT name, category FROM items")).all() == [("Velho", "armor")]
    assert contar(engine, "runs") == 1


def test_falha_na_atualizacao_do_backup_antigo_preserva_dados_atuais(
    backup, populated, engine, tmp_path
):
    caminho = tmp_path / "legado_sem_categoria.db"
    _banco_legado(caminho, None)
    with pytest.raises(BackupError, match="atualizado"):
        backup.restore(caminho, tmp_path / "seg")
    assert (contar(engine, "runs"), contar(engine, "items")) == (4, 3)
    assert not (tmp_path / "seg").exists()
