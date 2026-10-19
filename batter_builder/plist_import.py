"""Reading keys from an existing .plist file for a plist write.

config.json holds JSON, so only values JSON can hold are taken: text,
whole and real numbers, booleans, arrays and dictionaries of them. Data and
dates are left out, and so are whole numbers outside the 32-bit range the
editor's number cells take.
"""
import plistlib

from .i18n import _

INT_LIMIT = 2 ** 31 - 1


class PlistError(ValueError):
    pass


def convert(value):
    """``value`` as config.json can hold it; raises ValueError otherwise."""
    if isinstance(value, bool) or isinstance(value, (str, float)):
        return value
    if isinstance(value, int):
        if abs(value) > INT_LIMIT:
            raise ValueError(_("a number beyond the 32-bit range"))
        return value
    if isinstance(value, dict):
        return {str(key): convert(item) for key, item in value.items()}
    if isinstance(value, list):
        return [convert(item) for item in value]
    if isinstance(value, (bytes, bytearray)):
        raise ValueError(_("data"))
    raise ValueError(_("a date") if type(value).__name__ == "datetime" else type(value).__name__)


def read(data: bytes) -> tuple:
    """(values, skipped): the keys that can be written, and a note per key
    that cannot."""
    try:
        root = plistlib.loads(data)
    except Exception as error:      # plistlib raises several kinds
        raise PlistError(_("This is not a plist file: {error}").format(error=error)) from None
    if not isinstance(root, dict):
        raise PlistError(_("The plist holds no keys: its top level is not a dictionary."))
    values, skipped = {}, []
    for key, value in root.items():
        try:
            values[str(key)] = convert(value)
        except ValueError as error:
            skipped.append(f"{key}: {error}")
    return values, skipped
