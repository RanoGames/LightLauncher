"""Менеджер установленных модов Minecraft (Mod Manager).

Позволяет просматривать, включать, отключать, удалять и добавлять моды
в папку .minecraft/mods с поддержкой быстрого поиска и фонового чтения метаданных.
"""

import json
import logging
import os
import re
import shutil
import zipfile
from typing import Optional

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from constants import MINECRAFT_DIRECTORY
from utils import t

logger = logging.getLogger("LightLauncher")


def format_size(size_bytes: int) -> str:
    """Форматирует размер файла в удобочитаемый вид."""
    if size_bytes < 1024:
        return f"{size_bytes} Б"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} КБ"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} МБ"


def clean_filename_title(filename: str) -> str:
    """Преобразует имя файла мода в читаемый заголовок."""
    name = filename
    for ext in (".jar.disabled", ".disabled", ".jar"):
        if name.lower().endswith(ext):
            name = name[:-len(ext)]
            break
    # Убираем типичные суффиксы версий для красивого отображения
    return name


class ModMetadataWorker(QThread):
    """Фоновый парсер метаданных JAR-файлов (fabric.mod.json, mods.toml, mcmod.info)."""

    meta_loaded = pyqtSignal(str, str, str)  # filepath, display_name, version

    def __init__(self, filepaths: list[str]) -> None:
        super().__init__()
        self.filepaths = filepaths
        self._stopped = False

    def stop(self) -> None:
        self._stopped = True

    def run(self) -> None:
        for p in self.filepaths:
            if self._stopped:
                break
            if not os.path.exists(p):
                continue

            display_name = ""
            version = ""

            try:
                with zipfile.ZipFile(p, "r") as z:
                    namelist = set(z.namelist())

                    # 1. Fabric mod
                    if "fabric.mod.json" in namelist:
                        try:
                            data = json.loads(z.read("fabric.mod.json").decode("utf-8", errors="ignore"))
                            display_name = data.get("name", "")
                            version = data.get("version", "")
                        except Exception:
                            pass

                    # 2. NeoForge / Forge mods.toml
                    if not display_name:
                        for toml_name in ("META-INF/neoforge.mods.toml", "META-INF/mods.toml"):
                            if toml_name in namelist:
                                try:
                                    raw = z.read(toml_name).decode("utf-8", errors="ignore")
                                    m_name = re.search(r'displayName\s*=\s*["\']([^"\']+)["\']', raw)
                                    m_ver = re.search(r'version\s*=\s*["\']([^"\']+)["\']', raw)
                                    if m_name:
                                        display_name = m_name.group(1)
                                    if m_ver:
                                        version = m_ver.group(1)
                                    break
                                except Exception:
                                    pass

                    # 3. Старый Forge mcmod.info
                    if not display_name and "mcmod.info" in namelist:
                        try:
                            info_raw = z.read("mcmod.info").decode("utf-8", errors="ignore")
                            data = json.loads(info_raw)
                            modlist = data if isinstance(data, list) else data.get("modList", [])
                            if modlist and isinstance(modlist, list):
                                first = modlist[0]
                                display_name = first.get("name", "")
                                version = first.get("version", "")
                        except Exception:
                            pass
            except Exception:
                pass

            if display_name:
                self.meta_loaded.emit(p, display_name, version)


