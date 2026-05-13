# -*- coding: utf-8 -*-
"""
MCL Launcher v1.2 — 可复用 UI 组件 & 动画引擎
"""
import time
import math
import webbrowser
import customtkinter as ctk

from ..constants import MINECRAFT_STORE_URL
from ..theme import Theme

_FRAME_MS = 16


def ease_out_cubic(t):   return 1 - (1 - t) ** 3
def ease_out_quint(t):   return 1 - (1 - t) ** 5
def ease_in_out(t):      return 4*t**3 if t < 0.5 else 1 - (-2*t+2)**3/2


class Tween:
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
        if self._after_id:
            try: self.widget.after_cancel(self._after_id)
            except Exception: pass
            self._after_id = None

    def _tick(self):
        if self.cancelled: return
        elapsed = (time.perf_counter() - self.start_time) * 1000
        t = min(1.0, elapsed / self.duration)
        try: self.on_update(self.easing(t))
        except Exception: self.cancel(); return
        if t >= 1.0:
            if self.on_complete:
                try: self.on_complete()
                except Exception: pass
            return
        try: self._after_id = self.widget.after(_FRAME_MS, self._tick)
        except Exception: pass


def _hex_to_rgb(h):
    h = h.lstrip("#")
    return int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)

def _lerp_hex(c1, c2, t):
    r1,g1,b1 = _hex_to_rgb(c1); r2,g2,b2 = _hex_to_rgb(c2)
    return f"#{int(r1+(r2-r1)*t):02x}{int(g1+(g2-g1)*t):02x}{int(b1+(b2-b1)*t):02x}"


def hover_btn(btn, normal=None, hover_color=None, dur=160):
    """给按钮添加平滑 hover 颜色过渡"""
    n = normal or btn.cget("fg_color")
    h = hover_color or btn.cget("hover_color")
    if isinstance(n, (tuple,list)): n = n[1] if str(ctk.get_appearance_mode()).lower() == "dark" else n[0]
    if isinstance(h, (tuple,list)): h = h[1] if str(ctk.get_appearance_mode()).lower() == "dark" else h[0]
    if n == "transparent" or h == "transparent": return
    btn.configure(hover=False)
    state = {"tw": None, "p": 0.0}
    def _go(target):
        p0 = state["p"]
        def _upd(e):
            p = p0 + (target - p0) * e
            state["p"] = p
            btn.configure(fg_color=_lerp_hex(n, h, p))
        def _done():
            state["p"] = target
            btn.configure(fg_color=_lerp_hex(n, h, target))
        if state["tw"]: state["tw"].cancel()
        state["tw"] = Tween(btn, dur, _upd, ease_out_cubic, _done)
    btn.bind("<Enter>", lambda e: _go(1.0), add="+")
    btn.bind("<Leave>", lambda e: _go(0.0), add="+")


def click_btn(btn, dur=100):
    """按下/释放脉冲反馈"""
    n = btn.cget("fg_color"); h = btn.cget("hover_color")
    if isinstance(n,(tuple,list)): n = n[1] if str(ctk.get_appearance_mode()).lower() == "dark" else n[0]
    if isinstance(h,(tuple,list)): h = h[1] if str(ctk.get_appearance_mode()).lower() == "dark" else h[0]
    if n == "transparent" or h == "transparent": return
    state = {"tw": None}
    def _run(s, e):
        if state["tw"]: state["tw"].cancel()
        state["tw"] = Tween(btn, dur, lambda t: btn.configure(fg_color=_lerp_hex(s,e,t)),
                            ease_out_quint, lambda: btn.configure(fg_color=e))
    btn.bind("<ButtonPress>",   lambda e: _run(n, h), add="+")
    btn.bind("<ButtonRelease>", lambda e: _run(h, n), add="+")


def flat_btn(parent, text, command=None, width=None, height=36, font_size=13,
             fg=None, hover=None, text_color=None, bold=False, corner=8, **kw):
    """统一风格的扁平按钮"""
    fg = fg or Theme.accent()
    hover = hover or _lerp_hex(fg, "#000000", 0.18)
    tc = text_color or "#FFFFFF"
    kwargs = dict(text=text, height=height, corner_radius=corner,
                  fg_color=fg, hover_color=hover, text_color=tc,
                  font=ctk.CTkFont(size=font_size, weight="bold" if bold else "normal"),
                  command=command, **kw)
    if width: kwargs["width"] = width
    btn = ctk.CTkButton(parent, **kwargs)
    hover_btn(btn, fg, hover)
    click_btn(btn)
    return btn


