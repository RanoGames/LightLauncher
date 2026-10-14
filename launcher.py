"""Главное окно LightLauncher."""

import contextlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
import webbrowser
from collections import defaultdict
from typing import Optional

from minecraft_launcher_lib.command import get_minecraft_command
from PyQt6 import QtGui
from PyQt6.QtCore import (
    QEasingCurve,
    QProcess,
    QPropertyAnimation,
    QSize,
    Qt,
    QTimer,
)
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QGraphicsOpacityEffect,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSystemTrayIcon,
    QTabWidget,
    QVBoxLayout,
)

from console import ConsoleWindow
from constants import (
    CACHE_DIR,
    DEFAULT_SETTINGS,
    DISCORD_CLIENT_ID,
    LAUNCHER_VERSION,
    MINECRAFT_DIRECTORY,
    SETTINGS_FILE,
)
from crash_analyzer import analyze_latest_crash
from design import Ui_MainWindowClassic, Ui_MainWindowModern
from discord_rpc import DiscordRPC
from java_downloader import JavaDownloadDialog
from java_manager import (
    get_required_java_major,
    get_runtime_name_for_version,
    select_best_java,
)
from mod_browser import ModBrowserDialog
from mod_manager import ModManagerWidget
from modloader_installer import ModloaderDialog
from playtime_tracker import add_playtime
from settings_window import SettingsWindow
from skin_manager import ELY_BY_API, ensure_authlib_injector
from threads import BackgroundLoader, InstallThread, VersionLoader
from updater import UpdateChecker, UpdateDialog
from utils import (
    check_disk_space,
    get_cached_path,
    get_optimal_ram,
    is_valid_nickname,
    resolve_lang,
    resource_path,
    t,
)
from widgets import ClickComboBox

# Windows уведомления (опционально)
try:
    from winotify import Notification as WinNotification
    WIN_NOTIFY_AVAILABLE = True
except ImportError:
    WIN_NOTIFY_AVAILABLE = False

logger = logging.getLogger("LightLauncher")


