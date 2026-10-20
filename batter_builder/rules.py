"""The checks GoldenNugget applies when it loads a template, plus the risk
notes its apply summary shows.

They mirror src/tweaks/posterboard/community_tweaks.py and
src/restore/path_mapping.py in the GoldenNugget repository; keep them in step
with those files. Unlike GoldenNugget, which stops at the first problem, every
problem is collected so the editor can list them all.
"""
import fnmatch
import posixpath
import re
from dataclasses import dataclass

from .i18n import _
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
    tweak: int = -1       # index of the tweak, TEMPLATE or OPTIONS


TEMPLATE, OPTIONS = -1, -2
OPTION_TYPES = ("replace", "set", "remove", "picker", "bundle_id")
SETTER_TYPES = ("textbox", "slider", "toggle", "color_picker")
VALUE_TYPES = ("integer", "float", "string")
DOMAIN_PREFIXES_TEMPLATE = ("AppDomain-", "Sparserestore-")


def safe_member(name) -> bool:
    """A path inside the template GoldenNugget accepts (archive_safety.py)."""
    if not isinstance(name, str) or not name:
        return False
    parts = name.rstrip("/").split("/")
    return (not name.startswith("/") and "\\" not in name and "\0" not in name and ":" not in name
            and all(part not in ("", ".", "..") for part in parts))


def _matches(template: Template, pattern: str) -> bool:
    """Whether ``pattern`` (wildcards allowed) names a file or folder of the
    template, as GoldenNugget resolves option files."""
    return any(fnmatch.fnmatchcase(name, pattern) or name.startswith(pattern.rstrip("/") + "/")
               for name in template.entries)


def check_options(template: Template, issues: list):
    """The wallpaper options (format 2): what GoldenNugget refuses when it
    loads them, and options that would do nothing."""
    extra = template.extra
    options = extra.get("options")
    add_template = lambda text, level=ERROR: issues.append(Issue(level, _("Template"), text, OPTIONS))
    if options is None:
        return
    if not isinstance(options, list):
        add_template(_("\"options\" must be a list."))
        return
    domain = extra.get("domain", "")
    if options and not domain:
        add_template(_("A template with wallpaper options needs a domain, or its options are never applied."))
    elif domain and not str(domain).startswith(DOMAIN_PREFIXES_TEMPLATE) and domain != "com.apple.PosterBoard":
        add_template(_("Domains start with AppDomain- or Sparserestore-."), WARNING)
    resources = [r for r in extra.get("resources", []) if isinstance(r, str)] \
        if isinstance(extra.get("resources", []), list) else []
    previews = extra.get("previews", [])
    previews = [p for p in previews if isinstance(p, str)] if isinstance(previews, list) else []
    for preview in previews:
        if not any(fnmatch.fnmatchcase(preview, pattern) for pattern in resources):
            add_template(_("The preview {name} is not listed in resources, so GoldenNugget does not show it.")
                         .format(name=preview), WARNING)
    for pattern in resources:
        if not safe_member(pattern):
            add_template(_("Unsafe resource path: {name}").format(name=pattern))
        elif not _matches(template, pattern):
            add_template(_("The resource {name} matches no file in the template.").format(name=pattern), WARNING)
    if extra.get("preview_layout", "horizontal") not in ("horizontal", "stacked"):
        add_template(_("The preview layout is horizontal or stacked."), WARNING)
    for number, option in enumerate(options, 1):
        check_option(template, option, number, domain, previews, issues)


def _check_files(template, files, add, required=True):
    if not isinstance(files, list) or (required and files is None):
        add(_("\"files\" must be a list of paths inside the template."))
        return
    for name in files:
        if not safe_member(name):
            add(_("Unsafe path: {name}").format(name=name))
        elif not _matches(template, name):
            add(_("{name} matches no file in the template.").format(name=name), WARNING)


