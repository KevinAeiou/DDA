"""Configuração, logging, utilitários de tempo e inicialização."""

import logging
from datetime import UTC, datetime, timedelta, timezone

from dungeon_drop_analyzer.core.bootstrap import initialize
from dungeon_drop_analyzer.core.config import DATA_DIR_ENV, Settings, default_data_dir
from dungeon_drop_analyzer.core.logging_setup import LOG_FILE_NAME, LOGGER_NAME, setup_logging
from dungeon_drop_analyzer.core.timeutils import ensure_aware, to_utc
from dungeon_drop_analyzer.services import DungeonService


def test_diretorio_padrao_respeita_variavel_de_ambiente(monkeypatch, tmp_path):
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path / "dados"))
    assert default_data_dir() == tmp_path / "dados"
    assert Settings.load().db_path == tmp_path / "dados" / "dda.db"


def test_diretorio_padrao_no_perfil_do_usuario(monkeypatch, tmp_path):
    monkeypatch.delenv(DATA_DIR_ENV, raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert default_data_dir() == tmp_path / "DungeonDropAnalyzer"


def test_settings_explicito_tem_precedencia(monkeypatch, tmp_path):
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path / "env"))
    s = Settings.load(tmp_path / "explicito")
    assert s.data_dir == tmp_path / "explicito"
    assert s.log_dir == s.data_dir / "logs" and s.backup_dir == s.data_dir / "backups"


def test_to_utc_e_ensure_aware():
    br = timezone(timedelta(hours=-3))
    assert to_utc(datetime(2026, 1, 1, 9, tzinfo=br)) == datetime(2026, 1, 1, 12, tzinfo=UTC)
    assert ensure_aware(datetime(2026, 1, 1)).tzinfo is not None


def test_logging_rotativo_e_idempotente(tmp_path):
    logger = setup_logging(tmp_path / "logs")
    setup_logging(tmp_path / "logs")
    marcados = [h for h in logger.handlers if getattr(h, "_dda_handler", False)]
    assert len(marcados) == 1
    logging.getLogger(f"{LOGGER_NAME}.teste").info("mensagem de teste")
    marcados[0].flush()
    assert "mensagem de teste" in (tmp_path / "logs" / LOG_FILE_NAME).read_text(encoding="utf-8")
    for h in marcados:
        logger.removeHandler(h)
        h.close()


def test_initialize_cria_diretorios_banco_e_persiste(tmp_path):
    settings = Settings.load(tmp_path / "app")
    factory = initialize(settings)
    DungeonService(factory).create("Persistida", 2)
    assert settings.db_path.exists() and settings.log_dir.exists()

    reaberta = initialize(settings)
    assert [d.name for d in DungeonService(reaberta).list()] == ["Persistida"]
    logger = logging.getLogger(LOGGER_NAME)
    for h in list(logger.handlers):
        if getattr(h, "_dda_handler", False):
            logger.removeHandler(h)
            h.close()
