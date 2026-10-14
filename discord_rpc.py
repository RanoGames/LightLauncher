"""Discord Rich Presence интеграция."""

import contextlib
import logging
import threading
import time
from typing import Optional

logger = logging.getLogger("LightLauncher")

try:
    from pypresence import Presence as _DiscordPresence
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False


class DiscordRPC:
    """Управление Discord Rich Presence (подключение/отключение)."""

    def __init__(self, client_id: str) -> None:
        self.client_id = client_id
        self.running = False
        self._rpc = None
        self._thread: Optional[threading.Thread] = None
        self._version: str = ""

    def start(self, version: str) -> None:
        """Запускает RPC в фоновом потоке."""
        if not DISCORD_AVAILABLE:
            return
        self.stop()
        self._version = version
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        self.running = True
        while self.running:
            try:
                self._rpc = _DiscordPresence(self.client_id)
                self._rpc.connect()
                self._rpc.update(
                    state=f"Версия {self._version}",
                    details="Играет в Minecraft",
                    start=int(time.time()),
                    large_image="minecraft",
                    large_text="Light Minecraft Launcher",
                )
                while self.running:
                    time.sleep(15)
            except Exception:
                if self.running:
                    time.sleep(10)

    def stop(self) -> None:
        """Останавливает RPC и закрывает соединение."""
        self.running = False
        if self._rpc:
            with contextlib.suppress(Exception):
                self._rpc.close()
            self._rpc = None
