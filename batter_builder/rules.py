"""The checks GoldenNugget applies when it loads a template, plus the risk
notes its apply summary shows.

They mirror src/tweaks/posterboard/community_tweaks.py and
src/restore/path_mapping.py in the GoldenNugget repository; keep them in step
with those files. Unlike GoldenNugget, which stops at the first problem, every
problem is collected so the editor can list them all.
"""
import posixpath
import re
from dataclasses import dataclass

from .locations import GOLDENNUGGET_FILES
from .model import CONTROL_TYPES, VALUE_TOKEN, WRITE_TYPES, Template, Tweak, Write

MAX_TWEAKS = 64
MAX_WRITES = 32
MAX_SOURCE_BYTES = 4 * 1024 * 1024
MAX_TOTAL_SOURCE_BYTES = 16 * 1024 * 1024
MAX_TEMPLATE_BYTES = 25 * 1024 * 1024          # catalog limit
MAX_TAGS, MAX_TAG_CHARS = 8, 24
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
CATALOG_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{1,47}$")
VERSION_PATTERN = re.compile(r"^\d{1,2}(\.\d{1,2}){0,2}$")

DOMAIN_PREFIXES = (
    ("/var/Managed Preferences/", False),
    ("/var/root/", False),
    ("/var/preferences/", False),
    ("/var/MobileDevice/", False),
    ("/var/mobile/", False),
    ("/var/db/", False),
    ("/var/containers/Shared/SystemGroup/", True),
    ("/var/containers/Data/SystemGroup/", True),
)
BLOCKED_PREFIXES = (
    "/var/root/Library/Lockdown/",
    "/var/mobile/Library/Preferences/com.apple.purplebuddy.plist",
    "/var/Managed Preferences/mobile/com.apple.purplebuddy.plist",
    "/var/mobile/Library/Backup/",
)
MANAGED_PREFIX = "/var/Managed Preferences/"
SYSTEM_PREFIXES = ("/var/db/", "/var/root/", "/var/preferences/", "/var/MobileDevice/", "/var/containers/")

ERROR, WARNING, INFO = "error", "warning", "info"


@dataclass
class Issue:
    level: str
    where: str
    text: str
    tweak: int = -1       # index of the tweak, -1 for the template itself


def path_problem(path: str) -> str:
    """Why GoldenNugget would refuse to write ``path``, or ""."""
    if not isinstance(path, str) or not path.startswith("/var/"):
        return "Paths must be absolute and start with /var/."
    if posixpath.normpath(path) != path or "\0" in path or path.endswith("/"):
        return "Paths may not contain '..', '//' or a trailing slash."
    for prefix, container in DOMAIN_PREFIXES:
        if path.startswith(prefix):
            rest = path[len(prefix):]
            if container:
                rest = rest.partition("/")[2]
            if not rest:
                break
            if path.startswith(BLOCKED_PREFIXES):
                return "This file is protected and cannot be changed by a template."
            return ""
    return "GoldenNugget cannot write to this location."


def plist_value_problem(value, depth=0) -> str:
    if depth > 16:
        return "Plist values are nested too deeply."
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            return "Plist keys must be text."
        return next((p for p in (plist_value_problem(v, depth + 1) for v in value.values()) if p), "")
    if isinstance(value, list):
        return next((p for p in (plist_value_problem(v, depth + 1) for v in value) if p), "")
    if value is None or not isinstance(value, (str, int, float, bool)):
        return "Plist values cannot be null."
    return ""


def _number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _version_key(text):
    return tuple(int(part) for part in text.split("."))


def write_risk(write: Write) -> tuple:
    """(level, note) as GoldenNugget's risk check rates the write."""
    if write.path.startswith(SYSTEM_PREFIXES):
        return WARNING, "High risk: writes into a system folder."
    if write.type == "plist" and write.path.startswith(MANAGED_PREFIX):
        return INFO, "Low risk: keys in Managed Preferences."
    return WARNING, "Medium risk: the whole file is replaced and the iPhone's own copy is lost."


def check_control(tweak: Tweak, where: str, index: int, issues: list):
    control = tweak.control
    add = lambda text, level=ERROR: issues.append(Issue(level, where + " › control", text, index))
    if control is None:
        if tweak.uses_value():
            add("\"$value\" is used but the tweak has no control, so it is written literally.", WARNING)
        return
    if control.type not in CONTROL_TYPES:
        add("Controls are slider, text or choice.")
        return
    if control.type == "slider":
        if not all(_number(v) for v in (control.min, control.max, control.step, control.default)):
            add("Slider limits must be numbers.")
        elif control.min >= control.max or control.step <= 0:
            add("A slider needs min below max and a positive step.")
        elif not control.min <= control.default <= control.max:
            add("The slider default is outside min and max; GoldenNugget clamps it.", WARNING)
    elif control.type == "text":
        if isinstance(control.max_length, bool) or not isinstance(control.max_length, int) \
                or not 0 < control.max_length <= 1000:
            add("max_length must be between 1 and 1000.")
        if not isinstance(control.default, str):
            add("A text default must be text.")
        elif isinstance(control.max_length, int) and len(control.default) > control.max_length:
            add("The text default is longer than max_length; GoldenNugget cuts it.", WARNING)
    else:
        if not 0 < len(control.choices) <= 50:
            add("A choice needs between 1 and 50 choices.")
        for number, choice in enumerate(control.choices, 1):
            if not choice.label.strip() or len(choice.label) > 80:
                add(f"Choice {number} needs a label of at most 80 characters.")
            problem = plist_value_problem(choice.value)
            if problem:
                add(f"Choice {number}: {problem}")
        if isinstance(control.default, bool) or not isinstance(control.default, int) \
                or not 0 <= control.default < max(len(control.choices), 1):
            add("A choice default is the index of a choice.")
    if not tweak.uses_value():
        add("The control's value is not used: put \"$value\" into a plist value.", WARNING)


