"""Editor for a tweak's writes: a list on the left, the selected write on
the right."""
import copy
import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QListWidget, QMessageBox,
    QStackedWidget, QVBoxLayout, QWidget,
)

from ..i18n import _
from ..locations import LOCATIONS
from ..model import Template, Write
from ..rules import MAX_SOURCE_BYTES, path_problem
from .parts import Segments, button, muted
from .value_table import ValuesTable
from .widgets import FitStack

TYPES = ((_("Plist keys"), "plist"), (_("Whole file"), "file"), (_("Empty file"), "empty"))
OWNERS = ((_("mobile (501)"), 501), (_("root (0)"), 0))


def describe(write: Write) -> str:
    name = write.path.rsplit("/", 1)[-1] or _("(no path)")
    if write.type == "plist":
        return f"{name}: {', '.join(write.values) or _('no keys')}"
    if write.type == "file":
        return f"{name} ← {write.source or _('no file')}"
    return f"{name} {_('(empty)')}"


class WriteForm(QWidget):
    """Edits one Write in place."""
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.write = None
        self.template = None
        self._loading = False
        form = QFormLayout(self)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.type = Segments(TYPES, icon_names=("keys", "file", "empty"))
        self.type.currentIndexChanged.connect(self._type_changed)
        form.addRow(_("Write"), self.type)

        self.path = QComboBox()
        self.path.setEditable(True)
        self.path.setInsertPolicy(QComboBox.NoInsert)
        for path, label in LOCATIONS:
            self.path.addItem(path)
            self.path.setItemData(self.path.count() - 1, _(label), Qt.ToolTipRole)
        self.path.lineEdit().setPlaceholderText("/var/Managed Preferences/mobile/com.apple.springboard.plist")
        self.path.editTextChanged.connect(self._path_changed)
        form.addRow(_("Path on iPhone"), self.path)
        self.path_note = QLabel()
        self.path_note.setWordWrap(True)
        form.addRow("", self.path_note)

        self.owner = Segments(OWNERS, icon_names=("mobile", "root"))
        self.owner.currentIndexChanged.connect(self._owner_changed)
        form.addRow(_("Owner"), self.owner)

        self.stack = FitStack()
        self.values = ValuesTable()
        self.values.changed.connect(self._emit)
        self.stack.addWidget(self.values)
        file_page = QWidget()
        file_row = QHBoxLayout(file_page)
        file_row.setContentsMargins(0, 0, 0, 0)
        self.source = QLabel()
        self.source.setWordWrap(True)
        file_row.addWidget(self.source, 1)
        file_row.addWidget(button(_("Choose File…"), self._choose_file, "open"), 0, Qt.AlignTop)
        self.stack.addWidget(file_page)
        self.stack.addWidget(muted(_("Writes an empty file. A path ending in .plist gets an empty plist, "
                                     "since a zero-byte plist can send iOS 26.2+ into a boot loop.")))
        form.addRow(self.stack)

    def edit(self, template: Template, write: Write):
        self.template, self.write = template, write
        self._loading = True
        self.type.set_data(write.type)
        self.path.setEditText(write.path)
        self.owner.set_data(write.owner)
        self.values.set_values(write.values)
        self._show_type()
        self._loading = False
        self._update_path_note()

    def _emit(self):
        if not self._loading:
            self.changed.emit()

    def _show_type(self):
        self.stack.setCurrentIndex(("plist", "file", "empty").index(self.write.type))
        self.source.setText(self._source_text())

    def _source_text(self):
        source = self.write.source
        if not source:
            return _("No file chosen.")
        if source not in self.template.entries:
            return f"{source} {_('(missing)')}"
        return f"{source} (" + _("{size} bytes").format(size=f"{len(self.template.entries[source]):,}") + ")"

    def _type_changed(self):
        if self.write is None or self._loading:
            return
        self.write.type = self.type.currentData()
        self._show_type()
        self._emit()

    def _path_changed(self, text):
        if self.write is None or self._loading:
            return
        self.write.path = text.strip()
        self._update_path_note()
        self._emit()

    def _update_path_note(self):
        problem = path_problem(self.write.path) if self.write.path else _("Enter where the iPhone stores the file.")
        self.path_note.setText(problem or _("GoldenNugget can write here."))
        self.path_note.setObjectName("bad" if problem else "good")
        self.path_note.style().unpolish(self.path_note)
        self.path_note.style().polish(self.path_note)

    def _owner_changed(self):
        if self.write is None or self._loading:
            return
        self.write.owner = self.owner.currentData()
        self._emit()

    def _choose_file(self):
        path, _filter = QFileDialog.getOpenFileName(self, _("Choose the file to install"))
        if not path:
            return
        if os.path.getsize(path) > MAX_SOURCE_BYTES:
            QMessageBox.warning(self, _("File too large"), _("GoldenNugget accepts files of at most 4 MB."))
            return
        with open(path, "rb") as handle:
            data = handle.read()
        self.write.source = self.template.add_source(os.path.basename(path), data)
        self.source.setText(self._source_text())
        self._emit()


