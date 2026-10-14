"""Поддержка скинов для пиратских аккаунтов (Ely.by / authlib-injector) и отображение аватарок."""

import logging
import os
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage

from constants import CACHE_DIR
from utils import get_http_session

logger = logging.getLogger("LightLauncher")

AUTHLIB_URL = "https://github.com/yushijinhun/authlib-injector/releases/download/v1.2.8/authlib-injector-1.2.8.jar"
AUTHLIB_JAR_PATH = os.path.join(CACHE_DIR, "authlib-injector.jar")
ELY_BY_API = "https://authlib-injector.yggdrasil.ely.by"


def ensure_authlib_injector() -> Optional[str]:
    """Проверяет наличие authlib-injector.jar в кэше, при необходимости скачивает."""
    if os.path.exists(AUTHLIB_JAR_PATH) and os.path.getsize(AUTHLIB_JAR_PATH) > 100000:
        return AUTHLIB_JAR_PATH

    os.makedirs(CACHE_DIR, exist_ok=True)
    try:
        logger.info("Скачивание authlib-injector.jar для скинов Ely.by...")
        session = get_http_session()
        resp = session.get(AUTHLIB_URL, timeout=15, allow_redirects=True)
        if resp.status_code == 200 and len(resp.content) > 100000:
            with open(AUTHLIB_JAR_PATH, "wb") as f:
                f.write(resp.content)
            return AUTHLIB_JAR_PATH
    except Exception as e:
        logger.warning("Не удалось скачать authlib-injector: %s", e)

    return None


class AvatarLoader(QThread):
    """Поток загрузки 2D-аватарки головы игрока (48x48) по никнейму."""

    avatar_loaded = pyqtSignal(str, QImage)  # username, image

    def __init__(self, username: str) -> None:
        super().__init__()
        self.username = username

    def run(self) -> None:
        if not self.username:
            return

        avatar_dir = os.path.join(CACHE_DIR, "avatars")
        os.makedirs(avatar_dir, exist_ok=True)
        cached_file = os.path.join(avatar_dir, f"{self.username.lower()}.png")

        # 1. Если уже в кэше
        if os.path.exists(cached_file):
            img = QImage(cached_file)
            if not img.isNull():
                self.avatar_loaded.emit(self.username, img)
                return

        # 2. Скачиваем с Minotar / Crafatar
        urls = [
            f"https://minotar.net/avatar/{self.username}/48.png",
            f"https://crafatar.com/avatars/{self.username}?size=48&overlay",
        ]
        session = get_http_session()
        for url in urls:
            try:
                r = session.get(url, timeout=4)
                if r.status_code == 200 and len(r.content) > 100:
                    with open(cached_file, "wb") as f:
                        f.write(r.content)
                    img = QImage()
                    img.loadFromData(r.content)
                    if not img.isNull():
                        self.avatar_loaded.emit(self.username, img)
                        return
            except Exception:
                pass
