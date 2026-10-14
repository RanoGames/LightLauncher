"""Проверка и установка обновлений лаунчера."""

import logging
import os
import subprocess
import sys
import tempfile

from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from constants import GITHUB_API_URL, LAUNCHER_VERSION
from utils import get_http_session, resource_path, version_tuple

logger = logging.getLogger("LightLauncher")


class UpdateChecker(QThread):
    """Проверяет наличие новой версии на GitHub."""

    update_available = pyqtSignal(str, str, str)   # version, body, download_url
    error_occurred = pyqtSignal(str)

    def run(self) -> None:
        try:
            session = get_http_session()
            resp = session.get(GITHUB_API_URL, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            latest_version = data.get("tag_name", "").lstrip("v")
            body = data.get("body", "Нет описания")

            if not latest_version:
                self.error_occurred.emit("Нет данных о версии")
                return

            if version_tuple(latest_version) > version_tuple(LAUNCHER_VERSION):
                download_url = None
                for asset in data.get("assets", []):
                    if asset["name"].endswith(".exe"):
                        download_url = asset["browser_download_url"]
                        break
                if download_url:
                    self.update_available.emit(latest_version, body, download_url)
        except Exception as e:
            logger.debug("Проверка обновлений не удалась: %s", e)


class UpdateDownloader(QThread):
    """Скачивает setup.exe обновления."""

    progress = pyqtSignal(int)
    download_finished = pyqtSignal(str)  # путь к скачанному файлу
    error = pyqtSignal(str)

    def __init__(self, url: str) -> None:
        super().__init__()
        self.url = url

    def run(self) -> None:
        try:
            session = get_http_session()
            resp = session.get(self.url, stream=True, timeout=120)
            resp.raise_for_status()

            total = int(resp.headers.get("content-length", 0))
            downloaded = 0

            setup_path = os.path.join(tempfile.gettempdir(), "LightLauncher_setup.exe")
            with open(setup_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        self.progress.emit(int(downloaded * 100 / total))

            self.download_finished.emit(setup_path)
        except Exception as e:
            self.error.emit(str(e))


class UpdateDialog(QDialog):
    """Диалог обновления: скачивание → установка → перезапуск."""

    def __init__(self, version: str, body: str, download_url: str,
                 parent=None) -> None:
        super().__init__(parent)
        self.download_url = download_url
        self._installer_process = None                  # Bug #5 fix

        self.setWindowTitle("Доступно обновление")
        self.setMinimumSize(400, 200)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )

        # Bug #14 fix: путь к иконке рядом с exe
        icon_path = resource_path("mclovin.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        layout = QVBoxLayout(self)

        title = QLabel(f"Новая версия: v{version}")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        desc = QLabel(body[:300] + ("..." if len(body) > 300 else ""))
        desc.setWordWrap(True)
        layout.addWidget(desc)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        btn_layout = QHBoxLayout()
        self.skip_btn = QPushButton("Пропустить")
        self.skip_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.skip_btn)

        self.update_btn = QPushButton("Обновить")
        self.update_btn.clicked.connect(self.start_update)
        btn_layout.addWidget(self.update_btn)

        layout.addLayout(btn_layout)

    def start_update(self) -> None:
        self.update_btn.setEnabled(False)
        self.skip_btn.setEnabled(False)
        self.progress_bar.show()
        self.status_label.setText("Скачивание обновления...")

        self.downloader = UpdateDownloader(self.download_url)
        self.downloader.progress.connect(self.on_progress)
        self.downloader.download_finished.connect(self.on_downloaded)
        self.downloader.error.connect(self.on_error)
        self.downloader.start()

    def on_progress(self, value: int) -> None:
        self.progress_bar.setValue(value)

    # ------------------------------------------------------------------
    # Bug #5 fix: ждём завершения инсталлятора через таймер, а не
    #             через фиксированный QTimer.singleShot(3000)
    # ------------------------------------------------------------------
    def on_downloaded(self, setup_path: str) -> None:
        self.status_label.setText("Установка обновления...")

        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0

        self._installer_process = subprocess.Popen(
            [setup_path, "/SILENT", "/SUPPRESSMSGBOXES",
             "/NORESTART", "/CLOSEAPPLICATIONS"],
            startupinfo=si,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

        # Проверяем завершение каждые 500 мс
        self._check_timer = QTimer(self)
        self._check_timer.timeout.connect(self._check_installer_done)
        self._check_timer.start(500)

    def _check_installer_done(self) -> None:
        if self._installer_process and self._installer_process.poll() is not None:
            self._check_timer.stop()
            self._restart_launcher()

    # ------------------------------------------------------------------
    # Bug #6 fix: корректный перезапуск и в frozen, и в dev-режиме
    # ------------------------------------------------------------------
    def _restart_launcher(self) -> None:
        if getattr(sys, "frozen", False):
            exe = os.path.abspath(sys.executable)
            subprocess.Popen([exe], creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            exe = sys.executable
            script = os.path.abspath(sys.argv[0])
            subprocess.Popen(
                [exe, script], creationflags=subprocess.CREATE_NO_WINDOW
            )
        QApplication.quit()

    def on_error(self, msg: str) -> None:
        self.status_label.setText(f"Ошибка: {msg}")
        self.update_btn.setEnabled(True)
        self.skip_btn.setEnabled(True)
