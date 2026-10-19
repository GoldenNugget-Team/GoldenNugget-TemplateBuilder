"""Guided tour (Help → Guided Tour): the app fills in an example template by
itself while a spotlight and a bubble explain each step.

The tour works on a fresh template. Before it starts the window's template,
file path and unsaved-changes flag are kept, and when the tour ends (by
itself, with End Tour, Esc or by closing the window) they are put back, so
nothing of the example remains and nothing is written to disk. While it
runs, clicks and keys meant for the app are held back so they cannot derail
the steps; the tour's own buttons keep working.
"""
from PySide6.QtCore import QEvent, QObject, QPoint, QRect, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QApplication, QComboBox, QHBoxLayout, QLabel, QPushButton, QScrollArea,
                               QVBoxLayout, QWidget)

from . import value_table

ACCENT = "#FFB020"


class Overlay(QWidget):
    """Dims the window except the highlighted widget and shows the bubble.
    It also swallows mouse clicks meant for the app."""

    def __init__(self, parent):
        super().__init__(parent)
        self.target = None
        self.title = ""
        self.text = ""
        self.setMouseTracking(True)

    def set_step(self, title, text, target):
        self.title, self.text, self.target = title, text, target
        self.raise_()
        self.update()

    def target_rect(self):
        widget = self.target
        try:
            if widget is None or not widget.isVisible():
                return None
            top = widget.mapTo(self.parentWidget(), QPoint(0, 0))
            return QRectF(top.x() - 8, top.y() - 8, widget.width() + 16, widget.height() + 16)
        except RuntimeError:          # the app rebuilt that widget (the sidebar is rebuilt often)
            self.target = None
            return None

    def mousePressEvent(self, event):
        event.accept()

    def mouseReleaseEvent(self, event):
        event.accept()

    def mouseDoubleClickEvent(self, event):
        event.accept()

    def wheelEvent(self, event):
        event.accept()

    def paintEvent(self, _event):
        if not self.text:
            return
        p = QPainter(self)
        try:
            self._paint(p)
        finally:
            p.end()

    def _paint(self, p):
        p.setRenderHint(QPainter.Antialiasing)
        hole = self.target_rect()
        shade = QPainterPath()
        shade.addRect(QRectF(self.rect()))
        if hole is not None:
            cut = QPainterPath()
            cut.addRoundedRect(hole, 12, 12)
            shade = shade.subtracted(cut)
        p.fillPath(shade, QColor(10, 12, 20, 95))
        if hole is not None:
            p.setPen(QPen(QColor(ACCENT), 3))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(hole, 12, 12)
        width = 460
        title_font, body_font = QFont(), QFont()
        title_font.setPixelSize(17)
        title_font.setBold(True)
        body_font.setPixelSize(15)
        p.setFont(body_font)
        body = p.fontMetrics().boundingRect(QRect(0, 0, width - 40, 2000), Qt.TextWordWrap, self.text)
        height = body.height() + 70
        if hole is not None:
            x = hole.right() + 20
            if x + width > self.width() - 16:
                x = hole.left() - width - 20
            if x < 16:
                x = min(max(16, hole.center().x() - width / 2), self.width() - width - 16)
                below = hole.bottom() + 16
                y = below if below + height < self.height() - 90 else hole.top() - height - 16
            else:
                y = min(max(16, hole.center().y() - height / 2), self.height() - height - 90)
        else:
            x, y = (self.width() - width) / 2, (self.height() - height) / 2
        box = QRectF(x, max(16, y), width, height)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 60))
        p.drawRoundedRect(box.adjusted(3, 5, 3, 5), 16, 16)
        p.setBrush(QColor("#1d1f27"))
        p.setPen(QPen(QColor(ACCENT), 2))
        p.drawRoundedRect(box, 16, 16)
        p.setPen(QColor("#FFC94D"))
        p.setFont(title_font)
        p.drawText(box.adjusted(20, 16, -20, 0), Qt.AlignTop | Qt.AlignLeft, self.title)
        p.setPen(QColor("white"))
        p.setFont(body_font)
        p.drawText(box.adjusted(20, 48, -20, -16), Qt.TextWordWrap | Qt.AlignTop | Qt.AlignLeft, self.text)


