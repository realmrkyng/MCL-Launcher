# -*- coding: utf-8 -*-
"""
Modrinth API v2 客户端 — 搜索、浏览、下载 Mod / 光影 / 资源包
https://docs.modrinth.com/api/
"""
import json
import time
import threading
import requests as _requests
from pathlib import Path

API_BASE = "https://api.modrinth.com/v2"
USER_AGENT = "MCL-Launcher/1.2 (github.com/realmrkyng)"
REQUESTS_TIMEOUT = 20
_MIN_INTERVAL = 0.25


class ModrinthAPI:
    """封装 Modrinth API v2 的搜索 & 下载，内置线程安全速率限制"""

    _lock = threading.Lock()
    _last_request = 0.0

    # ── 通用请求 ──
    @classmethod
    def _get(cls, endpoint, params=None):
        cls._rate_limit()
        url = f"{API_BASE}{endpoint}"
        resp = _requests.get(url, params=params,
                             headers={"User-Agent": USER_AGENT},
                             timeout=REQUESTS_TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    @classmethod
    def _rate_limit(cls):
        with cls._lock:
            now = time.monotonic()
            wait = _MIN_INTERVAL - (now - cls._last_request)
            if wait > 0:
                time.sleep(wait)
            cls._last_request = time.monotonic()

    # ── 搜索 ──
    @classmethod
    def search(cls, query, facets=None, index="relevance",
               offset=0, limit=20):
        """
        通用搜索。
        facets 示例: [["project_type:mod"], ["categories:fabric"]]
        """
        params = {
            "query": query or "",
            "index": index,
            "offset": offset,
            "limit": limit,
        }
        if facets:
            params["facets"] = json.dumps(facets, separators=(",", ":"))
        data = cls._get("/search", params)
        return data.get("hits", []), data.get("total_hits", 0), data.get("offset", 0)

    @classmethod
    def search_mods(cls, query, loader=None, version=None, limit=20, offset=0):
        """搜索 Mod，可筛选加载器和游戏版本"""
        facets = [["project_type:mod"]]
        if loader:
            facets.append([f"categories:{cls.loader_facet(loader)}"])
        if version:
            facets.append([f"versions:{version}"])
        return cls.search(query, facets=facets, limit=limit, offset=offset)

    @classmethod
    def search_shaders(cls, query, version=None, limit=20, offset=0):
        """搜索光影包"""
        facets = [["project_type:shader"]]
        if version:
            facets.append([f"versions:{version}"])
        return cls.search(query, facets=facets, limit=limit, offset=offset)

    @classmethod
    def search_resourcepacks(cls, query, version=None, limit=20, offset=0):
        """搜索资源包"""
        facets = [["project_type:resourcepack"]]
        if version:
            facets.append([f"versions:{version}"])
        return cls.search(query, facets=facets, limit=limit, offset=offset)

    # ── 项目详情 ──
    @classmethod
    def get_project(cls, project_id):
        """获取项目详情（支持 slug 或 ID）"""
        return cls._get(f"/project/{project_id}")

    # ── 版本列表 ──
    @classmethod
    def get_versions(cls, project_id, loaders=None, game_versions=None):
        """获取项目的版本列表，可按 loader 和游戏版本筛选"""
        params = {}
        if loaders:
            params["loaders"] = json.dumps(loaders, separators=(",", ":"))
        if game_versions:
            params["game_versions"] = json.dumps(game_versions, separators=(",", ":"))
        return cls._get(f"/project/{project_id}/version", params)

    @classmethod
    def get_version(cls, version_id):
        """获取单个版本详情（含下载 URL 和文件信息）"""
        return cls._get(f"/version/{version_id}")

    # ── 获取最新下载 URL ──
    @classmethod
    def get_latest_download_info(cls, project_id, game_version=None, loader=None):
        """
        获取项目最新版本的下载信息。
        返回 (filename, url, version_number) 或 (None, None, None)
        """
        ldrs = [loader] if loader else None
        gv = [game_version] if game_version else None
        versions = cls.get_versions(project_id, loaders=ldrs, game_versions=gv)
        if not versions:
            return None, None, None

        v = versions[0]
        files = v.get("files", [])
        primary = next((f for f in files if f.get("primary")), None)
        if not primary and files:
            primary = files[0]
        if not primary:
            return None, None, None

        return primary.get("filename"), primary.get("url"), v.get("version_number")

    # ── 下载文件 ──
    @classmethod
    def download_file(cls, url, dest_dir, filename=None, callback=None):
        """
        下载文件到指定目录。
        callback: dict with setStatus(str), setProgress(int), setMax(int)
        返回完整文件路径，失败返回 None
        """
        cb_status = (callback or {}).get("setStatus", lambda s: None)
        cb_progress = (callback or {}).get("setProgress", lambda p: None)
        cb_max = (callback or {}).get("setMax", lambda m: None)

        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)

        resp = _requests.get(url, stream=True, timeout=REQUESTS_TIMEOUT,
                            headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()

        if not filename:
            cd = resp.headers.get("content-disposition", "")
            if "filename=" in cd:
                filename = cd.split("filename=")[-1].strip('" ')
            else:
                filename = url.split("/")[-1].split("?")[0]

        dest_path = dest_dir / filename
        total = int(resp.headers.get("content-length", 0))
        cb_max(total if total > 0 else 50 * 1024 * 1024)

        downloaded = 0
        try:
            with open(dest_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        cb_progress(downloaded)
            return str(dest_path)
        except Exception:
            try:
                dest_path.unlink(missing_ok=True)
            except Exception:
                pass
            raise

    @classmethod
    def get_popular_mods(cls, loader=None, version=None, limit=20):
        return cls.search_mods("", loader=loader, version=version, limit=limit)

    @classmethod
    def get_popular_shaders(cls, version=None, limit=20):
        return cls.search_shaders("", version=version, limit=limit)

    @classmethod
    def loader_facet(cls, loader):
        mapping = {
            "forge": "forge", "neoforge": "neoforge",
            "fabric": "fabric", "quilt": "quilt",
            "optifine": "optifine", "vanilla": "vanilla",
        }
        return mapping.get(loader.lower(), loader.lower())

    @classmethod
    def project_type_facet(cls, ptype):
        valid = {"mod", "modpack", "resourcepack", "shader", "datapack", "plugin"}
        return ptype if ptype in valid else "mod"
