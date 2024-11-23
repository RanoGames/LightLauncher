import design
from design import Ui_MainWindow
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QWidget
from PyQt6.QtGui import QPalette, QColor, QIcon
from minecraft_launcher_lib.install import install_minecraft_version
from minecraft_launcher_lib.utils import get_minecraft_directory
from minecraft_launcher_lib.command import get_minecraft_command
from subprocess import call
import sys
import threading
import subprocess

minecraft_directory = get_minecraft_directory().replace('minecraft', 'LightMinecraft')

max_value = [0]
def maximum(max_value, value):
    max_value[0] = value

def printprogressbar(iteration, total, prefix='', suffix='', decimals=1, length=100, fill='█', printEnd="\r"):
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledlength = int(length * iteration // total)
    bar = fill * filledlength + '-' * (length - filledlength)
    print('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix), end=printEnd)
    if iteration == total:
        print()


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
        self.setWindowIcon(QIcon("mclovin.ico"))
        mcversion = self.ui.Version.text()
        mcoptions = {'username': self.ui.Nickname.text(), }
        self.ui.PlayMinecraft.clicked.connect(lambda:  self.runmc(mcoptions, mcversion))
        self.ui.DownLoadMinecraft.clicked.connect(lambda: self.installmc(mcoptions, mcversion))

    def runmc(self, mcoptions, mcversion):
        mcoptions = {'username': self.ui.Nickname.text(), }
        mcversion = self.ui.Version.text()
        Launcher.hide(self)
        thread = threading.Thread(target=call(get_minecraft_command(version=mcversion,minecraft_directory=minecraft_directory,options=mcoptions)))
        thread.start()
        thread.join()
        Launcher.show(self)

    def installmc(self, mcoptions, mcversion):
        self.ui.Progress.setText("Идет установка")
        mcoptions = {'username': self.ui.Nickname.text(), }
        mcversion = self.ui.Version.text()
        self.setWindowTitle("Идет загрузка...")
        thread = threading.Thread(target=install_minecraft_version(versionid=mcversion,minecraft_directory=minecraft_directory,callback=callback))
        thread.start()
        thread.join()
        self.ui.Progress.setText("Установка прошла успешно")
        self.setWindowTitle("TLSLanucher")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    Launcher().show()
    app.exec()
    Launcher.show()
