"""Render assets/icon.svg (and icon-small.svg for 16-32 px) into the icon
files the builds use: assets/icon.png, icon.ico and icon.icns.

    python tools/make_icons.py
"""
import io
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PIL import Image
from PySide6.QtCore import QBuffer, QByteArray, Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

ASSETS = Path(__file__).resolve().parents[1] / "assets"


def render(svg: str, size: int) -> Image.Image:
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    QSvgRenderer(str(ASSETS / svg)).render(painter)
    painter.end()
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QBuffer.WriteOnly)
    image.save(buffer, "PNG")
    return Image.open(io.BytesIO(bytes(data))).convert("RGBA")


def icon(size: int) -> Image.Image:
    return render("icon-small.svg" if size <= 32 else "icon.svg", size)


def main():
    app = QGuiApplication(sys.argv)
    icon(1024).save(ASSETS / "icon.png")
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = [icon(size) for size in sizes]
    images[-1].save(ASSETS / "icon.ico", sizes=[(s, s) for s in sizes], append_images=images[:-1])
    icon(1024).save(ASSETS / "icon.icns", append_images=[icon(s) for s in (16, 32, 64, 128, 256, 512)])
    del app


if __name__ == "__main__":
    main()
