"""Фоновые потоки: загрузка версий, установка Minecraft, фон."""

import json
import logging
import os
from typing import Optional

from minecraft_launcher_lib.install import install_minecraft_version
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage

from constants import MINECRAFT_DIRECTORY, VERSION_MANIFEST_URL
from utils import get_cached_path, get_exe_dir, get_http_session, is_cache_valid

logger = logging.getLogger("LightLauncher")


class BackgroundLoader(QThread):
    """Загружает фоновое изображение в отдельном потоке."""

    loaded = pyqtSignal(QImage)

    def __init__(self, custom_path: Optional[str] = None) -> None:
        super().__init__()
        self.custom_path = custom_path

    def run(self) -> None:
        if self.custom_path and os.path.exists(self.custom_path):
            img = QImage(self.custom_path)
            if not img.isNull():
                self.loaded.emit(img)
                return

        for name in (
            os.path.join("Backgrounds", "01_Night_Mountains.jpg"),
            "background.jpg",
            "background.png",
        ):
            path = os.path.join(get_exe_dir(), name)
            if os.path.exists(path):
                img = QImage(path)
                if not img.isNull():
                    self.loaded.emit(img)
                    return


class VersionLoader(QThread):
    """Загружает список версий Minecraft (с кэшированием)."""

    versions_loaded = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, filters: list[str] | None = None,
                 force_refresh: bool = False) -> None:
        super().__init__()
        self.filters = filters if filters else ["release"]
        self.force_refresh = force_refresh

    def run(self) -> None:
        filename = "version_manifest.json"
        path = get_cached_path(filename)
        data = None

        try:
            if not self.force_refresh and is_cache_valid(filename, 3600):
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
            else:
                session = get_http_session()
                resp = session.get(VERSION_MANIFEST_URL, timeout=10)
                data = resp.json()
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f)
        except Exception as e:                          # Bug #8 fix
            logger.warning("Ошибка загрузки манифеста: %s", e)
            if os.path.exists(path):
                try:
                    with open(path, encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    pass

        if data:
            self.versions_loaded.emit(
                [v["id"] for v in data["versions"] if v["type"] in self.filters]
            )
        else:
            self.error_occurred.emit("Нет сети и кэша")


class InstallThread(QThread):
    """Устанавливает конкретную версию Minecraft."""

    update_status = pyqtSignal(str)
    update_progress = pyqtSignal(int)
    install_finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, version: str) -> None:
        super().__init__()
        self.version = version
        self._cancelled = False

    def cancel(self) -> None:
        """Запрашивает отмену установки."""
        self._cancelled = True

    def run(self) -> None:
        total_max = 0

        def set_status(status):
            if self._cancelled:
                raise Exception("Установка отменена")
            self.update_status.emit(str(status))

        def set_progress(curr):
            if self._cancelled:
                raise Exception("Установка отменена")
            nonlocal total_max
            if total_max > 0:
                self.update_progress.emit(int(curr * 100 / total_max))
            else:
                self.update_progress.emit(-1)

        def set_max(m):
            nonlocal total_max
            total_max = m

        try:
            install_minecraft_version(
                self.version, MINECRAFT_DIRECTORY,
                callback={
                    "setStatus": set_status,
                    "setProgress": set_progress,
                    "setMax": set_max,
                },
            )
            if not self._cancelled:
                self.install_finished.emit()
        except Exception as e:
            if not self._cancelled:
                self.error.emit(str(e))


class JavaInstallThread(QThread):
    """Скачивает и устанавливает Mojang Java Runtime в фоновом потоке."""

    update_status = pyqtSignal(str)
    update_progress = pyqtSignal(int)
    install_finished = pyqtSignal(str)  # возвращает путь к исполняемому файлу javaw.exe
    error = pyqtSignal(str)

    def __init__(self, jvm_version: str) -> None:
        super().__init__()
        self.jvm_version = jvm_version
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        import minecraft_launcher_lib.runtime as rt

        from java_manager import get_runtime_java_path

        total_max = 0

        def set_status(status):
            if self._cancelled:
                raise Exception("Установка отменена")
            self.update_status.emit(str(status))

        def set_progress(curr):
            if self._cancelled:
                raise Exception("Установка отменена")
            nonlocal total_max
            if total_max > 0:
                self.update_progress.emit(int(curr * 100 / total_max))
            else:
                self.update_progress.emit(-1)

        def set_max(m):
            nonlocal total_max
            total_max = m

        try:
            rt.install_jvm_runtime(
                self.jvm_version,
                MINECRAFT_DIRECTORY,
                callback={
                    "setStatus": set_status,
                    "setProgress": set_progress,
                    "setMax": set_max,
                },
            )
            if not self._cancelled:
                path = get_runtime_java_path(self.jvm_version) or ""
                self.install_finished.emit(path)
        except Exception as e:
            if not self._cancelled:
                self.error.emit(str(e))

