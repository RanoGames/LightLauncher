"""LightLauncher — точка входа.

Настраивает logging, глобальный exception hook и запускает приложение.
"""

import datetime
import logging
import os
import sys
import traceback

from PyQt6.QtWidgets import QApplication, QMessageBox

from constants import CACHE_DIR, LAUNCHER_VERSION, MINECRAFT_DIRECTORY

# ================================================================
# Recommendation #3: logging вместо print()
# ================================================================
# Bug #10 fix: логи пишутся в MINECRAFT_DIRECTORY, а не в CWD
os.makedirs(MINECRAFT_DIRECTORY, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

LOG_FILE = os.path.join(MINECRAFT_DIRECTORY, "launcher.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("LightLauncher")


# ================================================================
# Глобальный перехват исключений
# Bug #10 fix: crash_log.txt → MINECRAFT_DIRECTORY
# Bug #8 fix: except Exception вместо голого except
# ================================================================
def log_uncaught_exceptions(ex_cls, ex, tb):
    """Записывает необработанные исключения в crash_log.txt."""
    text = "".join(traceback.format_exception(ex_cls, ex, tb))
    logger.critical(text)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sys_info = (
        f"Launcher: v{LAUNCHER_VERSION}\n"
        f"Python: {sys.version}\n"
        f"Platform: {sys.platform}\n"
        f"MC Dir: {MINECRAFT_DIRECTORY}\n"
    )

    try:
        import platform
        sys_info += f"OS: {platform.platform()}\n"
    except Exception:
        pass

    try:
        import psutil
        sys_info += f"RAM: {psutil.virtual_memory().total // (1024 * 1024)} MB\n"
    except Exception:
        pass

    crash_log_path = os.path.join(MINECRAFT_DIRECTORY, "crash_log.txt")
    with open(crash_log_path, "a", encoding="utf-8") as f:
        f.write(f"\n{'=' * 50}\n")
        f.write(f"[{timestamp}] CRITICAL ERROR\n")
        f.write(f"{'=' * 50}\n")
        f.write(f"{sys_info}\n")
        f.write(f"Exception: {ex_cls.__name__}: {ex}\n")
        f.write(f"{'-' * 50}\n")
        f.write(text)
        f.write(f"{'=' * 50}\n")

    if QApplication.instance():
        try:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setText("Критическая ошибка!")
            msg.setInformativeText(
                f"Лог сохранён в {crash_log_path}\n\n{ex_cls.__name__}: {ex}"
            )
            msg.setDetailedText(f"{sys_info}\n{text}")
            msg.exec()
        except Exception:                               # Bug #8 fix
            pass
    sys.exit(1)


sys.excepthook = log_uncaught_exceptions


# ================================================================
# Запуск приложения
# ================================================================
if __name__ == "__main__":
    from launcher import Launcher

    app = QApplication(sys.argv)
    window = Launcher()
    window.show()
    logger.info("LightLauncher v%s запущен", LAUNCHER_VERSION)
    sys.exit(app.exec())