class WriteList(QWidget):
    """Edits a list of writes in place."""
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.writes = []
        self.template = None
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        left = QVBoxLayout()
        self.list = QListWidget()
        self.list.setMinimumWidth(210)
        self.list.currentRowChanged.connect(self._select)
        left.addWidget(self.list, 1)
        buttons = QHBoxLayout()
        for text, handler, name in ((_("Add"), self._add, "plus"), (_("Duplicate"), self._duplicate, "copy"),
                                    (_("Remove"), self._remove, "trash")):
            buttons.addWidget(button(text, handler, name))
        left.addLayout(buttons)
        layout.addLayout(left, 1)
        self.form = WriteForm()
        self.form.changed.connect(self._form_changed)
        self.placeholder = muted(_("Add a write to say what this tweak changes on the iPhone."))
        self.placeholder.setAlignment(Qt.AlignCenter)
        self.right = QStackedWidget()
        self.right.addWidget(self.placeholder)
        self.right.addWidget(self.form)
        layout.addWidget(self.right, 2)

    def edit(self, template: Template, writes: list):
        self.template, self.writes = template, writes
        self._refresh(0 if writes else -1)

    def value_errors(self) -> list:
        write = self.form.write
        if self.right.currentWidget() is self.form and write is not None and write.type == "plist":
            return self.form.values.errors()
        return []

    def _refresh(self, select):
        self.list.blockSignals(True)
        self.list.clear()
        for write in self.writes:
            self.list.addItem(describe(write))
        self.list.blockSignals(False)
        if select >= 0:
            self.list.setCurrentRow(select)
        self._select(self.list.currentRow())

    def _select(self, row):
        if 0 <= row < len(self.writes):
            self.form.edit(self.template, self.writes[row])
            self.right.setCurrentWidget(self.form)
        else:
            self.right.setCurrentWidget(self.placeholder)

    def _form_changed(self):
        row = self.list.currentRow()
        if 0 <= row < len(self.writes):
            self.list.item(row).setText(describe(self.writes[row]))
        self.changed.emit()

    def _add(self):
        previous = self.writes[-1].path if self.writes else LOCATIONS[0][0]
        self.writes.append(Write("plist", previous, {}))
        self._refresh(len(self.writes) - 1)
        self.changed.emit()

    def _duplicate(self):
        row = self.list.currentRow()
        if 0 <= row < len(self.writes):
            self.writes.insert(row + 1, copy.deepcopy(self.writes[row]))
            self._refresh(row + 1)
            self.changed.emit()

    def _remove(self):
        row = self.list.currentRow()
        if 0 <= row < len(self.writes):
            del self.writes[row]
            self._refresh(min(row, len(self.writes) - 1))
            self.changed.emit()
