"""The guided tour runs through, and the user's template comes back after it
however it ends (offscreen)."""
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QSettings, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

APP = QApplication.instance() or QApplication([])
QSettings.setDefaultFormat(QSettings.IniFormat)
QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, tempfile.mkdtemp())

from batter_builder import rules
from batter_builder.model import Template, Tweak, Write
from batter_builder.ui import theme

theme.install()

from batter_builder.ui.main_window import MainWindow

SPRINGBOARD = "/var/Managed Preferences/mobile/com.apple.springboard.plist"


def wait_until(condition, seconds=60):
    end = time.monotonic() + seconds
    while not condition() and time.monotonic() < end:
        QTest.qWait(5)
    return condition()


class GuidedTour(unittest.TestCase):
    def setUp(self):
        self.window = MainWindow()
        self.window.resize(1300, 880)
        self.window.show()
        mine = Template(title="Mine", author="me", tweaks=[
            Tweak(id="keep", label="Keep Me", writes=[Write("plist", SPRINGBOARD, {"A": True})])])
        self.window.load_template(mine, "/somewhere/mine.batter")
        self.window.dirty = True
        self.mine = mine
        self.before = mine.to_config()

    def tearDown(self):
        if self.window.tour is not None:
            self.window.tour.finish()
        self.window.dirty = False
        self.window.close()

    def assert_restored(self):
        window = self.window
        self.assertIs(window.template, self.mine)
        self.assertEqual(window.template.to_config(), self.before)
        self.assertEqual(window.path, "/somewhere/mine.batter")
        self.assertTrue(window.dirty)
        self.assertEqual(window.details.title.text(), "Mine")
        self.assertEqual(window.sidebar.item("tweak:0").label, "Keep Me")

    def test_full_tour_builds_a_valid_example_and_restores(self):
        seen = {}
        with patch("batter_builder.batter.save", side_effect=AssertionError("the tour must not save")):
            tour = self.window.start_tour(speed=400)
            self.assertIsNot(self.window.template, self.mine)

            def watch():
                if tour.active and self.window.template is not self.mine:
                    seen["config"] = self.window.template.to_config()
                    seen["errors"] = rules.errors(rules.validate(self.window.template))
                return not tour.active
            self.assertTrue(wait_until(watch, 120))
        self.assertGreater(tour.number, 30)
        self.assertEqual(seen["config"]["title"], "Still Home Screen")
        self.assertEqual([t["id"] for t in seen["config"]["tweaks"]], ["no-parallax", "auto-lock"])
        self.assertEqual(seen["config"]["tweaks"][1]["control"],
                         {"type": "slider", "min": 1, "max": 10, "step": 1, "default": 5})
        self.assertEqual(seen["errors"], [])
        self.assert_restored()

    def test_end_tour_midway_restores(self):
        tour = self.window.start_tour(speed=20)
        QTest.qWait(300)
        self.assertTrue(tour.active)
        tour.controls.end.click()
        self.assertFalse(tour.active)
        self.assert_restored()

    def test_escape_ends_and_other_keys_are_held_back(self):
        tour = self.window.start_tour(speed=1)
        QTest.qWait(50)
        title = self.window.details.title
        swallowed = tour.eventFilter(title, QKeyEvent(QEvent.KeyPress, Qt.Key_A, Qt.NoModifier, "a"))
        self.assertTrue(swallowed)
        QTest.keyClick(self.window, Qt.Key_Escape)
        self.assertFalse(tour.active)
        self.assert_restored()

    def test_pause_and_next(self):
        tour = self.window.start_tour(speed=1)
        QTest.qWait(50)
        tour.controls.pause.click()
        self.assertTrue(tour.paused)
        before = tour.number
        tour.controls.next.click()
        self.assertGreater(tour.number, before)
        self.assertTrue(tour.paused)
        tour.controls.pause.click()
        self.assertFalse(tour.paused)
        tour.finish()
        self.assert_restored()

    def test_closing_the_window_during_the_tour_restores_first(self):
        tour = self.window.start_tour(speed=1)
        QTest.qWait(50)
        asked = []
        with patch.object(self.window, "_confirm_discard",
                          side_effect=lambda: asked.append(self.window.template is self.mine) or False):
            self.window.close()
        self.assertFalse(tour.active)
        self.assertEqual(asked, [True])
        self.assert_restored()

    def test_starting_twice_keeps_one_tour(self):
        first = self.window.start_tour(speed=1)
        self.assertIs(self.window.start_tour(speed=1), first)
        first.finish()
        self.assert_restored()


if __name__ == "__main__":
    unittest.main()
