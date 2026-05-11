# -*- coding: utf-8 -*-
"""
MCL Launcher — 五页 UI 构建器：启动 / 下载 / 联机 / 设置 / 关于
"""
import os
import webbrowser
import customtkinter as ctk
from tkinter import messagebox

from ..constants import APP_VERSION, AUTHOR_NAME, GITHUB_URL
from ..backend import LauncherBackend
from ..update_checker import UpdateChecker
from .widgets import add_hover_animation, add_click_feedback


class PageBuilder:
    """负责创建所有页面的 UI 布局，将控件引用挂到 parent (LauncherGUI) 上"""

    def __init__(self, app):
        self.app = app  # LauncherGUI 实例

    @property
    def t(self):
        return self.app._

    def build_all(self):
        pages = {}
        pages["launch"] = self._build_launch()
        pages["download"] = self._build_download()
        pages["multiplayer"] = self._build_multiplayer()
        pages["settings"] = self._build_settings()
        pages["about"] = self._build_about()
        return pages

    # ================================================================
    #  启动页
    # ================================================================
    def _build_launch(self):
        app = self.app
        page = ctk.CTkFrame(app.main_area, fg_color="transparent")
        padx = 30

        # ---- 顶部栏：标题 + 启动按钮 ----
        top_bar = ctk.CTkFrame(page, fg_color="transparent")
        top_bar.pack(pady=(20, 8), padx=padx, fill="x")

        title_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        title_frame.pack(side="left")
        ctk.CTkLabel(title_frame, text="MCL Launcher",
                     font=ctk.CTkFont(size=22, weight="bold")).pack(anchor="w")
        app.lbl_login_status = ctk.CTkLabel(title_frame, text="",
                                            font=ctk.CTkFont(size=12), text_color="gray55")
        app.lbl_login_status.pack(anchor="w", pady=(2, 0))

        # 绿色启动按钮 — 右上角显眼位置
        app.btn_launch = ctk.CTkButton(top_bar, text=self.t("launch_game"), height=46, width=190,
                                       font=ctk.CTkFont(size=16, weight="bold"),
                                       fg_color="#4CAF50", hover_color="#388E3C",
                                       border_color="#81C784", border_width=2,
                                       corner_radius=10, command=app._on_launch)
        app.btn_launch.pack(side="right")
        add_hover_animation(app.btn_launch, "#4CAF50", "#388E3C")
        add_click_feedback(app.btn_launch)

        # ---- 卡片内容 ----
        card = ctk.CTkFrame(page, corner_radius=14)
        card.pack(pady=(5, 8), padx=padx, fill="both", expand=True)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(pady=(15, 5), padx=25, fill="both", expand=True)

        fh, lw = 34, 68

        # ---- 用户名 ----
        r1 = ctk.CTkFrame(inner, fg_color="transparent")
        r1.pack(fill="x", pady=(0, 7))
        app.lbl_user_text = ctk.CTkLabel(r1, text=self.t("username"), width=lw, anchor="w",
                                         font=ctk.CTkFont(size=13))
        app.lbl_user_text.pack(side="left")
        app.entry_user = ctk.CTkEntry(r1, height=fh, font=ctk.CTkFont(size=13),
                                      placeholder_text=self.t("username_placeholder"))
        app.entry_user.pack(side="left", fill="x", expand=True, padx=(5, 0))
        app.entry_user.insert(0, os.environ.get("USERNAME", "Player"))

        # ---- 版本 ----
        r2 = ctk.CTkFrame(inner, fg_color="transparent")
        r2.pack(fill="x", pady=(0, 7))
        app.lbl_version_text = ctk.CTkLabel(r2, text=self.t("game_version"), width=lw, anchor="w",
                                            font=ctk.CTkFont(size=13))
        app.lbl_version_text.pack(side="left")
        app.combo_version = ctk.CTkComboBox(r2, values=[self.t("loading")], height=fh,
                                            font=ctk.CTkFont(size=13), state="readonly",
                                            command=app._on_version_changed)
        app.combo_version.set(self.t("loading"))
        app.combo_version.pack(side="left", fill="x", expand=True, padx=(5, 8))
        app.btn_refresh = ctk.CTkButton(r2, text=self.t("refresh"), width=50, height=fh,
                                        font=ctk.CTkFont(size=12), command=app._refresh_versions)
        app.btn_refresh.pack(side="right")
        add_hover_animation(app.btn_refresh)

        # ---- Java ----
        r3 = ctk.CTkFrame(inner, fg_color="transparent")
        r3.pack(fill="x", pady=(0, 7))
        app.lbl_java_text = ctk.CTkLabel(r3, text=self.t("java_env"), width=lw, anchor="w",
                                         font=ctk.CTkFont(size=13))
        app.lbl_java_text.pack(side="left")
        app.combo_java = ctk.CTkComboBox(r3, values=[self.t("loading")], height=fh,
                                         font=ctk.CTkFont(size=13), state="readonly")
        app.combo_java.set(self.t("loading"))
        app.combo_java.pack(side="left", fill="x", expand=True, padx=(5, 8))
        app.btn_scan_java = ctk.CTkButton(r3, text=self.t("scan"), width=50, height=fh,
                                          font=ctk.CTkFont(size=12), command=app._scan_java)
        app.btn_scan_java.pack(side="right")
        add_hover_animation(app.btn_scan_java)

        # Java 提示（可点击）
        app.lbl_java_hint = ctk.CTkButton(inner, text="", font=ctk.CTkFont(size=11),
                                          fg_color="transparent", hover_color=("gray90", "gray20"),
                                          anchor="w", command=app._on_java_hint_click)
        app.lbl_java_hint.pack(anchor="w", padx=(lw + 5, 0), pady=(0, 7))

        # ---- 内存 ----
        r4 = ctk.CTkFrame(inner, fg_color="transparent")
        r4.pack(fill="x", pady=(0, 7))
        app.lbl_ram_text = ctk.CTkLabel(r4, text=self.t("ram"), width=lw, anchor="w",
                                        font=ctk.CTkFont(size=13))
        app.lbl_ram_text.pack(side="left")
        app.combo_ram = ctk.CTkComboBox(r4, values=["1 GB", "2 GB", "4 GB", "6 GB", "8 GB", "12 GB", "16 GB"],
                                        height=fh, font=ctk.CTkFont(size=13), state="readonly")
        app.combo_ram.set("4 GB")
        app.combo_ram.pack(side="left", fill="x", expand=True, padx=(5, 0))

        # ---- 安装状态 ----
        app.lbl_install_status = ctk.CTkLabel(inner, text="", font=ctk.CTkFont(size=12), text_color="gray60")
        app.lbl_install_status.pack(anchor="w", padx=(lw + 5, 0), pady=(3, 0))

        # ---- 进度条 ----
        app.progress = ctk.CTkProgressBar(inner, height=14, corner_radius=8)
        app.progress.pack(fill="x", pady=(10, 3))
        app.progress.set(0)
        app.lbl_status = ctk.CTkLabel(inner, text=self.t("status_ready"),
                                      font=ctk.CTkFont(size=12), text_color="gray55")
        app.lbl_status.pack()

        # ---- 日志 ----
        app.lbl_log_text = ctk.CTkLabel(inner, text=self.t("log_title"), anchor="w",
                                        font=ctk.CTkFont(size=12))
        app.lbl_log_text.pack(anchor="w", pady=(8, 4))
        app.txt_log = ctk.CTkTextbox(inner, height=90, font=("Consolas", 11), wrap="word", corner_radius=10)
        app.txt_log.pack(fill="both", expand=True)
        app.txt_log.configure(state="disabled")

        # ---- 底部提示 ----
        app.lbl_hint = ctk.CTkLabel(inner, text=self.t("hint_offline"),
                                    font=ctk.CTkFont(size=11), text_color="gray55")
        app.lbl_hint.pack(pady=(6, 3))

        return page

    # ================================================================
    #  下载页
    # ================================================================
    def _build_download(self):
        app = self.app
        page = ctk.CTkFrame(app.main_area, fg_color="transparent")
        padx = 30

        ctk.CTkFrame(page, fg_color="transparent").pack(pady=(20, 8), padx=padx, fill="x")
        app.lbl_dl_title = ctk.CTkLabel(page, text=self.t("download_page"),
                                        font=ctk.CTkFont(size=20, weight="bold"))
        app.lbl_dl_title.pack(pady=(20, 12), padx=padx, anchor="w")

        card = ctk.CTkFrame(page, corner_radius=14)
        card.pack(pady=(5, 8), padx=padx, fill="both", expand=True)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(pady=18, padx=25, fill="both", expand=True)

        app.lbl_dl_ver_text = ctk.CTkLabel(inner, text=self.t("download_versions"),
                                           font=ctk.CTkFont(size=14, weight="bold"))
        app.lbl_dl_ver_text.pack(anchor="w", pady=(0, 10))

        app.dl_version_list = ctk.CTkScrollableFrame(inner, height=280)
        app.dl_version_list.pack(fill="both", expand=True, pady=(0, 15))

        app.dl_checkboxes = {}
        app._populate_download_versions()

        app.btn_dl_install = ctk.CTkButton(inner, text=self.t("download_install"), height=40,
                                           font=ctk.CTkFont(size=14),
                                           command=app._on_download_selected)
        app.btn_dl_install.pack(fill="x")
        add_hover_animation(app.btn_dl_install)

        return page

    # ================================================================
    #  联机页
    # ================================================================
    def _build_multiplayer(self):
        app = self.app
        page = ctk.CTkFrame(app.main_area, fg_color="transparent")
        padx = 30

        ctk.CTkFrame(page, fg_color="transparent").pack(pady=(20, 8), padx=padx, fill="x")
        app.lbl_mp_title = ctk.CTkLabel(page, text=self.t("multiplayer"),
                                        font=ctk.CTkFont(size=20, weight="bold"))
        app.lbl_mp_title.pack(pady=(20, 25), padx=padx, anchor="w")

        card = ctk.CTkFrame(page, corner_radius=14)
        card.pack(pady=(5, 8), padx=padx, fill="both", expand=True)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(pady=50, padx=40, fill="both", expand=True)

        ctk.CTkLabel(inner, text="🌐", font=ctk.CTkFont(size=48)).pack(pady=(20, 10))
        app.lbl_mp_subtitle = ctk.CTkLabel(inner, text="Multiplayer",
                                           font=ctk.CTkFont(size=18, weight="bold"))
        app.lbl_mp_subtitle.pack(pady=(0, 25))

        app.btn_create_room = ctk.CTkButton(inner, text=self.t("creating_room"), height=44,
                                            font=ctk.CTkFont(size=14),
                                            command=lambda: messagebox.showinfo("MCL", self.t("multiplayer_wip")))
        app.btn_create_room.pack(fill="x", pady=(0, 10))
        add_hover_animation(app.btn_create_room)

        app.btn_join_room = ctk.CTkButton(inner, text=self.t("joining_room"), height=44,
                                          font=ctk.CTkFont(size=14),
                                          command=lambda: messagebox.showinfo("MCL", self.t("multiplayer_wip")))
        app.btn_join_room.pack(fill="x")
        add_hover_animation(app.btn_join_room)

        return page

    # ================================================================
    #  设置页
    # ================================================================
    def _build_settings(self):
        app = self.app
        page = ctk.CTkFrame(app.main_area, fg_color="transparent")
        padx = 30

        ctk.CTkFrame(page, fg_color="transparent").pack(pady=(20, 8), padx=padx, fill="x")
        app.lbl_set_title = ctk.CTkLabel(page, text=self.t("settings"),
                                         font=ctk.CTkFont(size=20, weight="bold"))
        app.lbl_set_title.pack(pady=(20, 12), padx=padx, anchor="w")

        card = ctk.CTkFrame(page, corner_radius=14)
        card.pack(pady=(5, 8), padx=padx, fill="both", expand=True)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(pady=20, padx=30, fill="both", expand=True)

        lw_s = 80

        # --- 主题 ---
        r1 = ctk.CTkFrame(inner, fg_color="transparent")
        r1.pack(fill="x", pady=(8, 10))
        app.lbl_theme_text = ctk.CTkLabel(r1, text=self.t("theme"), width=lw_s, anchor="w",
                                          font=ctk.CTkFont(size=14))
        app.lbl_theme_text.pack(side="left")
        app.combo_theme = ctk.CTkComboBox(r1, values=[self.t("theme_dark"), self.t("theme_light")],
                                          height=34, font=ctk.CTkFont(size=13), state="readonly",
                                          command=app._on_theme_changed)
        app.combo_theme.set(self.t("theme_dark") if app.config.get("theme", "dark") == "dark" else self.t("theme_light"))
        app.combo_theme.pack(side="left", padx=(8, 0))

        # --- 语言 ---
        r2 = ctk.CTkFrame(inner, fg_color="transparent")
        r2.pack(fill="x", pady=(0, 10))
        app.lbl_lang_text = ctk.CTkLabel(r2, text=self.t("language"), width=lw_s, anchor="w",
                                         font=ctk.CTkFont(size=14))
        app.lbl_lang_text.pack(side="left")
        app.combo_lang = ctk.CTkComboBox(r2, values=[self.t("lang_cn"), self.t("lang_en")],
                                         height=34, font=ctk.CTkFont(size=13), state="readonly",
                                         command=app._on_lang_changed)
        app.combo_lang.set(self.t("lang_cn") if app.lang == "cn" else self.t("lang_en"))
        app.combo_lang.pack(side="left", padx=(8, 0))

        ctk.CTkFrame(inner, height=1, fg_color=("gray75", "gray30")).pack(fill="x", pady=12)

        # --- 版本隔离 ---
        iso_row = ctk.CTkFrame(inner, fg_color="transparent")
        iso_row.pack(fill="x", pady=(0, 5))
        app.lbl_isolation_text = ctk.CTkLabel(iso_row, text=self.t("version_isolation"), width=lw_s,
                                              anchor="w", font=ctk.CTkFont(size=14))
        app.lbl_isolation_text.pack(side="left")
        app.switch_isolation = ctk.CTkButton(iso_row, text="ON" if app.version_isolation else "OFF",
                                             width=50, height=30, font=ctk.CTkFont(size=12),
                                             command=app._on_isolation_toggle)
        app.switch_isolation.pack(side="left", padx=(8, 10))
        app.lbl_isolation_desc = ctk.CTkLabel(iso_row, text=self.t("version_isolation_desc"),
                                              font=ctk.CTkFont(size=12), text_color="gray55")
        app.lbl_isolation_desc.pack(side="left")

        # --- 自动内存 ---
        ram_row = ctk.CTkFrame(inner, fg_color="transparent")
        ram_row.pack(fill="x", pady=(0, 8))
        app.lbl_auto_ram_text = ctk.CTkLabel(ram_row, text=self.t("auto_ram"), width=lw_s,
                                             anchor="w", font=ctk.CTkFont(size=14))
        app.lbl_auto_ram_text.pack(side="left")
        app.switch_auto_ram = ctk.CTkButton(ram_row, text="ON" if app.auto_ram else "OFF",
                                            width=50, height=30, font=ctk.CTkFont(size=12),
                                            command=app._on_auto_ram_toggle)
        app.switch_auto_ram.pack(side="left", padx=(8, 10))
        app.lbl_auto_ram_desc = ctk.CTkLabel(ram_row, text=self.t("auto_ram_desc"),
                                             font=ctk.CTkFont(size=12), text_color="gray55")
        app.lbl_auto_ram_desc.pack(side="left")

        if app.system_ram_gb > 0:
            ram_info = f"系统总内存: {app.system_ram_gb:.1f} GB | 推荐分配: {app.recommended_ram:.1f} GB"
            app.lbl_ram_info = ctk.CTkLabel(inner, text=ram_info, font=ctk.CTkFont(size=11), text_color="gray55")
            app.lbl_ram_info.pack(anchor="w", padx=(lw_s + 60, 0), pady=(0, 5))

        ctk.CTkFrame(inner, height=1, fg_color=("gray75", "gray30")).pack(fill="x", pady=12)

        # --- 正版登录 ---
        r3 = ctk.CTkFrame(inner, fg_color="transparent")
        r3.pack(fill="x", pady=(0, 5))
        ctk.CTkLabel(r3, text="🔑", font=ctk.CTkFont(size=16)).pack(side="left", padx=(0, 10))
        app.btn_ms_login = ctk.CTkButton(r3, text=self.t("ms_login"), width=140, height=36,
                                         font=ctk.CTkFont(size=13),
                                         command=app._microsoft_login)
        app.btn_ms_login.pack(side="left")
        add_hover_animation(app.btn_ms_login)
        app.lbl_ms_status = ctk.CTkLabel(r3, text=self.t("ms_login_soon"),
                                         font=ctk.CTkFont(size=12), text_color="gray55")
        app.lbl_ms_status.pack(side="left", padx=15)

        return page

    # ================================================================
    #  关于页
    # ================================================================
    def _build_about(self):
        app = self.app
        page = ctk.CTkFrame(app.main_area, fg_color="transparent")
        padx = 30

        app.lbl_ab_title = ctk.CTkLabel(page, text=self.t("about_title"),
                                        font=ctk.CTkFont(size=20, weight="bold"))
        app.lbl_ab_title.pack(pady=(20, 12), padx=padx, anchor="w")

        card = ctk.CTkFrame(page, corner_radius=14)
        card.pack(pady=(5, 8), padx=padx, fill="both", expand=True)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(pady=30, padx=35, fill="both", expand=True)

        app.ab_info_labels = []
        info_items = [
            ("📌", "MCL Launcher", None),
            ("📌", "about_version", APP_VERSION),
            ("👤", "about_author", AUTHOR_NAME),
            ("📄", "about_license", "MIT"),
        ]
        for icon, key, val in info_items:
            row = ctk.CTkFrame(inner, fg_color="transparent")
            row.pack(fill="x", pady=6)
            ctk.CTkLabel(row, text=icon, font=ctk.CTkFont(size=16)).pack(side="left", padx=(0, 10))
            text = f"{self.t(key)}: {val}" if key else "MCL Launcher"
            lbl = ctk.CTkLabel(row, text=text, font=ctk.CTkFont(size=14))
            lbl.pack(side="left")
            if key:
                app.ab_info_labels.append((lbl, key, val))

        # GitHub 链接
        link_row = ctk.CTkFrame(inner, fg_color="transparent")
        link_row.pack(fill="x", pady=6)
        ctk.CTkLabel(link_row, text="🔗", font=ctk.CTkFont(size=16)).pack(side="left", padx=(0, 10))
        app.lbl_ab_github = ctk.CTkButton(link_row, text=f"GitHub: {GITHUB_URL}",
                                          font=ctk.CTkFont(size=13, underline=True),
                                          fg_color="transparent", hover_color=("gray80", "gray25"),
                                          text_color=("#2050a0", "#6090d0"),
                                          command=lambda: webbrowser.open(GITHUB_URL))
        app.lbl_ab_github.pack(side="left")

        # 更新状态
        update_row = ctk.CTkFrame(inner, fg_color="transparent")
        update_row.pack(fill="x", pady=6)
        ctk.CTkLabel(update_row, text="🔄", font=ctk.CTkFont(size=16)).pack(side="left", padx=(0, 10))
        app.lbl_update_status = ctk.CTkLabel(update_row, text=self.t("update_checking"),
                                             font=ctk.CTkFont(size=13), text_color="gray55")
        app.lbl_update_status.pack(side="left")
        app.btn_check_update = ctk.CTkButton(update_row, text="↻", width=36, height=28,
                                             font=ctk.CTkFont(size=14),
                                             command=lambda: UpdateChecker.check(app._on_update_result))
        app.btn_check_update.pack(side="left", padx=10)

        app.lbl_ab_hint = ctk.CTkLabel(inner, text=self.t("hint_copyright"),
                                       font=ctk.CTkFont(size=12), text_color="gray55")
        app.lbl_ab_hint.pack(pady=(25, 10))

        return page
