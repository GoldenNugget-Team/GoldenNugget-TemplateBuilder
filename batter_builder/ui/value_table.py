"""Editor for the keys of a plist write: one row per key with its type."""
import json

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QHBoxLayout, QHeaderView, QLineEdit,
    QSpinBox, QTableWidget, QVBoxLayout, QWidget,
)

from ..model import VALUE_TOKEN
from .parts import button

BOOLEAN, INTEGER, REAL, STRING, CONTROL, STRUCTURE = (
    "Boolean", "Integer", "Real", "String", "Control value", "Array / Dictionary (JSON)")
TYPES = (BOOLEAN, INTEGER, REAL, STRING, CONTROL, STRUCTURE)
INT_LIMIT = 2 ** 31 - 1


def type_of(value) -> str:
    if value == VALUE_TOKEN:
        return CONTROL
    if isinstance(value, bool):
        return BOOLEAN
    if isinstance(value, int):
        return INTEGER
    if isinstance(value, float):
        return REAL
    if isinstance(value, (list, dict)):
        return STRUCTURE
    return STRING


def default_for(kind: str):
    return {BOOLEAN: True, INTEGER: 0, REAL: 0.0, STRING: "", CONTROL: VALUE_TOKEN, STRUCTURE: []}[kind]


class ValueEditor(QWidget):
    """One value cell; its widget follows the row's type."""
    changed = Signal()

    def __init__(self, kind, value, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 0, 2, 0)
        self.kind = kind
        self.error = ""
        if kind == BOOLEAN:
            self.widget = QCheckBox("true")
            self.widget.setChecked(bool(value))
            self.widget.toggled.connect(lambda on: (self.widget.setText("true" if on else "false"),
                                                    self.changed.emit()))
            self.widget.setText("true" if value else "false")
        elif kind == INTEGER:
            self.widget = QSpinBox()
            self.widget.setRange(-INT_LIMIT, INT_LIMIT)
            self.widget.setValue(int(value) if isinstance(value, (int, float)) else 0)
            self.widget.valueChanged.connect(self.changed)
        elif kind == REAL:
            self.widget = QDoubleSpinBox()
            self.widget.setRange(-1e9, 1e9)
            self.widget.setDecimals(4)
            self.widget.setValue(float(value) if isinstance(value, (int, float)) else 0.0)
            self.widget.valueChanged.connect(self.changed)
        elif kind == CONTROL:
            self.widget = QLineEdit(VALUE_TOKEN)
            self.widget.setReadOnly(True)
            self.widget.setToolTip("Replaced with the value of the tweak's slider, text box or choice.")
        else:
            text = json.dumps(value, ensure_ascii=False) if kind == STRUCTURE else str(value)
            self.widget = QLineEdit(text)
            if kind == STRUCTURE:
                self.widget.setPlaceholderText('[1, 2] or {"key": true}')
            self.widget.textChanged.connect(self.changed)
        layout.addWidget(self.widget)

    def value(self):
        self.error = ""
        if self.kind == BOOLEAN:
            return self.widget.isChecked()
        if self.kind in (INTEGER, REAL):
            return self.widget.value()
        if self.kind == CONTROL:
            return VALUE_TOKEN
        text = self.widget.text()
        if self.kind == STRING:
            return text
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as error:
            self.error = f"Not valid JSON: {error.msg}"
            return []
        if not isinstance(parsed, (list, dict)):
            self.error = "Use a JSON array [...] or object {...}."
            return []
        return parsed


class ValuesTable(QWidget):
    """Edits ``values`` (a dict) in place and emits ``changed``."""
    changed = Signal()
    KEY, TYPE, VALUE = range(3)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.values = {}
        self._loading = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Key", "Type", "Value"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(self.KEY, QHeaderView.Stretch)
        header.setSectionResizeMode(self.TYPE, QHeaderView.Fixed)
        self.table.setColumnWidth(self.TYPE, 200)
        header.setSectionResizeMode(self.VALUE, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setMinimumHeight(150)
        self.table.verticalHeader().setDefaultSectionSize(38)
        self.table.itemChanged.connect(lambda _item: self._store())
        layout.addWidget(self.table)
        buttons = QHBoxLayout()
        add = button("Add Key", self.add_row)
        remove = button("Remove Key", self.remove_row)
        buttons.addWidget(add)
        buttons.addWidget(remove)
        buttons.addStretch()
        layout.addLayout(buttons)

    def set_values(self, values: dict):
        self.values = values
        self._loading = True
        self.table.setRowCount(0)
        for key, value in values.items():
            self._append(key, type_of(value), value)
        self._loading = False

    def errors(self) -> list:
        problems, seen = [], set()
        for row in range(self.table.rowCount()):
            key = self._key(row)
            if not key:
                problems.append(f"row {row + 1}: the key is empty and is not saved")
            elif key in seen:
                problems.append(f"{key}: the key is used twice; only the last row is saved")
            seen.add(key)
            editor = self.table.cellWidget(row, self.VALUE)
            editor.value()
            if editor.error:
                problems.append(f"{self._key(row) or 'row ' + str(row + 1)}: {editor.error}")
        return problems

    def _append(self, key, kind, value):
        from PySide6.QtWidgets import QTableWidgetItem
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, self.KEY, QTableWidgetItem(key))
        combo = QComboBox()
        combo.addItems(TYPES)
        combo.setCurrentText(kind)
        combo.currentTextChanged.connect(lambda text, c=combo: self._retype(c, text))
        self.table.setCellWidget(row, self.TYPE, combo)
        self._set_editor(row, kind, value)

    def _set_editor(self, row, kind, value):
        editor = ValueEditor(kind, value)
        editor.changed.connect(self._store)
        self.table.setCellWidget(row, self.VALUE, editor)

    def _row_of(self, widget) -> int:
        for row in range(self.table.rowCount()):
            if self.table.cellWidget(row, self.TYPE) is widget:
                return row
        return -1

    def _retype(self, combo, kind):
        row = self._row_of(combo)
        if row >= 0:
            self._set_editor(row, kind, default_for(kind))
            self._store()

    def _key(self, row) -> str:
        item = self.table.item(row, self.KEY)
        return item.text().strip() if item else ""

    def add_row(self):
        used = {self._key(row) for row in range(self.table.rowCount())}
        name, number = "NewKey", 1
        while name in used:
            number += 1
            name = f"NewKey{number}"
        self._loading = True
        self._append(name, BOOLEAN, True)
        self._loading = False
        self._store()
        self.table.setCurrentCell(self.table.rowCount() - 1, self.KEY)
        self.table.editItem(self.table.item(self.table.rowCount() - 1, self.KEY))

    def remove_row(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)
            self._store()

    def _store(self):
        if self._loading:
            return
        rebuilt = {}
        for row in range(self.table.rowCount()):
            key = self._key(row)
            editor = self.table.cellWidget(row, self.VALUE)
            if key and editor is not None:
                rebuilt[key] = editor.value()
        self.values.clear()
        self.values.update(rebuilt)
        self.changed.emit()
