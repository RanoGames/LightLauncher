"""Окно настроек лаунчера."""

import logging
import os

import psutil
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from constants import CACHE_DIR
from java_downloader import JavaDownloadDialog
from playtime_tracker import get_playtime_stats
from utils import get_optimal_ram, get_system_lang, resource_path, t

logger = logging.getLogger("LightLauncher")


class SettingsWindow(QDialog):
    """Диалог настроек: язык, стиль, версии, Java, RAM, разрешение, фон, скины, кэш."""

    def __init__(
        self,
        parent=None,
        current_filters: list[str] | None = None,
        current_memory: int = 2048,
        show_console: bool = False,
        current_lang: str = "auto",
        jvm_args: str = "",
        validate_nickname: bool = True,
        auto_java: bool = True,
        java_path: str | None = None,
        fullscreen: bool = False,
        resolution_width: int = 1920,
        resolution_height: int = 1080,
        custom_background: str | None = None,
        ely_by_skins: bool = True,
        current_version: str | None = None,
        ui_theme: str = "modern",
    ) -> None:
        super().__init__(parent)
        L = current_lang if current_lang != "auto" else get_system_lang()
        self.setWindowTitle(t("settings", L))
        self.resize(580, 520)
        self.setMinimumSize(540, 480)
        self._lang = current_lang
        self.current_version = current_version
        self.custom_bg_path = custom_background
        self.ui_theme = ui_theme

        icon_path = resource_path("mclovin.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        if current_filters is None:
            current_filters = ["release"]
        self.old_filters = list(current_filters)

        self._apply_dialog_styles()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 16, 18, 16)
        main_layout.setSpacing(14)

        # Табы настроек
        self.tabs = QTabWidget(self)

        # -------------------------------------------------------------
        # Вкладка 1: Основные (Интерфейс и игра)
        # -------------------------------------------------------------
        tab_general = QWidget()
        gen_layout = QVBoxLayout(tab_general)
        gen_layout.setContentsMargins(14, 14, 14, 14)
        gen_layout.setSpacing(10)

        # Язык
        gen_layout.addWidget(QLabel(f"<b>{t('language', L)}</b>"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItem(t("auto_lang", L), "auto")
        self.lang_combo.addItem(t("russian", L), "ru")
        self.lang_combo.addItem(t("english", L), "en")
        idx = self.lang_combo.findData(current_lang)
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)
        self.lang_combo.currentIndexChanged.connect(self._on_lang_changed)
        gen_layout.addWidget(self.lang_combo)

        # Стиль интерфейса
        gen_layout.addWidget(QLabel(f"<b>{t('ui_theme', L)}</b>"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItem(t("theme_modern", L), "modern")
        self.theme_combo.addItem(t("theme_classic", L), "classic")
        idx_t = self.theme_combo.findData(ui_theme)
        if idx_t >= 0:
            self.theme_combo.setCurrentIndex(idx_t)
        gen_layout.addWidget(self.theme_combo)

        # Свой фон
        gen_layout.addWidget(QLabel(f"<b>{t('custom_background', L)}</b>"))
        bg_layout = QHBoxLayout()
        self.bg_label = QLabel(self._get_bg_display_text(L))
        self.bg_label.setStyleSheet("color: #94a3b8; font-weight: 500;")
        self.choose_bg_btn = QPushButton(t("choose_bg", L))
        self.choose_bg_btn.clicked.connect(self._choose_background)
        self.reset_bg_btn = QPushButton(t("reset_bg", L))
        self.reset_bg_btn.clicked.connect(self._reset_background)
        bg_layout.addWidget(self.bg_label, stretch=2)
        bg_layout.addWidget(self.choose_bg_btn)
        bg_layout.addWidget(self.reset_bg_btn)
        gen_layout.addLayout(bg_layout)

        # Экран игры (разрешение и полноэкранный режим)
        gen_layout.addWidget(QLabel(f"<b>{t('game_screen', L)}</b>"))
        self.fullscreen_cb = QCheckBox(t("fullscreen", L))
        self.fullscreen_cb.setChecked(fullscreen)
        gen_layout.addWidget(self.fullscreen_cb)

        res_layout = QHBoxLayout()
        self.res_w = QSpinBox()
        self.res_w.setRange(640, 3840)
        self.res_w.setValue(resolution_width)
        self.res_w.setSuffix(" px")
        self.res_h = QSpinBox()
        self.res_h.setRange(480, 2160)
        self.res_h.setValue(resolution_height)
        self.res_h.setSuffix(" px")
        res_layout.addWidget(QLabel("Ширина (W):"))
        res_layout.addWidget(self.res_w)
        res_layout.addSpacing(10)
        res_layout.addWidget(QLabel("Высота (H):"))
        res_layout.addWidget(self.res_h)
        gen_layout.addLayout(res_layout)

        # Скины Ely.by
        self.ely_skins_cb = QCheckBox(t("ely_by_skins", L))
        self.ely_skins_cb.setChecked(ely_by_skins)
        gen_layout.addWidget(self.ely_skins_cb)

        gen_layout.addStretch()
        self.tabs.addTab(tab_general, f"🎮 {t('tab_general', L)}")

        # -------------------------------------------------------------
        # Вкладка 2: Java и Память
        # -------------------------------------------------------------
        tab_java = QWidget()
        java_box = QVBoxLayout(tab_java)
        java_box.setContentsMargins(14, 14, 14, 14)
        java_box.setSpacing(10)

        java_box.addWidget(QLabel("<b>Среда выполнения Java:</b>"))
        self.auto_java_cb = QCheckBox(t("auto_java", L))
        self.auto_java_cb.setChecked(auto_java)
        self.auto_java_cb.toggled.connect(self._toggle_java_inputs)
        java_box.addWidget(self.auto_java_cb)

        java_path_row = QHBoxLayout()
        self.java_path_input = QLineEdit(java_path or "")
        self.java_path_input.setPlaceholderText("C:\\Program Files\\Java\\jdk-21\\bin\\javaw.exe")
        self.browse_java_btn = QPushButton(t("browse", L))
        self.browse_java_btn.clicked.connect(self._browse_java)
        java_path_row.addWidget(self.java_path_input, stretch=3)
        java_path_row.addWidget(self.browse_java_btn)
        java_box.addLayout(java_path_row)
        self._toggle_java_inputs(auto_java)

        # Кнопка скачивания Java Runtime
        self.download_java_btn = QPushButton("⚡ " + t("download_java_title", L) + "...")
        self.download_java_btn.setObjectName("DownloadJavaBtn")
        self.download_java_btn.setStyleSheet("""
            QPushButton#DownloadJavaBtn {
                background-color: rgba(16, 185, 129, 0.22);
                border: 1px solid #10b981;
                border-radius: 8px;
                color: #4ade80;
                padding: 7px 14px;
                font-weight: bold;
            }
            QPushButton#DownloadJavaBtn:hover {
                background-color: rgba(16, 185, 129, 0.38);
                color: #ffffff;
            }
        """)
        self.download_java_btn.clicked.connect(self._show_java_download_menu)
        java_box.addWidget(self.download_java_btn)

        # Разделитель
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: rgba(255, 255, 255, 15);")
        java_box.addWidget(sep)

        # Выделение оперативной памяти (RAM)
        ram_label_row = QHBoxLayout()
        ram_label_row.addWidget(QLabel(f"<b>{t('memory', L)}</b>"))
        self.memory_value = QLabel(f"{current_memory} {t('mb', L)}")
        self.memory_value.setStyleSheet("color: #38bdf8; font-weight: bold;")
        ram_label_row.addStretch()
        ram_label_row.addWidget(self.memory_value)
        java_box.addLayout(ram_label_row)

        self.memory_slider = QSlider(Qt.Orientation.Horizontal)
        self.memory_slider.setMinimum(1024)
        max_ram = int(psutil.virtual_memory().total / (1024 * 1024))
        self.memory_slider.setMaximum(max_ram)
        self.memory_slider.setValue(current_memory)
        self.memory_slider.valueChanged.connect(
            lambda v: self.memory_value.setText(f"{v} {t('mb', L)}")
        )
        java_box.addWidget(self.memory_slider)

        optimal = get_optimal_ram()
        self.auto_ram_btn = QPushButton(f"⚡ {t('auto', L)} ({optimal} {t('mb', L)})")
        self.auto_ram_btn.clicked.connect(lambda: self.memory_slider.setValue(optimal))
        java_box.addWidget(self.auto_ram_btn)

        # JVM аргументы запуска
        java_box.addWidget(QLabel(f"<b>{t('jvm_args', L)}</b>"))
        self.jvm_args_input = QLineEdit(jvm_args)
        self.jvm_args_input.setPlaceholderText(t("jvm_args_tip", L))
        java_box.addWidget(self.jvm_args_input)

        java_box.addStretch()
        self.tabs.addTab(tab_java, f"☕ {t('tab_java', L)}")

        # -------------------------------------------------------------
        # Вкладка 3: Дополнительно (Версии и Система)
        # -------------------------------------------------------------
        tab_adv = QWidget()
        adv_layout = QVBoxLayout(tab_adv)
        adv_layout.setContentsMargins(14, 14, 14, 14)
        adv_layout.setSpacing(10)

        adv_layout.addWidget(QLabel(f"<b>{t('version_types', L)}</b>"))
        self.release_cb = QCheckBox(t("releases", L))
        self.snapshot_cb = QCheckBox(t("snapshots", L))
        self.old_beta_cb = QCheckBox(t("old_betas", L))
        self.old_alpha_cb = QCheckBox(t("old_alphas", L))
        self.release_cb.setChecked("release" in current_filters)
        self.snapshot_cb.setChecked("snapshot" in current_filters)
        self.old_beta_cb.setChecked("old_beta" in current_filters)
        self.old_alpha_cb.setChecked("old_alpha" in current_filters)
        adv_layout.addWidget(self.release_cb)
        adv_layout.addWidget(self.snapshot_cb)
        adv_layout.addWidget(self.old_beta_cb)
        adv_layout.addWidget(self.old_alpha_cb)

        adv_layout.addWidget(QLabel(f"<b>{t('additional', L)}</b>"))
        self.console_cb = QCheckBox(t("show_console", L))
        self.console_cb.setChecked(show_console)
        adv_layout.addWidget(self.console_cb)

        self.validate_nick_cb = QCheckBox(t("validate_nickname", L))
        self.validate_nick_cb.setChecked(validate_nickname)
        adv_layout.addWidget(self.validate_nick_cb)

        # Статистика времени
        total_time_str, ver_time_str = get_playtime_stats(self.current_version)
        stat_text = f"<b>{t('total_playtime', L)}</b> <span style='color:#4ade80;'>{total_time_str}</span>"
        if self.current_version and ver_time_str != "0 мин.":
            stat_text += f" <span style='color:#94a3b8; font-size:11px;'>({self.current_version}: {ver_time_str})</span>"
        self.playtime_label = QLabel(stat_text)
        adv_layout.addWidget(self.playtime_label)

        # Кнопка очистки кэша
        self.clear_cache_btn = QPushButton("🗑 " + t("clear_cache", L))
        self.clear_cache_btn.setObjectName("ClearCacheBtn")
        self.clear_cache_btn.setStyleSheet("""
            QPushButton#ClearCacheBtn {
                background-color: rgba(239, 68, 68, 0.18);
                border: 1px solid rgba(239, 68, 68, 0.5);
                border-radius: 8px;
                color: #fca5a5;
                font-weight: 600;
                padding: 7px 14px;
            }
            QPushButton#ClearCacheBtn:hover {
                background-color: rgba(239, 68, 68, 0.35);
                color: #ffffff;
            }
        """)
        self.clear_cache_btn.clicked.connect(self._clear_cache)
        adv_layout.addWidget(self.clear_cache_btn)

        adv_layout.addStretch()
        self.tabs.addTab(tab_adv, f"🛠 {t('tab_advanced', L)}")

        main_layout.addWidget(self.tabs)

        # -------------------------------------------------------------
        # Нижняя панель действий (Сохранить / Отмена)
        # -------------------------------------------------------------
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        self.cancel_button = QPushButton(t("cancel", L))
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 14);
                border: 1px solid rgba(255, 255, 255, 28);
                border-radius: 8px;
                color: #cbd5e1;
                padding: 8px 20px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 26);
                color: #ffffff;
            }
        """)
        self.cancel_button.clicked.connect(self.reject)
        bottom_layout.addWidget(self.cancel_button)

        self.save_button = QPushButton("✓ " + t("save", L))
        self.save_button.setObjectName("SaveButton")
        self.save_button.setStyleSheet("""
            QPushButton#SaveButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #059669);
                border: 1px solid rgba(255, 255, 255, 0.25);
                border-radius: 8px;
                color: #ffffff;
                padding: 8px 26px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton#SaveButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #34d399, stop:1 #10b981);
                border-color: rgba(255, 255, 255, 0.45);
            }
            QPushButton#SaveButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #047857);
            }
        """)
        self.save_button.clicked.connect(self.accept)
        bottom_layout.addWidget(self.save_button)

        main_layout.addLayout(bottom_layout)

    def _apply_dialog_styles(self) -> None:
        """Применяет общие стили ко всем элементам настроек."""
        self.setStyleSheet("""
            QDialog {
                background-color: #12141c;
                color: #ffffff;
            }
            QLabel {
                color: #e2e8f0;
                font-size: 12px;
            }
            QCheckBox {
                color: #e2e8f0;
                font-size: 12px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid rgba(255, 255, 255, 35);
                background-color: rgba(255, 255, 255, 14);
            }
            QCheckBox::indicator:checked {
                background-color: #3b82f6;
                border-color: #60a5fa;
            }
            QComboBox, QLineEdit, QSpinBox {
                background-color: rgba(255, 255, 255, 14);
                border: 1px solid rgba(255, 255, 255, 28);
                border-radius: 8px;
                color: #ffffff;
                padding: 6px 12px;
                font-size: 12px;
            }
            QComboBox:hover, QLineEdit:focus, QSpinBox:focus {
                border-color: #3b82f6;
                background-color: rgba(255, 255, 255, 22);
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
            QPushButton {
                background-color: rgba(255, 255, 255, 16);
                border: 1px solid rgba(255, 255, 255, 32);
                border-radius: 8px;
                color: #ffffff;
                padding: 6px 14px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 28);
                border-color: rgba(255, 255, 255, 55);
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 42);
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: rgba(255, 255, 255, 22);
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #8b5cf6);
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #ffffff;
                border: 2px solid #8b5cf6;
                width: 16px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 8px;
            }
            QTabWidget::pane {
                border: 1px solid rgba(255, 255, 255, 18);
                border-radius: 12px;
                background-color: rgba(18, 20, 28, 0.7);
            }
            QTabBar::tab {
                background-color: rgba(255, 255, 255, 10);
                color: #94a3b8;
                border: 1px solid rgba(255, 255, 255, 16);
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 8px 18px;
                font-weight: 600;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background-color: rgba(59, 130, 246, 0.25);
                color: #ffffff;
                border-color: rgba(59, 130, 246, 0.6);
            }
        """)

    def _get_bg_display_text(self, L: str) -> str:
        if self.custom_bg_path and os.path.exists(self.custom_bg_path):
            basename = os.path.basename(self.custom_bg_path)
            return basename if len(basename) < 22 else basename[:19] + "..."
        return t("default_bg", L)

    def _choose_background(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите фоновое изображение",
            "",
            "Изображения (*.png *.jpg *.jpeg *.webp);;Все файлы (*.*)",
        )
        if path:
            self.custom_bg_path = os.path.normpath(path)
            L = self._lang if self._lang != "auto" else get_system_lang()
            self.bg_label.setText(self._get_bg_display_text(L))

    def _reset_background(self) -> None:
        self.custom_bg_path = None
        L = self._lang if self._lang != "auto" else get_system_lang()
        self.bg_label.setText(t("default_bg", L))

    def _toggle_java_inputs(self, auto: bool) -> None:
        self.java_path_input.setEnabled(not auto)
        self.browse_java_btn.setEnabled(not auto)

    def _browse_java(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите javaw.exe или java.exe",
            "C:\\Program Files\\Java",
            "Java Executable (javaw.exe java.exe);;All Files (*.*)",
        )
        if path:
            self.java_path_input.setText(os.path.normpath(path))

    def _clear_cache(self) -> None:
        freed_bytes = 0
        if os.path.exists(CACHE_DIR):
            try:
                for root, _, files in os.walk(CACHE_DIR):
                    for f in files:
                        fp = os.path.join(root, f)
                        try:
                            freed_bytes += os.path.getsize(fp)
                            os.remove(fp)
                        except Exception:
                            pass
            except Exception as e:
                logger.warning("Ошибка при очистке кэша: %s", e)

        mb = freed_bytes / (1024 * 1024)
        L = self._lang if self._lang != "auto" else get_system_lang()
        msg = f"{t('cache_cleared', L)} {mb:.1f} {t('mb', L)}"
        QMessageBox.information(self, t("clear_cache", L), msg)

    def _on_lang_changed(self, index: int) -> None:
        self._lang = self.lang_combo.currentData()
        L = self._lang if self._lang != "auto" else get_system_lang()
        self.setWindowTitle(t("settings", L))
        self.tabs.setTabText(0, f"🎮 {t('tab_general', L)}")
        self.tabs.setTabText(1, f"☕ {t('tab_java', L)}")
        self.tabs.setTabText(2, f"🛠 {t('tab_advanced', L)}")

    def _show_java_download_menu(self) -> None:
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1e293b;
                color: #ffffff;
                border: 1px solid #475569;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #3b82f6;
            }
        """)

        act_8 = menu.addAction("Скачать Java 8 (для MC <= 1.16.5)")
        act_17 = menu.addAction("Скачать Java 17 (для MC 1.17 - 1.20.4)")
        act_21 = menu.addAction("Скачать Java 21 (для MC 1.20.5+)")

        action = menu.exec(self.download_java_btn.mapToGlobal(self.download_java_btn.rect().bottomLeft()))
        if not action:
            return

        runtime_name = "java-runtime-delta"
        major = 21
        if action == act_8:
            runtime_name = "jre-legacy"
            major = 8
        elif action == act_17:
            runtime_name = "java-runtime-gamma"
            major = 17
        elif action == act_21:
            runtime_name = "java-runtime-delta"
            major = 21

        dlg = JavaDownloadDialog(runtime_name, major, parent=self, lang=self._lang)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.java_path:
            self.java_path_input.setText(dlg.java_path)
            self.auto_java_cb.setChecked(False)
            QMessageBox.information(
                self,
                t("download_java_title", self._lang),
                f"{t('download_java_success', self._lang)}\n{dlg.java_path}",
            )

    def get_settings(self) -> dict:
        """Возвращает словарь со всеми сохранёнными настройками."""
        filters: list[str] = []
        if self.release_cb.isChecked():
            filters.append("release")
        if self.snapshot_cb.isChecked():
            filters.append("snapshot")
        if self.old_alpha_cb.isChecked():
            filters.append("old_alpha")
        if self.old_beta_cb.isChecked():
            filters.append("old_beta")

        return {
            "filters": filters,
            "memory": self.memory_slider.value(),
            "show_console": self.console_cb.isChecked(),
            "language": self.lang_combo.currentData(),
            "jvm_args": self.jvm_args_input.text().strip(),
            "validate_nickname": self.validate_nick_cb.isChecked(),
            "auto_java": self.auto_java_cb.isChecked(),
            "java_path": self.java_path_input.text().strip() or None,
            "fullscreen": self.fullscreen_cb.isChecked(),
            "resolution_width": self.res_w.value(),
            "resolution_height": self.res_h.value(),
            "custom_background": self.custom_bg_path,
            "ely_by_skins": self.ely_skins_cb.isChecked(),
            "ui_theme": self.theme_combo.currentData(),
        }
