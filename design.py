# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'untitled.ui'
##
## Created by: Qt User Interface Compiler version 6.8.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PyQt6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PyQt6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PyQt6.QtWidgets import (QApplication, QLineEdit, QMainWindow, QMenuBar,
    QPushButton, QSizePolicy, QStatusBar, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(800, 600)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.PlayMinecraft = QPushButton(self.centralwidget)
        self.PlayMinecraft.setObjectName(u"PlayMinecraft")
        self.PlayMinecraft.setGeometry(QRect(550, 450, 161, 61))
        font = QFont()
        font.setFamilies([u"Microsoft Tai Le"])
        font.setPointSize(20)
        font.setBold(True)
        self.PlayMinecraft.setFont(font)
        self.Version = QLineEdit(self.centralwidget)
        self.Version.setObjectName(u"Version")
        self.Version.setGeometry(QRect(170, 430, 271, 81))
        self.Version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.DownLoadMinecraft = QPushButton(self.centralwidget)
        self.DownLoadMinecraft.setObjectName(u"DownLoadMinecraft")
        self.DownLoadMinecraft.setGeometry(QRect(550, 360, 161, 61))
        self.DownLoadMinecraft.setFont(font)
        self.Nickname = QLineEdit(self.centralwidget)
        self.Nickname.setObjectName(u"Nickname")
        self.Nickname.setGeometry(QRect(300, 310, 271, 81))
        self.Nickname.setAlignment(Qt.AlignmentFlag.AlignCenter)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 800, 33))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"TLSLanucher", None))
        self.PlayMinecraft.setText(QCoreApplication.translate("MainWindow", u"\u0418\u0413\u0420\u0410\u0422\u042c", None))
        self.DownLoadMinecraft.setText(QCoreApplication.translate("MainWindow", u"\u0421\u041a\u0410\u0427\u0410\u0422\u042c", None))
    # retranslateUi



