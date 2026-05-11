"""
MCL Launcher — 可复用 UI 组件：顶部正版横幅、侧边栏导航
"""
import webbrowser
import customtkinter as ctk

from ..constants import MINECRAFT_STORE_URL, GITHUB_URL


def build_banner(root, t):
    """创建顶部正版支持横幅，点击跳转 Minecraft 官网"""
    banner_bg = ("#E3F2FD", "#1A2733")
    banner_frame = ctk.CTkFrame(root, height=36, corner_radius=0, fg_color=banner_bg)
    banner_frame.pack(side="top", fill="x")
    banner_frame.pack_propagate(False)

    lbl = ctk.CTkButton(banner_frame, text=t("banner_text"),
                        fg_color="transparent", hover_color=banner_bg,
                        font=ctk.CTkFont(size=12),
                        text_color=("#1565C0", "#64B5F6"),
                        anchor="center",
                        command=lambda: webbrowser.open(MINECRAFT_STORE_URL))
    lbl.pack(fill="both", expand=True, padx=12, pady=2)
    return banner_frame, lbl


def build_sidebar(root, t, on_navigate):
    """创建左侧 160px 导航栏，返回 (sidebar_frame, nav_buttons_dict)"""
    sidebar = ctk.CTkFrame(root, width=160, corner_radius=0, fg_color=("gray85", "gray13"))
    sidebar.pack(side="left", fill="y")
    sidebar.pack_propagate(False)

    # Logo
    ctk.CTkLabel(sidebar, text="MCL", font=ctk.CTkFont(size=22, weight="bold")
                 ).pack(pady=(25, 5))
    ctk.CTkLabel(sidebar, text="Launcher",
                 font=ctk.CTkFont(size=11), text_color="gray55").pack(pady=(0, 25))

    ctk.CTkFrame(sidebar, height=1, fg_color=("gray70", "gray30")).pack(fill="x", padx=20)

    # 导航按钮
    nav_btns = {}
    nav_items = [
        ("launch", "🚀"),
        ("download", "📥"),
        ("multiplayer", "🌐"),
        ("settings", "⚙"),
        ("about", "ℹ"),
    ]
    btn_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
    btn_frame.pack(pady=(15, 0), padx=12, fill="x")

    for key, icon in nav_items:
        btn = ctk.CTkButton(btn_frame, text=f"  {icon}  {t(key)}",
                            anchor="w", height=38, fg_color="transparent",
                            text_color=("gray40", "gray70"),
                            hover_color=("gray75", "gray25"),
                            corner_radius=8,
                            font=ctk.CTkFont(size=13),
                            command=lambda k=key: on_navigate(k))
        btn.pack(fill="x", pady=2)
        nav_btns[key] = btn

    ctk.CTkLabel(sidebar, text="MCL v1.0",
                 font=ctk.CTkFont(size=10), text_color="gray50").pack(side="bottom", pady=12)

    return sidebar, nav_btns
