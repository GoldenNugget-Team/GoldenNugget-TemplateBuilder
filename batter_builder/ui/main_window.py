"""Main window: an awesomeUI sidebar with the template, its check and one
entry per tweak; the selected page on the right."""
import copy
import os
import re

from PySide6.QtCore import QEvent, QObject, QSettings, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QActionGroup, QColor, QDesktopServices, QFont, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QPlainTextEdit, QScrollArea, QStackedWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from awesomeui import EmptyState, Sidebar, StatusBadge, Toast
from awesomeui.controls import IOSCollapsibleSection, IOSPrimaryButton

from .. import APP_NAME, CATALOG_UPLOAD_URL, FORMAT_DOCS_URL, batter, rules
from ..model import Template, Tweak, Write
from . import icons, theme
from .parts import button, card, header, muted, versions_row
from .preview_page import PreviewPage
from .tweak_editor import TweakEditor

FILE_FILTER = "GoldenNugget templates (*.batter)"
LEVEL_LABELS = {rules.ERROR: "Error", rules.WARNING: "Warning", rules.INFO: "Note"}
LEVEL_ICONS = {rules.ERROR: ("error", "error"), rules.WARNING: ("warning", "warning"),
               rules.INFO: ("info", "success")}
DETAILS, CHECK, PREVIEW = "details", "check", "preview"
MAX_RECENT = 8
MAX_UNDO = 100


def slug(text: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:48]
    return value if len(value) >= 2 else "my-template"


def new_template() -> Template:
    return Template(tweaks=[new_tweak(1)])


def new_tweak(number: int) -> Tweak:
    return Tweak(id=f"tweak-{number}", label=f"Tweak {number}",
                 writes=[Write("plist", "/var/Managed Preferences/mobile/com.apple.springboard.plist", {})])


def scrolled(widget):
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setFrameShape(QScrollArea.NoFrame)
    area.setWidget(widget)
    return area


class DetailsPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.setObjectName("page")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 28, 28)
        layout.setSpacing(10)
        title = QLabel("Template")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        layout.addWidget(muted("The catalog shows the title, author, description, iOS range and tags. "
                               "Each tweak becomes a switch in GoldenNugget's PosterBoard → Templates."))
        layout.addWidget(header("Details"))
        box, form = card(form=True)
        self.title = QLineEdit()
        self.title.setPlaceholderText("Dock Tweaks")
        self.author = QLineEdit()
        self.author.setPlaceholderText("your name")
        self.description = QPlainTextEdit()
        self.description.setPlaceholderText("What the template changes. Name every file it writes outside "
                                            "Managed Preferences.")
        self.description.setFixedHeight(90)
        self.min_version, self.max_version = QLineEdit(), QLineEdit()
        self.tags = QLineEdit()
        self.tags.setPlaceholderText("dock, minimal")
        form.addRow("Title", self.title)
        form.addRow("Author", self.author)
        form.addRow("Description", self.description)
        form.addRow("iOS", versions_row(self.min_version, self.max_version))
        form.addRow("Tags", self.tags)
        layout.addWidget(box)
        for widget in (self.title, self.author, self.min_version, self.max_version, self.tags):
            widget.textChanged.connect(window._store_template)
        self.description.textChanged.connect(window._store_template)

        layout.addWidget(header("Files"))
        files, files_layout = card()
        self.files = muted("")
        files_layout.addWidget(self.files)
        self.remove_unused = button("Remove Unused Files", window.remove_unused_files, "trash")
        files_layout.addWidget(self.remove_unused, 0, Qt.AlignLeft)
        layout.addWidget(files)
        layout.addStretch()

    def show_files(self, template: Template):
        self.remove_unused.setVisible(bool(template.unused_sources()))
        if not template.entries:
            self.files.setText("No files yet. A tweak's Whole file write adds one.")
            return
        used = template.referenced_sources()
        lines = [f"{name}  ({len(data):,} bytes){'' if name in used or not name.startswith('files/') else '  — unused'}"
                 for name, data in sorted(template.entries.items())]
        self.files.setText("\n".join(lines[:40]) + ("\n…" if len(lines) > 40 else ""))


class CheckPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.setObjectName("page")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 28, 28)
        layout.setSpacing(10)
        top = QHBoxLayout()
        title = QLabel("Check")
        title.setObjectName("pageTitle")
        top.addWidget(title)
        self.badge = StatusBadge("Ready", "success")
        top.addWidget(self.badge, 0, Qt.AlignVCenter)
        top.addStretch()
        layout.addLayout(top)
        layout.addWidget(muted("The same checks GoldenNugget runs when it loads the template, plus the "
                               "risk notes its apply summary shows. Double-click a line to open the tweak."))
        layout.addWidget(header("Problems and notes"))
        box, box_layout = card()
        self.problems = QTreeWidget()
        self.problems.setHeaderLabels(["", "Where", "Problem"])
        self.problems.setRootIsDecorated(False)
        self.problems.setColumnWidth(0, 100)
        self.problems.setColumnWidth(1, 300)
        self.problems.setMinimumHeight(260)
        self.problems.itemDoubleClicked.connect(window._jump_to_problem)
        box_layout.addWidget(self.problems)
        layout.addWidget(box)
        self.preview_section = IOSCollapsibleSection("config.json", expanded=False)
        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        font = QFont("monospace")
        font.setStyleHint(QFont.Monospace)
        self.preview.setFont(font)
        self.preview.setMinimumHeight(320)
        self.preview_section.body_layout.addWidget(self.preview)
        layout.addWidget(self.preview_section)
        layout.addStretch()

    def show_issues(self, issues, config_text):
        colors = theme.ThemeHost.instance().colors
        level_colors = {rules.ERROR: colors.error, rules.WARNING: colors.warning, rules.INFO: colors.success}
        self.problems.clear()
        order = {rules.ERROR: 0, rules.WARNING: 1, rules.INFO: 2}
        for issue in sorted(issues, key=lambda i: order[i.level]):
            item = QTreeWidgetItem([LEVEL_LABELS[issue.level], issue.where, issue.text])
            item.setData(0, Qt.UserRole, issue.tweak)
            item.setForeground(0, QColor(level_colors[issue.level]))
            item.setIcon(0, icons.icon(LEVEL_ICONS[issue.level][0], LEVEL_ICONS[issue.level][1], 16))
            item.setToolTip(2, issue.text)
            self.problems.addTopLevelItem(item)
        errors = len(rules.errors(issues))
        warnings = sum(1 for issue in issues if issue.level == rules.WARNING)
        if errors:
            self.badge.setText(f"{errors} error{'s' if errors != 1 else ''}")
            self.badge.set_kind("error")
        elif warnings:
            self.badge.setText(f"Ready, {warnings} warning{'s' if warnings != 1 else ''}")
            self.badge.set_kind("warning")
        else:
            self.badge.setText("Ready")
            self.badge.set_kind("success")
        self.preview.setPlainText(config_text)


