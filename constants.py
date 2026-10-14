"""Константы и конфигурация LightLauncher."""

import os

from minecraft_launcher_lib.utils import get_minecraft_directory

# Bug #1 fix: убран бессмысленный .replace('minecraft', 'minecraft')
MINECRAFT_DIRECTORY: str = get_minecraft_directory()
SETTINGS_FILE: str = os.path.join(MINECRAFT_DIRECTORY, "settings.json")
CACHE_DIR: str = os.path.join(MINECRAFT_DIRECTORY, "cache")

VERSION_MANIFEST_URL: str = "https://launchermeta.mojang.com/mc/game/version_manifest_v2.json"
GITHUB_API_URL: str = "https://api.github.com/repos/RanoGames/LightLauncher/releases/latest"

DEFAULT_SETTINGS: dict = {
    "filters": ["release"],
    "memory": 2048,
    "last_version": None,
    "show_console": False,
    "java_path": None,
    "nicknames": [],
    "last_nickname": None,
    "language": "auto",
    "jvm_args": "",
    "validate_nickname": True,
    "auto_java": True,
    "fullscreen": False,
    "resolution_width": 1920,
    "resolution_height": 1080,
    "custom_background": None,
    "ely_by_skins": True,
    "ui_theme": "modern"
}

DISCORD_CLIENT_ID: str = "1420709615468810403"
LAUNCHER_VERSION: str = "0.50"

