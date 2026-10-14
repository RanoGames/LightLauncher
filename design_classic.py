"""Классический дизайн LightLauncher (Classic UI)."""

from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_MainWindowClassic:
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(735, 575)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)
        MainWindow.setSizePolicy(sizePolicy)
        MainWindow.setMinimumSize(QtCore.QSize(735, 575))
        MainWindow.setMaximumSize(QtCore.QSize(735, 575))

        self.centralwidget = QtWidgets.QWidget(parent=MainWindow)
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(12)
        font.setBold(True)
        self.centralwidget.setFont(font)

        # Версия лаунчера (самый верх)
        self.JavaInfoLabel = QtWidgets.QLabel(parent=self.centralwidget)
        self.JavaInfoLabel.setGeometry(QtCore.QRect(0, 2, 735, 18))
        self.JavaInfoLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.JavaInfoLabel.setObjectName("JavaInfoLabel")

        # Прогресс/сообщения
        self.Progress = QtWidgets.QLabel(parent=self.centralwidget)
        self.Progress.setGeometry(QtCore.QRect(0, 0, 735, 150))
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(18)
        font.setBold(True)
        self.Progress.setFont(font)
        self.Progress.setText("")
        self.Progress.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.Progress.setObjectName("Progress")

        # Прогресс-бар установки (скрыт по умолчанию)
        self.InstallProgressBar = QtWidgets.QProgressBar(parent=self.centralwidget)
        self.InstallProgressBar.setGeometry(QtCore.QRect(210, 140, 325, 12))
        self.InstallProgressBar.setValue(0)
        self.InstallProgressBar.setTextVisible(False)
        self.InstallProgressBar.setObjectName("InstallProgressBar")
        self.InstallProgressBar.hide()

        # --- Левая колонка ---

        # Никнейм
        self.NicknameLabel = QtWidgets.QLabel(parent=self.centralwidget)
        self.NicknameLabel.setGeometry(QtCore.QRect(210, 365, 260, 20))
        self.NicknameLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.NicknameLabel.setObjectName("NicknameLabel")

        self.Nickname = QtWidgets.QComboBox(parent=self.centralwidget)
        self.Nickname.setEditable(True)
        self.Nickname.setGeometry(QtCore.QRect(210, 395, 260, 70))
        self.Nickname.setObjectName("Nickname")

        # Крестик удаления ника (70x70 квадрат)
        self.DeleteNicknameButton = QtWidgets.QPushButton(parent=self.centralwidget)
        self.DeleteNicknameButton.setGeometry(QtCore.QRect(475, 395, 70, 70))
        font = QtGui.QFont()
        font.setPointSize(20)
        font.setBold(True)
        self.DeleteNicknameButton.setFont(font)
        self.DeleteNicknameButton.setObjectName("DeleteNicknameButton")

        # Версия игры
        self.GameVersionLabel = QtWidgets.QLabel(parent=self.centralwidget)
        self.GameVersionLabel.setGeometry(QtCore.QRect(210, 475, 260, 20))
        self.GameVersionLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.GameVersionLabel.setObjectName("GameVersionLabel")

        self.VersionComboBox = QtWidgets.QComboBox(parent=self.centralwidget)
        self.VersionComboBox.setEditable(False)
        self.VersionComboBox.setGeometry(QtCore.QRect(210, 495, 260, 70))
        self.VersionComboBox.setObjectName("VersionComboBox")

        # Кнопка обновить версии (70x70 квадрат)
        self.RefreshVersionsButton = QtWidgets.QPushButton(parent=self.centralwidget)
        self.RefreshVersionsButton.setGeometry(QtCore.QRect(475, 495, 70, 70))
        font = QtGui.QFont()
        font.setPointSize(20)
        font.setBold(True)
        self.RefreshVersionsButton.setFont(font)
        self.RefreshVersionsButton.setObjectName("RefreshVersionsButton")

        # Кнопка "Открыть папку" (70x70)
        self.FilesButton = QtWidgets.QPushButton(parent=self.centralwidget)
        self.FilesButton.setGeometry(QtCore.QRect(10, 495, 70, 70))
        font = QtGui.QFont()
        font.setPointSize(20)
        font.setBold(True)
        self.FilesButton.setFont(font)
        self.FilesButton.setText("")
        self.FilesButton.setObjectName("FilesButton")

        # Кнопка GitHub (70x70)
        self.GitHubButton = QtWidgets.QPushButton(parent=self.centralwidget)
        self.GitHubButton.setGeometry(QtCore.QRect(90, 495, 70, 70))
        self.GitHubButton.setText("")
        self.GitHubButton.setObjectName("GitHubButton")

        # --- Правая колонка ---

        # Кнопка "Настройки"
        self.SettingsButton = QtWidgets.QPushButton(parent=self.centralwidget)
        self.SettingsButton.setGeometry(QtCore.QRect(550, 295, 175, 70))
        self.SettingsButton.setObjectName("SettingsButton")

        # Кнопка "Скачать"
        self.DownLoadMinecraft = QtWidgets.QPushButton(parent=self.centralwidget)
        self.DownLoadMinecraft.setGeometry(QtCore.QRect(550, 395, 175, 70))
        self.DownLoadMinecraft.setObjectName("DownLoadMinecraft")

        # Кнопка "Играть"
        self.PlayMinecraft = QtWidgets.QPushButton(parent=self.centralwidget)
        self.PlayMinecraft.setGeometry(QtCore.QRect(550, 495, 175, 70))
        self.PlayMinecraft.setObjectName("PlayMinecraft")

        # Кнопка "Удалить версию" (70x70)
        self.DeleteVersionButton = QtWidgets.QPushButton(parent=self.centralwidget)
        self.DeleteVersionButton.setGeometry(QtCore.QRect(10, 415, 70, 70))
        font = QtGui.QFont()
        font.setPointSize(16)
        font.setBold(True)
        self.DeleteVersionButton.setFont(font)
        self.DeleteVersionButton.setObjectName("DeleteVersionButton")

        # Кнопка "Отмена установки" (скрыта по умолчанию)
        self.CancelInstallButton = QtWidgets.QPushButton(parent=self.centralwidget)
        self.CancelInstallButton.setGeometry(QtCore.QRect(550, 395, 175, 70))
        self.CancelInstallButton.setObjectName("CancelInstallButton")
        self.CancelInstallButton.hide()

        # Кнопка модов (+MOD) рядом с кнопкой удаления версии
        self.InstallModloaderButton = QtWidgets.QPushButton(parent=self.centralwidget)
        self.InstallModloaderButton.setGeometry(QtCore.QRect(90, 415, 70, 70))
        font_mod = QtGui.QFont()
        font_mod.setPointSize(13)
        font_mod.setBold(True)
        self.InstallModloaderButton.setFont(font_mod)
        self.InstallModloaderButton.setText("+MOD")
        self.InstallModloaderButton.setObjectName("InstallModloaderButton")

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(parent=MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 735, 22))
        MainWindow.setMenuBar(self.menubar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "LightLauncher"))
        self.PlayMinecraft.setText(_translate("MainWindow", "ИГРАТЬ"))
        self.DownLoadMinecraft.setText(_translate("MainWindow", "СКАЧАТЬ"))
        self.SettingsButton.setText(_translate("MainWindow", "НАСТРОЙКИ"))
        self.NicknameLabel.setText(_translate("MainWindow", "Имя игрока"))
        self.GameVersionLabel.setText(_translate("MainWindow", " Версия игры"))
        self.RefreshVersionsButton.setText(_translate("MainWindow", "\U0001f504"))
        self.DeleteNicknameButton.setText(_translate("MainWindow", "\u2715"))
        self.DeleteVersionButton.setText(_translate("MainWindow", "\U0001f5d1"))
        self.CancelInstallButton.setText(_translate("MainWindow", "ОТМЕНА"))

        # Тултипы
        self.PlayMinecraft.setToolTip(_translate("MainWindow", "Запустить Minecraft"))
        self.DownLoadMinecraft.setToolTip(_translate("MainWindow", "Скачать выбранную версию"))
        self.SettingsButton.setToolTip(_translate("MainWindow", "Открыть настройки лаунчера"))
        self.Nickname.setToolTip(_translate("MainWindow", "Введите или выберите никнейм"))
        self.VersionComboBox.setToolTip(_translate("MainWindow", "Выберите версию Minecraft"))
        self.RefreshVersionsButton.setToolTip(_translate("MainWindow", "Обновить список версий"))
        self.FilesButton.setToolTip(_translate("MainWindow", "Открыть папку с игрой"))
        self.GitHubButton.setToolTip(_translate("MainWindow", "Открыть GitHub проекта"))
        self.DeleteNicknameButton.setToolTip(_translate("MainWindow", "Удалить ник из списка"))
        self.DeleteVersionButton.setToolTip(_translate("MainWindow", "Удалить выбранную версию"))
        self.CancelInstallButton.setToolTip(_translate("MainWindow", "Отменить установку"))