def ghost_btn(parent, text, command=None, width=None, height=34, font_size=13, **kw):
    """透明背景幽灵按钮"""
    kwargs = dict(text=text, height=height, corner_radius=8,
                  fg_color="transparent", hover_color=Theme.pair("hover"),
                  text_color=Theme.pair("text_muted"),
                  font=ctk.CTkFont(size=font_size),
                  command=command, **kw)
    if width: kwargs["width"] = width
    return ctk.CTkButton(parent, **kwargs)


def section_label(parent, text, size=11):
    """分区标题小标签"""
    return ctk.CTkLabel(parent, text=text.upper(),
                        font=ctk.CTkFont(size=size, weight="bold"),
                        text_color=Theme.pair("text_dim"))


def separator(parent, vertical=False):
    if vertical:
        return ctk.CTkFrame(parent, width=1, fg_color=Theme.pair("separator"))
    return ctk.CTkFrame(parent, height=1, fg_color=Theme.pair("separator"))


def card(parent, corner=12, **kw):
    return ctk.CTkFrame(parent, corner_radius=corner,
                        fg_color=Theme.pair("card"),
                        border_width=1, border_color=Theme.pair("border"), **kw)


def build_banner(root, t_fn):
    bg = ("#E3F2FD", "#111827")
    frame = ctk.CTkFrame(root, height=32, corner_radius=0, fg_color=bg)
    frame.pack(side="top", fill="x")
    frame.pack_propagate(False)
    lbl = ctk.CTkButton(frame, text=t_fn("banner_text"),
                        fg_color="transparent", hover_color=bg,
                        font=ctk.CTkFont(size=11),
                        text_color=("#1565C0", "#5B9BD5"),
                        anchor="center",
                        command=lambda: webbrowser.open(MINECRAFT_STORE_URL))
    lbl.pack(fill="both", expand=True, padx=12, pady=2)
    return frame, lbl


def build_sidebar(root, t_fn, on_navigate, width=168):
    sidebar = ctk.CTkFrame(root, width=width, corner_radius=0,
                           fg_color=Theme.pair("sidebar"))
    sidebar.pack(side="left", fill="y")
    sidebar.pack_propagate(False)

    # Logo 区
    logo_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
    logo_frame.pack(pady=(22, 18), padx=16, fill="x")
    ctk.CTkLabel(logo_frame, text="MCL",
                 font=ctk.CTkFont(size=24, weight="bold"),
                 text_color=(Theme.accent(), Theme.accent())).pack(anchor="w")
    ctk.CTkLabel(logo_frame, text="Launcher  v1.2",
                 font=ctk.CTkFont(size=10),
                 text_color=Theme.pair("text_dim")).pack(anchor="w")

    separator(sidebar).pack(fill="x", padx=14, pady=(0, 8))

    nav_btns = {}
    nav_indicators = {}
    nav_items = [
        ("launch",      "▶",  ),
        ("download",    "↓",  ),
        ("multiplayer", "⊙",  ),
        ("settings",    "⚙",  ),
        ("about",       "ⓘ",  ),
    ]

    btn_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
    btn_frame.pack(fill="x", padx=0)

    for key, icon in nav_items:
        row = ctk.CTkFrame(btn_frame, fg_color="transparent", height=40)
        row.pack(fill="x", pady=1)
        row.pack_propagate(False)

        ind = ctk.CTkFrame(row, width=3, corner_radius=2, fg_color="transparent")
        ind.pack(side="left", fill="y", padx=(5, 0))

        btn = ctk.CTkButton(row,
                            text=f"  {icon}  {t_fn(key)}",
                            anchor="w", height=36,
                            fg_color="transparent",
                            text_color=Theme.pair("text_muted"),
                            hover_color=Theme.pair("hover"),
                            corner_radius=8,
                            font=ctk.CTkFont(size=13),
                            command=lambda k=key: on_navigate(k))
        btn.pack(side="left", fill="x", expand=True, padx=(2, 8))
        nav_btns[key] = btn
        nav_indicators[key] = ind

    return sidebar, nav_btns, nav_indicators
