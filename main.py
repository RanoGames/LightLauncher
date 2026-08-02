import sys
import os
import json
import time
import tempfile
import threading
import subprocess
import shutil
import requests
import psutil
import traceback
import datetime

# PyQt6
from PyQt6.QtCore import QProcess, Qt, QThread, pyqtSignal, QSize, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import (QApplication, QMainWindow, QMessageBox, QDialog,
                             QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCheckBox, QSlider,
                             QPlainTextEdit, QWidget, QProgressBar, QComboBox, QGraphicsOpacityEffect,
                             QLineEdit)
from PyQt6 import QtGui
from PyQt6.QtGui import QIcon, QPixmap

# Minecraft Library
from minecraft_launcher_lib.install import install_minecraft_version
from minecraft_launcher_lib.utils import get_minecraft_directory
from minecraft_launcher_lib.command import get_minecraft_command

# Discord (опционально)
try:
    from pypresence import Presence as _DiscordPresence
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False

# Windows уведомления (опционально)
try:
    from winotify import Notification as WinNotification
    WIN_NOTIFY_AVAILABLE = True
except ImportError:
    WIN_NOTIFY_AVAILABLE = False

# Импорт дизайна
import design
from design import Ui_MainWindow

# --- КОНСТАНТЫ ---
MINECRAFT_DIRECTORY = get_minecraft_directory().replace('minecraft', 'minecraft')
SETTINGS_FILE = os.path.join(MINECRAFT_DIRECTORY, "settings.json")
CACHE_DIR = os.path.join(MINECRAFT_DIRECTORY, "cache")
VERSION_MANIFEST_URL = "https://launchermeta.mojang.com/mc/game/version_manifest_v2.json"
GITHUB_API_URL = "https://api.github.com/repos/RanoGames/LightLauncher/releases/latest"
DEFAULT_SETTINGS = {
    "filters": ["release"],
    "memory": 2048,
    "last_version": None,
    "show_console": False,
    "java_path": None,
    "nicknames": [],
    "last_nickname": None,
    "language": "auto",
    "jvm_args": ""
}

LANG = {
    "play": {"ru": "ИГРАТЬ", "en": "PLAY"},
    "download": {"ru": "СКАЧАТЬ", "en": "INSTALL"},
    "settings": {"ru": "НАСТРОЙКИ", "en": "SETTINGS"},
    "nickname_label": {"ru": "Имя игрока", "en": "Player name"},
    "version_label": {"ru": " Версия игры", "en": " Game version"},
    "nickname_tip": {"ru": "Введите или выберите никнейм", "en": "Enter or select a nickname"},
    "version_tip": {"ru": "Выберите версию Minecraft", "en": "Select Minecraft version"},
    "refresh_tip": {"ru": "Обновить список версий", "en": "Refresh version list"},
    "files_tip": {"ru": "Открыть папку с игрой", "en": "Open game folder"},
    "github_tip": {"ru": "Открыть GitHub проекта", "en": "Open project GitHub"},
    "delete_nick_tip": {"ru": "Удалить ник из списка", "en": "Remove nickname from list"},
    "delete_ver_tip": {"ru": "Удалить выбранную версию", "en": "Delete selected version"},
    "cancel_tip": {"ru": "Отменить установку", "en": "Cancel installation"},
    "cancel": {"ru": "ОТМЕНА", "en": "CANCEL"},
    "loading": {"ru": "Загрузка...", "en": "Loading..."},
    "size": {"ru": "Размер", "en": "Size"},
    "delete_ver_title": {"ru": "Удаление версии", "en": "Delete version"},
    "delete_ver_ask": {"ru": "Удалить версию", "en": "Delete version"},
    "yes": {"ru": "Да", "en": "Yes"},
    "no": {"ru": "Нет", "en": "No"},
    "not_installed": {"ru": "не установлена!", "en": "not installed!"},
    "deleted": {"ru": "удалена!", "en": "deleted!"},
    "delete_err": {"ru": "Ошибка удаления:", "en": "Delete error:"},
    "installing": {"ru": "Установка", "en": "Installing"},
    "install_done": {"ru": "Установка завершена!", "en": "Installation complete!"},
    "install_cancelled": {"ru": "Установка отменена!", "en": "Installation cancelled!"},
    "install_err": {"ru": "Ошибка установки:", "en": "Installation error:"},
    "java_not_found": {"ru": "Java не найдена! Установите Java.", "en": "Java not found! Install Java."},
    "launch_err": {"ru": "Ошибка запуска:", "en": "Launch error:"},
    "select_version": {"ru": "Выберите версию!", "en": "Select a version!"},
    "enter_nick": {"ru": "Введите никнейм!", "en": "Enter a nickname!"},
    "crash": {"ru": "Краш игры! Код:", "en": "Game crash! Code:"},
    "launcher_running": {"ru": "Minecraft запущен:", "en": "Minecraft running:"},
    "save": {"ru": "Сохранить", "en": "Save"},
    "auto": {"ru": "Авто", "en": "Auto"},
    "language": {"ru": "Язык", "en": "Language"},
    "auto_lang": {"ru": "Авто (из системы)", "en": "Auto (from system)"},
    "russian": {"ru": "Русский", "en": "Russian"},
    "english": {"ru": "Английский", "en": "English"},
    "version_types": {"ru": "Типы версий:", "en": "Version types:"},
    "releases": {"ru": "Релизы", "en": "Releases"},
    "snapshots": {"ru": "Снапшоты", "en": "Snapshots"},
    "old_betas": {"ru": "Старые беты", "en": "Old betas"},
    "old_alphas": {"ru": "Старые альфы", "en": "Old alphas"},
    "additional": {"ru": "Дополнительно:", "en": "Additional:"},
    "show_console": {"ru": "Показывать консоль отладки Minecraft", "en": "Show Minecraft debug console"},
    "memory": {"ru": "Память (RAM):", "en": "Memory (RAM):"},
    "mb": {"ru": "МБ", "en": "MB"},
    "calculating_size": {"ru": "Просчитываем размер...", "en": "Calculating size..."},
    "installed": {"ru": " [Установлена]", "en": " [Installed]"},
    "no_space": {"ru": "Недостаточно места на диске!", "en": "Not enough disk space!"},
    "free_space": {"ru": "Свободно:", "en": "Free:"},
    "required_space": {"ru": "Нужно:", "en": "Required:"},
    "jvm_args": {"ru": "Аргументы запуска:", "en": "Launch arguments:"},
    "jvm_args_tip": {"ru": "-Dsome.property=value", "en": "-Dsome.property=value"},
    "launching": {"ru": "Запуск Minecraft", "en": "Launching Minecraft"},
    "install_err": {"ru": "Ошибка установки:", "en": "Install error:"},
}
DISCORD_CLIENT_ID = "1420709615468810403"

