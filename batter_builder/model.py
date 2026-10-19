"""Template data: what the editor changes and what config.json holds.

The config.json format is GoldenNugget's (documentation.md, "Community Tweaks
(format 3)"). Loading is lenient so a broken template can still be opened and
fixed; ``rules.validate`` reports what GoldenNugget would refuse.
"""
from dataclasses import dataclass, field
from typing import Any, Optional

FORMAT_VERSION = "3"
VALUE_TOKEN = "$value"
WRITE_TYPES = ("plist", "file", "empty")
CONTROL_TYPES = ("slider", "text", "choice")

# config.json keys the editor owns; every other key (options, domain,
# resources, previews, ...) is kept as it was.
OWN_KEYS = ("title", "author", "description", "format_version", "min_version",
            "max_version", "tags", "tweaks")


@dataclass
class Choice:
    label: str = ""
    value: Any = ""


@dataclass
class Control:
    type: str = "slider"
    default: Any = 0          # slider: number, text: string, choice: index
    min: float = 0
    max: float = 1
    step: float = 1
    max_length: int = 200
    choices: list = field(default_factory=list)

    def to_config(self) -> dict:
        if self.type == "slider":
            return {"type": "slider", "min": self.min, "max": self.max,
                    "step": self.step, "default": self.default}
        if self.type == "text":
            return {"type": "text", "default": self.default, "max_length": self.max_length}
        return {"type": "choice", "default": self.default,
                "choices": [{"label": c.label, "value": c.value} for c in self.choices]}

    @classmethod
    def from_config(cls, raw) -> Optional["Control"]:
        if not isinstance(raw, dict):
            return None
        kind = raw.get("type") if raw.get("type") in CONTROL_TYPES else "slider"
        control = cls(type=kind)
        if kind == "slider":
            control.min = raw.get("min", 0)
            control.max = raw.get("max", 1)
            control.step = raw.get("step", 1)
            control.default = raw.get("default", control.min)
        elif kind == "text":
            control.default = raw.get("default", "")
            control.max_length = raw.get("max_length", 200)
        else:
            control.default = raw.get("default", 0)
            choices = raw.get("choices")
            control.choices = [Choice(c.get("label") if isinstance(c.get("label"), str) else "",
                                      c.get("value", ""))
                               for c in (choices if isinstance(choices, list) else [])
                               if isinstance(c, dict)]
        return control


@dataclass
class Write:
    type: str = "plist"
    path: str = ""
    values: dict = field(default_factory=dict)
    source: str = ""
    owner: int = 501

    def to_config(self) -> dict:
        data = {"type": self.type, "path": self.path}
        if self.type == "plist":
            data["values"] = self.values
        elif self.type == "file":
            data["source"] = self.source
        if self.owner != 501:
            data["owner"] = self.owner
        return data

    @classmethod
    def from_config(cls, raw) -> "Write":
        raw = raw if isinstance(raw, dict) else {}
        values = raw.get("values")
        return cls(type=raw.get("type") if raw.get("type") in WRITE_TYPES else "plist",
                   path=raw.get("path") if isinstance(raw.get("path"), str) else "",
                   values=values if isinstance(values, dict) else {},
                   source=raw.get("source") if isinstance(raw.get("source"), str) else "",
                   owner=raw.get("owner", 501))


@dataclass
class Tweak:
    id: str = ""
    label: str = ""
    description: str = ""
    default: bool = False
    min_version: str = ""
    max_version: str = ""
    control: Optional[Control] = None
    writes: list = field(default_factory=list)
    writes_off: list = field(default_factory=list)

    def to_config(self) -> dict:
        data = {"id": self.id, "label": self.label}
        if self.description:
            data["description"] = self.description
        data["default"] = self.default
        for key in ("min_version", "max_version"):
            if getattr(self, key):
                data[key] = getattr(self, key)
        if self.control is not None:
            data["control"] = self.control.to_config()
        data["writes"] = [write.to_config() for write in self.writes]
        if self.writes_off:
            data["writes_off"] = [write.to_config() for write in self.writes_off]
        return data

    @classmethod
    def from_config(cls, raw) -> "Tweak":
        raw = raw if isinstance(raw, dict) else {}

        def text(key):
            return raw.get(key) if isinstance(raw.get(key), str) else ""

        def writes(key):
            items = raw.get(key)
            return [Write.from_config(item) for item in items] if isinstance(items, list) else []
        return cls(id=text("id"), label=text("label"), description=text("description"),
                   default=raw.get("default") is True, min_version=text("min_version"),
                   max_version=text("max_version"), control=Control.from_config(raw.get("control")),
                   writes=writes("writes"), writes_off=writes("writes_off"))

    def uses_value(self) -> bool:
        return any(_contains_token(write.values) for write in self.writes + self.writes_off)


@dataclass
class Template:
    title: str = ""
    author: str = ""
    description: str = ""
    min_version: str = ""
    max_version: str = ""
    tags: list = field(default_factory=list)
    tweaks: list = field(default_factory=list)
    extra: dict = field(default_factory=dict)     # config keys the editor does not own
    entries: dict = field(default_factory=dict)   # archive files next to config.json, name -> bytes

    def to_config(self) -> dict:
        data = {"title": self.title, "author": self.author, "format_version": FORMAT_VERSION}
        if self.description:
            data["description"] = self.description
        for key in ("min_version", "max_version"):
            if getattr(self, key):
                data[key] = getattr(self, key)
        if self.tags:
            data["tags"] = self.tags
        data.update(self.extra)
        data["tweaks"] = [tweak.to_config() for tweak in self.tweaks]
        return data

    @classmethod
    def from_config(cls, raw, entries=None) -> "Template":
        raw = raw if isinstance(raw, dict) else {}

        def text(key):
            return raw.get(key) if isinstance(raw.get(key), str) else ""
        tags = raw.get("tags")
        tweaks = raw.get("tweaks")
        return cls(title=text("title"), author=text("author"), description=text("description"),
                   min_version=text("min_version"), max_version=text("max_version"),
                   tags=[t for t in tags if isinstance(t, str)] if isinstance(tags, list) else [],
                   tweaks=[Tweak.from_config(t) for t in tweaks] if isinstance(tweaks, list) else [],
                   extra={k: v for k, v in raw.items() if k not in OWN_KEYS},
                   entries=dict(entries or {}))

    def referenced_sources(self) -> set:
        return {write.source for tweak in self.tweaks for write in tweak.writes + tweak.writes_off
                if write.type == "file" and write.source}

    def add_source(self, name: str, data: bytes) -> str:
        """Store a file for a ``file`` write under files/ and return its name.
        Identical contents reuse the existing entry."""
        base = "files/" + (name.replace("\\", "/").rsplit("/", 1)[-1] or "file")
        for existing, content in self.entries.items():
            if existing.startswith("files/") and content == data:
                return existing
        stem, dot, ext = base.rpartition(".") if "." in base[len("files/"):] else (base, "", "")
        candidate, number = base, 1
        while candidate in self.entries:
            number += 1
            candidate = f"{stem}-{number}{dot}{ext}"
        self.entries[candidate] = data
        return candidate

    def unused_sources(self) -> list:
        used = self.referenced_sources()
        return sorted(name for name in self.entries if name.startswith("files/") and name not in used)


def _contains_token(value) -> bool:
    if isinstance(value, dict):
        return any(_contains_token(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_token(item) for item in value)
    return value == VALUE_TOKEN