def check_write(template: Template, write: Write, where: str, index: int, issues: list):
    add = lambda text, level=ERROR: issues.append(Issue(level, where, text, index))
    if write.type not in WRITE_TYPES:
        add("Writes are plist, file or empty.")
        return
    if write.owner not in (0, 501) or isinstance(write.owner, bool):
        add("The owner is 501 (mobile) or 0 (root).")
    problem = path_problem(write.path)
    if problem:
        add(problem)
        return
    if write.type == "plist":
        if not isinstance(write.values, dict) or not write.values:
            add("A plist write needs at least one key.")
        else:
            problem = plist_value_problem(write.values)
            if problem:
                add(problem)
        if not write.path.endswith(".plist"):
            add("The path does not end in .plist.", WARNING)
    elif write.type == "file":
        source = write.source
        if not source or posixpath.normpath(source) != source or source.startswith(("/", "../")) \
                or source == "..":
            add("A file write needs a file inside the template.")
        elif source not in template.entries:
            add(f"Missing file in template: {source}")
        elif len(template.entries[source]) > MAX_SOURCE_BYTES:
            add("The file is larger than 4 MB.")
    if write.type != "plist" and write.path in GOLDENNUGGET_FILES:
        add("GoldenNugget writes this file itself; replacing it is refused while its own tweaks use it.",
            WARNING)
    level, note = write_risk(write)
    add(note, level)


def check_tweak(template: Template, tweak: Tweak, index: int, seen: set, issues: list):
    where = f"Tweak {index + 1}" + (f" ({tweak.label})" if tweak.label else "")
    add = lambda text, level=ERROR: issues.append(Issue(level, where, text, index))
    if not ID_PATTERN.match(tweak.id):
        add("The id uses letters, digits, '.', '_' or '-' (up to 64, starting with a letter or digit).")
    elif tweak.id in seen:
        add(f"The id \"{tweak.id}\" is used twice.")
    seen.add(tweak.id)
    if not tweak.label.strip() or len(tweak.label) > 80:
        add("Every tweak needs a label of at most 80 characters.")
    if len(tweak.description) > 500:
        add("The description is longer than 500 characters.")
    for key in ("min_version", "max_version"):
        value = getattr(tweak, key)
        if value and not VERSION_PATTERN.match(value):
            add("iOS versions look like 18 or 18.4.")
    if all(VERSION_PATTERN.match(v) for v in (tweak.min_version, tweak.max_version)) \
            and _version_key(tweak.min_version) > _version_key(tweak.max_version):
        add("The minimum iOS version is above the maximum.", WARNING)
    if not tweak.writes:
        add("A tweak needs at least one write for when it is on.")
    if len(tweak.writes) + len(tweak.writes_off) > MAX_WRITES:
        add("A tweak has at most 32 writes.")
    check_control(tweak, where, index, issues)
    for label, writes in (("on", tweak.writes), ("off", tweak.writes_off)):
        kinds = {}
        for number, write in enumerate(writes, 1):
            check_write(template, write, f"{where} › {label} › write {number}", index, issues)
            kinds.setdefault(write.path, set()).add("plist" if write.type == "plist" else "file")
        for path, found in kinds.items():
            if len(found) > 1:
                add(f"{path} is written both as plist keys and as a whole file.")


def validate(template: Template) -> list:
    """Every problem GoldenNugget would report, plus warnings and risk notes."""
    issues = []
    add = lambda text, level=ERROR: issues.append(Issue(level, "Template", text))
    if not template.title.strip():
        add("The template needs a title.")
    if not template.author.strip():
        add("The template needs an author.")
    for key in ("min_version", "max_version"):
        value = getattr(template, key)
        if value and not VERSION_PATTERN.match(value):
            add("iOS versions look like 18 or 18.4.")
    if len(template.tags) > MAX_TAGS or any(not t.strip() or len(t) > MAX_TAG_CHARS for t in template.tags):
        add("Up to 8 tags of at most 24 characters.")
    if not template.tweaks and "options" not in template.extra:
        add("Add at least one tweak.")
    if len(template.tweaks) > MAX_TWEAKS:
        add("A template has at most 64 tweaks.")
    has_container = any(part.lower() == "container"
                        for name in template.entries for part in name.split("/")[:-1])
    if has_container and not template.extra.get("domain"):
        add("The template has a Container folder but no domain.")
    total = sum(len(template.entries[s]) for s in template.referenced_sources() if s in template.entries)
    if total > MAX_TOTAL_SOURCE_BYTES:
        add("Files used by tweaks add up to more than 16 MB.")
    for name in template.unused_sources():
        add(f"{name} is not used by any tweak and will still be saved.", WARNING)
    seen = set()
    for index, tweak in enumerate(template.tweaks):
        check_tweak(template, tweak, index, seen, issues)
    return issues


def errors(issues) -> list:
    return [issue for issue in issues if issue.level == ERROR]
