"""Diálogo de formulário que só fecha quando o envio é aceito pelos serviços."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout, QWidget

from dungeon_drop_analyzer.ui.widgets.messages import guarded


class FormDialog(QDialog):
    def __init__(
        self,
        title: str,
        content: QWidget,
        on_submit: Callable[[], object],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self._on_submit = on_submit
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Salvar")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(content)
        layout.addWidget(buttons)

    def accept(self) -> None:
        ok, _ = guarded(self, self._on_submit)
        if ok:
            super().accept()
