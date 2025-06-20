from PyQt6.QtGui import QIcon
import ibrowse
from PyQt6.QtCore import QEvent, QTimer, QUrl, Qt, QRect, QPropertyAnimation, QEasingCurve, QPoint
from PyQt6.QtWidgets import (QLineEdit, QCompleter, QMenu, QVBoxLayout, QWidget, QWidgetAction, QComboBox, QApplication,
    QHBoxLayout, QLabel)
from src.gui.commands import COMMANDS


class SearchBar(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(False)
        self.setPlaceholderText('Search...')
        self.installEventFilter(self)

        self.addAction(QIcon('resources/icons/ui/search_icon.svg'), QLineEdit.ActionPosition.LeadingPosition)

        self.updateCompleter()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.clearFocus()

        else:
            super().keyPressEvent(event)

    def focusInEvent(self, event):
        super().focusInEvent(event)

        if event.reason() != Qt.FocusReason.PopupFocusReason:
            QTimer.singleShot(0, self.startEditing)

    def startEditing(self):
        self.setFocus()
        self.selectAll()

    def setUrl(self, url: QUrl):
        self.blockSignals(True)
        self.setText(url.toString())
        self.blockSignals(False)

    def updateCompleter(self):
        items = COMMANDS.copy()

        for url, name in ibrowse.bookmarks().items():
            items.append(url)

        self._completer = QCompleter(items)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)

        self.setCompleter(self._completer)
