"""The interface language: English, or a translation chosen at start.

Interface text goes through ``_`` (and ``n_`` when it counts something); a
translation is a dict from the English text to its own (translations_ru.py).
Text without a translation stays English. The language is picked once, before
the window is built, so changing it takes a restart.
"""
from PySide6.QtCore import QLocale

LANGUAGES = (("system", "Same as System"), ("en", "English"), ("ru", "Русский"))
_table = {}
_language = "en"


def setup(choice: str = "system") -> str:
    """Use the language ``choice`` (a LANGUAGES key); returns the one used."""
    global _table, _language
    if choice not in ("en", "ru"):
        choice = "ru" if QLocale.system().language() == QLocale.Russian else "en"
    _language = choice
    if choice == "ru":
        from .translations_ru import RU
        _table = RU
    else:
        _table = {}
    return choice


def language() -> str:
    return _language


def _(text: str) -> str:
    found = _table.get(text, text)
    return found if isinstance(found, str) else text


def n_(count: int, singular: str, plural: str) -> str:
    """``singular`` or ``plural`` for ``count``, with {n} filled in. A
    translation of ``singular`` may be a tuple of forms: Russian has three
    (1, 2–4, 5+)."""
    forms = _table.get(singular)
    if isinstance(forms, tuple):
        if len(forms) == 3:
            tens, ones = count % 100, count % 10
            text = forms[0] if ones == 1 and tens != 11 else \
                forms[1] if 2 <= ones <= 4 and not 12 <= tens <= 14 else forms[2]
        else:
            text = forms[0] if count == 1 else forms[-1]
    else:
        text = singular if count == 1 else plural
    return text.format(n=count)
