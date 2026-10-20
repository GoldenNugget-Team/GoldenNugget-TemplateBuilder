"""The Russian translation covers every interface text, keeps placeholders,
and the window and tour work in it (offscreen)."""
import ast
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from batter_builder import i18n
from batter_builder.translations_ru import RU

ROOT = Path(__file__).resolve().parents[1] / "batter_builder"


def interface_texts() -> set:
    """Every English text the code passes through _ or n_, the tour's step
    texts, and the type names shown in combo boxes."""
    found = set()
    for path in ROOT.rglob("*.py"):
        if path.name.startswith("translations_"):
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call):
                name = getattr(node.func, "id", getattr(node.func, "attr", ""))
                texts = [a.value for a in node.args if isinstance(a, ast.Constant) and isinstance(a.value, str)]
                if name == "_" and texts:
                    found.add(texts[0])
                elif name == "n_" and texts:
                    found.add(texts[0])
                elif name in ("say", "show") and path.name == "tour.py" and len(texts) >= 2:
                    found.update(texts[:2])
    from batter_builder.ui import options_page, tweak_editor, value_table
    return (found | set(value_table.TYPES) | set(tweak_editor.CHOICE_TYPES)
            | set(options_page.TYPE_LABELS.values()) | set(options_page.TYPE_NOTES.values()))


def fields(text: str) -> set:
    return set(re.findall(r"\{(\w*)\}", text))


class Translation(unittest.TestCase):
    def test_every_text_is_translated(self):
        missing = sorted(text for text in interface_texts() if text not in RU)
        self.assertEqual(missing, [])

    def test_no_text_is_translated_twice(self):
        import collections
        source = (ROOT / "translations_ru.py").read_text(encoding="utf-8")
        table = next(node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Dict))
        keys = collections.Counter(ast.literal_eval(key) for key in table.keys)
        self.assertEqual([key for key, count in keys.items() if count > 1], [])

    def test_placeholders_are_kept(self):
        for english, russian in RU.items():
            with self.subTest(text=english):
                for form in (russian if isinstance(russian, tuple) else (russian,)):
                    self.assertEqual(fields(form), fields(english))

    def test_no_name_hides_the_translate_function(self):
        for path in ROOT.rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            with self.subTest(file=path.name):
                self.assertNotRegex(source, r"\*_\)|\b_\s*=[^=]|for _ in|, _ =|lambda _\b(?!\w)")

    def test_plural_forms(self):
        try:
            i18n.setup("ru")
            self.assertEqual([i18n.n_(n, "{n} error", "{n} errors") for n in (1, 2, 5, 11, 21, 22, 112)],
                             ["1 ошибка", "2 ошибки", "5 ошибок", "11 ошибок", "21 ошибка", "22 ошибки",
                              "112 ошибок"])
            self.assertEqual(i18n._("Save"), "Сохранить")
            self.assertEqual(i18n._("not translated"), "not translated")
        finally:
            i18n.setup("en")
        self.assertEqual(i18n.n_(2, "{n} error", "{n} errors"), "2 errors")
        self.assertEqual(i18n._("Save"), "Save")


class RussianWindow(unittest.TestCase):
    def test_window_and_tour_in_russian(self):
        from PySide6.QtCore import QSettings, QStandardPaths
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])
        QStandardPaths.setTestModeEnabled(True)
        QSettings.setDefaultFormat(QSettings.IniFormat)
        QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, tempfile.mkdtemp())
        from batter_builder.ui import theme
        theme.install()
        from batter_builder.ui.main_window import MainWindow
        i18n.setup("ru")
        try:
            window = MainWindow()
            self.assertEqual(window.menuBar().actions()[0].text(), "&Файл")
            self.assertEqual(window.sidebar.item("details").label, "Сведения")
            self.assertIn("ошиб", window.check.badge.text())
            self.assertTrue(any("Записи plist нужен" in issue.text for issue in window.issues))
            window.sidebar.set_current("preview")
            self.assertIn("выкл", window.preview.writes.toPlainText())
            tour = window.start_tour(speed=400)
            for _step in range(2000):
                if not tour.active:
                    break
                app.processEvents()
                tour.skip()
            self.assertFalse(tour.active)
            self.assertEqual(window.template.tweaks[0].id, "tweak-1")     # the user's template is back
            window.dirty = False
            window.close()
        finally:
            i18n.setup("en")


if __name__ == "__main__":
    unittest.main()