class TweakDrag(QObject):
    """Reorders tweaks by dragging their sidebar entries: a line shows where
    the tweak lands when the mouse is let go."""

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.items = []
        self.line = None
        self.source = -1
        self.start = None
        self.dragging = False

    def watch(self, sidebar, count):
        self.items = [sidebar.item(f"tweak:{index}") for index in range(count)]
        self.source, self.start, self.dragging = -1, None, False
        if not self.items:
            return
        for item in self.items:
            item.installEventFilter(self)
        self.line = QFrame(self.items[0].parentWidget())
        self.line.setFixedHeight(2)
        self.line.setStyleSheet(f"background: {theme.ThemeHost.instance().colors.accent};")
        self.line.hide()

    def _slot(self, item, pos) -> int:
        """Where the dragged tweak would go: 0 is above the first tweak."""
        y = item.mapTo(item.parentWidget(), pos).y()
        return sum(1 for other in self.items if other.y() + other.height() / 2 < y)

    def eventFilter(self, item, event):
        kind = event.type()
        if kind == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            self.source, self.start, self.dragging = self.items.index(item), event.position().toPoint(), False
        elif kind == QEvent.MouseMove and self.start is not None and event.buttons() & Qt.LeftButton:
            pos = event.position().toPoint()
            if not self.dragging and (pos - self.start).manhattanLength() >= QApplication.startDragDistance():
                self.dragging = True
                item.setCursor(Qt.ClosedHandCursor)
            if self.dragging:
                slot = self._slot(item, pos)
                last = self.items[-1]
                y = self.items[slot].y() - 1 if slot < len(self.items) else last.y() + last.height()
                self.line.setGeometry(6, y, item.parentWidget().width() - 12, 2)
                self.line.show()
                self.line.raise_()
                return True
        elif kind == QEvent.MouseButtonRelease and self.start is not None:
            dragging, source = self.dragging, self.source
            self.source, self.start, self.dragging = -1, None, False
            if dragging:
                self.line.hide()
                item.setDown(False)
                item.setCursor(Qt.PointingHandCursor)
                slot = self._slot(item, event.position().toPoint())
                # the sidebar is rebuilt, which deletes this item
                QTimer.singleShot(0, lambda: self.window.move_tweak_to(source, slot))
                return True
        return False


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("GoldenNugget-Team", APP_NAME)
        self.template = new_template()
        self.path = ""
        self.dirty = False
        self.issues = []
        self.tour = None
        self._loading = False
        self._timer = QTimer(self, singleShot=True, interval=200, timeout=self.revalidate)
        self._drag = TweakDrag(self)
        # Undo keeps copies of the whole template. Changes that come in quick
        # succession (typing) become one step when the edits pause.
        self._undo, self._redo = [], []
        self._snapshot = self._saved = None
        self._history_timer = QTimer(self, singleShot=True, interval=700, timeout=self._commit)
        self._build_menu()
        self._build_ui()
        self.resize(1320, 900)
        self.setAcceptDrops(True)
        self.load_template(self.template, "")

    # ----- layout -----
    def _build_menu(self):
        menu = self.menuBar().addMenu("&File")
        for text, shortcut, handler, name in (
                ("New", QKeySequence.New, self.new_file, "details"),
                ("Open…", QKeySequence.Open, self.open_file, "open"),
                ("Save", QKeySequence.Save, self.save_file, "save"),
                ("Save As…", QKeySequence.SaveAs, self.save_as, None)):
            action = QAction(text, self, shortcut=shortcut, triggered=handler)
            if name:
                action.setIcon(icons.icon(name))
            menu.addAction(action)
            if text == "Open…":
                self.recent_menu = menu.addMenu("Open Recent")
                self.recent_menu.aboutToShow.connect(self._fill_recent)
        menu.addSeparator()
        menu.addAction(QAction("Quit", self, shortcut=QKeySequence.Quit, triggered=self.close))
        edit = self.menuBar().addMenu("&Edit")
        self.undo_action = QAction("Undo", self, shortcut=QKeySequence.Undo, triggered=self.undo, enabled=False)
        self.redo_action = QAction("Redo", self, shortcut=QKeySequence.Redo, triggered=self.redo, enabled=False)
        edit.addAction(self.undo_action)
        edit.addAction(self.redo_action)
        tweak_menu = self.menuBar().addMenu("&Tweak")
        for text, shortcut, handler, name in (
                ("Add Tweak", "Ctrl+T", self.add_tweak, "plus"),
                ("Duplicate Tweak", "Ctrl+D", self.duplicate_tweak, "copy"),
                ("Move Up", "Alt+Up", lambda: self.move_tweak(-1), "up"),
                ("Move Down", "Alt+Down", lambda: self.move_tweak(1), "down"),
                ("Remove Tweak…", "Ctrl+Shift+Backspace", self.remove_tweak, "trash")):
            tweak_menu.addAction(QAction(icons.icon(name), text, self, shortcut=QKeySequence(shortcut),
                                         triggered=handler))
        view = self.menuBar().addMenu("&View")
        appearance = view.addMenu("Appearance")
        group = QActionGroup(self)
        for mode, text in (("system", "Same as System"), ("light", "Light"), ("dark", "Dark")):
            action = QAction(text, self, checkable=True, checked=theme.ThemeHost.instance().mode == mode)
            action.triggered.connect(lambda _checked, m=mode: theme.ThemeHost.instance().set_mode(m))
            group.addAction(action)
            appearance.addAction(action)
        theme.ThemeHost.instance().changed.connect(self._retheme)
        catalog = self.menuBar().addMenu("&Catalog")
        catalog.addAction(QAction(icons.icon("upload"), "Submit to Catalog…", self,
                                  triggered=self.submit_to_catalog))
        help_menu = self.menuBar().addMenu("&Help")
        help_menu.addAction(QAction(icons.icon("toggle"), "Guided Tour", self, triggered=lambda: self.start_tour()))
        help_menu.addAction(QAction(icons.icon("help"), "Template Format Guide", self,
                                    triggered=lambda: QDesktopServices.openUrl(QUrl(FORMAT_DOCS_URL))))
        help_menu.addAction(QAction("About", self, triggered=self.about))

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("page")
        row = QHBoxLayout(central)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        self.sidebar_slot = QVBoxLayout()
        self.sidebar_slot.setContentsMargins(0, 0, 0, 0)
        row.addLayout(self.sidebar_slot)
        self.sidebar = None

        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)
        bar = QWidget()
        bar.setObjectName("page")
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(28, 14, 28, 6)
        self.file_label = muted("")
        bar_layout.addWidget(self.file_label, 1)
        bar_layout.addWidget(button("Open…", self.open_file, "open"))
        bar_layout.addWidget(button("Save", self.save_file, "save"))
        self.submit = IOSPrimaryButton("Submit to Catalog")
        icons.attach(self.submit, "upload", "text_inverse", 18)
        self.submit.setFixedHeight(38)
        self.submit.clicked.connect(self.submit_to_catalog)
        bar_layout.addWidget(self.submit)
        right.addWidget(bar)

        self.details = DetailsPage(self)
        self.check = CheckPage(self)
        self.editor = TweakEditor()
        self.editor.changed.connect(self.mark_dirty)
        self.editor.renamed.connect(self._refresh_tweak_labels)
        self.editor.removeRequested.connect(self.remove_tweak)
        self.editor.duplicateRequested.connect(self.duplicate_tweak)
        self.editor.moveRequested.connect(self.move_tweak)
        self.empty = EmptyState("No tweaks yet", "A tweak is a switch in GoldenNugget that writes plist keys "
                                "or files on the iPhone.", "Add Tweak")
        self.empty.actionRequested.connect(self.add_tweak)
        self.pages = QStackedWidget()
        for page in (self.details, self.check, self.editor):
            self.pages.addWidget(scrolled(page))
        self.pages.addWidget(self.empty)
        self.preview = PreviewPage()
        self.pages.addWidget(scrolled(self.preview))
        right.addWidget(self.pages, 1)
        row.addLayout(right, 1)
        self.setCentralWidget(central)

    def _build_sidebar(self, current=DETAILS):
        if self.sidebar is not None:
            self.sidebar_slot.removeWidget(self.sidebar)
            self.sidebar.deleteLater()
        sidebar = Sidebar(theme=theme.sidebar_theme(), collapsible=False)
        sidebar.add_section("Template")
        sidebar.add_item(DETAILS, "Details", icons.icon("details", "text_secondary"))
        sidebar.add_item(CHECK, "Check and Preview", icons.icon("check", "text_secondary"))
        sidebar.add_item(PREVIEW, "iPhone Preview", icons.icon("mobile", "text_secondary"))
        sidebar.add_section("Tweaks")
        for index, tweak in enumerate(self.template.tweaks):
            sidebar.add_item(f"tweak:{index}", tweak.label or tweak.id or "(no label)",
                             icons.icon("toggle", "text_secondary"))
        add = button("Add Tweak", self.add_tweak, "plus")
        sidebar.add_footer_widget(add)
        sidebar.currentChanged.connect(self._open_page)
        self._drag.watch(sidebar, len(self.template.tweaks))
        self.sidebar = sidebar
        self.sidebar_slot.addWidget(sidebar)
        if sidebar.item(current) is None:
            current = DETAILS
        sidebar.set_current(current)
        self._update_badges()

    def _retheme(self):
        # The sidebar takes its colors when it is built.
        self._build_sidebar(self.sidebar.current_item_id() or DETAILS)
        self.revalidate()

    def _open_page(self, item_id):
        if item_id == DETAILS:
            self.details.show_files(self.template)
            self.pages.setCurrentIndex(0)
        elif item_id == CHECK:
            self.revalidate()
            self.pages.setCurrentIndex(1)
        elif item_id == PREVIEW:
            self.preview.show_template(self.template)
            self.pages.setCurrentIndex(4)
        else:
            index = int(item_id.split(":")[1])
            self.editor.edit(self.template, self.template.tweaks[index])
            self.pages.setCurrentIndex(2)
            self.pages.widget(2).verticalScrollBar().setValue(0)

    def current_tweak(self) -> int:
        item_id = self.sidebar.current_item_id() if self.sidebar else None
        return int(item_id.split(":")[1]) if item_id and item_id.startswith("tweak:") else -1

    # ----- template state -----
    def load_template(self, template: Template, path: str):
        self.template, self.path = template, path
        self._show_details()
        self._build_sidebar("tweak:0" if template.tweaks and not path else DETAILS)
        self.dirty = False
        self.set_history(([], [], copy.deepcopy(template), self._state(template)))
        self.revalidate()

    def _show_details(self):
        template = self.template
        self._loading = True
        details = self.details
        details.title.setText(template.title)
        details.author.setText(template.author)
        details.description.setPlainText(template.description)
        details.min_version.setText(template.min_version)
        details.max_version.setText(template.max_version)
        details.tags.setText(", ".join(template.tags))
        self._loading = False

    def _store_template(self, *_):
        if self._loading:
            return
        details, template = self.details, self.template
        template.title = details.title.text().strip()
        template.author = details.author.text().strip()
        template.description = details.description.toPlainText().strip()
        template.min_version = details.min_version.text().strip()
        template.max_version = details.max_version.text().strip()
        template.tags = [tag.strip() for tag in details.tags.text().split(",") if tag.strip()]
        self.mark_dirty()

    def mark_dirty(self):
        self.dirty = True
        self._timer.start()
        self._history_timer.start()
        self._update_undo_actions()
        self._update_title()

    def _update_title(self):
        name = os.path.basename(self.path) if self.path else "Untitled"
        self.setWindowTitle(f"{name}{' •' if self.dirty else ''} — {APP_NAME}")
        self.file_label.setText(self.path or "Not saved yet")

    def revalidate(self):
        self.issues = rules.validate(self.template)
        index = self.current_tweak()
        if index >= 0:
            for problem in self.editor.editor_errors():
                self.issues.insert(0, rules.Issue(rules.ERROR, f"Tweak {index + 1}", problem, index))
        self.check.show_issues(self.issues, batter.dumps_config(self.template))
        self._update_badges()
        self._update_title()

    def _update_badges(self):
        if self.sidebar is None:
            return
        errors = rules.errors(self.issues)
        self._set_badge(CHECK, str(len(errors)) if errors else "")
        for index in range(len(self.template.tweaks)):
            count = sum(1 for issue in errors if issue.tweak == index)
            self._set_badge(f"tweak:{index}", str(count) if count else "")

    def _set_badge(self, item_id, text):
        """An error count on a sidebar entry: a red pill at the sidebar's
        right edge. awesomeUI's own badge sits inside the entry, which is only
        as wide as its text, so this one lives on the sidebar's content."""
        item = self.sidebar.item(item_id)
        if item is None:
            return
        badges = self.sidebar.__dict__.setdefault("_error_badges", {})
        badge = badges.get(item_id)
        if not text:
            if badge is not None:
                badge.hide()
            return
        if badge is None:
            badge = QLabel(item.parentWidget())
            badge.setAlignment(Qt.AlignCenter)
            badges[item_id] = badge
        badge.setStyleSheet(f"color: white; background: {theme.ThemeHost.instance().colors.error}; "
                            "border-radius: 9px; padding: 0px 7px; font-size: 11px; font-weight: 700;")
        badge.setText(text)
        badge.setFixedHeight(18)
        badge.adjustSize()
        badge.setMinimumWidth(18)
        badge.show()
        badge.raise_()

        def place():
            try:
                parent = item.parentWidget()
                badge.move(parent.width() - badge.width() - 8,
                           item.y() + (item.height() - badge.height()) // 2)
            except RuntimeError:     # the sidebar was rebuilt meanwhile
                pass
        place()
        QTimer.singleShot(0, place)

    def _jump_to_problem(self, item):
        index = item.data(0, Qt.UserRole)
        if isinstance(index, int) and 0 <= index < len(self.template.tweaks):
            self.sidebar.set_current(f"tweak:{index}")

    # ----- undo -----
    @staticmethod
    def _state(template: Template):
        return template.to_config(), dict(template.entries)

    def history(self):
        return self._undo, self._redo, self._snapshot, self._saved

    def set_history(self, history):
        self._undo, self._redo, self._snapshot, self._saved = history
        self._history_timer.stop()
        self._update_undo_actions()

    def _commit(self):
        """Make the changes since the last step one undo step."""
        self._history_timer.stop()
        if self._snapshot is None or self._state(self.template) == self._state(self._snapshot):
            return
        self._undo.append(self._snapshot)
        del self._undo[:-MAX_UNDO]
        self._redo.clear()
        self._snapshot = copy.deepcopy(self.template)
        self._update_undo_actions()

    def _update_undo_actions(self):
        self.undo_action.setEnabled(bool(self._undo) or self._history_timer.isActive())
        self.redo_action.setEnabled(bool(self._redo))

    def _tour_running(self) -> bool:
        return self.tour is not None and self.tour.active

    def undo(self):
        if self._tour_running():
            return
        self._commit()
        if self._undo:
            self._redo.append(self._snapshot)
            self._restore(self._undo.pop())

    def redo(self):
        if self._tour_running():
            return
        self._commit()
        if self._redo:
            self._undo.append(self._snapshot)
            self._restore(self._redo.pop())

    @staticmethod
    def _changed_page(before: Template, after: Template, current: str) -> str:
        """The page that shows what an undo or redo changed."""
        head = lambda t: {k: v for k, v in t.to_config().items() if k != "tweaks"}
        if head(before) != head(after):
            return DETAILS
        old = [tweak.to_config() for tweak in before.tweaks]
        new = [tweak.to_config() for tweak in after.tweaks]
        for index in range(max(len(old), len(new))):
            if old[index:index + 1] != new[index:index + 1]:
                return f"tweak:{min(index, len(new) - 1)}" if new else DETAILS
        return current

    def _restore(self, snapshot: Template):
        current = self._changed_page(self.template, snapshot, self.sidebar.current_item_id() or DETAILS)
        self.template = copy.deepcopy(snapshot)
        self._show_details()
        self._build_sidebar(current)
        if not self.template.tweaks and current.startswith("tweak:"):
            self.pages.setCurrentWidget(self.empty)
        # the pages may tidy values while they show them; that is not a step
        self._snapshot = copy.deepcopy(self.template)
        self._history_timer.stop()
        self.dirty = self._state(self.template) != self._saved
        self._update_undo_actions()
        self.revalidate()

    # ----- tweaks -----
    def _refresh_tweak_labels(self):
        for index, tweak in enumerate(self.template.tweaks):
            item = self.sidebar.item(f"tweak:{index}")
            if item is not None:
                item.set_label(tweak.label or tweak.id or "(no label)")

    def _after_list_change(self, select):
        self._commit()
        self._build_sidebar(f"tweak:{select}" if 0 <= select < len(self.template.tweaks) else DETAILS)
        if not self.template.tweaks:
            self.pages.setCurrentWidget(self.empty)
        self.mark_dirty()

    def add_tweak(self):
        self._commit()
        used = {tweak.id for tweak in self.template.tweaks}
        number = len(self.template.tweaks) + 1
        while f"tweak-{number}" in used:
            number += 1
        self.template.tweaks.append(new_tweak(number))
        self._after_list_change(len(self.template.tweaks) - 1)

    def duplicate_tweak(self):
        self._commit()
        row = self.current_tweak()
        if row < 0:
            return
        clone = copy.deepcopy(self.template.tweaks[row])
        used = {tweak.id for tweak in self.template.tweaks}
        base, number = clone.id or "tweak", 2
        while f"{base}-{number}" in used:
            number += 1
        clone.id = f"{base}-{number}"[:64]
        clone.label = f"{clone.label} (copy)"[:80]
        self.template.tweaks.insert(row + 1, clone)
        self._after_list_change(row + 1)

    def remove_tweak(self):
        self._commit()
        row = self.current_tweak()
        if row < 0:
            return
        label = self.template.tweaks[row].label or "this tweak"
        if QMessageBox.question(self, "Remove Tweak", f"Remove {label}?") != QMessageBox.Yes:
            return
        del self.template.tweaks[row]
        self._after_list_change(min(row, len(self.template.tweaks) - 1))

    def move_tweak_to(self, source, slot):
        """Move tweak ``source`` to ``slot``, a gap between tweaks (0 is
        before the first)."""
        tweaks = self.template.tweaks
        target = slot - 1 if slot > source else slot
        if not 0 <= source < len(tweaks) or target == source:
            return
        self._commit()
        tweaks.insert(target, tweaks.pop(source))
        self._after_list_change(target)

    def move_tweak(self, step):
        self._commit()
        row = self.current_tweak()
        target = row + step
        tweaks = self.template.tweaks
        if 0 <= row < len(tweaks) and 0 <= target < len(tweaks):
            tweaks[row], tweaks[target] = tweaks[target], tweaks[row]
            self._after_list_change(target)

    def remove_unused_files(self):
        unused = self.template.unused_sources()
        if not unused:
            return
        self._commit()
        for name in unused:
            del self.template.entries[name]
        self.details.show_files(self.template)
        self.mark_dirty()
        self._commit()
        Toast.show_message(self, f"Removed {len(unused)} unused file{'s' if len(unused) != 1 else ''}")

    # ----- files -----
    def _confirm_discard(self) -> bool:
        if not self.dirty:
            return True
        answer = QMessageBox.question(
            self, "Unsaved Changes", "Save the changes to this template first?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        if answer == QMessageBox.Save:
            return self.save_file()
        return answer == QMessageBox.Discard

    def _folder(self) -> str:
        return os.path.dirname(self.path) if self.path else self.settings.value("folder", os.path.expanduser("~"))

    def _end_tour(self):
        # Opening a file mid-tour would be undone when the tour puts the
        # user's template back.
        if self._tour_running():
            self.tour.finish()

    def recent_files(self) -> list:
        value = self.settings.value("recent", [])
        return [value] if isinstance(value, str) else list(value or [])

    def _remember(self, path):
        path = os.path.abspath(path)
        recent = [p for p in self.recent_files() if p != path]
        self.settings.setValue("recent", [path] + recent[:MAX_RECENT - 1])

    def _fill_recent(self):
        self.recent_menu.clear()
        recent = self.recent_files()
        for path in recent:
            action = self.recent_menu.addAction(os.path.basename(path))
            action.setToolTip(path)
            action.setStatusTip(path)
            action.triggered.connect(lambda _checked=False, p=path: self.open_recent(p))
        if recent:
            self.recent_menu.addSeparator()
            self.recent_menu.addAction("Clear Menu", lambda: self.settings.setValue("recent", []))
        else:
            self.recent_menu.addAction("No recent templates").setEnabled(False)

    def open_recent(self, path):
        self._end_tour()
        if not self._confirm_discard():
            return
        if not os.path.exists(path):
            self.settings.setValue("recent", [p for p in self.recent_files() if p != path])
            QMessageBox.warning(self, "Cannot Open", f"{path} no longer exists.")
            return
        self.open_file(path)

    def dragEnterEvent(self, event):
        if self._dropped_template(event):
            event.acceptProposedAction()

    def dropEvent(self, event):
        path = self._dropped_template(event)
        if path:
            event.acceptProposedAction()
            self._end_tour()
            if self._confirm_discard():
                self.open_file(path)

    @staticmethod
    def _dropped_template(event) -> str:
        urls = event.mimeData().urls() if event.mimeData().hasUrls() else []
        if len(urls) == 1 and urls[0].isLocalFile() and urls[0].toLocalFile().lower().endswith(".batter"):
            return urls[0].toLocalFile()
        return ""

    def new_file(self):
        self._end_tour()
        if self._confirm_discard():
            self.load_template(new_template(), "")

    def open_file(self, path: str = ""):
        if not path:
            self._end_tour()
            if not self._confirm_discard():
                return
            path, _ = QFileDialog.getOpenFileName(self, "Open Template", self._folder(), FILE_FILTER)
            if not path:
                return
        try:
            template = batter.load(path)
        except batter.BatterError as error:
            QMessageBox.warning(self, "Cannot Open", str(error))
            return
        self.settings.setValue("folder", os.path.dirname(path))
        self._remember(path)
        self.load_template(template, path)

    def _confirm_errors(self) -> bool:
        """Saving a template GoldenNugget would refuse is allowed, after a
        warning: it may be work in progress."""
        self.revalidate()
        found = rules.errors(self.issues)
        if not found:
            return True
        box = QMessageBox(QMessageBox.Warning, "Save Template",
                          f"The template has {len(found)} error{'s' if len(found) != 1 else ''}. "
                          "GoldenNugget refuses to load it until they are fixed.", parent=self)
        save = box.addButton("Save Anyway", QMessageBox.AcceptRole)
        show = box.addButton("Show Problems", QMessageBox.ActionRole)
        box.addButton(QMessageBox.Cancel)
        box.setDefaultButton(save)
        box.exec()
        if box.clickedButton() is show:
            self.sidebar.set_current(CHECK)
        return box.clickedButton() is save

    def save_file(self) -> bool:
        self._end_tour()      # the tour's example is never saved
        if not self._confirm_errors():
            return False
        return self._write(self.path) if self.path else self._save_as()

    def save_as(self) -> bool:
        self._end_tour()
        return self._confirm_errors() and self._save_as()

    def _save_as(self) -> bool:
        name = os.path.basename(self.path) if self.path else slug(self.template.title) + ".batter"
        path, _ = QFileDialog.getSaveFileName(self, "Save Template", os.path.join(self._folder(), name),
                                              FILE_FILTER)
        if not path:
            return False
        if not path.endswith(".batter"):
            path += ".batter"
        return self._write(path)

    def _write(self, path) -> bool:
        try:
            batter.save(self.template, path)
        except OSError as error:
            QMessageBox.warning(self, "Cannot Save", str(error))
            return False
        self.path = path
        self.dirty = False
        self._saved = self._state(self.template)
        self.settings.setValue("folder", os.path.dirname(path))
        self._remember(path)
        self._update_title()
        if self.isVisible():
            Toast.show_message(self, f"Saved {os.path.basename(path)}")
        return True

    def submit_to_catalog(self):
        self._end_tour()
        self.revalidate()
        found = rules.errors(self.issues)
        if found:
            self.sidebar.set_current(CHECK)
            QMessageBox.warning(self, "Submit to Catalog",
                                f"Fix the {len(found)} error(s) on the Check page first. "
                                "GoldenNugget would refuse this template.")
            return
        name, ok = QInputDialog.getText(
            self, "Submit to Catalog", "Catalog id (the file name: lowercase letters, digits and dashes):",
            text=slug(self.template.title))
        if not ok:
            return
        name = name.strip()
        if not rules.CATALOG_ID_PATTERN.match(name):
            QMessageBox.warning(self, "Submit to Catalog",
                                "Use 2–48 lowercase letters, digits and dashes, for example dock-tweaks.")
            return
        folder = QFileDialog.getExistingDirectory(self, "Where to save the file to upload", self._folder())
        if not folder:
            return
        target = os.path.join(folder, name + ".batter")
        if os.path.exists(target) and os.path.abspath(target) != os.path.abspath(self.path) \
                and QMessageBox.question(self, "Submit to Catalog", f"{target} exists. Replace it?") != QMessageBox.Yes:
            return
        data = batter.dumps(self.template)
        if len(data) > rules.MAX_TEMPLATE_BYTES:
            QMessageBox.warning(self, "Submit to Catalog", "The catalog accepts templates of at most 25 MB; "
                                f"this one is {len(data) / 1024 / 1024:.1f} MB.")
            return
        try:
            batter.save(self.template, target, data)
        except OSError as error:
            QMessageBox.warning(self, "Cannot Save", str(error))
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
        QDesktopServices.openUrl(QUrl(CATALOG_UPLOAD_URL))
        QMessageBox.information(
            self, "Submit to Catalog",
            f"Saved {name}.batter and opened GitHub.\n\n"
            "1. Drag the file onto the GitHub page.\n"
            "2. Click Propose changes, then Create pull request.\n\n"
            "GitHub makes a copy (fork) of the catalog for you if you need one. A check lists every "
            "file your tweaks write, and the team reviews it before it appears in GoldenNugget.")

    def about(self):
        from .. import __version__
        QMessageBox.about(self, APP_NAME,
                          f"{APP_NAME} {__version__}\n\nBuilds GoldenNugget .batter templates with "
                          "community tweaks (format 3) and checks them with GoldenNugget's rules.\n\n"
                          "Controls: awesomeUI.")

    def start_tour(self, speed=1.0):
        """Run the guided tour on an example template; the current template
        comes back when it ends."""
        if self.tour is not None and self.tour.active:
            return self.tour
        from .tour import Tour
        self.tour = Tour(self, speed)
        self.tour.start()
        return self.tour

    def closeEvent(self, event):
        if self.tour is not None and self.tour.active:
            self.tour.finish()
        if self._confirm_discard():
            event.accept()
        else:
            event.ignore()
