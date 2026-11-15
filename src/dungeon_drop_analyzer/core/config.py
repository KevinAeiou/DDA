"""Configuração: diretório de dados do usuário, caminho do banco e dos logs."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

APP_DIR_NAME = "DungeonDropAnalyzer"
DATA_DIR_ENV = "DDA_DATA_DIR"
DB_FILE_NAME = "dda.db"
USER_CONFIG_NAME = "config.json"


def config_dir() -> Path:
    """Pasta fixa do perfil do usuário onde fica a escolha do diretório de dados."""
    base = os.environ.get("LOCALAPPDATA")
    root = Path(base) if base else Path.home() / ".local" / "share"
    return root / APP_DIR_NAME


def user_config_path() -> Path:
    return config_dir() / USER_CONFIG_NAME


def saved_data_dir() -> Path | None:
    """Diretório escolhido pelo usuário na interface, se houver e for válido."""
    try:
        data = json.loads(user_config_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    value = data.get("data_dir") if isinstance(data, dict) else None
    return Path(value).expanduser() if isinstance(value, str) and value.strip() else None


def save_data_dir(path: Path | str) -> Path:
    target = user_config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps({"data_dir": str(Path(path))}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return target


def clear_saved_data_dir() -> None:
    user_config_path().unlink(missing_ok=True)


def default_data_dir() -> Path:
    """Prioridade: variável DDA_DATA_DIR, escolha salva na interface, pasta padrão do perfil."""
    override = os.environ.get(DATA_DIR_ENV)
    if override:
        return Path(override).expanduser()
    return saved_data_dir() or config_dir()


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

    @property
    def export_dir(self) -> Path:
        return self.data_dir / "exports"
