from minecraft_launcher_lib import utils, command, install
import subprocess


minecraft_directory = utils.get_minecraft_directory().replace('minecraft', 'LightMinecraft')


def printprogressbar(iteration, total, prefix='', suffix='', decimals=1, length=100, fill='█', printEnd="\r"):
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix), end=printEnd)
    if iteration == total:
        print()


def maximum(max_value, value):
    max_value[0] = value

while True:
    version = input('Select version: ')
    username = input('username: ')

    print('=======================================================================================')
    max_value = [0]
    callback = {
        "setStatus": lambda text: print(text, end='\n'),
        "setProgress": lambda value: printprogressbar(value, max_value[0]),
        "setMax": lambda value: maximum(max_value, value)
    }
    options = {
        'username': username,
    }

    while True:
        DownloadOrRun = int(input("[1] Run Minecraft \n[2] Download/Repair Minecraft \nPlease enter number: "))

        if DownloadOrRun == 1:
            subprocess.call(
                command.get_minecraft_command(version=version,
                                                                     minecraft_directory=minecraft_directory,
                                                                     options=options))
            break
        if DownloadOrRun == 2:
            install.install_minecraft_version(versionid=version,
                                                                     minecraft_directory=minecraft_directory,
                                                                     callback=callback)
            break
        print("\nIncorrect Choose, Please Enter Correct Number\n")