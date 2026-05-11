# -*- coding: utf-8 -*-
"""
MCL Launcher — 全局常量 & 路径配置
"""
import os
import platform
from pathlib import Path

APP_NAME = "MCL Launcher"
APP_VERSION = "v1.1"
AUTHOR_NAME = "MrKyng"
GITHUB_URL = "https://github.com/realmrkyng"
UPDATE_URL = "https://raw.githubusercontent.com/realmrkyng/MCL/main/version.txt"
MINECRAFT_STORE_URL = "https://www.minecraft.net/zh-hans/store"

DEFAULT_RAM = 4  # GB


def get_minecraft_dir():
    """返回启动器数据存放根目录"""
    if platform.system() == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path.home()
    return base / ".custom_mclauncher"


MINECRAFT_DIR = get_minecraft_dir()
MINECRAFT_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_FILE = MINECRAFT_DIR / "launcher_config.json"
