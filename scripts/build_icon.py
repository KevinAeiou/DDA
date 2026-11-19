"""Gera os PNGs e o icon.ico do aplicativo a partir dos SVGs em resources/."""

from __future__ import annotations

import struct
import sys
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

RESOURCES = Path(__file__).resolve().parents[1] / "src" / "dungeon_drop_analyzer" / "resources"

VARIANTS = {
    "icon.svg": (256, 128, 64, 48),
    "icon-medio.svg": (32, 24),
    "icon-pequeno.svg": (16,),
}


def render_png(svg: Path, size: int) -> bytes:
    renderer = QSvgRenderer(str(svg))
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(0)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    renderer.render(painter)
    painter.end()
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    buffer.close()
    return bytes(data)


def build_ico(frames: dict[int, bytes]) -> bytes:
    sizes = sorted(frames)
    header = struct.pack("<HHH", 0, 1, len(sizes))
    offset = 6 + 16 * len(sizes)
    entries = b""
    body = b""
    for size in sizes:
        png = frames[size]
        dimension = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", dimension, dimension, 0, 0, 1, 32, len(png), offset)
        body += png
        offset += len(png)
    return header + entries + body


def main() -> int:
    QGuiApplication.instance() or QGuiApplication(["build_icon", "-platform", "offscreen"])
    frames: dict[int, bytes] = {}
    for name, sizes in VARIANTS.items():
        for size in sizes:
            frames[size] = render_png(RESOURCES / name, size)
    for size in (16, 32, 256):
        (RESOURCES / f"icon-{size}.png").write_bytes(frames[size])
    (RESOURCES / "icon.ico").write_bytes(build_ico(frames))
    print(f"icone gerado com os tamanhos {sorted(frames)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
