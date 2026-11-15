"""Backup manual consistente, validação e restauração de backups do banco SQLite."""

from __future__ import annotations

import logging
import os
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from alembic.script import ScriptDirectory
from sqlalchemy import Engine

from dungeon_drop_analyzer.core.database import (
    _alembic_config,
    create_db_engine,
    upgrade_database,
)
from dungeon_drop_analyzer.core.timeutils import utc_now

from .errors import BackupError

logger = logging.getLogger(__name__)

REQUIRED_TABLES = {"dungeons", "items", "runs", "audit_log", "alembic_version"}


@dataclass(frozen=True)
class BackupInfo:
    path: Path
    size_bytes: int
    revision: str
    needs_upgrade: bool
    dungeons: int
    items: int
    runs: int


@dataclass(frozen=True)
class RestoreResult:
    info: BackupInfo
    safety_backup: Path


def _stamp(now: datetime | None = None) -> str:
    return f"{(now or utc_now()).astimezone():%Y%m%d-%H%M%S}"


def default_backup_name(now: datetime | None = None) -> str:
    return f"dda-backup-{_stamp(now)}.db"


def _known_revisions() -> tuple[set[str], str]:
    script = ScriptDirectory.from_config(_alembic_config())
    revisions = {rev.revision for rev in script.walk_revisions()}
    return revisions, script.get_current_head()


def _open_readonly(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)


def validate_backup(path: Path | str) -> BackupInfo:
    """Verifica integridade, estrutura e versão do esquema de um arquivo de backup."""
    path = Path(path)
    if not path.is_file() or path.stat().st_size == 0:
        raise BackupError("O arquivo de backup não existe ou está vazio.")
    try:
        connection = _open_readonly(path)
    except sqlite3.Error:
        raise BackupError("Não foi possível abrir o arquivo como um banco de dados.") from None
    try:
        try:
            integrity = connection.execute("PRAGMA integrity_check").fetchall()
            tables = {
                r[0]
                for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
        except sqlite3.DatabaseError:
            raise BackupError(
                "O arquivo não é um banco SQLite válido ou está corrompido."
            ) from None
        if integrity != [("ok",)]:
            raise BackupError("O backup está corrompido (falha na verificação de integridade).")
        if not REQUIRED_TABLES <= tables:
            raise BackupError("O arquivo não é um backup do Dungeon Drop Analyzer.")
        row = connection.execute("SELECT version_num FROM alembic_version").fetchone()
        revision = row[0] if row else ""
        known, head = _known_revisions()
        if revision not in known:
            raise BackupError(
                "O backup foi criado por uma versão desconhecida ou mais nova do aplicativo "
                f"(esquema '{revision}')."
            )
        if connection.execute("PRAGMA foreign_key_check").fetchall():
            raise BackupError("O backup contém referências inválidas entre registros.")
        counts = [
            connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            for table in ("dungeons", "items", "runs")
        ]
    finally:
        connection.close()
    return BackupInfo(path, path.stat().st_size, revision, revision != head, *counts)


class BackupService:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def create_backup(self, destination: Path | str, overwrite: bool = False) -> BackupInfo:
        """Cópia consistente via API de backup do SQLite; só substitui o destino se for válida."""
        destination = Path(destination)
        if destination.exists() and not overwrite:
            raise BackupError("Já existe um arquivo no destino escolhido.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(suffix=".db", dir=destination.parent)
        os.close(fd)
        temp = Path(temp_name)
        try:
            self._copy_live_to(temp)
            validate_backup(temp)
            os.replace(temp, destination)
        except BackupError:
            temp.unlink(missing_ok=True)
            raise
        except (OSError, sqlite3.Error) as error:
            temp.unlink(missing_ok=True)
            logger.exception("Falha ao criar backup")
            raise BackupError(f"Não foi possível criar o backup: {error}") from error
        info = validate_backup(destination)
        logger.info("Backup criado em %s", destination)
        return info

    def validate(self, path: Path | str) -> BackupInfo:
        return validate_backup(path)

    def restore(self, backup_path: Path | str, safety_dir: Path | str) -> RestoreResult:
        """Restaura um backup validado, após criar uma cópia de segurança dos dados atuais.

        O backup é copiado e, se for de um esquema antigo, atualizado em um arquivo temporário
        antes de tocar no banco em uso; qualquer falha nessa etapa deixa os dados intactos.
        """
        info = validate_backup(backup_path)
        workdir = Path(tempfile.mkdtemp(prefix="dda-restore-"))
        try:
            candidate = workdir / "candidate.db"
            shutil.copyfile(info.path, candidate)
            if info.needs_upgrade:
                self._upgrade_candidate(candidate)
            validate_backup(candidate)
            safety = self.create_backup(Path(safety_dir) / f"pre-restore-{_stamp()}.db")
            try:
                self._copy_to_live(candidate)
            except Exception as error:
                logger.exception("Falha ao restaurar; revertendo para a cópia de segurança")
                self._copy_to_live(safety.path)
                raise BackupError(
                    "A restauração falhou e os dados anteriores foram mantidos."
                ) from error
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
        logger.info("Backup restaurado de %s (cópia de segurança em %s)", info.path, safety.path)
        return RestoreResult(info=info, safety_backup=safety.path)

    @staticmethod
    def _upgrade_candidate(candidate: Path) -> None:
        engine = create_db_engine(candidate)
        try:
            upgrade_database(engine)
        except Exception as error:
            raise BackupError(
                f"O backup não pôde ser atualizado para a versão atual do esquema: {error}"
            ) from error
        finally:
            engine.dispose()

    def _copy_live_to(self, target: Path) -> None:
        raw = self._engine.raw_connection()
        try:
            destination = sqlite3.connect(target)
            try:
                raw.driver_connection.backup(destination)
            finally:
                destination.close()
        finally:
            raw.close()

    def _copy_to_live(self, source: Path) -> None:
        origin = sqlite3.connect(source)
        raw = self._engine.raw_connection()
        try:
            origin.backup(raw.driver_connection)
            raw.driver_connection.commit()
        finally:
            raw.close()
            origin.close()
