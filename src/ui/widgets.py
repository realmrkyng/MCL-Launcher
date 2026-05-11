# -*- coding: utf-8 -*-
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

    ctk.CTkLabel(sidebar, text="MCL v1.1",
                 font=ctk.CTkFont(size=10), text_color="gray50").pack(side="bottom", pady=12)

    return sidebar, nav_btns


def _interpolate_hex(c1, c2, t):
    c1, c2 = c1.lstrip("#"), c2.lstrip("#")
    r1, g1, b1 = int(c1[0:2], 16), int(c1[2:4], 16), int(c1[4:6], 16)
    r2, g2, b2 = int(c2[0:2], 16), int(c2[2:4], 16), int(c2[4:6], 16)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def add_hover_animation(btn, normal_color=None, hover_color=None, steps=10, interval=20):
    """为 CTkButton 添加平滑 hover 颜色过渡 (0.2s) + 边框微抬"""
    if normal_color is None:
        normal_color = btn.cget("fg_color")
    if hover_color is None:
        hover_color = btn.cget("hover_color")

    if isinstance(normal_color, tuple):
        idx = 1 if ctk.get_appearance_mode() == "Dark" else 0
        normal_color = normal_color[idx]
    if isinstance(hover_color, tuple):
        idx = 1 if ctk.get_appearance_mode() == "Dark" else 0
        hover_color = hover_color[idx]

    if normal_color == "transparent" or hover_color == "transparent":
        return

    base_bw = btn.cget("border_width")

    btn.configure(hover=False)
    timer = [None]

    def cancel():
        if timer[0] is not None:
            btn.after_cancel(timer[0])
            timer[0] = None

    def animate_enter(step=0):
        cancel()
        if step <= steps:
            t = step / steps
            btn.configure(
                fg_color=_interpolate_hex(normal_color, hover_color, t),
                border_width=base_bw + int(2 * t))
            timer[0] = btn.after(interval, lambda: animate_enter(step + 1))

    def animate_leave(step=0):
        cancel()
        if step <= steps:
            t = step / steps
            btn.configure(
                fg_color=_interpolate_hex(hover_color, normal_color, t),
                border_width=base_bw + int(2 * (1 - t)))
            timer[0] = btn.after(interval, lambda: animate_leave(step + 1))

    btn.bind("<Enter>", lambda e: animate_enter(), add="+")
    btn.bind("<Leave>", lambda e: animate_leave(), add="+")


def add_click_feedback(btn, steps=4, interval=20):
    """为按钮添加点击颜色反馈：按下变深，释放恢复（不影响布局）"""
    normal = btn.cget("fg_color")
    hover = btn.cget("hover_color")
    if isinstance(normal, tuple):
        idx = 1 if ctk.get_appearance_mode() == "Dark" else 0
        normal = normal[idx]
    if isinstance(hover, tuple):
        idx = 1 if ctk.get_appearance_mode() == "Dark" else 0
        hover = hover[idx]
    if normal == "transparent" or hover == "transparent":
        return

    timer = [None]

    def cancel():
        if timer[0] is not None:
            btn.after_cancel(timer[0])
            timer[0] = None

    def animate_press(step=0):
        cancel()
        if step <= steps:
            t = step / steps
            btn.configure(fg_color=_interpolate_hex(normal, hover, t))
            timer[0] = btn.after(interval, lambda: animate_press(step + 1))

    def animate_release(step=0):
        cancel()
        if step <= steps:
            t = step / steps
            btn.configure(fg_color=_interpolate_hex(hover, normal, t))
            timer[0] = btn.after(interval, lambda: animate_release(step + 1))

    btn.bind("<ButtonPress>", lambda e: animate_press(), add="+")
    btn.bind("<ButtonRelease>", lambda e: animate_release(), add="+")
