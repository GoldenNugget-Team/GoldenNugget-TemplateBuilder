"""Self-test of a packaged build: ``Batter Builder --smoke``.

Builds the window offscreen, edits, saves, reopens and checks a template, then
prints BATTER_SMOKE_OK. CI runs it on each slice of the macOS app.
"""
import json
import os
import platform
import sys
import tempfile


def say(text: str):
    """Print, and append to $BATTER_SMOKE_OUT: a windowed Windows build has no
    stdout."""
    if sys.stdout is not None:
        print(text, flush=True)
    target = os.environ.get("BATTER_SMOKE_OUT")
    if target:
        with open(target, "a", encoding="utf-8") as handle:
            handle.write(text + "\n")


def run() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    expected = os.environ.get("TEST_ARCH")
    if expected and platform.machine() != expected:
        say(f"running as {platform.machine()}, expected {expected}")
        return 1
    from PySide6.QtCore import QSettings, QStandardPaths
    from PySide6.QtWidgets import QApplication
    QStandardPaths.setTestModeEnabled(True)
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, tempfile.mkdtemp())
    app = QApplication([])
    from .ui import theme
    theme.install()
    from . import batter, rules
    from .ui import icons
    assert not icons.app_icon().isNull(), "the app icon is missing"
    assert not icons.icon("toggle").isNull(), "the interface icons are missing"
    from .ui.main_window import MainWindow
    window = MainWindow()
    window.show()
    from .ui.updates import UpdateChecker     # QtNetwork made it into the build
    UpdateChecker(window)
    window.details.title.setText("Smoke")
    window.details.author.setText("CI")
    values = window.editor.writes.form.values
    values.add_row()
    window.editor.control.kind.setCurrentIndex(1)
    app.processEvents()
    path = os.path.join(tempfile.mkdtemp(), "smoke.batter")
    assert window._write(path), "save failed"
    loaded = batter.load(path)
    assert loaded.to_config() == window.template.to_config(), "round trip changed the template"
    found = rules.errors(rules.validate(loaded))
    window.dirty = False
    window.close()
    import PySide6
    say(json.dumps({"frozen": getattr(sys, "frozen", False), "machine": platform.machine(),
                      "python": platform.python_version(), "pyside6": PySide6.__version__,
                      "errors": [issue.text for issue in found]}))
    say("BATTER_SMOKE_OK")
    return 0
