"""Build the Universal2 macOS app, validate it and package a ZIP and a DMG.
Adapted from GoldenNugget's tools/package_macos.py.

Run with a universal2 Python (the python.org installer) whose PySide6 wheels
are universal2:

    python tools/build_macos.py

Writes dist/Batter Builder.app, dist/BatterBuilder-macOS-Universal2.zip,
dist/BatterBuilder-macOS-Universal2.dmg, dist/macOS-validation.json and
dist/SHA256SUMS-macOS.txt.
"""
from pathlib import Path
import hashlib
import json
import plistlib
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
NAME = "Batter Builder"
APP = DIST / f"{NAME}.app"
BUNDLE_ID = "com.goldennugget-team.batterbuilder"
FLOOR = "12.0"          # what PySide6 6.9.3's universal2 binaries target (requirements-macos.txt)
DATA = ("--add-data", "batter_builder/ui/icons:batter_builder/ui/icons",
        "--add-data", "assets/icon.png:assets", "--add-data", "assets/icon-small.svg:assets")
ZIP = DIST / "BatterBuilder-macOS-Universal2.zip"
DMG = DIST / "BatterBuilder-macOS-Universal2.dmg"


def run(*args):
    print("+", " ".join(str(a) for a in args), flush=True)
    subprocess.run([str(a) for a in args], check=True, cwd=ROOT)


def version() -> str:
    namespace = {}
    exec((ROOT / "batter_builder/__init__.py").read_text(), namespace)
    return namespace["__version__"]


def build():
    shutil.rmtree(DIST, ignore_errors=True)
    run(sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed",
        "--name", NAME, "--target-arch", "universal2", "--osx-bundle-identifier", BUNDLE_ID,
        "--icon", "assets/icon.icns", *DATA,
        "--collect-submodules", "batter_builder", "--collect-submodules", "awesomeui", "main.py")
    plist = APP / "Contents/Info.plist"
    data = plistlib.loads(plist.read_bytes())
    data.update(CFBundleShortVersionString=version(), CFBundleVersion=version(),
                LSMinimumSystemVersion=FLOOR, NSHighResolutionCapable=True,
                CFBundleDocumentTypes=[{
                    "CFBundleTypeName": "GoldenNugget Template",
                    "CFBundleTypeExtensions": ["batter"],
                    "CFBundleTypeRole": "Editor",
                    "LSHandlerRank": "Alternate",
                }])
    plist.write_bytes(plistlib.dumps(data))
    run("codesign", "--force", "--deep", "--sign", "-", APP)


def validate():
    result = subprocess.run([sys.executable, str(ROOT / "tools/validate_macos.py"), str(APP), FLOOR],
                            capture_output=True, text=True)
    # Keep the findings even when validation fails, for the diagnostics artifact.
    (DIST / "macOS-validation.json").write_text(result.stdout)
    (DIST / "macOS-validation.stderr.log").write_text(result.stderr)
    print(result.stdout, end="", flush=True)
    print(result.stderr, end="", file=sys.stderr, flush=True)
    result.check_returncode()
    json.loads(result.stdout)


def package():
    run("ditto", "-c", "-k", "--keepParent", APP, ZIP)
    with tempfile.TemporaryDirectory() as directory:
        staging = Path(directory) / "staging"
        staging.mkdir()
        run("ditto", APP, staging / APP.name)
        (staging / "Applications").symlink_to("/Applications")
        (staging / "README.txt").write_text(
            f"{NAME} {version()} — macOS {FLOOR} Monterey or later.\n"
            "Universal2: Intel and Apple Silicon.\n"
            f"Drag {APP.name} into Applications.\n"
            "Ad-hoc signed and not notarized: the first time, right-click the app and choose Open.\n")
        shutil.copy2(ROOT / "assets/icon.icns", staging / ".VolumeIcon.icns")
        # hdiutil create has no icon option: set the custom icon flag on a
        # writable volume, then convert it to the compressed final image.
        writable = Path(directory) / "writable.dmg"
        run("hdiutil", "create", "-ov", "-volname", f"{NAME} {version()}", "-srcfolder", staging,
            "-fs", "HFS+", "-format", "UDRW", writable)
        mounted = Path(directory) / "mounted"
        mounted.mkdir()
        run("hdiutil", "attach", "-nobrowse", "-mountpoint", mounted, writable)
        try:
            run("xcrun", "SetFile", "-a", "C", mounted)
        finally:
            run("hdiutil", "detach", mounted)
        run("hdiutil", "convert", writable, "-ov", "-format", "UDZO", "-o", DMG)
        run("hdiutil", "verify", DMG)
        run("hdiutil", "attach", "-readonly", "-nobrowse", "-mountpoint", mounted, DMG)
        try:
            app = mounted / APP.name
            if not app.is_dir() or app.is_symlink():
                raise RuntimeError("The DMG does not contain a real app bundle")
            run("codesign", "--verify", "--deep", "--strict", app)
        finally:
            run("hdiutil", "detach", mounted)
    (DIST / "SHA256SUMS-macOS.txt").write_text("".join(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n" for path in (ZIP, DMG)))


def main():
    build()
    validate()
    package()


if __name__ == "__main__":
    main()
