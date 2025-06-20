import os
import sys
import ibrowse
from PyQt6.QtCore import QUrl, QTimer, QCoreApplication, QProcess, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QMainWindow, QApplication, QMessageBox
from src.gui.tab import Tab
from src.gui.tab_view import TabView
from src.gui.web_engine import WebEngineProfile


if getattr(sys, 'frozen', False):
    os.chdir(sys._MEIPASS)


class Ibrowse(QMainWindow):
    def __init__(self, profile=None):
        super().__init__()
        self.setWindowTitle('Ibrowse')
        self.setWindowIcon(QIcon('resources/icons/logos/ibrowse_icon.svg'))
        self.resize(1000, 800)

        if profile:
            self._profile = profile

        else:
            self._profile = WebEngineProfile('PersistentProfile', self)
            self._profile.setCachePath(ibrowse.cache_dir())

        self.createUI()

    def closeEvent(self, event):
        if self.tab_view.count() > 0:
            tabs = []

            for i in range(self.tab_view.count()):
                tab = self.tab_view.widget(i)
                tabs.append(tab.activeUrl().toString())

            ibrowse.set_previous_tabs(tabs)
            ibrowse.set_preferred_browser(self.tab_view.currentWidget().engineCombo().currentText())

        else:
            ibrowse.set_previous_tabs([])

        super().closeEvent(event)

    def createUI(self):
        self.tab_view = TabView(self)

        self.setCentralWidget(self.tab_view)

    def loadTabs(self):
        if len(ibrowse.previous_tabs()) > 0:
            for url in ibrowse.previous_tabs():
                if not url.startswith('https'):
                    continue

                tab = Tab(self.tab_view, self._profile, url=url, parent=self)
                self.tab_view.addTab(tab, '')

            return

        self.loadDefaultTab()

    def loadDefaultTab(self):
        self.tab_view.addTab(
            Tab(self.tab_view, self._profile, parent=self).fromHtml('resources/pages/startup.html'),
            'Welcome'
        )

    def openFromArg(self, arg: str):
        if os.path.exists(arg):
            try:
                tab = Tab(self.tab_view, self._profile, parent=self).fromHtml(arg)

                self.tab_view.addTab(tab, 'File')
                self.tab_view.setCurrentWidget(tab)

            except:
                return

        else:
            tab = Tab(self.tab_view, self._profile, url=arg, parent=self)

            self.tab_view.addTab(tab, '')
            self.tab_view.setCurrentWidget(tab)

    def newWindow(self, start_editing=True):
        window = Ibrowse(self._profile)
        window.show()
        window.loadDefaultTab()

        if start_editing:
            QTimer.singleShot(300, window.tab_view.startEditing)

        self.window = window

    def newWindowFromUrl(self, url: QUrl):
        window = Ibrowse(self._profile)
        window.show()
        window.tab_view.newTabFromUrl(url)

        self.window = window

    def restart(self):
        QCoreApplication.quit()
        QCoreApplication.processEvents()

        status = QProcess.startDetached(sys.executable, sys.argv)
        print(status)

    def profile(self) -> WebEngineProfile:
        return self._profile


def main():
    app = QApplication(sys.argv)
    app.setEffectEnabled(Qt.UIEffect.UI_AnimateCombo, False)
    app.setEffectEnabled(Qt.UIEffect.UI_AnimateTooltip, False)
    app.setStyleSheet(ibrowse.read_html('resources/stylesheets/ibrowse_dark.css'))

    window = Ibrowse()
    window.show()

    app.processEvents()

    if len(sys.argv) > 1:
            window.openFromArg(sys.argv[1])
    else:
        window.loadTabs()

    # Crash handler
    def handle_exception(exctype, value, tb):
        QMessageBox.critical(window, 'Error:(', f'Ibrowse encountered an error:\n\n{value}\n')
        sys.__excepthook__(exctype, value, tb)

    # Set the global exception hook
    sys.excepthook = handle_exception

    sys.exit(app.exec())

if __name__ == '__main__':
    main()
