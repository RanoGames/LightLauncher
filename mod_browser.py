"""Каталог и поиск модов через открытое API Modrinth."""

import json
import logging
import os
import re
import urllib.parse
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from constants import MINECRAFT_DIRECTORY
from utils import get_http_session

logger = logging.getLogger("LightLauncher")


class ModSearchThread(QThread):
    """Поток поиска модов на Modrinth."""

    results_loaded = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, query: str, mc_version: str, loader: str = "fabric") -> None:
        super().__init__()
        self.query = query
        self.mc_version = mc_version
        self.loader = loader.lower()

    def run(self) -> None:
        try:
            m = re.search(r'1\.\d+(?:\.\d+)?', self.mc_version)
            clean_ver = m.group(0) if m else self.mc_version

            facets = [["project_type:mod"]]
            if clean_ver:
                facets.append([f"versions:{clean_ver}"])
            if self.loader and self.loader != "all":
                facets.append([f"categories:{self.loader}"])

            params = {
                "query": self.query,
                "facets": json.dumps(facets),
                "limit": 20,
            }
            url = f"https://api.modrinth.com/v2/search?{urllib.parse.urlencode(params)}"
            session = get_http_session()
            resp = session.get(url, timeout=10)
            if resp.status_code != 200:
                self.error_occurred.emit(f"Modrinth ответил кодом {resp.status_code}")
                return

            data = resp.json()
            hits = data.get("hits", [])
            self.results_loaded.emit(hits)
        except Exception as e:
            logger.warning("Ошибка поиска на Modrinth: %s", e)
            self.error_occurred.emit(str(e))


class ModDownloadThread(QThread):
    """Поток скачивания .jar файла мода в папку mods."""

    status_updated = pyqtSignal(str)
    download_finished = pyqtSignal(str)  # filename
    error_occurred = pyqtSignal(str)

    def __init__(self, project_id: str, mod_title: str, mc_version: str, loader: str) -> None:
        super().__init__()
        self.project_id = project_id
        self.mod_title = mod_title
        self.mc_version = mc_version
        self.loader = loader.lower()

    def run(self) -> None:
        try:
            m = re.search(r'1\.\d+(?:\.\d+)?', self.mc_version)
            clean_ver = m.group(0) if m else self.mc_version

            session = get_http_session()
            self.status_updated.emit(f"Поиск совместимого файла {self.mod_title}...")

            params = {}
            if self.loader and self.loader != "all":
                params["loaders"] = json.dumps([self.loader])
            if clean_ver:
                params["game_versions"] = json.dumps([clean_ver])

            ver_url = f"https://api.modrinth.com/v2/project/{self.project_id}/version"
            if params:
                ver_url += f"?{urllib.parse.urlencode(params)}"

            resp = session.get(ver_url, timeout=10)
            if resp.status_code != 200:
                raise Exception(f"Ошибка получения версий мода (HTTP {resp.status_code})")

            versions = resp.json()
            if not versions:
                raise Exception("Не найден подходящий файл для вашей версии Minecraft / мод-лоадера")

            # Берём самый свежий релиз
            target_file = None
            for v in versions:
                files = v.get("files", [])
                for f in files:
                    if f.get("primary", False):
                        target_file = f
                        break
                if target_file:
                    break
                if files:
                    target_file = files[0]
                    break

            if not target_file:
                raise Exception("В релизе не найдено файлов для скачивания")

            dl_url = target_file["url"]
            filename = target_file["filename"]

            mods_dir = os.path.join(MINECRAFT_DIRECTORY, "mods")
            os.makedirs(mods_dir, exist_ok=True)
            save_path = os.path.join(mods_dir, filename)

            self.status_updated.emit(f"Скачивание {filename}...")
            r_file = session.get(dl_url, stream=True, timeout=60)
            r_file.raise_for_status()

            with open(save_path, "wb") as f:
                for chunk in r_file.iter_content(chunk_size=16384):
                    f.write(chunk)

            self.download_finished.emit(filename)
        except Exception as e:
            logger.error("Ошибка скачивания мода: %s", e)
            self.error_occurred.emit(str(e))


