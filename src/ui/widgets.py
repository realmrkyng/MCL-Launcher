# -*- coding: utf-8 -*-
"""
MCL Launcher — 可复用 UI 组件 & 丝滑动画引擎
"""
import time
import math
import webbrowser
import customtkinter as ctk

from ..constants import MINECRAFT_STORE_URL, GITHUB_URL

# ======================================================================
#  主题颜色常量（深色模式）
# ======================================================================
DARK_BG      = "#1E1E1E"
SIDEBAR_BG   = "#252526"
CARD_BG      = "#2D2D2D"
ACCENT       = "#FF8C00"
TEXT_PRIMARY = "#CCCCCC"
TEXT_MUTED   = "#888888"
NAV_HOVER    = "#3A3A3A"
NAV_ACTIVE   = "#2A2A2A"


# ======================================================================
#  动画引擎：基于时间的缓动补间（取代等步长 after 链）
# ======================================================================
#   * 所有补间按"真实时间"推进，不会因 tk 事件抖动被拉长
#   * 支持多种缓动：ease_out_cubic / ease_in_out_cubic / ease_out_quint
#   * 约 60 FPS（16 ms 间隔）+ 最后一帧强制对齐到终点，避免尾部抖动
# ----------------------------------------------------------------------

_FRAME_MS = 16  # ~60 FPS


def ease_out_cubic(t):
    return 1 - (1 - t) ** 3


def ease_in_out_cubic(t):
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def ease_out_quint(t):
    return 1 - (1 - t) ** 5


def ease_out_expo(t):
    if t >= 1:
        return 1.0
    return 1 - math.pow(2, -10 * t)


class Tween:
    """基于时间的补间动画，可取消 / 可替换"""

    def __init__(self, widget, duration_ms, on_update, easing=ease_out_cubic, on_complete=None):
        self.widget = widget
        self.duration = max(1, duration_ms)
        self.on_update = on_update
        self.easing = easing
        self.on_complete = on_complete
        self.start_time = time.perf_counter()
        self.cancelled = False
        self._after_id = None
        self._tick()

    def cancel(self):
        self.cancelled = True
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _tick(self):
        if self.cancelled:
            return
        elapsed = (time.perf_counter() - self.start_time) * 1000
        t = min(1.0, elapsed / self.duration)
        eased = self.easing(t)
        try:
            self.on_update(eased)
        except Exception:
            self.cancel()
            return
        if t >= 1.0:
            if self.on_complete:
                try:
                    self.on_complete()
                except Exception:
                    pass
            return
        try:
            self._after_id = self.widget.after(_FRAME_MS, self._tick)
        except Exception:
            pass


# ======================================================================
#  顶部正版横幅
# ======================================================================
def build_banner(root, t):
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


# ======================================================================
#  侧边栏导航
# ======================================================================
def build_sidebar(root, t, on_navigate):
    sidebar = ctk.CTkFrame(root, width=160, corner_radius=0,
                           fg_color=("gray88", SIDEBAR_BG))
    sidebar.pack(side="left", fill="y")
    sidebar.pack_propagate(False)

    ctk.CTkLabel(sidebar, text="MCL",
                 font=ctk.CTkFont(size=22, weight="bold"),
                 text_color=(ACCENT, ACCENT)).pack(pady=(25, 5))
    ctk.CTkLabel(sidebar, text="Launcher",
                 font=ctk.CTkFont(size=11),
                 text_color=("gray55", TEXT_MUTED)).pack(pady=(0, 25))

    ctk.CTkFrame(sidebar, height=1,
                 fg_color=("gray75", "#3A3A3A")).pack(fill="x", padx=20)

    nav_btns = {}
    nav_indicators = {}
    nav_items = [
        ("launch",      "🏠"),
        ("download",    "📥"),
        ("multiplayer", "🔌"),
        ("settings",    "⚙️"),
        ("about",       "ℹ️"),
    ]
    btn_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
    btn_frame.pack(pady=(15, 0), padx=0, fill="x")

    for key, icon in nav_items:
        row = ctk.CTkFrame(btn_frame, fg_color="transparent", height=42)
        row.pack(fill="x", pady=2)
        row.pack_propagate(False)

        # 左侧橙色指示条（默认透明）
        indicator = ctk.CTkFrame(row, width=3, corner_radius=2,
                                 fg_color="transparent")
        indicator.pack(side="left", fill="y", padx=(4, 0))

        btn = ctk.CTkButton(row, text=f"  {icon}  {t(key)}",
                            anchor="w", height=38,
                            fg_color="transparent",
                            text_color=("gray40", TEXT_MUTED),
                            hover_color=("gray80", NAV_HOVER),
                            corner_radius=8,
                            font=ctk.CTkFont(size=13),
                            command=lambda k=key: on_navigate(k))
        btn.pack(side="left", fill="x", expand=True, padx=(2, 6))
        nav_btns[key] = btn
        nav_indicators[key] = indicator

    ctk.CTkLabel(sidebar, text="MCL v1.1",
                 font=ctk.CTkFont(size=10),
                 text_color=("gray55", TEXT_MUTED)).pack(side="bottom", pady=12)

    return sidebar, nav_btns, nav_indicators