def check_option(template, option, number, domain, previews, issues):
    label = option.get("label") if isinstance(option, dict) else None
    where = _("Option {n}").format(n=number) + (f" ({label})" if isinstance(label, str) and label else "")
    add = lambda text, level=ERROR: issues.append(Issue(level, where, text, OPTIONS))
    if not isinstance(option, dict):
        add(_("Every option is an object with a type and a label."))
        return
    kind = option.get("type")
    if kind not in OPTION_TYPES:
        add(_("Option types are replace, set, remove, picker or bundle_id."))
        return
    if not isinstance(label, str) or not label.strip():
        add(_("Every option needs a label."))
    if kind == "bundle_id":
        if domain and not str(domain).startswith("AppDomain-"):
            add(_("A bundle id option only works with an AppDomain- domain."), WARNING)
        return
    preview = option.get("associated_preview")
    if preview is not None and preview not in previews:
        add(_("The associated preview {name} is not one of the template's previews.").format(name=preview), WARNING)
    if kind != "picker":
        if "files" not in option:
            add(_("The option needs \"files\": the files it changes."))
        else:
            _check_files(template, option["files"], add)
            if isinstance(option["files"], list) and not option["files"]:
                add(_("The option lists no files, so it changes nothing."), WARNING)
    if kind == "replace":
        if not isinstance(option.get("allowed_files"), str) or not option.get("allowed_files"):
            add(_("A replace option needs allowed files, for example Images (*.png *.jpg)."))
    elif kind == "set":
        for key in ("identifier", "key"):
            if not isinstance(option.get(key), str) or not option.get(key):
                add(_("A set option needs an identifier and a key."))
                break
        if option.get("setter_type") not in SETTER_TYPES:
            add(_("The setter is textbox, slider, toggle or color_picker."))
        elif option["setter_type"] == "slider":
            if not all(_number(option.get(key)) for key in ("min_value", "max_value")):
                add(_("A slider needs a minimum and a maximum."))
            elif option["min_value"] >= option["max_value"]:
                add(_("The slider's minimum is not below its maximum."), WARNING)
        if "value_type" in option and option["value_type"] not in VALUE_TYPES:
            add(_("The value type is integer, float or string."), WARNING)
    elif kind == "picker":
        choices = option.get("options")
        if not isinstance(choices, list) or not choices:
            add(_("A picker needs at least one choice."))
            return
        for index, choice in enumerate(choices, 1):
            if not isinstance(choice, dict) or not isinstance(choice.get("label"), str) or "files" not in choice:
                add(_("Choice {n} needs a label and files.").format(n=index))
                continue
            _check_files(template, choice["files"], add)
            choice_preview = choice.get("associated_preview")
            if choice_preview is not None and choice_preview not in previews:
                add(_("The associated preview {name} is not one of the template's previews.")
                    .format(name=choice_preview), WARNING)
        if option.get("rename") and not option.get("allow_multiple_selection"):
            names = option.get("names")
            if not isinstance(names, list) or not all(safe_member(name) for name in names):
                add(_("A renaming picker needs \"names\": safe paths inside the template."))
            elif any(isinstance(c, dict) and isinstance(c.get("files"), list) and len(c["files"]) > len(names)
                     for c in choices):
                add(_("A renaming picker needs a name for each file of a choice."))
        default = option.get("default_value")
        if default is not None and (not isinstance(default, int) or isinstance(default, bool)
                                    or not 0 <= default < len(choices)):
            add(_("The default choice is the number of a choice, counting from 0."), WARNING)


def path_problem(path: str) -> str:
    """Why GoldenNugget would refuse to write ``path``, or ""."""
    if not isinstance(path, str) or not path.startswith("/var/"):
        return _("Paths must be absolute and start with /var/.")
    if posixpath.normpath(path) != path or "\0" in path or path.endswith("/"):
        return _("Paths may not contain '..', '//' or a trailing slash.")
    for prefix, container in DOMAIN_PREFIXES:
        if path.startswith(prefix):
            rest = path[len(prefix):]
            if container:
                rest = rest.partition("/")[2]
            if not rest:
                break
            if path.startswith(BLOCKED_PREFIXES):
                return _("This file is protected and cannot be changed by a template.")
            return ""
    return _("GoldenNugget cannot write to this location.")


