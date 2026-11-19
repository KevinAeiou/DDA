"""Inicialização da aplicação Qt em português do Brasil."""

from __future__ import annotations

import logging
import sys

from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
from PySide6.QtWidgets import QApplication, QMessageBox

from dungeon_drop_analyzer.core.bootstrap import initialize
from dungeon_drop_analyzer.core.config import Settings
from dungeon_drop_analyzer.services import Services
from dungeon_drop_analyzer.ui.app_icon import load_app_icon, set_windows_app_id
from dungeon_drop_analyzer.ui.widgets.messages import APP_TITLE
from dungeon_drop_analyzer.ui.windows import MainWindow

logger = logging.getLogger(__name__)


def configure_locale(app: QApplication) -> list[QTranslator]:
    QLocale.setDefault(QLocale(QLocale.Language.Portuguese, QLocale.Country.Brazil))
    translators = []
    path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    for name in ("qtbase", "qt"):
        translator = QTranslator(app)
        if translator.load(QLocale(), name, "_", path):
            app.installTranslator(translator)
            translators.append(translator)
    return translators


def run(argv: list[str] | None = None) -> int:
    set_windows_app_id()
    app = QApplication.instance() or QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName(APP_TITLE)
    app.setWindowIcon(load_app_icon())
    configure_locale(app)
    settings = Settings.load()
    try:
        session_factory = initialize(settings)
    except Exception:
        logging.getLogger(__name__).exception("Falha ao inicializar o banco")
        QMessageBox.critical(
            None,
            APP_TITLE,
            f"Não foi possível abrir o banco de dados em:\n{settings.db_path}\n\n"
            "Verifique as permissões da pasta e consulte o log.",
        )
        return 1
    window = MainWindow(Services.create(session_factory), settings)
    window.show()
    return app.exec()
