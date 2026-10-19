"""Reading keys from an existing .plist file for a plist write.

config.json holds JSON, so only values JSON can hold are taken: text,
whole and real numbers, booleans, arrays and dictionaries of them. Data and
dates are left out, and so are whole numbers outside the 32-bit range the
editor's number cells take.
"""
import plistlib

INT_LIMIT = 2 ** 31 - 1


class PlistError(ValueError):
    pass


def convert(value):
    """``value`` as config.json can hold it; raises ValueError otherwise."""
    if isinstance(value, bool) or isinstance(value, (str, float)):
        return value
    if isinstance(value, int):
        if abs(value) > INT_LIMIT:
            raise ValueError("a number beyond the 32-bit range")
        return value
    if isinstance(value, dict):
        return {str(key): convert(item) for key, item in value.items()}
    if isinstance(value, list):
        return [convert(item) for item in value]
    if isinstance(value, (bytes, bytearray)):
        raise ValueError("data")
    raise ValueError(type(value).__name__.replace("datetime", "a date"))


def read(data: bytes) -> tuple:
    """(values, skipped): the keys that can be written, and a note per key
    that cannot."""
    try:
        root = plistlib.loads(data)
    except Exception as error:      # plistlib raises several kinds
        raise PlistError(f"This is not a plist file: {error}") from None
    if not isinstance(root, dict):
        raise PlistError("The plist holds no keys: its top level is not a dictionary.")
    values, skipped = {}, []
    for key, value in root.items():
        try:
            values[str(key)] = convert(value)
        except ValueError as error:
            skipped.append(f"{key}: {error}")
    return values, skipped
