"""Diálogo de correção de uma incursão do histórico."""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from dungeon_drop_analyzer.models import Run
from dungeon_drop_analyzer.services import Services
from dungeon_drop_analyzer.ui.widgets.formatting import to_local_naive
from dungeon_drop_analyzer.ui.widgets.run_form import RunForm

from .form_dialog import FormDialog


class RunEditDialog(FormDialog):
    def __init__(self, services: Services, run: Run, parent: QWidget | None = None) -> None:
        self._services = services
        self._run = run
        self.form = RunForm(collapsible=False)
        dungeons = [d for d in services.dungeons.list() if d.is_active or d.id == run.dungeon_id]
        items = [i for i in services.items.list() if i.is_active or i.id == run.item_id]
        self.form.set_choices(dungeons, items)
        self.form.load_run(run)
        super().__init__("Corrigir incursão", self.form, self._submit, parent)

    def _submit(self) -> None:
        values = self.form.values()
        original = to_local_naive(self._run.completed_at).replace(microsecond=0)
        if values["completed_at"] == original:
            del values["completed_at"]
        self._services.runs.update(self._run.id, **values)
