# -*- coding: utf-8 -*-
"""
MCL Launcher v1.2 — 五页 UI 构建器
"""
import os
import threading
import webbrowser
import customtkinter as ctk
from tkinter import messagebox, colorchooser, filedialog
from pathlib import Path

from ..constants import APP_VERSION, AUTHOR_NAME, GITHUB_URL, MINECRAFT_DIR
from ..theme import Theme, ACCENT_PRESETS
from ..update_checker import UpdateChecker
from ..modrinth import ModrinthAPI
from ..mod_loader import ModLoaderManager, LOADER_DEFS
from .widgets import flat_btn, ghost_btn, card, separator, section_label, hover_btn


class PageBuilder:
    def __init__(self, app):
        self.app = app

    @property
    def t(self): return self.app._

    def build_all(self):
        return {
            "launch":      self._build_launch(),
            "download":    self._build_download(),
            "multiplayer": self._build_multiplayer(),
            "settings":    self._build_settings(),
            "about":       self._build_about(),
        }

    # ── 启动页 ──────────────────────────────────────────────────────────
    def _build_launch(self):
        app = self.app
        page = ctk.CTkFrame(app.main_area, fg_color="transparent")
        px = 28

        # 顶部：标题 + 启动按钮
        top = ctk.CTkFrame(page, fg_color="transparent")
        top.pack(pady=(22, 10), padx=px, fill="x")

        left = ctk.CTkFrame(top, fg_color="transparent")
        left.pack(side="left")
        ctk.CTkLabel(left, text="MCL Launcher",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=Theme.pair("text")).pack(anchor="w")
        app.lbl_login_status = ctk.CTkLabel(left, text="",
                                            font=ctk.CTkFont(size=11),
                                            text_color=Theme.pair("text_muted"))
        app.lbl_login_status.pack(anchor="w", pady=(1, 0))

        app.btn_launch = flat_btn(top, self.t("launch_game"),
                                  command=app._on_launch,
                                  height=46, width=190, font_size=15, bold=True,
                                  fg="#4CAF50", hover="#388E3C")
        app.btn_launch.pack(side="right")

        # 主卡片
        c = card(page)
        c.pack(pady=(0, 10), padx=px, fill="both", expand=True)
        inner = ctk.CTkFrame(c, fg_color="transparent")
        inner.pack(pady=18, padx=22, fill="both", expand=True)

        fh, lw = 34, 72

        def row_frame():
            f = ctk.CTkFrame(inner, fg_color="transparent")
            f.pack(fill="x", pady=(0, 8))
            return f

        def lbl(parent, key, w=lw):
            return ctk.CTkLabel(parent, text=self.t(key), width=w, anchor="w",
                                font=ctk.CTkFont(size=13),
                                text_color=Theme.pair("text"))

        # 用户名
        r1 = row_frame()
        app.lbl_user_text = lbl(r1, "username")
        app.lbl_user_text.pack(side="left")
        app.entry_user = ctk.CTkEntry(r1, height=fh, font=ctk.CTkFont(size=13),
                                      placeholder_text=self.t("username_placeholder"),
                                      fg_color=Theme.pair("input_bg"),
                                      border_color=Theme.pair("border"),
                                      corner_radius=8)
        app.entry_user.pack(side="left", fill="x", expand=True, padx=(6, 0))
        app.entry_user.insert(0, os.environ.get("USERNAME", "Player"))

        # 版本
        r2 = row_frame()
        app.lbl_version_text = lbl(r2, "game_version")
        app.lbl_version_text.pack(side="left")
        app.combo_version = ctk.CTkComboBox(r2, values=[self.t("loading")], height=fh,
                                            font=ctk.CTkFont(size=13), state="readonly",
                                            corner_radius=8, command=app._on_version_changed,
                                            border_color=Theme.pair("border"))
        app.combo_version.set(self.t("loading"))
        app.combo_version.pack(side="left", fill="x", expand=True, padx=(6, 8))
        app.btn_refresh = ghost_btn(r2, self.t("refresh"), command=app._refresh_versions,
                                    width=54, height=fh)
        app.btn_refresh.pack(side="right")

        # Java
        r3 = row_frame()
        app.lbl_java_text = lbl(r3, "java_env")
        app.lbl_java_text.pack(side="left")
        app.combo_java = ctk.CTkComboBox(r3, values=[self.t("loading")], height=fh,
                                         font=ctk.CTkFont(size=12), state="readonly",
                                         corner_radius=8,
                                         border_color=Theme.pair("border"))
        app.combo_java.set(self.t("loading"))
        app.combo_java.pack(side="left", fill="x", expand=True, padx=(6, 8))
        app.btn_scan_java = ghost_btn(r3, self.t("scan"), command=app._scan_java,
                                      width=54, height=fh)
        app.btn_scan_java.pack(side="right")

        # Java 提示
        app.lbl_java_hint = ctk.CTkButton(inner, text="", font=ctk.CTkFont(size=11),
                                          fg_color="transparent",
                                          hover_color=Theme.pair("hover"),
                                          anchor="w", command=app._on_java_hint_click)
        app.lbl_java_hint.pack(anchor="w", padx=(lw + 6, 0), pady=(0, 6))

        # 内存
        r4 = row_frame()
        app.lbl_ram_text = lbl(r4, "ram")
        app.lbl_ram_text.pack(side="left")
        app.combo_ram = ctk.CTkComboBox(r4, values=["1 GB","2 GB","4 GB","6 GB","8 GB","12 GB","16 GB"],
                                        height=fh, font=ctk.CTkFont(size=13), state="readonly",
                                        corner_radius=8,
                                        border_color=Theme.pair("border"))
        app.combo_ram.set("4 GB")
        app.combo_ram.pack(side="left", fill="x", expand=True, padx=(6, 0))

        # 安装状态
        app.lbl_install_status = ctk.CTkLabel(inner, text="",
                                              font=ctk.CTkFont(size=11),
                                              text_color=Theme.pair("text_muted"))
        app.lbl_install_status.pack(anchor="w", padx=(lw + 6, 0), pady=(2, 0))

        separator(inner).pack(fill="x", pady=(10, 8))

        # 进度条
        app.progress = ctk.CTkProgressBar(inner, height=6, corner_radius=3,
                                          progress_color=(Theme.accent(), Theme.accent()),
                                          fg_color=Theme.pair("progress_bg"))
        app.progress.pack(fill="x")
        app.progress.set(0)
        app.lbl_status = ctk.CTkLabel(inner, text=self.t("status_ready"),
                                      font=ctk.CTkFont(size=11),
                                      text_color=Theme.pair("text_muted"))
        app.lbl_status.pack(anchor="w", pady=(3, 0))
        # Java 下载提示
        app.lbl_java_dl_hint = ctk.CTkLabel(inner, text=self.t("java_download_hint"),
                                             font=ctk.CTkFont(size=10),
                                             text_color=Theme.pair("text_dim"))
        app.lbl_java_dl_hint.pack(anchor="w", padx=(2, 0))

        # 日志
        app.lbl_log_text = ctk.CTkLabel(inner, text=self.t("log_title"), anchor="w",
                                        font=ctk.CTkFont(size=11, weight="bold"),
                                        text_color=Theme.pair("text_dim"))
        app.lbl_log_text.pack(anchor="w", pady=(10, 4))
        app.txt_log = ctk.CTkTextbox(inner, height=80, font=("Consolas", 11),
                                     wrap="word", corner_radius=8,
                                     fg_color=Theme.pair("card2"),
                                     border_width=1,
                                     border_color=Theme.pair("border"))
        app.txt_log.pack(fill="both", expand=True)
        app.txt_log.configure(state="disabled")

        app.lbl_hint = ctk.CTkLabel(inner, text=self.t("hint_offline"),
                                    font=ctk.CTkFont(size=10),
                                    text_color=Theme.pair("text_dim"))
        app.lbl_hint.pack(pady=(6, 2))

        return page

    # ── 下载页 ──────────────────────────────────────────────────────────
    def _build_download(self):
        app = self.app
        page = ctk.CTkFrame(app.main_area, fg_color="transparent")
        px = 28

        # 顶部标题 + 子选项卡
        top = ctk.CTkFrame(page, fg_color="transparent")
        top.pack(pady=(22, 6), padx=px, fill="x")
        app.lbl_dl_title = ctk.CTkLabel(top, text=self.t("download_page"),
                                        font=ctk.CTkFont(size=20, weight="bold"))
        app.lbl_dl_title.pack(side="left")

        tab_frame = ctk.CTkFrame(top, fg_color=Theme.pair("card2"), corner_radius=8)
        tab_frame.pack(side="right")
        app.dl_tab_btns = {}
        app.dl_current_tab = "versions"
        for key, label_key in [("versions", "download_versions"),
                                ("mods", "mods_browser"),
                                ("shaders", "shaders_browser")]:
            btn = ctk.CTkButton(tab_frame, text=self.t(label_key),
                                height=28, width=80 if key == "versions" else 72,
                                font=ctk.CTkFont(size=11),
                                corner_radius=6,
                                fg_color=Theme.accent() if key == "versions" else "transparent",
                                text_color="#FFFFFF" if key == "versions" else Theme.pair("text_muted"),
                                hover_color=Theme.pair("hover"),
                                command=lambda k=key: self._switch_dl_tab(k))
            btn.pack(side="left", padx=2, pady=2)
            app.dl_tab_btns[key] = btn

        # 内容容器 (三页)
        app.dl_content = ctk.CTkFrame(page, fg_color="transparent")
        app.dl_content.pack(fill="both", expand=True, padx=px, pady=(0, 10))
        app.dl_sub_pages = {
            "versions": self._build_dl_versions(app.dl_content),
            "mods":     self._build_dl_mods(app.dl_content),
            "shaders":  self._build_dl_shaders(app.dl_content),
        }
        app.dl_sub_pages["versions"].place(relx=0, rely=0, relwidth=1, relheight=1)
        for k in ("mods", "shaders"):
            app.dl_sub_pages[k].place_forget()

        return page

    # ── 下载子页: 版本 + 加载器 ──
    def _build_dl_versions(self, parent):
        app = self.app
        sub = ctk.CTkFrame(parent, fg_color="transparent")

        c = card(sub)
        c.pack(fill="both", expand=True)
        inner = ctk.CTkFrame(c, fg_color="transparent")
        inner.pack(pady=14, padx=18, fill="both", expand=True)

        app.lbl_dl_ver_text = ctk.CTkLabel(inner, text=self.t("download_versions"),
                                           font=ctk.CTkFont(size=13, weight="bold"))
        app.lbl_dl_ver_text.pack(anchor="w", pady=(0, 8))

        app.dl_version_list = ctk.CTkScrollableFrame(inner,
                                                     fg_color=Theme.pair("card2"),
                                                     corner_radius=8, height=200)
        app.dl_version_list.pack(fill="both", expand=True, pady=(0, 8))
        app.dl_checkboxes = {}
        app._populate_download_versions()

        # ── 模组加载器选择 ──
        separator(inner).pack(fill="x", pady=(4, 8))

        app.lbl_loader_section = ctk.CTkLabel(inner, text=self.t("mod_loader"),
                                              font=ctk.CTkFont(size=12, weight="bold"))
        app.lbl_loader_section.pack(anchor="w", pady=(0, 6))

        loader_frame = ctk.CTkFrame(inner, fg_color="transparent")
        loader_frame.pack(fill="x", pady=(0, 10))

        app.dl_loader_var = ctk.StringVar(value="none")
        app.dl_loader_btns = {}
        app.dl_loader_warn = ctk.CTkLabel(inner, text="", font=ctk.CTkFont(size=10),
                                          text_color=("#E65100", "#FFB74D"), anchor="w")
        app.dl_loader_warn.pack(anchor="w", pady=(0, 6))

        loaders = [
            ("none",     "loader_none",     None),
            ("forge",    "loader_forge",    None),
            ("fabric",   "loader_fabric",   None),
            ("neoforge", "loader_neoforge", None),
            ("optifine", "loader_optifine", None),
        ]
        col = 0
        for key, label_key, group in loaders:
            rb = ctk.CTkRadioButton(
                loader_frame, text=self.t(label_key),
                variable=app.dl_loader_var, value=key,
                font=ctk.CTkFont(size=12),
                fg_color=Theme.accent(),
                hover_color=Theme.pair("hover"),
                command=lambda k=key: self._on_loader_selected(k),
            )
            rb.grid(row=0, column=col, padx=(0, 14), pady=4)
            app.dl_loader_btns[key] = rb
            col += 1

        app.btn_dl_install = flat_btn(inner, self.t("download_install"),
                                      command=self._on_dl_with_loader, height=40)
        app.btn_dl_install.pack(fill="x")

        return sub

    # ── 下载子页: 模组浏览 ──
    def _build_dl_mods(self, parent):
        app = self.app
        sub = ctk.CTkFrame(parent, fg_color="transparent")

        # 搜索栏
        search_frame = ctk.CTkFrame(sub, fg_color="transparent")
        search_frame.pack(fill="x", pady=(0, 8))
        app.mods_search_entry = ctk.CTkEntry(
            search_frame, height=34, font=ctk.CTkFont(size=13),
            placeholder_text=self.t("mod_search_hint"),
            fg_color=Theme.pair("input_bg"),
            border_color=Theme.pair("border"), corner_radius=8,
        )
        app.mods_search_entry.pack(side="left", fill="x", expand=True)
        app.mods_search_entry.bind("<Return>", lambda e: self._search_mods())
        app.mods_search_btn = flat_btn(search_frame, "🔍", width=36, height=34,
                                       command=self._search_mods)
        app.mods_search_btn.pack(side="left", padx=(6, 0))

        # 结果列表
        c = card(sub)
        c.pack(fill="both", expand=True)
        inner = ctk.CTkFrame(c, fg_color="transparent")
        inner.pack(pady=10, padx=14, fill="both", expand=True)

        app.mods_result_list = ctk.CTkScrollableFrame(inner,
                                                      fg_color=Theme.pair("card2"),
                                                      corner_radius=8)
        app.mods_result_list.pack(fill="both", expand=True)

        # 初始提示
        ctk.CTkLabel(app.mods_result_list,
                     text=self.t("mod_search_hint"),
                     font=ctk.CTkFont(size=12),
                     text_color=Theme.pair("text_muted")).pack(pady=30)
        app.mod_search_offset = 0
        app.mod_search_results = []

        return sub

    # ── 下载子页: 光影浏览 ──
    def _build_dl_shaders(self, parent):
        app = self.app
        sub = ctk.CTkFrame(parent, fg_color="transparent")

        search_frame = ctk.CTkFrame(sub, fg_color="transparent")
        search_frame.pack(fill="x", pady=(0, 8))
        app.shaders_search_entry = ctk.CTkEntry(
            search_frame, height=34, font=ctk.CTkFont(size=13),
            placeholder_text=self.t("search_shaders"),
            fg_color=Theme.pair("input_bg"),
            border_color=Theme.pair("border"), corner_radius=8,
        )
        app.shaders_search_entry.pack(side="left", fill="x", expand=True)
        app.shaders_search_entry.bind("<Return>", lambda e: self._search_shaders())
        app.shaders_search_btn = flat_btn(search_frame, "🔍", width=36, height=34,
                                          command=self._search_shaders)
        app.shaders_search_btn.pack(side="left", padx=(6, 0))

        c = card(sub)
        c.pack(fill="both", expand=True)
        inner = ctk.CTkFrame(c, fg_color="transparent")
        inner.pack(pady=10, padx=14, fill="both", expand=True)

        app.shaders_result_list = ctk.CTkScrollableFrame(inner,
                                                         fg_color=Theme.pair("card2"),
                                                         corner_radius=8)
        app.shaders_result_list.pack(fill="both", expand=True)

        ctk.CTkLabel(app.shaders_result_list,
                     text=self.t("search_shaders"),
                     font=ctk.CTkFont(size=12),
                     text_color=Theme.pair("text_muted")).pack(pady=30)
        app.shader_search_offset = 0
        app.shader_search_results = []

        return sub

    # ── 下载页 子Tab 切换 ──
    def _switch_dl_tab(self, tab_key):
        app = self.app
        app.dl_current_tab = tab_key
        for key, btn in app.dl_tab_btns.items():
            active = key == tab_key
            btn.configure(fg_color=Theme.accent() if active else "transparent",
                          text_color="#FFFFFF" if active else Theme.pair("text_muted"))
        for key, page in app.dl_sub_pages.items():
            if key == tab_key:
                page.place(relx=0, rely=0, relwidth=1, relheight=1)
            else:
                page.place_forget()

    # ── 加载器选择 ──
    def _on_loader_selected(self, loader_key):
        app = self.app
        if loader_key == "none":
            app.dl_loader_warn.configure(text="")
            return
        # 兼容性提示
        if loader_key == "optifine":
            app.dl_loader_warn.configure(text=self.t("loader_optifine_forge_warn"))
        elif loader_key in ("forge", "neoforge", "fabric"):
            app.dl_loader_warn.configure(text="")
        else:
            app.dl_loader_warn.configure(text="")

    # ── 下载 (版本 + 可选加载器) ──
    def _on_dl_with_loader(self):
        app = self.app
        # 复用原有版本选择逻辑
        app._on_download_selected()
        # 加载器信息已通过 app.dl_loader_var 获取
        # app._start_download 会在后台自动安装加载器 (见 app.py 修改)

    # ── 模组搜索 ──
    def _search_mods(self):
        app = self.app
        query = (app.mods_search_entry.get() or "").strip()
        if not query:
            query = ""
        app.mod_search_offset = 0
        threading.Thread(target=self._search_mods_task,
                         args=(query,), daemon=True).start()

    def _search_mods_task(self, query):
        app = self.app
        try:
            version = app.combo_version.get()
            if version in (self.t("loading"), self.t("fetch_failed"), ""):
                version = None
            hits, total, offset = ModrinthAPI.search_mods(
                query, version=version, limit=20,
                offset=app.mod_search_offset,
            )
            app.mod_search_results = hits
            app.root.after(0, lambda: self._render_mod_results(hits, total))
        except Exception as e:
            app.root.after(0, lambda: self._show_search_error(
                app.mods_result_list, str(e)))

    def _render_mod_results(self, hits, total):
        app = self.app
        lst = app.mods_result_list
        for w in lst.winfo_children():
            w.destroy()

        if not hits:
            ctk.CTkLabel(lst, text=self.t("no_results"),
                        font=ctk.CTkFont(size=12),
                        text_color=Theme.pair("text_muted")).pack(pady=20)
            return

        for hit in hits:
            self._render_project_card(lst, hit, "mod")

        # 加载更多
        if len(hits) >= 20:
            btn_more = ghost_btn(lst, self.t("load_more"),
                                 command=lambda: self._load_more_mods(),
                                 height=32)
            btn_more.pack(fill="x", pady=(6, 2))

    def _load_more_mods(self):
        app = self.app
        app.mod_search_offset += 20
        query = (app.mods_search_entry.get() or "").strip()
        threading.Thread(target=self._search_mods_task,
                         args=(query,), daemon=True).start()

    # ── 光影搜索 ──
    def _search_shaders(self):
        app = self.app
        query = (app.shaders_search_entry.get() or "").strip()
        if not query:
            query = ""
        app.shader_search_offset = 0
        threading.Thread(target=self._search_shaders_task,
                         args=(query,), daemon=True).start()

    def _search_shaders_task(self, query):
        app = self.app
        try:
            hits, total, offset = ModrinthAPI.search_shaders(
                query, limit=20, offset=app.shader_search_offset,
            )
            app.shader_search_results = hits
            app.root.after(0, lambda: self._render_shader_results(hits, total))
        except Exception as e:
            app.root.after(0, lambda: self._show_search_error(
                app.shaders_result_list, str(e)))

    def _render_shader_results(self, hits, total):
        app = self.app
        lst = app.shaders_result_list
        for w in lst.winfo_children():
            w.destroy()

        if not hits:
            ctk.CTkLabel(lst, text=self.t("no_results"),
                        font=ctk.CTkFont(size=12),
                        text_color=Theme.pair("text_muted")).pack(pady=20)
            return

        for hit in hits:
            self._render_project_card(lst, hit, "shader")

        if len(hits) >= 20:
            btn_more = ghost_btn(lst, self.t("load_more"),
                                 command=lambda: self._load_more_shaders(),
                                 height=32)
            btn_more.pack(fill="x", pady=(6, 2))

    def _load_more_shaders(self):
        app = self.app
        app.shader_search_offset += 20
        query = (app.shaders_search_entry.get() or "").strip()
        threading.Thread(target=self._search_shaders_task,
                         args=(query,), daemon=True).start()

    # ── 项目卡片 ──
    def _render_project_card(self, parent, hit, ptype):
        app = self.app
        title = hit.get("title", hit.get("slug", "Unknown"))
        author = hit.get("author", "Unknown")
        slug = hit.get("slug", "")
        desc = (hit.get("description", "") or "")[:80]
        downloads = hit.get("downloads", 0)
        icon_url = hit.get("icon_url", "")

        row = ctk.CTkFrame(parent, fg_color="transparent", height=44)
        row.pack(fill="x", pady=2)
        row.pack_propagate(False)

        name_lbl = ctk.CTkLabel(row, text=title, font=ctk.CTkFont(size=12, weight="bold"),
                                anchor="w")
        name_lbl.pack(side="left", padx=(8, 0))
        # 截断长标题
        if len(title) > 28:
            name_lbl.configure(text=title[:25] + "...")

        info = f"{author}  |  {downloads:,} DL"
        info_lbl = ctk.CTkLabel(row, text=info,
                                font=ctk.CTkFont(size=10),
                                text_color=Theme.pair("text_muted"), anchor="w")
        info_lbl.pack(side="left", padx=(10, 0))

        install_btn = flat_btn(row, self.t("mod_install"),
                               command=lambda s=slug, p=ptype, t=title: self._install_project(s, p, t),
                               height=26, width=56, font_size=10)
        install_btn.pack(side="right", padx=(0, 8))

    # ── 安装模组/光影 ──
    def _install_project(self, slug, ptype, title):
        app = self.app
        if app.is_busy:
            messagebox.showwarning(self.t("please_wait"), self.t("busy"))
            return

        version = app.combo_version.get()
        if version in (self.t("loading"), self.t("fetch_failed"), ""):
            version = None

        dest_dir = Path(str(MINECRAFT_DIR))
        if ptype == "mod":
            dest_dir = dest_dir / "mods"
        elif ptype == "shader":
            dest_dir = dest_dir / "shaderpacks"
        else:
            dest_dir = dest_dir / "resourcepacks"
        dest_dir.mkdir(parents=True, exist_ok=True)

        app._log(f"{self.t('mod_installing', title)}")
        app._status(self.t("mod_installing", title))

        threading.Thread(target=self._install_project_task,
                         args=(slug, ptype, str(dest_dir), title, version),
                         daemon=True).start()

    def _install_project_task(self, slug, ptype, dest_dir, title, game_version):
        app = self.app
        try:
            filename, url, ver = ModrinthAPI.get_latest_download_info(
                slug, game_version=game_version,
                loader=app.dl_loader_var.get() if app.dl_loader_var.get() != "none" else None,
            )
            if not url:
                app.root.after(0, lambda: messagebox.showwarning(
                    "MCL", f"{title}: 未找到兼容版本"))
                return

            app.root.after(0, lambda: app._status(f"Downloading {title}..."))
            cb = {
                "setStatus": lambda s: app.root.after(0, lambda: app._status(s)),
                "setProgress": lambda p: app.root.after(0, lambda: app._progress_set(p, 100)),
                "setMax": lambda m: None,
            }
            path = ModrinthAPI.download_file(url, dest_dir, filename=filename, callback=cb)
            if path:
                app._log(f"Installed: {title} → {path}")
                app.root.after(0, lambda: app._status(f"{title} installed"))
                app.root.after(0, lambda: messagebox.showinfo("MCL",
                                f"{title} installed successfully"))
        except Exception as e:
            app._log(f"Install failed: {title} — {e}")
            app.root.after(0, lambda: messagebox.showerror(
                "MCL", f"Install failed:\n{e}"))

    def _show_search_error(self, list_widget, err):
        for w in list_widget.winfo_children():
            w.destroy()
        ctk.CTkLabel(list_widget, text=f"Search error: {err}",
                    font=ctk.CTkFont(size=12),
                    text_color=Theme.pair("error")).pack(pady=20)

    # ── 联机页 ──────────────────────────────────────────────────────────
    def _build_multiplayer(self):
        app = self.app
        page = ctk.CTkFrame(app.main_area, fg_color="transparent")
        px = 28

        top = ctk.CTkFrame(page, fg_color="transparent")
        top.pack(pady=(22, 10), padx=px, fill="x")
        app.lbl_mp_title = ctk.CTkLabel(top, text=self.t("multiplayer"),
                                        font=ctk.CTkFont(size=20, weight="bold"))
        app.lbl_mp_title.pack(side="left")

        c = card(page)
        c.pack(pady=(0, 10), padx=px, fill="both", expand=True)
        inner = ctk.CTkFrame(c, fg_color="transparent")
        inner.pack(pady=60, padx=40, fill="both", expand=True)

        ctk.CTkLabel(inner, text="⊙", font=ctk.CTkFont(size=52),
                     text_color=(Theme.accent(), Theme.accent())).pack(pady=(20, 8))
        app.lbl_mp_subtitle = ctk.CTkLabel(inner, text=self.t("multiplayer"),
                                           font=ctk.CTkFont(size=17, weight="bold"))
        app.lbl_mp_subtitle.pack(pady=(0, 6))
        ctk.CTkLabel(inner, text=self.t("multiplayer_wip"),
                     font=ctk.CTkFont(size=12),
                     text_color=Theme.pair("text_muted")).pack(pady=(0, 28))

        app.btn_create_room = flat_btn(inner, self.t("creating_room"), height=42,
                                       command=lambda: messagebox.showinfo("MCL", self.t("multiplayer_wip")))
        app.btn_create_room.pack(fill="x", pady=(0, 10))

        app.btn_join_room = ghost_btn(inner, self.t("joining_room"), height=42,
                                      command=lambda: messagebox.showinfo("MCL", self.t("multiplayer_wip")))
        app.btn_join_room.pack(fill="x")

        return page

    # ── 设置页 ──────────────────────────────────────────────────────────
    def _build_settings(self):
        app = self.app
        page = ctk.CTkFrame(app.main_area, fg_color="transparent")
        px = 28

        top = ctk.CTkFrame(page, fg_color="transparent")
        top.pack(pady=(22, 10), padx=px, fill="x")
        app.lbl_set_title = ctk.CTkLabel(top, text=self.t("settings"),
                                         font=ctk.CTkFont(size=20, weight="bold"))
        app.lbl_set_title.pack(side="left")

        scroll = ctk.CTkScrollableFrame(page, fg_color="transparent", corner_radius=0)
        scroll.pack(fill="both", expand=True, padx=px, pady=(0, 10))

        def group(title_key):
            f = ctk.CTkFrame(scroll, fg_color="transparent")
            f.pack(fill="x", pady=(14, 4))
            section_label(f, self.t(title_key)).pack(anchor="w", pady=(0, 6))
            c = card(f)
            c.pack(fill="x")
            inner = ctk.CTkFrame(c, fg_color="transparent")
            inner.pack(pady=14, padx=18, fill="x")
            return inner

        def setting_row(parent, label_text, desc_text=None):
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", pady=(0, 10))
            left = ctk.CTkFrame(row, fg_color="transparent")
            left.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(left, text=label_text, font=ctk.CTkFont(size=13),
                         anchor="w").pack(anchor="w")
            if desc_text:
                ctk.CTkLabel(left, text=desc_text, font=ctk.CTkFont(size=11),
                             text_color=Theme.pair("text_muted"),
                             anchor="w").pack(anchor="w")
            return row

        # ── 界面自定义 ──
        ui_inner = group("ui_settings")

        # 主题
        r_theme = setting_row(ui_inner, self.t("theme"))
        app.combo_theme = ctk.CTkComboBox(r_theme,
                                          values=[self.t("theme_dark"), self.t("theme_light")],
                                          height=32, width=130, font=ctk.CTkFont(size=12),
                                          state="readonly", corner_radius=8,
                                          command=app._on_theme_changed)
        app.combo_theme.set(self.t("theme_dark") if app.config.get("theme","dark")=="dark"
                            else self.t("theme_light"))
        app.combo_theme.pack(side="right")

        # 语言
        r_lang = setting_row(ui_inner, self.t("language"))
        app.combo_lang = ctk.CTkComboBox(r_lang,
                                         values=[self.t("lang_cn"), self.t("lang_en")],
                                         height=32, width=130, font=ctk.CTkFont(size=12),
                                         state="readonly", corner_radius=8,
                                         command=app._on_lang_changed)
        app.combo_lang.set(self.t("lang_cn") if app.lang=="cn" else self.t("lang_en"))
        app.combo_lang.pack(side="right")

        # 强调色
        r_accent = setting_row(ui_inner, self.t("accent_color"))
        accent_frame = ctk.CTkFrame(r_accent, fg_color="transparent")
        accent_frame.pack(side="right")
        app._accent_btns = {}
        for name, color in ACCENT_PRESETS.items():
            is_active = color == Theme.accent()
            dot = ctk.CTkButton(accent_frame, text="", width=24, height=24,
                                corner_radius=12, fg_color=color, hover_color=color,
                                border_width=2 if is_active else 0,
                                border_color="#FFFFFF",
                                command=lambda c=color, n=name: app._on_accent_changed(c, n))
            dot.pack(side="left", padx=3)
            app._accent_btns[name] = dot

        # 自定义背景图
        r_bg = setting_row(ui_inner, self.t("custom_bg"))
        bg_frame = ctk.CTkFrame(r_bg, fg_color="transparent")
        bg_frame.pack(side="right")
        app.btn_choose_bg = ghost_btn(bg_frame, self.t("choose_image"),
                                      command=app._on_choose_bg, height=30, width=90)
        app.btn_choose_bg.pack(side="left", padx=(0, 6))
        app.btn_clear_bg = ghost_btn(bg_frame, self.t("clear_image"),
                                     command=app._on_clear_bg, height=30, width=70)
        app.btn_clear_bg.pack(side="left")

        # 背景透明度
        r_opacity = setting_row(ui_inner, self.t("opacity"))
        app.slider_opacity = ctk.CTkSlider(r_opacity, from_=0.3, to=1.0, width=160,
                                           command=app._on_opacity_changed,
                                           progress_color=(Theme.accent(), Theme.accent()))
        app.slider_opacity.set(app.config.get("bg_opacity", 1.0))
        app.slider_opacity.pack(side="right")

        # 紧凑模式
        r_compact = setting_row(ui_inner, self.t("compact_mode"), self.t("compact_mode_desc"))
        app.switch_compact = ctk.CTkSwitch(r_compact, text="",
                                           command=app._on_compact_toggle,
                                           progress_color=(Theme.accent(), Theme.accent()))
        app.switch_compact.pack(side="right")
        if app.config.get("compact_mode", False):
            app.switch_compact.select()

        # ── 游戏设置 ──
        game_inner = group("game_settings")

        # 下载源
        r_src = setting_row(game_inner, self.t("download_source"), self.t("download_source_desc"))
        app.combo_dl_source = ctk.CTkComboBox(r_src,
                                              values=[self.t("source_official"), self.t("source_bmclapi")],
                                              height=32, width=200, font=ctk.CTkFont(size=12),
                                              state="readonly", corner_radius=8,
                                              command=app._on_dl_source_changed)
        app.combo_dl_source.set(self.t("source_bmclapi") if app.download_source=="bmclapi"
                                else self.t("source_official"))
        app.combo_dl_source.pack(side="right")

        # 版本隔离
        r_iso = setting_row(game_inner, self.t("version_isolation"), self.t("version_isolation_desc"))
        app.switch_isolation = ctk.CTkSwitch(r_iso, text="",
                                             command=app._on_isolation_toggle,
                                             progress_color=(Theme.accent(), Theme.accent()))
        app.switch_isolation.pack(side="right")
        if app.version_isolation:
            app.switch_isolation.select()

        # 自动内存
        r_ram = setting_row(game_inner, self.t("auto_ram"), self.t("auto_ram_desc"))
        app.switch_auto_ram = ctk.CTkSwitch(r_ram, text="",
                                            command=app._on_auto_ram_toggle,
                                            progress_color=(Theme.accent(), Theme.accent()))
        app.switch_auto_ram.pack(side="right")
        if app.auto_ram:
            app.switch_auto_ram.select()

        if app.system_ram_gb > 0:
            ctk.CTkLabel(game_inner,
                         text=f"系统内存: {app.system_ram_gb:.1f} GB  |  推荐分配: {app.recommended_ram:.1f} GB",
                         font=ctk.CTkFont(size=11),
                         text_color=Theme.pair("text_muted")).pack(anchor="w", pady=(0, 4))

        # ── Java 设置 ──
        java_inner = group("java_settings")

        # 正版登录
        r_ms = setting_row(java_inner, self.t("ms_login"))
        ms_frame = ctk.CTkFrame(r_ms, fg_color="transparent")
        ms_frame.pack(side="right")
        app.btn_ms_login = flat_btn(ms_frame, self.t("ms_login"),
                                    command=app._microsoft_login,
                                    height=30, width=120, font_size=12)
        app.btn_ms_login.pack(side="left", padx=(0, 8))
        app.lbl_ms_status = ctk.CTkLabel(ms_frame, text=self.t("ms_login_soon"),
                                         font=ctk.CTkFont(size=11),
                                         text_color=Theme.pair("text_muted"))
        app.lbl_ms_status.pack(side="left")

        return page

    # ── 关于页 ──────────────────────────────────────────────────────────
    def _build_about(self):
        app = self.app
        page = ctk.CTkFrame(app.main_area, fg_color="transparent")
        px = 28

        app.lbl_ab_title = ctk.CTkLabel(page, text=self.t("about_title"),
                                        font=ctk.CTkFont(size=20, weight="bold"))
        app.lbl_ab_title.pack(pady=(22, 10), padx=px, anchor="w")

        c = card(page)
        c.pack(pady=(0, 10), padx=px, fill="both", expand=True)
        inner = ctk.CTkFrame(c, fg_color="transparent")
        inner.pack(pady=28, padx=28, fill="both", expand=True)

        # 大 Logo
        logo_f = ctk.CTkFrame(inner, fg_color="transparent")
        logo_f.pack(pady=(0, 20))
        ctk.CTkLabel(logo_f, text="MCL",
                     font=ctk.CTkFont(size=42, weight="bold"),
                     text_color=(Theme.accent(), Theme.accent())).pack()
        ctk.CTkLabel(logo_f, text="Launcher",
                     font=ctk.CTkFont(size=14),
                     text_color=Theme.pair("text_muted")).pack()

        separator(inner).pack(fill="x", pady=(0, 18))

        app.ab_info_labels = []
        info_items = [
            ("about_version", APP_VERSION),
            ("about_author",  AUTHOR_NAME),
            ("about_license", "MIT"),
        ]
        for key, val in info_items:
            row = ctk.CTkFrame(inner, fg_color="transparent")
            row.pack(fill="x", pady=5)
            lbl = ctk.CTkLabel(row, text=f"{self.t(key)}",
                               font=ctk.CTkFont(size=13),
                               text_color=Theme.pair("text_muted"),
                               width=80, anchor="w")
            lbl.pack(side="left")
            val_lbl = ctk.CTkLabel(row, text=val, font=ctk.CTkFont(size=13), anchor="w")
            val_lbl.pack(side="left")
            app.ab_info_labels.append((val_lbl, key, val))

        # GitHub
        gh_row = ctk.CTkFrame(inner, fg_color="transparent")
        gh_row.pack(fill="x", pady=5)
        ctk.CTkLabel(gh_row, text=self.t("about_github"),
                     font=ctk.CTkFont(size=13),
                     text_color=Theme.pair("text_muted"),
                     width=80, anchor="w").pack(side="left")
        app.lbl_ab_github = ctk.CTkButton(gh_row, text=GITHUB_URL,
                                          font=ctk.CTkFont(size=13, underline=True),
                                          fg_color="transparent",
                                          hover_color=Theme.pair("hover"),
                                          text_color=("#1565C0", "#5B9BD5"),
                                          anchor="w",
                                          command=lambda: webbrowser.open(GITHUB_URL))
        app.lbl_ab_github.pack(side="left")

        separator(inner).pack(fill="x", pady=(14, 10))

        # 更新
        upd_row = ctk.CTkFrame(inner, fg_color="transparent")
        upd_row.pack(fill="x", pady=4)
        app.lbl_update_status = ctk.CTkLabel(upd_row, text=self.t("update_checking"),
                                             font=ctk.CTkFont(size=12),
                                             text_color=Theme.pair("text_muted"))
        app.lbl_update_status.pack(side="left")
        app.btn_check_update = ghost_btn(upd_row, "↻", width=32, height=28, font_size=16,
                                         command=lambda: UpdateChecker.check(app._on_update_result))
        app.btn_check_update.pack(side="left", padx=8)

        app.lbl_ab_hint = ctk.CTkLabel(inner, text=self.t("hint_copyright"),
                                       font=ctk.CTkFont(size=11),
                                       text_color=Theme.pair("text_muted"))
        app.lbl_ab_hint.pack(pady=(16, 4))

        return page