def plist_value_problem(value, depth=0) -> str:
    if depth > 16:
        return _("Plist values are nested too deeply.")
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            return _("Plist keys must be text.")
        return next((p for p in (plist_value_problem(v, depth + 1) for v in value.values()) if p), "")
    if isinstance(value, list):
        return next((p for p in (plist_value_problem(v, depth + 1) for v in value) if p), "")
    if value is None or not isinstance(value, (str, int, float, bool)):
        return _("Plist values cannot be null.")
    return ""


def _number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _version_key(text):
    return tuple(int(part) for part in text.split("."))


def write_risk(write: Write) -> tuple:
    """(level, note) as GoldenNugget's risk check rates the write."""
    if write.path.startswith(SYSTEM_PREFIXES):
        return WARNING, _("High risk: writes into a system folder.")
    if write.type == "plist" and write.path.startswith(MANAGED_PREFIX):
        return INFO, _("Low risk: keys in Managed Preferences.")
    return WARNING, _("Medium risk: the whole file is replaced and the iPhone's own copy is lost.")


def check_control(tweak: Tweak, where: str, index: int, issues: list):
    control = tweak.control
    add = lambda text, level=ERROR: issues.append(Issue(level, where + " › " + _("control"), text, index))
    if control is None:
        if tweak.uses_value():
            add(_("\"$value\" is used but the tweak has no control, so it is written literally."), WARNING)
        return
    if control.type not in CONTROL_TYPES:
        add(_("Controls are slider, text or choice."))
        return
    if control.type == "slider":
        if not all(_number(v) for v in (control.min, control.max, control.step, control.default)):
            add(_("Slider limits must be numbers."))
        elif control.min >= control.max or control.step <= 0:
            add(_("A slider needs min below max and a positive step."))
        elif not control.min <= control.default <= control.max:
            add(_("The slider default is outside min and max; GoldenNugget clamps it."), WARNING)
    elif control.type == "text":
        if isinstance(control.max_length, bool) or not isinstance(control.max_length, int) \
                or not 0 < control.max_length <= 1000:
            add(_("max_length must be between 1 and 1000."))
        if not isinstance(control.default, str):
            add(_("A text default must be text."))
        elif isinstance(control.max_length, int) and len(control.default) > control.max_length:
            add(_("The text default is longer than max_length; GoldenNugget cuts it."), WARNING)
    else:
        if not 0 < len(control.choices) <= 50:
            add(_("A choice needs between 1 and 50 choices."))
        for number, choice in enumerate(control.choices, 1):
            if not choice.label.strip() or len(choice.label) > 80:
                add(_("Choice {n} needs a label of at most 80 characters.").format(n=number))
            problem = plist_value_problem(choice.value)
            if problem:
                add(_("Choice {n}: {problem}").format(n=number, problem=problem))
        if isinstance(control.default, bool) or not isinstance(control.default, int) \
                or not 0 <= control.default < max(len(control.choices), 1):
            add(_("A choice default is the index of a choice."))
    if not tweak.uses_value():
        add(_("The control's value is not used: put \"$value\" into a plist value."), WARNING)


def check_write(template: Template, write: Write, where: str, index: int, issues: list):
    add = lambda text, level=ERROR: issues.append(Issue(level, where, text, index))
    if write.type not in WRITE_TYPES:
        add(_("Writes are plist, file or empty."))
        return
    if write.owner not in (0, 501) or isinstance(write.owner, bool):
        add(_("The owner is 501 (mobile) or 0 (root)."))
    problem = path_problem(write.path)
    if problem:
        add(problem)
        return
    if write.type == "plist":
        if not isinstance(write.values, dict) or not write.values:
            add(_("A plist write needs at least one key."))
        else:
            problem = plist_value_problem(write.values)
            if problem:
                add(problem)
        if not write.path.endswith(".plist"):
            add(_("The path does not end in .plist."), WARNING)
    elif write.type == "file":
        source = write.source
        if not source or posixpath.normpath(source) != source or source.startswith(("/", "../")) \
                or source == "..":
            add(_("A file write needs a file inside the template."))
        elif source not in template.entries:
            add(_("Missing file in template: {name}").format(name=source))
        elif len(template.entries[source]) > MAX_SOURCE_BYTES:
            add(_("The file is larger than 4 MB."))
    if write.type != "plist" and write.path in GOLDENNUGGET_FILES:
        add(_("GoldenNugget writes this file itself; replacing it is refused while its own tweaks use it."),
            WARNING)
    level, note = write_risk(write)
    add(note, level)


