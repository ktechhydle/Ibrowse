import ibrowse
import requests
from PyQt6.QtCore import QFileInfo, Qt, QPoint
from PyQt6.QtGui import QAction, QImage
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QFileDialog, QApplication
from PyQt6.QtWebEngineCore import (QWebEngineProfile, QWebEngineDownloadRequest, QWebEnginePage,
                                   QWebEngineContextMenuRequest, QWebEngineFullScreenRequest)
from urllib.parse import urlparse


class WebEngineProfile(QWebEngineProfile):
    def __init__(self, profile: str, parent=None):
        super().__init__(profile, parent)
        self.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
        self.setCachePath(ibrowse.cache_dir())
        self.setPersistentStoragePath(ibrowse.cache_dir())

        self.downloadRequested.connect(self.download)

    def download(self, request: QWebEngineDownloadRequest):
        filename, _ = QFileDialog.getSaveFileName(
            self.parent(),
            'Save As',
            request.downloadFileName()
        )

        if filename:
            request.setDownloadDirectory(QFileInfo(filename).path())
            request.setDownloadFileName(QFileInfo(filename).fileName())
            request.accept()


class WebEnginePage(QWebEnginePage):
    def __init__(self, profile, tab_view):
        super().__init__(profile, tab_view)
        self.tab_view = tab_view

        self.fullScreenRequested.connect(self.showFullScreenMode)

    def showFullScreenMode(self, request: QWebEngineFullScreenRequest):
        request.accept()
        tab = self.tab_view.currentTab()

        if request.toggleOn():
            tab.browser().setParent(None)
            tab.browser().showFullScreen()

        else:
            tab.browser().setParent(tab)
            tab.browser().showNormal()
            tab.layout().addWidget(tab.browser())


class WebEngineView(QWebEngineView):
    def __init__(self, page: WebEnginePage, tab_view, parent=None):
        super().__init__(parent)
        self.setPage(page)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self.tab_view = tab_view

        self.customContextMenuRequested.connect(self.showMenu)

    def createWindow(self, _type: QWebEnginePage.WebWindowType):
        if _type == QWebEnginePage.WebWindowType.WebBrowserTab:
            self.tab_view.newTab(start_editing=False)

        elif _type == QWebEnginePage.WebWindowType.WebBrowserWindow:
            self.tab_view.parent().newWindow(start_editing=False)

            return self.tab_view.parent().window.tab_view.currentTab().browser()

        return self.tab_view.currentTab().browser()

    def showMenu(self, pos: QPoint):
        menu = self.createStandardContextMenu()
        menu.removeAction(self.pageAction(QWebEnginePage.WebAction.DownloadLinkToDisk))
        menu.removeAction(self.pageAction(QWebEnginePage.WebAction.InspectElement))
        menu.removeAction(self.pageAction(QWebEnginePage.WebAction.ViewSource))
        data = self.lastContextMenuRequest()

        menu.addSeparator()

        print_action = menu.addAction('Print...')
        print_action.triggered.connect(self.printPage)

        if self.pageAction(QWebEnginePage.WebAction.Paste) in menu.actions():  # we can paste stuff
            paste_username_action = QAction('Paste Username', self)
            paste_username_action.triggered.connect(self.pasteUsername)

            paste_password_action = QAction('Paste Password', self)
            paste_password_action.triggered.connect(self.pastePassword)

            menu.insertAction(self.pageAction(QWebEnginePage.WebAction.PasteAndMatchStyle), paste_username_action)
            menu.insertAction(self.pageAction(QWebEnginePage.WebAction.PasteAndMatchStyle), paste_password_action)

        if not hasattr(self, 'connected_actions'):
            self.connected_actions = True
            self.pageAction(
                QWebEnginePage.WebAction.DownloadImageToDisk
            ).triggered.connect(lambda: self.saveImage(data))
            self.pageAction(
                QWebEnginePage.WebAction.CopyImageToClipboard
            ).triggered.connect(lambda: self.copyImage(data))
            self.pageAction(
                QWebEnginePage.WebAction.CopyImageUrlToClipboard
            ).triggered.connect(lambda: self.copyImageUrl(data))

        menu.exec(self.mapToGlobal(pos))

    def saveImage(self, data: QWebEngineContextMenuRequest):
        response = requests.get(data.mediaUrl().toString())

        if response.status_code == 200:
            url_filename = data.mediaUrl().toString().split('/')[-1]
            filename, _ = QFileDialog.getSaveFileName(self,
                                                      'Save Image As',
                                                      url_filename,
                                                      'Image files (*.)')

            if filename and '.' in filename:
                ibrowse.write_bytes(filename, response.content)

    def copyImage(self, data: QWebEngineContextMenuRequest):
        image_url = data.mediaUrl().toString()
        response = requests.get(image_url)

        if response.status_code == 200:
            image = QImage.fromData(response.content)

            if not image.isNull():
                clipboard = QApplication.clipboard()
                clipboard.setImage(image)

    def copyImageUrl(self, data: QWebEngineContextMenuRequest):
        image_url = data.mediaUrl().toString()

        clipboard = QApplication.clipboard()
        clipboard.setText(image_url)

    def printPage(self, data: QWebEngineContextMenuRequest):
        self.tab_view.currentTab().printPreview()

    def pasteUsername(self, data: QWebEngineContextMenuRequest):
        username = None

        for url, value in ibrowse.passwords().items():
            if self.normalizeUrl(url) == self.normalizeUrl(self.url().toString()):
                username = value[0]

        if username:
            script = f"""
                (function() {{
                    const focusedElement = document.activeElement;
                    if (focusedElement) {{
                        focusedElement.value = '{username}';
                        focusedElement.selectionStart = focusedElement.selectionEnd = '{len(username)}';
                        focusedElement.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    }}
                }})();
            """
            self.page().runJavaScript(script)

    def pastePassword(self, data: QWebEngineContextMenuRequest):
        password = None

        for url, value in ibrowse.passwords().items():
            if self.normalizeUrl(url) == self.normalizeUrl(self.url().toString()):
                password = value[1]

        if password:
            script = f"""
                (function() {{
                    const focusedElement = document.activeElement;
                    if (focusedElement) {{
                        focusedElement.value = '{password}';
                        focusedElement.selectionStart = focusedElement.selectionEnd = '{len(password)}';
                        focusedElement.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    }}
                }})();
            """
            self.page().runJavaScript(script)

    def normalizeUrl(self, url: str):
        parsed = urlparse(url if '://' in url else 'https://' + url)
        netloc = parsed.netloc.lower()
        path = parsed.path.rstrip('/')

        return f'{netloc}{path}'

    def stopMedia(self):
        self.page().setAudioMuted(True)
