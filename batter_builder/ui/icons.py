"""The app's line icons (ui/icons/*.svg, drawn white) tinted to the theme.

``icon(name)`` gives a QIcon in the current text color; ``attach`` puts one on
a button and re-tints it when the appearance changes.
"""
import sys
from pathlib import Path

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon

from . import theme

# Packaged builds carry both folders as data files (tools/build_macos.py and
# the Windows/Linux build step add them with --add-data).
BASE = Path(sys._MEIPASS) if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[2]
FOLDER = BASE / "batter_builder/ui/icons"
ASSETS = BASE / "assets"

ROLES = ("text_primary", "text_secondary", "text_inverse", "accent", "error", "warning", "success")


def path(name: str) -> str:
    return str(FOLDER / f"{name}.svg")


def icon(name: str, role: str = "text_primary", size: int = 18) -> QIcon:
    color = getattr(theme.ThemeHost.instance().colors, role)
    result = QIcon()
    for scale in (1.0, 2.0):
        result.addPixmap(theme.pixmap(path(name), color, size, scale))
    return result


def attach(widget, name: str, role: str = "text_primary", size: int = 18):
    """Set ``widget``'s icon and keep it tinted to the theme."""
    def apply():
        try:
            widget.setIcon(icon(name, role, size))
        except RuntimeError:     # the widget is gone
            pass
    widget.setIconSize(QSize(size, size))
    apply()
    theme.ThemeHost.instance().changed.connect(apply)
    return widget


def app_icon() -> QIcon:
    result = QIcon()
    for name in ("icon.png", "icon-small.svg"):
        candidate = ASSETS / name
        if candidate.exists():
            result.addFile(str(candidate))
    return result

