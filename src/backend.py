# -*- coding: utf-8 -*-
"""
MCL Launcher — 后端逻辑：版本管理、下载、启动命令、Java 检测、内存检测
"""
import os
import re
import json
import uuid
import shutil
import zipfile
import tempfile
import platform
import subprocess
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import sys as _sys
import requests as _requests
import minecraft_launcher_lib as mll

# 抑制 Windows 上 subprocess 调用的控制台窗口闪烁
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

from .constants import (
    APP_NAME, APP_VERSION, MINECRAFT_DIR, CONFIG_FILE,
    URL_REWRITE_RULES, JVM_MANIFEST_URL_OFFICIAL,
)

try:
    import winreg
except ImportError:
    winreg = None

# 原始引用保存（用于 monkey-patch 恢复）
_original_download_file = None
_original_jvm_manifest_url = None
_original_get_requests_response_cache = None
_original_runtime_requests_get = None


def _rewrite_url(url):
    """将 Mojang 官方 URL 重写为 BMCLAPI 镜像 URL"""
    if not url:
        return url
    try:
        parsed = urlparse(url)
        host = parsed.netloc
        if host in URL_REWRITE_RULES:
            new_host = URL_REWRITE_RULES[host]
            # libraries.minecraft.net → bmclapi2.bangbang93.com/libraries
            # 此时路径需要合并
            new_parsed = urlparse(f"https://{new_host}")
            path = new_parsed.path.rstrip("/") + "/" + parsed.path.lstrip("/")
            return urlunparse((
                "https",
                new_parsed.netloc,
                path.rstrip("/"),
                parsed.params,
                parsed.query,
                parsed.fragment,
            ))
    except Exception:
        pass
    return url


def apply_mirror_patch():
    """激活镜像下载：monkey-patch minecraft-launcher-lib 的下载函数和 JVM 清单 URL"""
    global _original_download_file, _original_jvm_manifest_url
    global _original_get_requests_response_cache, _original_runtime_requests_get

    # 保存原始引用（仅首次）
    if _original_download_file is None:
        _original_download_file = mll._helper.download_file
    if _original_jvm_manifest_url is None:
        _original_jvm_manifest_url = mll.runtime._JVM_MANIFEST_URL
    if _original_get_requests_response_cache is None:
        _original_get_requests_response_cache = mll._helper.get_requests_response_cache
    if _original_runtime_requests_get is None:
        _original_runtime_requests_get = mll.runtime.requests.get

    # 包装 download_file，在下载前重写 URL
    def _patched_download_file(url, path, callback=None, sha1=None,
                               lzma_compressed=False, session=None,
                               minecraft_directory=None):
        return _original_download_file(
            _rewrite_url(url), path,
            callback=callback or {},
            sha1=sha1,
            lzma_compressed=lzma_compressed,
            session=session,
            minecraft_directory=minecraft_directory,
        )

    mll._helper.download_file = _patched_download_file
    mll.install.download_file = _patched_download_file
    mll.runtime.download_file = _patched_download_file

    # 重写 JVM 清单 URL
    mll.runtime._JVM_MANIFEST_URL = _rewrite_url(JVM_MANIFEST_URL_OFFICIAL)

    # 包装 get_requests_response_cache 以重写版本清单 URL
    def _patched_cache(url):
        return _original_get_requests_response_cache(_rewrite_url(url))

    mll._helper.get_requests_response_cache = _patched_cache

    # 同时包装 runtime 模块中的 requests.get 调用（JVM 子清单请求）
    def _patched_requests_get(url, **kwargs):
        return _original_runtime_requests_get(_rewrite_url(url), **kwargs)

    mll.runtime.requests.get = _patched_requests_get


def restore_mirror_patch():
    """恢复为官方源"""
    global _original_download_file, _original_jvm_manifest_url
    global _original_get_requests_response_cache, _original_runtime_requests_get
    if _original_download_file is not None:
        mll._helper.download_file = _original_download_file
        mll.install.download_file = _original_download_file
        mll.runtime.download_file = _original_download_file
    if _original_jvm_manifest_url is not None:
        mll.runtime._JVM_MANIFEST_URL = _original_jvm_manifest_url
    if _original_get_requests_response_cache is not None:
        mll._helper.get_requests_response_cache = _original_get_requests_response_cache
    if _original_runtime_requests_get is not None:
        mll.runtime.requests.get = _original_runtime_requests_get