def check_tweak(template: Template, tweak: Tweak, index: int, seen: set, issues: list):
    where = _("Tweak {n}").format(n=index + 1) + (f" ({tweak.label})" if tweak.label else "")
    add = lambda text, level=ERROR: issues.append(Issue(level, where, text, index))
    if not ID_PATTERN.match(tweak.id):
        add(_("The id uses letters, digits, '.', '_' or '-' (up to 64, starting with a letter or digit)."))
    elif tweak.id in seen:
        add(_("The id \"{id}\" is used twice.").format(id=tweak.id))
    seen.add(tweak.id)
    if not tweak.label.strip() or len(tweak.label) > 80:
        add(_("Every tweak needs a label of at most 80 characters."))
    if len(tweak.description) > 500:
        add(_("The description is longer than 500 characters."))
    for key in ("min_version", "max_version"):
        value = getattr(tweak, key)
        if value and not VERSION_PATTERN.match(value):
            add(_("iOS versions look like 18 or 18.4."))
    if all(VERSION_PATTERN.match(v) for v in (tweak.min_version, tweak.max_version)) \
            and _version_key(tweak.min_version) > _version_key(tweak.max_version):
        add(_("The minimum iOS version is above the maximum."), WARNING)
    if not tweak.writes:
        add(_("A tweak needs at least one write for when it is on."))
    if len(tweak.writes) + len(tweak.writes_off) > MAX_WRITES:
        add(_("A tweak has at most 32 writes."))
    check_control(tweak, where, index, issues)
    for label, writes in ((_("on"), tweak.writes), (_("off"), tweak.writes_off)):
        kinds = {}
        for number, write in enumerate(writes, 1):
            check_write(template, write, f"{where} › {label} › " + _("write {n}").format(n=number), index, issues)
            kinds.setdefault(write.path, set()).add("plist" if write.type == "plist" else "file")
        for path, found in kinds.items():
            if len(found) > 1:
                add(_("{path} is written both as plist keys and as a whole file.").format(path=path))


def validate(template: Template) -> list:
    """Every problem GoldenNugget would report, plus warnings and risk notes."""
    issues = []
    add = lambda text, level=ERROR: issues.append(Issue(level, _("Template"), text))
    if not template.title.strip():
        add(_("The template needs a title."))
    if not template.author.strip():
        add(_("The template needs an author."))
    for key in ("min_version", "max_version"):
        value = getattr(template, key)
        if value and not VERSION_PATTERN.match(value):
            add(_("iOS versions look like 18 or 18.4."))
    if len(template.tags) > MAX_TAGS or any(not t.strip() or len(t) > MAX_TAG_CHARS for t in template.tags):
        add(_("Up to 8 tags of at most 24 characters."))
    if not template.tweaks and not template.extra.get("options"):
        add(_("Add at least one tweak or wallpaper option."))
    if len(template.tweaks) > MAX_TWEAKS:
        add(_("A template has at most 64 tweaks."))
    has_container = any(part.lower() == "container"
                        for name in template.entries for part in name.split("/")[:-1])
    if has_container and not template.extra.get("domain"):
        add(_("The template has a Container folder but no domain."))
    total = sum(len(template.entries[s]) for s in template.referenced_sources() if s in template.entries)
    if total > MAX_TOTAL_SOURCE_BYTES:
        add(_("Files used by tweaks add up to more than 16 MB."))
    for name in template.unused_sources():
        add(_("{name} is not used by any tweak and will still be saved.").format(name=name), WARNING)
    check_options(template, issues)
    seen = set()
    for index, tweak in enumerate(template.tweaks):
        check_tweak(template, tweak, index, seen, issues)
    return issues


def errors(issues) -> list:
    return [issue for issue in issues if issue.level == ERROR]
