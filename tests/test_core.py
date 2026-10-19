"""Model, rules and .batter file tests (no display needed)."""
import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from batter_builder import batter, rules
from batter_builder.model import Choice, Control, Template, Tweak, Write

SPRINGBOARD = "/var/Managed Preferences/mobile/com.apple.springboard.plist"


def sample() -> Template:
    return Template(
        title="Dock Tweaks", author="me", description="Dock things.", min_version="26.0",
        tags=["dock"],
        tweaks=[
            Tweak(id="hide-dock", label="Hide Dock Background", default=True,
                  writes=[Write("plist", SPRINGBOARD, {"SBHideDockBackground": True})],
                  writes_off=[Write("plist", SPRINGBOARD, {"SBHideDockBackground": False})]),
            Tweak(id="dock-alpha", label="Dock Opacity", control=Control("slider", 0.5, 0, 1, 0.1),
                  writes=[Write("plist", SPRINGBOARD, {"SBDockAlpha": "$value"})]),
            Tweak(id="size", label="Size", control=Control("choice", 1, choices=[Choice("S", 1), Choice("L", 2)]),
                  writes=[Write("plist", SPRINGBOARD, {"Size": "$value"})]),
        ])


def texts(issues, level=rules.ERROR):
    return [issue.text for issue in issues if issue.level == level]


class Model(unittest.TestCase):
    def test_config_round_trip(self):
        template = sample()
        config = template.to_config()
        self.assertEqual(config["format_version"], "3")
        self.assertNotIn("writes_off", config["tweaks"][1])
        self.assertEqual(Template.from_config(json.loads(json.dumps(config))).to_config(), config)

    def test_unknown_keys_and_files_are_kept(self):
        raw = sample().to_config()
        raw.update(domain="AppDomain-com.apple.PosterBoard", options=[{"type": "remove"}])
        template = Template.from_config(raw, {"Container/a.txt": b"x"})
        self.assertEqual(template.to_config()["options"], [{"type": "remove"}])
        self.assertEqual(template.entries, {"Container/a.txt": b"x"})

    def test_add_source_reuses_identical_files(self):
        template = Template()
        first = template.add_source("dir/a.plist", b"1")
        self.assertEqual(first, "files/a.plist")
        self.assertEqual(template.add_source("a.plist", b"2"), "files/a-2.plist")
        self.assertEqual(template.add_source("other", b"1"), first)

    def test_uses_value(self):
        tweak = sample().tweaks[1]
        self.assertTrue(tweak.uses_value())
        self.assertFalse(sample().tweaks[0].uses_value())


class Rules(unittest.TestCase):
    def test_sample_has_no_errors(self):
        issues = rules.validate(sample())
        self.assertEqual(texts(issues), [])
        self.assertIn("Low risk: keys in Managed Preferences.", texts(issues, rules.INFO))

    def test_paths(self):
        self.assertEqual(rules.path_problem(SPRINGBOARD), "")
        self.assertEqual(rules.path_problem("/var/containers/Shared/SystemGroup/group/Library/a.plist"), "")
        self.assertIn("cannot write", rules.path_problem("/var/containers/Shared/SystemGroup/group"))
        self.assertIn("cannot write", rules.path_problem("/var/tmp/a.plist"))
        self.assertIn("start with /var/", rules.path_problem("/private/var/mobile/a"))
        self.assertIn("'..'", rules.path_problem("/var/mobile/../root/a"))
        self.assertIn("protected", rules.path_problem("/var/root/Library/Lockdown/data_ark.plist"))
        self.assertIn("protected", rules.path_problem("/var/mobile/Library/Backup/x"))

    def test_tweak_errors(self):
        template = sample()
        template.tweaks[1].id = "hide-dock"
        template.tweaks[2].label = ""
        template.tweaks[0].min_version = "26.x"
        template.tweaks[0].writes = []
        found = texts(rules.validate(template))
        self.assertIn('The id "hide-dock" is used twice.', found)
        self.assertIn("Every tweak needs a label of at most 80 characters.", found)
        self.assertIn("iOS versions look like 18 or 18.4.", found)
        self.assertIn("A tweak needs at least one write for when it is on.", found)

    def test_control_errors_and_warnings(self):
        template = sample()
        template.tweaks[1].control = Control("slider", 0, 1, 1, 0)
        template.tweaks[2].control.default = 5
        template.tweaks[0].control = Control("text", "abc", max_length=2)
        issues = rules.validate(template)
        self.assertIn("A slider needs min below max and a positive step.", texts(issues))
        self.assertIn("A choice default is the index of a choice.", texts(issues))
        warnings = texts(issues, rules.WARNING)
        self.assertIn("The text default is longer than max_length; GoldenNugget cuts it.", warnings)
        self.assertIn("The control's value is not used: put \"$value\" into a plist value.", warnings)

    def test_value_without_control_is_a_warning(self):
        template = sample()
        template.tweaks[1].control = None
        self.assertTrue(any("written literally" in text for text in texts(rules.validate(template), rules.WARNING)))

    def test_write_errors(self):
        template = sample()
        template.tweaks[0].writes = [
            Write("plist", SPRINGBOARD, {}),
            Write("plist", SPRINGBOARD, {"A": None}),
            Write("file", "/var/mobile/Library/Preferences/x.plist", source="files/missing"),
            Write("empty", "/var/db/x", owner=7),
        ]
        found = texts(rules.validate(template))
        self.assertIn("A plist write needs at least one key.", found)
        self.assertIn("Plist values cannot be null.", found)
        self.assertIn("Missing file in template: files/missing", found)
        self.assertIn("The owner is 501 (mobile) or 0 (root).", found)
        self.assertIn(f"{SPRINGBOARD} is written both as plist keys and as a whole file.",
                      texts(rules.validate(Template(title="t", author="a", tweaks=[Tweak(
                          id="x", label="x", writes=[Write("plist", SPRINGBOARD, {"A": 1}),
                                                     Write("empty", SPRINGBOARD)])]))))

    def test_risk_levels(self):
        self.assertEqual(rules.write_risk(Write("plist", SPRINGBOARD, {"A": 1}))[0], rules.INFO)
        self.assertIn("Medium", rules.write_risk(Write("plist", "/var/mobile/Library/Preferences/a.plist"))[1])
        self.assertIn("High", rules.write_risk(Write("empty", "/var/db/a"))[1])

    def test_template_errors(self):
        found = texts(rules.validate(Template(tags=["x" * 30])))
        self.assertIn("The template needs a title.", found)
        self.assertIn("The template needs an author.", found)
        self.assertIn("Add at least one tweak.", found)
        self.assertIn("Up to 8 tags of at most 24 characters.", found)
        template = sample()
        template.entries["Container/Library/a"] = b"x"
        self.assertIn("The template has a Container folder but no domain.", texts(rules.validate(template)))


