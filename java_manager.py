"""Менеджер версий Java: поиск, парсинг версий и сопоставление с версиями Minecraft."""

import logging
import os
import re
import subprocess
from typing import Optional

logger = logging.getLogger("LightLauncher")


def parse_java_major_version(java_exe: str) -> Optional[int]:
    """Запускает java.exe -version и возвращает мажорную версию (8, 11, 16, 17, 21 и т.д.)."""
    if not os.path.exists(java_exe):
        return None
    try:
        res = subprocess.run(
            [java_exe, "-version"],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        output = res.stderr or res.stdout
        # Обрабатывает: 'version "1.8.0_401"', 'version "17.0.2"', 'version "21.0.1"'
        m = re.search(r'version\s+"(?:1\.)?(\d+)', output)
        if m:
            return int(m.group(1))
    except Exception as e:
        logger.debug("Не удалось определить версию Java для %s: %s", java_exe, e)
    return None


def find_installed_javas() -> list[dict]:
    """Ищет все установленные в системе среды Java (JRE/JDK).

    Возвращает список словарей: [{'path': str, 'version': int, 'name': str}]
    """
    found_paths: set[str] = set()

    from constants import MINECRAFT_DIRECTORY

    search_dirs: list[str] = []
    if os.name == "nt":
        prog_files = os.environ.get("PROGRAMFILES", "C:\\Program Files")
        prog_files_x86 = os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)")
        local_app_data = os.environ.get("LOCALAPPDATA", "")

        for base in [prog_files, prog_files_x86]:
            search_dirs.extend([
                os.path.join(base, "Java"),
                os.path.join(base, "Eclipse Adoptium"),
                os.path.join(base, "BellSoft"),
                os.path.join(base, "Microsoft"),
                os.path.join(base, "Zulu"),
                os.path.join(base, "Semeru"),
            ])
        if local_app_data:
            search_dirs.append(os.path.join(local_app_data, "Programs", "Eclipse Adoptium"))

    runtime_dir = os.path.join(MINECRAFT_DIRECTORY, "runtime")
    if os.path.isdir(runtime_dir):
        search_dirs.append(runtime_dir)

    # Поиск по директориям
    for d in search_dirs:
        if os.path.isdir(d):
            try:
                for root, _, files in os.walk(d):
                    for f in files:
                        if f.lower() in ("javaw.exe", "java.exe"):
                            full_p = os.path.normpath(os.path.join(root, f))
                            # Предпочитаем javaw.exe
                            found_paths.add(full_p)
            except Exception:
                pass

    # Проверка PATH / системной Java
    try:
        from minecraft_launcher_lib.utils import get_java_executable
        sys_java = get_java_executable()
        if sys_java and os.path.exists(sys_java):
            found_paths.add(os.path.normpath(sys_java))
    except Exception:
        pass

    # Группируем javaw / java
    parsed: list[dict] = []
    seen_dirs: set[str] = set()

    # Сначала проверяем javaw
    sorted_paths = sorted(found_paths, key=lambda p: (0 if "javaw.exe" in p.lower() else 1))

    for p in sorted_paths:
        parent_dir = os.path.dirname(p).lower()
        if parent_dir in seen_dirs:
            continue
        major = parse_java_major_version(p)
        if major:
            seen_dirs.add(parent_dir)
            parsed.append({
                "path": p,
                "version": major,
                "name": f"Java {major} ({p})",
            })

    # Сортируем по версии (по убыванию: 21, 17, 16, 8...)
    parsed.sort(key=lambda x: x["version"], reverse=True)
    return parsed


def get_required_java_major(mc_version: str) -> int:
    """Определяет необходимую мажорную версию Java для заданной версии Minecraft."""
    # Поддержка снапшотов вида 24w14a
    snap_match = re.match(r'^(\d{2})w\d+[a-z]', mc_version.lower())
    if snap_match:
        year = int(snap_match.group(1))
        if year >= 24:
            return 21
        elif year >= 22:
            return 17
        elif year == 21:
            return 16
        else:
            return 8

    # Поиск шаблона 1.X.X или 1.X
    m = re.search(r'1\.(\d+)(?:\.(\d+))?', mc_version)
    if not m:
        return 8  # по умолчанию для старых/неизвестных версий

    minor = int(m.group(1))
    patch = int(m.group(2)) if m.group(2) else 0

    if minor >= 21 or (minor == 20 and patch >= 5):
        return 21
    elif minor >= 18:
        return 17
    elif minor == 17:
        return 16
    else:
        return 8


