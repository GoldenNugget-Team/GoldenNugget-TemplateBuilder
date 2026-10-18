"""Editing through the awesomeUI-based widgets changes the template (offscreen)."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QMessageBox

APP = QApplication.instance() or QApplication([])
QSettings.setDefaultFormat(QSettings.IniFormat)
QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, tempfile.mkdtemp())

from batter_builder import rules
from batter_builder.ui import theme, value_table

theme.install()

from batter_builder.ui.main_window import DETAILS, CHECK, MainWindow, slug


class Window(unittest.TestCase):
    def setUp(self):
        self.window = MainWindow()
        self.window.dirty = False

    def tearDown(self):
        self.window.dirty = False
        self.window.close()

    def test_new_template_opens_its_first_tweak(self):
        window = self.window
        self.assertEqual(len(window.template.tweaks), 1)
        self.assertEqual(window.sidebar.current_item_id(), "tweak:0")
        window.details.title.setText("My Pack")
        window.details.tags.setText("dock, ,minimal")
        self.assertEqual(window.template.title, "My Pack")
        self.assertEqual(window.template.tags, ["dock", "minimal"])
        self.assertTrue(window.dirty)

    def test_editing_a_tweak(self):
        window, editor = self.window, self.window.editor
        editor.label.setText("Dock Opacity")
        editor.id.setText("dock-alpha")
        editor.default.setChecked(True)
        tweak = window.template.tweaks[0]
        self.assertEqual((tweak.label, tweak.id, tweak.default), ("Dock Opacity", "dock-alpha", True))
        self.assertEqual(window.sidebar.item("tweak:0").label, "Dock Opacity")
        self.assertEqual(editor.title.text(), "Dock Opacity")

        values = editor.writes.form.values
        values.add_row()
        values.table.item(0, 0).setText("SBDockAlpha")
        values.table.cellWidget(0, 1).setCurrentText(value_table.CONTROL)
        self.assertEqual(tweak.writes[0].values, {"SBDockAlpha": "$value"})

        editor.control.kind.setCurrentIndex(1)     # Slider
        editor.control.s_max.setValue(10)
        editor.control.s_step.setValue(1)
        editor.control.s_default.setValue(4)
        self.assertEqual(tweak.control.to_config(),
                         {"type": "slider", "min": 0, "max": 10, "step": 1, "default": 4})

        window.details.title.setText("Dock")
        window.details.author.setText("me")
        window.revalidate()
        self.assertEqual(rules.errors(window.issues), [])
        self.assertIn('"SBDockAlpha": "$value"', window.check.preview.toPlainText())
        self.assertEqual(window.check.badge.text(), "Ready")

    def test_write_type_owner_and_off_side(self):
        editor = self.window.editor
        tweak = self.window.template.tweaks[0]
        form = editor.writes.form
        form.type.setCurrentIndex(2)               # Empty file
        form.owner.setCurrentIndex(1)              # root
        self.assertEqual((tweak.writes[0].type, tweak.writes[0].owner), ("empty", 0))
        editor.side.setCurrentIndex(1)             # When off
        editor.writes._add()
        self.assertEqual(len(tweak.writes_off), 1)
        self.assertEqual(editor.side._group.button(1).text(), "When off (1)")

    def test_value_types(self):
        values = self.window.editor.writes.form.values
        values.add_row()
        combo = values.table.cellWidget(0, 1)
        for kind, expected in ((value_table.INTEGER, 0), (value_table.REAL, 0.0),
                               (value_table.STRING, ""), (value_table.STRUCTURE, [])):
            combo.setCurrentText(kind)
            self.assertEqual(values.values["NewKey"], expected)
        values.table.cellWidget(0, 2).widget.setText('{"a": [1, true]}')
        self.assertEqual(values.values["NewKey"], {"a": [1, True]})
        values.table.cellWidget(0, 2).widget.setText("{broken")
        self.assertTrue(values.errors())

    def test_choice_control(self):
        control = self.window.editor.control
        control.kind.setCurrentIndex(3)            # Choice list (None, Slider, Text box, Choice list)
        tweak = self.window.template.tweaks[0]
        self.assertEqual([c.value for c in tweak.control.choices], [1, 2])
        control.c_table.item(1, 2).setText("x")
        self.assertTrue(control.choice_errors)
        control.c_table.cellWidget(1, 1).setCurrentText("String")
        self.assertEqual(tweak.control.choices[1].value, "x")
        self.assertEqual(control.choice_errors, [])

    def test_file_write(self):
        form = self.window.editor.writes.form
        form.type.setCurrentIndex(1)               # Whole file
        source = os.path.join(tempfile.mkdtemp(), "pref.plist")
        Path(source).write_bytes(b"<plist/>")
        with patch("batter_builder.ui.write_editor.QFileDialog.getOpenFileName", return_value=(source, "")):
            form._choose_file()
        write = self.window.template.tweaks[0].writes[0]
        self.assertEqual((write.type, write.source), ("file", "files/pref.plist"))
        self.assertEqual(self.window.template.entries["files/pref.plist"], b"<plist/>")

    def test_tweak_list_actions(self):
        window = self.window
        window.add_tweak()
        self.assertEqual(window.sidebar.current_item_id(), "tweak:1")
        window.duplicate_tweak()
        self.assertEqual(len({t.id for t in window.template.tweaks}), 3)
        window.move_tweak(-1)
        self.assertEqual(window.current_tweak(), 1)
        with patch("batter_builder.ui.main_window.QMessageBox.question", return_value=QMessageBox.Yes):
            window.remove_tweak()
            window.remove_tweak()
            window.remove_tweak()
        self.assertEqual(window.template.tweaks, [])
        self.assertIs(window.pages.currentWidget(), window.empty)

    def test_check_page_and_badges(self):
        window = self.window
        window.sidebar.set_current(CHECK)
        self.assertIn("error", window.check.badge.text())
        badge = window.sidebar._error_badges[CHECK]
        self.assertTrue(badge.text())
        self.assertFalse(badge.isHidden())
        window.sidebar.set_current(DETAILS)
        self.assertEqual(window.pages.currentIndex(), 0)

    def test_appearance_switch(self):
        host = theme.ThemeHost.instance()
        before = host.mode
        try:
            host.set_mode("dark")
            self.assertTrue(host.is_dark)
            host.set_mode("light")
            self.assertFalse(host.is_dark)
            self.assertIsNotNone(self.window.sidebar)
        finally:
            host.set_mode(before)

    def test_save_open_and_submit(self):
        window = self.window
        window.details.title.setText("Dock Pack")
        window.details.author.setText("me")
        window.editor.writes.form.values.add_row()
        folder = tempfile.mkdtemp()
        path = os.path.join(folder, "pack.batter")
        self.assertTrue(window._write(path))
        self.assertFalse(window.dirty)
        reopened = MainWindow()
        reopened.open_file(path)
        self.assertEqual(reopened.template.to_config(), window.template.to_config())
        reopened.dirty = False
        reopened.close()

        opened = []
        with patch("batter_builder.ui.main_window.QInputDialog.getText", return_value=("dock-pack", True)), \
                patch("batter_builder.ui.main_window.QFileDialog.getExistingDirectory", return_value=folder), \
                patch("batter_builder.ui.main_window.QDesktopServices.openUrl", side_effect=opened.append), \
                patch("batter_builder.ui.main_window.QMessageBox.information"):
            window.submit_to_catalog()
        self.assertTrue(os.path.exists(os.path.join(folder, "dock-pack.batter")))
        self.assertIn("upload/main/templates", opened[-1].toString())

    def test_submit_refuses_errors(self):
        with patch("batter_builder.ui.main_window.QMessageBox.warning") as warning, \
                patch("batter_builder.ui.main_window.QInputDialog.getText") as ask:
            self.window.submit_to_catalog()
        self.assertTrue(warning.called)
        self.assertFalse(ask.called)
        self.assertEqual(self.window.sidebar.current_item_id(), CHECK)

    def test_every_icon_used_exists(self):
        import re
        from batter_builder.ui import icons
        root = Path(__file__).resolve().parents[1] / "batter_builder"
        source = "\n".join(p.read_text() for p in root.rglob("*.py"))
        names = set(re.findall(r'icons\.(?:icon|attach)\((?:[\w.]+, )?"([\w-]+)"', source))
        names |= {n for group in re.findall(r'icon_names=\(([^)]*)\)', source)
                  for n in re.findall(r'"([\w-]+)"', group)}
        names |= set(re.findall(r'button\("[^"]*", [^,]+, "([\w-]+)"\)', source))
        self.assertGreater(len(names), 15)
        for name in sorted(names):
            with self.subTest(icon=name):
                self.assertTrue(Path(icons.path(name)).exists())
                self.assertFalse(icons.icon(name).isNull())
        self.assertFalse(icons.app_icon().isNull())

    def test_slug(self):
        self.assertEqual(slug("Dock Tweaks!"), "dock-tweaks")
        self.assertEqual(slug("Ж"), "my-template")


if __name__ == "__main__":
    unittest.main()
