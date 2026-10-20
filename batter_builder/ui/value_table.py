"""Editor for the keys of a plist write: one row per key with its type."""
import json

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QCompleter, QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QMessageBox, QSpinBox, QTableWidget, QTreeWidget,
    QStyledItemDelegate, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from .. import known_keys, plist_import
from ..i18n import _, n_
from ..model import VALUE_TOKEN
from .parts import button, muted

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
            self.widget.setToolTip(_("Replaced with the value of the tweak's slider, text box or choice."))
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
            self.error = _("Not valid JSON: {error}").format(error=error.msg)
            return []
        if not isinstance(parsed, (list, dict)):
            self.error = _("Use a JSON array [...] or object {...}.")
            return []
        return parsed


class KeyDelegate(QStyledItemDelegate):
    """Key cells complete the keys GoldenNugget writes in the write's file."""

    def __init__(self, table):
        super().__init__(table)
        self.model = QStandardItemModel(self)

    def set_keys(self, keys: dict):
        self.model.clear()
        for key, entry in keys.items():
            item = QStandardItem(key)
            item.setToolTip(known_keys.summary(key, entry))
            self.model.appendRow(item)

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        completer = QCompleter(self.model, editor)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        editor.setCompleter(completer)
        return editor


class ValuesTable(QWidget):
    """Edits ``values`` (a dict) in place and emits ``changed``."""
    changed = Signal()
    KEY, TYPE, VALUE = range(3)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.values = {}
        self.known = {}
        self._loading = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels([_("Key"), _("Type"), _("Value")])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(self.KEY, QHeaderView.Stretch)
        header.setSectionResizeMode(self.TYPE, QHeaderView.Fixed)
        self.table.setColumnWidth(self.TYPE, 200)
        header.setSectionResizeMode(self.VALUE, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setMinimumHeight(150)
        self.table.verticalHeader().setDefaultSectionSize(38)
        self.keys = KeyDelegate(self.table)
        self.table.setItemDelegateForColumn(self.KEY, self.keys)
        self.table.itemChanged.connect(self._item_changed)
        self.table.currentCellChanged.connect(lambda *_args: self._show_note())
        layout.addWidget(self.table)
        self.note = muted("")
        self.note.hide()
        layout.addWidget(self.note)
        buttons = QHBoxLayout()
        add = button(_("Add Key"), self.add_row, "plus")
        remove = button(_("Remove Key"), self.remove_row, "trash")
        buttons.addWidget(add)
        buttons.addWidget(remove)
        buttons.addStretch()
        buttons.addWidget(button(_("Import from Plist…"), self.import_plist, "upload"))
        layout.addLayout(buttons)

    def set_path(self, path: str):
        """The write's file: its known keys are suggested."""
        self.known = known_keys.for_path(path)
        self.keys.set_keys(self.known)
        self._show_note()

    def set_values(self, values: dict):
        self.values = values
        self._loading = True
        self.table.setRowCount(0)
        for key, value in values.items():
            self._append(key, type_of(value), value)
        self._loading = False
        self._show_note()

    def _item_changed(self, item):
        if item.column() == self.KEY and not self._loading:
            self._suggest(item)
        self._store()

    def _suggest(self, item):
        """Typing a key GoldenNugget knows sets the type and value its tweak
        uses, once: renaming the row to another known key sets them again."""
        key = item.text().strip()
        entry = self.known.get(key)
        item.setToolTip(known_keys.summary(key, entry) if entry else "")
        if entry is None or item.data(Qt.UserRole) == key:
            self._show_note()
            return
        self.table.blockSignals(True)
        item.setData(Qt.UserRole, key)
        self.table.blockSignals(False)
        row, kind = item.row(), entry["type"]
        combo = self.table.cellWidget(row, self.TYPE)
        if combo is not None and combo.currentData() != CONTROL:
            combo.blockSignals(True)
            combo.setCurrentIndex(max(0, combo.findData(kind)))
            combo.blockSignals(False)
            self._set_editor(row, kind, entry["value"])
        self._show_note()

    def _show_note(self):
        row = self.table.currentRow()
        entry = self.known.get(self._key(row)) if row >= 0 else None
        if entry is not None:
            self.note.setText(known_keys.summary(self._key(row), entry))
        elif self.known:
            self.note.setText(n_(len(self.known), "{n} key GoldenNugget writes in this file is suggested as you type a key.",
                                 "{n} keys GoldenNugget writes in this file are suggested as you type a key."))
        self.note.setVisible(entry is not None or bool(self.known))

    def errors(self) -> list:
        problems, seen = [], set()
        for row in range(self.table.rowCount()):
            key = self._key(row)
            if not key:
                problems.append(_("row {n}: the key is empty and is not saved").format(n=row + 1))
            elif key in seen:
                problems.append(_("{key}: the key is used twice; only the last row is saved").format(key=key))
            seen.add(key)
            editor = self.table.cellWidget(row, self.VALUE)
            editor.value()
            if editor.error:
                problems.append(f"{self._key(row) or _('row {n}').format(n=row + 1)}: {editor.error}")
        return problems

    def _append(self, key, kind, value):
        from PySide6.QtWidgets import QTableWidgetItem
        row = self.table.rowCount()
        self.table.insertRow(row)
        item = QTableWidgetItem(key)
        item.setData(Qt.UserRole, key)     # its type and value are already chosen
        entry = self.known.get(key)
        if entry:
            item.setToolTip(known_keys.summary(key, entry))
        self.table.setItem(row, self.KEY, item)
        combo = QComboBox()
        for name in TYPES:
            combo.addItem(_(name), name)
        combo.setCurrentIndex(max(0, combo.findData(kind)))
        combo.currentIndexChanged.connect(lambda _index, c=combo: self._retype(c, c.currentData()))
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

    def import_plist(self, path: str = ""):
        if not path:
            path, _filter = QFileDialog.getOpenFileName(self, _("Import Keys from a Plist"), "",
                                                        _("Property lists (*.plist);;All files (*)"))
            if not path:
                return
        try:
            with open(path, "rb") as handle:
                values, skipped = plist_import.read(handle.read())
        except (OSError, plist_import.PlistError) as error:
            QMessageBox.warning(self, _("Import from Plist"), str(error))
            return
        if not values:
            QMessageBox.warning(self, _("Import from Plist"), _("The plist has no keys that can be written."))
            return
        dialog = ImportDialog(values, skipped, self)
        if dialog.exec() == QDialog.Accepted:
            self.add_values(dialog.chosen())

    def add_values(self, values: dict):
        """Add rows for ``values``; a key that is already there gets the new
        value."""
        rows = {self._key(row): row for row in range(self.table.rowCount())}
        self._loading = True
        for key, value in values.items():
            if key not in rows:
                self._append(key, type_of(value), value)
                continue
            combo = self.table.cellWidget(rows[key], self.TYPE)
            combo.blockSignals(True)
            combo.setCurrentIndex(combo.findData(type_of(value)))
            combo.blockSignals(False)
            self._set_editor(rows[key], type_of(value), value)
        self._loading = False
        self._store()

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


class ImportDialog(QDialog):
    """Pick which keys of a plist to import."""

    def __init__(self, values: dict, skipped: list, parent=None):
        super().__init__(parent)
        self.values = values
        self.setWindowTitle(_("Import from Plist"))
        self.resize(640, 520)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(n_(len(values), "{n} key found.", "{n} keys found.") + " "
                                + _("Tick the ones this write should set.")))
        self.filter = QLineEdit()
        self.filter.setPlaceholderText(_("Filter keys"))
        self.filter.setClearButtonEnabled(True)
        self.filter.textChanged.connect(self._filter)
        layout.addWidget(self.filter)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([_("Key"), _("Type"), _("Value")])
        self.tree.setRootIsDecorated(False)
        self.tree.setColumnWidth(0, 260)
        self.tree.setColumnWidth(1, 120)
        for key, value in values.items():
            text = json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict, bool)) else str(value)
            item = QTreeWidgetItem([key, _(type_of(value)).split(" (")[0], text[:200]])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(0, Qt.Unchecked)
            item.setToolTip(2, text[:2000])
            self.tree.addTopLevelItem(item)
        self.tree.itemChanged.connect(self._count)
        layout.addWidget(self.tree, 1)
        row = QHBoxLayout()
        row.addWidget(button(_("Select All"), lambda: self._check_visible(Qt.Checked)))
        row.addWidget(button(_("Select None"), lambda: self._check_visible(Qt.Unchecked)))
        row.addStretch()
        layout.addLayout(row)
        if skipped:
            note = muted(_("Left out ({n}), since config.json cannot hold them: ").format(n=len(skipped))
                         + "; ".join(skipped[:8]) + ("; …" if len(skipped) > 8 else ""))
            layout.addWidget(note)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self._count()

    def _items(self):
        return [self.tree.topLevelItem(index) for index in range(self.tree.topLevelItemCount())]

    def _filter(self, text):
        needle = text.strip().lower()
        for item in self._items():
            item.setHidden(bool(needle) and needle not in item.text(0).lower())

    def _check_visible(self, state):
        for item in self._items():
            if not item.isHidden():
                item.setCheckState(0, state)

    def _count(self, *_args):
        count = len(self.chosen())
        ok = self.buttons.button(QDialogButtonBox.Ok)
        ok.setText(n_(count, "Import {n} Key", "Import {n} Keys") if count else _("Import"))
        ok.setEnabled(bool(count))

    def chosen(self) -> dict:
        keys = [item.text(0) for item in self._items() if item.checkState(0) == Qt.Checked]
        return {key: self.values[key] for key in keys}