# ======================================================================
#  颜色插值
# ======================================================================
def _hex_to_rgb(h):
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _interpolate_hex(c1, c2, t):
    r1, g1, b1 = _hex_to_rgb(c1)
    r2, g2, b2 = _hex_to_rgb(c2)
    r = int(round(r1 + (r2 - r1) * t))
    g = int(round(g1 + (g2 - g1) * t))
    b = int(round(b1 + (b2 - b1) * t))
    return f"#{r:02x}{g:02x}{b:02x}"


def _resolve_color(c):
    """把 ('light','dark') 或 单色 转成当前模式下的 hex"""
    if isinstance(c, (tuple, list)):
        idx = 1 if ctk.get_appearance_mode() == "Dark" else 0
        return c[idx]
    return c


# ======================================================================
#  按钮 hover / 点击反馈动画（时间驱动，丝滑）
# ======================================================================
def add_hover_animation(btn, normal_color=None, hover_color=None, duration_ms=180):
    """hover 时颜色 + 边框抬起补间（ease-out-cubic）"""
    if normal_color is None:
        normal_color = btn.cget("fg_color")
    if hover_color is None:
        hover_color = btn.cget("hover_color")

    normal_color = _resolve_color(normal_color)
    hover_color = _resolve_color(hover_color)
    if normal_color == "transparent" or hover_color == "transparent":
        return

    try:
        base_bw = int(btn.cget("border_width"))
    except Exception:
        base_bw = 0

    btn.configure(hover=False)
    state = {"tween": None, "progress": 0.0}  # progress: 0=normal, 1=hover

    def _update(target):
        def _do(eased_t):
            p0 = state["progress"]
            p = p0 + (target - p0) * eased_t
            btn.configure(
                fg_color=_interpolate_hex(normal_color, hover_color, p),
                border_width=base_bw + int(round(2 * p)))
            state["_current_p"] = p

        def _done():
            state["progress"] = target
            btn.configure(
                fg_color=_interpolate_hex(normal_color, hover_color, target),
                border_width=base_bw + int(round(2 * target)))

        if state["tween"]:
            state["tween"].cancel()
        state["tween"] = Tween(btn, duration_ms, _do, ease_out_cubic, _done)

    btn.bind("<Enter>", lambda e: _update(1.0), add="+")
    btn.bind("<Leave>", lambda e: _update(0.0), add="+")


def add_click_feedback(btn, duration_ms=120):
    """按下/释放时短促的颜色脉冲（ease-out-quint）"""
    normal = _resolve_color(btn.cget("fg_color"))
    hover = _resolve_color(btn.cget("hover_color"))
    if normal == "transparent" or hover == "transparent":
        return

    state = {"tween": None}

    def _run(start, end):
        if state["tween"]:
            state["tween"].cancel()

        def _do(t):
            btn.configure(fg_color=_interpolate_hex(start, end, t))

        def _done():
            btn.configure(fg_color=end)

        state["tween"] = Tween(btn, duration_ms, _do, ease_out_quint, _done)

    btn.bind("<ButtonPress>", lambda e: _run(normal, hover), add="+")
    btn.bind("<ButtonRelease>", lambda e: _run(hover, normal), add="+")
