"""Templates saved here load in GoldenNugget itself.

Set GOLDENNUGGET_DIR to a GoldenNugget checkout (with its dependencies
installed) to run; skipped otherwise.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from batter_builder import batter, rules
from batter_builder.model import Tweak, Write
from tests.test_core import SPRINGBOARD, sample

GOLDENNUGGET = os.environ.get("GOLDENNUGGET_DIR", "")


@unittest.skipUnless(GOLDENNUGGET and os.path.isdir(GOLDENNUGGET), "GOLDENNUGGET_DIR is not set")
class GoldenNugget(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, GOLDENNUGGET)
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])
        from src.tweaks.posterboard.template_file import TemplateFile
        from src.tweaks.posterboard import community_tweaks
        from src.exceptions.posterboard_exceptions import PBTemplateException
        cls.TemplateFile, cls.community, cls.Refused = TemplateFile, community_tweaks, PBTemplateException

    def save(self, template):
        path = os.path.join(tempfile.mkdtemp(), "t.batter")
        batter.save(template, path)
        return path

    def test_known_keys_match_goldennuggets_registry(self):
        import importlib.util
        from batter_builder import known_keys_data
        tool = Path(__file__).resolve().parents[1] / "tools" / "make_known_keys.py"
        spec = importlib.util.spec_from_file_location("make_known_keys", tool)
        maker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(maker)
        current = maker.build(Path(GOLDENNUGGET).resolve())["paths"]
        self.assertEqual(known_keys_data.PATHS, current,
                         "GoldenNugget's tweaks changed: run python tools/make_known_keys.py $GOLDENNUGGET_DIR")

    def test_sample_loads_with_the_same_tweaks(self):
        template = sample()
        source = template.add_source("pref.plist", b"<plist/>")
        template.tweaks.append(Tweak(id="file", label="File", writes=[
            Write("file", "/var/mobile/Library/Preferences/com.example.plist", source=source),
            Write("empty", "/var/mobile/Library/Preferences/com.example.empty.plist")]))
        self.assertEqual(rules.errors(rules.validate(template)), [])
        loaded = self.TemplateFile(self.save(template))
        self.assertEqual([t.id for t in loaded.tweaks], [t.id for t in template.tweaks])
        self.assertEqual(loaded.tweaks[3].writes[0].data, b"<plist/>")
        self.assertEqual(loaded.tweaks[1].control.default, 0.5)
        self.assertEqual(loaded.tweaks[2].control.default, 2)

    def test_errors_here_are_errors_there(self):
        cases = [
            Write("plist", "/var/tmp/a.plist", {"A": 1}),
            Write("plist", "/var/root/Library/Lockdown/a.plist", {"A": 1}),
            Write("plist", SPRINGBOARD, {}),
            Write("empty", "/var/mobile/a", owner=7),
            Write("file", "/var/mobile/a", source="files/missing"),
        ]
        for write in cases:
            template = sample()
            template.tweaks[0].writes = [write]
            with self.subTest(write=write):
                self.assertTrue(rules.errors(rules.validate(template)))
                with self.assertRaises((self.community.CommunityTweakError, self.Refused)):
                    self.TemplateFile(self.save(template))

    def test_path_rules_match(self):
        for path in (SPRINGBOARD, "/var/containers/Shared/SystemGroup/g/Library/a.plist",
                     "/var/containers/Data/SystemGroup/g", "/var/db/x", "/var/preferences/a",
                     "/var/mobile/Library/Backup/a", "/var/mobile/../a", "/var/mobile/", "/etc/a"):
            try:
                self.community.check_path(path)
                theirs = ""
            except self.community.CommunityTweakError as error:
                theirs = str(error)
            with self.subTest(path=path):
                self.assertEqual(rules.path_problem(path), theirs)


if __name__ == "__main__":
    unittest.main()