class Files(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()

    def path(self, name):
        return os.path.join(self.folder, name)

    def test_save_and_load(self):
        template = sample()
        source = template.add_source("pref.plist", b"<plist/>")
        template.tweaks.append(Tweak(id="file", label="File", writes=[
            Write("file", "/var/mobile/Library/Preferences/com.example.plist", source=source)]))
        batter.save(template, self.path("t.batter"))
        with zipfile.ZipFile(self.path("t.batter")) as archive:
            self.assertEqual(sorted(archive.namelist()), ["config.json", "files/pref.plist"])
        loaded = batter.load(self.path("t.batter"))
        self.assertEqual(loaded.to_config(), template.to_config())
        self.assertEqual(loaded.entries, {"files/pref.plist": b"<plist/>"})

    def test_config_in_a_folder(self):
        with zipfile.ZipFile(self.path("nested.batter"), "w") as archive:
            archive.writestr("Pack/config.json", json.dumps(sample().to_config()))
            archive.writestr("Pack/files/a", b"1")
        loaded = batter.load(self.path("nested.batter"))
        self.assertEqual(loaded.entries, {"files/a": b"1"})
        with zipfile.ZipFile(self.path("outside.batter"), "w") as archive:
            archive.writestr("Pack/config.json", json.dumps(sample().to_config()))
            archive.writestr("Other/a", b"1")
        with self.assertRaises(batter.BatterError):
            batter.load(self.path("outside.batter"))

    def test_bad_files(self):
        Path(self.path("text.batter")).write_text("not a zip")
        with self.assertRaises(batter.BatterError):
            batter.load(self.path("text.batter"))
        with zipfile.ZipFile(self.path("empty.batter"), "w") as archive:
            archive.writestr("readme.txt", "x")
        with self.assertRaises(batter.BatterError):
            batter.load(self.path("empty.batter"))
        with zipfile.ZipFile(self.path("json.batter"), "w") as archive:
            archive.writestr("config.json", "{")
        with self.assertRaises(batter.BatterError):
            batter.load(self.path("json.batter"))

    def test_failed_save_keeps_previous_file(self):
        batter.save(sample(), self.path("keep.batter"))
        before = Path(self.path("keep.batter")).read_bytes()
        broken = sample()
        broken.entries["files/x"] = object()   # not bytes: writing fails
        with self.assertRaises(TypeError):
            batter.save(broken, self.path("keep.batter"))
        self.assertEqual(Path(self.path("keep.batter")).read_bytes(), before)
        self.assertEqual([n for n in os.listdir(self.folder) if n.endswith(".tmp")], [])

    def test_saved_file_is_readable_like_any_other(self):
        umask = os.umask(0o022)
        try:
            batter.save(sample(), self.path("mode.batter"))
            self.assertEqual(os.stat(self.path("mode.batter")).st_mode & 0o777, 0o644)
            os.chmod(self.path("mode.batter"), 0o640)
            batter.save(sample(), self.path("mode.batter"))
            self.assertEqual(os.stat(self.path("mode.batter")).st_mode & 0o777, 0o640)
        finally:
            os.umask(umask)

    def test_malformed_choices_still_open(self):
        for choices in (5, "abc", [{"label": 5, "value": 1}, "x"]):
            with self.subTest(choices=choices):
                template = Template.from_config({"tweaks": [{"control": {"type": "choice", "choices": choices}}]})
                self.assertTrue(all(isinstance(c.label, str) for c in template.tweaks[0].control.choices))
                rules.validate(template)


class PlistImport(unittest.TestCase):
    def test_reads_what_config_json_can_hold(self):
        import datetime
        import plistlib
        from batter_builder import plist_import
        data = plistlib.dumps({"On": True, "Count": 3, "Alpha": 0.5, "Name": "x", "List": [1, {"a": "b"}],
                               "Blob": b"\x00", "When": datetime.datetime(2026, 1, 1), "Huge": 2 ** 40},
                              fmt=plistlib.FMT_BINARY)
        values, skipped = plist_import.read(data)
        self.assertEqual(values, {"On": True, "Count": 3, "Alpha": 0.5, "Name": "x", "List": [1, {"a": "b"}]})
        self.assertEqual(sorted(note.split(":")[0] for note in skipped), ["Blob", "Huge", "When"])
        for bad in (b"nope", plistlib.dumps([1, 2])):
            with self.assertRaises(plist_import.PlistError):
                plist_import.read(bad)


if __name__ == "__main__":
    unittest.main()