LAUNCHER_VERSION = "0.43"


# --- БЛОК ОТЛОВЩИКА ОШИБОК ---
def log_uncaught_exceptions(ex_cls, ex, tb):
    text = ''.join(traceback.format_exception(ex_cls, ex, tb))
    print(text)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sys_info = (
        f"Launcher: v{LAUNCHER_VERSION}\n"
        f"Python: {sys.version}\n"
        f"Platform: {sys.platform}\n"
        f"MC Dir: {MINECRAFT_DIRECTORY}\n"
    )

    try:
        import platform
        sys_info += f"OS: {platform.platform()}\n"
    except Exception:
        pass

    try:
        import psutil
        sys_info += f"RAM: {psutil.virtual_memory().total // (1024*1024)} MB\n"
    except Exception:
        pass

    with open("crash_log.txt", "a", encoding="utf-8") as f:
        f.write(f"\n{'=' * 50}\n")
        f.write(f"[{timestamp}] CRITICAL ERROR\n")
        f.write(f"{'=' * 50}\n")
        f.write(f"{sys_info}\n")
        f.write(f"Exception: {ex_cls.__name__}: {ex}\n")
        f.write(f"{'-' * 50}\n")
        f.write(text)
        f.write(f"{'=' * 50}\n")

    if QApplication.instance():
        try:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setText("Критическая ошибка!")
            msg.setInformativeText(f"Лог сохранен в crash_log.txt\n\n{ex_cls.__name__}: {ex}")
            msg.setDetailedText(f"{sys_info}\n{text}")
            msg.exec()
        except:
            pass
    sys.exit(1)

sys.excepthook = log_uncaught_exceptions


if not os.path.exists(MINECRAFT_DIRECTORY): os.makedirs(MINECRAFT_DIRECTORY)
if not os.path.exists(CACHE_DIR): os.makedirs(CACHE_DIR)


# --- ФУНКЦИИ КЭШИРОВАНИЯ ---
def get_cached_path(filename):
    return os.path.join(CACHE_DIR, filename)


def is_cache_valid(filename, max_age_seconds=3600):
    path = get_cached_path(filename)
    if not os.path.exists(path): return False
    try:
        return (time.time() - os.path.getmtime(path)) < max_age_seconds
    except:
        return False


def version_tuple(v):
    parts = v.strip().split('.')
    return tuple(int(p) for p in parts)


def get_system_lang():
    try:
        import locale
        lang = locale.getlocale()[0]
        if lang and lang.startswith("ru"):
            return "ru"
    except Exception:
        pass
    return "en"


def t(key, lang="ru"):
    return LANG.get(key, {}).get(lang, LANG.get(key, {}).get("ru", key))


