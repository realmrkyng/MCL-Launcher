# -*- coding: utf-8 -*-
"""
MCL Launcher — 主 GUI 类：窗口管理、页面切换、启动/下载流程、配置持久化
"""
import os
import re
import json
import time
import webbrowser
import threading
import subprocess
import customtkinter as ctk
from tkinter import messagebox

from ..constants import APP_NAME, APP_VERSION, DEFAULT_RAM, GITHUB_URL, MINECRAFT_DIR, CONFIG_FILE
from ..i18n import T
from ..backend import LauncherBackend
from ..update_checker import UpdateChecker
from .widgets import (build_banner, build_sidebar, Tween,
                       ease_out_cubic, ease_in_out_cubic, ease_out_expo,
                       ACCENT, CARD_BG, TEXT_MUTED, NAV_ACTIVE, NAV_HOVER)
from .pages import PageBuilder


class LauncherGUI:
    """MCL Launcher 主窗口"""

    def __init__(self):
        self.backend = LauncherBackend()
        self.is_busy = False
        self.version_data = []
        self.java_list = []
        self.ms_logged_in = False
        self.ms_username = ""

        # 加载配置
        self.config = self._load_config()

        # 主题
        theme = self.config.get("theme", "dark")
        ctk.set_appearance_mode(theme)
        ctk.set_default_color_theme("blue")

        # 语言
        self.lang = self.config.get("language", "cn")

        # 版本隔离
        self.version_isolation = self.config.get("version_isolation", True)

        # 自动内存
        self.auto_ram = self.config.get("auto_ram", True)
        self.system_ram_gb = LauncherBackend.get_system_ram_gb()
        self.recommended_ram = LauncherBackend.get_recommended_ram(self.system_ram_gb)

        # 窗口
        self.root = ctk.CTk()
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry("1000x700")
        self.root.minsize(800, 550)

        self.root.attributes("-alpha", 0.0)
        self.root.update_idletasks()
        w, h = 1000, 700
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        self._enable_window_shadow()

        self.current_page = None

        # 构建 UI
        self.banner_frame, self.lbl_banner = build_banner(self.root, self._)
        self.sidebar, self.nav_btns, self.nav_indicators = build_sidebar(self.root, self._, self._switch_page)

        # 底部状态栏
        self._build_statusbar()

        self.main_area = ctk.CTkFrame(self.root, fg_color=("gray93", CARD_BG))
        self.main_area.pack(side="left", fill="both", expand=True)

        self.page_builder = PageBuilder(self)
        self.pages = self.page_builder.build_all()
        self._switch_page("launch")

        # 后台初始化
        threading.Thread(target=self._init_backend, daemon=True).start()
        UpdateChecker.check(self._on_update_result)

        # 应用启动时的内存设置
        if self.auto_ram:
            self._update_ram_values()

        self._fade_in()

    # ==================== 国际化 ====================
    def _(self, key, *args):
        val = T[self.lang].get(key, T["cn"].get(key, key))
        if args:
            try:
                return val.format(*args)
            except Exception:
                return val
        return val

    # ==================== 配置管理 ====================
    def _load_config(self):
        try:
            if CONFIG_FILE.is_file():
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _save_config(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ==================== 底部状态栏 ====================
    def _build_statusbar(self):
        ctk.CTkFrame(self.root, height=1,
                     fg_color=("gray75", "#3A3A3A")).pack(side="bottom", fill="x")
        bar = ctk.CTkFrame(self.root, height=30, corner_radius=0,
                           fg_color=("gray90", CARD_BG))
        bar.pack(side="bottom", fill="x")
        bar.pack_propagate(False)

        self.lbl_statusbar_java = ctk.CTkLabel(
            bar, text="☕ Java 检测中...",
            font=ctk.CTkFont(size=11), text_color=("gray50", TEXT_MUTED), anchor="w")
        self.lbl_statusbar_java.pack(side="left", padx=12)

        self.lbl_statusbar_ram = ctk.CTkLabel(
            bar, text="💾 内存: --",
            font=ctk.CTkFont(size=11), text_color=("gray50", TEXT_MUTED), anchor="e")
        self.lbl_statusbar_ram.pack(side="right", padx=12)

    def _update_statusbar(self):
        if self.java_list:
            best = self.java_list[0]
            ver = best["version"]
            self.root.after(0, lambda: self.lbl_statusbar_java.configure(
                text=f"☕ Java {ver} 已就绪", text_color=("#2E7D32", "#4CAF50")))
        else:
            self.root.after(0, lambda: self.lbl_statusbar_java.configure(
                text="❌ 未检测到 Java", text_color=("#C62828", "#FF5252")))

        if self.auto_ram:
            ram = max(1, round(self.recommended_ram))
        else:
            try:
                ram = int(self.combo_ram.get().replace("GB", "").strip())
            except Exception:
                ram = 0
        if ram:
            self.root.after(0, lambda: self.lbl_statusbar_ram.configure(
                text=f"💾 内存: {ram} GB"))

    # ==================== 动画 ====================
    def _fade_in(self):
        self.root.attributes("-alpha", 0.0)
        start = __import__("time").perf_counter()
        duration = 0.32  # seconds

        def tick():
            t = min(1.0, (__import__("time").perf_counter() - start) / duration)
            # ease-out-cubic
            eased = 1 - (1 - t) ** 3
            self.root.attributes("-alpha", eased)
            if t < 1.0:
                self.root.after(16, tick)

        self.root.after(16, tick)

    # ==================== 窗口阴影 ====================
    def _enable_window_shadow(self):
        try:
            import ctypes
            hwnd = self.root.winfo_id()
            DWMWA_NCRENDERING_POLICY = 2
            DWMNCRP_ENABLED = 2
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_NCRENDERING_POLICY,
                ctypes.byref(ctypes.c_int(DWMNCRP_ENABLED)),
                ctypes.sizeof(ctypes.c_int))
        except Exception:
            pass

    # ==================== 页面切换 ====================
    def _switch_page(self, name):
        for key, btn in self.nav_btns.items():
            if key == name:
                btn.configure(fg_color=("gray80", NAV_ACTIVE),
                              text_color=(ACCENT, ACCENT))
                self.nav_indicators[key].configure(fg_color=(ACCENT, ACCENT))
            else:
                btn.configure(fg_color="transparent",
                              text_color=("gray40", TEXT_MUTED))
                self.nav_indicators[key].configure(fg_color="transparent")

        new_page = self.pages[name]
        old_page = self.current_page

        if old_page is None:
            self.current_page = new_page
            new_page.place(relx=0, rely=0, relwidth=1.0, relheight=1.0)
            self._refresh_page_texts(name)
            return

        if old_page is new_page:
            return

        new_page.place(relx=1.0, rely=0, relwidth=1.0, relheight=1.0)

        import time as _time
        _start = _time.perf_counter()
        _dur = 0.22  # seconds

        def _tick():
            t = min(1.0, (_time.perf_counter() - _start) / _dur)
            eased = 1 - (1 - t) ** 3  # ease-out-cubic
            old_page.place_configure(relx=-eased * 0.28)
            new_page.place_configure(relx=1.0 - eased)
            if t < 1.0:
                self.root.after(16, _tick)
            else:
                old_page.place_forget()
                new_page.place_configure(relx=0)
                self.current_page = new_page
                self._refresh_page_texts(name)

        _tick()

    def _refresh_page_texts(self, name=None):
        if name is None:
            name = list(self.nav_btns.keys())[0] if self.nav_btns else "launch"
        icons = {"launch": "🏠", "download": "📥", "multiplayer": "🔌", "settings": "⚙️", "about": "ℹ️"}
        for key, btn in self.nav_btns.items():
            btn.configure(text=f"  {icons[key]}  {self._(key)}")

        self.lbl_banner.configure(text=self._("banner_text"))

        if name == "launch":
            self.lbl_user_text.configure(text=self._("username"))
            self.entry_user.configure(placeholder_text=self._("username_placeholder"))
            self.lbl_version_text.configure(text=self._("game_version"))
            self.btn_refresh.configure(text=self._("refresh"))
            self.lbl_java_text.configure(text=self._("java_env"))
            self.btn_scan_java.configure(text=self._("scan"))
            self._update_ram_display()
            self.lbl_log_text.configure(text=self._("log_title"))
            if not self.is_busy:
                self.btn_launch.configure(text=self._("launch_game"))
            self.lbl_hint.configure(text=self._("hint_offline"))
            if self.ms_logged_in:
                self.lbl_login_status.configure(text=self._("logged_in_as", self.ms_username))
            else:
                self.lbl_login_status.configure(text=self._("offline_mode"))
            ver = self.combo_version.get()
            if ver and ver not in (self._("loading"), self._("fetch_failed")):
                self._update_install_label(ver)
                self._update_java_hint_from_combo()
            if not self.java_list:
                self._update_java_no_found_hint()
        elif name == "download":
            self.lbl_dl_title.configure(text=self._("download_page"))
            self.lbl_dl_ver_text.configure(text=self._("download_versions"))
            self.btn_dl_install.configure(text=self._("download_install"))
        elif name == "multiplayer":
            self.lbl_mp_title.configure(text=self._("multiplayer"))
            self.lbl_mp_subtitle.configure(text=self._("multiplayer"))
            self.btn_create_room.configure(text=self._("creating_room"))
            self.btn_join_room.configure(text=self._("joining_room"))
        elif name == "settings":
            self.lbl_set_title.configure(text=self._("settings"))
            self.lbl_theme_text.configure(text=self._("theme"))
            self.lbl_lang_text.configure(text=self._("language"))
            self.lbl_isolation_text.configure(text=self._("version_isolation"))
            self.lbl_isolation_desc.configure(text=self._("version_isolation_desc"))
            self.lbl_auto_ram_text.configure(text=self._("auto_ram"))
            self.lbl_auto_ram_desc.configure(text=self._("auto_ram_desc"))
            self.btn_ms_login.configure(text=self._("ms_login") if not self.ms_logged_in else self._("ms_logout"))
            self.lbl_ms_status.configure(text=self._("ms_login_soon") if not self.ms_logged_in else self._("logged_in_as", self.ms_username))
            self._refresh_settings_states()
        elif name == "about":
            self.lbl_ab_title.configure(text=self._("about_title"))
            for lbl, key, val in self.ab_info_labels:
                lbl.configure(text=f"{self._(key)}: {val}")
            self.lbl_ab_github.configure(text=f"🔗 {self._('about_github')}: {GITHUB_URL}")
            self.lbl_ab_hint.configure(text=self._("hint_copyright"))

    # ==================== 设置事件 ====================
    def _on_theme_changed(self, choice):
        mode = "dark" if choice == self._("theme_dark") else "light"
        import time as _t

        def _fade(phase, on_done=None):
            start = _t.perf_counter()
            dur = 0.12 if phase == "out" else 0.20

            def tick():
                p = min(1.0, (_t.perf_counter() - start) / dur)
                eased = 1 - (1 - p) ** 3
                alpha = (1.0 - 0.85 * eased) if phase == "out" else (0.15 + 0.85 * eased)
                self.root.attributes("-alpha", alpha)
                if p < 1.0:
                    self.root.after(16, tick)
                elif on_done:
                    on_done()

            tick()

        def _switch():
            self.combo_theme.configure(state="disabled")
            ctk.set_appearance_mode(mode)
            self.config["theme"] = mode
            self._save_config()
            self.root.update_idletasks()
            self.root.after(10, lambda: _fade("in", lambda: self.combo_theme.configure(state="readonly")))

        _fade("out", _switch)

    def _on_lang_changed(self, choice):
        self.lang = "cn" if choice == self._("lang_cn") else "en"
        self.config["language"] = self.lang
        self._save_config()
        for p in ("launch", "download", "multiplayer", "settings", "about"):
            self._refresh_page_texts(p)
        self._refresh_settings_states()

    def _on_isolation_toggle(self):
        self.version_isolation = not self.version_isolation
        self.config["version_isolation"] = self.version_isolation
        self._save_config()
        self.switch_isolation.configure(text="ON" if self.version_isolation else "OFF")
        messagebox.showinfo(self._("settings"), self._("isolation_warning"))

    def _on_auto_ram_toggle(self):
        self.auto_ram = not self.auto_ram
        self.config["auto_ram"] = self.auto_ram
        self._save_config()
        self.switch_auto_ram.configure(text="ON" if self.auto_ram else "OFF")
        self._update_ram_values()

    def _refresh_settings_states(self):
        self.switch_isolation.configure(text="ON" if self.version_isolation else "OFF")
        self.switch_auto_ram.configure(text="ON" if self.auto_ram else "OFF")
        self.combo_theme.configure(values=[self._("theme_dark"), self._("theme_light")])
        self.combo_theme.set(self._("theme_dark") if self.config.get("theme", "dark") == "dark" else self._("theme_light"))
        self.combo_lang.configure(values=[self._("lang_cn"), self._("lang_en")])
        self.combo_lang.set(self._("lang_cn") if self.lang == "cn" else self._("lang_en"))

    def _update_ram_values(self):
        vals = ["1 GB", "2 GB", "4 GB", "6 GB", "8 GB", "12 GB", "16 GB"]
        self.combo_ram.configure(values=vals)
        if self.auto_ram:
            auto_val = max(1, round(self.recommended_ram))
            auto_str = f"{auto_val} GB"
            if auto_str not in vals:
                vals.insert(0, auto_str)
                self.combo_ram.configure(values=vals)
            self.combo_ram.set(auto_str)
            self.combo_ram.configure(state="disabled")
            self.lbl_ram_text.configure(text=self._("ram") + f" ({self._('auto_ram')})")
        else:
            self.combo_ram.configure(state="readonly")
            self.lbl_ram_text.configure(text=self._("ram"))
        self._update_statusbar()

    def _update_ram_display(self):
        if self.auto_ram:
            self._update_ram_values()
        else:
            self.lbl_ram_text.configure(text=self._("ram"))

    # ==================== 更新回调 ====================
    def _on_update_result(self, has_update, new_version):
        self.root.after(0, lambda: self._handle_update_result(has_update, new_version))

    def _handle_update_result(self, has_update, new_version):
        if has_update:
            self.lbl_update_status.configure(text=f"🔔 {self._('update_new', new_version)}")
            if messagebox.askyesno("MCL Launcher", self._("update_new", new_version)):
                webbrowser.open(f"{GITHUB_URL}/releases")
        else:
            self.lbl_update_status.configure(text=f"✓ {self._('update_latest')} ({APP_VERSION})")

    # ==================== 微软登录 ====================
    def _microsoft_login(self):
        if self.ms_logged_in:
            self.ms_logged_in = False
            self.ms_username = ""
            self.lbl_ms_status.configure(text=self._("ms_login_soon"))
            self.btn_ms_login.configure(text=self._("ms_login"))
            self._refresh_page_texts("launch")
            return
        messagebox.showinfo("MCL", self._("ms_login_soon"))

    # ==================== 加载动画 ====================
    def _start_spinner(self):
        self._spinner_base = self._("launching_java")
        self._spinner_step = 0
        self._tick_spinner()

    def _tick_spinner(self):
        if not self.is_busy:
            return
        chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.btn_launch.configure(text=f"  {chars[self._spinner_step % len(chars)]}  {self._spinner_base}")
        self._spinner_step += 1
        self.root.after(100, self._tick_spinner)

    def _set_spinner_text(self, text):
        self._spinner_base = text

    # ==================== 日志 / 进度 ====================
    def _log(self, msg):
        self.root.after(0, lambda: self._log_sync(msg))

    def _log_sync(self, msg):
        self.txt_log.configure(state="normal")
        self.txt_log.insert("end", msg + "\n")
        self.txt_log.see("end")
        self.txt_log.configure(state="disabled")

    def _status(self, msg):
        self.root.after(0, lambda: self.lbl_status.configure(text=msg))

    def _progress_set(self, cur, total):
        if total > 0:
            self.root.after(0, lambda: (
                self.progress.configure(mode="determinate") if self.progress.cget("mode") != "determinate" else None,
                self.progress.set(cur / total)
            ))

    # ==================== 后台初始化 ====================
    def _init_backend(self):
        def load_versions():
            try:
                self.version_data = self.backend.get_versions()
                ids = [v["id"] for v in self.version_data[:35]]
                self._log(f"获取到 {len(self.version_data)} 个正式版")
                self.root.after(0, lambda: self._fill_versions(ids))
                self.root.after(0, self._populate_download_versions)
            except Exception as e:
                self._log(f"获取版本列表失败: {e}")
                self.root.after(0, lambda: self.combo_version.configure(values=[self._("fetch_failed")]))

        def scan_java():
            self._refresh_java_list()

        t1 = threading.Thread(target=load_versions, daemon=True)
        t2 = threading.Thread(target=scan_java, daemon=True)
        t1.start()
        t2.start()

    # ==================== 版本相关 ====================
    def _fill_versions(self, ids):
        self.combo_version.configure(values=ids)
        if ids:
            self.combo_version.set(ids[0])
            self._update_install_label(ids[0])
            self._auto_pick_java(ids[0])

    def _refresh_versions(self):
        if self.is_busy:
            return
        self.combo_version.configure(values=[self._("loading")])
        self.combo_version.set(self._("loading"))
        self.btn_refresh.configure(state="disabled")

        def task():
            try:
                self.version_data = self.backend.get_versions()
                ids = [v["id"] for v in self.version_data[:35]]
                self._log("版本列表已刷新")
                self.root.after(0, lambda: self._fill_versions(ids))
                self.root.after(0, self._populate_download_versions)
            except Exception as e:
                self._log(f"刷新失败: {e}")
            finally:
                self.root.after(0, lambda: self.btn_refresh.configure(state="normal"))
        threading.Thread(target=task, daemon=True).start()

    def _on_version_changed(self, version):
        if not version or version in (self._("loading"), self._("fetch_failed")):
            return
        self._update_install_label(version)
        self._auto_pick_java(version)

    def _update_install_label(self, version):
        if not version or version in (self._("loading"), self._("fetch_failed")):
            return
        mc_dir = self._get_effective_minecraft_dir(version)
        self.backend.set_minecraft_dir(mc_dir)
        installed = self.backend.is_installed(version)
        self.backend.set_minecraft_dir(str(MINECRAFT_DIR))
        if installed:
            self.lbl_install_status.configure(text=f"✓ {self._('installed')}", text_color="#4CAF50")
        else:
            self.lbl_install_status.configure(text=f"○ {self._('not_installed')}", text_color="gray60")

    # ==================== 下载页版本列表 ====================
    def _populate_download_versions(self):
        for w in self.dl_version_list.winfo_children():
            w.destroy()
        self.dl_checkboxes = {}
        if not self.version_data:
            lbl = ctk.CTkLabel(self.dl_version_list, text=self._("loading"),
                               font=ctk.CTkFont(size=13), text_color="gray55")
            lbl.pack(pady=10)
            return
        for v in self.version_data[:50]:
            vid = v["id"]
            cb = ctk.CTkCheckBox(self.dl_version_list, text=vid, font=ctk.CTkFont(size=12))
            cb.pack(anchor="w", pady=1)
            self.dl_checkboxes[vid] = cb

    def _on_download_selected(self):
        selected = [vid for vid, cb in self.dl_checkboxes.items() if cb.get()]
        if not selected:
            messagebox.showinfo("MCL", self._("select_version"))
            return
        version = selected[0]
        self._switch_page("launch")
        self.combo_version.set(version)
        java_path, java_ver = self._get_selected_java_path()
        if java_path:
            self._start_download("", version, DEFAULT_RAM, java_path)

    # ==================== Java 查找 ====================
    def _refresh_java_list(self):
        try:
            self.java_list = LauncherBackend.find_all_java()
            if self.java_list:
                labels = [j["label"] for j in self.java_list]
                self._log(f"扫描到 {len(self.java_list)} 个 Java:")
                for j in self.java_list:
                    self._log(f"  {j['label']}")
                self.root.after(0, lambda: self.combo_java.configure(values=labels))
                mc_ver = self.combo_version.get()
                if mc_ver and mc_ver not in (self._("loading"), self._("fetch_failed")):
                    self._auto_pick_java(mc_ver)
                else:
                    self.combo_java.set(labels[0])
                    self._update_java_hint(self.java_list[0]["version"])
                self.root.after(0, lambda: self.lbl_java_hint.configure(
                    text="", fg_color="transparent", text_color="gray55"))
            else:
                self._log("未扫描到任何 Java")
                self.root.after(0, lambda: self.combo_java.configure(values=[self._("not_found_java")]))
                self.root.after(0, lambda: self.combo_java.set(self._("not_found_java")))
                self._update_java_no_found_hint()
            self._update_statusbar()
        except Exception as e:
            self._log(f"扫描 Java 失败: {e}")

    def _update_java_no_found_hint(self):
        self.lbl_java_hint.configure(
            text=self._("java_not_found_hint"),
            fg_color="transparent",
            text_color="#FF5252",
            hover_color=("#FFCDD2", "#4A2020"))

    def _on_java_hint_click(self):
        if not self.java_list:
            self._prompt_auto_download_java()

    def _prompt_auto_download_java(self):
        version = self.combo_version.get()
        if not version or version in (self._("loading"), self._("fetch_failed")):
            version = "1.21"
        if messagebox.askyesno(
            self._("java_download_title"),
            f"未检测到 Java，是否自动下载适合 Minecraft {version} 的 Java 运行时？\n\n"
            "（将通过 Mojang 官方源下载，约 100-200 MB）"
        ):
            self._auto_download_java(version)
        else:
            webbrowser.open("https://adoptium.net/download/")

    def _auto_download_java(self, mc_version):
        if self.is_busy:
            return
        self.is_busy = True
        self.btn_launch.configure(state="disabled")
        self.btn_scan_java.configure(state="disabled")
        self.progress.configure(mode="indeterminate")
        self.progress.start()
        self._status("正在下载 Java 运行时...")
        self._log(f"开始自动下载适合 MC {mc_version} 的 Java...")

        max_val = [100]

        def cb_set_status(s):
            self._log(s)
            self._status(s)

        def cb_set_progress(p):
            self._progress_set(p, max_val[0])

        def cb_set_max(m):
            max_val[0] = m

        callback = {
            "setStatus": cb_set_status,
            "setProgress": cb_set_progress,
            "setMax": cb_set_max,
        }

        def task():
            path, err = self.backend.auto_install_java(mc_version, callback=callback)
            self.is_busy = False
            self.root.after(0, lambda: self.progress.stop())
            self.root.after(0, lambda: self.progress.configure(mode="determinate"))
            self.root.after(0, lambda: self.progress.set(0))
            self.root.after(0, lambda: self.btn_launch.configure(state="normal", text=self._("launch_game")))
            self.root.after(0, lambda: self.btn_scan_java.configure(state="normal"))
            if path:
                self._log(f"Java 下载完成: {path}")
                self._status("Java 下载完成，正在重新扫描...")
                self._refresh_java_list()
            else:
                self._log(f"Java 下载失败: {err}")
                self._status("Java 下载失败")
                self.root.after(0, lambda: messagebox.showerror(
                    "下载失败",
                    f"Java 自动下载失败：{err}\n\n请手动安装：https://adoptium.net/download/"
                ))

        threading.Thread(target=task, daemon=True).start()

    def _scan_java(self):
        if self.is_busy:
            return
        self.btn_scan_java.configure(state="disabled")
        self.combo_java.configure(values=[self._("loading")])
        self.combo_java.set(self._("loading"))
        def task():
            self._refresh_java_list()
            self.root.after(0, lambda: self.btn_scan_java.configure(state="normal"))
        threading.Thread(target=task, daemon=True).start()

    def _auto_pick_java(self, mc_version):
        if not self.java_list:
            return
        best = LauncherBackend.pick_best_java(self.java_list, mc_version)
        if best:
            idx = self.java_list.index(best)
            self.combo_java.set(self.java_list[idx]["label"])
            self._update_java_hint(best["version"], mc_version)
            self._log(self._("java_auto_selected", best["label"]))

    def _update_java_hint(self, java_ver, mc_version=None):
        if mc_version is None:
            mc_version = self.combo_version.get()
            if not mc_version or mc_version in (self._("loading"), self._("fetch_failed")):
                return
        min_java = LauncherBackend.get_min_java_for_mc(mc_version)
        if java_ver >= min_java:
            self.lbl_java_hint.configure(
                text=f"MC {mc_version} → Java {min_java}+ {self._('compatible')}",
                fg_color="transparent", text_color="#4CAF50")
        else:
            self.lbl_java_hint.configure(
                text=f"MC {mc_version} → Java {min_java}+ | Java {java_ver} {self._('incompatible')}",
                fg_color="transparent", text_color="#FF6B6B")

    def _update_java_hint_from_combo(self):
        sel = self.combo_java.get()
        for j in self.java_list:
            if j["label"] == sel:
                self._update_java_hint(j["version"])
                return

    def _get_selected_java_path(self):
        sel = self.combo_java.get()
        for j in self.java_list:
            if j["label"] == sel:
                return j["path"], j["version"]
        return None, 0

    # ==================== 版本隔离 ====================
    def _get_effective_minecraft_dir(self, version_id):
        if self.version_isolation:
            isolated = MINECRAFT_DIR / "versions" / version_id
            isolated.mkdir(parents=True, exist_ok=True)
            return str(isolated)
        return str(MINECRAFT_DIR)

    # ==================== 启动流程 ====================
    def _on_launch(self):
        if self.is_busy:
            messagebox.showwarning(self._("please_wait"), self._("busy"))
            return

        username = self.entry_user.get().strip()
        if not username:
            messagebox.showwarning(self._("input_error"), self._("input_error"))
            return
        if len(username) < 2 or len(username) > 16:
            messagebox.showwarning(self._("input_error"), self._("username_len"))
            return
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            messagebox.showwarning(self._("input_error"), self._("username_chars"))
            return

        version = self.combo_version.get().strip()
        if not version or version in (self._("loading"), self._("fetch_failed")):
            messagebox.showwarning(self._("version_error"), self._("select_version"))
            return

        self.is_busy = True
        self.btn_launch.configure(state="disabled")
        self._start_spinner()

        def check_and_launch():
            java_path, java_ver = self._get_selected_java_path()

            if java_path and not os.path.isfile(java_path):
                self._log(f"Java 路径已失效: {java_path}")
                self.root.after(0, lambda: self._set_spinner_text(self._("java_path_invalid")))
                self._refresh_java_list()
                time.sleep(0.3)
                java_path, java_ver = self._get_selected_java_path()

            if not java_path:
                self.root.after(0, lambda: self._on_no_java())
                return

            time.sleep(0.3)

            min_java = LauncherBackend.get_min_java_for_mc(version)
            if java_ver > 0 and java_ver < min_java:
                self._log(f"Java {java_ver} 不兼容 MC {version}（需要 Java {min_java}+）")
                better = [j for j in self.java_list if j["version"] >= min_java]
                if better:
                    better.sort(key=lambda x: x["version"])
                    hint = "\n".join(f"  • {j['label']}" for j in better[:3])
                    msg = (f"Minecraft {version} 需要 Java {min_java}+。\n"
                           f"当前选中: Java {java_ver}\n\n系统中有兼容的 Java:\n{hint}\n\n"
                           "请在 Java 环境下拉框中切换后重试。")
                    self.root.after(0, lambda: self._on_launch_error(self._("java_incompatible"), msg))
                    return
                msg = (f"Minecraft {version} 需要 Java {min_java} 或更高版本。\n\n"
                       f"当前版本: Java {java_ver}\n\n"
                       "请手动安装更高版本的 Java:\n• https://adoptium.net/download/")
                self.root.after(0, lambda: self._on_launch_error(self._("java_incompatible"), msg))
                return

            try:
                if self.auto_ram:
                    ram_gb = max(1, round(self.recommended_ram))
                else:
                    ram_text = self.combo_ram.get().replace("GB", "").replace("gb", "").strip()
                    ram_gb = int(ram_text)
            except ValueError:
                ram_gb = DEFAULT_RAM

            self._log(f"Java: {java_path} (v{java_ver})")
            self._log(f"玩家: {username}  版本: {version}  内存: {ram_gb} GB")
            if self.version_isolation:
                self._log(f"版本隔离: ON → {self._get_effective_minecraft_dir(version)}")

            self.root.after(0, lambda: self._set_spinner_text(self._("launching_game")))

            mc_dir = self._get_effective_minecraft_dir(version)
            self.backend.set_minecraft_dir(mc_dir)

            if self.backend.is_installed(version):
                self.root.after(0, lambda: self._do_launch(username, version, ram_gb, java_path))
            else:
                self.root.after(0, lambda: self._start_download(username, version, ram_gb, java_path))

        threading.Thread(target=check_and_launch, daemon=True).start()

    def _on_no_java(self):
        self.is_busy = False
        self.btn_launch.configure(state="normal", text=self._("launch_game"))
        self._status(self._("launch_failed"))
        version = self.combo_version.get()
        if not version or version in (self._("loading"), self._("fetch_failed")):
            version = "1.21"
        self._prompt_auto_download_java()

    def _on_launch_error(self, title, msg):
        self.is_busy = False
        self.btn_launch.configure(state="normal", text=self._("launch_game"))
        self._status(self._("launch_failed"))
        messagebox.showerror(title, msg)

    # ==================== 下载 ====================
    def _start_download(self, username, version, ram_gb, java_path):
        self._status(f"准备下载 {version} ...")
        self._log(f"版本 {version} 尚未安装，开始从官方源下载…")

        mc_dir = self._get_effective_minecraft_dir(version)
        self.backend.set_minecraft_dir(mc_dir)
        if self.version_isolation:
            self._log(f"下载到隔离目录: {mc_dir}")

        self.is_busy = True
        self.btn_launch.configure(state="disabled")
        self.btn_refresh.configure(state="disabled")
        self.btn_scan_java.configure(state="disabled")
        self.combo_version.configure(state="disabled")
        self.combo_java.configure(state="disabled")
        self.progress.configure(mode="indeterminate")
        self.progress.start()

        max_val = [100]
        cur_val = [0]

        def cb_set_status(s):
            self._log(s)
            self._status(s)

        def cb_set_progress(p):
            cur_val[0] = p
            self._progress_set(p, max_val[0])

        def cb_set_max(m):
            max_val[0] = m

        callback = {
            "setStatus": cb_set_status,
            "setProgress": cb_set_progress,
            "setMax": cb_set_max,
        }

        def task():
            try:
                self.backend.install(version, callback=callback)
                self._log("下载完成，正在启动…")
                self._update_install_label(version)
                self.root.after(0, lambda: self._do_launch(username, version, ram_gb, java_path))
            except Exception as e:
                self._log(f"下载失败: {e}")
                self._status("下载失败")
            finally:
                self.is_busy = False
                self.root.after(0, lambda: self.btn_launch.configure(state="normal",
                                                                     text=self._("launch_game")))
                self.root.after(0, lambda: self.btn_refresh.configure(state="normal"))
                self.root.after(0, lambda: self.btn_scan_java.configure(state="normal"))
                self.root.after(0, lambda: self.combo_version.configure(state="readonly"))
                self.root.after(0, lambda: self.combo_java.configure(state="readonly"))
                self.root.after(0, lambda: (self.progress.stop(), self.progress.configure(mode="determinate"), self.progress.set(0)))

        threading.Thread(target=task, daemon=True).start()

    # ==================== 启动游戏 ====================
    def _do_launch(self, username, version, ram_gb, java_path):
        try:
            self._status("正在构建启动参数…")
            self._log("构建启动命令…")

            cmd = self.backend.get_launch_command(version, username, ram_gb, java_path)

            self._log(f"启动命令已就绪 ({len(cmd)} 个参数)")
            self._status(self._("status_game_running"))

            self.root.iconify()

            mc_dir = self.backend.minecraft_dir
            proc = subprocess.Popen(
                cmd,
                cwd=mc_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            def check_startup():
                time.sleep(3)
                ret = proc.poll()
                if ret is not None and ret != 0:
                    err = proc.stderr.read()
                    self._log(f"游戏进程异常退出 (code {ret})")
                    if err:
                        for line in err.strip().split("\n")[-6:]:
                            self._log(f"  {line}")
                    self._status(self._("launch_failed"))
                    self.root.after(0, self.root.deiconify)
                    self.root.after(0, lambda: self.btn_launch.configure(
                        state="normal", text=self._("launch_game")))
                    self.root.after(0, lambda: setattr(self, 'is_busy', False))

            threading.Thread(target=check_startup, daemon=True).start()

            self._log("游戏进程已创建")
            self._status(self._("status_game_running"))

        except Exception as e:
            self._log(f"启动失败: {e}")
            self._status(self._("launch_failed"))
            self.is_busy = False
            self.btn_launch.configure(state="normal", text=self._("launch_game"))
            messagebox.showerror("启动失败", str(e))
