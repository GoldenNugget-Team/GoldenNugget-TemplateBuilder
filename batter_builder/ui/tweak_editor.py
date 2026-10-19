"""Editor page for one tweak: its switch, writes and optional control."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QPlainTextEdit, QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from awesomeui.controls import IOSDangerButton, IOSSwitch

from ..i18n import _
from ..model import Choice, Control, Template, Tweak
from . import icons
from .parts import Segments, button, card, header, muted, switch_row, versions_row
from .widgets import FitStack
from .write_editor import WriteList

CONTROLS = ((_("None"), None), (_("Slider"), "slider"), (_("Text box"), "text"), (_("Choice list"), "choice"))
CHOICE_TYPES = ("String", "Integer", "Real", "Boolean")


def _whole(*numbers) -> bool:
    return all(float(number).is_integer() for number in numbers)


def choice_type(value) -> str:
    if isinstance(value, bool):
        return "Boolean"
    if isinstance(value, int):
        return "Integer"
    if isinstance(value, float):
        return "Real"
    return "String"


def parse_choice(kind: str, text: str):
    """(value, error) for a choice cell."""
    text = text.strip() if kind != "String" else text
    try:
        if kind == "Integer":
            return int(text), ""
        if kind == "Real":
            return float(text), ""
    except ValueError:
        return 0, _("\"{text}\" is not a number").format(text=text)
    if kind == "Boolean":
        if text.lower() in ("true", "yes", "1"):
            return True, ""
        if text.lower() in ("false", "no", "0"):
            return False, ""
        return False, _("\"{text}\" is not true or false").format(text=text)
    return text, ""


class ControlEditor(QWidget):
    """Edits ``tweak.control``."""
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tweak = None
        self._loading = False
        self.choice_errors = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(muted(_("A control adds a slider, text box or list under the switch. Its value "
                                 "replaces every key of the type Control value in this tweak's writes.")))
        self.kind = Segments(CONTROLS, icon_names=("none", "slider", "text", "choice"))
        self.kind.currentIndexChanged.connect(self._kind_changed)
        layout.addWidget(self.kind)
        self.stack = FitStack()
        self.stack.addWidget(QWidget())

        slider = QWidget()
        form = QFormLayout(slider)
        form.setContentsMargins(0, 4, 0, 0)
        self.s_min, self.s_max, self.s_step, self.s_default = (self._spin() for _spin in range(4))
        for label, spin in ((_("Minimum"), self.s_min), (_("Maximum"), self.s_max),
                            (_("Step"), self.s_step), (_("Default"), self.s_default)):
            form.addRow(label, spin)
        form.addRow("", muted(_("Whole-number limits and step give whole-number values.")))
        self.stack.addWidget(slider)

        text = QWidget()
        form = QFormLayout(text)
        form.setContentsMargins(0, 4, 0, 0)
        self.t_default = QLineEdit()
        self.t_default.textChanged.connect(self._store)
        self.t_length = QSpinBox()
        self.t_length.setRange(1, 1000)
        self.t_length.valueChanged.connect(self._store)
        form.addRow(_("Default text"), self.t_default)
        form.addRow(_("Maximum length"), self.t_length)
        self.stack.addWidget(text)

        choice = QWidget()
        box = QVBoxLayout(choice)
        box.setContentsMargins(0, 4, 0, 0)
        self.c_table = QTableWidget(0, 3)
        self.c_table.setHorizontalHeaderLabels([_("Label"), _("Type"), _("Value")])
        self.c_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.c_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.c_table.setColumnWidth(1, 120)
        self.c_table.verticalHeader().setVisible(False)
        self.c_table.verticalHeader().setDefaultSectionSize(38)
        self.c_table.setMinimumHeight(130)
        self.c_table.setMaximumHeight(200)
        self.c_table.itemChanged.connect(lambda _item: self._store())
        box.addWidget(self.c_table)
        row = QHBoxLayout()
        row.addWidget(button(_("Add Choice"), self._add_choice, "plus"))
        row.addWidget(button(_("Remove Choice"), self._remove_choice, "trash"))
        row.addStretch()
        row.addWidget(QLabel(_("Default")))
        self.c_default = QComboBox()
        self.c_default.currentIndexChanged.connect(self._store)
        row.addWidget(self.c_default)
        box.addLayout(row)
        self.stack.addWidget(choice)
        layout.addWidget(self.stack)

    def _spin(self):
        spin = QDoubleSpinBox()
        spin.setRange(-1e9, 1e9)
        spin.setDecimals(4)
        spin.valueChanged.connect(self._store)
        return spin

    def edit(self, tweak: Tweak):
        self.tweak = tweak
        self._loading = True
        control = tweak.control
        self.kind.set_data(control.type if control else None)
        self.stack.setCurrentIndex(self.kind.currentIndex())
        if control is not None:
            self._show(control)
        self._loading = False
        self._check_choices()

    def _show(self, control: Control):
        number = lambda v: float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else 0.0
        if control.type == "slider":
            for spin, value in ((self.s_min, control.min), (self.s_max, control.max),
                                (self.s_step, control.step), (self.s_default, control.default)):
                spin.setValue(number(value))
        elif control.type == "text":
            self.t_default.setText(control.default if isinstance(control.default, str) else "")
            self.t_length.setValue(control.max_length if isinstance(control.max_length, int) else 200)
        else:
            self.c_table.setRowCount(0)
            for item in control.choices:
                self._append_choice(item.label, choice_type(item.value), item.value)
            self._fill_default(control.default if isinstance(control.default, int) else 0)

    def _append_choice(self, label, kind, value):
        row = self.c_table.rowCount()
        self.c_table.insertRow(row)
        self.c_table.setItem(row, 0, QTableWidgetItem(label))
        combo = QComboBox()
        for name in CHOICE_TYPES:
            combo.addItem(_(name), name)
        combo.setCurrentIndex(max(0, combo.findData(kind)))
        combo.currentIndexChanged.connect(self._store)
        self.c_table.setCellWidget(row, 1, combo)
        text = ("true" if value else "false") if isinstance(value, bool) else str(value)
        self.c_table.setItem(row, 2, QTableWidgetItem(text))

    def _fill_default(self, index):
        self.c_default.blockSignals(True)
        self.c_default.clear()
        for row in range(self.c_table.rowCount()):
            item = self.c_table.item(row, 0)
            self.c_default.addItem(item.text() if item and item.text() else _("Choice {n}").format(n=row + 1))
        self.c_default.setCurrentIndex(index if 0 <= index < self.c_default.count() else 0)
        self.c_default.blockSignals(False)

    def _kind_changed(self):
        if self.tweak is None or self._loading:
            return
        kind = self.kind.currentData()
        self.stack.setCurrentIndex(self.kind.currentIndex())
        if kind is None:
            self.tweak.control = None
        else:
            control = {"slider": Control("slider", 0.5, 0, 1, 0.1),
                       "text": Control("text", ""),
                       "choice": Control("choice", 0, choices=[Choice("Small", 1), Choice("Big", 2)])}[kind]
            self.tweak.control = control
            self._loading = True
            self._show(control)
            self._loading = False
        self._check_choices()
        self.changed.emit()

    def _add_choice(self):
        self._loading = True
        self._append_choice(f"Option {self.c_table.rowCount() + 1}", "String", "")
        self._loading = False
        self._store()

    def _remove_choice(self):
        row = self.c_table.currentRow()
        if row >= 0:
            self.c_table.removeRow(row)
            self._store()

    def _check_choices(self):
        self.choice_errors = []
        control = self.tweak.control if self.tweak else None
        if control is None or control.type != "choice":
            return
        for row in range(self.c_table.rowCount()):
            item = self.c_table.item(row, 2)
            _value, error = parse_choice(self.c_table.cellWidget(row, 1).currentData(), item.text() if item else "")
            if error:
                self.choice_errors.append(_("Choice {n}: {problem}").format(n=row + 1, problem=error))

    def _store(self, *_args):
        if self.tweak is None or self._loading or self.tweak.control is None:
            return
        control = self.tweak.control
        if control.type == "slider":
            values = [spin.value() for spin in (self.s_min, self.s_max, self.s_step, self.s_default)]
            if _whole(*values[:3]):
                values[:3] = [int(v) for v in values[:3]]
                values[3] = int(round(values[3]))
            control.min, control.max, control.step, control.default = values
        elif control.type == "text":
            control.default, control.max_length = self.t_default.text(), self.t_length.value()
        else:
            choices = []
            for row in range(self.c_table.rowCount()):
                label, value = self.c_table.item(row, 0), self.c_table.item(row, 2)
                kind = self.c_table.cellWidget(row, 1).currentData()
                choices.append(Choice(label.text() if label else "",
                                      parse_choice(kind, value.text() if value else "")[0]))
            control.choices = choices
            self._fill_default(self.c_default.currentIndex())
            control.default = max(0, self.c_default.currentIndex())
        self._check_choices()
        self.changed.emit()


class TweakEditor(QWidget):
    """The page for one tweak. ``removeRequested``, ``duplicateRequested`` and
    ``moveRequested(step)`` are handled by the window, which owns the list."""
    changed = Signal()
    renamed = Signal()
    removeRequested = Signal()
    duplicateRequested = Signal()
    moveRequested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("page")
        self.tweak = None
        self.template = None
        self._loading = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 28, 28)
        layout.setSpacing(10)

        top = QHBoxLayout()
        self.title = QLabel()
        self.title.setObjectName("pageTitle")
        top.addWidget(self.title, 1)
        top.addWidget(button(_("Move Up"), lambda: self.moveRequested.emit(-1), "up"))
        top.addWidget(button(_("Move Down"), lambda: self.moveRequested.emit(1), "down"))
        top.addWidget(button(_("Duplicate"), self.duplicateRequested.emit, "copy"))
        layout.addLayout(top)

        layout.addWidget(header(_("Switch")))
        details, form = card(form=True)
        self.label = QLineEdit()
        self.label.setMaxLength(80)
        self.label.setPlaceholderText("Hide Dock Background")
        self.id = QLineEdit()
        self.id.setMaxLength(64)
        self.id.setPlaceholderText(_("hide-dock (presets remember the switch by it)"))
        self.description = QPlainTextEdit()
        self.description.setPlaceholderText(_("Shown under the switch. Say what it changes."))
        self.description.setFixedHeight(64)
        self.default = IOSSwitch()
        self.min_version, self.max_version = QLineEdit(), QLineEdit()
        form.addRow(_("Label"), self.label)
        form.addRow(_("Id"), self.id)
        form.addRow(_("Description"), self.description)
        form.addRow(_("iOS"), versions_row(self.min_version, self.max_version))
        form.addRow(switch_row(_("On by default"), self.default, _("Switched on when someone adds the template.")))
        layout.addWidget(details)
        for widget in (self.label, self.id, self.min_version, self.max_version):
            widget.textChanged.connect(self._store)
        self.description.textChanged.connect(self._store)
        self.default.toggled.connect(self._store)

        layout.addWidget(header(_("Writes")))
        writes_card, writes_layout = card()
        self.side = Segments(((_("When on"), "on"), (_("When off"), "off")), icon_names=("power", "poweroff"))
        self.side.currentIndexChanged.connect(self._show_side)
        writes_layout.addWidget(self.side)
        self.side_note = muted("")
        writes_layout.addWidget(self.side_note)
        self.writes = WriteList()
        self.writes.changed.connect(self._writes_changed)
        writes_layout.addWidget(self.writes)
        writes_card.setMinimumHeight(430)
        layout.addWidget(writes_card)

        layout.addWidget(header(_("Control")))
        control_card, control_layout = card()
        self.control = ControlEditor()
        self.control.changed.connect(self.changed)
        control_layout.addWidget(self.control)
        layout.addWidget(control_card)

        layout.addSpacing(8)
        remove = IOSDangerButton(_("Remove Tweak"))
        icons.attach(remove, "trash", "text_inverse", 18)
        remove.setFixedHeight(42)
        remove.clicked.connect(self.removeRequested.emit)
        layout.addWidget(remove, 0, Qt.AlignLeft)
        layout.addStretch()

    def edit(self, template: Template, tweak: Tweak):
        self.template, self.tweak = template, tweak
        self._loading = True
        self.label.setText(tweak.label)
        self.id.setText(tweak.id)
        self.description.setPlainText(tweak.description)
        self.default.setChecked(tweak.default)
        self.min_version.setText(tweak.min_version)
        self.max_version.setText(tweak.max_version)
        self._loading = False
        self.title.setText(tweak.label or _("Untitled tweak"))
        self.control.edit(tweak)
        self.side.set_data("on")
        self._show_side()

    def editor_errors(self) -> list:
        """Problems only the widgets know about (cells that do not parse)."""
        return self.control.choice_errors + self.writes.value_errors()

    def _show_side(self, *_args):
        on = self.side.currentData() == "on"
        self.side_note.setText(_("Written while the switch is on.") if on else
                               _("Written while the switch is off, for example to put a key back. Optional."))
        self.writes.edit(self.template, self.tweak.writes if on else self.tweak.writes_off)
        self._side_titles()

    def _side_titles(self):
        self.side.set_title(0, f"{_('When on')} ({len(self.tweak.writes)})")
        self.side.set_title(1, f"{_('When off')} ({len(self.tweak.writes_off)})")

    def _writes_changed(self):
        self._side_titles()
        self.changed.emit()

    def _store(self, *_args):
        if self.tweak is None or self._loading:
            return
        old_label = self.tweak.label
        self.tweak.label = self.label.text()
        self.tweak.id = self.id.text().strip()
        self.tweak.description = self.description.toPlainText()
        self.tweak.default = self.default.isChecked()
        self.tweak.min_version = self.min_version.text().strip()
        self.tweak.max_version = self.max_version.text().strip()
        if old_label != self.tweak.label:
            self.title.setText(self.tweak.label or _("Untitled tweak"))
            self.renamed.emit()
        self.changed.emit()
