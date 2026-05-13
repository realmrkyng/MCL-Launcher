# -*- coding: utf-8 -*-
"""
MCL Launcher — 模组加载器管理
兼容性规则 + 版本查找 + 安装调度
"""
import os
import threading
from pathlib import Path

import minecraft_launcher_lib as mll

from .modrinth import ModrinthAPI

# ── 加载器定义 ──
#            key        显示名    有 mll 支持  Modrinth loader 标签  可共存组
LOADER_DEFS = {
    "forge":     ("Forge",      True,  "forge",     "a"),
    "neoforge":  ("NeoForge",   False, "neoforge",  "b"),
    "fabric":    ("Fabric",     True,  "fabric",    "c"),
    "optifine":  ("OptiFine",   False, "optifine",  "d"),
}

# 同一组内的加载器互斥 (不能同时安装)
# A 组: Forge / NeoForge (都是 Forge 生态)
# B 组: Fabric
# C 组: OptiFine (可与 Fabric 或 Forge 共存，但需要额外模组)
EXCLUSIVE_GROUPS = {
    "forge":    "forge_ecosystem",
    "neoforge": "forge_ecosystem",
    "fabric":   "fabric_ecosystem",
    "optifine": "optifine",
}

# OptiFine 兼容性说明
# OptiFine + Forge: 部分兼容 (可能崩溃)
# OptiFine + Fabric: 需要 OptiFabric 模组
# OptiFine 独立: 完全兼容 (直接安装为版本)


