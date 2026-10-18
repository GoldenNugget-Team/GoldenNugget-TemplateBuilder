"""Batter Builder's theme host for the awesomeUI controls.

awesomeUI's iOS controls take their colors and stylesheets from the host
application (``awesomeui.configure_theme``). This module supplies them with
GoldenNugget's palette, follows the system's light or dark mode and styles the
plain Qt widgets to match.
"""
from dataclasses import dataclass

from PySide6.QtCore import QObject, QRect, QSettings, QSize, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QPainter, QPalette, QPixmap
from PySide6.QtWidgets import QApplication

import awesomeui


@dataclass(frozen=True)
class Colors:
    bg_primary: str
    bg_secondary: str
    bg_tertiary: str
    bg_input: str
    text_primary: str
    text_secondary: str
    text_disabled: str
    text_inverse: str
    accent: str
    accent_hover: str
    accent_pressed: str
    success: str
    error: str
    error_hover: str
    error_pressed: str
    warning: str
    border: str
    divider: str
    surface_hover: str


# GoldenNugget's palettes (src/gui/theme/colors.py).
DARK = Colors(
    bg_primary="#1e1e1e", bg_secondary="#1C1C1E", bg_tertiary="#2C2C2E", bg_input="#1C1C1E",
    text_primary="#FFFFFF", text_secondary="#8E8E93", text_disabled="#787878", text_inverse="#FFFFFF",
    accent="#007AFF", accent_hover="#0066CC", accent_pressed="#0055AA",
    success="#30D158", error="#FF453A", error_hover="#FF5A50", error_pressed="#C2322A",
    warning="#FFD60A", border="#3A3A3C", divider="#3A3A3C", surface_hover="#2C2C2E")
LIGHT = Colors(
    bg_primary="#F3F4F7", bg_secondary="#FFFFFF", bg_tertiary="#E9ECF2", bg_input="#FFFFFF",
    text_primary="#181C25", text_secondary="#515A6B", text_disabled="#747C8B", text_inverse="#FFFFFF",
    accent="#005FC7", accent_hover="#0054B0", accent_pressed="#004999",
    success="#147437", error="#BC2629", error_hover="#AB2024", error_pressed="#941B20",
    warning="#775800", border="#B3BAC7", divider="#D0D5DF", surface_hover="#E3E7EF")

