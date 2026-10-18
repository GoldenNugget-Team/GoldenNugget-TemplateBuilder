"""Small building blocks on top of the awesomeUI controls."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFormLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from awesomeui.controls import IOSCard, IOSSectionHeader, IOSSegmentedFilter, IOSSwitch

from . import icons


class Segments(IOSSegmentedFilter):
    """IOSSegmentedFilter that can be set from code without emitting and can
    rename its segments."""

    def __init__(self, items, parent=None, icon_names=None):
        super().__init__(items, parent)
        self._data = [data for _title, data in items]
        for index, name in enumerate(icon_names or []):
            if name:
                icons.attach(self._group.button(index), name, "text_secondary", 16)

    def set_data(self, data):
        """Select the segment holding ``data`` without emitting a signal."""
        if data in self._data:
            self.blockSignals(True)
            index = self._data.index(data)
            self._index = -1          # force the change even when it is the same index
            self.setCurrentIndex(index)
            self.blockSignals(False)

    def set_title(self, index, title):
        self._group.button(index).setText(title)


def card(form=False):
    """An IOSCard with a form or box layout; returns (card, layout)."""
    widget = IOSCard()
    layout = QFormLayout(widget) if form else QVBoxLayout(widget)
    layout.setContentsMargins(16, 14, 16, 14)
    layout.setSpacing(10)
    if form:
        layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
    return widget, layout


def header(text):
    return IOSSectionHeader(text)


def button(text, handler=None, icon=None):
    """A secondary (non-primary) action button, optionally with an icon."""
    widget = QPushButton(text)
    if icon:
        icons.attach(widget, icon, "text_primary", 16)
    widget.setObjectName("secondary")
    widget.setCursor(Qt.PointingHandCursor)
    if handler is not None:
        widget.clicked.connect(handler)
    return widget


def muted(text):
    label = QLabel(text)
    label.setObjectName("muted")
    label.setWordWrap(True)
    return label


def switch_row(text, switch: IOSSwitch, note=""):
    """A label (with an optional note under it) and an IOSSwitch on the right."""
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    texts = QVBoxLayout()
    texts.setSpacing(2)
    texts.addWidget(QLabel(text))
    if note:
        texts.addWidget(muted(note))
    layout.addLayout(texts, 1)
    layout.addWidget(switch, 0, Qt.AlignVCenter)
    return row


def versions_row(first, second):
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    first.setPlaceholderText("any")
    second.setPlaceholderText("any")
    layout.addWidget(first)
    layout.addWidget(QLabel("to"))
    layout.addWidget(second)
    return row
