"""Asking GitHub for the latest release, without blocking the window."""
from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from .. import APP_NAME, RELEASES_API_URL, __version__, updates


class UpdateChecker(QObject):
    """``checked(version, url, error)``: version is "" when this one is the
    latest; error is "" unless the check failed."""
    checked = Signal(str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.network = QNetworkAccessManager(self)

    def check(self):
        request = QNetworkRequest(QUrl(RELEASES_API_URL))
        request.setRawHeader(b"Accept", b"application/vnd.github+json")
        request.setRawHeader(b"User-Agent", f"{APP_NAME.replace(' ', '')}/{__version__}".encode())
        request.setTransferTimeout(15000)
        reply = self.network.get(request)
        reply.finished.connect(lambda: self._finished(reply))

    def _finished(self, reply):
        reply.deleteLater()
        if reply.error() != QNetworkReply.NoError:
            self.handle(None, reply.errorString())
        else:
            self.handle(bytes(reply.readAll()), "")

    def handle(self, data, error):
        if error:
            self.checked.emit("", "", error)
            return
        try:
            found = updates.newer_release(data)
        except ValueError as problem:
            self.checked.emit("", "", str(problem))
            return
        self.checked.emit(*(found or ("", "")), "")