class Controls(QWidget):
    """Step counter with Pause, Next and End Tour."""

    def __init__(self, parent, tour):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QWidget#tourBar {{ background: #1d1f27; border: 2px solid {ACCENT}; border-radius: 14px; }}
            QLabel {{ color: #FFC94D; font-weight: 700; font-size: 13px; background: transparent; }}
            QPushButton {{ background: #2c2f3a; color: white; border: 1px solid #4a4e5c; border-radius: 9px;
                          padding: 6px 14px; font-size: 13px; }}
            QPushButton:hover {{ border-color: {ACCENT}; }}
            QPushButton#tourNext {{ background: #F27A05; border-color: #F27A05; font-weight: 700; }}
        """)
        bar = QWidget(self)
        bar.setObjectName("tourBar")
        bar.setAttribute(Qt.WA_StyledBackground, True)
        row = QHBoxLayout(bar)
        row.setContentsMargins(14, 8, 10, 8)
        self.step = QLabel("")
        row.addWidget(self.step)
        self.pause = QPushButton("⏸ Pause")
        self.pause.clicked.connect(tour.toggle_pause)
        self.next = QPushButton("Next ▶")
        self.next.setObjectName("tourNext")
        self.next.clicked.connect(tour.skip)
        self.end = QPushButton("End Tour")
        self.end.clicked.connect(tour.finish)
        for button in (self.pause, self.next, self.end):
            button.setCursor(Qt.PointingHandCursor)
            button.setFocusPolicy(Qt.NoFocus)
            row.addWidget(button)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(bar)
        # size the buttons with the stylesheet's padding applied, not before it
        for button in (self.pause, self.next, self.end):
            button.ensurePolished()
            button.setMinimumWidth(button.sizeHint().width() + 8)
        self.adjustSize()


def scroll_to(widget):
    parent = widget.parentWidget()
    while parent is not None and not isinstance(parent, QScrollArea):
        parent = parent.parentWidget()
    if parent is not None:
        parent.ensureWidgetVisible(widget, 40, 120)


class Tour(QObject):
    """Runs the lesson as a generator that yields pauses in milliseconds."""

    def __init__(self, window, speed=1.0, on_finished=None):
        super().__init__(window)
        self.window = window
        self.speed = speed
        self.on_finished = on_finished
        self.paused = False
        self.waiting = False
        self.active = False
        self.number = 0
        self.timer = QTimer(self, singleShot=True, timeout=self.advance)
        self.saved = None

    # ----- start and end -----
    def start(self):
        from .main_window import new_template
        window = self.window
        self.saved = (window.template, window.path, window.dirty,
                      window.sidebar.current_item_id() if window.sidebar else None, window.history())
        window.load_template(new_template(), "")
        central = window.centralWidget()
        self.overlay = Overlay(central)
        self.controls = Controls(central, self)
        # children added to a shown window stay hidden until shown
        self.overlay.show()
        self.controls.show()
        central.installEventFilter(self)
        QApplication.instance().installEventFilter(self)
        self.active = True
        self.steps = self.script()
        self.place()
        QTimer.singleShot(0, self.place)     # once Qt has laid out the controls
        self.timer.start(int(400 / self.speed))

    def finish(self):
        """End the tour and put the user's template back."""
        if not self.active:
            return
        self.active = False
        self.timer.stop()
        self.steps.close()
        QApplication.instance().removeEventFilter(self)
        self.window.centralWidget().removeEventFilter(self)
        for widget in (self.overlay, self.controls):
            widget.hide()
            widget.deleteLater()
        window = self.window
        for combo in window.findChildren(QComboBox):
            combo.hidePopup()
        template, path, dirty, current, history = self.saved
        window.load_template(template, path)
        window.set_history(history)
        window.dirty = dirty
        window._update_title()
        if current and window.sidebar.item(current) is not None:
            window.sidebar.set_current(current)
        if self.on_finished:
            self.on_finished()

    def place(self):
        if not self.active:
            return
        central = self.window.centralWidget()
        self.overlay.setGeometry(central.rect())
        self.controls.layout().activate()
        self.controls.resize(self.controls.sizeHint())
        self.controls.move(central.width() - self.controls.width() - 20,
                           central.height() - self.controls.height() - 16)
        self.controls.raise_()

    def eventFilter(self, obj, event):
        if not self.active:
            return False
        kind = event.type()
        if kind == QEvent.Resize and obj is self.window.centralWidget():
            self.place()
        elif kind in (QEvent.KeyPress, QEvent.KeyRelease, QEvent.ShortcutOverride):
            if kind == QEvent.KeyPress and event.key() == Qt.Key_Escape:
                self.finish()
                return True
            # keep the user's keys away from the app while it types by itself
            if isinstance(obj, QWidget) and (obj is self.window or self.window.isAncestorOf(obj)):
                return True
        return False

    # ----- flow -----
    def advance(self):
        if not self.active:
            return
        if self.paused:
            self.waiting = True
            return
        self.waiting = False
        try:
            delay = next(self.steps)
        except StopIteration:
            self.finish()
            return
        self.overlay.update()
        self.place()
        self.timer.start(max(1, int(delay / self.speed)))

    def toggle_pause(self):
        self.paused = not self.paused
        self.controls.pause.setText("▶ Resume" if self.paused else "⏸ Pause")
        if not self.paused and (self.waiting or not self.timer.isActive()):
            self.advance()

    def skip(self):
        self.timer.stop()
        paused = self.paused
        self.paused = False
        self.advance()
        self.paused = paused

    def show(self, title, text, target=None):
        if target is not None:
            scroll_to(target)
        self.number += 1
        self.controls.step.setText(f"Step {self.number}")
        self.overlay.set_step(title, text, target)

    def say(self, title, text, target, wait):
        self.show(title, text, target)
        yield wait

    # ----- actions (generators) -----
    def type_into(self, widget, text, per_char=70):
        widget.setFocus()
        line = widget.lineEdit() if hasattr(widget, "lineEdit") else widget
        if hasattr(widget, "lineEdit"):
            line.selectAll()
            line.del_()
        else:
            line.clear()
        for ch in text:
            if hasattr(line, "insertPlainText"):
                line.insertPlainText(ch)
            else:
                line.insert(ch)
            yield per_char
        if hasattr(widget, "interpretText"):
            widget.interpretText()

    def type_item(self, item, text, per_char=70):
        for i in range(1, len(text) + 1):
            item.setText(text[:i])
            yield per_char

    def popup(self, combo, index=None, text=None, hold=1300):
        combo.showPopup()
        yield hold
        combo.hidePopup()
        if text is not None:
            combo.setCurrentText(text)
        elif index is not None:
            combo.setCurrentIndex(index)
        yield 400

    # ----- the lesson -----
    def script(self):
        window = self.window
        side = window.sidebar
        yield from self.say(
            "Welcome!", "This is Batter Builder, the editor for GoldenNugget .batter templates. Watch while it "
            "builds a template with two tweaks. Your own template is put back when the tour ends, and nothing "
            "is saved. Pause stops the tour; Esc or End Tour ends it.", None, 7000)
        yield from self.say(
            "The sidebar", "Details holds the template's information, Check and Preview runs the checks, and "
            "below are the tweaks. A red number counts the errors left to fix.", side, 6000)

        side.item("details").click()
        d = window.details
        yield from self.say("Template details",
                            "The catalog shows these: title, author, description, iOS range and tags.", d.title, 3800)
        yield from self.type_into(d.title, "Still Home Screen")
        yield 500
        self.show("Author", "Your name or handle.", d.author)
        yield from self.type_into(d.author, "your-name")
        yield 500
        self.show("Description", "What the template changes. If it writes files outside Managed Preferences, "
                  "name them here.", d.description)
        yield from self.type_into(d.description, "Stops the icon parallax and sets the Lock Screen auto-lock.", 35)
        yield 800
        self.show("iOS versions", "The first and last iOS version it works on. Empty means any.", d.min_version)
        yield from self.type_into(d.min_version, "17.0")
        yield 900
        self.show("Tags", "Comma-separated words people can find it by in the catalog.", d.tags)
        yield from self.type_into(d.tags, "home screen, lock screen")
        yield 1500

        side.item("tweak:0").click()
        e = window.editor
        yield from self.say("A tweak is a switch",
                            "Every tweak shows up in GoldenNugget as a switch. First, its label…", e.label, 3800)
        yield from self.type_into(e.label, "No Icon Parallax")
        yield 600
        self.show("Id", "The tweak's internal name. Presets remember the switch by it, so keep it once the "
                  "template is shared.", e.id)
        yield from self.type_into(e.id, "no-parallax")
        yield 900
        self.show("Tweak description", "The text under the switch in GoldenNugget.", e.description)
        yield from self.type_into(e.description, "Home Screen icons stop moving when you tilt the iPhone.", 35)
        yield 900
        yield from self.say("On by default", "Decides whether the switch starts on when someone adds the "
                            "template.", e.default, 2800)
        e.default.click()
        yield 2200

        form = e.writes.form
        yield from self.say("What to write", "Writes say what the tweak changes on the iPhone. When on holds the "
                            "writes made while the switch is on.", e.side, 5000)
        yield from self.say("Kind of write", "Plist keys (the usual one), a Whole file stored in the template, or "
                            "an Empty file.", form.type, 5000)
        yield from self.say("Path on the iPhone", "The suggestions are the Managed Preferences files GoldenNugget "
                            "itself uses; their keys merge safely with GoldenNugget's own.", form.path, 3500)
        yield from self.popup(form.path, 0)
        yield from self.say("Green means OK", "GoldenNugget can write to this path. A wrong path turns this note "
                            "red.", form.path_note, 4500)
        form.path.setEditText("/etc/hosts")
        yield from self.say("Like this one", "Outside /var/: red error. Let's put the right path back.",
                            form.path_note, 3500)
        form.path.setEditText(form.path.itemText(0))
        yield 1500
        values = form.values
        values.table.editItem = lambda _item: None
        yield from self.say("Key and value", "Add Key, then the key's name. SBDisableParallax turns the icon "
                            "parallax off.", values, 3500)
        values.add_row()
        yield from self.type_item(values.table.item(0, 0), "SBDisableParallax")
        yield 900
        yield from self.say("Value type", "Boolean true turns it on. Other types: numbers, text, arrays, or "
                            "Control value.", values.table.cellWidget(0, 1), 3000)
        yield from self.popup(values.table.cellWidget(0, 1), text=value_table.BOOLEAN)
        yield 800

        e.side._group.button(1).click()
        yield from self.say("When off", "What to write when the switch is turned off. Here: set the key back "
                            "to false.", e.side, 4500)
        e.writes._add()
        values = e.writes.form.values
        values.table.editItem = lambda _item: None
        values.add_row()
        yield from self.type_item(values.table.item(0, 0), "SBDisableParallax")
        box = values.table.cellWidget(0, 2).widget
        yield from self.say("false", "Untick it and the value becomes false.", box, 2500)
        box.setChecked(False)
        yield 2200
        e.side._group.button(0).click()
        yield 700

        yield from self.say("A second tweak", "Now a tweak with a slider. Add Tweak is at the bottom left.", None, 3500)
        window.add_tweak()
        yield 400
        window.revalidate()
        yield from self.say("The red number", "The new tweak has an error for now: its write has no key yet. "
                            "The number goes away once it is fixed.", window.sidebar.item("tweak:1"), 5000)
        e = window.editor
        self.show("Label", "The Lock Screen's auto-lock.", e.label)
        yield from self.type_into(e.label, "Lock Screen Auto-Lock")
        yield 400
        yield from self.type_into(e.id, "auto-lock")
        yield 600
        values = e.writes.form.values
        values.table.editItem = lambda _item: None
        yield from self.say("The key", "SBMinimumLockscreenIdleTime: after how many minutes the Lock Screen "
                            "turns the display off.", values, 3000)
        values.add_row()
        yield from self.type_item(values.table.item(0, 0), "SBMinimumLockscreenIdleTime", 50)
        yield 700
        combo = values.table.cellWidget(0, 1)
        yield from self.say("Control value", "With the type Control value, the value comes from the slider.",
                            combo, 2500)
        yield from self.popup(combo, text=value_table.CONTROL)
        yield 1200
        c = e.control
        yield from self.say("The control", "Choose what appears under the switch: a slider, a text box or a "
                            "choice list.", c.kind, 3500)
        c.kind._group.button(1).click()
        yield 1200
        for spin, text, title, note in (
                (c.s_min, "1", "Minimum", "The slider's smallest value."),
                (c.s_max, "10", "Maximum", "Its largest value."),
                (c.s_step, "1", "Step", "How far it moves. Whole numbers give whole-number values."),
                (c.s_default, "5", "Default", "Where the slider starts.")):
            self.show(title, note, spin)
            yield from self.type_into(spin, text, 150)
            yield 1300
        window.revalidate()
        yield from self.say("No errors left", "The red number is gone.", window.sidebar.item("tweak:1"), 3500)

        window.sidebar.item("check").click()
        chk = window.check
        yield from self.say("Check", "The same rules GoldenNugget applies when it loads a template. Ready means "
                            "it is good to go.", chk.badge, 4500)
        yield from self.say("Risk notes", "Every write gets a risk level. Keys in Managed Preferences are low "
                            "risk.", chk.problems, 5000)
        chk.preview_section.set_expanded(True)
        yield from self.say("config.json", "Exactly what is saved in the file. No JSON by hand.", chk.preview, 5500)

        save = next(b for b in window.findChildren(QPushButton) if b.text() == "Save")
        yield from self.say("Save", "Save writes the .batter file. (The tour does not save anything.)", save, 4500)
        yield from self.say("Submit to Catalog", "Checks the template, saves it as <id>.batter and opens GitHub: "
                            "drag the file in and click Propose changes. The team reviews it before it appears "
                            "in GoldenNugget's Community Catalog.", window.submit, 7500)
        yield from self.say("That's it!", "When the tour ends your own template comes back. Click End Tour "
                            "now, or wait a moment.", None, 30000)
