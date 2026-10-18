import sys

from PySide6.QtWidgets import QApplication

from .. import APP_NAME


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("GoldenNugget-Team")
    app.setStyle("Fusion")
    from . import theme
    theme.install()
    from .main_window import MainWindow   # awesomeUI controls need the theme first
    window = MainWindow()
    window.show()
    if len(sys.argv) > 1:
        window.open_file(sys.argv[1])
    sys.exit(app.exec())