class ModManagerWidget(QWidget):
    """Виджет управления установленными модами."""

    mods_changed = pyqtSignal()

    def __init__(self, parent=None, lang: str = "ru") -> None:
        super().__init__(parent)
        self._lang = lang
        self.mods_dir = os.path.join(MINECRAFT_DIRECTORY, "mods")
        os.makedirs(self.mods_dir, exist_ok=True)

        self.setAcceptDrops(True)
        self._meta_worker: Optional[ModMetadataWorker] = None
        self._mod_rows: dict[str, int] = {}  # filepath -> row index

        self._setup_ui()
        self.refresh_mods()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # --- Верхняя панель инструментов ---
        top_layout = QHBoxLayout()

        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("🔍 " + t("search_mods", self._lang))
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 14);
                border: 1px solid rgba(255, 255, 255, 28);
                border-radius: 8px;
                color: #ffffff;
                padding: 6px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #3b82f6;
                background-color: rgba(255, 255, 255, 20);
            }
        """)
        self.search_input.textChanged.connect(self._filter_mods)
        top_layout.addWidget(self.search_input, stretch=2)

        self.filter_combo = QtWidgets.QComboBox(self)
        self.filter_combo.addItem("Все моды", "all")
        self.filter_combo.addItem("Только активные", "active")
        self.filter_combo.addItem("Только отключенные", "disabled")
        self.filter_combo.setStyleSheet("""
            QComboBox {
                background-color: rgba(255, 255, 255, 14);
                border: 1px solid rgba(255, 255, 255, 28);
                border-radius: 8px;
                color: #ffffff;
                padding: 6px 12px;
            }
            QComboBox QAbstractItemView {
                background-color: #1a1e29;
                color: white;
                selection-background-color: #3b82f6;
            }
        """)
        self.filter_combo.currentIndexChanged.connect(self._filter_mods)
        top_layout.addWidget(self.filter_combo)

        btn_add = QPushButton("➕ " + t("add_mods", self._lang), self)
        btn_add.setStyleSheet(self._btn_style("#10b981"))
        btn_add.clicked.connect(self._add_mods_dialog)
        top_layout.addWidget(btn_add)

        btn_folder = QPushButton("📁 " + t("open_mods_folder", self._lang), self)
        btn_folder.setStyleSheet(self._btn_style("#3b82f6"))
        btn_folder.clicked.connect(self._open_folder)
        top_layout.addWidget(btn_folder)

        btn_refresh = QPushButton("🔄", self)
        btn_refresh.setToolTip("Обновить список модов")
        btn_refresh.setStyleSheet(self._btn_style("#64748b"))
        btn_refresh.setFixedWidth(36)
        btn_refresh.clicked.connect(self.refresh_mods)
        top_layout.addWidget(btn_refresh)

        layout.addLayout(top_layout)

        # --- Вторая панель (счетчики и массовые действия) ---
        stats_layout = QHBoxLayout()

        self.stats_label = QLabel(self)
        self.stats_label.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: 600;")
        stats_layout.addWidget(self.stats_label)

        stats_layout.addStretch()

        btn_enable_all = QPushButton("✓ " + t("enable_all", self._lang), self)
        btn_enable_all.setStyleSheet(self._mini_btn_style())
        btn_enable_all.clicked.connect(lambda: self._set_all_enabled(True))
        stats_layout.addWidget(btn_enable_all)

        btn_disable_all = QPushButton("✕ " + t("disable_all", self._lang), self)
        btn_disable_all.setStyleSheet(self._mini_btn_style())
        btn_disable_all.clicked.connect(lambda: self._set_all_enabled(False))
        stats_layout.addWidget(btn_disable_all)

        layout.addLayout(stats_layout)

        # --- Таблица модов ---
        self.table = QTableWidget(self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "Статус",
            "Мод / Файл",
            "Размер",
            "Действия",
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: rgba(18, 20, 28, 0.7);
                border: 1px solid rgba(255, 255, 255, 18);
                border-radius: 12px;
                color: #ffffff;
                gridline-color: rgba(255, 255, 255, 8);
            }
            QTableWidget::item {
                padding: 6px;
                border-bottom: 1px solid rgba(255, 255, 255, 10);
            }
            QTableWidget::item:selected {
                background-color: rgba(59, 130, 246, 0.25);
            }
            QHeaderView::section {
                background-color: rgba(30, 41, 59, 0.85);
                color: #94a3b8;
                font-weight: bold;
                border: none;
                padding: 6px;
            }
        """)
        layout.addWidget(self.table)

    def _btn_style(self, hover_color: str) -> str:
        return f"""
            QPushButton {{
                background-color: rgba(255, 255, 255, 14);
                border: 1px solid rgba(255, 255, 255, 28);
                border-radius: 8px;
                color: #ffffff;
                padding: 6px 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
                border-color: {hover_color};
            }}
        """

    def _mini_btn_style(self) -> str:
        return """
            QPushButton {
                background-color: rgba(255, 255, 255, 10);
                border: 1px solid rgba(255, 255, 255, 20);
                border-radius: 6px;
                color: #cbd5e1;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 25);
                color: #ffffff;
            }
        """

    def refresh_mods(self) -> None:
        """Сканирует папку mods и заполняет таблицу."""
        if self._meta_worker and self._meta_worker.isRunning():
            self._meta_worker.stop()
            self._meta_worker.wait()

        self.table.setRowCount(0)
        self._mod_rows.clear()

        if not os.path.isdir(self.mods_dir):
            self._update_stats(0, 0, 0)
            return

        entries: list[str] = []
        try:
            for f in os.listdir(self.mods_dir):
                lf = f.lower()
                if lf.endswith(".jar") or lf.endswith(".disabled"):
                    entries.append(f)
        except Exception as e:
            logger.error("Ошибка сканирования папки модов: %s", e)
            return

        entries.sort(key=lambda x: x.lower())
        active_count = 0
        disabled_count = 0
        jar_paths_for_meta: list[str] = []

        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(entries))

        for row, filename in enumerate(entries):
            filepath = os.path.join(self.mods_dir, filename)
            is_enabled = filename.lower().endswith(".jar")
            if is_enabled:
                active_count += 1
            else:
                disabled_count += 1

            try:
                size_bytes = os.path.getsize(filepath)
            except Exception:
                size_bytes = 0

            self._mod_rows[filepath] = row

            # 0. Статус (Чекбокс)
            cb_widget = QWidget()
            cb_layout = QHBoxLayout(cb_widget)
            cb_layout.setContentsMargins(6, 0, 6, 0)
            cb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cb = QtWidgets.QCheckBox()
            cb.setChecked(is_enabled)
            cb.stateChanged.connect(lambda state, p=filepath: self._on_toggle_mod(p, state))
            cb_layout.addWidget(cb)
            self.table.setCellWidget(row, 0, cb_widget)

            # 1. Название мода / файла
            title_text = clean_filename_title(filename)
            item_title = QTableWidgetItem(title_text)
            item_title.setToolTip(f"Файл: {filename}\nПуть: {filepath}")
            item_title.setData(Qt.ItemDataRole.UserRole, filepath)
            item_title.setData(Qt.ItemDataRole.UserRole + 1, filename)
            if not is_enabled:
                item_title.setForeground(QtGui.QColor("#71717a"))
            self.table.setItem(row, 1, item_title)

            # 2. Размер файла
            item_size = QTableWidgetItem(format_size(size_bytes))
            item_size.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_size.setForeground(QtGui.QColor("#94a3b8"))
            self.table.setItem(row, 2, item_size)

            # 3. Кнопка удаления
            action_widget = QWidget()
            act_layout = QHBoxLayout(action_widget)
            act_layout.setContentsMargins(4, 0, 4, 0)
            act_layout.setSpacing(6)

            btn_del = QPushButton("🗑", action_widget)
            btn_del.setToolTip("Удалить мод")
            btn_del.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #ef4444;
                    font-size: 13px;
                    border: none;
                    padding: 2px 6px;
                }
                QPushButton:hover {
                    background-color: rgba(239, 68, 68, 0.2);
                    border-radius: 4px;
                }
            """)
            btn_del.clicked.connect(lambda _, p=filepath, fn=filename: self._delete_mod(p, fn))
            act_layout.addWidget(btn_del)
            self.table.setCellWidget(row, 3, action_widget)

            if is_enabled:
                jar_paths_for_meta.append(filepath)

        self._update_stats(len(entries), active_count, disabled_count)
        self._filter_mods()

        # Запуск фонового извлечения красивых имён и версий
        if jar_paths_for_meta:
            self._meta_worker = ModMetadataWorker(jar_paths_for_meta)
            self._meta_worker.meta_loaded.connect(self._on_meta_loaded)
            self._meta_worker.start()

    def _on_meta_loaded(self, filepath: str, display_name: str, version: str) -> None:
        """Обновляет название мода красивым именем из манифеста JAR."""
        row = self._mod_rows.get(filepath)
        if row is not None and row < self.table.rowCount():
            item = self.table.item(row, 1)
            if item:
                filename = item.data(Qt.ItemDataRole.UserRole + 1)
                text = f"{display_name}"
                if version:
                    text += f" ({version})"
                text += f"   [{filename}]"
                item.setText(text)

    def _on_toggle_mod(self, filepath: str, state: int) -> None:
        """Переключает статус мода (переименовывает foo.jar <-> foo.jar.disabled)."""
        is_enable = (state == Qt.CheckState.Checked.value)
        if not os.path.exists(filepath):
            return

        dirname, basename = os.path.split(filepath)
        if is_enable:
            new_basename = re.sub(r'\.disabled$', '', basename, flags=re.IGNORECASE)
            if not new_basename.lower().endswith(".jar"):
                new_basename += ".jar"
        else:
            new_basename = (
                basename + ".disabled"
                if not basename.lower().endswith(".disabled")
                else basename
            )

        new_filepath = os.path.join(dirname, new_basename)
        if new_filepath != filepath:
            try:
                os.rename(filepath, new_filepath)
                logger.info("Мод переименован: %s -> %s", basename, new_basename)
                self.refresh_mods()
                self.mods_changed.emit()
            except Exception as e:
                logger.error("Ошибка переименования мода: %s", e)
                QMessageBox.critical(self, "Ошибка", f"Не удалось изменить статус мода:\n{e}")
                self.refresh_mods()

    def _delete_mod(self, filepath: str, filename: str) -> None:
        """Удаляет файл мода после подтверждения."""
        msg = QMessageBox(self)
        msg.setWindowTitle(t("delete_mod_title", self._lang))
        msg.setText(f"{t('delete_mod_ask', self._lang)} '{filename}'?")
        msg.setIcon(QMessageBox.Icon.Question)
        yes_btn = msg.addButton(t("yes", self._lang), QMessageBox.ButtonRole.YesRole)
        msg.addButton(t("no", self._lang), QMessageBox.ButtonRole.NoRole)
        msg.exec()

        if msg.clickedButton() == yes_btn:
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
                    logger.info("Удален мод: %s", filepath)
                    self.refresh_mods()
                    self.mods_changed.emit()
            except Exception as e:
                logger.error("Ошибка удаления мода: %s", e)
                QMessageBox.critical(self, "Ошибка", f"Не удалось удалить мод:\n{e}")

    def _set_all_enabled(self, enable: bool) -> None:
        """Включает или выключает все моды в папке."""
        if not os.path.isdir(self.mods_dir):
            return

        changed = 0
        try:
            for f in os.listdir(self.mods_dir):
                p = os.path.join(self.mods_dir, f)
                if enable and f.lower().endswith(".disabled"):
                    new_name = re.sub(r'\.disabled$', '', f, flags=re.IGNORECASE)
                    if not new_name.lower().endswith(".jar"):
                        new_name += ".jar"
                    os.rename(p, os.path.join(self.mods_dir, new_name))
                    changed += 1
                elif not enable and f.lower().endswith(".jar"):
                    new_name = f + ".disabled"
                    os.rename(p, os.path.join(self.mods_dir, new_name))
                    changed += 1
        except Exception as e:
            logger.error("Ошибка при массовом изменении модов: %s", e)

        if changed > 0:
            self.refresh_mods()
            self.mods_changed.emit()

    def _filter_mods(self) -> None:
        """Фильтрует строки таблицы по поисковой строке и выпадающему фильтру."""
        query = self.search_input.text().strip().lower()
        filter_type = self.filter_combo.currentData()

        for row in range(self.table.rowCount()):
            item = self.table.item(row, 1)
            if not item:
                continue
            text = item.text().lower()
            filepath = item.data(Qt.ItemDataRole.UserRole)
            is_enabled = filepath.lower().endswith(".jar")

            match_query = (not query) or (query in text)
            match_filter = True
            if (filter_type == "active" and not is_enabled) or (filter_type == "disabled" and is_enabled):
                match_filter = False

            self.table.setRowHidden(row, not (match_query and match_filter))

    def _update_stats(self, total: int, active: int, disabled: int) -> None:
        self.stats_label.setText(
            f"📦 {t('total_mods', self._lang)} {total}   "
            f"(🟢 {active} {t('active_mods', self._lang)}, "
            f"⚪ {disabled} {t('disabled_mods', self._lang)})"
        )

    def _add_mods_dialog(self) -> None:
        """Диалог выбора JAR-файлов для добавления в папку mods."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            t("add_mods", self._lang),
            "",
            "Minecraft Mods (*.jar)",
        )
        if not files:
            return

        added = 0
        for f in files:
            try:
                dest = os.path.join(self.mods_dir, os.path.basename(f))
                shutil.copy2(f, dest)
                added += 1
            except Exception as e:
                logger.error("Ошибка копирования мода %s: %s", f, e)

        if added > 0:
            self.refresh_mods()
            self.mods_changed.emit()

    def _open_folder(self) -> None:
        """Открывает папку mods в проводнике."""
        os.makedirs(self.mods_dir, exist_ok=True)
        if os.name == "nt":
            os.startfile(self.mods_dir)
        else:
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(self.mods_dir))

    # Drag and Drop поддержка для быстрого закидывания модов
    def dragEnterEvent(self, event: QtGui.QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith((".jar", ".disabled")):
                    event.acceptProposedAction()
                    return
        super().dragEnterEvent(event)

    def dropEvent(self, event: QtGui.QDropEvent) -> None:
        added = 0
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith((".jar", ".disabled")) and os.path.isfile(file_path):
                try:
                    dest = os.path.join(self.mods_dir, os.path.basename(file_path))
                    shutil.copy2(file_path, dest)
                    added += 1
                except Exception as e:
                    logger.error("Ошибка при переносе мода: %s", e)

        if added > 0:
            self.refresh_mods()
            self.mods_changed.emit()
            event.acceptProposedAction()
        super().dropEvent(event)
