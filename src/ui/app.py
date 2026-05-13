# -*- coding: utf-8 -*-
"""
MCL Launcher v1.2 — 主 GUI 类
"""
import os
import re
import json
import time
import webbrowser
import threading
import subprocess
import customtkinter as ctk
from tkinter import messagebox, filedialog
from pathlib import Path

# 抑制 Windows 上 subprocess 调用的控制台窗口闪烁
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

from ..constants import (
    APP_NAME, APP_VERSION, DEFAULT_RAM, GITHUB_URL, MINECRAFT_DIR, CONFIG_FILE,
    get_default_download_source,
)
from ..i18n import T
from ..backend import LauncherBackend
from ..theme import Theme, ACCENT_PRESETS
from ..update_checker import UpdateChecker
from ..mod_loader import ModLoaderManager
from .widgets import build_banner, build_sidebar
from .pages import PageBuilder


class LauncherGUI:
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
        mode = self.config.get("theme", "dark")
        Theme.set_mode(mode)
        Theme.set_accent(self.config.get("accent_color", "#FF8C00"))
        ctk.set_appearance_mode(mode)
        ctk.set_default_color_theme("blue")

        self.lang = self.config.get("language", "cn")
        self.version_isolation = self.config.get("version_isolation", True)
        self.download_source = self.config.get("download_source", get_default_download_source())
        self.auto_ram = self.config.get("auto_ram", True)
        self.system_ram_gb = LauncherBackend.get_system_ram_gb()
        self.recommended_ram = LauncherBackend.get_recommended_ram(self.system_ram_gb)

        # ── 窗口 ──
        self.root = ctk.CTk()
        self.root.title(f"{APP_NAME} {APP_VERSION}")
        w, h = 1000, 680
        self.root.geometry(f"{w}x{h}")
        self.root.minsize(800, 560)
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        self.root.attributes("-alpha", 0.0)
        self._enable_window_shadow()

        self.current_page = None
        self.current_page_name = "launch"

        # ── 构建 UI ──
        self.banner_frame, self.lbl_banner = build_banner(self.root, self._)
        self.sidebar, self.nav_btns, self.nav_indicators = build_sidebar(
            self.root, self._, self._switch_page)
        self._build_statusbar()

        self.main_area = ctk.CTkFrame(self.root,
                                      fg_color=Theme.pair("bg"),
                                      corner_radius=0)
        self.main_area.pack(side="left", fill="both", expand=True)

        self.page_builder = PageBuilder(self)
        self.pages = self.page_builder.build_all()
        self._switch_page("launch")

        # 后台初始化
        threading.Thread(target=self._init_backend, daemon=True).start()
        UpdateChecker.check(self._on_update_result)

        if self.auto_ram:
            self._update_ram_values()

        self._fade_in()

    # ── 国际化 ──
    def _(self, key, *args):
        val = T[self.lang].get(key, T["cn"].get(key, key))
        if args:
            try: return val.format(*args)
            except Exception: return val
        return val

    # ── 配置 ──
    def _load_config(self):
        try:
            if CONFIG_FILE.is_file():
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception: pass
        return {}

    def _save_config(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception: pass


    # ── 状态栏 ──
    def _build_statusbar(self):
        separator = ctk.CTkFrame(self.root, height=1,
                                 fg_color=("gray78", "#1E1E1E"))
        separator.pack(side="bottom", fill="x")
        bar = ctk.CTkFrame(self.root, height=26, corner_radius=0,
                           fg_color=("gray92", "#181818"))
        bar.pack(side="bottom", fill="x")
        bar.pack_propagate(False)

        self.lbl_statusbar_java = ctk.CTkLabel(
            bar, text="  Java 检测中...",
            font=ctk.CTkFont(size=10),
            text_color=Theme.pair("text_dim"), anchor="w")
        self.lbl_statusbar_java.pack(side="left", padx=10)

        self.lbl_statusbar_ram = ctk.CTkLabel(
            bar, text="",
            font=ctk.CTkFont(size=10),
            text_color=Theme.pair("text_dim"), anchor="e")
        self.lbl_statusbar_ram.pack(side="right", padx=10)

        self.lbl_statusbar_source = ctk.CTkLabel(
            bar, text="",
            font=ctk.CTkFont(size=10),
            text_color=Theme.pair("text_dim"), anchor="e")
        self.lbl_statusbar_source.pack(side="right", padx=10)

    def _update_statusbar(self):
        src = "BMCLAPI" if self.download_source == "bmclapi" else "Official"
        self._safe_set(self.lbl_statusbar_source, "text", f"  {src}  ")
        if self.java_list:
            best = self.java_list[0]
            self._safe_set(self.lbl_statusbar_java, "text",
                          f"  Java {best['version']} ready  ",
                          text_color=Theme.pair("success"))
        else:
            self._safe_set(self.lbl_statusbar_java, "text",
                          "  Java not found  ",
                          text_color=Theme.pair("error"))

    def _safe_set(self, widget, attr, value, **kw):
        try:
            self.root.after(0, lambda: widget.configure(**{attr: value}, **kw))
        except Exception: pass

    # ── 动画 ──
    def _fade_in(self):
        start = time.perf_counter()
        dur = 0.3
        def tick():
            t = min(1.0, (time.perf_counter() - start) / dur)
            self.root.attributes("-alpha", 1 - (1-t)**3)
            if t < 1.0:
                self.root.after(16, tick)
        self.root.after(16, tick)

    def _enable_window_shadow(self):
        try:
            import ctypes
            hwnd = self.root.winfo_id()
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 2, ctypes.byref(ctypes.c_int(2)), ctypes.sizeof(ctypes.c_int))
        except Exception: pass

    # ── 页面切换 ──
    def _switch_page(self, name):
        for key, btn in self.nav_btns.items():
            active = key == name
            btn.configure(fg_color=Theme.pair("nav_active") if active else "transparent",
                         text_color=(Theme.accent(), Theme.accent()) if active
                                    else Theme.pair("text_muted"))
            self.nav_indicators[key].configure(fg_color=(Theme.accent(), Theme.accent()) if active
                                               else "transparent")

        new_page = self.pages[name]
        old_page = self.current_page

        if old_page is None:
            self.current_page = new_page
            self.current_page_name = name
            new_page.place(relx=0, rely=0, relwidth=1.0, relheight=1.0)
            self._refresh_page_texts(name)
            return
        if old_page is new_page:
            return

        # 滑动动画
        new_page.place(relx=1.0, rely=0, relwidth=1.0, relheight=1.0)
        _start = time.perf_counter()
        _dur = 0.18
        def _tick():
            t = min(1.0, (time.perf_counter() - _start) / _dur)
            eased = 1 - (1-t)**3
            old_page.place_configure(relx=-eased * 0.22)
            new_page.place_configure(relx=1.0 - eased)
            if t < 1.0:
                self.root.after(16, _tick)
            else:
                old_page.place_forget()
                new_page.place_configure(relx=0)
                self.current_page = new_page
                self.current_page_name = name
                self._refresh_page_texts(name)
        _tick()

    def _refresh_page_texts(self, name=None):
        icons = {"launch":"▶","download":"↓","multiplayer":"⊙","settings":"⚙","about":"ⓘ"}
        for key, btn in self.nav_btns.items():
            btn.configure(text=f"  {icons[key]}  {self._(key)}")
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
            self.lbl_login_status.configure(
                text=self._("logged_in_as", self.ms_username) if self.ms_logged_in
                else self._("offline_mode"))
            ver = self.combo_version.get()
            if ver and ver not in (self._("loading"), self._("fetch_failed")):
                self._update_install_label(ver)
            if not self.java_list:
                self._update_java_no_found_hint()
        elif name == "download":
            self.lbl_dl_title.configure(text=self._("download_page"))
            self.lbl_dl_ver_text.configure(text=self._("download_versions"))
            self.btn_dl_install.configure(text=self._("download_install"))
            if hasattr(self, "lbl_loader_section"):
                self.lbl_loader_section.configure(text=self._("mod_loader"))
            if hasattr(self, "dl_tab_btns"):
                tab_labels = {"versions": "download_versions", "mods": "mods_browser", "shaders": "shaders_browser"}
                for key, label_key in tab_labels.items():
                    if key in self.dl_tab_btns:
                        self.dl_tab_btns[key].configure(text=self._(label_key))
        elif name == "multiplayer":
            pass
        elif name == "settings":
            self.lbl_set_title.configure(text=self._("settings"))
            self._refresh_settings_states()
        elif name == "about":
            self.lbl_ab_title.configure(text=self._("about_title"))
            for lbl, key, val in self.ab_info_labels:
                lbl.configure(text=val)

    # ── 设置事件 ──
    def _on_theme_changed(self, choice):
        mode = "dark" if choice == self._("theme_dark") else "light"
        Theme.set_mode(mode)
        ctk.set_appearance_mode(mode)
        self.config["theme"] = mode
        self._save_config()
        self._refresh_page_texts(self.current_page_name)

    def _on_lang_changed(self, choice):
        self.lang = "cn" if choice == self._("lang_cn") else "en"
        self.config["language"] = self.lang
        self._save_config()
        for p in ("launch", "download", "multiplayer", "settings", "about"):
            self._refresh_page_texts(p)
        self._refresh_settings_states()

    def _on_accent_changed(self, color, name):
        Theme.set_accent(color)
        self.config["accent_color"] = color
        self._save_config()
        for n, btn in self._accent_btns.items():
            btn.configure(border_color="#FFFFFF" if n == name else "transparent")
        self.progress.configure(progress_color=(color, color))
        if hasattr(self, "slider_opacity"):
            self.slider_opacity.configure(progress_color=(color, color))

    def _on_choose_bg(self):
        path = filedialog.askopenfilename(
            title=self._("choose_image"),
            filetypes=[("Image", "*.png *.jpg *.jpeg *.bmp"), ("All", "*.*")])
        if path:
            self.config["bg_image"] = path
            self._save_config()
            self._apply_bg_image(path)

    def _on_clear_bg(self):
        if "bg_image" in self.config:
            del self.config["bg_image"]
            self._save_config()
        self.main_area.configure(fg_color=Theme.pair("bg"))

    def _apply_bg_image(self, path):
        try:
            from PIL import Image
            img = ctk.CTkImage(Image.open(path), size=(self.main_area.winfo_width() or 800,
                                                       self.main_area.winfo_height() or 600))
            # 用 canvas 放背景图略复杂，暂用 label 实现
        except Exception: pass

    def _on_opacity_changed(self, val):
        self.config["bg_opacity"] = val
        self._save_config()

    def _on_compact_toggle(self):
        compact = bool(self.switch_compact.get())
        self.config["compact_mode"] = compact
        self._save_config()

    def _on_dl_source_changed(self, choice):
        src = "bmclapi" if choice == self._("source_bmclapi") else "official"
        self.download_source = src
        self.config["download_source"] = src
        self._save_config()
        self.backend.set_download_source(src)
        self._log(f"Download source: {choice}")
        self._update_statusbar()
        messagebox.showinfo(self._("settings"), self._("source_switch_warning"))

    def _on_isolation_toggle(self):
        self.version_isolation = bool(self.switch_isolation.get())
        self.config["version_isolation"] = self.version_isolation
        self._save_config()
        messagebox.showinfo(self._("settings"), self._("isolation_warning"))

    def _on_auto_ram_toggle(self):
        self.auto_ram = bool(self.switch_auto_ram.get())
        self.config["auto_ram"] = self.auto_ram
        self._save_config()
        self._update_ram_values()

    def _refresh_settings_states(self):
        if hasattr(self, "switch_isolation"):
            if self.version_isolation:
                self.switch_isolation.select()
            else:
                self.switch_isolation.deselect()
        if hasattr(self, "switch_auto_ram"):
            if self.auto_ram:
                self.switch_auto_ram.select()
            else:
                self.switch_auto_ram.deselect()
        if hasattr(self, "combo_theme"):
            self.combo_theme.configure(values=[self._("theme_dark"), self._("theme_light")])
            self.combo_theme.set(self._("theme_dark") if self.config.get("theme","dark")=="dark"
                                else self._("theme_light"))
        if hasattr(self, "combo_lang"):
            self.combo_lang.configure(values=[self._("lang_cn"), self._("lang_en")])
            self.combo_lang.set(self._("lang_cn") if self.lang=="cn" else self._("lang_en"))
        if hasattr(self, "combo_dl_source"):
            self.combo_dl_source.configure(values=[self._("source_official"), self._("source_bmclapi")])
            self.combo_dl_source.set(self._("source_bmclapi") if self.download_source=="bmclapi"
                                    else self._("source_official"))

    def _update_ram_values(self):
        vals = ["1 GB","2 GB","4 GB","6 GB","8 GB","12 GB","16 GB"]
        self.combo_ram.configure(values=vals)
        if self.auto_ram:
            auto_val = max(1, round(self.recommended_ram))
            auto_str = f"{auto_val} GB"
            if auto_str not in vals:
                vals.insert(0, auto_str)
                self.combo_ram.configure(values=vals)
            self.combo_ram.set(auto_str)
            self.combo_ram.configure(state="disabled")
            self._safe_set(self.lbl_statusbar_ram, "text", f"RAM: {auto_val} GB  ")
        else:
            self.combo_ram.configure(state="readonly")

    def _update_ram_display(self):
        if self.auto_ram:
            self._update_ram_values()
        else:
            try:
                ram = int(self.combo_ram.get().replace("GB","").strip())
            except Exception: ram = 0
            if ram:
                self._safe_set(self.lbl_statusbar_ram, "text",
                              f"RAM: {ram} GB  ")

    # ── 更新 ──
    def _on_update_result(self, has_update, new_version):
        self.root.after(0, lambda: self._handle_update(has_update, new_version))

    def _handle_update(self, has_update, new_version):
        if has_update:
            self.lbl_update_status.configure(
                text=f"New: {new_version}", text_color=(Theme.accent(), Theme.accent()))
            if messagebox.askyesno("MCL Launcher", self._("update_new", new_version)):
                webbrowser.open(f"{GITHUB_URL}/releases")
        else:
            self.lbl_update_status.configure(
                text=f"{APP_VERSION} {self._('update_latest')}",
                text_color=Theme.pair("text_muted"))

    # ── 微软登录 ──
    def _microsoft_login(self):
        if self.ms_logged_in:
            self.ms_logged_in = False
            self.ms_username = ""
            if hasattr(self, "lbl_ms_status"):
                self.lbl_ms_status.configure(text=self._("ms_login_soon"))
                self.btn_ms_login.configure(text=self._("ms_login"))
            self._refresh_page_texts("launch")
            return
        messagebox.showinfo("MCL", self._("ms_login_soon"))

    # ── 加载动画 ──
    def _start_spinner(self):
        self._spinner_base = self._("launching_java")
        self._spinner_step = 0
        self._tick_spinner()

    def _tick_spinner(self):
        if not self.is_busy: return
        chars = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
        self.btn_launch.configure(
            text=f" {chars[self._spinner_step % len(chars)]}  {self._spinner_base}")
        self._spinner_step += 1
        self.root.after(100, self._tick_spinner)

    def _set_spinner_text(self, text):
        self._spinner_base = text

    # ── 日志 / 进度 ──
    def _log(self, msg):
        self.root.after(0, lambda: self._log_sync(msg))

    def _log_sync(self, msg):
        try:
            self.txt_log.configure(state="normal")
            self.txt_log.insert("end", msg + "\n")
            self.txt_log.see("end")
            self.txt_log.configure(state="disabled")
        except Exception: pass

    def _status(self, msg):
        self.root.after(0, lambda: self.lbl_status.configure(text=msg))

    def _progress_set(self, cur, total):
        if total > 0:
            self.root.after(0, lambda: self.progress.set(cur / total))

    # ── 后台初始化 ──
    def _init_backend(self):
        self.backend.set_download_source(self.download_source)
        t1 = threading.Thread(target=self._load_versions, daemon=True)
        t2 = threading.Thread(target=self._refresh_java_list, daemon=True)
        t1.start(); t2.start()

    def _load_versions(self):
        try:
            self.version_data = self.backend.get_versions()
            ids = [v["id"] for v in self.version_data[:45]]
            self._log(f"Versions: {len(self.version_data)} releases")
            self.root.after(0, lambda: self._fill_versions(ids))
            self.root.after(0, self._populate_download_versions)
        except Exception as e:
            self._log(f"Failed to get versions: {e}")
            self.root.after(0, lambda: self.combo_version.configure(
                values=[self._("fetch_failed")]))

    # ── 版本 ──
    def _fill_versions(self, ids):
        self.combo_version.configure(values=ids)
        if ids:
            self.combo_version.set(ids[0])
            self._update_install_label(ids[0])
            self._auto_pick_java(ids[0])

    def _refresh_versions(self):
        if self.is_busy: return
        self.combo_version.configure(values=[self._("loading")])
        self.combo_version.set(self._("loading"))
        self.btn_refresh.configure(state="disabled")
        threading.Thread(target=self._refresh_versions_task, daemon=True).start()

    def _refresh_versions_task(self):
        try:
            self.version_data = self.backend.get_versions()
            ids = [v["id"] for v in self.version_data[:45]]
            self._log("Version list refreshed")
            self.root.after(0, lambda: self._fill_versions(ids))
            self.root.after(0, self._populate_download_versions)
        except Exception as e:
            self._log(f"Refresh failed: {e}")
        finally:
            self.root.after(0, lambda: self.btn_refresh.configure(state="normal"))

    def _on_version_changed(self, version):
        if not version or version in (self._("loading"), self._("fetch_failed")): return
        self._update_install_label(version)
        self._auto_pick_java(version)

    def _update_install_label(self, version):
        if not version or version in (self._("loading"), self._("fetch_failed")): return
        mc_dir = self._get_effective_minecraft_dir(version)
        self.backend.set_minecraft_dir(mc_dir)
        installed = self.backend.is_installed(version)
        self.backend.set_minecraft_dir(str(MINECRAFT_DIR))
        if installed:
            self.lbl_install_status.configure(
                text=self._("installed"), text_color=Theme.pair("success"))
        else:
            self.lbl_install_status.configure(
                text=self._("not_installed"), text_color=Theme.pair("text_muted"))

    # ── 下载页 ──
    def _populate_download_versions(self):
        for w in self.dl_version_list.winfo_children():
            w.destroy()
        self.dl_checkboxes = {}
        if not self.version_data:
            ctk.CTkLabel(self.dl_version_list, text=self._("loading"),
                        font=ctk.CTkFont(size=12),
                        text_color=Theme.pair("text_muted")).pack(pady=10)
            return
        for v in self.version_data[:50]:
            vid = v["id"]
            cb = ctk.CTkCheckBox(self.dl_version_list, text=vid, font=ctk.CTkFont(size=12))
            cb.pack(anchor="w", pady=2)
            self.dl_checkboxes[vid] = cb

    def _on_download_selected(self):
        selected = [vid for vid, cb in self.dl_checkboxes.items() if cb.get()]
        if not selected:
            messagebox.showinfo("MCL", self._("select_version"))
            return
        version = selected[0]
        loader = getattr(self, "dl_loader_var", None)
        self._selected_loader = loader.get() if loader else "none"
        self._switch_page("launch")
        self.combo_version.set(version)
        java_path, java_ver = self._get_selected_java_path()
        if java_path:
            self._start_download("", version, DEFAULT_RAM, java_path)

    # ── Java ──
    def _refresh_java_list(self):
        try:
            self.java_list = LauncherBackend.find_all_java()
            if self.java_list:
                labels = [j["label"] for j in self.java_list]
                self._log(self._("java_found", len(self.java_list)))
                self.root.after(0, lambda: self.combo_java.configure(values=labels))
                mc_ver = self.combo_version.get()
                if mc_ver and mc_ver not in (self._("loading"), self._("fetch_failed")):
                    self._auto_pick_java(mc_ver)
                else:
                    self.combo_java.set(labels[0])
                    self._update_java_hint(self.java_list[0]["version"])
            else:
                self._log("No Java found")
                self.root.after(0, lambda: self.combo_java.configure(
                    values=[self._("not_found_java")]))
                self.root.after(0, lambda: self.combo_java.set(self._("not_found_java")))
            self._update_java_no_found_hint()
            self.root.after(0, self._update_statusbar)
        except Exception as e:
            self._log(f"Java scan failed: {e}")

    def _update_java_no_found_hint(self):
        try:
            self.lbl_java_hint.configure(
                text=self._("java_not_found_hint"),
                fg_color="transparent", text_color=Theme.pair("error"))
        except Exception: pass

    def _on_java_hint_click(self):
        if not self.java_list:
            self._auto_download_java_for_current_version()

    def _auto_download_java_for_current_version(self):
        version = self.combo_version.get()
        if not version or version in (self._("loading"), self._("fetch_failed")):
            version = "1.21"
        self._auto_download_java(version)

    def _auto_download_java(self, mc_version):
        self.is_busy = True
        self.btn_launch.configure(state="disabled")
        self.btn_scan_java.configure(state="disabled")
        self.progress.configure(mode="indeterminate")
        self.progress.start()
        self._status(self._("java_downloading"))
        self._log(f"Downloading Java for MC {mc_version}...")
        max_val = [100]

        def task():
            zip_path, err = self.backend.download_java_zip(
                mc_version, callback={
                    "setStatus": lambda s: (self._log(s), self._status(s)),
                    "setProgress": lambda p: self._progress_set(p, max_val[0]),
                    "setMax": lambda m: (
                        max_val.__setitem__(0, m),
                        self.root.after(0, lambda: (
                            self.progress.stop(),
                            self.progress.configure(mode="determinate"),
                        )),
                    ),
                })
            self.is_busy = False
            self.root.after(0, lambda: self.progress.stop())
            self.root.after(0, lambda: self.progress.configure(mode="determinate"))
            self.root.after(0, lambda: self.btn_launch.configure(
                state="normal", text=self._("launch_game")))
            self.root.after(0, lambda: self.btn_scan_java.configure(state="normal"))
            if zip_path:
                self._log(f"Java downloaded: {zip_path}")
                self._status(self._("java_download_done"))
                # 进度条显示 100%
                self.root.after(0, lambda: self.progress.set(1.0))
                # 打开下载文件夹让用户自行安装
                folder = os.path.dirname(zip_path)
                self.root.after(0, lambda: os.startfile(folder))
                # 弹窗提示
                ext = os.path.splitext(zip_path)[1]
                if ext == ".msi":
                    hint = "请双击 .msi 安装程序，一路下一步即可完成安装。"
                else:
                    hint = "请解压 .zip 文件并将 Java 放到合适位置。"
                self.root.after(0, lambda: messagebox.showinfo(
                    self._("java_download_done"),
                    f"Java 已下载到:\n{zip_path}\n\n{hint}"))
            else:
                self._log(f"Java download failed: {err}")
                self._status(self._("java_download_failed"))
                self.root.after(0, lambda: messagebox.showerror(
                    self._("java_download_failed"), str(err)))

        threading.Thread(target=task, daemon=True).start()

    def _try_launch_again(self):
        self._log("Java ready, launching...")
        self._on_launch()

    def _scan_java(self):
        if self.is_busy: return
        self.btn_scan_java.configure(state="disabled")
        self.combo_java.configure(values=[self._("loading")])
        self.combo_java.set(self._("loading"))
        threading.Thread(target=self._scan_java_task, daemon=True).start()

    def _scan_java_task(self):
        self._refresh_java_list()
        self.root.after(0, lambda: self.btn_scan_java.configure(state="normal"))

    def _auto_pick_java(self, mc_version):
        if not self.java_list: return
        saved = LauncherBackend.load_java_preferences().get(mc_version)
        if saved and os.path.isfile(saved):
            ver, _ = LauncherBackend._parse_java_version(saved)
            if ver >= LauncherBackend.get_min_java_for_mc(mc_version):
                for j in self.java_list:
                    if os.path.normpath(j["path"]) == os.path.normpath(saved):
                        self.combo_java.set(j["label"])
                        self._update_java_hint(j["version"], mc_version)
                        return
        best = LauncherBackend.pick_best_java(self.java_list, mc_version)
        if best:
            idx = self.java_list.index(best)
            self.combo_java.set(self.java_list[idx]["label"])
            self._update_java_hint(best["version"], mc_version)
            LauncherBackend.save_java_preference(mc_version, best["path"])

    def _update_java_hint(self, java_ver, mc_version=None):
        if mc_version is None:
            mc_version = self.combo_version.get()
            if not mc_version or mc_version in (self._("loading"), self._("fetch_failed")): return
        min_java = LauncherBackend.get_min_java_for_mc(mc_version)
        if java_ver >= min_java:
            self.lbl_java_hint.configure(
                text=f"{self._('compatible')}  |  MC {mc_version} → Java {min_java}+",
                fg_color="transparent", text_color=Theme.pair("success"))
        else:
            self.lbl_java_hint.configure(
                text=f"{self._('incompatible')}  |  MC {mc_version} → Java {min_java}+  (Java {java_ver})",
                fg_color="transparent", text_color=Theme.pair("error"))

    def _get_selected_java_path(self):
        sel = self.combo_java.get()
        for j in self.java_list:
            if j["label"] == sel:
                ver = self.combo_version.get()
                if ver and ver not in (self._("loading"), self._("fetch_failed")):
                    LauncherBackend.save_java_preference(ver, j["path"])
                return j["path"], j["version"]
        return None, 0

    # ── 版本隔离 ──
    def _get_effective_minecraft_dir(self, version_id):
        if self.version_isolation:
            isolated = MINECRAFT_DIR / "versions" / version_id
            isolated.mkdir(parents=True, exist_ok=True)
            return str(isolated)
        return str(MINECRAFT_DIR)

    # ── 启动流程 ──
    def _on_launch(self):
        if self.is_busy:
            messagebox.showwarning(self._("please_wait"), self._("busy"))
            return
        username = self.entry_user.get().strip()
        if not username:
            messagebox.showwarning(self._("input_error"), self._("input_error")); return
        if len(username) < 2 or len(username) > 16:
            messagebox.showwarning(self._("input_error"), self._("username_len")); return
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            messagebox.showwarning(self._("input_error"), self._("username_chars")); return

        version = self.combo_version.get().strip()
        if not version or version in (self._("loading"), self._("fetch_failed")):
            messagebox.showwarning(self._("version_error"), self._("select_version")); return

        self.is_busy = True
        self.btn_launch.configure(state="disabled")
        self._start_spinner()

        threading.Thread(target=self._launch_task, args=(username, version), daemon=True).start()

    def _launch_task(self, username, version):
        java_path, java_ver = self._get_selected_java_path()

        if java_path and not os.path.isfile(java_path):
            self._log(f"Java path invalid: {java_path}")
            self.root.after(0, lambda: self._set_spinner_text(self._("java_path_invalid")))
            self._refresh_java_list()
            java_path, java_ver = self._get_selected_java_path()

        if not java_path:
            self.root.after(0, self._on_no_java)
            return

        min_java = LauncherBackend.get_min_java_for_mc(version)
        if java_ver > 0 and java_ver < min_java:
            self._log(f"Java {java_ver} incompatible with MC {version}")
            better = [j for j in self.java_list if j["version"] >= min_java]
            if better:
                better.sort(key=lambda x: x["version"])
                bj = better[0]
                for idx, j in enumerate(self.java_list):
                    if j["path"] == bj["path"]:
                        self.root.after(0, lambda i=idx: self.combo_java.set(
                            self.java_list[i]["label"])); break
                java_path, java_ver = bj["path"], bj["version"]
            else:
                self._log(f"No compatible Java, downloading Java {min_java}...")
                self.root.after(0, lambda: self._auto_download_java(version))
                return

        ram_gb = max(1, round(self.recommended_ram)) if self.auto_ram else DEFAULT_RAM
        if not self.auto_ram:
            try:
                ram_gb = int(self.combo_ram.get().replace("GB","").strip())
            except ValueError: pass

        self._log(f"Java: {java_path} (v{java_ver})  |  Player: {username}  |  MC: {version}  |  RAM: {ram_gb} GB")
        self.root.after(0, lambda: self._set_spinner_text(self._("launching_game")))

        mc_dir = self._get_effective_minecraft_dir(version)
        self.backend.set_minecraft_dir(mc_dir)

        mc_dir = self._get_effective_minecraft_dir(version)
        self.backend.set_minecraft_dir(mc_dir)

        if self.backend.is_installed(version):
            # 在后台线程预构建启动命令（避开 UI 线程阻塞），
            # 然后把轻量的 subprocess + iconify 派回主线程执行
            try:
                launch_version = getattr(self, "_selected_loader_version_id", None) or version
                cmd = self.backend.get_launch_command(launch_version, username, ram_gb, java_path)
                self._log(f"Launch command ready ({len(cmd)} args)")
                self.root.after(0, lambda c=cmd: self._do_launch_with_cmd(c))
            except Exception as e:
                self._log(f"Launch failed: {e}")
                self.root.after(0, lambda: self._status(self._("launch_failed")))
                self.is_busy = False
                self.root.after(0, lambda: self.btn_launch.configure(
                    state="normal", text=self._("launch_game")))
                self.root.after(0, lambda: messagebox.showerror(
                    self._("launch_failed"), str(e)))
        else:
            self.root.after(0, lambda: self._start_download(username, version, ram_gb, java_path))

    def _on_no_java(self):
        self._status("Downloading Java...")
        version = self.combo_version.get()
        if not version or version in (self._("loading"), self._("fetch_failed")):
            version = "1.21"
        self._auto_download_java(version)

    # ── 下载 ──
    def _start_download(self, username, version, ram_gb, java_path):
        src = "BMCLAPI" if self.download_source == "bmclapi" else "Official"
        self._status(f"Downloading {version}...")
        self._log(f"Downloading {version} from {src}...")
        mc_dir = self._get_effective_minecraft_dir(version)
        self.backend.set_minecraft_dir(mc_dir)

        self.is_busy = True
        self.btn_launch.configure(state="disabled")
        self.btn_refresh.configure(state="disabled")
        self.btn_scan_java.configure(state="disabled")
        self.combo_version.configure(state="disabled")
        self.combo_java.configure(state="disabled")
        self.progress.configure(mode="indeterminate")
        self.progress.start()

        max_val = [100]
        threading.Thread(target=self._download_task, args=(
            username, version, ram_gb, java_path, max_val), daemon=True).start()

    def _download_task(self, username, version, ram_gb, java_path, max_val):
        try:
            self.backend.install(version, callback={
                "setStatus": lambda s: (self._log(s), self._status(s)),
                "setProgress": lambda p: self._progress_set(p, max_val[0]),
                "setMax": lambda m: max_val.__setitem__(0, m),
            })
            self._log("Download complete, launching...")
            self._update_install_label(version)

            # 安装模组加载器（如果选择了）
            loader_key = getattr(self, "_selected_loader", "none")
            if loader_key and loader_key != "none":
                self._log(f"Installing loader: {loader_key}")
                mc_dir = self._get_effective_minecraft_dir(version)
                ok, err = ModLoaderManager.install_loader(
                    loader_key, version, mc_dir,
                    callback={
                        "setStatus": lambda s: (self._log(s), self._status(s)),
                        "setProgress": lambda p: self._progress_set(p, max_val[0]),
                        "setMax": lambda m: max_val.__setitem__(0, m),
                    },
                    java_path=java_path,
                )
                if ok:
                    self._selected_loader_version_id = \
                        ModLoaderManager.get_installed_loader_version_id(loader_key, version)
                    self._log(f"Loader installed: {self._selected_loader_version_id}")
                else:
                    self._log(f"Loader install failed: {err}")
                    self._selected_loader_version_id = None
            else:
                self._selected_loader_version_id = None

            try:
                launch_version = getattr(self, "_selected_loader_version_id", None) or version
                cmd = self.backend.get_launch_command(launch_version, username, ram_gb, java_path)
                self._log(f"Launch command ready ({len(cmd)} args)")
                self.root.after(0, lambda c=cmd: self._do_launch_with_cmd(c))
            except Exception as e:
                self._log(f"Launch failed: {e}")
                self._status(self._("launch_failed"))
                self.root.after(0, lambda: messagebox.showerror(
                    self._("launch_failed"), str(e)))
        except Exception as e:
            import traceback as _tb
            tb_msg = _tb.format_exc()
            self._log(f"Download failed: {e}")
            self._log(f"Traceback: {tb_msg}")
            self._status(self._("launch_failed"))
        finally:
            self.is_busy = False
            self.root.after(0, lambda: self.btn_launch.configure(
                state="normal", text=self._("launch_game")))
            self.root.after(0, lambda: self.btn_refresh.configure(state="normal"))
            self.root.after(0, lambda: self.btn_scan_java.configure(state="normal"))
            self.root.after(0, lambda: self.combo_version.configure(state="readonly"))
            self.root.after(0, lambda: self.combo_java.configure(state="readonly"))
            self.root.after(0, lambda: (self.progress.stop(),
                                       self.progress.configure(mode="determinate", value=0)))

    # ── 启动游戏 ──
    def _do_launch_with_cmd(self, cmd):
        """在主线程执行：启动进程 + 最小化窗口（必须在主线程调用）"""
        try:
            self._status(self._("status_game_running"))
            self.root.iconify()
            mc_dir = self.backend.minecraft_dir
            proc = subprocess.Popen(cmd, cwd=mc_dir,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                    creationflags=_NO_WINDOW)
            threading.Thread(target=self._monitor_process, args=(proc,), daemon=True).start()
            self._log("Game process started")
        except Exception as e:
            self._log(f"Launch failed: {e}")
            self._status(self._("launch_failed"))
            self.is_busy = False
            self.btn_launch.configure(state="normal", text=self._("launch_game"))
            messagebox.showerror(self._("launch_failed"), str(e))

    def _monitor_process(self, proc):
        time.sleep(3)
        ret = proc.poll()
        if ret is not None and ret != 0:
            err = proc.stderr.read()
            self._log(f"Game exited with code {ret}")
            if err:
                for line in err.strip().split("\n")[-6:]:
                    self._log(f"  {line}")
            self._status(self._("launch_failed"))
            self.root.after(0, self.root.deiconify)
            self.root.after(0, lambda: self.btn_launch.configure(
                state="normal", text=self._("launch_game")))
            self.root.after(0, lambda: setattr(self, 'is_busy', False))