# The stylesheet keys awesomeUI's controls ask for, as GoldenNugget renders
# them (src/gui/theme/styles.py), plus this app's own.
STYLES = {
    "section_header": (
        "font-size: 13px; font-weight: 600; color: {text_secondary}; text-transform: uppercase; "
        "letter-spacing: 0.5px; padding-left: 4px; background-color: transparent;"),
    "collapsible_header": """
        QPushButton#iosCollapsibleHeader {{ background: transparent; border: none;
            color: {text_primary}; font-size: 14px; font-weight: 650; text-align: left; padding: 9px 6px; }}
        QPushButton#iosCollapsibleHeader:hover {{ background: transparent; }}
    """,
    "card": """
        IOSCard {{ background-color: {bg_secondary}; border-radius: 14px; border: 1px solid {border}; }}
        IOSCard QLabel {{ background-color: transparent; }}
    """,
    "primary_button": """
        QPushButton {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {accent}, stop:1 {accent_pressed});
            border-radius: 12px; color: {text_inverse}; font-size: 15px; font-weight: 600; border: none;
            padding: 0 18px; }}
        QPushButton:hover {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {accent_hover}, stop:1 {accent}); }}
        QPushButton:pressed {{ background-color: {accent_pressed}; }}
        QPushButton:disabled {{ background-color: {border}; color: {text_disabled}; }}
    """,
    "danger_button": """
        QPushButton {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {error}, stop:1 {error_pressed});
            border-radius: 12px; color: {text_inverse}; font-size: 15px; font-weight: 600; border: none;
            padding: 0 18px; }}
        QPushButton:hover {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {error_hover}, stop:1 {error}); }}
        QPushButton:pressed {{ background-color: {error_pressed}; }}
    """,
    "segmented_filter": """
        QWidget#iosSegmentedFilter {{ background-color: {bg_secondary}; border: 1px solid {border}; border-radius: 12px; }}
        QWidget#iosSegmentedFilter QPushButton {{ background: transparent; border: none; border-radius: 8px;
            padding: 0px 12px; color: {text_secondary}; font-size: 13px; font-weight: 500; }}
        QWidget#iosSegmentedFilter QPushButton:hover {{ color: {text_primary}; }}
        QWidget#iosSegmentedFilter QPushButton:checked {{ background: {bg_tertiary}; color: {text_primary}; font-weight: 600; }}
    """,
    "list_search_empty": "color: {text_secondary}; background-color: transparent; font-size: 14px; padding: 12px;",
    "app": """
        QMainWindow, QWidget#page, QScrollArea, QScrollArea > QWidget > QWidget#page {{ background: {bg_primary}; }}
        QWidget {{ color: {text_primary}; font-size: 13px; }}
        QLabel {{ background: transparent; }}
        QLabel#pageTitle {{ font-size: 24px; font-weight: 700; }}
        QLabel#muted {{ color: {text_secondary}; }}
        QLabel#good {{ color: {success}; }}
        QLabel#bad {{ color: {error}; }}
        QLineEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
            background: {bg_input}; border: 1px solid {border}; border-radius: 9px;
            padding: 6px 10px; selection-background-color: {accent}; selection-color: {text_inverse}; }}
        QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
            border-color: {accent}; }}
        QComboBox::drop-down {{ border: none; width: 22px; }}
        QComboBox QAbstractItemView {{ background: {bg_secondary}; border: 1px solid {border};
            selection-background-color: {accent}; selection-color: {text_inverse}; }}
        QListWidget, QTableWidget, QTreeWidget {{ background: {bg_input}; border: 1px solid {border};
            border-radius: 9px; alternate-background-color: {bg_tertiary}; gridline-color: {divider}; }}
        QListWidget::item {{ padding: 6px 8px; border-radius: 6px; }}
        QListWidget::item:selected, QTreeWidget::item:selected, QTableWidget::item:selected {{
            background: {accent}; color: {text_inverse}; }}
        QHeaderView::section {{ background: {bg_tertiary}; color: {text_secondary}; border: none;
            border-bottom: 1px solid {divider}; padding: 6px 8px; font-weight: 600; }}
        QTableWidget QLineEdit, QTableWidget QComboBox, QTableWidget QSpinBox, QTableWidget QDoubleSpinBox {{
            border-radius: 6px; padding: 2px 6px; }}
        QPushButton#secondary {{ background: {bg_tertiary}; border: 1px solid {border}; border-radius: 9px;
            padding: 6px 14px; font-weight: 500; }}
        QPushButton#secondary:hover {{ background: {surface_hover}; border-color: {accent}; }}
        QPushButton#secondary:disabled {{ color: {text_disabled}; }}
        QCheckBox {{ spacing: 6px; }}
        QMenuBar {{ background: {bg_primary}; }}
        QMenuBar::item:selected, QMenu::item:selected {{ background: {accent}; color: {text_inverse}; }}
        QMenu {{ background: {bg_secondary}; border: 1px solid {border}; }}
        QScrollBar:vertical {{ background: transparent; width: 10px; }}
        QScrollBar::handle:vertical {{ background: {border}; border-radius: 5px; min-height: 30px; }}
        QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
        QToolTip {{ background: {bg_secondary}; color: {text_primary}; border: 1px solid {border}; }}
    """,
}


MODES = ("system", "light", "dark")


