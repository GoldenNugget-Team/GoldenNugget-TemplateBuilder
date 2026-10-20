"""Wallpaper options (config format 2): the restore domain, previews and the
options people change in GoldenNugget before applying, such as replacing an
image, setting a value in a .caml file, removing files or picking one of
several versions.

The options are edited in place in ``template.extra``, as plain dicts, so
keys this page does not know are kept as they were.
"""
import json
import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMenu, QPlainTextEdit, QSpinBox, QStackedWidget,
    QVBoxLayout, QWidget,
)

from awesomeui.controls import IOSSwitch

from ..i18n import _, n_
from ..model import Template
from ..rules import OPTION_TYPES
from .parts import button, card, header, muted
from .widgets import FitStack

DOMAINS = ("AppDomain-com.apple.PosterBoard", "Sparserestore-/var/Managed Preferences")
TYPE_LABELS = {"replace": "Replace files", "set": "Set a value", "remove": "Remove files",
               "picker": "Picker", "bundle_id": "App bundle id"}
TYPE_NOTES = {
    "replace": "People choose a file of their own; it replaces the files listed here.",
    "set": "Changes a property in .caml files: the layer whose nuggetId (or id) is the identifier.",
    "remove": "A checkbox; while it is ticked the files listed here are removed (or the layer, "
              "with an identifier).",
    "picker": "People pick one of several choices; the files of the other choices are removed.",
    "bundle_id": "For AppDomain templates: people can type another app's bundle id to restore to.",
}
MAX_FOLDER_FILES = 5000


def parse_value(text: str):
    """A number, true/false or JSON value as written; anything else is text."""
    text = text.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def show_value(value) -> str:
    if value is None:
        return ""
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


class FilesEdit(QWidget):
    """One path per line, plus a picker for files already in the template."""
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.template = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.text = QPlainTextEdit()
        self.text.setPlaceholderText(_("descriptors/…/bg.ca/main.caml (one per line; * matches anything)"))
        self.text.setFixedHeight(84)
        self.text.textChanged.connect(self.changed)
        layout.addWidget(self.text)
        layout.addWidget(button(_("Add from Template…"), self._pick, "file"), 0, Qt.AlignLeft)

    def set_files(self, template: Template, files):
        self.template = template
        self.text.blockSignals(True)
        self.text.setPlainText("\n".join(f for f in (files or []) if isinstance(f, str)))
        self.text.blockSignals(False)

    def files(self) -> list:
        return [line.strip() for line in self.text.toPlainText().splitlines() if line.strip()]

    def _pick(self):
        dialog = EntryPicker(sorted(self.template.entries) if self.template else [], self)
        if dialog.exec() == QDialog.Accepted:
            current = self.files()
            self.text.setPlainText("\n".join(current + [n for n in dialog.chosen() if n not in current]))