def select_best_java(
    mc_version: str,
    user_java_path: Optional[str] = None,
    auto_detect: bool = True,
) -> tuple[Optional[str], Optional[str]]:
    """Выбирает подходящий путь к Java.

    Возвращает: (путь_к_java, предупреждение_если_есть)
    """
    req_major = get_required_java_major(mc_version)

    # Если автоопределение выключено и пользователь указал конкретный путь
    if not auto_detect and user_java_path and os.path.exists(user_java_path):
        actual_major = parse_java_major_version(user_java_path)
        warning = None
        if actual_major and actual_major != req_major:
            # Для MC >= 18 подходит и Java 21, но для < 17 Java 17/21 часто ломает Forge
            if req_major == 8 and actual_major > 8:
                warning = f"Версии Minecraft {mc_version} требуется Java 8, а выбрана Java {actual_major}. Возможен краш!"
            elif req_major > actual_major:
                warning = f"Minecraft {mc_version} требуется как минимум Java {req_major}, а выбрана Java {actual_major}!"
        return user_java_path, warning

    # Режим автоопределения
    installed = find_installed_javas()
    if not installed:
        # Пытаемся взять системную Java
        try:
            from minecraft_launcher_lib.utils import get_java_executable
            sys_java = get_java_executable()
            if sys_java and os.path.exists(sys_java):
                actual = parse_java_major_version(sys_java)
                warning = None
                if actual and actual < req_major:
                    warning = f"Для Minecraft {mc_version} требуется Java {req_major}, а в системе установлена только Java {actual}."
                return sys_java, warning
        except Exception:
            pass
        return None, "Java не найдена на компьютере! Установите Java."

    # 1. Ищем точное совпадение
    exact_matches = [j for j in installed if j["version"] == req_major]
    if exact_matches:
        return exact_matches[0]["path"], None

    # 2. Если требуется Java 17, а есть Java 21 — она часто подходит
    if req_major in (16, 17):
        compatible = [j for j in installed if j["version"] >= req_major]
        if compatible:
            best = compatible[-1]  # берем минимально совместимую (например 17 вместо 21)
            return best["path"], None

    # 3. Если точной нет, берём максимально близкую с предупреждением
    fallback = installed[0]
    warning = (
        f"Для Minecraft {mc_version} рекомендуется Java {req_major}, "
        f"но найдена только Java {fallback['version']}. Возможен краш при запуске!"
    )
    return fallback["path"], warning


def get_mojang_runtime_name(req_major: int) -> str:
    """Возвращает кодовое имя официального Mojang JVM Runtime для указанной мажорной версии."""
    if req_major <= 8:
        return "jre-legacy"
    elif req_major == 16:
        return "java-runtime-alpha"
    elif req_major in (17, 18, 19, 20):
        return "java-runtime-gamma"
    else:
        return "java-runtime-delta"


def get_runtime_name_for_version(mc_version: str) -> str:
    """Определяет имя Mojang JVM Runtime для заданной версии Minecraft."""
    from constants import MINECRAFT_DIRECTORY
    try:
        import minecraft_launcher_lib.runtime as rt
        info = rt.get_version_runtime_information(mc_version, MINECRAFT_DIRECTORY)
        if isinstance(info, dict) and "name" in info and info["name"]:
            return info["name"]
    except Exception:
        pass
    major = get_required_java_major(mc_version)
    return get_mojang_runtime_name(major)


def get_runtime_java_path(runtime_name: str) -> Optional[str]:
    """Ищет исполняемый файл javaw.exe/java.exe в установленном Mojang runtime."""
    from constants import MINECRAFT_DIRECTORY
    try:
        import minecraft_launcher_lib.runtime as rt
        exe = rt.get_executable_path(runtime_name, MINECRAFT_DIRECTORY)
        if exe and os.path.exists(exe):
            javaw = os.path.join(os.path.dirname(exe), "javaw.exe")
            if os.path.exists(javaw):
                return javaw
            return exe
    except Exception:
        pass

    rt_dir = os.path.join(MINECRAFT_DIRECTORY, "runtime", runtime_name)
    if os.path.isdir(rt_dir):
        for root, _, files in os.walk(rt_dir):
            if "javaw.exe" in files:
                return os.path.join(root, "javaw.exe")
            if "java.exe" in files:
                return os.path.join(root, "java.exe")
    return None


def is_runtime_installed(runtime_name: str) -> bool:
    """Проверяет, скачан ли уже указанный Mojang JVM runtime."""
    return get_runtime_java_path(runtime_name) is not None
