# -*- coding: utf-8 -*-
"""
MCL Launcher — 全局常量 & 路径配置
"""
import os
import locale
import platform
from pathlib import Path

APP_NAME = "MCL Launcher"
APP_VERSION = "v1.1"
AUTHOR_NAME = "MrKyng"
GITHUB_URL = "https://github.com/realmrkyng"
UPDATE_URL = "https://raw.githubusercontent.com/realmrkyng/MCL/main/version.txt"
MINECRAFT_STORE_URL = "https://www.minecraft.net/zh-hans/store"

DEFAULT_RAM = 4  # GB

# ==================== 下载源配置 ====================
MIRROR_BASE_URL = "https://bmclapi2.bangbang93.com"

# 官方 Mojang 域名 → BMCLAPI 镜像域名映射
URL_REWRITE_RULES = {
    "launchermeta.mojang.com":           "bmclapi2.bangbang93.com",
    "libraries.minecraft.net":           "bmclapi2.bangbang93.com/libraries",
    "resources.download.minecraft.net":  "bmclapi2.bangbang93.com/assets",
}

# Java 运行时清单 URL (官方 / 镜像)
JVM_MANIFEST_URL_OFFICIAL = (
    "https://launchermeta.mojang.com/v1/products/java-runtime/"
    "2ec0cc96c44e5a76b9c8b7c39df7210883d12871/all.json"
)

# 国内 Java JDK 下载指引
JAVA_DOWNLOAD_GUIDE_URLS_CN = [
    ("Adoptium (清华 TUNA)", "https://mirrors.tuna.tsinghua.edu.cn/Adoptium/"),
    ("华为云 OpenJDK", "https://mirrors.huaweicloud.com/openjdk/"),
    ("阿里 Dragonwell JDK", "https://dragonwell-jdk.io/"),
    ("INJDK 综合下载站", "https://www.injdk.cn/"),
]
JAVA_DOWNLOAD_GUIDE_URLS_INTL = [
    ("Adoptium", "https://adoptium.net/download/"),
    ("Oracle JDK", "https://www.oracle.com/java/technologies/downloads/"),
    ("Microsoft OpenJDK", "https://www.microsoft.com/openjdk"),
]


def is_chinese_locale():
    """检测系统是否为中国区域（用于默认下载源选择）"""
    try:
        lang = locale.getdefaultlocale()[0] or ""
        return lang.lower().startswith("zh")
    except Exception:
        return False


def get_default_download_source():
    """中文系统默认使用 BMCLAPI 镜像，其他默认使用官方源"""
    return "bmclapi" if is_chinese_locale() else "official"


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
