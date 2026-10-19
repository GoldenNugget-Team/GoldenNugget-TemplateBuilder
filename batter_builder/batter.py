"""Reading and writing .batter files: a ZIP with config.json and the files
the template uses.

Opening keeps every other file of the archive (containers, previews,
resources) so an existing template can get tweaks without losing anything.
Files are stored relative to the folder that holds config.json; a saved
template always has config.json at the root.
"""
import io
import json
import os
import stat
import tempfile
import zipfile

from .model import Template

MAX_ARCHIVE_ENTRIES = 20000
MAX_ARCHIVE_BYTES = 512 * 1024 * 1024


class BatterError(ValueError):
    pass


def _find_config(names) -> str:
    # GoldenNugget takes the first config.json that is not inside a
    # descriptor or container folder.
    for name in names:
        lower = name.lower()
        if "config.json" in lower and "descriptor" not in lower and "container" not in lower:
            return name
    return ""


def load(path: str) -> Template:
    try:
        with zipfile.ZipFile(path) as archive:
            infos = [info for info in archive.infolist() if not info.is_dir()]
            if len(infos) > MAX_ARCHIVE_ENTRIES or sum(i.file_size for i in infos) > MAX_ARCHIVE_BYTES:
                raise BatterError("The template is too large to open.")
            config_name = _find_config(info.filename for info in infos)
            if not config_name:
                raise BatterError("The file has no config.json.")
            base = config_name[:-len("config.json")]
            try:
                config = json.loads(archive.read(config_name).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise BatterError(f"config.json is not valid JSON: {error}") from None
            entries = {}
            for info in infos:
                name = info.filename
                if name == config_name:
                    continue
                if not name.startswith(base):
                    # Saving puts config.json at the root; such a file would
                    # be lost, so the template is not opened at all.
                    raise BatterError(f"{name} is outside the folder that holds config.json.")
                relative = name[len(base):]
                if relative.startswith("/") or ".." in relative.split("/"):
                    raise BatterError(f"Unsafe file name in the template: {name}")
                entries[relative] = archive.read(info)
    except (zipfile.BadZipFile, OSError) as error:
        raise BatterError(f"This is not a .batter file: {error}") from None
    return Template.from_config(config, entries)


def dumps_config(template: Template) -> str:
    return json.dumps(template.to_config(), indent=2, ensure_ascii=False) + "\n"


def dumps(template: Template) -> bytes:
    """The .batter file as bytes, so its size is known before anything is
    written."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("config.json", dumps_config(template))
        for name in sorted(template.entries):
            archive.writestr(name, template.entries[name])
    return buffer.getvalue()


def _file_mode(path: str) -> int:
    # mkstemp creates the file readable by its owner only; a saved template
    # gets the mode of the file it replaces, or the usual one for new files.
    try:
        return stat.S_IMODE(os.stat(path).st_mode)
    except OSError:
        umask = os.umask(0)
        os.umask(umask)
        return 0o666 & ~umask


def save(template: Template, path: str, data: bytes = None):
    """Write the template atomically: an interrupted save never replaces the
    previous file. ``data`` is what ``dumps`` returned, if it was already
    called."""
    data = dumps(template) if data is None else data
    folder = os.path.dirname(os.path.abspath(path))
    handle, temporary = tempfile.mkstemp(prefix=".batter-", suffix=".tmp", dir=folder)
    try:
        with os.fdopen(handle, "wb") as output:
            output.write(data)
        os.chmod(temporary, _file_mode(path))
        os.replace(temporary, path)
    except BaseException:
        if os.path.exists(temporary):
            os.remove(temporary)
        raise