class ModLoaderManager:
    """管理模组加载器的版本查询、兼容性检查与安装"""

    @staticmethod
    def get_loader_info(loader_key):
        """返回加载器的显示名和元数据"""
        if loader_key in LOADER_DEFS:
            name, mll_sup, mr_loader, _ = LOADER_DEFS[loader_key]
            return {
                "key": loader_key,
                "name": name,
                "has_mll_support": mll_sup,
                "modrinth_loader": mr_loader,
                "exclusive_group": EXCLUSIVE_GROUPS.get(loader_key, loader_key),
            }
        return None

    @staticmethod
    def get_available_loaders(mc_version):
        """返回给定 MC 版本可用的加载器列表"""
        available = []

        # Forge — 通过 mll 查询
        try:
            forge_ver = mll.forge.find_forge_version(mc_version)
            if forge_ver:
                available.append({
                    "key": "forge",
                    "name": "Forge",
                    "version": forge_ver,
                    "recommended": True,
                    "group": EXCLUSIVE_GROUPS["forge"],
                })
        except Exception:
            pass

        # Fabric — 通过 mll 查询
        try:
            if mll.fabric.is_minecraft_version_supported(mc_version):
                available.append({
                    "key": "fabric",
                    "name": "Fabric",
                    "version": mll.fabric.get_latest_loader_version(),
                    "recommended": True,
                    "group": EXCLUSIVE_GROUPS["fabric"],
                })
        except Exception:
            pass

        # NeoForge — Maven 源在国内被屏蔽
        # 暂时不显示 NeoForge，引导用户使用 Forge 替代

        # OptiFine — 通过 optifine.net 检查可用性
        try:
            import requests as _req
            r = _req.get("https://optifine.net/downloads", timeout=10,
                         headers={"User-Agent": "MCL-Launcher/2.0"})
            if r.status_code == 200 and mc_version in r.text:
                available.append({
                    "key": "optifine",
                    "name": "OptiFine",
                    "version": None,
                    "recommended": False,
                    "group": EXCLUSIVE_GROUPS["optifine"],
                })
        except Exception:
            pass

        return available

    @staticmethod
    def check_compatibility(selected_loaders):
        """
        检查所选的加载器组合是否兼容。
        返回 (is_compatible, warning_message) 或 (True, "")
        """
        groups = set()
        has_optifine = False

        for key in selected_loaders:
            if key not in EXCLUSIVE_GROUPS:
                continue
            group = EXCLUSIVE_GROUPS[key]
            if group == "optifine":
                has_optifine = True
                continue
            if group in groups:
                return False, f"同生态加载器冲突: {key}"
            groups.add(group)

        if has_optifine and "forge_ecosystem" in groups:
            return True, "OptiFine + Forge/NeoForge 可能存在兼容性问题，建议使用独立的 OptiFine 版本"
        if has_optifine and "fabric_ecosystem" in groups:
            return True, "OptiFine + Fabric 需要额外安装 OptiFabric 模组"

        return True, ""

    # ── 安装 ──
    @staticmethod
    def install_loader(loader_key, mc_version, mc_dir,
                       callback=None, java_path=None):
        """
        安装模组加载器。根据 loader_key 调度到具体安装方法。
        回调: callback dict with setStatus / setProgress / setMax
        """
        if callback is None:
            callback = {}

        if loader_key == "forge":
            return ModLoaderManager._install_forge(mc_version, mc_dir, callback, java_path)
        elif loader_key == "fabric":
            return ModLoaderManager._install_fabric(mc_version, mc_dir, callback, java_path)
        elif loader_key == "neoforge":
            return False, "NeoForge 下载源在国内不可达，请使用 Forge 替代"
        elif loader_key == "optifine":
            return ModLoaderManager._install_optifine(mc_version, mc_dir, callback)
        else:
            return False, f"Unsupported loader: {loader_key}"

    @staticmethod
    def _install_forge(mc_version, mc_dir, callback, java_path):
        """通过 mll 安装 Forge（含原版 MC）"""
        cb_status = callback.get("setStatus", lambda s: None)
        cb_progress = callback.get("setProgress", lambda p: None)
        cb_max = callback.get("setMax", lambda m: None)

        try:
            forge_version = mll.forge.find_forge_version(mc_version)
            if not forge_version:
                return False, f"未找到适用于 MC {mc_version} 的 Forge 版本"

            if not mll.forge.supports_automatic_install(forge_version):
                return False, "此 Forge 版本不支持自动安装，请手动安装"

            cb_status(f"正在安装 Forge {forge_version}...")
            cb_max(100)
            cb_progress(0)

            mll.forge.install_forge_version(
                forge_version, str(mc_dir),
                callback=callback,
                java=java_path,
            )
            return True, None
        except Exception as e:
            return False, str(e)

    @staticmethod
    def _install_fabric(mc_version, mc_dir, callback, java_path):
        """通过 mll 安装 Fabric（需已有原版 MC）"""
        cb_status = callback.get("setStatus", lambda s: None)

        try:
            if not mll.fabric.is_minecraft_version_supported(mc_version):
                return False, f"Fabric 不支持 Minecraft {mc_version}"

            cb_status(f"正在安装 Fabric Loader...")
            mll.fabric.install_fabric(
                mc_version, str(mc_dir),
                callback=callback,
                java=java_path,
            )
            return True, None
        except Exception as e:
            return False, str(e)

    @staticmethod
    def _install_optifine(mc_version, mc_dir, callback):
        """从 optifine.net 下载对应 MC 版本的 OptiFine JAR"""
        import re as _re
        import requests as _req
        from pathlib import Path

        cb_status = callback.get("setStatus", lambda s: None)
        cb_progress = callback.get("setProgress", lambda p: None)
        cb_max = callback.get("setMax", lambda m: None)

        try:
            cb_status(f"正在查找 OptiFine {mc_version}...")
            # 获取下载页面
            r = _req.get("https://optifine.net/downloads", timeout=10,
                         headers={"User-Agent": "MCL-Launcher/2.0"})
            if r.status_code != 200:
                return False, "无法访问 OptiFine 下载页面"

            # 查找对应 MC 版本的下载链接
            # 页面格式: <a href="/adloadx?f=OptiFine_{version}_HD_U_X.jar">
            pattern = _re.escape(mc_version) + r"[\w._-]*\.jar"
            match = _re.search(r'href="([^"]*' + pattern + r')"', r.text)
            if not match:
                return False, f"未找到 OptiFine {mc_version} 版本"

            dl_path = match.group(1)
            if not dl_path.startswith("http"):
                dl_url = f"https://optifine.net{dl_path}"
            else:
                dl_url = dl_path

            jar_name = dl_url.split("?f=")[-1] if "?f=" in dl_url else dl_url.split("/")[-1]

            cb_status(f"正在下载 OptiFine {jar_name}...")
            # 下载 JAR
            r2 = _req.get(dl_url, stream=True, timeout=60,
                         headers={"User-Agent": "MCL-Launcher/2.0"},
                         allow_redirects=True)
            if r2.status_code != 200:
                return False, f"下载 OptiFine 失败: HTTP {r2.status_code}"

            total = int(r2.headers.get("content-length", 0))
            cb_max(total if total > 0 else 10 * 1024 * 1024)

            dest_dir = Path(mc_dir) / "mods"
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_path = dest_dir / jar_name

            downloaded = 0
            with open(str(dest_path), "wb") as f:
                for chunk in r2.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            cb_progress(downloaded)

            cb_status("OptiFine 安装完成")
            return True, None
        except Exception as e:
            return False, str(e)

    @staticmethod
    def _install_loader_via_modrinth(loader_key, mc_version, mc_dir, callback):
        """
        通过 Modrinth 下载并安装加载器 (NeoForge / OptiFine)。
        下载对应版本 JAR 到 versions/{mc_version}-{loader}/ 并创建版本 JSON。
        """
        cb_status = callback.get("setStatus", lambda s: None)
        cb_progress = callback.get("setProgress", lambda p: None)
        cb_max = callback.get("setMax", lambda m: None)

        loader_info = LOADER_DEFS.get(loader_key)
        if not loader_info:
            return False, f"Unknown loader: {loader_key}"
        loader_name, _, modrinth_loader, _ = loader_info

        # Modrinth 上的项目 slug
        slug_map = {
            "neoforge": "neoforge",
            "optifine": "optifine",
        }
        slug = slug_map.get(loader_key)
        if not slug:
            return False, f"No Modrinth slug for {loader_key}"

        try:
            cb_status(f"正在查找 {loader_name} 的 {mc_version} 版本...")
            filename, url, ver_num = ModrinthAPI.get_latest_download_info(
                slug, game_version=mc_version, loader=modrinth_loader
            )
            if not url:
                return False, f"Modrinth 上未找到 {loader_name} 的 MC {mc_version} 版本"

            cb_status(f"正在下载 {loader_name} {ver_num or ''}...")
            dest_dir = Path(mc_dir) / "mods"
            dest_dir.mkdir(parents=True, exist_ok=True)

            ModrinthAPI.download_file(url, dest_dir, filename=filename,
                                      callback=callback)
            cb_status(f"{loader_name} 安装完成")
            return True, None
        except Exception as e:
            return False, str(e)

    @staticmethod
    def get_forge_version_id(mc_version):
        """获取 Forge 安装后的版本 ID"""
        try:
            forge_ver = mll.forge.find_forge_version(mc_version)
            if forge_ver:
                return mll.forge.forge_to_installed_version(forge_ver)
        except Exception:
            pass
        return None

    @staticmethod
    def get_fabric_version_id(mc_version):
        """获取 Fabric 安装后的版本 ID"""
        try:
            loader = mll.fabric.get_latest_loader_version()
            return f"fabric-loader-{loader}-{mc_version}"
        except Exception:
            pass
        return f"fabric-loader-{mc_version}"

    @staticmethod
    def get_installed_loader_version_id(loader_key, mc_version):
        """获取安装后的完整版本 ID（用于启动命令）"""
        if loader_key == "forge":
            return ModLoaderManager.get_forge_version_id(mc_version)
        elif loader_key == "fabric":
            return ModLoaderManager.get_fabric_version_id(mc_version)
        elif loader_key in ("neoforge", "optifine"):
            # 通过 Modrinth 安装的加载器放在 mods 目录，
            # 版本 ID 仍然是原版
            return mc_version
        return mc_version
