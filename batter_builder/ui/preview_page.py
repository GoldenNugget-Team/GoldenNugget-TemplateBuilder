"""A rough picture of how GoldenNugget lists the template on an iPhone, with
working switches and controls, next to what GoldenNugget would write."""
import json

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath
from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QScrollArea, QSlider,
    QVBoxLayout, QWidget,
)

from awesomeui.controls import IOSSwitch

from .. import preview
from ..i18n import _
from ..model import Template, Tweak
from . import theme
from .parts import card, header, muted

SCREEN = {False: ("#F2F2F7", "#FFFFFF", "#000000", "#6C6C70"),     # background, card, text, secondary
          True: ("#000000", "#1C1C1E", "#FFFFFF", "#8E8E93")}


class PhoneShell(QWidget):
    """An iPhone outline; its layout holds the screen's contents."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(340, 700)
        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(22, 58, 22, 26)

    def paintEvent(self, _event):
        dark = theme.ThemeHost.instance().is_dark
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        outer = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(outer, 54, 54)
        painter.fillPath(path, QColor("#1C1C1E"))
        painter.setPen(QColor("#3A3A3C"))
        painter.drawPath(path)
        screen = QPainterPath()
        screen.addRoundedRect(outer.adjusted(11, 11, -11, -11), 44, 44)
        painter.fillPath(screen, QColor(SCREEN[dark][0]))
        island = QPainterPath()
        island.addRoundedRect(QRectF(self.width() / 2 - 48, 22, 96, 28), 14, 14)
        painter.fillPath(island, QColor("#000000"))
        painter.setPen(QColor(SCREEN[dark][2]))
        font = QFont(self.font())
        font.setPointSizeF(10.5)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRectF(40, 24, 80, 24), Qt.AlignCenter, "9:41")


class TweakRow(QFrame):
    """One tweak as a card: switch, description and control."""

    def __init__(self, tweak: Tweak, on_change):
        super().__init__()
        self.tweak = tweak
        self.on_change = on_change
        self.setObjectName("phoneCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 12)
        layout.setSpacing(4)
        top = QHBoxLayout()
        label = QLabel(tweak.label or tweak.id or _("(no label)"))
        label.setWordWrap(True)
        label.setObjectName("phoneLabel")
        top.addWidget(label, 1)
        self.switch = IOSSwitch()
        self.switch.setChecked(tweak.default)
        self.switch.toggled.connect(self._changed)
        top.addWidget(self.switch, 0, Qt.AlignVCenter)
        layout.addLayout(top)
        if tweak.description:
            note = QLabel(tweak.description)
            note.setWordWrap(True)
            note.setObjectName("phoneNote")
            layout.addWidget(note)
        self.control = self._control_widget(tweak.control)
        if self.control is not None:
            layout.addWidget(self.control)
        self._changed()

    def _control_widget(self, control):
        self.value = preview.default_value(control)
        if control is None:
            return None
        box = QWidget()
        row = QHBoxLayout(box)
        row.setContentsMargins(0, 4, 0, 0)
        if control.type == "slider":
            steps = preview.slider_steps(control)
            slider = QSlider(Qt.Horizontal)
            shown = QLabel()
            shown.setObjectName("phoneNote")
            shown.setMinimumWidth(44)
            shown.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if steps < 0:
                slider.setEnabled(False)
                shown.setText("?")
            else:
                slider.setRange(0, steps)
                default = control.default if isinstance(control.default, (int, float)) else control.min
                slider.setValue(int(round((min(max(default, control.min), control.max) - control.min)
                                          / control.step)))

                def moved(position):
                    self.value = preview.slider_value(control, position)
                    shown.setText(f"{self.value:g}")
                    self.on_change()
                slider.valueChanged.connect(moved)
                self.value = preview.slider_value(control, slider.value())
                shown.setText(f"{self.value:g}")
            row.addWidget(slider, 1)
            row.addWidget(shown)
        elif control.type == "text":
            field = QLineEdit(control.default if isinstance(control.default, str) else "")
            if isinstance(control.max_length, int) and control.max_length > 0:
                field.setMaxLength(control.max_length)
            self.value = field.text()

            def typed(text):
                self.value = text
                self.on_change()
            field.textChanged.connect(typed)
            row.addWidget(field)
        else:
            combo = QComboBox()
            for choice in control.choices:
                combo.addItem(choice.label or _("(no label)"))
            if isinstance(control.default, int) and 0 <= control.default < combo.count():
                combo.setCurrentIndex(control.default)

            def picked(index):
                self.value = control.choices[index].value if 0 <= index < len(control.choices) else None
                self.on_change()
            combo.currentIndexChanged.connect(picked)
            row.addWidget(combo, 1)
        return box

    def _changed(self, *_args):
        if self.control is not None:
            self.control.setVisible(self.switch.isChecked())
        self.on_change()


class PreviewPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("page")
        self.template = Template()
        self.rows = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 28, 28)
        layout.setSpacing(10)
        title = QLabel(_("iPhone Preview"))
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        layout.addWidget(muted(_("Roughly how GoldenNugget lists the template. Try the switches and controls: "
                                 "the right side shows what GoldenNugget would write. Nothing here changes "
                                 "the template.")))
        row = QHBoxLayout()
        row.setSpacing(24)
        self.phone = PhoneShell()
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.phone.layout_.addWidget(self.scroll)
        row.addWidget(self.phone, 0, Qt.AlignTop)
        right = QVBoxLayout()
        right.addWidget(header(_("What GoldenNugget writes")))
        box, box_layout = card()
        self.writes = QPlainTextEdit()
        self.writes.setReadOnly(True)
        font = QFont("monospace")
        font.setStyleHint(QFont.Monospace)
        self.writes.setFont(font)
        self.writes.setMinimumHeight(560)
        box_layout.addWidget(self.writes)
        right.addWidget(box)
        right.addStretch()
        row.addLayout(right, 1)
        layout.addLayout(row)
        layout.addStretch()

    def show_template(self, template: Template):
        dark = theme.ThemeHost.instance().is_dark
        background, card_color, text, secondary = SCREEN[dark]
        content = QWidget()
        content.setObjectName("phoneScreen")
        content.setStyleSheet(f"""
            #phoneScreen {{ background: {background}; }}
            #phoneScreen QLabel {{ background: transparent; color: {text}; }}
            #phoneScreen QLabel#phoneNote, #phoneScreen QLabel#phoneBy {{ color: {secondary}; font-size: 12px; }}
            #phoneScreen QLabel#phoneTitle {{ font-size: 24px; font-weight: 700; }}
            #phoneScreen QLabel#phoneLabel {{ font-size: 15px; }}
            #phoneScreen QFrame#phoneCard {{ background: {card_color}; border-radius: 12px; }}
        """)
        self.scroll.setStyleSheet(f"QScrollArea {{ background: {background}; border: none; }}")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(4, 0, 4, 12)
        layout.setSpacing(10)
        title = QLabel(template.title or _("Untitled template"))
        title.setObjectName("phoneTitle")
        title.setWordWrap(True)
        layout.addWidget(title)
        if template.author:
            by = QLabel(_("by {author}").format(author=template.author))
            by.setObjectName("phoneBy")
            layout.addWidget(by)
        if template.description:
            about = QLabel(template.description)
            about.setObjectName("phoneNote")
            about.setWordWrap(True)
            layout.addWidget(about)
        self.template, self.rows = template, []
        for tweak in template.tweaks:
            row = TweakRow(tweak, self._update_writes)
            self.rows.append(row)
            layout.addWidget(row)
        if not template.tweaks:
            empty = QLabel(_("No tweaks yet."))
            empty.setObjectName("phoneNote")
            layout.addWidget(empty)
        layout.addStretch()
        self.scroll.setWidget(content)
        self._update_writes()

    def _update_writes(self):
        if len(self.rows) != len(self.template.tweaks):
            return      # still building
        self.writes.setPlainText(describe(self.template, self.rows))


def _format(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def describe(template: Template, rows) -> str:
    lines = []
    for tweak, row in zip(template.tweaks, rows):
        on = row.switch.isChecked()
        name = tweak.label or tweak.id or _("(no label)")
        state = _("on") if on else _("off")
        if on and tweak.control is not None:
            state += ", " + _("value {value}").format(value=_format(row.value))
        lines.append(f"{'●' if on else '○'} {name} ({state})")
        writes = preview.writes_for(tweak, on, row.value)
        if not writes:
            lines.append("    " + (_("nothing is written") if not on else _("no writes")))
        for write in writes:
            owner = "" if write.owner == 501 else "  (" + _("owner {owner}").format(owner=write.owner) + ")"
            lines.append(f"    {write.path or _('(no path)')}{owner}")
            if write.type == "plist":
                for key, value in write.values.items():
                    lines.append(f"      {key} = {_format(value)}")
            elif write.type == "file":
                size = len(template.entries.get(write.source, b""))
                lines.append("      " + _("whole file ← {name}").format(name=write.source or _("(no file)"))
                             + " (" + _("{size} bytes").format(size=f"{size:,}") + ")")
            else:
                lines.append("      " + _("empty file"))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n" if lines else _("No tweaks yet.") + "\n"
