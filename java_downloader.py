"""Диалог автоматического скачивания и установки Java Runtime."""

import logging
import os
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from threads import JavaInstallThread
from utils import resource_path, t

logger = logging.getLogger("LightLauncher")


class JavaDownloadDialog(QDialog):
    """Диалог скачивания официального Mojang Java Runtime."""

    def __init__(
        self,
        jvm_version: str,
        major_version: int,
        parent=None,
        lang: str = "ru",
    ) -> None:
        super().__init__(parent)
        self.jvm_version = jvm_version
        self.major_version = major_version
        self._lang = lang
        self.java_path: Optional[str] = None

        self.setWindowTitle(t("download_java_title", self._lang))
        self.setFixedSize(480, 210)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        icon_path = resource_path("mclovin.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self._setup_ui()
        self._start_download()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        # Заголовок
        title_font = QFont("Segoe UI", 13, QFont.Weight.Bold)
        self.title_label = QLabel(
            f"⚡ {t('download_java_btn', self._lang).format(major=self.major_version)}",
            self,
        )
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet("color: #4ade80;")
        layout.addWidget(self.title_label)

        # Описание / инфо
        desc = QLabel(
            f"Загрузка официального пакета Mojang JRE ({self.jvm_version})...",
            self,
        )
        desc.setStyleSheet("color: #94a3b8; font-size: 11px;")
        layout.addWidget(desc)

        # Статус
        self.status_label = QLabel("Подготовка к загрузке...", self)
        self.status_label.setStyleSheet("color: #e2e8f0; font-size: 12px; font-weight: 500;")
        layout.addWidget(self.status_label)

        # Прогресс-бар
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: rgba(255, 255, 255, 15);
                border: 1px solid rgba(255, 255, 255, 30);
                border-radius: 8px;
                height: 22px;
                text-align: center;
                color: #ffffff;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #06b6d4);
                border-radius: 7px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Кнопки
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_btn = QPushButton(t("cancel", self._lang), self)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 16);
                border: 1px solid rgba(255, 255, 255, 35);
                border-radius: 8px;
                color: #ffffff;
                padding: 6px 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.4);
                border-color: rgba(239, 68, 68, 0.8);
            }
        """)
        self.cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)

    def _start_download(self) -> None:
        self.thread = JavaInstallThread(self.jvm_version)
        self.thread.update_status.connect(self._on_status)
        self.thread.update_progress.connect(self._on_progress)
        self.thread.install_finished.connect(self._on_finished)
        self.thread.error.connect(self._on_error)
        self.thread.start()

    def _on_status(self, text: str) -> None:
        self.status_label.setText(text)

    def _on_progress(self, percent: int) -> None:
        if percent < 0:
            self.progress_bar.setRange(0, 0)
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(percent)

    def _on_finished(self, java_path: str) -> None:
        self.java_path = java_path
        logger.info("Java Runtime %s successfully installed at %s", self.jvm_version, java_path)
        self.accept()

    def _on_error(self, err_msg: str) -> None:
        logger.error("Failed to install Java Runtime: %s", err_msg)
        QMessageBox.critical(
            self,
            t("download_java_title", self._lang),
            f"{t('download_java_error', self._lang)}\n{err_msg}",
        )
        self.reject()

    def _on_cancel(self) -> None:
        if hasattr(self, "thread") and self.thread.isRunning():
            self.thread.cancel()
        self.reject()

    def closeEvent(self, event) -> None:
        if hasattr(self, "thread") and self.thread.isRunning():
            self.thread.cancel()
        super().closeEvent(event)
