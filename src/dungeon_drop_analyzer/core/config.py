"""Configuração: diretório de dados do usuário, caminho do banco e dos logs."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

APP_DIR_NAME = "DungeonDropAnalyzer"
DATA_DIR_ENV = "DDA_DATA_DIR"
DB_FILE_NAME = "dda.db"


def default_data_dir() -> Path:
    override = os.environ.get(DATA_DIR_ENV)
    if override:
        return Path(override).expanduser()
    base = os.environ.get("LOCALAPPDATA")
    root = Path(base) if base else Path.home() / ".local" / "share"
    return root / APP_DIR_NAME


@dataclass(frozen=True)
class Settings:
    data_dir: Path

    @classmethod
    def load(cls, data_dir: Path | str | None = None) -> Settings:
        return cls(Path(data_dir).expanduser() if data_dir else default_data_dir())

    @property
    def db_path(self) -> Path:
        return self.data_dir / DB_FILE_NAME

    @property
    def log_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def backup_dir(self) -> Path:
        return self.data_dir / "backups"
