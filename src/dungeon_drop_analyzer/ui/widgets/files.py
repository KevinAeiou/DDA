"""Seletores de arquivo e pasta (isolados para facilitar a substituição em testes)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QWidget


def choose_save_path(
    parent: QWidget | None, title: str, default_path: Path, name_filter: str
) -> Path | None:
    chosen, _ = QFileDialog.getSaveFileName(parent, title, str(default_path), name_filter)
    return Path(chosen) if chosen else None


def choose_open_path(
    parent: QWidget | None, title: str, start_dir: Path, name_filter: str
) -> Path | None:
    chosen, _ = QFileDialog.getOpenFileName(parent, title, str(start_dir), name_filter)
    return Path(chosen) if chosen else None


def choose_directory(parent: QWidget | None, title: str, start_dir: Path) -> Path | None:
    chosen = QFileDialog.getExistingDirectory(parent, title, str(start_dir))
    return Path(chosen) if chosen else None
