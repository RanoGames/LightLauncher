"""Проверка и установка обновлений лаунчера, просмотр истории изменений."""

import logging
import os
import subprocess
import sys
import tempfile

from PyQt6.QtCore import Qt, QThread, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from constants import GITHUB_API_URL, LAUNCHER_VERSION
from utils import get_http_session, resource_path, version_tuple

logger = logging.getLogger("LightLauncher")


DEFAULT_CHANGELOG = """# LightLauncher v0.50 — Список изменений

## 🚀 Что нового в версии 0.50 (Major Update)

### 🎨 1. Новый современный интерфейс (Modern Glassmorphism)
- **Два стиля оформления**: переключайтесь между классическим (Classic) и новым современным (Modern Glass) интерфейсом в Настройках без перезапуска.
- **Glassmorphism & карточный интерфейс**: полупрозрачные акриловые панели с мягким размытием, скруглениями (16px) и палитрой Deep Space (`#0d1117`, `#161b22`, `#21262d`).
- **Свежий акцентный градиент**: изумрудно-бирюзовый градиент (`#10b981` → `#06b6d4`) для кнопок запуска, прогресс-баров и активных элементов.
- **Адаптивные размеры и типографика**: исправлены узкие кнопки и обрезка текста, увеличена ширина полей, элементы выровнены и снабжены понятными иконками и подсказками.
- **Чистый главный экран**: убрана лишняя строка пути Java вверху, скрыт пустой силуэт скина, фон гармонично интегрирован с полупрозрачной подложкой.

### 🧩 2. Менеджер установленных модов (Installed Mods Manager)
- **Управление прямо из лаунчера**: новая вкладка «Установленные моды» в диалоге модов.
- **Включение и отключение модов**: отключайте моды без удаления (файлы переименовываются в `.disabled` и обратно).
- **Быстрый доступ**: кнопки открытия папки `mods` в Проводнике, удаления модов и обновления списка в реальном времени.
- **Интеграция с Mod Browser**: загруженные через браузер моды мгновенно появляются в менеджере.

### ☕ 3. Автоматическое скачивание и настройка Java (Auto Java Downloader)
- **Умное определение Java**: лаунчер автоматически определяет требуемую версию Java для выбранной версии Minecraft:
  - Java 8 — для 1.0 — 1.16.4
  - Java 16/17 — для 1.17 — 1.20.4
  - Java 21 — для 1.20.5+
- **Авто-загрузка OpenJDK (Adoptium / Eclipse Temurin)**: безопасная распаковка в изолированную папку `.minecraft/runtime/java_custom/` с отображением прогресса скачивания.
- Если Java отсутствует в системе, лаунчер предлагает скачать её в один клик.

### 📊 4. Точный расчёт размера версий при скачивании
- **Реальный размер вместо заглушки в 450 МБ**: лаунчер обращается к манифестам Mojang и вычисляет точный размер клиента, библиотек и ассетов.
  - Minecraft 1.0: **~52 МБ** (вместо 450 МБ)
  - Minecraft 1.12.2: **~173 МБ**
  - Minecraft 1.20.1: **~705 МБ**
- **Локальное кэширование**: результаты вычислений сохраняются в кэш, повторный выбор версии отображает размер мгновенно (~5 мс).

### 🐛 5. Исправления ошибок и стабильность
- **Интеллектуальный просмотр обновлений**: форматирование Markdown в окне обновления с кнопкой «Читать полностью» и расширяемым окном.
- **Просмотр Changelog в один клик**: нажатие на версию в левом верхнем углу лаунчера открывает полный список изменений.
- **Исправлена логика проверки обновлений**: корректное сопоставление версий.
- **Поддержка High-DPI**: корректное масштабирование интерфейса на экранах с высоким разрешением.
- **Очистка проекта**: вспомогательные утилиты перемещены в директорию `Tools/`, временные файлы удалены, линтер Ruff проходит без единой ошибки.
"""


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
        self._installer_process = None
        self.is_expanded = False

        self.setWindowTitle("Доступно обновление")
        self.setMinimumSize(480, 280)
        self.resize(510, 310)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )

        icon_path = resource_path("mclovin.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setStyleSheet("""
            QDialog {
                background-color: #0d1117;
                color: #e6edf3;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        # Заголовок версии
        title = QLabel(f"Новая версия: v{version.lstrip('v')}")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        layout.addWidget(title)

        # Окно с описанием изменений (Markdown-рендеринг)
        self.desc_browser = QTextBrowser()
        self.desc_browser.setOpenExternalLinks(True)
        self.desc_browser.document().setDocumentMargin(8)
        self.desc_browser.setMarkdown(body)
        self.desc_browser.setFixedHeight(115)
        self.desc_browser.setStyleSheet("""
            QTextBrowser {
                background-color: #161b22;
                color: #e6edf3;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                padding: 6px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
                line-height: 1.4;
            }
            QScrollBar:vertical {
                background: #161b22;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #30363d;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #484f58;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        layout.addWidget(self.desc_browser)

        # Кнопка «Читать полностью»
        self.expand_btn = QPushButton("Читать полностью ▼")
        self.expand_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.expand_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #10b981;
                border: none;
                font-size: 12px;
                font-weight: bold;
                text-align: left;
                padding: 2px 2px;
            }
            QPushButton:hover {
                color: #34d399;
                text-decoration: underline;
            }
        """)
        self.expand_btn.clicked.connect(self._toggle_expand)
        layout.addWidget(self.expand_btn)

        # Прогресс-бар скачивания
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #161b22;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                text-align: center;
                color: #ffffff;
                height: 18px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #06b6d4);
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #8b949e; font-size: 12px;")
        layout.addWidget(self.status_label)

        # Кнопки действий
        btn_layout = QHBoxLayout()
        self.skip_btn = QPushButton("Пропустить")
        self.skip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.skip_btn.setStyleSheet("""
            QPushButton {
                background-color: #21262d;
                color: #c9d1d9;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                padding: 8px 18px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #30363d;
                color: #ffffff;
            }
        """)
        self.skip_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.skip_btn)

        self.update_btn = QPushButton("Обновить")
        self.update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #059669);
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                padding: 8px 24px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #34d399, stop:1 #10b981);
            }
            QPushButton:disabled {
                background: #21262d;
                color: #8b949e;
                border-color: rgba(255, 255, 255, 0.05);
            }
        """)
        self.update_btn.clicked.connect(self.start_update)
        btn_layout.addWidget(self.update_btn)

        layout.addLayout(btn_layout)

    def _toggle_expand(self) -> None:
        self.is_expanded = not self.is_expanded
        if self.is_expanded:
            self.expand_btn.setText("Свернуть ▲")
            self.desc_browser.setFixedHeight(280)
            self.resize(560, 490)
        else:
            self.expand_btn.setText("Читать полностью ▼")
            self.desc_browser.setFixedHeight(115)
            self.resize(510, 310)

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

        self._check_timer = QTimer(self)
        self._check_timer.timeout.connect(self._check_installer_done)
        self._check_timer.start(500)

    def _check_installer_done(self) -> None:
        if self._installer_process and self._installer_process.poll() is not None:
            self._check_timer.stop()
            self._restart_launcher()

    def _restart_launcher(self) -> None:
        if getattr(sys, "frozen", False) or hasattr(sys, "__compiled__"):
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


class ChangelogDialog(QDialog):
    """Окно с подробным списком изменений текущей версии."""

    def __init__(self, parent=None, version: str = LAUNCHER_VERSION) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Список изменений — LightLauncher v{version}")
        self.setMinimumSize(540, 440)
        self.resize(640, 540)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )

        icon_path = resource_path("mclovin.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setStyleSheet("""
            QDialog {
                background-color: #0d1117;
                color: #e6edf3;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Заголовок
        header_layout = QHBoxLayout()
        title_label = QLabel(f"LightLauncher v{version}")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        badge = QLabel("Текущая версия")
        badge.setStyleSheet("""
            background-color: rgba(16, 185, 129, 0.15);
            color: #10b981;
            border: 1px solid rgba(16, 185, 129, 0.4);
            border-radius: 6px;
            padding: 3px 8px;
            font-size: 11px;
            font-weight: bold;
        """)
        header_layout.addWidget(badge)
        layout.addLayout(header_layout)

        # Текстовое поле с Markdown
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        self.browser.document().setDocumentMargin(10)
        self.browser.setMarkdown(DEFAULT_CHANGELOG)
        self.browser.setStyleSheet("""
            QTextBrowser {
                background-color: #161b22;
                color: #e6edf3;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 10px;
                padding: 10px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
                line-height: 1.5;
            }
            QScrollBar:vertical {
                background: #161b22;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #30363d;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #484f58;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        layout.addWidget(self.browser)

        # Кнопки снизу
        btn_layout = QHBoxLayout()

        github_btn = QPushButton("Открыть на GitHub ↗")
        github_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        github_btn.setStyleSheet("""
            QPushButton {
                background-color: #21262d;
                color: #c9d1d9;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #30363d;
                color: #ffffff;
            }
        """)
        github_btn.clicked.connect(self._open_github)
        btn_layout.addWidget(github_btn)

        btn_layout.addStretch()

        close_btn = QPushButton("Закрыть")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #059669);
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                padding: 8px 24px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #34d399, stop:1 #10b981);
            }
        """)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _open_github(self) -> None:
        QDesktopServices.openUrl(QUrl("https://github.com/RanoGames/LightLauncher/releases"))
