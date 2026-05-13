# -*- coding: utf-8 -*-
"""
CurseForge Core API v1 客户端 — 搜索、浏览、下载 Mod / 光影 / 资源包
https://docs.curseforge.com/
"""
import time
import threading
import requests as _requests
from pathlib import Path

API_BASE = "https://api.curseforge.com/v1"
USER_AGENT = "MCL-Launcher/1.2 (github.com/realmrkyng)"
REQUESTS_TIMEOUT = 20
_MIN_INTERVAL = 0.3

# CurseForge 公开社区 API Key
# 如果失效，请前往 https://console.curseforge.com/ 申请替换
CF_API_KEY = "$2a$10$bL4bIL5pUWqfcO7KQtnMReakwtfHbNKh6v1uTpKlzhwoueEJQnPnm"


class CurseForgeAPI:
    """CurseForge Core API 客户端，内置速率限制"""

    _lock = threading.Lock()
    _last_request = 0.0

    GAME_ID = 432  # Minecraft
    CLASS_MOD = 6
    CLASS_SHADER = 12  # Resource Packs (光影通常在这里)

    # ── 通用请求 ──
    @classmethod
    def _get(cls, endpoint, params=None):
        cls._rate_limit()
        url = f"{API_BASE}{endpoint}"
        headers = {
            "User-Agent": USER_AGENT,
            "x-api-key": CF_API_KEY,
            "Accept": "application/json",
        }
        resp = _requests.get(url, params=params, headers=headers,
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

    # ── 搜索 Mod ──
    @classmethod
    def search_mods(cls, query, version=None, loader=None,
                    sort_field=2, limit=20, offset=0):
        """
        搜索 Mod。
        sort_field: 1=Featured, 2=Popularity, 3=LastUpdated, 4=Name, 5=Author, 6=TotalDownloads
        """
        params = {
            "gameId": cls.GAME_ID,
            "classId": cls.CLASS_MOD,
            "searchFilter": query or "",
            "sortField": sort_field,
            "sortOrder": "desc",
            "pageSize": limit,
            "index": offset,
        }
        if version:
            params["gameVersion"] = version
        if loader:
            params["modLoaderType"] = cls._loader_id(loader)

        resp = cls._get("/mods/search", params)
        mods = resp.get("data", [])
        pagination = resp.get("pagination", {})
        return mods, pagination.get("totalCount", len(mods)), offset

    @classmethod
    def search_shaders(cls, query, version=None, limit=20, offset=0):
        """搜索 Resource Packs / 光影"""
        params = {
            "gameId": cls.GAME_ID,
            "classId": cls.CLASS_SHADER,
            "searchFilter": query or "",
            "sortField": 2,
            "sortOrder": "desc",
            "pageSize": limit,
            "index": offset,
        }
        if version:
            params["gameVersion"] = version

        resp = cls._get("/mods/search", params)
        mods = resp.get("data", [])
        pagination = resp.get("pagination", {})
        return mods, pagination.get("totalCount", len(mods)), offset

    @classmethod
    def search_resourcepacks(cls, query, version=None, limit=20, offset=0):
        """搜索资源包"""
        return cls.search_shaders(query, version=version, limit=limit, offset=offset)

    # ── 项目详情 ──
    @classmethod
    def get_project(cls, mod_id):
        """获取 Mod 详情"""
        return cls._get(f"/mods/{mod_id}").get("data", {})

    # ── 文件列表 ──
    @classmethod
    def get_files(cls, mod_id, game_version=None, loader=None):
        """获取 Mod 的文件列表"""
        params = {}
        if game_version:
            params["gameVersion"] = game_version
        if loader is not None:
            params["modLoaderType"] = cls._loader_id(loader)
        return cls._get(f"/mods/{mod_id}/files", params).get("data", [])

    # ── 下载 URL ──
    @classmethod
    def get_download_url(cls, mod_id, file_id):
        """获取文件下载 URL"""
        resp = cls._get(f"/mods/{mod_id}/files/{file_id}/download-url")
        return resp.get("data", "")

    @classmethod
    def get_latest_download_info(cls, mod_id, game_version=None, loader=None):
        """
        获取最新文件的下载信息。
        返回 (filename, url) 或 (None, None)
        """
        files = cls.get_files(mod_id, game_version=game_version, loader=loader)
        if not files:
            return None, None

        # 取最新的 release
        latest = files[0]
        for f in files:
            if f.get("releaseType") == 1:  # 1 = Release
                latest = f
                break

        fid = latest.get("id")
        fname = latest.get("fileName") or latest.get("displayName", "")
        if not fid:
            return None, None

        try:
            url = cls.get_download_url(mod_id, fid)
            return fname, url
        except Exception:
            return None, None

    # ── 下载文件 ──
    @classmethod
    def download_file(cls, url, dest_dir, filename=None, callback=None):
        """下载文件到目录。callback: setStatus / setProgress / setMax"""
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

    # ── 辅助 ──
    @classmethod
    def _loader_id(cls, loader_name):
        """将 loader 名转为 CurseForge modLoaderType ID"""
        if not loader_name:
            return None
        mapping = {
            "forge": 1,
            "fabric": 4,
            "quilt": 5,
            "neoforge": 6,
        }
        return mapping.get(loader_name.lower())

    @classmethod
    def loader_facet(cls, loader):
        mapping = {
            "forge": "forge", "neoforge": "neoforge",
            "fabric": "fabric", "quilt": "quilt",
        }
        return mapping.get(loader.lower(), loader.lower())
