"""The plist keys GoldenNugget's own tweaks write, suggested in the key table.

The data comes from GoldenNugget's tweak registry (known_keys_data.py, made by
tools/make_known_keys.py): per file, each key's type, the value GoldenNugget
writes, and a title and description, in English and Russian.
"""
from . import i18n
from .known_keys_data import PATHS


def for_path(path: str) -> dict:
    """key -> entry for the plist at ``path``; empty for unknown files."""
    return PATHS.get(path, {})


def text(entry: dict, field: str) -> str:
    """``field`` ("title" or "description") in the interface language."""
    if i18n.language() == "ru" and entry.get(field + "_ru"):
        return entry[field + "_ru"]
    return entry.get(field, "")


def summary(key: str, entry: dict) -> str:
    title, description = text(entry, "title"), text(entry, "description")
    versions = ""
    if entry.get("min_version") or entry.get("max_version"):
        versions = " (iOS " + (entry.get("min_version") or "") + "–" + (entry.get("max_version") or "") + ")"
    return f"{key}: {title}{versions}" + (f". {description}" if description else "")
