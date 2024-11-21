from mypy.types import names

import design
from design import Ui_MainWindow
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget
from PyQt6.QtGui import QPalette, QColor
from minecraft_launcher_lib.install import install_minecraft_version
from minecraft_launcher_lib.utils import get_minecraft_directory
from minecraft_launcher_lib.command import get_minecraft_command
from subprocess import call
import sys

minecraft_directory = get_minecraft_directory().replace('minecraft', 'LightMinecraft')
max_value = [0]
callback = {
    "setStatus": lambda text: print(text, end=''),
    "setProgress": lambda value: printprogressbar(value, max_value[0]),
    "setMax": lambda value: maximum(max_value, value)
}

class Launcher(QMainWindow):
    def __init__(self):
        super(Launcher, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.setWindowTitle("TestTitle")
        self.setWindowIcon(QIcon("mclovin.ico"))
        self.ui.PlayMinecraft.clicked.connect(runmc)
        self.ui.DownLoadMinecraft.clicked.connect(downloadmc)
        self.ui.Version.textChanged.connect(runmc)
        self.ui.Nickname.textChanged.connect(downloadmc)


def runmc(self):
    options = {'username': "test" ,}
    version = "rd-132211"
    call(get_minecraft_command(version=version, minecraft_directory=minecraft_directory, options=options))

def downloadmc(self):
    options = {'username': "test", }
    version = "rd-132211"
    install_minecraft_version(versionid=version, minecraft_directory=minecraft_directory, callback=callback)

def printprogressbar(iteration, total, prefix='', suffix='', decimals=1, length=100, fill='█', printEnd="\r"):
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix), end=printEnd)
    if iteration == total:
        print()


def maximum(max_value, value):
    max_value[0] = value


app = QApplication(sys.argv)
window = Launcher()
window.show()
app.exec()


# while True:
#     version = input('Select version: ')
#     username = input('username: ')
#
#     print('=======================================================================================')
#     max_value = [0]
#     callback = {
#         "setStatus": lambda text: print(text, end=''),
#         "setProgress": lambda value: printprogressbar(value, max_value[0]),
#         "setMax": lambda value: maximum(max_value, value)
#     }
#     options = {
#         'username': username,
#     }
#
#     while True:
#         DownloadOrRun = int(input("[1] Run Minecraft \n[2] Download/Repair Minecraft \nPlease enter number: "))
#
#         if DownloadOrRun == 1:
#             call(
#                 get_minecraft_command(version=version,
#                                       minecraft_directory=minecraft_directory,
#                                       options=options))
#             break
#         if DownloadOrRun == 2:
#             install_minecraft_version(versionid=version,
#                                       minecraft_directory=minecraft_directory,
#                                       callback=callback)
#             break
#         print("\nIncorrect Choose, Please Enter Correct Number\n")
