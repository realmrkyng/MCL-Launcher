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
        p = os.path.join(self.minecraft_dir, "runtime", runtime_name, "bin", exe)
        if os.path.isfile(p):
            return p
        p2 = os.path.join(self.minecraft_dir, "runtime", runtime_name, "bin", "java")
        if os.path.isfile(p2):
            return p2
        return None

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
        found = {}
        exe_name = "javaw.exe" if platform.system() == "Windows" else "java"
        is_win = platform.system() == "Windows"
        is_mac = platform.system() == "Darwin"

        # 1. minecraft-launcher-lib 自动检测
        auto = mll.utils.get_java_executable()
        if auto:
            ver, _ = LauncherBackend._parse_java_version(auto)
            found[auto] = (ver, f"Java {ver} | {auto}" if ver else f"Java (auto) | {auto}")

        # 2. JAVA_HOME 环境变量
        java_home = os.environ.get("JAVA_HOME", "")
        if java_home:
            p = Path(java_home) / "bin" / exe_name
            if p.exists():
                path = str(p)
                if path not in found:
                    ver, _ = LauncherBackend._parse_java_version(path)
                    found[path] = (ver, f"Java {ver} (JAVA_HOME) | {path}" if ver else f"Java (JAVA_HOME) | {path}")

        # 3. PATH 环境变量
        try:
            which = subprocess.run(["where" if is_win else "which", "java"],
                                   capture_output=True, text=True, timeout=5)
            for line in which.stdout.strip().split("\n"):
                line = line.strip()
                if line and line not in found:
                    ver, _ = LauncherBackend._parse_java_version(line)
                    found[line] = (ver, f"Java {ver} (PATH) | {line}" if ver else f"Java (PATH) | {line}")
        except Exception:
            pass

        # 4. macOS /usr/libexec/java_home
        if is_mac:
            try:
                result = subprocess.run(["/usr/libexec/java_home", "-V"],
                                       capture_output=True, text=True, timeout=10)
                for line in result.stderr.splitlines():
                    if line.strip():
                        m = re.search(r'([^\s]+)\s+".+"\s+"(.+)"', line)
                        if m and "jdk" in line.lower():
                            vm_path = m.group(1)
                            java_exe = os.path.join(vm_path, "Contents", "Home", "bin", exe_name)
                            if os.path.isfile(java_exe) and java_exe not in found:
                                ver, _ = LauncherBackend._parse_java_version(java_exe)
                                found[java_exe] = (ver, f"Java {ver} (macOS) | {java_exe}" if ver else f"Java (macOS) | {java_exe}")
            except Exception:
                pass

        # 5. Windows 注册表
        if is_win and winreg:
            reg_keys = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\JavaSoft\Java Runtime Environment"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\JavaSoft\Java Development Kit"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\JavaSoft\JDK"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Eclipse Adoptium\JDK"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Eclipse Foundation\JDK"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Eclipse Temurin\JDK"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\JDK"),
            ]
            for root_key, sub_path in reg_keys:
                try:
                    key = winreg.OpenKey(root_key, sub_path)
                    try:
                        java_home_reg, _ = winreg.QueryValueEx(key, "JavaHome")
                        if java_home_reg:
                            p = Path(java_home_reg) / "bin" / exe_name
                            if p.exists():
                                path = str(p)
                                if path not in found:
                                    ver, _ = LauncherBackend._parse_java_version(path)
                                    found[path] = (ver, f"Java {ver} (Registry) | {path}" if ver else f"Java (Registry) | {path}")
                    except Exception:
                        pass
                    try:
                        for i in range(winreg.QueryInfoKey(key)[0]):
                            sub_name = winreg.EnumKey(key, i)
                            try:
                                sub_key = winreg.OpenKey(key, sub_name)
                                java_home_reg, _ = winreg.QueryValueEx(sub_key, "JavaHome")
                                if java_home_reg:
                                    p = Path(java_home_reg) / "bin" / exe_name
                                    if p.exists():
                                        path = str(p)
                                        if path not in found:
                                            ver, _ = LauncherBackend._parse_java_version(path)
                                            found[path] = (ver, f"Java {ver} (Registry) | {path}" if ver else f"Java (Registry) | {path}")
                            except Exception:
                                pass
                    except Exception:
                        pass
                    try:
                        path_reg, _ = winreg.QueryValueEx(key, "Path")
                        if path_reg:
                            p = Path(path_reg) / "bin" / exe_name
                            if p.exists():
                                path = str(p)
                                if path not in found:
                                    ver, _ = LauncherBackend._parse_java_version(path)
                                    found[path] = (ver, f"Java {ver} (Registry) | {path}" if ver else f"Java (Registry) | {path}")
                    except Exception:
                        pass
                    winreg.CloseKey(key)
                except Exception:
                    pass

        # 6. 常见安装目录扫描
        if is_win:
            search_roots = [
                Path("C:/Program Files/Java"),
                Path("C:/Program Files (x86)/Java"),
                Path("C:/Program Files/Eclipse Adoptium"),
                Path("C:/Program Files/Eclipse Temurin"),
                Path("C:/Program Files/AdoptOpenJDK"),
                Path("C:/Program Files/Microsoft"),
                Path("C:/Program Files/Zulu"),
                Path("C:/Program Files/GraalVM"),
                Path("C:/Program Files/Amazon Corretto"),
                Path("C:/Program Files/Semeru"),
                Path("C:/Program Files/Common Files/Oracle/Java"),
            ]
            for root in search_roots:
                if root.exists():
                    for exe in root.rglob(exe_name):
                        path = str(exe)
                        if path not in found:
                            ver, _ = LauncherBackend._parse_java_version(path)
                            rel = Path(path).relative_to(root)
                            found[path] = (ver, f"Java {ver} ({rel.parts[0]}) | {path}" if ver else f"Java ({rel.parts[0]}) | {path}")

        if not is_win:
            for base in [Path("/usr/lib/jvm"), Path("/Library/Java/JavaVirtualMachines"),
                         Path.home() / ".sdkman/candidates/java"]:
                if base.exists():
                    for exe in base.rglob(exe_name):
                        path = str(exe)
                        if path not in found:
                            ver, _ = LauncherBackend._parse_java_version(path)
                            found[path] = (ver, f"Java {ver} | {path}" if ver else f"Java | {path}")

        result = []
        for path, (ver, label) in found.items():
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