class ThemeHost(QObject):
    """Holds the current palette. ``mode`` is system, light or dark (saved in
    the settings); ``changed`` fires whenever the palette changes."""
    changed = Signal()
    _instance = None

    def __init__(self):
        super().__init__()
        self.settings = QSettings("GoldenNugget-Team", "Batter Builder")
        mode = self.settings.value("appearance", "system")
        self.mode = mode if mode in MODES else "system"
        self.colors = self._pick()
        hints = QGuiApplication.styleHints()
        if hasattr(hints, "colorSchemeChanged"):
            hints.colorSchemeChanged.connect(lambda _scheme: self._update())

    @classmethod
    def instance(cls) -> "ThemeHost":
        if cls._instance is None:
            cls._instance = ThemeHost()
        return cls._instance

    def _pick(self) -> Colors:
        if self.mode == "system":
            hints = QGuiApplication.styleHints()
            dark = hasattr(hints, "colorScheme") and hints.colorScheme() == Qt.ColorScheme.Dark
        else:
            dark = self.mode == "dark"
        return DARK if dark else LIGHT

    def set_mode(self, mode: str):
        if mode in MODES:
            self.mode = mode
            self.settings.setValue("appearance", mode)
            self._update()

    def _update(self):
        colors = self._pick()
        if colors is not self.colors:
            self.colors = colors
            apply_app_style()
            self.changed.emit()

    @property
    def is_dark(self) -> bool:
        return self.colors is DARK


def stylesheet(key: str) -> str:
    return STYLES[key].format_map(ThemeHost.instance().colors.__dict__)


def pixmap(resource_path: str, color_hex: str, size: int, dpr: float = 1.0) -> QPixmap:
    """A monochrome icon tinted to ``color_hex`` (awesomeUI's search field)."""
    scale = max(1.0, float(dpr))
    result = QPixmap(int(round(size * scale)), int(round(size * scale)))
    result.setDevicePixelRatio(scale)
    result.fill(Qt.GlobalColor.transparent)
    painter = QPainter(result)
    painter.drawPixmap(QRect(0, 0, size, size), QIcon(resource_path).pixmap(QSize(size, size)))
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(QRect(0, 0, size, size), QColor(color_hex))
    painter.end()
    return result


def connect(widget):
    """Re-render a control's stylesheet when the palette changes."""
    retheme = getattr(widget, "_retheme", None)
    if retheme is not None:
        ThemeHost.instance().changed.connect(retheme)


def sidebar_theme() -> awesomeui.SidebarTheme:
    c = ThemeHost.instance().colors
    return awesomeui.SidebarTheme(
        background=c.bg_secondary, border=c.divider, text=c.text_primary, text_muted=c.text_secondary,
        hover_background=c.surface_hover, active_background=c.bg_tertiary, active_indicator=c.accent,
        separator=c.divider, width=250)


def apply_app_style():
    app = QApplication.instance()
    if app is None:
        return
    c = ThemeHost.instance().colors
    palette = QPalette()
    for role, color in ((QPalette.Window, c.bg_primary), (QPalette.Base, c.bg_input),
                        (QPalette.AlternateBase, c.bg_tertiary), (QPalette.Button, c.bg_tertiary),
                        (QPalette.WindowText, c.text_primary), (QPalette.Text, c.text_primary),
                        (QPalette.ButtonText, c.text_primary), (QPalette.ToolTipBase, c.bg_secondary),
                        (QPalette.ToolTipText, c.text_primary), (QPalette.PlaceholderText, c.text_secondary),
                        (QPalette.Highlight, c.accent), (QPalette.HighlightedText, c.text_inverse),
                        (QPalette.Link, c.accent)):
        palette.setColor(role, QColor(color))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor(c.text_disabled))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(c.text_disabled))
    app.setPalette(palette)
    app.setStyleSheet(stylesheet("app"))


def install():
    """Configure awesomeUI and style the application. Call once, after the
    QApplication exists and before any control is created."""
    awesomeui.configure_theme(manager=ThemeHost.instance, stylesheet=stylesheet,
                              pixmap=pixmap, connect=connect)
    apply_app_style()
