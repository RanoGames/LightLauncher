"""Модуль автоматической установки мод-лоадеров Fabric и Forge."""

import logging
import re
from typing import Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)

from constants import MINECRAFT_DIRECTORY
from utils import t

logger = logging.getLogger("LightLauncher")


class ModloaderInstallThread(QThread):
    """Поток фоновой установки Fabric / Forge."""

    status_updated = pyqtSignal(str)
    progress_updated = pyqtSignal(int)
    install_finished = pyqtSignal(str)  # имя созданной версии
    error_occurred = pyqtSignal(str)

    def __init__(self, loader_type: str, mc_version: str, java_path: Optional[str] = None) -> None:
        super().__init__()
        self.loader_type = loader_type
        self.mc_version = mc_version
        self.java_path = java_path

    def run(self) -> None:
        try:
            # Извлекаем чистую версию Minecraft (например, из 1.20.1 или Forge 1.20.1)
            m = re.search(r'1\.\d+(?:\.\d+)?', self.mc_version)
            target_mc = m.group(0) if m else self.mc_version

            cb = {
                "setStatus": lambda s: self.status_updated.emit(str(s)),
                "setProgress": lambda p: self.progress_updated.emit(int(p)),
                "setMax": lambda m: None,
            }

            if self.loader_type == "fabric":
                import minecraft_launcher_lib.fabric as fabric
                self.status_updated.emit(f"Установка Fabric для Minecraft {target_mc}...")
                fabric.install_fabric(target_mc, MINECRAFT_DIRECTORY, callback=cb)
                self.install_finished.emit(f"Fabric ({target_mc})")

            elif self.loader_type == "forge":
                import minecraft_launcher_lib.forge as forge
                self.status_updated.emit(f"Поиск версии Forge для {target_mc}...")
                forge_ver = forge.find_forge_version(target_mc)
                if not forge_ver:
                    raise Exception(f"Не найдена стабильная версия Forge для Minecraft {target_mc}")

                self.status_updated.emit(f"Установка Forge {forge_ver}...")
                kwargs = {"callback": cb}
                if self.java_path:
                    kwargs["java"] = self.java_path
                forge.install_forge_version(forge_ver, MINECRAFT_DIRECTORY, **kwargs)
                self.install_finished.emit(f"Forge {forge_ver}")

            else:
                raise Exception(f"Неизвестный тип мод-лоадера: {self.loader_type}")

        except Exception as e:
            logger.error("Ошибка при установке мод-лоадера: %s", e)
            self.error_occurred.emit(str(e))


class ModloaderDialog(QDialog):
    """Диалог выбора и установки мод-лоадера для текущей версии игры."""

    installed = pyqtSignal()

    def __init__(self, mc_version: str, java_path: Optional[str] = None, parent=None, lang="ru") -> None:
        super().__init__(parent)
        self.mc_version = mc_version
        self.java_path = java_path
        self._lang = lang

        # Извлекаем чистую версию 1.X.X
        m = re.search(r'1\.\d+(?:\.\d+)?', mc_version)
        self.clean_ver = m.group(0) if m else mc_version

        self.setWindowTitle(t("install_modloader", lang))
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)

        title = QLabel(f"<b>Установка мод-лоадера для Minecraft {self.clean_ver}</b>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        layout.addSpacing(10)

        self.fabric_rb = QRadioButton("Fabric (рекомендуется — быстрый, меньше лагов)")
        self.fabric_rb.setChecked(True)
        self.forge_rb = QRadioButton("Forge (классический — для старых глобальных модов)")

        self.btn_group = QButtonGroup(self)
        self.btn_group.addButton(self.fabric_rb)
        self.btn_group.addButton(self.forge_rb)

        layout.addWidget(self.fabric_rb)
        layout.addWidget(self.forge_rb)
        layout.addSpacing(10)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # indeterminate
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        buttons_layout = QHBoxLayout()
        self.cancel_btn = QPushButton(t("cancel", lang))
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)
        self.install_btn = QPushButton(t("download", lang))
        self.install_btn.clicked.connect(self._start_install)

        buttons_layout.addWidget(self.cancel_btn)
        buttons_layout.addWidget(self.install_btn)
        layout.addLayout(buttons_layout)

        self._thread: Optional[ModloaderInstallThread] = None

    def _on_cancel_clicked(self) -> None:
        top = self.window()
        if top and top != self:
            top.close()
        else:
            self.reject()

    def _start_install(self) -> None:
        loader_type = "fabric" if self.fabric_rb.isChecked() else "forge"
        self.install_btn.setEnabled(False)
        self.fabric_rb.setEnabled(False)
        self.forge_rb.setEnabled(False)
        self.progress_bar.show()
        self.status_label.setText("Подготовка к установке...")

        self._thread = ModloaderInstallThread(loader_type, self.clean_ver, self.java_path)
        self._thread.status_updated.connect(self.status_label.setText)
        self._thread.install_finished.connect(self._on_finished)
        self._thread.error_occurred.connect(self._on_error)
        self._thread.start()

    def _on_finished(self, ver_name: str) -> None:
        self.status_label.setText(f"Успешно установлено: {ver_name}!")
        self.progress_bar.hide()
        self.cancel_btn.setText(t("close", self._lang))
        self.install_btn.hide()
        self.installed.emit()

    def _on_error(self, err: str) -> None:
        self.status_label.setText(f"Ошибка: {err}")
        self.progress_bar.hide()
        self.install_btn.setEnabled(True)
        self.fabric_rb.setEnabled(True)
        self.forge_rb.setEnabled(True)
