"""What GoldenNugget writes for a tweak, given its switch and control.

The control's value replaces every plist value that is exactly "$value"
(GoldenNugget's community_tweaks.py does the same).
"""
import copy

from .model import VALUE_TOKEN, Control, Tweak


def substitute(value, replacement):
    if isinstance(value, dict):
        return {key: substitute(item, replacement) for key, item in value.items()}
    if isinstance(value, list):
        return [substitute(item, replacement) for item in value]
    return replacement if value == VALUE_TOKEN else value


def slider_steps(control: Control) -> int:
    """How many steps the slider has past its minimum, or -1 when its limits
    are unusable."""
    numbers = (control.min, control.max, control.step)
    if not all(isinstance(n, (int, float)) and not isinstance(n, bool) for n in numbers) \
            or control.step <= 0 or control.min >= control.max:
        return -1
    return min(int(round((control.max - control.min) / control.step)), 100000)


def slider_value(control: Control, position: int):
    value = min(control.min + position * control.step, control.max)
    whole = all(float(n).is_integer() for n in (control.min, control.step))
    return int(round(value)) if whole else round(value, 6)


def default_value(control: Control):
    if control is None:
        return None
    if control.type == "choice":
        index = control.default if isinstance(control.default, int) else 0
        return control.choices[index].value if 0 <= index < len(control.choices) else None
    return control.default


def writes_for(tweak: Tweak, on: bool, value=None) -> list:
    """Copies of the writes GoldenNugget makes, with the value filled in."""
    writes = copy.deepcopy(tweak.writes if on else tweak.writes_off)
    if tweak.control is not None and value is not None:
        for write in writes:
            if write.type == "plist":
                write.values = substitute(write.values, value)
    return writes
