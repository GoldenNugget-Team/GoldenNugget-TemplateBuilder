"""Editing through the awesomeUI-based widgets changes the template (offscreen)."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings, QStandardPaths, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QComboBox, QMessageBox, QSlider

APP = QApplication.instance() or QApplication([])
QStandardPaths.setTestModeEnabled(True)
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

    def test_recent_files_and_drop(self):
        from PySide6.QtCore import QMimeData, QPointF, QUrl
        from PySide6.QtGui import QDropEvent
        window = self.window
        window.settings.setValue("recent", [])
        window.details.title.setText("Dock Pack")
        window.details.author.setText("me")
        folder = tempfile.mkdtemp()
        first, second = os.path.join(folder, "a.batter"), os.path.join(folder, "b.batter")
        self.assertTrue(window._write(first))
        self.assertTrue(window._write(second))
        self.assertEqual(window.recent_files(), [second, first])
        window._fill_recent()
        self.assertEqual([a.text() for a in window.recent_menu.actions()][:2], ["b.batter", "a.batter"])

        os.remove(first)
        with patch("batter_builder.ui.main_window.QMessageBox.warning") as warning:
            window.open_recent(first)
        self.assertTrue(warning.called)
        self.assertEqual(window.recent_files(), [second])

        window.load_template(window.template.__class__(), "")
        data = QMimeData()
        data.setUrls([QUrl.fromLocalFile(second)])
        event = QDropEvent(QPointF(5, 5), Qt.CopyAction, data, Qt.LeftButton, Qt.NoModifier)
        window.dropEvent(event)
        self.assertEqual(window.path, second)
        self.assertEqual(window.template.title, "Dock Pack")

    def test_submit_refuses_a_too_large_template_without_saving(self):
        window = self.window
        window.details.title.setText("Dock Pack")
        window.details.author.setText("me")
        window.editor.writes.form.values.add_row()
        folder = tempfile.mkdtemp()
        with patch("batter_builder.ui.main_window.QInputDialog.getText", return_value=("dock-pack", True)), \
                patch("batter_builder.ui.main_window.QFileDialog.getExistingDirectory", return_value=folder), \
                patch("batter_builder.ui.main_window.rules.MAX_TEMPLATE_BYTES", 10), \
                patch("batter_builder.ui.main_window.QDesktopServices.openUrl") as opened, \
                patch("batter_builder.ui.main_window.QMessageBox.warning") as warning:
            window.submit_to_catalog()
        self.assertTrue(warning.called)
        self.assertFalse(opened.called)
        self.assertEqual(os.listdir(folder), [])

    def test_undo_and_redo(self):
        window, editor = self.window, self.window.editor
        self.assertFalse(window.undo_action.isEnabled())
        editor.label.setText("Dock")
        editor.label.setText("Dock Opacity")       # typing in a row is one step
        window._commit()
        window.details.title.setText("Pack")
        window.add_tweak()
        self.assertEqual(len(window.template.tweaks), 2)

        window.undo()                               # the added tweak
        self.assertEqual(len(window.template.tweaks), 1)
        self.assertEqual(window.template.title, "Pack")
        window.undo()                               # the title
        self.assertEqual(window.template.title, "")
        self.assertEqual(window.details.title.text(), "")
        window.undo()                               # the label
        self.assertEqual(window.template.tweaks[0].label, "Tweak 1")
        self.assertEqual(window.sidebar.item("tweak:0").label, "Tweak 1")
        self.assertFalse(window.undo_action.isEnabled())
        self.assertFalse(window.dirty)              # back to what was loaded

        window.redo()
        window.redo()
        self.assertEqual((window.template.tweaks[0].label, window.template.title), ("Dock Opacity", "Pack"))
        self.assertTrue(window.redo_action.isEnabled())
        editor = window.editor
        window.sidebar.set_current("tweak:0")
        window.editor.id.setText("dock")           # a new change drops the redo steps
        window._commit()
        self.assertFalse(window.redo_action.isEnabled())
        window.undo()
        self.assertEqual(window.template.tweaks[0].id, "tweak-1")

    def test_undo_brings_back_a_removed_tweak_and_its_file(self):
        window = self.window
        window.template.add_source("a.plist", b"1")
        window.template.tweaks[0].writes[0] = window.template.tweaks[0].writes[0].__class__(
            "file", "/var/mobile/Library/Preferences/a.plist", source="files/a.plist")
        window.load_template(window.template, "")
        with patch("batter_builder.ui.main_window.QMessageBox.question", return_value=QMessageBox.Yes):
            window.remove_tweak()
        self.assertEqual(window.template.tweaks, [])
        self.assertIs(window.pages.currentWidget(), window.empty)
        window.undo()
        self.assertEqual(window.template.tweaks[0].writes[0].source, "files/a.plist")
        self.assertEqual(window.template.entries, {"files/a.plist": b"1"})
        self.assertEqual(window.sidebar.current_item_id(), "tweak:0")

    def test_save_warns_about_errors(self):
        window = self.window
        folder = tempfile.mkdtemp()
        path = os.path.join(folder, "broken.batter")
        window.path = path
        for choice, saved, page in (("Cancel", False, "tweak:0"), ("Show Problems", False, CHECK),
                                    ("Save Anyway", True, CHECK)):
            with self.subTest(choice=choice), patch.object(QMessageBox, "exec"), \
                    patch.object(QMessageBox, "clickedButton",
                                 lambda box, c=choice: next(b for b in box.buttons()
                                                            if b.text().replace("&", "") == c)):
                self.assertEqual(window.save_file(), saved)
                self.assertEqual(os.path.exists(path), saved)
                self.assertEqual(window.sidebar.current_item_id(), page)

    def test_saving_during_the_tour_saves_the_users_template(self):
        window = self.window
        window.details.title.setText("Mine")
        window.details.author.setText("me")
        window.editor.writes.form.values.add_row()
        path = os.path.join(tempfile.mkdtemp(), "mine.batter")
        window._write(path)
        window.start_tour(speed=50)
        self.assertTrue(window.tour.active)
        self.assertTrue(window.save_file())
        self.assertFalse(window.tour.active)
        from batter_builder import batter
        self.assertEqual(batter.load(path).title, "Mine")

    def test_remove_unused_files(self):
        window = self.window
        window.template.add_source("old.plist", b"1")
        window.sidebar.set_current(DETAILS)
        self.assertFalse(window.details.remove_unused.isHidden())
        window.details.remove_unused.click()
        self.assertEqual(window.template.entries, {})
        self.assertTrue(window.details.remove_unused.isHidden())
        window.undo()
        self.assertEqual(window.template.entries, {"files/old.plist": b"1"})

    def test_tweak_shortcuts(self):
        from PySide6.QtGui import QKeySequence
        window = self.window
        actions = {a.text(): a for a in window.findChildren(QAction)}
        self.assertEqual(actions["Add Tweak"].shortcut(), QKeySequence("Ctrl+T"))
        actions["Add Tweak"].trigger()
        actions["Duplicate Tweak"].trigger()
        self.assertEqual([t.id for t in window.template.tweaks], ["tweak-1", "tweak-2", "tweak-2-2"])
        actions["Move Up"].trigger()
        self.assertEqual([t.id for t in window.template.tweaks], ["tweak-1", "tweak-2-2", "tweak-2"])
        self.assertEqual(window.current_tweak(), 1)
        actions["Move Down"].trigger()
        self.assertEqual(window.current_tweak(), 2)

    def test_import_keys_from_a_plist(self):
        import plistlib
        from batter_builder.ui.value_table import ImportDialog
        path = os.path.join(tempfile.mkdtemp(), "prefs.plist")
        with open(path, "wb") as handle:
            plistlib.dump({"SBDockAlpha": 0.5, "SBHideDock": True, "Other": "x"}, handle)
        values = self.window.editor.writes.form.values
        values.add_row()
        values.table.item(0, 0).setText("SBHideDock")         # already there: gets the plist's value

        def pick(dialog):
            dialog.filter.setText("sb")
            self.assertTrue(dialog.tree.findItems("Other", Qt.MatchExactly)[0].isHidden())
            dialog._check_visible(Qt.Checked)
            self.assertEqual(dialog.buttons.button(dialog.buttons.StandardButton.Ok).text(), "Import 2 Keys")
            return ImportDialog.Accepted
        with patch.object(ImportDialog, "exec", pick):
            values.import_plist(path)
        self.assertEqual(self.window.template.tweaks[0].writes[0].values, {"SBHideDock": True, "SBDockAlpha": 0.5})
        self.assertEqual(values.table.rowCount(), 2)
        self.assertEqual(values.errors(), [])

    def test_drag_a_tweak_in_the_sidebar(self):
        from PySide6.QtCore import QEvent, QPoint, QPointF
        from PySide6.QtGui import QMouseEvent
        window = self.window
        window.show()
        window.add_tweak()
        window.add_tweak()
        APP.processEvents()

        def send(item, kind, y, buttons=Qt.LeftButton):
            point = QPointF(10, y)
            event = QMouseEvent(kind, point, item.mapToGlobal(point), Qt.LeftButton, buttons, Qt.NoModifier)
            APP.sendEvent(item, event)

        first, last = window.sidebar.item("tweak:0"), window.sidebar.item("tweak:2")
        below = first.mapFromGlobal(last.mapToGlobal(QPoint(0, last.height() - 2))).y()
        send(first, QEvent.MouseButtonPress, 5)
        send(first, QEvent.MouseMove, 30)
        self.assertTrue(window._drag.line.isVisible())
        send(first, QEvent.MouseMove, below)
        send(first, QEvent.MouseButtonRelease, below, Qt.NoButton)
        APP.processEvents()
        self.assertEqual([t.id for t in window.template.tweaks], ["tweak-2", "tweak-3", "tweak-1"])
        self.assertEqual(window.current_tweak(), 2)
        window.undo()
        self.assertEqual([t.id for t in window.template.tweaks], ["tweak-1", "tweak-2", "tweak-3"])

        item = window.sidebar.item("tweak:1")       # a plain click still opens the tweak
        send(item, QEvent.MouseButtonPress, 5)
        send(item, QEvent.MouseButtonRelease, 5, Qt.NoButton)
        self.assertEqual([t.id for t in window.template.tweaks], ["tweak-1", "tweak-2", "tweak-3"])

    def test_iphone_preview(self):
        from batter_builder.model import Choice, Control, Write
        window = self.window
        tweak = window.template.tweaks[0]
        tweak.label = "Dock Opacity"
        tweak.writes[0].values = {"SBDockAlpha": "$value", "Fixed": True}
        tweak.writes_off = [Write("plist", tweak.writes[0].path, {"SBDockAlpha": 1})]
        tweak.control = Control("slider", 0.5, 0, 1, 0.25)
        window.template.tweaks.append(window.template.tweaks[0].__class__(
            id="size", label="Size", default=True, writes=[Write("plist", tweak.writes[0].path, {"S": "$value"})],
            control=Control("choice", 1, choices=[Choice("Small", 1), Choice("Big", 2)])))
        window.load_template(window.template, "")
        window.sidebar.set_current("preview")
        page = window.preview
        self.assertEqual(window.pages.currentWidget().widget(), page)
        text = page.writes.toPlainText()
        self.assertIn("○ Dock Opacity (off)", text)
        self.assertIn("SBDockAlpha = 1", text)
        self.assertIn("● Size (on, value 2)", text)

        dock, size = page.rows
        dock.switch.setChecked(True)
        dock.control.findChild(QSlider).setValue(3)
        size.control.findChild(QComboBox).setCurrentIndex(0)
        text = page.writes.toPlainText()
        self.assertIn("● Dock Opacity (on, value 0.75)", text)
        self.assertIn("SBDockAlpha = 0.75", text)
        self.assertIn("S = 1", text)
        self.assertEqual(tweak.writes[0].values["SBDockAlpha"], "$value")    # the template is untouched

    def test_unsaved_changes_are_kept_and_offered_back(self):
        window = self.window
        window.clear_recovery()
        window.autosave()                                   # nothing unsaved: nothing kept
        self.assertFalse(os.path.exists(window.recovery_path()))
        path = os.path.join(tempfile.mkdtemp(), "mine.batter")
        window.details.title.setText("Before")
        window.details.author.setText("me")
        window._write(path)
        window.details.title.setText("Unsaved work")
        window.autosave()
        self.assertTrue(os.path.exists(window.recovery_path()))

        later = MainWindow()                                # the next start, after a crash
        with patch("batter_builder.ui.main_window.QMessageBox.question", return_value=QMessageBox.Yes):
            self.assertTrue(later.offer_recovery())
        self.assertEqual((later.template.title, later.path, later.dirty), ("Unsaved work", path, True))
        later._write(path)                                  # saving drops the copy
        self.assertFalse(os.path.exists(window.recovery_path()))
        later.close()

        window.autosave()
        again = MainWindow()
        with patch("batter_builder.ui.main_window.QMessageBox.question", return_value=QMessageBox.No):
            self.assertFalse(again.offer_recovery())
        self.assertFalse(os.path.exists(window.recovery_path()))
        again.close()

    def test_update_check(self):
        import json
        window = self.window
        with patch("batter_builder.ui.updates.UpdateChecker.check"):     # no network in tests
            window.check_updates()
        checker = window.updates
        release = lambda tag: json.dumps({"tag_name": tag, "html_url": "https://example.invalid/r"}).encode()
        checker.handle(release("v0.1.0"), "")
        self.assertTrue(window.update_button.isHidden())
        checker.handle(release("v99.0"), "")
        self.assertFalse(window.update_button.isHidden())
        self.assertEqual(window.update_button.text(), "Version 99.0 is available")
        self.assertEqual(window.update_url, "https://example.invalid/r")
        window._manual_update_check = True
        with patch("batter_builder.ui.main_window.QMessageBox.warning") as warning:
            checker.handle(None, "Host not found")
        self.assertIn("Host not found", warning.call_args[0][2])
        with patch("batter_builder.ui.main_window.QMessageBox.information") as information:
            checker.handle(release("v0.1"), "")
        self.assertIn("latest version", information.call_args[0][2])

    def test_known_keys_are_suggested(self):
        from batter_builder import known_keys
        values = self.window.editor.writes.form.values
        springboard = known_keys.for_path(self.window.template.tweaks[0].writes[0].path)
        self.assertIn("SBDisableParallax", springboard)
        self.assertEqual(values.keys.model.rowCount(), len(springboard))
        self.assertFalse(values.note.isHidden())

        values.add_row()                                   # NewKey, Boolean true
        values.table.item(0, 0).setText("SBDontDimOrLockOnAC")
        entry = springboard["SBDontDimOrLockOnAC"]
        self.assertEqual(values.table.cellWidget(0, 1).currentData(), entry["type"])
        self.assertIn(entry["title"], values.table.item(0, 0).toolTip())
        self.assertEqual(self.window.template.tweaks[0].writes[0].values, {"SBDontDimOrLockOnAC": entry["value"]})

        values.table.cellWidget(0, 1).setCurrentText(value_table.CONTROL)   # a chosen type is kept
        values.table.item(0, 0).setText("SBDisableParallax")
        self.assertEqual(self.window.template.tweaks[0].writes[0].values, {"SBDisableParallax": "$value"})

        self.window.editor.writes.form.path.setEditText("/var/mobile/Library/Preferences/com.example.plist")
        self.assertEqual(values.keys.model.rowCount(), 0)
        self.assertTrue(values.note.isHidden())

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