class LauncherBackend:
    """Minecraft 后端管理：版本安装 / 启动命令生成 / Java 查找 / 系统内存"""

    def __init__(self):
        self.minecraft_dir = str(MINECRAFT_DIR)
        self._mirror_active = False
        self._installed_ids_cache = None

    def set_minecraft_dir(self, path):
        path = str(path)
        if path != self.minecraft_dir:
            self._installed_ids_cache = None
        self.minecraft_dir = path

    # ---- 镜像管理 ----
    def set_download_source(self, source):
        """设置下载源: 'official' 或 'bmclapi'"""
        if source == "bmclapi":
            if not self._mirror_active:
                apply_mirror_patch()
                self._mirror_active = True
        else:
            if self._mirror_active:
                restore_mirror_patch()
                self._mirror_active = False

    @staticmethod
    def get_jvm_manifest_url():
        """返回当前 JVM 清单 URL（受镜像设置影响）"""
        return mll.runtime._JVM_MANIFEST_URL

    # ---- 版本列表 ----
    def get_versions(self):
        releases = [v for v in mll.utils.get_version_list() if v["type"] == "release"]
        return releases

    def is_installed(self, version_id):
        if self._installed_ids_cache is None:
            self._installed_ids_cache = frozenset(
                mll.utils.get_installed_versions(self.minecraft_dir)
            )
        if version_id not in self._installed_ids_cache:
            return False
        jar = os.path.join(self.minecraft_dir, "versions", version_id, f"{version_id}.jar")
        return os.path.isfile(jar)

    def install(self, version_id, callback):
        mll.install.install_minecraft_version(version_id, self.minecraft_dir, callback=callback)
        self._installed_ids_cache = None

    # ---- 启动命令 ----
    def get_launch_command(self, version_id, username, ram_gb, java_path):
        options = {
            "username": username,
            "uuid": str(uuid.uuid4()),
            "token": "0",
            "executablePath": java_path,
            "jvmArguments": [f"-Xmx{ram_gb}G"],
            "launcherName": APP_NAME,
            "launcherVersion": APP_VERSION,
        }
        return mll.command.get_minecraft_command(version_id, self.minecraft_dir, options)

    # ---- JRE 运行时 ----
    def get_available_jre_runtimes(self):
        try:
            return mll.runtime.get_jvm_runtimes()
        except Exception:
            return []

    def install_jre(self, runtime, callback=None):
        mll.runtime.install_jvm_runtime(runtime, self.minecraft_dir, callback=callback)

    def get_installed_jre_path(self, runtime_name):
        exe = "javaw.exe" if platform.system() == "Windows" else "java"
        base = Path(self.minecraft_dir) / "runtime" / runtime_name
        # 搜索所有 bin/javaw.exe 或 bin/java
        for candidate in base.rglob(exe):
            if candidate.parent.name == "bin":
                return str(candidate)
        for candidate in base.rglob("java"):
            if candidate.parent.name == "bin" and candidate.is_file():
                return str(candidate)
        return None

    # ---- Java 下载 (Temurin JDK / 多镜像高速下载) ----
    ADOPTIUM_API = "https://api.adoptium.net/v3/assets/latest/{major}/hotspot"

    # 国内高速镜像站（多个备用，按优先级排列）
    # {major} {minor} {arch} {os} {filename}
    JAVA_MIRRORS = [
        # 注意: TUNA 的实际路径不含 hotspot/eclipse 两层
        ("清华 TUNA 镜像",     "https://mirrors.tuna.tsinghua.edu.cn/Adoptium/{major}/jdk/{arch}/{os}/{filename}"),
    ]

    def auto_install_java(self, mc_version, callback=None):
        """下载适配 MC 版本的 Temurin JDK，返回 (java_path, None) 或 (None, error)"""
        min_ver = self.get_min_java_for_mc(mc_version)
        return self._download_temurin_jdk(min_ver, callback)

    def download_java_zip(self, mc_version, callback=None):
        """
        下载 Java 安装包到桌面（Windows 下为 .msi 安装程序，直接双击即安装）。
        返回 (installer_path, None) 或 (None, error)。
        """
        min_ver = self.get_min_java_for_mc(mc_version)
        if callback is None:
            callback = {}
        cb_status = callback.get("setStatus", lambda s: None)
        cb_progress = callback.get("setProgress", lambda p: None)
        cb_max = callback.get("setMax", lambda m: None)

        # 1. 获取 CPU 架构
        sysname = platform.system()
        if sysname == "Windows":
            os_key = "windows"
        elif sysname == "Darwin":
            os_key = "mac"
        else:
            os_key = "linux"
        machine = (platform.machine() or "").lower()
        if machine in ("arm64", "aarch64"):
            arch = "aarch64"
        elif platform.architecture()[0] == "64bit":
            arch = "x64"
        else:
            arch = "x32"

        # Windows 下优先用 .msi 安装包（双击即安装），没有则退回到 .zip
        is_windows = (sysname == "Windows")

        cb_status(f"正在查询 Java {min_ver} 最新版本...")

        # 2. 查询 Adoptium API 获取 .zip 包信息，然后转成 .msi 文件名
        pkg_name = None
        official_url = None
        try:
            resp = _requests.get(
                self.ADOPTIUM_API.format(major=min_ver),
                params={"architecture": arch, "image_type": "jdk", "os": os_key},
                headers={"User-Agent": "MCL-Launcher/2.0"},
                timeout=20,
            )
            if resp.status_code == 200:
                pkg_name, official_url = self._pick_temurin_zip_from_adoptium_payload(resp.json())
        except Exception:
            pass

        if not pkg_name and not official_url:
            return None, f"无法查询 Java {min_ver} 下载信息（网络异常或本机架构 {arch} 无可用包）"

        # 3. 构建下载 URL 列表
        # Windows: 优先 .msi，如果镜像没有 .msi 则退回 .zip
        # 非 Windows: 只用 .zip
        urls = []
        if pkg_name:
            zip_filename = pkg_name
            msi_filename = re.sub(r'\.zip$', '.msi', zip_filename) if is_windows else None
            for src_label, tpl in self.JAVA_MIRRORS:
                if is_windows and msi_filename:
                    # Windows 先尝试 .msi
                    msi_url = tpl.format(
                        major=min_ver, arch=arch, os=os_key, filename=msi_filename
                    )
                    urls.append((f"{src_label} (.msi)", msi_url, msi_filename))
                # 始终保留 .zip 作为兜底
                zip_url = tpl.format(
                    major=min_ver, arch=arch, os=os_key, filename=zip_filename
                )
                urls.append((f"{src_label} (.zip)", zip_url, zip_filename))
        if official_url:
            urls.append(("GitHub Releases", official_url, pkg_name or f"jdk-{min_ver}.zip"))

        # 4. 下载到桌面 (Java_Downloads 文件夹)
        download_dir = Path(self._get_desktop_path()) / "Java_Downloads"
        download_dir.mkdir(parents=True, exist_ok=True)

        last_error = ""
        for src_name, url, local_name in urls:
            try:
                cb_status(f"正在从 {src_name} 下载 Java {min_ver}...")
                installer_path = download_dir / local_name
                self._download_file_with_progress(url, str(installer_path), cb_status, cb_progress, cb_max)

                if installer_path.stat().st_size < 500_000:
                    raise Exception("下载文件过小，可能为错误页或阻断页")

                cb_status("下载完成！")
                cb_max(0)
                cb_progress(0)
                return str(installer_path), None
            except Exception as e:
                last_error = f"{src_name}: {e}"
                continue

        return None, last_error or "所有下载源均已尝试失败"

    @staticmethod
    def _get_desktop_path():
        """获取系统桌面路径（兼容中文/非英文系统）"""
        try:
            import ctypes
            buf = ctypes.create_unicode_buffer(260)
            # CSIDL_DESKTOP = 0x0000
            ctypes.windll.shell32.SHGetFolderPathW(None, 0x0000, None, 0, buf)
            path = buf.value
            if path and Path(path).exists():
                return str(path)
        except Exception:
            pass
        # 备选: 常见桌面路径
        for p in [Path.home() / "Desktop", Path.home() / "OneDrive" / "Desktop",
                  Path(os.environ.get("USERPROFILE", "")) / "Desktop"]:
            if p.exists():
                return str(p)
        # 最后兜底
        return str(Path.home())

    @staticmethod
    def _adoptium_asset_entries(data):
        """Adoptium API 可能返回 list 或包了一层 dict，统一成可遍历条目。"""
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            bins = data.get("binaries")
            if isinstance(bins, list) and bins:
                return bins
            return [data]
        return []

    @staticmethod
    def _pick_temurin_zip_from_adoptium_payload(data):
        """从 API JSON 中取出 .zip 安装包文件名与直链（跳过 .msi 等）。"""
        for item in LauncherBackend._adoptium_asset_entries(data):
            if not isinstance(item, dict):
                continue
            binary = item.get("binary")
            if not isinstance(binary, dict):
                binary = item
            pkg = binary.get("package") if isinstance(binary.get("package"), dict) else {}
            name = (pkg.get("name") or "").strip()
            link = (pkg.get("link") or "").strip()
            if name.lower().endswith(".zip"):
                return name, link
        return None, None

    def _download_temurin_jdk(self, major_version, callback=None):
        """多镜像自动下载 Java — 从官方查版本号，再依次尝试镜像站下载"""
        if callback is None:
            callback = {}
        cb_status = callback.get("setStatus", lambda s: None)
        cb_progress = callback.get("setProgress", lambda p: None)
        cb_max = callback.get("setMax", lambda m: None)

        cb_status(f"正在查询 Java {major_version} 最新版本...")

        sysname = platform.system()
        if sysname == "Windows":
            os_key = "windows"
        elif sysname == "Darwin":
            os_key = "mac"
        else:
            os_key = "linux"
        machine = (platform.machine() or "").lower()
        if machine in ("arm64", "aarch64"):
            arch = "aarch64"
        elif platform.architecture()[0] == "64bit":
            arch = "x64"
        else:
            arch = "x32"

        # 步骤1: 查询 Adoptium API 获取最新文件名
        pkg_name = None
        official_url = None
        try:
            resp = _requests.get(
                self.ADOPTIUM_API.format(major=major_version),
                params={"architecture": arch, "image_type": "jdk", "os": os_key},
                headers={"User-Agent": "MCL-Launcher/2.0"},
                timeout=20,
            )
            if resp.status_code == 200:
                pkg_name, official_url = self._pick_temurin_zip_from_adoptium_payload(resp.json())
        except Exception:
            pass

        if not pkg_name and not official_url:
            return None, f"无法查询 Java {major_version} 下载信息（网络异常或本机架构 {arch} 无可用包）"

        # 步骤2: 构建多级下载 URL 列表（镜像优先，国内快）
        urls = []
        if pkg_name:
            for src_label, tpl in self.JAVA_MIRRORS:
                mirror_url = tpl.format(
                    major=major_version, arch=arch, os=os_key, filename=pkg_name
                )
                urls.append((src_label, mirror_url))
        if official_url:
            urls.append(("GitHub Releases", official_url))

        # 步骤3: 依次尝试下载 + 解压
        runtime_dir = Path(self.minecraft_dir) / "runtime" / f"jdk-{major_version}"
        runtime_dir.mkdir(parents=True, exist_ok=True)

        last_error = ""
        for src_name, url in urls:
            try:
                cb_status(f"正在从 {src_name} 下载 Java {major_version}...")
                zip_path = runtime_dir / f"jdk-{major_version}.zip"
                self._download_file_with_progress(url, str(zip_path), cb_status, cb_progress, cb_max)

                if zip_path.stat().st_size < 500_000:
                    raise Exception("下载文件过小，可能为错误页或阻断页")

                cb_status(f"正在解压 Java {major_version}...")
                cb_max(0)
                cb_progress(0)
                extract_dir = runtime_dir / "extracted"
                if extract_dir.exists():
                    shutil.rmtree(extract_dir)
                extract_dir.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(str(zip_path), "r") as zf:
                    zf.extractall(str(extract_dir))
                zip_path.unlink(missing_ok=True)

                java_exe = self._find_java_in_dir(extract_dir)
                if java_exe:
                    return java_exe, None
                last_error = f"{src_name}: 解压后未找到 Java 可执行文件"
                continue
            except Exception as e:
                last_error = f"{src_name}: {e}"
                continue

        return None, last_error or "所有下载源均已尝试失败"

    @staticmethod
    def _download_file_with_progress(url, dest, cb_status, cb_progress, cb_max):
        """流式下载文件，支持进度回调，处理 SSL 证书问题"""
        # 先用系统证书，失败则不验证
        for verify in (True, False):
            try:
                resp = _requests.get(url, stream=True, timeout=60, verify=verify,
                                    headers={"User-Agent": "MCL-Launcher/2.0"})
                if resp.status_code != 200:
                    if verify:
                        continue
                    raise Exception(f"HTTP {resp.status_code}")
                total = int(resp.headers.get("content-length", 0))
                cb_max(total if total > 0 else 200 * 1024 * 1024)
                downloaded = 0
                with open(dest, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total > 0:
                                cb_progress(downloaded)
                            else:
                                cb_progress(min(downloaded, 200 * 1024 * 1024))
                return
            except Exception:
                if not verify:
                    raise
                continue

    @staticmethod
    def _find_java_in_dir(base_dir):
        """在解压目录中递归查找 JDK。Windows 优先 java.exe，便于 subprocess -version 检测版本。"""
        is_win = platform.system() == "Windows"
        for root, dirs, files in os.walk(str(base_dir)):
            if is_win:
                if "java.exe" in files:
                    return os.path.join(root, "java.exe")
                if "javaw.exe" in files:
                    return os.path.join(root, "javaw.exe")
            else:
                if "java" in files:
                    java_path = os.path.join(root, "java")
                    if os.access(java_path, os.X_OK):
                        return java_path
        return None

    # ---- Java 版本解析 ----
    @staticmethod
    def _parse_java_version(java_path):
        try:
            result = subprocess.run(
                [java_path, "-version"],
                capture_output=True, text=True, timeout=5,
                creationflags=_NO_WINDOW,
            )
            output = (result.stderr or "") + (result.stdout or "")
            for line in output.splitlines():
                if "version" in line:
                    m = re.search(r'version\s+"?(\d+(?:\.\d+)?)', line)
                    if m:
                        ver = m.group(1)
                        parts = ver.split(".")
                        major = int(parts[1]) if parts[0] == "1" else int(parts[0])
                        return major, line.strip()
        except Exception:
            pass
        return 0, ""

    @staticmethod
    def _parse_java_version_from_name(name):
        try:
            m = re.search(r'(\d+)', str(name))
            if m:
                v = int(m.group(1))
                # 兼容 "jdk-8u202" / "1.8.0_202" 这类命名
                if v == 1:
                    m2 = re.search(r'1\.(\d+)', str(name))
                    if m2:
                        return int(m2.group(1))
                return v
        except Exception:
            pass
        return 0

    @staticmethod
    def _is_valid_java(java_path):
        """快速验证 Java 是否可执行且版本可解析"""
        ver, _ = LauncherBackend._parse_java_version(java_path)
        return ver > 0

    # ---- Java 路径持久化 ----
    @staticmethod
    def load_java_preferences():
        """从配置加载已保存的 Java 路径映射 {mc_version: java_path}"""
        try:
            if CONFIG_FILE.is_file():
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f).get("java_paths", {})
        except Exception:
            pass
        return {}

    @staticmethod
    def save_java_preference(mc_version, java_path):
        """保存某 MC 版本对应的 Java 路径"""
        try:
            config = {}
            if CONFIG_FILE.is_file():
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    try:
                        config = json.load(f)
                    except Exception:
                        config = {}
            java_paths = config.get("java_paths", {})
            java_paths[mc_version] = java_path
            config["java_paths"] = java_paths
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ---- Java 全面扫描 ----
    @staticmethod
    def find_all_java():
        is_win = platform.system() == "Windows"
        is_mac = platform.system() == "Darwin"
        exe_name = "javaw.exe" if is_win else "java"

        # 规范化路径：解析符号链接 + 大小写统一，用于去重
        def _norm(p):
            try:
                return str(Path(p).resolve())
            except Exception:
                return str(p)

        found = {}  # norm_path -> (real_path, ver, source_label)

        def _add(path, source):
            path = str(path)
            if not os.path.isfile(path):
                return
            key = _norm(path)
            if key in found:
                return
            ver, _ = LauncherBackend._parse_java_version(path)
            found[key] = (path, ver, source)

        # 1. minecraft-launcher-lib 自动检测
        try:
            auto = mll.utils.get_java_executable()
            if auto:
                _add(auto, "mll")
        except Exception:
            pass

        # 2. JAVA_HOME
        java_home = os.environ.get("JAVA_HOME", "")
        if java_home:
            _add(Path(java_home) / "bin" / exe_name, "JAVA_HOME")

        # 3. PATH（where/which 找到的所有条目）
        try:
            cmd = ["where", "java", "javaw"] if is_win else ["which", "-a", "java"]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=5,
                              creationflags=_NO_WINDOW)
            for line in r.stdout.strip().splitlines():
                line = line.strip()
                if line:
                    _add(line, "PATH")
        except Exception:
            pass

        # 4. Windows 注册表（含 WOW6432Node 镜像）
        if is_win and winreg:
            reg_roots = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\JavaSoft\Java Runtime Environment"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\JavaSoft\Java Development Kit"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\JavaSoft\JDK"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\JavaSoft\JRE"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Eclipse Adoptium\JDK"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Eclipse Adoptium\JRE"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Eclipse Foundation\JDK"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Eclipse Temurin\JDK"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\JDK"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Azul Systems\Zulu"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Amazon Corretto\JDK"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\BellSoft\Liberica JDK"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Dragonwell\JDK"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Alibaba Dragonwell\JDK"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Huawei\bisheng"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\JavaSoft\Java Runtime Environment"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\JavaSoft\Java Development Kit"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\JavaSoft\JDK"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Eclipse Adoptium\JDK"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Eclipse Temurin\JDK"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\JDK"),
            ]

            def _probe_reg_key(key):
                for val_name in ("JavaHome", "Path", "InstallDir"):
                    try:
                        home, _ = winreg.QueryValueEx(key, val_name)
                        if home:
                            _add(Path(home) / "bin" / exe_name, "Registry")
                            _add(Path(home) / "bin" / "java.exe", "Registry")
                    except Exception:
                        pass

            for root_key, sub_path in reg_roots:
                try:
                    key = winreg.OpenKey(root_key, sub_path,
                                        access=winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
                    _probe_reg_key(key)
                    # 枚举子版本键（如 "21.0.3"）
                    try:
                        for i in range(winreg.QueryInfoKey(key)[0]):
                            try:
                                sub_key = winreg.OpenKey(key, winreg.EnumKey(key, i))
                                _probe_reg_key(sub_key)
                                winreg.CloseKey(sub_key)
                            except Exception:
                                pass
                    except Exception:
                        pass
                    winreg.CloseKey(key)
                except Exception:
                    pass

        # 5. macOS /usr/libexec/java_home -V
        if is_mac:
            try:
                r = subprocess.run(["/usr/libexec/java_home", "-V"],
                                   capture_output=True, text=True, timeout=10)
                for line in r.stderr.splitlines():
                    m = re.search(r'(/[^\s"]+\.jdk[^\s"]*)', line)
                    if m:
                        base = Path(m.group(1))
                        for candidate in [
                            base / "Contents" / "Home" / "bin" / exe_name,
                            base / "bin" / exe_name,
                        ]:
                            _add(candidate, "macOS")
            except Exception:
                pass

        # 6. 常见安装目录扫描（深度限制 4 层，避免全盘扫描）
        if is_win:
            search_roots = [
                Path(os.environ.get("ProgramFiles", "C:/Program Files")),
                Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")),
                Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")),
            ]
            vendor_dirs = [
                "Java", "Eclipse Adoptium", "Eclipse Temurin", "AdoptOpenJDK",
                "Microsoft", "Zulu", "GraalVM", "Amazon Corretto", "Semeru",
                "BellSoft", "SapMachine", "Oracle", "Dragonwell", "Alibaba",
                "bisheng",
            ]
            for root in search_roots:
                for vendor in vendor_dirs:
                    vendor_path = root / vendor
                    if not vendor_path.exists():
                        continue
                    # 只扫描 vendor/*/bin/java*.exe，不递归全部
                    for jdk_dir in vendor_path.iterdir():
                        if not jdk_dir.is_dir():
                            continue
                        for exe_candidate in [
                            jdk_dir / "bin" / exe_name,
                            jdk_dir / "bin" / "java.exe",
                        ]:
                            _add(exe_candidate, vendor)
        else:
            unix_roots = [
                Path("/usr/lib/jvm"),
                Path("/usr/local/lib/jvm"),
                Path("/Library/Java/JavaVirtualMachines"),
                Path.home() / ".sdkman/candidates/java",
                Path.home() / ".jabba/jdk",
            ]
            for base in unix_roots:
                if not base.exists():
                    continue
                for jdk_dir in base.iterdir():
                    if not jdk_dir.is_dir():
                        continue
                    for candidate in [
                        jdk_dir / "bin" / exe_name,
                        jdk_dir / "Contents" / "Home" / "bin" / exe_name,
                    ]:
                        _add(candidate, "System")

        # 7. 组装结果，过滤无效 Java 并按版本降序
        result = []
        for key, (path, ver, source) in found.items():
            if ver <= 0:
                continue
            label = f"Java {ver} ({source}) | {path}"
            result.append({"path": path, "version": ver, "label": label})
        result.sort(key=lambda x: x["version"], reverse=True)
        return result

    # ---- Minecraft 版本 → 最低 Java 版本 ----
    @staticmethod
    def get_min_java_for_mc(mc_version):
        """Minecraft 版本 → 最低 Java 版本 精确映射"""
        try:
            parts = mc_version.split(".")
            if parts[0] == "1":
                major, minor = int(parts[1]), int(parts[2]) if len(parts) >= 3 else 0
                # 1.20.5+ → Java 21 (Mojang 从 24w14a 起强制要求)
                if major == 20 and minor >= 5:
                    return 21
                if major >= 21:
                    return 21
                # 1.18+ → Java 17
                if major >= 18:
                    return 17
                # 1.17 → Java 16
                if major >= 17:
                    return 16
                # ≤1.16.5 → Java 8
                return 8
            else:
                # 新版命名规则 (如 26.1) → 尝试读取 version.json
                return LauncherBackend._detect_java_from_jvm_args(mc_version)
        except (ValueError, IndexError):
            return 8

    @staticmethod
    def _detect_java_from_jvm_args(mc_version):
        try:
            vdir = os.path.join(str(MINECRAFT_DIR), "versions", mc_version, f"{mc_version}.json")
            if os.path.isfile(vdir):
                with open(vdir, "r", encoding="utf-8") as f:
                    data = json.load(f)
                args = data.get("arguments", {}).get("jvm", [])
                jvm_text = " ".join(str(a) for a in args if isinstance(a, str))
                if "--enable-native-access" in jvm_text:
                    return 22
                if "panama" in jvm_text.lower() or "foreign" in jvm_text.lower():
                    return 22
        except Exception:
            pass
        try:
            first = int(mc_version.split(".")[0])
            if first >= 26:
                return 25
            return 21
        except (ValueError, IndexError):
            return 21

    @staticmethod
    def pick_best_java(java_list, mc_version):
        if not java_list:
            return None
        min_ver = LauncherBackend.get_min_java_for_mc(mc_version)
        compatible = [j for j in java_list if j["version"] >= min_ver]
        if compatible:
            compatible.sort(key=lambda x: x["version"])
            return compatible[0]
        return java_list[0]

    # ---- 系统内存检测 ----
    @staticmethod
    def get_system_ram_gb():
        try:
            import ctypes
            if platform.system() == "Windows":
                kernel32 = ctypes.windll.kernel32

                class MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [
                        ("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                    ]

                ms = MEMORYSTATUSEX()
                ms.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
                kernel32.GlobalMemoryStatusEx(ctypes.byref(ms))
                return ms.ullTotalPhys / (1024 ** 3)
            else:
                try:
                    with open("/proc/meminfo", "r") as f:
                        for line in f:
                            if line.startswith("MemTotal:"):
                                return int(line.split()[1]) / (1024 ** 2)
                except Exception:
                    pass
                try:
                    result = subprocess.run(["sysctl", "-n", "hw.memsize"],
                                            capture_output=True, text=True, timeout=5)
                    return int(result.stdout.strip()) / (1024 ** 3)
                except Exception:
                    pass
        except Exception:
            pass
        return 0

    @staticmethod
    def get_recommended_ram(system_ram_gb):
        if system_ram_gb <= 0:
            return 4
        is_64bit = platform.architecture()[0] == "64bit"
        max_alloc = 8 if is_64bit else 4
        recommended = system_ram_gb / 4
        return max(1, min(recommended, max_alloc))
