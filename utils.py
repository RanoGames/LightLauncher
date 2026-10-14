"""Утилиты: кэш, локализация, пути, системные функции."""

import json
import locale
import logging
import os
import re
import sys
import time
from typing import Optional

import psutil
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from constants import CACHE_DIR

logger = logging.getLogger("LightLauncher")


# ============================================================
# Recommendation #7: HTTP-сессия с автоматическими повторами
# ============================================================
_session: Optional[requests.Session] = None


def get_http_session() -> requests.Session:
    """Возвращает HTTP-сессию с retry (3 попытки, backoff 0.5 с)."""
    global _session
    if _session is None:
        _session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry)
        _session.mount("https://", adapter)
        _session.mount("http://", adapter)
        _session.headers.update({"User-Agent": "LightLauncher"})
    return _session


# ============================================================
# Кэширование
# ============================================================
def get_cached_path(filename: str) -> str:
    """Путь к файлу в кэше."""
    return os.path.join(CACHE_DIR, filename)


def is_cache_valid(filename: str, max_age_seconds: int = 3600) -> bool:
    """Проверяет, не устарел ли кэш."""
    path = get_cached_path(filename)
    if not os.path.exists(path):
        return False
    try:
        return (time.time() - os.path.getmtime(path)) < max_age_seconds
    except Exception:                                   # Bug #8 fix
        return False


# ============================================================
# Bug #3 fix: робастный парсинг версий
# ============================================================
def version_tuple(v: str) -> tuple[int, ...]:
    """Парсит строку версии в кортеж чисел.

    Обрабатывает суффиксы вроде ``0.43-beta``, ``1.0rc1``.
    Также нормализует минорные версии вроде ``0.5`` -> ``(0, 50)``,
    чтобы идти после ``0.42`` / ``0.43``.
    """
    parts = re.split(r'[.\-_]', v.strip())
    result: list[int] = []
    for i, p in enumerate(parts):
        m = re.match(r'(\d+)', p)
        if m:
            val = int(m.group(1))
            if i == 1 and parts[0] == "0" and len(m.group(1)) == 1 and val < 10:
                val = val * 10
            result.append(val)
    return tuple(result) if result else (0,)


# ============================================================
# Recommendation #5: локализация из JSON-файлов
# ============================================================
_lang_data: dict[str, dict[str, str]] = {}


def _load_lang_data() -> None:
    """Загружает ``lang/ru.json`` и ``lang/en.json``."""
    global _lang_data
    lang_dir = os.path.join(get_exe_dir(), "lang")
    for code in ("ru", "en"):
        path = os.path.join(lang_dir, f"{code}.json")
        try:
            with open(path, encoding="utf-8") as f:
                _lang_data[code] = json.load(f)
        except Exception:
            logger.warning("Не удалось загрузить локализацию: %s", path)
            _lang_data[code] = {}


def get_system_lang() -> str:
    """Определяет язык ОС (``'ru'`` или ``'en'``)."""
    try:
        lang = locale.getlocale()[0]
        if lang and lang.startswith("ru"):
            return "ru"
    except Exception:
        pass
    return "en"


def resolve_lang(lang_setting: str) -> str:
    """Превращает ``'auto'`` в конкретный язык; остальное — без изменений."""
    if lang_setting == "auto":
        return get_system_lang()
    return lang_setting


def t(key: str, lang: str = "ru") -> str:
    """Возвращает локализованную строку по ключу."""
    if not _lang_data:
        _load_lang_data()
    return _lang_data.get(lang, {}).get(key,
           _lang_data.get("ru", {}).get(key, key))


# ============================================================
# Bug #14 fix: пути к ресурсам рядом с exe, а не в CWD
# ============================================================
def get_exe_dir() -> str:
    """Папка, где лежит лаунчер (frozen exe или .py скрипт)."""
    if getattr(sys, "frozen", False) or hasattr(sys, "__compiled__") or "__compiled__" in globals():
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def resource_path(filename: str) -> str:
    """Абсолютный путь к ресурсу (иконка, фон и т.д.)."""
    return os.path.join(get_exe_dir(), filename)


# ============================================================
# Системные функции
# ============================================================
def get_optimal_ram() -> int:
    """Оптимальный объём RAM для Minecraft (в МБ)."""
    total_mb = int(psutil.virtual_memory().total / (1024 * 1024))
    if total_mb <= 4096:
        return max(1024, total_mb // 4)
    elif total_mb <= 8192:
        return total_mb // 3
    else:
        return min(total_mb // 2, 8192)


def check_disk_space(path: str, required_mb: int = 2048) -> tuple[float, bool]:
    """Возвращает ``(свободно_МБ, хватает_ли)``."""
    try:
        usage = psutil.disk_usage(path)
        free_mb = usage.free / (1024 * 1024)
        return free_mb, free_mb >= required_mb
    except Exception:
        return 0.0, False


# ============================================================
# Recommendation #6: валидация никнейма
# ============================================================
_NICK_RE = re.compile(r'^[a-zA-Z0-9_]{3,16}$')


def is_valid_nickname(nick: str) -> bool:
    """3-16 символов: латиница, цифры, ``_``."""
    return bool(_NICK_RE.match(nick))
