"""Окно консоли отладки Minecraft."""

import logging
import os

from PyQt6.QtGui import QIcon, QTextCursor
from PyQt6.QtWidgets import QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

from utils import resource_path

logger = logging.getLogger("LightLauncher")


class ConsoleWindow(QWidget):
    """Окно с логами stdout/stderr Minecraft."""

    def __init__(self, lang: str = "ru") -> None:
        super().__init__()
        self.setWindowTitle("Консоль отладки Minecraft" if lang == "ru" else "Minecraft Debug Console")
        self.resize(800, 500)

        # Bug #14 fix: иконка по абсолютному пути
        icon_path = resource_path("mclovin.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        layout = QVBoxLayout(self)

        self.text_edit = QPlainTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: Consolas, 'Courier New', monospace;
                font-size: 12px;
                border: none;
            }
        """)
        self.text_edit.setMaximumBlockCount(3000)
        layout.addWidget(self.text_edit)

        btn_text = "Скрыть консоль" if lang == "ru" else "Hide console"
        self.close_btn = QPushButton(btn_text)
        self.close_btn.clicked.connect(self.hide)
        layout.addWidget(self.close_btn)

    def append_log(self, text: str) -> None:
        """Добавляет текст в конец консоли."""
        self.text_edit.moveCursor(QTextCursor.MoveOperation.End)
        self.text_edit.insertPlainText(text)
        self.text_edit.moveCursor(QTextCursor.MoveOperation.End)
