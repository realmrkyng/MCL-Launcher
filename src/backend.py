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

import requests as _requests
import minecraft_launcher_lib as mll

from .constants import (
    APP_NAME, APP_VERSION, MINECRAFT_DIR, CONFIG_FILE,
    MIRROR_BASE_URL, URL_REWRITE_RULES, JVM_MANIFEST_URL_OFFICIAL,
)

try:
    import winreg
except ImportError:
    winreg = None

# 原始引用保存（用于 monkey-patch 恢复）
_original_download_file = None
_original_jvm_manifest_url = None


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

    # 保存原始引用（仅首次）
    if _original_download_file is None:
        _original_download_file = mll._helper.download_file
    if _original_jvm_manifest_url is None:
        _original_jvm_manifest_url = mll.runtime._JVM_MANIFEST_URL

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
    _original_cache = mll._helper.get_requests_response_cache

    def _patched_cache(url):
        return _original_cache(_rewrite_url(url))

    mll._helper.get_requests_response_cache = _patched_cache

    # 同时包装 runtime 模块中的 requests.get 调用（JVM 子清单请求）
    _original_requests_get = mll.runtime.requests.get

    def _patched_requests_get(url, **kwargs):
        return _original_requests_get(_rewrite_url(url), **kwargs)

    mll.runtime.requests.get = _patched_requests_get


def restore_mirror_patch():
    """恢复为官方源"""
    global _original_download_file, _original_jvm_manifest_url
    if _original_download_file is not None:
        mll._helper.download_file = _original_download_file
        mll.install.download_file = _original_download_file
        mll.runtime.download_file = _original_download_file
    if _original_jvm_manifest_url is not None:
        mll.runtime._JVM_MANIFEST_URL = _original_jvm_manifest_url


class LauncherBackend:
    """Minecraft 后端管理：版本安装 / 启动命令生成 / Java 查找 / 系统内存"""

    def __init__(self):
        self.minecraft_dir = str(MINECRAFT_DIR)
        self._mirror_active = False

    def set_minecraft_dir(self, path):
        self.minecraft_dir = str(path)

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
        if version_id not in mll.utils.get_installed_versions(self.minecraft_dir):
            return False
        jar = os.path.join(self.minecraft_dir, "versions", version_id, f"{version_id}.jar")
        return os.path.isfile(jar)

    def install(self, version_id, callback):
        mll.install.install_minecraft_version(version_id, self.minecraft_dir, callback=callback)

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

    # ---- Java 下载 (Temurin JDK) ----
    ADOPTIUM_API = "https://api.adoptium.net/v3/assets/latest/{major}/hotspot"
    # 备用镜像列表：清华 TUNA（主）、华为云
    FALLBACK_MIRRORS = [
        "https://mirrors.tuna.tsinghua.edu.cn/Adoptium/{major}/jdk/{arch}/{os}/hotspot/eclipse/{filename}",
    ]

    def auto_install_java(self, mc_version, callback=None):
        """下载适配 MC 版本的 Temurin JDK，返回 (java_path, None) 或 (None, error)"""
        min_ver = self.get_min_java_for_mc(mc_version)
        return self._download_temurin_jdk(min_ver, callback)

    def _download_temurin_jdk(self, major_version, callback=None):
        """从 Adoptium 官方源（优先）或镜像站下载 Temurin JDK"""
        if callback is None:
            callback = {}
        cb_status = callback.get("setStatus", lambda s: None)
        cb_progress = callback.get("setProgress", lambda p: None)
        cb_max = callback.get("setMax", lambda m: None)

        cb_status(f"查询 Java {major_version} 最新版本...")

        sysname = platform.system()
        if sysname == "Windows":
            os_key = "windows"
        elif sysname == "Darwin":
            os_key = "mac"
        else:
            os_key = "linux"
        arch = "x64" if platform.architecture()[0] == "64bit" else "x32"

        # 步骤1: 查询 Adoptium API
        pkg_name = None
        official_url = None
        try:
            resp = _requests.get(
                self.ADOPTIUM_API.format(major=major_version),
                params={"architecture": arch, "image_type": "jdk", "os": os_key},
                headers={"User-Agent": "MCL-Launcher/2.0"},
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                binary = (data or [{}])[0].get("binary", {})
                if binary:
                    pkg = binary.get("package", {})
                    pkg_name = pkg.get("name", "")
                    official_url = pkg.get("link", "")
        except Exception:
            pass

        if not official_url and not pkg_name:
            return None, f"无法查询 Java {major_version} 下载信息（网络异常）"

        # 步骤2: 构建下载 URL 列表
        urls = []
        if official_url:
            urls.append(("Adoptium 官方", official_url))
        if pkg_name:
            for mirror_tpl in self.FALLBACK_MIRRORS:
                mirror_url = mirror_tpl.format(
                    major=major_version, arch=arch, os=os_key, filename=pkg_name
                )
                urls.append(("镜像站", mirror_url))

        # 步骤3: 下载 + 解压
        runtime_dir = Path(self.minecraft_dir) / "runtime" / f"jdk-{major_version}"
        runtime_dir.mkdir(parents=True, exist_ok=True)

        last_error = ""
        for src_name, url in urls:
            try:
                cb_status(f"从 {src_name} 下载 Java {major_version}...")
                zip_path = runtime_dir / f"jdk-{major_version}.zip"
                self._download_file_with_progress(url, str(zip_path), cb_status, cb_progress, cb_max)

                cb_status(f"解压 Java {major_version}...")
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

        return None, last_error or "所有下载源均失败"

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
        """在解压目录中递归查找 javaw.exe 或 java"""
        exe_name = "javaw.exe" if platform.system() == "Windows" else "java"
        for root, dirs, files in os.walk(str(base_dir)):
            if exe_name in files:
                return os.path.join(root, exe_name)
            if "java" in files and platform.system() != "Windows":
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
                capture_output=True, text=True, timeout=5
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
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
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
        try:
            parts = mc_version.split(".")
            if parts[0] == "1":
                major = int(parts[1])
                if major >= 21:
                    return 21
                elif major >= 18:
                    return 17
                elif major >= 17:
                    return 16
                return 8
            else:
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
            parts = mc_version.split(".")
            first = int(parts[0])
            if first >= 26:
                return 22
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