# --- Автообновление ---
# Для Inno Setup exe всегда на месте, путь известен
def _get_exe_dir():
    """Папка где лежит лаунчер"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


# --- КОМБОБОКС С ВЫБОМО ОДНИМ КЛИКОМ ---
class ClickComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.view().viewport().installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj == self.view().viewport() and event.type() == event.Type.MouseButtonPress:
            index = self.view().indexAt(event.pos())
            if index.isValid():
                self.setCurrentIndex(index.row())
                self.hidePopup()
                self.activated.emit(index.row())
                return True
        return super().eventFilter(obj, event)

# --- ОКНО КОНСОЛИ ---
class ConsoleWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Консоль отладки Minecraft")
        self.resize(800, 500)

        if os.path.exists("mclovin.ico"):
            self.setWindowIcon(QIcon("mclovin.ico"))

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
        layout.addWidget(self.text_edit)

        self.close_btn = QPushButton("Скрыть консоль")
        self.close_btn.clicked.connect(self.hide)
        layout.addWidget(self.close_btn)

    def append_log(self, text):
        self.text_edit.moveCursor(QtGui.QTextCursor.MoveOperation.End)
        self.text_edit.insertPlainText(text)
        self.text_edit.moveCursor(QtGui.QTextCursor.MoveOperation.End)


# --- ПОТОКИ ---
class DiscordRPC:
    def __init__(self, client_id):
        self.client_id = client_id
        self.running = False
        self._rpc = None
        self._thread = None

    def start(self, version: str):
        if not DISCORD_AVAILABLE:
            return
        self.stop()
        self._version = version
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        self.running = True
        while self.running:
            try:
                self._rpc = _DiscordPresence(self.client_id)
                self._rpc.connect()
                self._rpc.update(
                    state=f"Версия {self._version}",
                    details="Играет в Minecraft",
                    start=int(time.time()),
                    large_image="minecraft",
                    large_text="Light Minecraft Launcher"
                )
                while self.running:
                    time.sleep(15)
            except Exception:
                if self.running:
                    time.sleep(10)

    def stop(self):
        self.running = False
        if self._rpc:
            try:
                self._rpc.close()
            except Exception:
                pass
            self._rpc = None


class BackgroundLoader(QThread):
    loaded = pyqtSignal(QPixmap)
    def run(self):
        for name in ["background.png", "background.jpg"]:
            path = os.path.join(_get_exe_dir(), name)
            if os.path.exists(path):
                pixmap = QPixmap(path)
                if not pixmap.isNull():
                    self.loaded.emit(pixmap)
                    return


def get_optimal_ram():
    total_mb = int(psutil.virtual_memory().total / (1024 * 1024))
    if total_mb <= 4096:
        return max(1024, total_mb // 4)
    elif total_mb <= 8192:
        return total_mb // 3
    else:
        return min(total_mb // 2, 8192)


def check_disk_space(path, required_mb=2048):
    try:
        usage = psutil.disk_usage(path)
        free_mb = usage.free / (1024 * 1024)
        return free_mb, free_mb >= required_mb
    except Exception:
        return 0, False


class VersionSizeLoader(QThread):
    size_loaded = pyqtSignal(int)
    error_occurred = pyqtSignal(str)

    def __init__(self, version_manifest_url):
        super().__init__()
        self.version_manifest_url = version_manifest_url

    def run(self):
        try:
            resp = requests.get(self.version_manifest_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
            data = resp.json()
            total = 0
            if "client" in data.get("downloads", {}):
                total += data["downloads"]["client"].get("size", 0)
            if "assetIndex" in data:
                resp2 = requests.get(data["assetIndex"]["url"], headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
                asset_data = resp2.json()
                for obj in asset_data.get("objects", {}).values():
                    total += obj.get("size", 0)
            self.size_loaded.emit(total)
        except Exception:
            self.size_loaded.emit(0)


class VersionLoader(QThread):
    versions_loaded = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, filters=None, force_refresh=False):
        super().__init__()
        self.filters = filters if filters else ["release"]
        self.force_refresh = force_refresh

    def run(self):
        filename = "version_manifest.json"
        path = get_cached_path(filename)
        data = None
        try:
            if not self.force_refresh and is_cache_valid(filename, 3600):
                with open(path, "r") as f:
                    data = json.load(f)
            else:
                resp = requests.get(VERSION_MANIFEST_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
                data = resp.json()
                with open(path, "w") as f:
                    json.dump(data, f)
        except:
            if os.path.exists(path):
                with open(path, "r") as f:
                    data = json.load(f)

        if data:
            self.versions_loaded.emit([v['id'] for v in data['versions'] if v['type'] in self.filters])
        else:
            self.error_occurred.emit("Нет сети и кэша")


class InstallThread(QThread):
    update_status = pyqtSignal(str)
    update_progress = pyqtSignal(int)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, version):
        super().__init__()
        self.version = version
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        def callback(status):
            if self._cancelled:
                raise Exception("Установка отменена")
            self.update_status.emit(str(status))
            if "Downloading" in str(status):
                self.update_progress.emit(-1)

        try:
            install_minecraft_version(self.version, MINECRAFT_DIRECTORY,
                                      callback={"setStatus": callback})
            if not self._cancelled:
                self.finished.emit()
        except Exception as e:
            if not self._cancelled:
                self.error.emit(str(e))


# --- ПРОВЕРКА ОБНОВЛЕНИЙ ---
class UpdateChecker(QThread):
    update_available = pyqtSignal(str, str, str)  # version, body, download_url
    error_occurred = pyqtSignal(str)

    def run(self):
        try:
            resp = requests.get(GITHUB_API_URL, headers={"User-Agent": "LightLauncher"}, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            latest_version = data.get("tag_name", "").lstrip("v")
            body = data.get("body", "Нет описания")

            if not latest_version:
                self.error_occurred.emit("Нет данных о версии")
                return

            if version_tuple(latest_version) > version_tuple(LAUNCHER_VERSION):
                # Ищем .exe файл в assets
                download_url = None
                for asset in data.get("assets", []):
                    if asset["name"].endswith(".exe"):
                        download_url = asset["browser_download_url"]
                        break

                if download_url:
                    self.update_available.emit(latest_version, body, download_url)
        except Exception:
            pass


class UpdateDownloader(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)  # путь к скачанному setup.exe
    error = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            resp = requests.get(self.url, stream=True, timeout=120)
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

            self.finished.emit(setup_path)
        except Exception as e:
            self.error.emit(str(e))


# --- ОКНО ОБНОВЛЕНИЯ ---
class UpdateDialog(QDialog):
    def __init__(self, version, body, download_url, parent=None):
        super().__init__(parent)
        self.download_url = download_url
        self.setWindowTitle("Доступно обновление")
        self.setMinimumSize(400, 200)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        if os.path.exists("mclovin.ico"):
            self.setWindowIcon(QIcon("mclovin.ico"))

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

    def start_update(self):
        self.update_btn.setEnabled(False)
        self.skip_btn.setEnabled(False)
        self.progress_bar.show()
        self.status_label.setText("Скачивание обновления...")

        self.downloader = UpdateDownloader(self.download_url)
        self.downloader.progress.connect(self.on_progress)
        self.downloader.finished.connect(self.on_downloaded)
        self.downloader.error.connect(self.on_error)
        self.downloader.start()

    def on_progress(self, value):
        self.progress_bar.setValue(value)

    def on_downloaded(self, setup_path):
        self.status_label.setText("Установка обновления...")

        # Запускаем Inno Setup тихо — он заменит файлы в папке
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0

        subprocess.Popen(
            [setup_path, "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS"],
            startupinfo=si,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        # Перезапускаем лаунчер через 3 секунды (пока Inno Setup работает)
        QTimer.singleShot(3000, self._restart_launcher)

    def _restart_launcher(self):
        exe = os.path.abspath(sys.executable)
        subprocess.Popen(
            [exe],
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        QApplication.quit()

    def on_error(self, msg):
        self.status_label.setText(f"Ошибка: {msg}")
        self.update_btn.setEnabled(True)
        self.skip_btn.setEnabled(True)


# --- ОКНО НАСТРОЕК ---
class SettingsWindow(QDialog):
    def __init__(self, parent=None, current_filters=None, current_memory=2048, show_console=False, current_lang="auto", jvm_args=""):
        super().__init__(parent)
        L = current_lang if current_lang != "auto" else get_system_lang()
        self.setWindowTitle(t("settings", L))
        self.setMinimumSize(400, 520)
        self._lang = current_lang

        if os.path.exists("mclovin.ico"):
            self.setWindowIcon(QIcon("mclovin.ico"))

        if current_filters is None: current_filters = ["release"]
        self.old_filters = list(current_filters)
        layout = QVBoxLayout(self)

        # Язык
        self.lang_combo = QComboBox()
        self.lang_combo.addItem(t("auto_lang", L), "auto")
        self.lang_combo.addItem(t("russian", L), "ru")
        self.lang_combo.addItem(t("english", L), "en")
        idx = self.lang_combo.findData(current_lang)
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)
        self.lang_combo.currentIndexChanged.connect(self._on_lang_changed)

        # Фильтры
        self.release_cb = QCheckBox(t("releases", L))
        self.snapshot_cb = QCheckBox(t("snapshots", L))
        self.old_beta_cb = QCheckBox(t("old_betas", L))
        self.old_alpha_cb = QCheckBox(t("old_alphas", L))
        self.release_cb.setChecked("release" in current_filters)
        self.snapshot_cb.setChecked("snapshot" in current_filters)
        self.old_beta_cb.setChecked("old_beta" in current_filters)
        self.old_alpha_cb.setChecked("old_alpha" in current_filters)

        # Консоль
        self.console_cb = QCheckBox(t("show_console", L))
        self.console_cb.setChecked(show_console)

        # Память
        self.memory_slider = QSlider(Qt.Orientation.Horizontal)
        self.memory_slider.setMinimum(1024)
        max_ram = int(psutil.virtual_memory().total / (1024 * 1024))
        self.memory_slider.setMaximum(max_ram)
        self.memory_slider.setValue(current_memory)
        self.memory_value = QLabel(f"{current_memory} {t('mb', L)}")
        self.memory_slider.valueChanged.connect(lambda v: self.memory_value.setText(f"{v} {t('mb', L)}"))

        optimal = get_optimal_ram()
        self.auto_ram_btn = QPushButton(f"{t('auto', L)} ({optimal} {t('mb', L)})")
        self.auto_ram_btn.clicked.connect(lambda: self.memory_slider.setValue(optimal))

        # JVM аргументы
        self.jvm_args_input = QLineEdit(jvm_args)
        self.jvm_args_input.setPlaceholderText(t("jvm_args_tip", L))

        self.save_button = QPushButton(t("save", L))
        self.save_button.clicked.connect(self.accept)

        layout.addWidget(QLabel(t("language", L)))
        layout.addWidget(self.lang_combo)
        layout.addSpacing(5)
        layout.addWidget(QLabel(t("version_types", L)))
        layout.addWidget(self.release_cb)
        layout.addWidget(self.snapshot_cb)
        layout.addWidget(self.old_beta_cb)
        layout.addWidget(self.old_alpha_cb)
        layout.addSpacing(10)

        layout.addWidget(QLabel(t("additional", L)))
        layout.addWidget(self.console_cb)
        layout.addSpacing(10)

        layout.addWidget(QLabel(t("memory", L)))
        layout.addWidget(self.memory_value)
        layout.addWidget(self.memory_slider)
        layout.addWidget(self.auto_ram_btn)
        layout.addSpacing(10)

        layout.addWidget(QLabel(t("jvm_args", L)))
        layout.addWidget(self.jvm_args_input)
        layout.addWidget(self.save_button)

    def _on_lang_changed(self, index):
        self._lang = self.lang_combo.currentData()
        L = self._lang if self._lang != "auto" else get_system_lang()
        self.setWindowTitle(t("settings", L))

    def get_settings(self):
        filters = []
        if self.release_cb.isChecked(): filters.append("release")
        if self.snapshot_cb.isChecked(): filters.append("snapshot")
        if self.old_alpha_cb.isChecked(): filters.append("old_alpha")
        if self.old_beta_cb.isChecked(): filters.append("old_beta")
        return filters, self.memory_slider.value(), self.console_cb.isChecked(), self.lang_combo.currentData(), self.jvm_args_input.text().strip()


# --- ГЛАВНОЕ ОКНО ---

class Launcher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self._lang = "ru"

        # Заменяем комбобоксы на ClickComboBox (выбор одним кликом)
        old_nick = self.ui.Nickname
        nick = ClickComboBox(self)
        nick.setEditable(old_nick.isEditable())
        nick.setGeometry(old_nick.geometry())
        nick.setObjectName(old_nick.objectName())
        nick.setFont(QtGui.QFont("Arial", 12, QtGui.QFont.Weight.Bold))
        nick.setStyleSheet("QComboBox { font: bold 12pt Arial; } QComboBox QAbstractItemView { font: bold 12pt Arial; }")
        nick.setToolTip("Введите или выберите никнейм")
        old_nick.deleteLater()
        self.ui.Nickname = nick

        old_ver = self.ui.VersionComboBox
        ver = ClickComboBox(self)
        ver.setEditable(old_ver.isEditable())
        ver.setGeometry(old_ver.geometry())
        ver.setObjectName(old_ver.objectName())
        ver.setFont(QtGui.QFont("Arial", 12, QtGui.QFont.Weight.Bold))
        ver.setStyleSheet("QComboBox { font: bold 12pt Arial; } QComboBox QAbstractItemView { font: bold 12pt Arial; }")
        ver.setToolTip("Выберите версию Minecraft")
        old_ver.deleteLater()
        self.ui.VersionComboBox = ver

        if os.path.exists("mclovin.ico"):
            self.setWindowIcon(QIcon("mclovin.ico"))

        if os.path.exists("folder.png"):
            self.ui.FilesButton.setIcon(QIcon('folder.png'))
            self.ui.FilesButton.setIconSize(QSize(40, 40))
        else:
            self.ui.FilesButton.setText("\U0001f4c2")

        if os.path.exists("github.png"):
            self.ui.GitHubButton.setIcon(QIcon('github.png'))
            self.ui.GitHubButton.setIconSize(QSize(40, 40))
        else:
            self.ui.GitHubButton.setText("GitHub")

        # Полупрозрачный фон кнопок
        self._apply_button_transparency()

        # Язык
        if self._lang == "auto":
            self._lang = get_system_lang()
        self._apply_language()

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

        # Никнейм: сохранять только при выборе из списка или завершении ввода
        self.ui.Nickname.activated.connect(self._on_nickname_activated)
        self._nick_timer = QTimer(self)
        self._nick_timer.setSingleShot(True)
        self._nick_timer.setInterval(1000)
        self._nick_timer.timeout.connect(self._save_current_nickname)
        self.ui.Nickname.lineEdit().textChanged.connect(lambda: self._nick_timer.start())

        # Фикс: клик по line edit сразу открывает dropdown (без двойного клика)
        line_edit = self.ui.Nickname.lineEdit()
        line_edit.installEventFilter(self)

        self.minecraft_process = QProcess(self)
        self.minecraft_process.finished.connect(self.on_minecraft_exit)

        self.discord_rpc = DiscordRPC(DISCORD_CLIENT_ID)
        self.install_thread = None
        self._version_size_loader = None
        self.load_settings()

        self.bg_loader = BackgroundLoader()
        self.bg_loader.loaded.connect(self.set_background_image)
        self.bg_loader.start()

        # Загрузка версий
        self.ui.VersionComboBox.setPlaceholderText("Загрузка...")
        self.ui.VersionComboBox.setEnabled(False)
        self.load_versions()

        # Окно консоли
        self.console_window = None

        # Профили никнеймов
        self._setup_nicknames()

        # Java info
        self._detect_java()

        # Таймер запуска
        self._start_time = None
        self._launch_timer = QTimer(self)
        self._launch_timer.timeout.connect(self._update_launch_timer)

        # Версия лаунчера
        self.ui.JavaInfoLabel.setText(f"v{LAUNCHER_VERSION}")

        # Проверка обновлений при запуске
        self._check_for_updates()

    def eventFilter(self, obj, event):
        if obj == self.ui.Nickname.lineEdit() and event.type() == event.Type.MouseButtonPress:
            self.ui.Nickname.showPopup()
            return True
        return super().eventFilter(obj, event)

    def _check_for_updates(self):
        self._update_checker = UpdateChecker()
        self._update_checker.update_available.connect(self._on_update_available)
        self._update_checker.start()

    def _on_update_available(self, version, body, download_url):
        dialog = UpdateDialog(version, body, download_url, parent=self)
        dialog.exec()

    def _setup_nicknames(self):
        self.ui.Nickname.blockSignals(True)
        self.ui.Nickname.clear()
        for nick in self._nicknames:
            self.ui.Nickname.addItem(nick)
        if self._last_nickname and self._last_nickname in self._nicknames:
            self.ui.Nickname.setCurrentText(self._last_nickname)
        self.ui.Nickname.blockSignals(False)

    def _on_nickname_activated(self, index):
        nick = self.ui.Nickname.currentText()
        if nick and nick not in self._nicknames:
            self._nicknames.append(nick)
        self._last_nickname = nick
        self.save_settings()

    def _save_current_nickname(self):
        nick = self.ui.Nickname.currentText().strip()
        if not nick:
            return
        if nick not in self._nicknames:
            self._nicknames.append(nick)
        self._last_nickname = nick
        self.save_settings()

    def _apply_button_transparency(self):
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
        for btn in [self.ui.SettingsButton, self.ui.DownLoadMinecraft,
                     self.ui.PlayMinecraft, self.ui.RefreshVersionsButton,
                     self.ui.FilesButton, self.ui.GitHubButton,
                     self.ui.DeleteNicknameButton, self.ui.DeleteVersionButton,
                     self.ui.CancelInstallButton]:
            btn.setStyleSheet(style)

    def _apply_language(self):
        L = self._lang
        self.ui.PlayMinecraft.setText(t("play", L))
        self.ui.DownLoadMinecraft.setText(t("download", L))
        self.ui.SettingsButton.setText(t("settings", L))
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

        # Обновить размер версии на текущем языке
        current = self.ui.VersionComboBox.currentData()
        if current:
            self._load_version_size(current)

    def _fade_in(self, widget, duration=500):
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

    def _fade_out(self, widget, duration=300, callback=None):
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

    def _animate_text_change(self, label, text, duration=400):
        if not isinstance(label, QLabel):
            label.setText(text)
            return
        def set_text():
            label.setText(text)
            self._fade_in(label, duration)
        self._fade_out(label, duration // 2, set_text)

    def _show_notification(self, title, message):
        if not WIN_NOTIFY_AVAILABLE:
            return
        try:
            toast = WinNotification(
                app_id="LightLauncher",
                title=title,
                msg=message,
                duration="short"
            )
            toast.show()
        except Exception as e:
            print(f"Notification error: {e}")

    def _delete_current_nickname(self):
        nick = self.ui.Nickname.currentText().strip()
        if not nick:
            return
        if nick in self._nicknames:
            self._nicknames.remove(nick)
        if self._last_nickname == nick:
            self._last_nickname = self._nicknames[-1] if self._nicknames else None
        self._setup_nicknames()
        self.save_settings()

    def _detect_java(self):
        java_path = getattr(self, "java_path_cache", None)
        if not java_path:
            try:
                from minecraft_launcher_lib.utils import get_java_executable
                java_path = get_java_executable()
                self.java_path_cache = java_path
            except Exception:
                java_path = None
                self.java_path_cache = None

        if java_path:
            try:
                result = subprocess.run(
                    [java_path, "-version"],
                    capture_output=True, text=True, timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                ver_line = result.stderr.split('\n')[0]
            except Exception:
                pass
            short_path = java_path if len(java_path) < 50 else "..." + java_path[-47:]
            self.ui.JavaInfoLabel.setText(f"Java: {short_path}  |  v{LAUNCHER_VERSION}")
        else:
            self.ui.JavaInfoLabel.setText(f"Java: не найдена!  |  v{LAUNCHER_VERSION}")

    def _on_version_changed(self, index):
        version = self.ui.VersionComboBox.currentData()
        if not version:
            return
        self.last_version = version
        self.save_settings()
        self._load_version_size(version)

    def set_background_image(self, pixmap):
        if not hasattr(self, 'bg_label'):
            self.bg_label = QLabel(self)
            self.bg_label.setScaledContents(True)
            self.bg_label.lower()
        self.bg_label.setPixmap(pixmap)
        self.bg_label.resize(self.size())
        self.bg_label.show()

    def resizeEvent(self, event):
        if hasattr(self, 'bg_label'):
            self.bg_label.resize(self.size())
        super().resizeEvent(event)

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    data = json.load(f)
                    self.version_filters = data.get("filters", DEFAULT_SETTINGS["filters"])
                    self.allocated_memory = data.get("memory", DEFAULT_SETTINGS["memory"])
                    self.last_version = data.get("last_version", None)
                    self.show_console_opt = data.get("show_console", False)
                    self.java_path_cache = data.get("java_path", None)
                    self._nicknames = data.get("nicknames", [])
                    self._last_nickname = data.get("last_nickname", None)
                    self._lang = data.get("language", DEFAULT_SETTINGS["language"])
                    self._jvm_args = data.get("jvm_args", DEFAULT_SETTINGS["jvm_args"])
            except:
                self.set_defaults()
        else:
            self.set_defaults()

    def set_defaults(self):
        self.version_filters = DEFAULT_SETTINGS["filters"]
        self.allocated_memory = get_optimal_ram()
        self.last_version = DEFAULT_SETTINGS["last_version"]
        self.show_console_opt = DEFAULT_SETTINGS["show_console"]
        self.java_path_cache = DEFAULT_SETTINGS["java_path"]
        self._nicknames = list(DEFAULT_SETTINGS["nicknames"])
        self._last_nickname = DEFAULT_SETTINGS["last_nickname"]
        self._lang = DEFAULT_SETTINGS["language"]
        self._jvm_args = DEFAULT_SETTINGS["jvm_args"]

    def save_settings(self):
        data = {
            "filters": self.version_filters,
            "memory": self.allocated_memory,
            "last_version": self.last_version,
            "show_console": self.show_console_opt,
            "java_path": getattr(self, "java_path_cache", None),
            "nicknames": self._nicknames,
            "last_nickname": self._last_nickname,
            "language": self._lang,
            "jvm_args": self._jvm_args
        }
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Ошибка сохранения: {e}")

    def open_settings(self):
        dialog = SettingsWindow(self, self.version_filters, self.allocated_memory, self.show_console_opt, self._lang, self._jvm_args)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_filters, self.allocated_memory, self.show_console_opt, new_lang, jvm_args = dialog.get_settings()

            current_version = self.ui.VersionComboBox.currentData()
            if current_version:
                self.last_version = current_version

            self.version_filters = new_filters
            self._lang = new_lang
            self._jvm_args = jvm_args
            if self._lang == "auto":
                self._lang = get_system_lang()
            self._apply_language()
            self.save_settings()

            if new_filters != dialog.old_filters:
                self.load_versions()

    def load_versions(self, force_refresh=False):
        self.ui.VersionComboBox.clear()
        self.ui.VersionComboBox.addItem("Загрузка...")
        self.ui.VersionComboBox.setEnabled(False)
        self.ver_loader = VersionLoader(filters=self.version_filters, force_refresh=force_refresh)
        self.ver_loader.versions_loaded.connect(self.populate_versions)
        self.ver_loader.error_occurred.connect(self.show_error)
        self.ver_loader.start()

    def force_refresh_versions(self):
        self.load_versions(force_refresh=True)

    def populate_versions(self, versions):
        self.ui.VersionComboBox.clear()

        installed = set()
        versions_dir = os.path.join(MINECRAFT_DIRECTORY, "versions")
        if os.path.isdir(versions_dir):
            for d in os.listdir(versions_dir):
                if os.path.isdir(os.path.join(versions_dir, d)):
                    installed.add(d)

        L = self._lang
        added = set()
        for v in versions:
            label = f"{v}{t('installed', L)}" if v in installed else v
            self.ui.VersionComboBox.addItem(label, v)
            added.add(v)

        # Добавляем кастомные версии (Forge/Fabric) из папки versions
        for v in sorted(installed):
            if v not in added:
                self.ui.VersionComboBox.addItem(f"{v}{t('installed', L)}", v)

        self.ui.VersionComboBox.setEnabled(True)

        if self.last_version and self.last_version in versions:
            idx = versions.index(self.last_version)
            self.ui.VersionComboBox.setCurrentIndex(idx)
        else:
            self.ui.VersionComboBox.setCurrentIndex(0)

        current = self.ui.VersionComboBox.currentData()
        if current:
            self._load_version_size(current)

    def show_error(self, msg):
        QMessageBox.critical(self, "Ошибка", msg)
        self.ui.Progress.setText("")

    # --- ЗАПУСК ИГРЫ ---
    def runmc(self):
        version = self.ui.VersionComboBox.currentData()
        username = self.ui.Nickname.currentText()
        if not version:
            self.show_error(t("select_version", self._lang))
            return
        if not username:
            self.show_error("Введите никнейм!")
            return

        self.ui.Progress.setText(f"{t('launching', self._lang)}...")
        self.hide()

        self.last_version = version
        self.save_settings()

        java_path = getattr(self, "java_path_cache", None)
        if not java_path:
            try:
                from minecraft_launcher_lib.utils import get_java_executable
                java_path = get_java_executable()
                self.java_path_cache = java_path
            except Exception:
                self.show()
                self.show_error(t("java_not_found", self._lang))
                return

        if self.show_console_opt:
            if self.console_window is None:
                self.console_window = ConsoleWindow()
            self.console_window.show()
            self.console_window.activateWindow()

        mcoptions = {
            'username': username,
            'jvmArguments': [f"-Xmx{self.allocated_memory}M"] + ([self._jvm_args] if self._jvm_args else []),
            'launcherName': "LightLauncher",
            'launcherVersion': LAUNCHER_VERSION,
            'executablePath': java_path
        }

        try:
            command = get_minecraft_command(version=version, minecraft_directory=MINECRAFT_DIRECTORY, options=mcoptions)

            self.minecraft_process.setProgram(command[0])
            self.minecraft_process.setArguments(command[1:])

            if self.show_console_opt:
                self.minecraft_process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
                try:
                    self.minecraft_process.readyReadStandardOutput.disconnect()
                except:
                    pass
                self.minecraft_process.readyReadStandardOutput.connect(self.write_to_console)

            self.minecraft_process.start()
            self.discord_rpc.start(version)

            self._start_time = time.time()
            self._launch_timer.start(1000)

        except Exception as e:
            self.show()
            self.show_error(f"Ошибка запуска: {e}")

    def _update_launch_timer(self):
        if self._start_time:
            elapsed = int(time.time() - self._start_time)
            mins, secs = divmod(elapsed, 60)
            hours, mins = divmod(mins, 60)
            if hours > 0:
                self.ui.Progress.setText(f"Minecraft запущен: {hours}ч {mins}м {secs}с")
            else:
                self.ui.Progress.setText(f"Minecraft запущен: {mins}м {secs}с")

    def write_to_console(self):
        data = self.minecraft_process.readAllStandardOutput().data()
        try:
            text = data.decode('utf-8', errors='ignore')
        except:
            text = str(data)

        if self.console_window:
            self.console_window.append_log(text)

    def on_minecraft_exit(self, exit_code, *args):
        self.discord_rpc.stop()
        self._launch_timer.stop()
        self._start_time = None

        try:
            if exit_code != 0:
                self.ui.Progress.setText(f"Краш игры! Код: {exit_code}")
            else:
                self.ui.Progress.setText("")
            self.show()
        except RuntimeError:
            pass

    def closeEvent(self, event):
        try:
            self.minecraft_process.finished.disconnect()
        except:
            pass

        if self.minecraft_process.state() == QProcess.ProcessState.Running:
            self.minecraft_process.kill()

        self.discord_rpc.stop()
        self._launch_timer.stop()

        if self.console_window:
            self.console_window.close()

        event.accept()

    def installmc(self):
        version = self.ui.VersionComboBox.currentData()
        if not version:
            return

        L = self._lang

        # Проверка свободного места (минимум 2 ГБ)
        free_mb, enough = check_disk_space(MINECRAFT_DIRECTORY, 2048)
        if not enough:
            msg = QMessageBox(self)
            msg.setWindowTitle(t("no_space", L))
            msg.setText(f"{t('no_space', L)}\n{t('free_space', L)} {free_mb:.0f} {t('mb', L)}\n{t('required_space', L)} ~2048 {t('mb', L)}")
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.exec()
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
        self.install_thread.finished.connect(self.on_install_finished)
        self.install_thread.error.connect(lambda e: self.show_error(f"{t('install_err', L)} {e}"))
        self.install_thread.start()

    def _on_install_progress(self, value):
        if value == -1:
            self.ui.InstallProgressBar.setRange(0, 0)
        else:
            self.ui.InstallProgressBar.setRange(0, 100)
            self.ui.InstallProgressBar.setValue(value)

    def on_install_finished(self):
        L = self._lang
        version = self.ui.VersionComboBox.currentData()
        self._animate_text_change(self.ui.Progress, t("install_done", L))
        self.ui.InstallProgressBar.hide()
        self.ui.DownLoadMinecraft.show()
        self.ui.CancelInstallButton.hide()
        self.ui.PlayMinecraft.setEnabled(True)

        # Windows уведомление
        self._show_notification(
            "LightLauncher",
            f"{t('install_done', L)} — {version}"
        )

        # Обновить список чтобы появилась отметка [Установлена]
        self.load_versions(force_refresh=False)
        if version:
            self.last_version = version

    def open_game_directory(self):
        path = os.path.realpath(MINECRAFT_DIRECTORY)
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

    def _load_version_size(self, version):
        self.ui.Progress.setText(t("calculating_size", self._lang))
        filename = "version_manifest.json"
        path = get_cached_path(filename)
        if not os.path.exists(path):
            return
        try:
            with open(path, "r") as f:
                manifest = json.load(f)
            version_info = next((v for v in manifest['versions'] if v['id'] == version), None)
            if not version_info:
                return
            self._version_size_loader = VersionSizeLoader(version_info['url'])
            self._version_size_loader.size_loaded.connect(self._on_version_size_loaded)
            self._version_size_loader.start()
        except Exception:
            pass

    def _on_version_size_loaded(self, total_bytes):
        L = self._lang
        if total_bytes > 0:
            mb = total_bytes / (1024 * 1024)
            self._animate_text_change(self.ui.Progress, f"~{mb:.0f} {t('mb', L)}", 300)
        else:
            self._animate_text_change(self.ui.Progress, "", 300)

    def _delete_version(self):
        L = self._lang
        version = self.ui.VersionComboBox.currentData()
        if not version:
            return
        version_dir = os.path.join(MINECRAFT_DIRECTORY, "versions", version)
        if not os.path.isdir(version_dir):
            self.show_error(f"{t('delete_ver_title', L)} {version} {t('not_installed', L)}")
            return

        msg = QMessageBox(self)
        msg.setWindowTitle(t("delete_ver_title", L))
        msg.setText(f"{t('delete_ver_ask', L)} {version}?")
        msg.setIcon(QMessageBox.Icon.Question)
        yes_btn = msg.addButton(t("yes", L), QMessageBox.ButtonRole.YesRole)
        no_btn = msg.addButton(t("no", L), QMessageBox.ButtonRole.NoRole)
        msg.exec()
        if msg.clickedButton() == yes_btn:
            version_dir = os.path.join(MINECRAFT_DIRECTORY, "versions", version)
            try:
                shutil.rmtree(version_dir)
                self.ui.Progress.setText(f"{t('delete_ver_title', L)} {version} {t('deleted', L)}")
                QTimer.singleShot(2000, lambda: self._load_version_size(version))
                # Обновить список чтобы убрать отметку [Установлена]
                current = self.ui.VersionComboBox.currentData()
                self.load_versions(force_refresh=False)
                if current and current != version:
                    self.last_version = current
            except Exception as e:
                self.show_error(f"{t('delete_err', L)} {e}")

    def _cancel_install(self):
        if self.install_thread and self.install_thread.isRunning():
            self.install_thread.cancel()
            self.install_thread.wait(3000)
            self.ui.InstallProgressBar.hide()
            self.ui.DownLoadMinecraft.setEnabled(True)
            self.ui.PlayMinecraft.setEnabled(True)
            self.ui.CancelInstallButton.hide()
            self.ui.DownLoadMinecraft.show()
            self._animate_text_change(self.ui.Progress, t("install_cancelled", self._lang))

    def open_github(self):
        import webbrowser
        webbrowser.open("https://github.com/RanoGames/LightLauncher")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = Launcher()
    window.show()
    sys.exit(app.exec())
