"""Модуль учёта времени, проведённого в игре."""

import json
import logging
import os

from constants import MINECRAFT_DIRECTORY

logger = logging.getLogger("LightLauncher")

PLAYTIME_FILE = os.path.join(MINECRAFT_DIRECTORY, "playtime.json")


def _load_data() -> dict:
    if os.path.exists(PLAYTIME_FILE):
        try:
            with open(PLAYTIME_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"total_seconds": 0, "versions": {}}


def _save_data(data: dict) -> None:
    try:
        with open(PLAYTIME_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        logger.warning("Ошибка сохранения статистики времени: %s", e)


def add_playtime(version: str | None, elapsed_seconds: int) -> None:
    """Добавляет прошедшее время сессии в статистику."""
    if elapsed_seconds <= 0:
        return
    ver_key = version or "Unknown"
    data = _load_data()
    data["total_seconds"] = data.get("total_seconds", 0) + elapsed_seconds

    vers = data.setdefault("versions", {})
    vers[ver_key] = vers.get(ver_key, 0) + elapsed_seconds

    _save_data(data)


def format_seconds(seconds: int) -> str:
    """Форматирует секунды в человекочитаемый вид: '42 ч. 15 мин.' или '45 сек.'."""
    if seconds <= 0:
        return "0 мин."
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours > 0:
        return f"{hours} ч. {minutes} мин."
    if minutes > 0:
        return f"{minutes} мин."
    return f"{seconds} сек."


def get_playtime_stats(version: str | None = None) -> tuple[str, str]:
    """Возвращает кортеж: (общее_время_строка, время_в_версии_строка)."""
    data = _load_data()
    total_str = format_seconds(data.get("total_seconds", 0))

    ver_str = "0 мин."
    if version:
        ver_sec = data.get("versions", {}).get(version, 0)
        ver_str = format_seconds(ver_sec)

    return total_str, ver_str