class EntryPicker(QDialog):
    """Tick files of the template."""

    def __init__(self, names, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Files in the Template"))
        self.resize(560, 480)
        layout = QVBoxLayout(self)
        self.filter = QLineEdit()
        self.filter.setPlaceholderText(_("Filter files"))
        self.filter.setClearButtonEnabled(True)
        layout.addWidget(self.filter)
        self.list = QListWidget()
        for name in names:
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.list.addItem(item)
        self.filter.textChanged.connect(self._filter)
        layout.addWidget(self.list, 1)
        if not names:
            layout.addWidget(muted(_("The template has no files yet. Add a folder on the Wallpaper Options page.")))
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _filter(self, text):
        for index in range(self.list.count()):
            item = self.list.item(index)
            item.setHidden(bool(text) and text.lower() not in item.text().lower())

    def chosen(self) -> list:
        return [self.list.item(i).text() for i in range(self.list.count())
                if self.list.item(i).checkState() == Qt.Checked]


class OptionForm(QWidget):
    """Edits one option dict in place."""
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.option = None
        self.template = None
        self._loading = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.kind = QLabel()
        self.kind.setStyleSheet("font-size: 15px; font-weight: 650; background: transparent;")
        layout.addWidget(self.kind)
        self.note = muted("")
        layout.addWidget(self.note)
        common = QFormLayout()
        common.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.label = QLineEdit()
        self.label.textChanged.connect(lambda text: self._set("label", text))
        common.addRow(_("Label"), self.label)
        self.files = FilesEdit()
        self.files.changed.connect(lambda: self._set("files", self.files.files(), keep_empty=True))
        common.addRow(_("Files"), self.files)
        self.preview = QComboBox()
        self.preview.setEditable(True)
        self.preview.editTextChanged.connect(lambda text: self._set("associated_preview", text.strip()))
        common.addRow(_("Preview image"), self.preview)
        self.common = common
        layout.addLayout(common)
        self.stack = FitStack()
        self.pages = {}
        for kind in OPTION_TYPES:
            page = QWidget()
            form = QFormLayout(page)
            form.setContentsMargins(0, 0, 0, 0)
            form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
            getattr(self, f"_build_{kind}")(form)
            self.pages[kind] = self.stack.count()
            self.stack.addWidget(page)
        layout.addWidget(self.stack)

    # ----- building -----
    def _text(self, form, label, key, placeholder=""):
        field = QLineEdit()
        field.setPlaceholderText(placeholder)
        field.textChanged.connect(lambda text: self._set(key, text.strip()))
        form.addRow(label, field)
        return field

    def _value(self, form, label, key, placeholder=""):
        field = QLineEdit()
        field.setPlaceholderText(placeholder)
        field.textChanged.connect(lambda text: self._set(key, parse_value(text)))
        form.addRow(label, field)
        return field

    def _switch(self, form, label, key):
        switch = IOSSwitch()
        switch.toggled.connect(lambda on: self._set(key, on, default=False))
        form.addRow(label, switch)
        return switch

    def _combo(self, form, label, key, values, optional=False):
        combo = QComboBox()
        if optional:
            combo.addItem(_("(not set)"), None)
        for value in values:
            combo.addItem(value, value)
        combo.currentIndexChanged.connect(lambda _index: self._set(key, combo.currentData()))
        form.addRow(label, combo)
        return combo

    def _build_replace(self, form):
        self.r_button = self._text(form, _("Button label"), "button_label", _("Choose Image"))
        self.r_allowed = self._text(form, _("Allowed files"), "allowed_files", "Images (*.png *.jpg *.heic)")
        self.r_required = self._switch(form, _("Required"), "required")

    # the set fields each setter uses (GoldenNugget's set_option.py)
    SETTER_FIELDS = {"slider": ("s_min", "s_max", "s_step"), "textbox": ("s_min", "s_max"),
                     "toggle": ("s_inverted", "s_on", "s_off"), "color_picker": ("s_opacity",)}

    def _show_setter_fields(self):
        used = self.SETTER_FIELDS.get(self.s_setter.currentData(), ())
        for name in ("s_min", "s_max", "s_step", "s_inverted", "s_on", "s_off", "s_opacity"):
            self.set_form.setRowVisible(getattr(self, name), name in used)
        self.stack.adjustSize()

    def _build_set(self, form):
        self.set_form = form
        self.s_identifier = self._text(form, _("Identifier"), "identifier", _("the layer's nuggetId"))
        self.s_use_ca_id = self._switch(form, _("Use the CoreAnimation id"), "use_ca_id")
        self.s_key = self._text(form, _("Property"), "key", "opacity")
        self.s_setter = self._combo(form, _("Control"), "setter_type", ("textbox", "slider", "toggle", "color_picker"))
        self.s_value_type = self._combo(form, _("Value type"), "value_type", ("integer", "float", "string"), True)
        self.s_default = self._value(form, _("Default value"), "default_value", "1.0")
        self.s_min = self._value(form, _("Minimum"), "min_value")
        self.s_max = self._value(form, _("Maximum"), "max_value")
        self.s_step = self._value(form, _("Step"), "step")
        self.s_inverted = self._switch(form, _("Inverted"), "inverted")
        self.s_on = self._value(form, _("Value when on"), "toggle_on_value")
        self.s_off = self._value(form, _("Value when off"), "toggle_off_value")
        self.s_opacity = self._switch(form, _("Includes opacity"), "sets_opacity")
        self.s_setter.currentIndexChanged.connect(lambda _i: self._show_setter_fields())

    def _build_remove(self, form):
        self.m_default = self._switch(form, _("Ticked by default"), "default_value")
        self.m_inverted = self._switch(form, _("Inverted (remove while unticked)"), "inverted")
        self.m_identifier = self._text(form, _("Identifier"), "identifier", _("optional: remove one layer"))
        self.m_use_ca_id = self._switch(form, _("Use the CoreAnimation id"), "use_ca_id")

    def _build_picker(self, form):
        self.p_multiple = self._switch(form, _("Allow several choices"), "allow_multiple_selection")
        self.p_rename = self._switch(form, _("Rename the chosen files"), "rename")
        self.p_names = FilesEdit()
        self.p_names.changed.connect(lambda: self._set("names", self.p_names.files()))
        form.addRow(_("New names"), self.p_names)
        self.p_default = QSpinBox()
        self.p_default.setRange(0, 99)
        self.p_default.valueChanged.connect(lambda value: self._set("default_value", value, default=0))
        form.addRow(_("Default choice"), self.p_default)
        self.choices = ChoiceList()
        self.choices.changed.connect(self.changed)
        form.addRow(_("Choices"), self.choices)

    def _build_bundle_id(self, form):
        form.addRow(muted(_("No settings: the domain's bundle id is the default.")))

    # ----- editing -----
    def edit(self, template: Template, option: dict, previews: list):
        self.template, self.option = template, option
        kind = option.get("type") if option.get("type") in OPTION_TYPES else "replace"
        self._loading = True
        self.kind.setText(_(TYPE_LABELS[kind]))
        self.note.setText(_(TYPE_NOTES[kind]))
        self.label.setText(option.get("label", "") if isinstance(option.get("label"), str) else "")
        has_files = kind not in ("picker", "bundle_id")
        self.common.setRowVisible(self.files, has_files)
        self.common.setRowVisible(self.preview, kind != "bundle_id")
        self.files.set_files(template, option.get("files"))
        self.preview.clear()
        self.preview.addItem("")
        self.preview.addItems(previews)
        self.preview.setEditText(show_value(option.get("associated_preview")))
        get = lambda key: option.get(key)
        if kind == "replace":
            self.r_button.setText(show_value(get("button_label")))
            self.r_allowed.setText(show_value(get("allowed_files")))
            self.r_required.setChecked(get("required") is True)
        elif kind == "set":
            self.s_identifier.setText(show_value(get("identifier")))
            self.s_use_ca_id.setChecked(get("use_ca_id") is True)
            self.s_key.setText(show_value(get("key")))
            self.s_setter.setCurrentIndex(max(0, self.s_setter.findData(get("setter_type"))))
            self.s_value_type.setCurrentIndex(max(0, self.s_value_type.findData(get("value_type"))))
            for field, key in ((self.s_default, "default_value"), (self.s_min, "min_value"),
                               (self.s_max, "max_value"), (self.s_step, "step"),
                               (self.s_on, "toggle_on_value"), (self.s_off, "toggle_off_value")):
                field.setText(show_value(get(key)))
            self.s_inverted.setChecked(get("inverted") is True)
            self.s_opacity.setChecked(get("sets_opacity") is True)
            self._show_setter_fields()
        elif kind == "remove":
            self.m_default.setChecked(get("default_value") is True)
            self.m_inverted.setChecked(get("inverted") is True)
            self.m_identifier.setText(show_value(get("identifier")))
            self.m_use_ca_id.setChecked(get("use_ca_id") is True)
        elif kind == "picker":
            self.p_multiple.setChecked(get("allow_multiple_selection") is True)
            self.p_rename.setChecked(get("rename") is True)
            self.p_names.set_files(template, get("names"))
            self.p_default.setValue(get("default_value") if isinstance(get("default_value"), int) else 0)
            if not isinstance(option.get("options"), list):
                option["options"] = []
            self.choices.edit(template, option["options"], previews)
        self.stack.setCurrentIndex(self.pages[kind])
        self._loading = False

    def _set(self, key, value, default=None, keep_empty=False):
        """Store ``value``, or drop the key when it is empty or ``default`` so
        the config only holds what was chosen."""
        if self._loading or self.option is None:
            return
        if (value is None or value == "" or (value == [] and not keep_empty)
                or (default is not None and value == default)):
            self.option.pop(key, None)
        else:
            self.option[key] = value
        self.changed.emit()


class ChoiceList(QWidget):
    """The choices of a picker: a label and files each."""
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.choices = []
        self.template = None
        self._loading = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        row = QHBoxLayout()
        self.list = QListWidget()
        self.list.setMaximumHeight(120)
        self.list.currentRowChanged.connect(self._select)
        row.addWidget(self.list, 1)
        side = QVBoxLayout()
        side.addWidget(button(_("Add Choice"), self._add, "plus"))
        side.addWidget(button(_("Remove Choice"), self._remove, "trash"))
        side.addStretch()
        row.addLayout(side)
        layout.addLayout(row)
        self.form = QWidget()
        form = QFormLayout(self.form)
        form.setContentsMargins(0, 0, 0, 0)
        self.label = QLineEdit()
        self.label.textChanged.connect(self._store)
        form.addRow(_("Label"), self.label)
        self.files = FilesEdit()
        self.files.changed.connect(self._store)
        form.addRow(_("Files"), self.files)
        self.preview = QComboBox()
        self.preview.setEditable(True)
        self.preview.editTextChanged.connect(self._store)
        form.addRow(_("Preview image"), self.preview)
        layout.addWidget(self.form)

    def edit(self, template, choices: list, previews: list):
        self.template, self.choices = template, choices
        self.preview.blockSignals(True)
        self.preview.clear()
        self.preview.addItem("")
        self.preview.addItems(previews)
        self.preview.blockSignals(False)
        self._refresh(0 if choices else -1)

    def _refresh(self, select):
        self.list.blockSignals(True)
        self.list.clear()
        for number, choice in enumerate(self.choices, 1):
            label = choice.get("label") if isinstance(choice, dict) else None
            self.list.addItem(label or _("Choice {n}").format(n=number))
        self.list.blockSignals(False)
        self.list.setCurrentRow(select)
        self._select(select)

    def _select(self, row):
        self.form.setVisible(0 <= row < len(self.choices))
        if not 0 <= row < len(self.choices) or not isinstance(self.choices[row], dict):
            return
        choice = self.choices[row]
        self._loading = True
        self.label.setText(choice.get("label", "") if isinstance(choice.get("label"), str) else "")
        self.files.set_files(self.template, choice.get("files"))
        self.preview.setEditText(show_value(choice.get("associated_preview")))
        self._loading = False

    def _store(self, *_args):
        row = self.list.currentRow()
        if self._loading or not 0 <= row < len(self.choices) or not isinstance(self.choices[row], dict):
            return
        choice = self.choices[row]
        choice["label"] = self.label.text()
        choice["files"] = self.files.files()
        preview = self.preview.currentText().strip()
        if preview:
            choice["associated_preview"] = preview
        else:
            choice.pop("associated_preview", None)
        self.list.item(row).setText(choice["label"] or _("Choice {n}").format(n=row + 1))
        self.changed.emit()

    def _add(self):
        self.choices.append({"label": _("Choice {n}").format(n=len(self.choices) + 1), "files": []})
        self._refresh(len(self.choices) - 1)
        self.changed.emit()

    def _remove(self):
        row = self.list.currentRow()
        if 0 <= row < len(self.choices):
            del self.choices[row]
            self._refresh(min(row, len(self.choices) - 1))
            self.changed.emit()


class OptionsPage(QWidget):
    """The Wallpaper Options page. ``changed`` fires on every edit;
    ``commit`` (set by the window) makes the edits so far one undo step, so
    adding, removing and moving options are steps of their own."""
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("page")
        self.commit = lambda: None
        self.template = Template()
        self._loading = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 28, 28)
        layout.setSpacing(10)
        title = QLabel(_("Wallpaper Options"))
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        layout.addWidget(muted(_("For templates that restore files, like PosterBoard wallpapers: where the files "
                                 "go, and the options people change in GoldenNugget before applying. A template "
                                 "with only tweaks needs nothing here.")))

        layout.addWidget(header(_("Restore")))
        box, form = card(form=True)
        self.domain = QComboBox()
        self.domain.setEditable(True)
        self.domain.addItem("")
        self.domain.addItems(DOMAINS)
        self.domain.lineEdit().setPlaceholderText(_("none: the template has only tweaks"))
        self.domain.editTextChanged.connect(lambda text: self._set("domain", text.strip()))
        form.addRow(_("Domain"), self.domain)
        form.addRow("", muted(_("AppDomain-<bundle id> restores the template's Container folder into that app "
                                "(PosterBoard for wallpapers); Sparserestore-<path> restores it under a path.")))
        self.file_count = muted("")
        files = QWidget()
        files_row = QHBoxLayout(files)
        files_row.setContentsMargins(0, 0, 0, 0)
        files_row.addWidget(self.file_count, 1)
        files_row.addWidget(button(_("Add Folder…"), self.add_folder, "open"))
        form.addRow(_("Files"), files)
        layout.addWidget(box)

        layout.addWidget(header(_("Previews")))
        box, form = card(form=True)
        self.previews = QLineEdit()
        self.previews.setPlaceholderText("preview.png, preview-dark.png")
        self.previews.textChanged.connect(lambda text: self._set_list("previews", text))
        form.addRow(_("Preview images"), self.previews)
        self.resources = QLineEdit()
        self.resources.setPlaceholderText("preview*.png")
        self.resources.textChanged.connect(lambda text: self._set_list("resources", text))
        form.addRow(_("Resources"), self.resources)
        self.layout_combo = QComboBox()
        self.layout_combo.addItem(_("Side by side"), "horizontal")
        self.layout_combo.addItem(_("Stacked"), "stacked")
        self.layout_combo.currentIndexChanged.connect(
            lambda _i: self._set("preview_layout", self.layout_combo.currentData(), default="horizontal"))
        form.addRow(_("Layout"), self.layout_combo)
        self.banner = QLineEdit()
        self.banner.textChanged.connect(lambda text: self._set("banner_text", text.strip()))
        form.addRow(_("Banner text"), self.banner)
        form.addRow("", muted(_("Previews and the banner show above the options in GoldenNugget. Every preview "
                                "must also match a resource (comma-separated paths, * allowed).")))
        layout.addWidget(box)

        layout.addWidget(header(_("Options")))
        box, box_layout = card()
        row = QHBoxLayout()
        left = QVBoxLayout()
        self.list = QListWidget()
        self.list.setMinimumWidth(220)
        self.list.currentRowChanged.connect(self._select)
        left.addWidget(self.list, 1)
        buttons = QHBoxLayout()
        self.add_button = button(_("Add"), None, "plus")
        menu = QMenu(self.add_button)
        for kind in OPTION_TYPES:
            menu.addAction(_(TYPE_LABELS[kind]), lambda k=kind: self.add_option(k))
        self.add_button.setMenu(menu)
        buttons.addWidget(self.add_button)
        buttons.addWidget(button(_("Duplicate"), self._duplicate, "copy"))
        buttons.addWidget(button(_("Remove"), self._remove, "trash"))
        left.addLayout(buttons)
        moves = QHBoxLayout()
        moves.addWidget(button(_("Move Up"), lambda: self._move(-1), "up"))
        moves.addWidget(button(_("Move Down"), lambda: self._move(1), "down"))
        left.addLayout(moves)
        row.addLayout(left, 1)
        self.form = OptionForm()
        self.form.changed.connect(self._form_changed)
        self.placeholder = muted(_("No options yet. Add one to let people customize the wallpaper."))
        self.placeholder.setAlignment(Qt.AlignCenter)
        self.right = QStackedWidget()
        self.right.addWidget(self.placeholder)
        self.right.addWidget(self.form)
        row.addWidget(self.right, 2)
        box_layout.addLayout(row)
        layout.addWidget(box)
        layout.addStretch()

    # ----- state -----
    @property
    def options(self) -> list:
        options = self.template.extra.get("options")
        return options if isinstance(options, list) else []

    def show_template(self, template: Template, select: int = 0):
        self.template = template
        extra = template.extra
        self._loading = True
        self.domain.setEditText(str(extra.get("domain", "")))
        self.previews.setText(", ".join(p for p in extra.get("previews", []) if isinstance(p, str))
                              if isinstance(extra.get("previews"), list) else "")
        self.resources.setText(", ".join(r for r in extra.get("resources", []) if isinstance(r, str))
                               if isinstance(extra.get("resources"), list) else "")
        self.layout_combo.setCurrentIndex(max(0, self.layout_combo.findData(extra.get("preview_layout", "horizontal"))))
        self.banner.setText(str(extra.get("banner_text", "")))
        self._loading = False
        self._show_file_count()
        self._refresh(select if self.options else -1)

    def _show_file_count(self):
        count = len(self.template.entries)
        self.file_count.setText(n_(count, "{n} file in the template", "{n} files in the template") if count else
                                _("No files yet: add the folder that holds the Container (or descriptors)."))

    def _previews(self) -> list:
        previews = self.template.extra.get("previews", [])
        return [p for p in previews if isinstance(p, str)] if isinstance(previews, list) else []

    def _set(self, key, value, default=None):
        if self._loading:
            return
        if value in ("", None) or (default is not None and value == default):
            self.template.extra.pop(key, None)
        else:
            self.template.extra[key] = value
        self.changed.emit()

    def _set_list(self, key, text):
        values = [part.strip() for part in text.split(",") if part.strip()]
        self._set(key, values or None)

    def _describe(self, option) -> str:
        if not isinstance(option, dict):
            return _("(broken option)")
        kind = _(TYPE_LABELS.get(option.get("type"), "Unknown"))
        return f"{option.get('label') or _('(no label)')} · {kind}"

    def _refresh(self, select):
        self.list.blockSignals(True)
        self.list.clear()
        for option in self.options:
            self.list.addItem(self._describe(option))
        self.list.blockSignals(False)
        if select >= 0:
            self.list.setCurrentRow(select)
        self._select(self.list.currentRow())

    def _select(self, row):
        options = self.options
        if 0 <= row < len(options) and isinstance(options[row], dict):
            self.form.edit(self.template, options[row], self._previews())
            self.right.setCurrentWidget(self.form)
        else:
            self.right.setCurrentWidget(self.placeholder)

    def _structure_changed(self, select):
        self._refresh(select)
        self.changed.emit()
        self.commit()

    def _form_changed(self):
        row = self.list.currentRow()
        if 0 <= row < len(self.options):
            self.list.item(row).setText(self._describe(self.options[row]))
        self.changed.emit()

    # ----- actions -----
    def add_option(self, kind: str):
        option = {"type": kind, "label": _(TYPE_LABELS[kind])}
        if kind == "picker":
            option["options"] = []
        elif kind == "set":
            option.update(setter_type="textbox", identifier="", key="")
        elif kind == "replace":
            option["allowed_files"] = "Images (*.png *.jpg *.heic)"
        if kind not in ("picker", "bundle_id"):
            option["files"] = []
        self.commit()
        self.template.extra.setdefault("options", [])
        if not isinstance(self.template.extra["options"], list):
            self.template.extra["options"] = []
        self.template.extra["options"].append(option)
        self._structure_changed(len(self.options) - 1)

    def _duplicate(self):
        row = self.list.currentRow()
        if 0 <= row < len(self.options):
            self.commit()
            self.options.insert(row + 1, json.loads(json.dumps(self.options[row])))
            self._structure_changed(row + 1)

    def _remove(self):
        row = self.list.currentRow()
        if 0 <= row < len(self.options):
            self.commit()
            del self.options[row]
            self._structure_changed(min(row, len(self.options) - 1))

    def _move(self, step):
        row, options = self.list.currentRow(), self.options
        if 0 <= row < len(options) and 0 <= row + step < len(options):
            self.commit()
            options[row], options[row + step] = options[row + step], options[row]
            self._structure_changed(row + step)

    def add_folder(self, folder: str = ""):
        """Copy a folder's files into the template under its own name, e.g. a
        Container folder taken from a .tendies or another template."""
        if not folder:
            folder = QFileDialog.getExistingDirectory(self, _("Add a Folder to the Template"))
            if not folder:
                return 0
        added = 0
        self.commit()
        for root, _dirs, files in os.walk(folder):
            for name in files:
                if name == ".DS_Store" or added >= MAX_FOLDER_FILES:
                    continue
                path = os.path.join(root, name)
                relative = os.path.relpath(path, os.path.dirname(os.path.normpath(folder))).replace(os.sep, "/")
                with open(path, "rb") as handle:
                    self.template.entries[relative] = handle.read()
                added += 1
        if added:
            self._show_file_count()
            self.changed.emit()
            self.commit()
        return added
