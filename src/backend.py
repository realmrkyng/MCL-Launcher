# -*- coding: utf-8 -*-
"""
MCL Launcher — 后端逻辑：版本管理、下载、启动命令、Java 检测、内存检测
"""
import os
import re
import json
import uuid
import platform
import subprocess
from pathlib import Path

import minecraft_launcher_lib as mll

from .constants import APP_NAME, APP_VERSION, MINECRAFT_DIR

try:
    import winreg
except ImportError:
    winreg = None


class LauncherBackend:
    """Minecraft 后端管理：版本安装 / 启动命令生成 / Java 查找 / 系统内存"""

    def __init__(self):
        self.minecraft_dir = str(MINECRAFT_DIR)

    def set_minecraft_dir(self, path):
        self.minecraft_dir = str(path)

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

    def auto_install_java(self, mc_version, callback=None):
        """根据 MC 版本自动下载对应 JRE，返回安装后的 java 路径，失败返回 None"""
        min_ver = self.get_min_java_for_mc(mc_version)
        # mll runtime 名称 → 对应 Java 主版本
        runtime_map = [
            ("java-runtime-delta",   21),
            ("java-runtime-gamma",   17),
            ("java-runtime-beta",    16),
            ("java-runtime-alpha",   16),
            ("jre-legacy",            8),
        ]
        runtime = next((r for r, v in runtime_map if v >= min_ver), "java-runtime-gamma")
        try:
            mll.runtime.install_jvm_runtime(runtime, self.minecraft_dir, callback=callback)
        except Exception as e:
            return None, str(e)
        path = self.get_installed_jre_path(runtime)
        return path, None

    # ---- Java 版本解析 ----
    @staticmethod
    def _parse_java_version(java_path):
        try:
            result = subprocess.run(
                [java_path, "-version"],
                capture_output=True, text=True, timeout=10
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
                return int(m.group(1))
        except Exception:
            pass
        return 0

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
                "BellSoft", "SapMachine", "Oracle",
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

        # 7. 组装结果，按版本降序
        result = []
        for key, (path, ver, source) in found.items():
            if ver:
                label = f"Java {ver} ({source}) | {path}"
            else:
                label = f"Java (unknown, {source}) | {path}"
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
