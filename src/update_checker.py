# -*- coding: utf-8 -*-
"""
MCL Launcher — GitHub 版本更新检查
"""
import threading

from .constants import UPDATE_URL, APP_VERSION


class UpdateChecker:
    """异步从 GitHub raw URL 拉取最新版本号，回调通知"""

    @staticmethod
    def check(callback):
        def task():
            try:
                import urllib.request
                req = urllib.request.Request(UPDATE_URL)
                req.add_header("User-Agent", "MCL-Launcher/1.0")
                with urllib.request.urlopen(req, timeout=5) as resp:
                    remote = resp.read().decode("utf-8").strip()
                if remote and remote != APP_VERSION:
                    callback(True, remote)
                else:
                    callback(False, "")
            except Exception:
                callback(False, "")
        threading.Thread(target=task, daemon=True).start()
