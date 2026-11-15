"""Gráficos Matplotlib incorporados à interface."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import QSizePolicy, QWidget

PALETTE = [
    "#4C78A8",
    "#F58518",
    "#54A24B",
    "#E45756",
    "#72B7B2",
    "#B279A2",
    "#9D755D",
    "#BAB0AC",
]


class ChartCanvas(FigureCanvasQTAgg):
    def __init__(self, height: float = 3.0, parent: QWidget | None = None) -> None:
        self.figure = Figure(figsize=(6.5, height), layout="constrained")
        super().__init__(self.figure)
        self.setParent(parent)
        self.setMinimumHeight(int(height * 80))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.axes = self.figure.add_subplot(111)
        self.is_empty = True

    def reset(self, title: str) -> None:
        self.axes.clear()
        self.axes.set_title(title, fontsize=10)
        self.is_empty = False

    def show_empty(self, title: str) -> None:
        self.reset(title)
        self.axes.text(
            0.5,
            0.5,
            "Sem dados para exibir",
            ha="center",
            va="center",
            transform=self.axes.transAxes,
        )
        self.axes.set_xticks([])
        self.axes.set_yticks([])
        self.is_empty = True
        self.draw_idle()


def draw_bars(
    canvas: ChartCanvas, title: str, labels: Sequence[str], values: Sequence[float], ylabel: str
) -> None:
    if not labels or not any(values):
        canvas.show_empty(title)
        return
    canvas.reset(title)
    canvas.axes.bar(range(len(labels)), values, color=PALETTE[0])
    canvas.axes.set_xticks(range(len(labels)), labels, rotation=30, ha="right", fontsize=8)
    canvas.axes.set_ylabel(ylabel)
    canvas.draw_idle()


def draw_stacked(
    canvas: ChartCanvas,
    title: str,
    groups: Sequence[str],
    series: dict[str, Sequence[float]],
    ylabel: str,
) -> None:
    if not groups or not any(any(values) for values in series.values()):
        canvas.show_empty(title)
        return
    canvas.reset(title)
    bottoms = [0.0] * len(groups)
    for index, (name, values) in enumerate(series.items()):
        canvas.axes.bar(
            range(len(groups)),
            values,
            bottom=bottoms,
            label=name,
            color=PALETTE[index % len(PALETTE)],
        )
        bottoms = [b + v for b, v in zip(bottoms, values, strict=True)]
    canvas.axes.set_xticks(range(len(groups)), groups, rotation=20, ha="right", fontsize=8)
    canvas.axes.set_ylabel(ylabel)
    canvas.axes.legend(fontsize=7, loc="upper left", bbox_to_anchor=(1.0, 1.0))
    canvas.draw_idle()


def draw_lines(
    canvas: ChartCanvas, title: str, series: dict[str, list[tuple[date, int]]], ylabel: str
) -> None:
    if not series:
        canvas.show_empty(title)
        return
    canvas.reset(title)
    for index, (name, points) in enumerate(series.items()):
        canvas.axes.plot(
            [d for d, _ in points],
            [v for _, v in points],
            marker="o",
            markersize=3,
            label=name,
            color=PALETTE[index % len(PALETTE)],
        )
    canvas.axes.set_ylabel(ylabel)
    canvas.axes.legend(fontsize=7, loc="upper left", bbox_to_anchor=(1.0, 1.0))
    canvas.figure.autofmt_xdate()
    canvas.draw_idle()
