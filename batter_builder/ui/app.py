import sys

from PySide6.QtWidgets import QApplication

from .. import APP_NAME


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("GoldenNugget-Team")
    app.setStyle("Fusion")
    from PySide6.QtCore import QLibraryInfo, QLocale, QSettings, QTranslator
    from .. import i18n
    language = i18n.setup(QSettings("GoldenNugget-Team", APP_NAME).value("language", "system"))
    if language != "en":
        # Qt's own words: Yes, No, Cancel, file dialogs
        translator = QTranslator(app)
        if translator.load(QLocale(language), "qtbase", "_", QLibraryInfo.path(QLibraryInfo.TranslationsPath)):
            app.installTranslator(translator)
    from . import theme
    theme.install()
    from . import icons
    app.setWindowIcon(icons.app_icon())
    from .main_window import MainWindow   # awesomeUI controls need the theme first
    window = MainWindow()
    window.show()
    if not window.offer_recovery() and len(sys.argv) > 1:
        window.open_file(sys.argv[1])
    window.check_updates_on_start()
    sys.exit(app.exec())
