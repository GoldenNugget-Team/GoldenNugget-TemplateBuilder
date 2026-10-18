"""Validate a Universal2 app bundle: every Mach-O file has both slices, every
library it loads is inside the bundle with the same architecture, and nothing
needs a newer macOS than the floor. Adapted from GoldenNugget's
tools/validate_macos.py.

    python tools/validate_macos.py "dist/Batter Builder.app" 12.0
"""
from functools import lru_cache
from pathlib import Path
import json
import subprocess
import sys

from macholib.MachO import MachO
from macholib.mach_o import LC_BUILD_VERSION, LC_LOAD_WEAK_DYLIB, LC_RPATH, LC_VERSION_MIN_MACOSX

app = Path(sys.argv[1]).resolve()
major, minor = (int(part) for part in (sys.argv[2] if len(sys.argv) > 2 else "12.0").split("."))
floor = major << 16 | minor << 8
frameworks = app / "Contents/Frameworks"
executable = app / "Contents/MacOS"
MAGIC = {b"\xfe\xed\xfa\xce", b"\xce\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xcf\xfa\xed\xfe",
         b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca", b"\xca\xfe\xba\xbf", b"\xbf\xba\xfe\xca"}
CPU = {16777223: "x86_64", 16777228: "arm64"}


@lru_cache(None)
def archs(path):
    return set(subprocess.check_output(["lipo", "-archs", str(path)], text=True).split())


files = []
for path in app.rglob("*"):
    if path.is_file() and not path.is_symlink():
        with path.open("rb") as handle:
            if handle.read(4) in MAGIC:
                files.append(path)

errors, maximum = [], {}
for path in files:
    relative = str(path.relative_to(app))
    if not {"x86_64", "arm64"} <= archs(path):
        errors.append(("thin binary", relative, sorted(archs(path))))
    for header in MachO(str(path)).headers:
        arch = CPU.get(header.header.cputype)
        if not arch:
            errors.append(("unexpected architecture", relative, header.header.cputype))
            continue
        rpaths = [frameworks, executable]
        for cmd, obj, data in header.commands:
            version = obj.minos if cmd.cmd == LC_BUILD_VERSION else \
                obj.version if cmd.cmd == LC_VERSION_MIN_MACOSX else 0
            maximum[arch] = max(maximum.get(arch, 0), version)
            if version > floor:
                errors.append(("needs a newer macOS than the floor", relative, arch,
                               f"{version >> 16}.{version >> 8 & 255}"))
            if cmd.cmd == LC_RPATH:
                raw = data.rstrip(b"\x00").decode()
                raw = raw.replace("@loader_path", str(path.parent)).replace("@executable_path", str(executable))
                if not raw.startswith("@"):
                    rpaths.append(Path(raw))
        for index, _name, lib in header.walkRelocatables():
            if header.commands[index][0].cmd == LC_LOAD_WEAK_DYLIB or \
                    lib.startswith(("/usr/lib/", "/System/Library/")):
                continue
            if lib.startswith("@loader_path/"):
                candidates = [path.parent / lib[len("@loader_path/"):]]
            elif lib.startswith("@executable_path/"):
                candidates = [executable / lib[len("@executable_path/"):]]
            elif lib.startswith("@rpath/"):
                candidates = [rpath / lib[len("@rpath/"):] for rpath in rpaths]
            else:
                candidates = [Path(lib)]
            found = next((c.resolve() for c in candidates if c.exists()), None)
            if found is None:
                errors.append((arch, relative, lib, "missing"))
            elif not found.is_relative_to(app):
                errors.append((arch, relative, lib, "outside the bundle"))
            elif arch not in archs(found):
                errors.append((arch, relative, lib, "wrong architecture"))

print(json.dumps({
    "mach_o_files": len(files),
    "floor": f"{major}.{minor}",
    "maximum_deployment_target": {a: f"{v >> 16}.{v >> 8 & 255}.{v & 255}" for a, v in maximum.items()},
    "errors": errors,
}, indent=2))
if errors:
    raise SystemExit(1)
subprocess.run(["codesign", "--verify", "--deep", "--strict", str(app)], check=True)
