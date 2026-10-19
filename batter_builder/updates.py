"""Whether a newer release than this one is out (the GitHub API's latest
release)."""
import json
import re

from . import __version__
from .i18n import _


def parse_version(text: str) -> tuple:
    """(1, 2, 0) for "v1.2.0"; () when ``text`` is not a version."""
    match = re.fullmatch(r"v?(\d+(?:\.\d+)*)", (text or "").strip())
    return tuple(int(part) for part in match.group(1).split(".")) if match else ()


def newer_release(data: bytes, current: str = __version__):
    """(version, page url) of the latest release when it is newer than
    ``current``, else None. Raises ValueError for an unexpected answer."""
    try:
        release = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(_("GitHub's answer is not JSON: {error}").format(error=error)) from None
    if not isinstance(release, dict) or not parse_version(release.get("tag_name", "")):
        raise ValueError(_("GitHub's answer has no release version."))
    latest = parse_version(release["tag_name"])
    pad = lambda v: v + (0,) * (max(len(latest), len(parse_version(current))) - len(v))
    if pad(latest) <= pad(parse_version(current)):
        return None
    return ".".join(map(str, latest)), release.get("html_url") or ""
