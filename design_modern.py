"""Современный Glassmorphism дизайн LightLauncher (Modern UI)."""

from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_MainWindowModern:
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(780, 570)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed
        )
        MainWindow.setSizePolicy(sizePolicy)
        MainWindow.setMinimumSize(QtCore.QSize(780, 570))
        MainWindow.setMaximumSize(QtCore.QSize(780, 570))

        self.centralwidget = QtWidgets.QWidget(parent=MainWindow)
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(11)
        self.centralwidget.setFont(font)

        # 1. Верхний бейдж версии (слева вверху)
        self.JavaInfoLabel = QtWidgets.QLabel(parent=self.centralwidget)
        self.JavaInfoLabel.setGeometry(QtCore.QRect(16, 12, 120, 26))
        self.JavaInfoLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.JavaInfoLabel.setObjectName("JavaInfoLabel")
        self.JavaInfoLabel.setStyleSheet("""
            QLabel#JavaInfoLabel {
                background-color: rgba(18, 20, 26, 0.75);
                color: #b0b0b0;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                font-size: 11px;
                font-weight: bold;
            }
        """)

        # 2. Статус / сообщения по центру
        self.Progress = QtWidgets.QLabel(parent=self.centralwidget)
        self.Progress.setGeometry(QtCore.QRect(140, 220, 500, 42))
        self.Progress.setFont(QtGui.QFont("Segoe UI", 13, QtGui.QFont.Weight.Bold))
        self.Progress.setText("")
        self.Progress.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.Progress.setObjectName("Progress")
        self.Progress.setStyleSheet("""
            QLabel#Progress {
                color: #ffffff;
                background-color: rgba(18, 20, 26, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
                padding: 4px 12px;
            }
        """)
        self.Progress.hide()

        # Прогресс-бар установки
        self.InstallProgressBar = QtWidgets.QProgressBar(parent=self.centralwidget)
        self.InstallProgressBar.setGeometry(QtCore.QRect(180, 275, 420, 8))
        self.InstallProgressBar.setValue(0)
        self.InstallProgressBar.setTextVisible(False)
        self.InstallProgressBar.setObjectName("InstallProgressBar")
        self.InstallProgressBar.setStyleSheet("""
            QProgressBar {
                background-color: rgba(0, 0, 0, 0.5);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #43a047, stop:1 #81c784);
                border-radius: 3px;
            }
        """)
        self.InstallProgressBar.hide()

        # 3. Нижний стеклянный док (Floating Glass Dock)
        self.dock_card = QtWidgets.QFrame(parent=self.centralwidget)
        self.dock_card.setGeometry(QtCore.QRect(20, 385, 740, 168))
        self.dock_card.setObjectName("DockCard")
        self.dock_card.setStyleSheet("""
            QFrame#DockCard {
                background-color: rgba(18, 20, 28, 0.88);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 16px;
            }
        """)

        # ВЕРХНИЙ РЯД ДОКА:

        # Никнейм
        self.NicknameLabel = QtWidgets.QLabel(parent=self.dock_card)
        self.NicknameLabel.setGeometry(QtCore.QRect(16, 10, 220, 18))
        self.NicknameLabel.setStyleSheet("color: #8e8e93; font-size: 11px; font-weight: bold; letter-spacing: 0.5px;")
        self.NicknameLabel.setObjectName("NicknameLabel")

        self.Nickname = QtWidgets.QComboBox(parent=self.dock_card)
        self.Nickname.setEditable(True)
        self.Nickname.setGeometry(QtCore.QRect(16, 32, 175, 48))
        self.Nickname.setObjectName("Nickname")

        self.DeleteNicknameButton = QtWidgets.QPushButton(parent=self.dock_card)
        self.DeleteNicknameButton.setGeometry(QtCore.QRect(196, 32, 42, 48))
        self.DeleteNicknameButton.setFont(QtGui.QFont("Segoe UI", 12, QtGui.QFont.Weight.Bold))
        self.DeleteNicknameButton.setObjectName("DeleteNicknameButton")

        # Версия игры
        self.GameVersionLabel = QtWidgets.QLabel(parent=self.dock_card)
        self.GameVersionLabel.setGeometry(QtCore.QRect(250, 10, 245, 18))
        self.GameVersionLabel.setStyleSheet("color: #8e8e93; font-size: 11px; font-weight: bold; letter-spacing: 0.5px;")
        self.GameVersionLabel.setObjectName("GameVersionLabel")

        self.VersionComboBox = QtWidgets.QComboBox(parent=self.dock_card)
        self.VersionComboBox.setEditable(False)
        self.VersionComboBox.setGeometry(QtCore.QRect(250, 32, 200, 48))
        self.VersionComboBox.setObjectName("VersionComboBox")

        self.RefreshVersionsButton = QtWidgets.QPushButton(parent=self.dock_card)
        self.RefreshVersionsButton.setGeometry(QtCore.QRect(455, 32, 44, 48))
        self.RefreshVersionsButton.setFont(QtGui.QFont("Segoe UI", 13, QtGui.QFont.Weight.Bold))
        self.RefreshVersionsButton.setObjectName("RefreshVersionsButton")

        # Главная кнопка действия (Hero Button)
        self.PlayMinecraft = QtWidgets.QPushButton(parent=self.dock_card)
        self.PlayMinecraft.setGeometry(QtCore.QRect(514, 20, 210, 60))
        self.PlayMinecraft.setFont(QtGui.QFont("Segoe UI", 15, QtGui.QFont.Weight.Bold))
        self.PlayMinecraft.setObjectName("PlayMinecraft")

        self.DownLoadMinecraft = QtWidgets.QPushButton(parent=self.dock_card)
        self.DownLoadMinecraft.setGeometry(QtCore.QRect(514, 20, 210, 60))
        self.DownLoadMinecraft.setFont(QtGui.QFont("Segoe UI", 14, QtGui.QFont.Weight.Bold))
        self.DownLoadMinecraft.setObjectName("DownLoadMinecraft")

        self.CancelInstallButton = QtWidgets.QPushButton(parent=self.dock_card)
        self.CancelInstallButton.setGeometry(QtCore.QRect(514, 20, 210, 60))
        self.CancelInstallButton.setFont(QtGui.QFont("Segoe UI", 14, QtGui.QFont.Weight.Bold))
        self.CancelInstallButton.setObjectName("CancelInstallButton")
        self.CancelInstallButton.hide()

        # НИЖНИЙ РЯД ДОКА (Быстрые действия)
        btn_y = 108
        btn_h = 44

        self.SettingsButton = QtWidgets.QPushButton(parent=self.dock_card)
        self.SettingsButton.setGeometry(QtCore.QRect(16, btn_y, 134, btn_h))
        self.SettingsButton.setObjectName("SettingsButton")

        self.InstallModloaderButton = QtWidgets.QPushButton(parent=self.dock_card)
        self.InstallModloaderButton.setGeometry(QtCore.QRect(158, btn_y, 134, btn_h))
        self.InstallModloaderButton.setObjectName("InstallModloaderButton")

        self.FilesButton = QtWidgets.QPushButton(parent=self.dock_card)
        self.FilesButton.setGeometry(QtCore.QRect(300, btn_y, 134, btn_h))
        self.FilesButton.setObjectName("FilesButton")

        self.DeleteVersionButton = QtWidgets.QPushButton(parent=self.dock_card)
        self.DeleteVersionButton.setGeometry(QtCore.QRect(442, btn_y, 134, btn_h))
        self.DeleteVersionButton.setObjectName("DeleteVersionButton")

        self.GitHubButton = QtWidgets.QPushButton(parent=self.dock_card)
        self.GitHubButton.setGeometry(QtCore.QRect(584, btn_y, 140, btn_h))
        self.GitHubButton.setObjectName("GitHubButton")

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(parent=MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 780, 22))
        MainWindow.setMenuBar(self.menubar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "LightLauncher"))
        self.PlayMinecraft.setText(_translate("MainWindow", "▶ ИГРАТЬ"))
        self.DownLoadMinecraft.setText(_translate("MainWindow", "⬇ СКАЧАТЬ"))
        self.SettingsButton.setText(_translate("MainWindow", "⚙ Настройки"))
        self.InstallModloaderButton.setText(_translate("MainWindow", "🧩 Моды"))
        self.FilesButton.setText(_translate("MainWindow", "📁 Папка"))
        self.DeleteVersionButton.setText(_translate("MainWindow", "🗑 Удалить"))
        self.GitHubButton.setText(_translate("MainWindow", "🐙 GitHub"))
        self.NicknameLabel.setText(_translate("MainWindow", "👤 ИМЯ ИГРОКА"))
        self.GameVersionLabel.setText(_translate("MainWindow", "📦 ВЕРСИЯ ИГРЫ"))
        self.RefreshVersionsButton.setText(_translate("MainWindow", "🔄"))
        self.DeleteNicknameButton.setText(_translate("MainWindow", "✕"))
        self.CancelInstallButton.setText(_translate("MainWindow", "✕ ОТМЕНА"))

        # Тултипы
        self.PlayMinecraft.setToolTip(_translate("MainWindow", "Запустить Minecraft"))
        self.DownLoadMinecraft.setToolTip(_translate("MainWindow", "Скачать выбранную версию"))
        self.SettingsButton.setToolTip(_translate("MainWindow", "Открыть настройки лаунчера"))
        self.InstallModloaderButton.setToolTip(_translate("MainWindow", "Установка модов и мод-лоадеров"))
        self.Nickname.setToolTip(_translate("MainWindow", "Введите или выберите никнейм"))
        self.VersionComboBox.setToolTip(_translate("MainWindow", "Выберите версию Minecraft"))
        self.RefreshVersionsButton.setToolTip(_translate("MainWindow", "Обновить список версий"))
        self.FilesButton.setToolTip(_translate("MainWindow", "Открыть папку с игрой"))
        self.GitHubButton.setToolTip(_translate("MainWindow", "Открыть GitHub проекта"))
        self.DeleteNicknameButton.setToolTip(_translate("MainWindow", "Удалить ник из списка"))
        self.DeleteVersionButton.setToolTip(_translate("MainWindow", "Удалить выбранную версию"))
        self.CancelInstallButton.setToolTip(_translate("MainWindow", "Отменить установку"))
