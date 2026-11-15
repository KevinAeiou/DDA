"""Configurações: caminhos de dados, diretório de dados configurável, backup e restauração."""

from __future__ import annotations

from datetime import UTC, datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGroupBox, QLabel, QPushButton, QVBoxLayout, QWidget

from dungeon_drop_analyzer.core.config import Settings, clear_saved_data_dir, save_data_dir
from dungeon_drop_analyzer.services import Services
from dungeon_drop_analyzer.services.backup import BackupInfo, default_backup_name
from dungeon_drop_analyzer.ui.widgets.files import (
    choose_directory,
    choose_open_path,
    choose_save_path,
)
from dungeon_drop_analyzer.ui.widgets.formatting import format_datetime
from dungeon_drop_analyzer.ui.widgets.messages import confirm, guarded, show_info

from .base import Page

DB_FILTER = "Banco de dados do DDA (*.db)"


def _modified(info: BackupInfo) -> datetime:
    return datetime.fromtimestamp(info.path.stat().st_mtime, tz=UTC)


def describe_backup(info: BackupInfo) -> str:
    size_mb = info.size_bytes / (1024 * 1024)
    return (
        f"{info.dungeons} masmorra(s), {info.items} item(ns) e {info.runs} incursão(ões); "
        f"esquema {info.revision}; {size_mb:.2f} MB"
    )


class SettingsPage(Page):
    def __init__(self, settings: Settings, services: Services, parent: QWidget | None = None):
        super().__init__(parent)
        self.settings = settings
        self.services = services
        self.details = (
            f"<b>Diretório de dados:</b> {settings.data_dir}<br>"
            f"<b>Banco de dados:</b> {settings.db_path}<br>"
            f"<b>Logs:</b> {settings.log_dir}<br>"
            f"<b>Backups:</b> {settings.backup_dir}<br>"
            f"<b>Exportações:</b> {settings.export_dir}"
        )
        paths = QLabel(self.details)
        paths.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        paths.setWordWrap(True)
        self.result_label = QLabel()
        self.result_label.setWordWrap(True)

        self.backup_button = QPushButton("Criar backup...")
        self.restore_button = QPushButton("Restaurar backup...")
        self.change_dir_button = QPushButton("Alterar diretório de dados...")
        self.reset_dir_button = QPushButton("Voltar ao diretório padrão")
        self.backup_button.clicked.connect(self.create_backup)
        self.restore_button.clicked.connect(self.restore_backup)
        self.change_dir_button.clicked.connect(self.change_data_dir)
        self.reset_dir_button.clicked.connect(self.reset_data_dir)

        data_box = QGroupBox("Armazenamento")
        data_layout = QVBoxLayout(data_box)
        data_layout.addWidget(paths)
        data_layout.addWidget(self.change_dir_button)
        data_layout.addWidget(self.reset_dir_button)
        backup_box = QGroupBox("Backup e restauração")
        backup_layout = QVBoxLayout(backup_box)
        note = QLabel(
            "O backup é uma cópia consistente do banco. Antes de restaurar, o arquivo é validado e "
            "uma cópia de segurança dos dados atuais é criada automaticamente."
        )
        note.setWordWrap(True)
        backup_layout.addWidget(note)
        backup_layout.addWidget(self.backup_button)
        backup_layout.addWidget(self.restore_button)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h2>Configurações e backup</h2>"))
        layout.addWidget(data_box)
        layout.addWidget(backup_box)
        layout.addWidget(self.result_label)
        layout.addStretch()

    def refresh(self) -> None:
        return None

    def _report(self, text: str) -> None:
        self.result_label.setText(text)
        self.message.emit(text)
        show_info(self, text)

    def create_backup(self) -> None:
        default = self.settings.backup_dir / default_backup_name()
        path = choose_save_path(self, "Salvar backup", default, DB_FILTER)
        if path is None:
            return
        ok, info = guarded(self, lambda: self.services.backup.create_backup(path, overwrite=True))
        if ok:
            self._report(f"Backup criado em {info.path}: {describe_backup(info)}.")

    def restore_backup(self) -> None:
        path = choose_open_path(self, "Selecionar backup", self.settings.backup_dir, DB_FILTER)
        if path is None:
            return
        ok, info = guarded(self, lambda: self.services.backup.validate(path))
        if not ok:
            return
        question = (
            "Restaurar este backup substituirá TODOS os dados atuais.\n\n"
            f"Backup: {info.path.name}\nConteúdo: {describe_backup(info)}"
            f"\nÚltima modificação do arquivo: "
            f"{format_datetime(_modified(info))}\n\n"
            "Uma cópia de segurança dos dados atuais será criada antes da restauração."
        )
        if not confirm(self, question, "Restaurar"):
            return
        ok, result = guarded(
            self,
            lambda: self.services.backup.restore(path, self.settings.backup_dir),
        )
        if ok:
            self._report(
                f"Backup restaurado ({describe_backup(result.info)}). "
                f"Cópia de segurança dos dados anteriores: {result.safety_backup}."
            )

    def change_data_dir(self) -> None:
        directory = choose_directory(self, "Escolher diretório de dados", self.settings.data_dir)
        if directory is None:
            return
        question = (
            f"Usar '{directory}' como diretório de dados na próxima inicialização?\n\n"
            "Os dados existentes NÃO são movidos: o aplicativo abrirá (ou criará) o banco nessa "
            "pasta. Para levar seus dados, crie um backup agora e restaure-o depois de reiniciar."
        )
        if not confirm(self, question, "Alterar"):
            return
        ok, _ = guarded(self, lambda: save_data_dir(directory))
        if ok:
            self._report(
                f"Diretório de dados definido como {directory}. Reinicie o aplicativo para aplicar."
            )

    def reset_data_dir(self) -> None:
        if not confirm(
            self,
            "Voltar a usar o diretório de dados padrão na próxima inicialização?",
            "Voltar ao padrão",
        ):
            return
        ok, _ = guarded(self, clear_saved_data_dir)
        if ok:
            self._report("Diretório padrão restaurado. Reinicie o aplicativo para aplicar.")
