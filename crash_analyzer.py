"""Умный анализатор логов краша Minecraft."""

import glob
import logging
import os
import re
from typing import Optional

from constants import MINECRAFT_DIRECTORY

logger = logging.getLogger("LightLauncher")


def analyze_latest_crash() -> Optional[dict]:
    """Анализирует последний crash-report или latest.log и выдаёт понятный диагноз."""
    crash_text = ""
    report_file = None

    # 1. Проверяем папку crash-reports
    crash_dir = os.path.join(MINECRAFT_DIRECTORY, "crash-reports")
    if os.path.isdir(crash_dir):
        files = glob.glob(os.path.join(crash_dir, "crash-*.txt"))
        if files:
            # Сортируем по времени изменения (самый свежий в конце)
            files.sort(key=os.path.getmtime)
            latest = files[-1]
            try:
                with open(latest, encoding="utf-8", errors="ignore") as f:
                    crash_text = f.read()
                report_file = latest
            except Exception:
                pass

    # 2. Если в crash-reports ничего нет, смотрим последние 300 строк logs/latest.log
    if not crash_text:
        log_file = os.path.join(MINECRAFT_DIRECTORY, "logs", "latest.log")
        if os.path.exists(log_file):
            try:
                with open(log_file, encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                    crash_text = "".join(lines[-300:])
                report_file = log_file
            except Exception:
                pass

    if not crash_text:
        return None

    # --- Анализ частых причин ---

    # 1. Нехватка оперативной памяти
    if "OutOfMemoryError" in crash_text or "java.lang.OutOfMemoryError" in crash_text:
        return {
            "title": "Недостаточно оперативной памяти (OutOfMemoryError)",
            "cause": "Minecraft превысил выделенный лимит оперативной памяти.",
            "solution": "Откройте Настройки лаунчера и увеличьте ползунок «Память (RAM)» (например, до 4096 МБ или 6144 МБ для модов).",
            "file": report_file,
        }

    # 2. Несовместимая версия Java
    if "UnsupportedClassVersionError" in crash_text or "has been compiled by a more recent version" in crash_text:
        return {
            "title": "Несовместимая версия Java",
            "cause": "Игра или один из модов собраны под более новую версию Java, чем установлена.",
            "solution": "Включите «Автоопределение Java» в настройках лаунчера или выберите вручную Java 17/21.",
            "file": report_file,
        }

    # 3. Отсутствие обязательного мода / зависимости (Fabric / Forge)
    dep_match = re.search(r"requires '([^']+)'|missing dependency:? ([^\n\r]+)|Mod ([^\s]+) requires", crash_text, re.I)
    if "ModResolutionException" in crash_text or "IncompatibleModsException" in crash_text or dep_match:
        missing = "неизвестный мод"
        if dep_match:
            for g in (dep_match.group(1), dep_match.group(2), dep_match.group(3)):
                if g:
                    missing = g.strip()
                    break
        return {
            "title": "Отсутствует зависимость мода",
            "cause": f"Один из модов требует для работы: {missing}.",
            "solution": f"Установите недостающий мод ({missing}) в папку mods через каталог модов или вручную.",
            "file": report_file,
        }

    # 4. Дубликаты модов
    if "DuplicateModsException" in crash_text or "found duplicate mods" in crash_text.lower():
        return {
            "title": "Конфликт: найдены дубликаты модов",
            "cause": "В папке mods установлено несколько версий одного и того же мода.",
            "solution": "Откройте папку mods и удалите старую копию повторяющегося мода.",
            "file": report_file,
        }

    # 5. Ошибка видеодрайвера (OpenGL / GLFW)
    if "Pixel format not accelerated" in crash_text or "GLFW error 65542" in crash_text or "WGL: The driver does not appear to support OpenGL" in crash_text:
        return {
            "title": "Ошибка видеодрайвера (OpenGL / GLFW)",
            "cause": "Видеокарта или драйвер не поддерживают требуемый профиль OpenGL.",
            "solution": "Обновите драйвер видеокарты (NVIDIA, AMD или Intel) с официального сайта производителя.",
            "file": report_file,
        }

    # 6. Ошибка Mixin (конфликт модов)
    if "MixinApplyError" in crash_text or "org.spongepowered.asm.mixin" in crash_text:
        return {
            "title": "Конфликт модов (Mixin Error)",
            "cause": "Два или более мода пытаются несовместимым образом изменить один и тот же код игры.",
            "solution": "Попробуйте отключить последние добавленные моды по одному, чтобы найти конфликтующий.",
            "file": report_file,
        }

    return None
