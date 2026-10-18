from PySide6.QtWidgets import QSizePolicy, QStackedWidget


class FitStack(QStackedWidget):
    """A stacked widget as tall as its current page, not its tallest one."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.currentChanged.connect(self._resize)

    def addWidget(self, widget):
        widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Ignored)
        return super().addWidget(widget)

    def _resize(self, _index):
        for index in range(self.count()):
            policy = QSizePolicy.Preferred if index == self.currentIndex() else QSizePolicy.Ignored
            self.widget(index).setSizePolicy(QSizePolicy.Preferred, policy)
        self.adjustSize()
        self.updateGeometry()

    def sizeHint(self):
        current = self.currentWidget()
        return current.sizeHint() if current else super().sizeHint()

    def minimumSizeHint(self):
        current = self.currentWidget()
        return current.minimumSizeHint() if current else super().minimumSizeHint()