class ModItemWidget(QWidget):
    """Виджет отображения мода в списке с кнопкой быстрой установки."""

    install_requested = pyqtSignal(str, str)  # project_id, title

    def __init__(self, mod_data: dict, parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        info_layout = QVBoxLayout()
        title = QLabel(f"<b>{mod_data.get('title', 'Без названия')}</b> <span style='color:#888;'>от {mod_data.get('author', 'автор')}</span>")
        desc = QLabel(mod_data.get("description", ""))
        desc.setStyleSheet("color: #bbb; font-size: 11px;")
        desc.setWordWrap(True)

        downloads = mod_data.get("downloads", 0)
        d_str = f"{downloads:,}".replace(",", " ")
        stats = QLabel(f"<span style='color:#4caf50;'>⬇ {d_str} скачиваний</span>")
        stats.setStyleSheet("font-size: 10px;")

        info_layout.addWidget(title)
        info_layout.addWidget(desc)
        info_layout.addWidget(stats)

        self.install_btn = QPushButton("Скачать")
        self.install_btn.setFixedSize(80, 36)
        self.install_btn.setStyleSheet("""
            QPushButton {
                background-color: #2e7d32;
                color: white;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #388e3c; }
            QPushButton:disabled { background-color: #555; }
        """)
        self.install_btn.clicked.connect(
            lambda: self.install_requested.emit(mod_data["project_id"], mod_data["title"])
        )

        layout.addLayout(info_layout)
        layout.addWidget(self.install_btn)


class ModBrowserDialog(QDialog):
    """Окно каталога модов с поиском и установкой."""

    def __init__(self, mc_version: str, parent=None, lang: str = "ru") -> None:
        super().__init__(parent)
        self.mc_version = mc_version
        self._lang = lang

        self.setWindowTitle("Каталог модов Modrinth")
        self.resize(650, 520)

        layout = QVBoxLayout(self)

        # Верхняя панель: поиск + фильтр
        top_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск модов (например: Sodium, JEI, Iris, Xaero)...")
        self.search_input.returnPressed.connect(self._start_search)

        self.loader_combo = QComboBox()
        self.loader_combo.addItem("Все лоадеры", "all")
        self.loader_combo.addItem("Fabric", "fabric")
        self.loader_combo.addItem("Forge", "forge")

        self.search_btn = QPushButton("Найти")
        self.search_btn.clicked.connect(self._start_search)

        top_layout.addWidget(self.search_input)
        top_layout.addWidget(self.loader_combo)
        top_layout.addWidget(self.search_btn)
        layout.addLayout(top_layout)

        # Список результатов
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget { background-color: #1e1e1e; border: 1px solid #333; border-radius: 6px; }
            QListWidget::item { border-bottom: 1px solid #2a2a2a; }
        """)
        layout.addWidget(self.list_widget)

        # Нижняя панель со статусом
        self.status_label = QLabel("Введите название мода и нажмите «Найти»")
        self.status_label.setStyleSheet("color: #aaa;")
        layout.addWidget(self.status_label)

        self._search_thread: Optional[ModSearchThread] = None
        self._active_downloads: list[ModDownloadThread] = []

        # Сразу запускаем популярные моды
        self._start_search()

    def _start_search(self) -> None:
        query = self.search_input.text().strip()
        loader = self.loader_combo.currentData()
        self.status_label.setText("Поиск на Modrinth...")
        self.search_btn.setEnabled(False)

        if self._search_thread and self._search_thread.isRunning():
            try:
                self._search_thread.results_loaded.disconnect()
                self._search_thread.error_occurred.disconnect()
            except Exception:
                pass
            self._search_thread.wait(300)

        self._search_thread = ModSearchThread(query, self.mc_version, loader)
        self._search_thread.results_loaded.connect(self._display_results)
        self._search_thread.error_occurred.connect(self._on_search_error)
        self._search_thread.start()

    def _display_results(self, hits: list) -> None:
        self.search_btn.setEnabled(True)
        self.list_widget.clear()

        if not hits:
            self.status_label.setText("Ничего не найдено для этой версии игры.")
            return

        self.status_label.setText(f"Найдено модов: {len(hits)}")

        for h in hits:
            item = QListWidgetItem(self.list_widget)
            widget = ModItemWidget(h)
            widget.install_requested.connect(self._install_mod)
            item.setSizeHint(widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)

    def _on_search_error(self, err: str) -> None:
        self.search_btn.setEnabled(True)
        self.status_label.setText(f"Ошибка соединения с Modrinth: {err}")

    def _install_mod(self, project_id: str, title: str) -> None:
        loader = self.loader_combo.currentData()
        self.status_label.setText(f"Скачивание {title}...")

        thread = ModDownloadThread(project_id, title, self.mc_version, loader)
        self._active_downloads.append(thread)

        thread.status_updated.connect(self.status_label.setText)
        thread.download_finished.connect(
            lambda fn: self.status_label.setText(f"✅ Мод «{fn}» успешно установлен в папку mods!")
        )
        thread.error_occurred.connect(
            lambda e: self.status_label.setText(f"❌ Ошибка установки: {e}")
        )
        thread.finished.connect(
            lambda: self._active_downloads.remove(thread) if thread in self._active_downloads else None
        )
        thread.start()
