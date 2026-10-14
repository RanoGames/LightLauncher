"""Кастомные виджеты Qt."""

from PyQt6.QtCore import QEvent
from PyQt6.QtWidgets import QComboBox


class ClickComboBox(QComboBox):
    """ComboBox с выбором элемента одним кликом (без двойного)."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.view().viewport().installEventFilter(self)

    def eventFilter(self, obj, event) -> bool:
        if obj == self.view().viewport() and event.type() == QEvent.Type.MouseButtonPress:
            index = self.view().indexAt(event.pos())
            if index.isValid():
                self.setCurrentIndex(index.row())
                self.hidePopup()
                self.activated.emit(index.row())
                return True
        return super().eventFilter(obj, event)