class Launcher(QMainWindow):
    """Главное окно лаунчера Minecraft."""

    def __init__(self) -> None:
        super().__init__()

        # Трей Windows
        self.tray_icon: Optional[QSystemTrayIcon] = None
        self._session_start_time: Optional[float] = None

        # Загрузка настроек
        self.load_settings()
        self._lang = resolve_lang(self._lang_setting)

        # Выбор темы оформления
        if self.ui_theme == "classic":
            self.ui = Ui_MainWindowClassic()
        else:
            self.ui = Ui_MainWindowModern()
        self.ui.setupUi(self)

        # Заменяем комбобоксы на ClickComboBox
        self._replace_comboboxes()

        # Кнопка модов (+MOD): создаём, если отсутствует в UI (в classic)
        if not hasattr(self.ui, "InstallModloaderButton"):
            self.ui.InstallModloaderButton = QPushButton(parent=self.ui.centralwidget)
            self.ui.InstallModloaderButton.setGeometry(90, 415, 70, 70)
            font = QtGui.QFont()
            font.setPointSize(13)
            font.setBold(True)
            self.ui.InstallModloaderButton.setFont(font)
            self.ui.InstallModloaderButton.setText("+MOD")
            self.ui.InstallModloaderButton.setObjectName("InstallModloaderButton")
        self.ui.InstallModloaderButton.clicked.connect(self._open_mod_hub_dialog)

        # Иконки по абсолютному пути
        self._setup_icons()

        # Стили кнопок
        self._apply_button_transparency()

        # Применение языка
        self._apply_language()

        # Автоматическое скрытие Progress, когда текст пустой
        self._orig_progress_set_text = self.ui.Progress.setText

        def _safe_progress_set_text(text: str) -> None:
            self._orig_progress_set_text(text)
            self.ui.Progress.setVisible(bool(text and str(text).strip()))

        self.ui.Progress.setText = _safe_progress_set_text
        self.ui.Progress.hide()

        # Подключение сигналов
        self.ui.SettingsButton.clicked.connect(self.open_settings)
        self.ui.PlayMinecraft.clicked.connect(self.runmc)
        self.ui.DownLoadMinecraft.clicked.connect(self.installmc)
        self.ui.FilesButton.clicked.connect(self.open_game_directory)
        self.ui.GitHubButton.clicked.connect(self.open_github)
        self.ui.VersionComboBox.activated.connect(self._on_version_changed)
        self.ui.RefreshVersionsButton.clicked.connect(self.force_refresh_versions)
        self.ui.DeleteNicknameButton.clicked.connect(self._delete_current_nickname)
        self.ui.DeleteVersionButton.clicked.connect(self._delete_version)
        self.ui.CancelInstallButton.clicked.connect(self._cancel_install)

        # Никнейм: авто-сохранение через таймер
        self.ui.Nickname.activated.connect(self._on_nickname_activated)
        self._nick_timer = QTimer(self)
        self._nick_timer.setSingleShot(True)
        self._nick_timer.setInterval(1000)
        self._nick_timer.timeout.connect(self._save_current_nickname)
        self.ui.Nickname.lineEdit().textChanged.connect(self._on_nick_text_changed)

        # Клик по LineEdit открывает dropdown
        self.ui.Nickname.lineEdit().installEventFilter(self)

        # Процесс Minecraft
        self.minecraft_process = QProcess(self)
        self.minecraft_process.finished.connect(self.on_minecraft_exit)

        self.discord_rpc = DiscordRPC(DISCORD_CLIENT_ID)
        self.install_thread: Optional[InstallThread] = None

        # Фон (свой или стандартный)
        self._reload_background()

        # Загрузка версий
        self.ui.VersionComboBox.setPlaceholderText(t("loading", self._lang))
        self.ui.VersionComboBox.setEnabled(False)
        self.load_versions()

        # Консоль
        self.console_window: Optional[ConsoleWindow] = None

        # Профили никнеймов
        self._setup_nicknames()

        # Java
        self._detect_java()

        # Таймер запуска
        self._start_time = None
        self._launch_timer = QTimer(self)
        self._launch_timer.timeout.connect(self._update_launch_timer)

        # Версия лаунчера
        self.ui.JavaInfoLabel.setText(f"v{LAUNCHER_VERSION}")

        # Обновления
        self._check_for_updates()

    # ==============================================================
    # Инициализация UI
    # ==============================================================

    def _replace_comboboxes(self) -> None:
        """Заменяет дизайнерские QComboBox на ClickComboBox."""
        is_modern = (self.ui_theme == "modern")
        for attr, editable in [("Nickname", True), ("VersionComboBox", False)]:
            old = getattr(self.ui, attr)
            parent = old.parentWidget() or self
            new = ClickComboBox(parent)
            new.setEditable(editable)
            new.setGeometry(old.geometry())
            new.setObjectName(old.objectName())
            if is_modern:
                new.setFont(QtGui.QFont("Segoe UI", 11, QtGui.QFont.Weight.Bold))
                new.setStyleSheet("""
                    QComboBox {
                        background-color: rgba(255, 255, 255, 18);
                        border: 1px solid rgba(255, 255, 255, 35);
                        border-radius: 10px;
                        color: #ffffff;
                        padding-left: 10px;
                        padding-right: 25px;
                        font-family: 'Segoe UI', sans-serif;
                        font-weight: 600;
                        font-size: 13px;
                    }
                    QComboBox:hover {
                        background-color: rgba(255, 255, 255, 28);
                        border: 1px solid rgba(255, 255, 255, 60);
                    }
                    QComboBox::drop-down {
                        border: none;
                        width: 24px;
                    }
                    QComboBox QAbstractItemView {
                        background-color: #1a1e29;
                        color: #ffffff;
                        selection-background-color: #3b82f6;
                        border: 1px solid rgba(255, 255, 255, 30);
                        border-radius: 8px;
                        outline: none;
                        padding: 4px;
                    }
                    QLineEdit {
                        color: #ffffff;
                        background: transparent;
                        border: none;
                        font-family: 'Segoe UI', sans-serif;
                        font-weight: 600;
                        font-size: 13px;
                    }
                """)
            else:
                new.setFont(QtGui.QFont("Arial", 12, QtGui.QFont.Weight.Bold))
                new.setStyleSheet(
                    "QComboBox { font: bold 12pt Arial; } "
                    "QComboBox QAbstractItemView { font: bold 12pt Arial; }"
                )
            new.show()
            old.deleteLater()
            setattr(self.ui, attr, new)

    def _setup_icons(self) -> None:
        icon = resource_path("mclovin.ico")
        if os.path.exists(icon):
            self.setWindowIcon(QIcon(icon))

        # Для классического стиля устанавливаем иконки из файлов на квадратные кнопки
        if self.ui_theme == "classic":
            folder = resource_path("folder.png")
            if os.path.exists(folder):
                self.ui.FilesButton.setIcon(QIcon(folder))
                self.ui.FilesButton.setIconSize(QSize(40, 40))
            else:
                self.ui.FilesButton.setText("\U0001f4c2")

            github = resource_path("github.png")
            if os.path.exists(github):
                self.ui.GitHubButton.setIcon(QIcon(github))
                self.ui.GitHubButton.setIconSize(QSize(40, 40))
            else:
                self.ui.GitHubButton.setText("GitHub")

    # ==============================================================
    # Event filter
    # ==============================================================

    def eventFilter(self, obj, event) -> bool:
        if (obj == self.ui.Nickname.lineEdit()
                and event.type() == event.Type.MouseButtonPress):
            self.ui.Nickname.showPopup()
            return True
        return super().eventFilter(obj, event)

    # ==============================================================
    # Обновления
    # ==============================================================

    def _check_for_updates(self) -> None:
        self._update_checker = UpdateChecker()
        self._update_checker.update_available.connect(self._on_update_available)
        self._update_checker.start()

    def _on_update_available(self, version: str, body: str,
                             download_url: str) -> None:
        dialog = UpdateDialog(version, body, download_url, parent=self)
        dialog.exec()

    # ==============================================================
    # Никнеймы и аватарки
    # ==============================================================

    def _setup_nicknames(self) -> None:
        self.ui.Nickname.blockSignals(True)
        if self.ui.Nickname.lineEdit():
            self.ui.Nickname.lineEdit().blockSignals(True)
        self.ui.Nickname.clear()
        for nick in self._nicknames:
            self.ui.Nickname.addItem(nick)
        if self._last_nickname and self._last_nickname in self._nicknames:
            self.ui.Nickname.setCurrentText(self._last_nickname)
        if self.ui.Nickname.lineEdit():
            self.ui.Nickname.lineEdit().blockSignals(False)
        self.ui.Nickname.blockSignals(False)

    def _on_nick_text_changed(self) -> None:
        self._nick_timer.start()

    def _on_nickname_activated(self, index: int) -> None:
        nick = self.ui.Nickname.currentText().strip()
        if nick and nick not in self._nicknames:
            self._nicknames.append(nick)
            self.ui.Nickname.addItem(nick)
        self._last_nickname = nick
        self.save_settings()

    def _save_current_nickname(self) -> None:
        nick = self.ui.Nickname.currentText().strip()
        if not nick:
            return
        if nick not in self._nicknames:
            self._nicknames.append(nick)
            self.ui.Nickname.addItem(nick)
        self._last_nickname = nick
        self.save_settings()

    def _delete_current_nickname(self) -> None:
        nick = self.ui.Nickname.currentText().strip()
        if not nick:
            return
        if nick in self._nicknames:
            self._nicknames.remove(nick)
        if self._last_nickname == nick:
            self._last_nickname = self._nicknames[-1] if self._nicknames else None
        self._setup_nicknames()
        self.save_settings()

    # ==============================================================
    # Стилизация
    # ==============================================================

    def _apply_button_transparency(self) -> None:
        if self.ui_theme == "modern":
            # Геройские кнопки: Играть, Скачать, Отмена
            self.ui.PlayMinecraft.setStyleSheet("""
                QPushButton#PlayMinecraft {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #059669);
                    border: 1px solid rgba(255, 255, 255, 0.25);
                    border-radius: 12px;
                    color: #ffffff;
                    font-weight: bold;
                    font-size: 15px;
                }
                QPushButton#PlayMinecraft:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #34d399, stop:1 #10b981);
                    border-color: rgba(255, 255, 255, 0.45);
                }
                QPushButton#PlayMinecraft:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #047857);
                }
            """)
            self.ui.DownLoadMinecraft.setStyleSheet("""
                QPushButton#DownLoadMinecraft {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #2563eb);
                    border: 1px solid rgba(255, 255, 255, 0.25);
                    border-radius: 12px;
                    color: #ffffff;
                    font-weight: bold;
                    font-size: 15px;
                }
                QPushButton#DownLoadMinecraft:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #60a5fa, stop:1 #3b82f6);
                    border-color: rgba(255, 255, 255, 0.45);
                }
                QPushButton#DownLoadMinecraft:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #1d4ed8);
                }
            """)
            self.ui.CancelInstallButton.setStyleSheet("""
                QPushButton#CancelInstallButton {
                    background-color: rgba(239, 68, 68, 0.85);
                    border: 1px solid rgba(255, 255, 255, 0.25);
                    border-radius: 12px;
                    color: #ffffff;
                    font-weight: bold;
                    font-size: 14px;
                }
                QPushButton#CancelInstallButton:hover {
                    background-color: rgba(239, 68, 68, 1.0);
                }
                QPushButton#CancelInstallButton:pressed {
                    background-color: rgba(185, 28, 28, 1.0);
                }
            """)

            # Кнопки быстрых действий (пилюли)
            pill_style = """
                QPushButton {
                    background-color: rgba(255, 255, 255, 14);
                    border: 1px solid rgba(255, 255, 255, 28);
                    border-radius: 10px;
                    color: #e2e8f0;
                    font-family: 'Segoe UI', sans-serif;
                    font-size: 13px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 28);
                    border-color: rgba(255, 255, 255, 55);
                    color: #ffffff;
                }
                QPushButton:pressed {
                    background-color: rgba(255, 255, 255, 45);
                }
            """
            for btn in [
                self.ui.SettingsButton,
                self.ui.InstallModloaderButton,
                self.ui.FilesButton,
                self.ui.DeleteVersionButton,
                self.ui.GitHubButton,
            ]:
                btn.setStyleSheet(pill_style)

            # Маленькие вспомогательные кнопки
            mini_style = """
                QPushButton {
                    background-color: rgba(255, 255, 255, 14);
                    border: 1px solid rgba(255, 255, 255, 28);
                    border-radius: 8px;
                    color: #cbd5e1;
                    font-family: 'Segoe UI', sans-serif;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 30);
                    border-color: rgba(255, 255, 255, 60);
                    color: #ffffff;
                }
                QPushButton:pressed {
                    background-color: rgba(255, 255, 255, 50);
                }
            """
            self.ui.DeleteNicknameButton.setStyleSheet(mini_style)
            self.ui.RefreshVersionsButton.setStyleSheet(mini_style)

        else:
            style = """
                QPushButton {
                    background-color: rgba(0, 0, 0, 80);
                    border: none;
                    border-radius: 8px;
                    color: white;
                }
                QPushButton:hover {
                    background-color: rgba(0, 0, 0, 140);
                }
                QPushButton:pressed {
                    background-color: rgba(0, 0, 0, 180);
                }
            """
            for btn in [
                self.ui.SettingsButton, self.ui.DownLoadMinecraft,
                self.ui.PlayMinecraft, self.ui.RefreshVersionsButton,
                self.ui.FilesButton, self.ui.GitHubButton,
                self.ui.DeleteNicknameButton, self.ui.DeleteVersionButton,
                self.ui.CancelInstallButton, self.ui.InstallModloaderButton,
            ]:
                btn.setStyleSheet(style)

    # ==============================================================
    # Локализация
    # ==============================================================

    def _apply_language(self) -> None:
        L = self._lang
        is_modern = (self.ui_theme == "modern")
        if is_modern:
            self.ui.PlayMinecraft.setText("▶ " + t("play", L))
            self.ui.DownLoadMinecraft.setText("⬇ " + t("download", L))
            self.ui.SettingsButton.setText("⚙ " + t("settings", L))
            self.ui.InstallModloaderButton.setText("🧩 " + t("mods_btn", L))
            self.ui.FilesButton.setText("📁 " + t("folder_btn", L))
            self.ui.DeleteVersionButton.setText("🗑 " + t("delete_btn", L))
            self.ui.GitHubButton.setText("🐙 GitHub")
        else:
            self.ui.PlayMinecraft.setText(t("play", L))
            self.ui.DownLoadMinecraft.setText(t("download", L))
            self.ui.SettingsButton.setText(t("settings", L))
            self.ui.InstallModloaderButton.setText("+MOD")
            self.ui.DeleteVersionButton.setText("\U0001f5d1")
        self.ui.NicknameLabel.setText(t("nickname_label", L))
        self.ui.GameVersionLabel.setText(t("version_label", L))
        self.ui.CancelInstallButton.setText(t("cancel", L))
        self.ui.Nickname.setToolTip(t("nickname_tip", L))
        self.ui.VersionComboBox.setToolTip(t("version_tip", L))
        self.ui.RefreshVersionsButton.setToolTip(t("refresh_tip", L))
        self.ui.FilesButton.setToolTip(t("files_tip", L))
        self.ui.GitHubButton.setToolTip(t("github_tip", L))
        self.ui.DeleteNicknameButton.setToolTip(t("delete_nick_tip", L))
        self.ui.DeleteVersionButton.setToolTip(t("delete_ver_tip", L))
        self.ui.CancelInstallButton.setToolTip(t("cancel_tip", L))
        self.ui.VersionComboBox.setPlaceholderText(t("loading", L))
        self.ui.InstallModloaderButton.setToolTip(t("install_modloader", L))

    # ==============================================================
    # Анимации
    # ==============================================================

    def _fade_in(self, widget, duration: int = 500) -> None:
        if not isinstance(widget, QLabel):
            return
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(duration)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        anim.start()
        widget._fade_anim = anim

    def _fade_out(self, widget, duration: int = 300, callback=None) -> None:
        if not isinstance(widget, QLabel):
            if callback:
                callback()
            return
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(duration)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        if callback:
            anim.finished.connect(callback)
        anim.start()
        widget._fade_anim = anim

    def _animate_text_change(self, label, text: str,
                             duration: int = 400) -> None:
        if not isinstance(label, QLabel):
            label.setText(text)
            return

        def set_text():
            label.setText(text)
            self._fade_in(label, duration)
        self._fade_out(label, duration // 2, set_text)

    # ==============================================================
    # Уведомления и Системный Трей
    # ==============================================================

    def _show_notification(self, title: str, message: str) -> None:
        if not WIN_NOTIFY_AVAILABLE:
            return
        try:
            toast = WinNotification(
                app_id="LightLauncher",
                title=title,
                msg=message,
                duration="short",
            )
            toast.show()
        except Exception as e:
            logger.warning("Notification error: %s", e)

    def _setup_tray_icon(self, version: str) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        if self.tray_icon is None:
            self.tray_icon = QSystemTrayIcon(self)
            icon_p = resource_path("mclovin.ico")
            if os.path.exists(icon_p):
                self.tray_icon.setIcon(QIcon(icon_p))

            menu = QMenu(self)
            restore_act = menu.addAction("Развернуть лаунчер")
            restore_act.triggered.connect(self._restore_from_tray)

            if self.show_console_opt:
                console_act = menu.addAction("Консоль отладки")
                console_act.triggered.connect(self._show_console_from_tray)

            menu.addSeparator()
            quit_act = menu.addAction("Завершить игру")
            quit_act.triggered.connect(self._kill_game_from_tray)

            self.tray_icon.setContextMenu(menu)
            self.tray_icon.activated.connect(self._on_tray_activated)

        self.tray_icon.setToolTip(f"LightLauncher — Minecraft {version}")
        self.tray_icon.show()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._restore_from_tray()

    def _restore_from_tray(self) -> None:
        self.show()
        self.activateWindow()

    def _show_console_from_tray(self) -> None:
        if self.console_window:
            self.console_window.show()
            self.console_window.activateWindow()

    def _kill_game_from_tray(self) -> None:
        if self.minecraft_process.state() == QProcess.ProcessState.Running:
            msg = QMessageBox(self)
            msg.setWindowTitle("Подтверждение")
            msg.setText("Принудительно закрыть процесс Minecraft?")
            msg.setIcon(QMessageBox.Icon.Question)
            yes_b = msg.addButton(t("yes", self._lang), QMessageBox.ButtonRole.YesRole)
            msg.addButton(t("no", self._lang), QMessageBox.ButtonRole.NoRole)
            msg.exec()
            if msg.clickedButton() == yes_b:
                self.minecraft_process.kill()

    def _remove_tray_icon(self) -> None:
        if self.tray_icon:
            self.tray_icon.hide()

    # ==============================================================
    # Java
    # ==============================================================

    def _detect_java(self) -> None:
        self.ui.JavaInfoLabel.setText(f"v{LAUNCHER_VERSION}")

    # ==============================================================
    # Версии
    # ==============================================================

    def _on_version_changed(self, index: int) -> None:
        version = self.ui.VersionComboBox.currentData()
        if not version:
            return
        self.last_version = version
        self.save_settings()
        self._detect_java()

    def load_versions(self, force_refresh: bool = False) -> None:
        self.ui.VersionComboBox.clear()
        self.ui.VersionComboBox.addItem(t("loading", self._lang))
        self.ui.VersionComboBox.setEnabled(False)
        self.ver_loader = VersionLoader(
            filters=self.version_filters, force_refresh=force_refresh,
        )
        self.ver_loader.versions_loaded.connect(self.populate_versions)
        self.ver_loader.error_occurred.connect(self.show_error)
        self.ver_loader.start()

    def force_refresh_versions(self) -> None:
        self.load_versions(force_refresh=True)

    def populate_versions(self, versions: list[str]) -> None:
        self.ui.VersionComboBox.clear()

        installed = set()
        versions_dir = os.path.join(MINECRAFT_DIRECTORY, "versions")
        if os.path.isdir(versions_dir):
            for d in os.listdir(versions_dir):
                if os.path.isdir(os.path.join(versions_dir, d)):
                    installed.add(d)

        manifest_set = set(versions)
        custom_versions = installed - manifest_set

        custom_map = defaultdict(list)
        unmatched_custom = []

        for cv in sorted(custom_versions):
            base = None
            json_path = os.path.join(versions_dir, cv, f"{cv}.json")
            if os.path.exists(json_path):
                try:
                    with open(json_path, encoding="utf-8") as f:
                        v_data = json.load(f)
                    base = v_data.get("inheritsFrom")
                except Exception:
                    pass

            if not base:
                m = re.search(r'1\.\d+(?:\.\d+)?', cv)
                if m:
                    base = m.group(0)

            if base and base in manifest_set:
                custom_map[base].append(cv)
            else:
                unmatched_custom.append(cv)

        def add_version_item(label: str, ver_id: str, is_installed: bool) -> None:
            idx = self.ui.VersionComboBox.count()
            self.ui.VersionComboBox.addItem(label, ver_id)
            color = QtGui.QColor("#ffffff") if is_installed else QtGui.QColor("#888888")
            self.ui.VersionComboBox.setItemData(idx, color, Qt.ItemDataRole.ForegroundRole)

        for v in versions:
            add_version_item(v, v, v in installed)
            if v in custom_map:
                for cv in custom_map[v]:
                    add_version_item(f"↳ {cv}", cv, True)

        for ucv in unmatched_custom:
            add_version_item(ucv, ucv, True)

        self.ui.VersionComboBox.setEnabled(True)

        if self.last_version:
            idx = self.ui.VersionComboBox.findData(self.last_version)
            if idx >= 0:
                self.ui.VersionComboBox.setCurrentIndex(idx)
            else:
                self.ui.VersionComboBox.setCurrentIndex(0)
        else:
            self.ui.VersionComboBox.setCurrentIndex(0)

        self._detect_java()

    def _open_mod_hub_dialog(self) -> None:
        version = self.ui.VersionComboBox.currentData()
        if not version:
            self.show_error(t("select_version", self._lang))
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Центр модификаций")
        dlg.resize(760, 600)
        layout = QVBoxLayout(dlg)

        tabs = QTabWidget()
        manager_tab = ModManagerWidget(parent=dlg, lang=self._lang)
        browser_tab = ModBrowserDialog(version, parent=dlg, lang=self._lang)
        installer_tab = ModloaderDialog(version, self.java_path, parent=dlg, lang=self._lang)
        installer_tab.installed.connect(lambda: self.load_versions(force_refresh=False))

        # При переключении на менеджер модов освежаем список
        tabs.currentChanged.connect(lambda idx: manager_tab.refresh_mods() if idx == 0 else None)

        tabs.addTab(manager_tab, f"📦 {t('installed_mods', self._lang)}")
        tabs.addTab(browser_tab, f"🌐 {t('mod_catalog', self._lang)}")
        tabs.addTab(installer_tab, f"⚙ {t('install_modloader', self._lang)}")
        layout.addWidget(tabs)

        dlg.exec()

    # ==============================================================
    # Фон
    # ==============================================================

    def _reload_background(self) -> None:
        self.bg_loader = BackgroundLoader(self.custom_background)
        self.bg_loader.loaded.connect(self.set_background_image)
        self.bg_loader.start()

    def set_background_image(self, image) -> None:
        if not hasattr(self, "bg_label"):
            self.bg_label = QLabel(self)
            self.bg_label.setScaledContents(True)
            self.bg_label.lower()
        if isinstance(image, QPixmap):
            self.bg_label.setPixmap(image)
        else:
            self.bg_label.setPixmap(QPixmap.fromImage(image))
        self.bg_label.resize(self.size())
        self.bg_label.show()

    def resizeEvent(self, event) -> None:
        if hasattr(self, "bg_label"):
            self.bg_label.resize(self.size())
        super().resizeEvent(event)

    # ==============================================================
    # Настройки (load / save / open)
    # ==============================================================

    def load_settings(self) -> None:
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, encoding="utf-8") as f:
                    data = json.load(f)
                self.version_filters = data.get("filters", DEFAULT_SETTINGS["filters"])
                self.allocated_memory = data.get("memory", DEFAULT_SETTINGS["memory"])
                self.last_version = data.get("last_version", None)
                self.show_console_opt = data.get("show_console", False)
                self._nicknames = data.get("nicknames", [])
                self._last_nickname = data.get("last_nickname", None)
                self._lang_setting = data.get("language", DEFAULT_SETTINGS["language"])
                self._jvm_args = data.get("jvm_args", DEFAULT_SETTINGS["jvm_args"])
                self.validate_nickname = data.get(
                    "validate_nickname", DEFAULT_SETTINGS["validate_nickname"]
                )
                self.auto_java = data.get("auto_java", DEFAULT_SETTINGS["auto_java"])
                self.java_path = data.get("java_path", DEFAULT_SETTINGS["java_path"])
                self.fullscreen = data.get("fullscreen", DEFAULT_SETTINGS["fullscreen"])
                self.resolution_width = data.get(
                    "resolution_width", DEFAULT_SETTINGS["resolution_width"]
                )
                self.resolution_height = data.get(
                    "resolution_height", DEFAULT_SETTINGS["resolution_height"]
                )
                self.custom_background = data.get("custom_background", DEFAULT_SETTINGS["custom_background"])
                self.ely_by_skins = data.get("ely_by_skins", DEFAULT_SETTINGS["ely_by_skins"])
                self.ui_theme = data.get("ui_theme", DEFAULT_SETTINGS["ui_theme"])
            except Exception:
                logger.warning("Ошибка чтения настроек, сброс на умолчания")
                self.set_defaults()
        else:
            self.set_defaults()

    def set_defaults(self) -> None:
        self.version_filters = list(DEFAULT_SETTINGS["filters"])
        self.allocated_memory = get_optimal_ram()
        self.last_version = DEFAULT_SETTINGS["last_version"]
        self.show_console_opt = DEFAULT_SETTINGS["show_console"]
        self._nicknames = list(DEFAULT_SETTINGS["nicknames"])
        self._last_nickname = DEFAULT_SETTINGS["last_nickname"]
        self._lang_setting = DEFAULT_SETTINGS["language"]
        self._jvm_args = DEFAULT_SETTINGS["jvm_args"]
        self.validate_nickname = DEFAULT_SETTINGS["validate_nickname"]
        self.auto_java = DEFAULT_SETTINGS["auto_java"]
        self.java_path = DEFAULT_SETTINGS["java_path"]
        self.fullscreen = DEFAULT_SETTINGS["fullscreen"]
        self.resolution_width = DEFAULT_SETTINGS["resolution_width"]
        self.resolution_height = DEFAULT_SETTINGS["resolution_height"]
        self.custom_background = DEFAULT_SETTINGS["custom_background"]
        self.ely_by_skins = DEFAULT_SETTINGS["ely_by_skins"]
        self.ui_theme = DEFAULT_SETTINGS["ui_theme"]

    def save_settings(self) -> None:
        data = {
            "filters": self.version_filters,
            "memory": self.allocated_memory,
            "last_version": self.last_version,
            "show_console": self.show_console_opt,
            "nicknames": self._nicknames,
            "last_nickname": self._last_nickname,
            "language": self._lang_setting,
            "jvm_args": self._jvm_args,
            "validate_nickname": self.validate_nickname,
            "auto_java": self.auto_java,
            "java_path": self.java_path,
            "fullscreen": self.fullscreen,
            "resolution_width": self.resolution_width,
            "resolution_height": self.resolution_height,
            "custom_background": self.custom_background,
            "ely_by_skins": self.ely_by_skins,
            "ui_theme": self.ui_theme,
        }
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error("Ошибка сохранения настроек: %s", e)

    def open_settings(self) -> None:
        dialog = SettingsWindow(
            self,
            current_filters=self.version_filters,
            current_memory=self.allocated_memory,
            show_console=self.show_console_opt,
            current_lang=self._lang_setting,
            jvm_args=self._jvm_args,
            validate_nickname=self.validate_nickname,
            auto_java=self.auto_java,
            java_path=self.java_path,
            fullscreen=self.fullscreen,
            resolution_width=self.resolution_width,
            resolution_height=self.resolution_height,
            custom_background=self.custom_background,
            ely_by_skins=self.ely_by_skins,
            current_version=self.ui.VersionComboBox.currentData(),
            ui_theme=self.ui_theme,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            cfg = dialog.get_settings()

            current_version = self.ui.VersionComboBox.currentData()
            if current_version:
                self.last_version = current_version

            old_bg = self.custom_background
            old_theme = self.ui_theme
            self.version_filters = cfg["filters"]
            self.allocated_memory = cfg["memory"]
            self.show_console_opt = cfg["show_console"]
            self._lang_setting = cfg["language"]
            self._lang = resolve_lang(cfg["language"])
            self._jvm_args = cfg["jvm_args"]
            self.validate_nickname = cfg["validate_nickname"]
            self.auto_java = cfg["auto_java"]
            self.java_path = cfg["java_path"]
            self.fullscreen = cfg["fullscreen"]
            self.resolution_width = cfg["resolution_width"]
            self.resolution_height = cfg["resolution_height"]
            self.custom_background = cfg["custom_background"]
            self.ely_by_skins = cfg["ely_by_skins"]
            self.ui_theme = cfg.get("ui_theme", "modern")

            self._apply_language()
            self._detect_java()
            self.save_settings()

            if old_bg != self.custom_background:
                self._reload_background()

            if cfg["filters"] != dialog.old_filters:
                self.load_versions()

            if old_theme != self.ui_theme:
                QMessageBox.information(
                    self,
                    t("ui_theme", self._lang).rstrip(":"),
                    t("theme_restart_notice", self._lang),
                )

    # ==============================================================
    # Запуск игры
    # ==============================================================

    def runmc(self) -> None:
        version = self.ui.VersionComboBox.currentData()
        username = self.ui.Nickname.currentText().strip()

        if not version:
            self.show_error(t("select_version", self._lang))
            return
        if not username:
            self.show_error(t("enter_nick", self._lang))
            return

        if self.validate_nickname and not is_valid_nickname(username):
            self.show_error(t("invalid_nick", self._lang))
            return

        # Проверка наличия установленной версии
        version_dir = os.path.join(MINECRAFT_DIRECTORY, "versions", version)
        if not os.path.isdir(version_dir):
            msg = QMessageBox(self)
            msg.setWindowTitle("Версия не установлена")
            msg.setText(f"Версия {version} ещё не скачана на компьютер.\n\nСкачать её сейчас?")
            msg.setIcon(QMessageBox.Icon.Question)
            yes_b = msg.addButton(t("download", self._lang), QMessageBox.ButtonRole.YesRole)
            msg.addButton(t("cancel", self._lang), QMessageBox.ButtonRole.NoRole)
            msg.exec()
            if msg.clickedButton() == yes_b:
                self.installmc()
            return

        # Автоопределение Java и проверка совместимости
        java_path, warning = select_best_java(version, self.java_path, self.auto_java)
        if not java_path:
            # Предлагаем автоскачивание
            req_major = get_required_java_major(version)
            runtime_name = get_runtime_name_for_version(version)
            msg = QMessageBox(self)
            msg.setWindowTitle(t("download_java_title", self._lang))
            msg.setText(t("download_java_prompt", self._lang).format(version=version, major=req_major))
            msg.setIcon(QMessageBox.Icon.Question)
            yes_b = msg.addButton(t("yes", self._lang), QMessageBox.ButtonRole.YesRole)
            msg.addButton(t("no", self._lang), QMessageBox.ButtonRole.NoRole)
            msg.exec()
            if msg.clickedButton() == yes_b:
                dl_dialog = JavaDownloadDialog(runtime_name, req_major, parent=self, lang=self._lang)
                if dl_dialog.exec() == QDialog.DialogCode.Accepted and dl_dialog.java_path:
                    java_path = dl_dialog.java_path
                    warning = None
                else:
                    return
            else:
                self.show_error(warning or t("java_not_found", self._lang))
                return

        if warning:
            req_major = get_required_java_major(version)
            runtime_name = get_runtime_name_for_version(version)
            warn_msg = QMessageBox(self)
            warn_msg.setIcon(QMessageBox.Icon.Warning)
            warn_msg.setWindowTitle("Внимание: Версия Java")
            warn_msg.setText(f"{warning}\n\nРекомендуется скачать подходящую Java.")
            dl_btn = warn_msg.addButton(
                f"⬇ {t('download_java_btn', self._lang).format(major=req_major)}",
                QMessageBox.ButtonRole.ActionRole,
            )
            run_btn = warn_msg.addButton(t("yes", self._lang) + " (Запустить)", QMessageBox.ButtonRole.YesRole)
            warn_msg.addButton(t("cancel", self._lang), QMessageBox.ButtonRole.RejectRole)
            warn_msg.exec()
            clicked = warn_msg.clickedButton()
            if clicked == dl_btn:
                dl_dialog = JavaDownloadDialog(runtime_name, req_major, parent=self, lang=self._lang)
                if dl_dialog.exec() == QDialog.DialogCode.Accepted and dl_dialog.java_path:
                    java_path = dl_dialog.java_path
                else:
                    return
            elif clicked != run_btn:
                return

        self.ui.Progress.setText(f"{t('launching', self._lang)}...")
        self.hide()

        self.last_version = version
        self.save_settings()

        if self.show_console_opt:
            if self.console_window is None:
                self.console_window = ConsoleWindow(self._lang)
            self.console_window.show()
            self.console_window.activateWindow()

        extra_jvm = self._jvm_args.split() if self._jvm_args else []

        # Поддержка скинов Ely.by для пиратских аккаунтов
        if self.ely_by_skins:
            authlib_jar = ensure_authlib_injector()
            if authlib_jar:
                extra_jvm.append(f"-javaagent:{authlib_jar}={ELY_BY_API}")

        mcoptions = {
            "username": username,
            "jvmArguments": [f"-Xmx{self.allocated_memory}M"] + extra_jvm,
            "launcherName": "LightLauncher",
            "launcherVersion": LAUNCHER_VERSION,
            "executablePath": java_path,
        }

        if self.fullscreen:
            mcoptions["fullscreen"] = True
        else:
            mcoptions["customResolution"] = True
            mcoptions["resolutionWidth"] = str(self.resolution_width)
            mcoptions["resolutionHeight"] = str(self.resolution_height)

        try:
            command = get_minecraft_command(
                version=version,
                minecraft_directory=MINECRAFT_DIRECTORY,
                options=mcoptions,
            )

            self.minecraft_process.setProgram(command[0])
            self.minecraft_process.setArguments(command[1:])

            if self.show_console_opt:
                self.minecraft_process.setProcessChannelMode(
                    QProcess.ProcessChannelMode.MergedChannels
                )
                with contextlib.suppress(Exception):
                    self.minecraft_process.readyReadStandardOutput.disconnect()
                self.minecraft_process.readyReadStandardOutput.connect(
                    self.write_to_console
                )

            self.minecraft_process.start()
            self.discord_rpc.start(version)
            self._setup_tray_icon(version)

            self._session_start_time = time.time()
            self._start_time = time.time()
            self._launch_timer.start(1000)

        except Exception as e:
            self._remove_tray_icon()
            self.show()
            self.show_error(f"{t('launch_err', self._lang)} {e}")

    def _update_launch_timer(self) -> None:
        if self._start_time:
            elapsed = int(time.time() - self._start_time)
            mins, secs = divmod(elapsed, 60)
            hours, mins = divmod(mins, 60)
            prefix = t("launcher_running", self._lang)
            if hours > 0:
                self.ui.Progress.setText(f"{prefix} {hours}h {mins}m {secs}s")
            else:
                self.ui.Progress.setText(f"{prefix} {mins}m {secs}s")

    def write_to_console(self) -> None:
        data = self.minecraft_process.readAllStandardOutput().data()
        try:
            text = data.decode("utf-8", errors="ignore")
        except Exception:
            text = str(data)
        if self.console_window:
            self.console_window.append_log(text)

    def on_minecraft_exit(self, exit_code: int, *args) -> None:
        self.discord_rpc.stop()
        self._launch_timer.stop()
        self._start_time = None
        self._remove_tray_icon()

        # Сохранение времени в игре
        if self._session_start_time:
            elapsed = int(time.time() - self._session_start_time)
            add_playtime(self.last_version or "Unknown", elapsed)
            self._session_start_time = None

        try:
            if exit_code != 0:
                self.ui.Progress.setText(f"{t('crash', self._lang)} {exit_code}")
                # Умный анализ краша
                diag = analyze_latest_crash()
                if diag:
                    c_box = QMessageBox(self)
                    c_box.setIcon(QMessageBox.Icon.Critical)
                    c_box.setWindowTitle(t("crash_analyzer_title", self._lang))
                    c_box.setText(
                        f"<b>{diag['title']}</b>\n\n"
                        f"<b>Причина:</b> {diag['cause']}\n\n"
                        f"<b>Рекомендация:</b> {diag['solution']}"
                    )
                    if diag.get("file"):
                        c_box.setInformativeText(f"Лог сбоя: {diag['file']}")
                    c_box.exec()
            else:
                self.ui.Progress.setText("")
            self.show()
            self.activateWindow()
        except RuntimeError:
            pass

    # ==============================================================
    # Установка
    # ==============================================================

    def _get_version_estimated_mb(self, version: str) -> float:
        """Точно рассчитывает или оценивает размер загрузки версии Minecraft в МБ."""
        sizes_cache_file = os.path.join(CACHE_DIR, "version_sizes.json")
        sizes_cache: dict[str, float] = {}
        if os.path.exists(sizes_cache_file):
            try:
                with open(sizes_cache_file, encoding="utf-8") as f:
                    sizes_cache = json.load(f)
                if version in sizes_cache:
                    return sizes_cache[version]
            except Exception:
                pass

        v_data = None
        # 1. Проверяем локальный JSON файл версии
        local_v_json = os.path.join(MINECRAFT_DIRECTORY, "versions", version, f"{version}.json")
        if os.path.exists(local_v_json):
            try:
                with open(local_v_json, encoding="utf-8") as f:
                    v_data = json.load(f)
            except Exception:
                pass

        # 2. Если версия кастомная (Forge/Fabric), ищем базовую версию
        target_version_id = version
        if v_data and "inheritsFrom" in v_data:
            target_version_id = v_data["inheritsFrom"]
            v_data = None

        # 3. Ищем URL версии в кэше манифеста
        if not v_data:
            manifest_path = get_cached_path("version_manifest.json")
            if os.path.exists(manifest_path):
                try:
                    with open(manifest_path, encoding="utf-8") as f:
                        manifest = json.load(f)
                    v_info = next((v for v in manifest.get("versions", []) if v["id"] == target_version_id), None)
                    if v_info and "url" in v_info:
                        from utils import get_http_session
                        session = get_http_session()
                        resp = session.get(v_info["url"], timeout=4)
                        if resp.status_code == 200:
                            v_data = resp.json()
                except Exception:
                    pass

        # 4. Точный подсчёт байтов (клиент + библиотеки + ассеты)
        if v_data:
            try:
                client_size = v_data.get("downloads", {}).get("client", {}).get("size", 0)
                lib_size = sum(
                    lib.get("downloads", {}).get("artifact", {}).get("size", 0)
                    for lib in v_data.get("libraries", [])
                )
                asset_info = v_data.get("assetIndex", {})
                assets_size = asset_info.get("totalSize", 0) or asset_info.get("size", 0)
                total_bytes = client_size + lib_size + assets_size
                if total_bytes > 0:
                    mb = round(total_bytes / (1024 * 1024), 1)
                    sizes_cache[version] = mb
                    try:
                        os.makedirs(CACHE_DIR, exist_ok=True)
                        with open(sizes_cache_file, "w", encoding="utf-8") as f:
                            json.dump(sizes_cache, f)
                    except Exception:
                        pass
                    return mb
            except Exception:
                pass

        # 5. Умный fallback по поколениям Minecraft (если оффлайн)
        m = re.search(r'1\.(\d+)', version)
        if m:
            minor = int(m.group(1))
            if minor <= 5:
                return 52.0
            elif minor <= 12:
                return 175.0
            elif minor <= 17:
                return 380.0
            else:
                return 700.0

        return 180.0

    def installmc(self) -> None:
        version = self.ui.VersionComboBox.currentData()
        if not version:
            return

        L = self._lang

        # Проверка свободного места (минимум 2 ГБ)
        free_mb, enough = check_disk_space(MINECRAFT_DIRECTORY, 2048)
        if not enough:
            msg = QMessageBox(self)
            msg.setWindowTitle(t("no_space", L))
            msg.setText(
                f"{t('no_space', L)}\n"
                f"{t('free_space', L)} {free_mb:.0f} {t('mb', L)}\n"
                f"{t('required_space', L)} ~2048 {t('mb', L)}"
            )
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.exec()
            return

        # Диалог подтверждения установки с размером
        est_mb = self._get_version_estimated_mb(version)
        confirm_box = QMessageBox(self)
        confirm_box.setWindowTitle(t("confirm_install_title", L))
        confirm_box.setText(
            f"<b>{t('confirm_install_text', L)} {version}?</b>\n\n"
            f"• {t('estimated_size', L)} ~{est_mb:.0f} {t('mb', L)}\n"
            f"• {t('free_space', L)} {free_mb:.0f} {t('mb', L)}"
        )
        confirm_box.setIcon(QMessageBox.Icon.Question)
        yes_btn = confirm_box.addButton(t("download", L), QMessageBox.ButtonRole.YesRole)
        confirm_box.addButton(t("cancel", L), QMessageBox.ButtonRole.NoRole)
        confirm_box.exec()

        if confirm_box.clickedButton() != yes_btn:
            return

        self.ui.Progress.setText(f"{t('installing', L)} {version}...")
        self.ui.InstallProgressBar.setRange(0, 0)
        self.ui.InstallProgressBar.show()
        self.ui.DownLoadMinecraft.hide()
        self.ui.CancelInstallButton.show()
        self.ui.PlayMinecraft.setEnabled(False)

        self.install_thread = InstallThread(version)
        self.install_thread.update_status.connect(self.ui.Progress.setText)
        self.install_thread.update_progress.connect(self._on_install_progress)
        self.install_thread.install_finished.connect(self.on_install_finished)
        self.install_thread.error.connect(
            lambda e: self.show_error(f"{t('install_err', L)} {e}")
        )
        self.install_thread.start()

    def _on_install_progress(self, value: int) -> None:
        if value == -1:
            self.ui.InstallProgressBar.setRange(0, 0)
        else:
            self.ui.InstallProgressBar.setRange(0, 100)
            self.ui.InstallProgressBar.setValue(value)

    def on_install_finished(self) -> None:
        L = self._lang
        version = self.ui.VersionComboBox.currentData()
        self._animate_text_change(self.ui.Progress, t("install_done", L))
        self.ui.InstallProgressBar.hide()
        self.ui.DownLoadMinecraft.show()
        self.ui.CancelInstallButton.hide()
        self.ui.PlayMinecraft.setEnabled(True)

        self._show_notification(
            "LightLauncher", f"{t('install_done', L)} — {version}"
        )

        self.load_versions(force_refresh=False)
        if version:
            self.last_version = version

    def _cancel_install(self) -> None:
        if self.install_thread and self.install_thread.isRunning():
            self.install_thread.cancel()
            try:
                self.install_thread.install_finished.disconnect()
                self.install_thread.error.disconnect()
                self.install_thread.update_status.disconnect()
                self.install_thread.update_progress.disconnect()
            except Exception:
                pass
            self.ui.InstallProgressBar.hide()
            self.ui.DownLoadMinecraft.setEnabled(True)
            self.ui.PlayMinecraft.setEnabled(True)
            self.ui.CancelInstallButton.hide()
            self.ui.DownLoadMinecraft.show()
            self._animate_text_change(
                self.ui.Progress, t("install_cancelled", self._lang)
            )

    # ==============================================================
    # Удаление версии
    # ==============================================================

    def _delete_version(self) -> None:
        L = self._lang
        version = self.ui.VersionComboBox.currentData()
        if not version:
            return
        version_dir = os.path.join(MINECRAFT_DIRECTORY, "versions", version)
        if not os.path.isdir(version_dir):
            self.show_error(
                f"{t('delete_ver_title', L)} {version} {t('not_installed', L)}"
            )
            return

        msg = QMessageBox(self)
        msg.setWindowTitle(t("delete_ver_title", L))
        msg.setText(f"{t('delete_ver_ask', L)} {version}?")
        msg.setIcon(QMessageBox.Icon.Question)
        yes_btn = msg.addButton(t("yes", L), QMessageBox.ButtonRole.YesRole)
        msg.addButton(t("no", L), QMessageBox.ButtonRole.NoRole)
        msg.exec()

        if msg.clickedButton() == yes_btn:
            try:
                shutil.rmtree(version_dir)
                self.ui.Progress.setText(
                    f"{t('delete_ver_title', L)} {version} {t('deleted', L)}"
                )
                if self.last_version == version:
                    self.last_version = None
                    self.save_settings()
                self.load_versions(force_refresh=False)
            except Exception as e:
                self.show_error(f"{t('delete_err', L)} {e}")

    # ==============================================================
    # Прочее
    # ==============================================================

    def open_game_directory(self) -> None:
        path = os.path.realpath(MINECRAFT_DIRECTORY)
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

    def open_github(self) -> None:
        webbrowser.open("https://github.com/RanoGames/LightLauncher")

    def show_error(self, msg: str) -> None:
        QMessageBox.critical(self, "Error", msg)
        self.ui.Progress.setText("")

    def closeEvent(self, event) -> None:
        if self.install_thread and self.install_thread.isRunning():
            self.install_thread.cancel()

        if self.minecraft_process.state() == QProcess.ProcessState.Running:
            msg = QMessageBox(self)
            msg.setWindowTitle("Minecraft запущен")
            msg.setText("Игра Minecraft всё ещё работает.\nЗакрыть лаунчер и принудительно остановить игру?")
            msg.setIcon(QMessageBox.Icon.Question)
            yes_b = msg.addButton("Остановить игру", QMessageBox.ButtonRole.YesRole)
            msg.addButton("Отмена", QMessageBox.ButtonRole.NoRole)
            msg.exec()

            if msg.clickedButton() != yes_b:
                event.ignore()
                return
            self.minecraft_process.kill()

        self._remove_tray_icon()
        self.discord_rpc.stop()
        self._launch_timer.stop()

        if self.console_window:
            self.console_window.close()

        event.accept()
