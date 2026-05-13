# -*- coding: utf-8 -*-
"""
MCL Launcher — 开机启动动画 (Splash Screen)
纯 tkinter 实现，无外部依赖
"""
import tkinter as tk
import math
import time
import random


class BootSplash:
    """启动动画窗口，淡入 → 进度动画 → 淡出 → 自动关闭"""

    def __init__(self, app_name="MCL Launcher", duration=2.8):
        self.app_name = app_name
        self.duration = duration

        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)

        self.W, self.H = 480, 320
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - self.W) // 2
        y = (sh - self.H) // 2
        self.root.geometry(f"{self.W}x{self.H}+{x}+{y}")

        self.root.configure(bg="#0d1117")
        self.root.attributes("-alpha", 0.0)
        self.root.attributes("-transparentcolor", "#0d1117")

        self.canvas = tk.Canvas(
            self.root, width=self.W, height=self.H,
            bg="#0d1117", highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True)

        self._draw_background()
        self._draw_logo()
        self._draw_title()
        self._draw_progress_track()
        self._draw_status_text()

        self.progress = 0.0
        self.particles = []
        self._spawn_particles()

        self.status_messages = [
            "加载核心组件...",
            "初始化图形引擎...",
            "配置运行环境...",
            "校验系统完整性...",
            "连接更新服务...",
            "准备就绪",
        ]

        self._fade_in()

    # ── 背景 ──
    def _draw_background(self):
        r = 20
        self.canvas.create_rectangle(r, 0, self.W - r, self.H, fill="#161b22", outline="", tags="bg")
        self.canvas.create_rectangle(0, r, self.W, self.H - r, fill="#161b22", outline="", tags="bg")
        for cx, cy in [(r, r), (self.W - r, r), (r, self.H - r), (self.W - r, self.H - r)]:
            self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill="#161b22", outline="", tags="bg")
        self.canvas.create_rectangle(2, 2, self.W - 2, self.H - 2, outline="#30363d", width=1, tags="border")

    # ── Logo ──
    def _draw_logo(self):
        cx, cy = self.W // 2, 100
        size = 28
        points = []
        for i in range(6):
            angle = math.radians(60 * i - 30)
            points.extend([cx + size * math.cos(angle), cy + size * math.sin(angle)])
        self.canvas.create_polygon(points, fill="", outline="#58a6ff", width=2.5, tags="logo")
        self.canvas.create_text(cx, cy, text="M", fill="#58a6ff", font=("Segoe UI", 24, "bold"), tags="logo")

    # ── 标题 ──
    def _draw_title(self):
        self.canvas.create_text(
            self.W // 2, 148, text=self.app_name,
            fill="#e6edf3", font=("Segoe UI", 18, "bold"), tags="title",
        )

    # ── 进度条 ──
    def _draw_progress_track(self):
        x1, y1 = 80, 210
        x2, y2 = self.W - 80, 216
        self.canvas.create_rectangle(x1, y1, x2, y2, fill="#21262d", outline="", tags="progress")
        self.progress_bar = self.canvas.create_rectangle(x1, y1, x1, y2, fill="#58a6ff", outline="", tags="progress")
        self.progress_bounds = (x1, y1, x2, y2)

    # ── 状态文字 ──
    def _draw_status_text(self):
        self.status_text = self.canvas.create_text(
            self.W // 2, 236, text="",
            fill="#8b949e", font=("Microsoft YaHei UI", 9), tags="status",
        )

    # ── 粒子 ──
    def _spawn_particles(self):
        for _ in range(30):
            x = random.uniform(0, self.W)
            y = random.uniform(0, self.H)
            r = random.uniform(1.0, 3.0)
            vx = random.uniform(-0.5, 0.5)
            vy = random.uniform(-1.2, -0.3)
            life = random.uniform(0.6, 1.0)
            pid = self.canvas.create_oval(x - r, y - r, x + r, y + r, fill="#58a6ff", outline="", tags="particle")
            self.particles.append({"id": pid, "x": x, "y": y, "r": r, "vx": vx, "vy": vy, "life": life, "max_life": life})

    def _update_particles(self, dt):
        alive = []
        for p in self.particles:
            p["life"] -= dt * 0.3
            if p["life"] <= 0:
                self.canvas.delete(p["id"])
                continue
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vy"] += 0.01
            alpha = p["life"] / p["max_life"]
            r, g, b = int(88 * alpha), int(166 * alpha), int(255 * alpha)
            self.canvas.itemconfig(p["id"], fill=f"#{r:02x}{g:02x}{b:02x}")
            pr = p["r"] * alpha
            self.canvas.coords(p["id"], p["x"] - pr, p["y"] - pr, p["x"] + pr, p["y"] + pr)
            alive.append(p)
        self.particles = alive
        if len(self.particles) < 20:
            x = random.uniform(0, self.W)
            y = self.H + 5
            self.particles.append({
                "id": self.canvas.create_oval(x - 2, y - 2, x + 2, y + 2, fill="#58a6ff", outline="", tags="particle"),
                "x": x, "y": y, "r": random.uniform(1.0, 2.5),
                "vx": random.uniform(-0.4, 0.4), "vy": random.uniform(-1.5, -0.6),
                "life": random.uniform(0.5, 1.0), "max_life": 1.0,
            })

    # ── 淡入 ──
    def _fade_in(self):
        self._fade_start = time.perf_counter()
        self._fade_dur = 0.35
        self._tick_fade_in()

    def _tick_fade_in(self):
        t = min(1.0, (time.perf_counter() - self._fade_start) / self._fade_dur)
        self.root.attributes("-alpha", 1 - (1 - t) ** 3)
        if t < 1.0:
            self.root.after(16, self._tick_fade_in)
        else:
            self.root.attributes("-alpha", 1.0)
            self._start_progress()

    # ── 进度 ──
    def _start_progress(self):
        self._progress_start = time.perf_counter()
        self._tick_progress()

    def _tick_progress(self):
        elapsed = time.perf_counter() - self._progress_start
        t = min(1.0, elapsed / self.duration)
        self.progress = 1 - (1 - t) ** 2.5

        x1, y1, x2, y2 = self.progress_bounds
        bar_x2 = x1 + (x2 - x1) * self.progress
        self.canvas.coords(self.progress_bar, x1, y1, bar_x2, y2)

        idx = min(len(self.status_messages) - 1, int(t * len(self.status_messages)))
        self.canvas.itemconfig(self.status_text, text=self.status_messages[idx])

        self._update_particles(0.016)

        if t < 1.0:
            self.root.after(16, self._tick_progress)
        else:
            self.progress = 1.0
            self.canvas.coords(self.progress_bar, x1, y1, x2, y2)
            self.canvas.itemconfig(self.status_text, text=self.status_messages[-1])
            self.root.after(400, self._fade_out)

    # ── 淡出 ──
    def _fade_out(self):
        self._fadeo_start = time.perf_counter()
        self._fadeo_dur = 0.3
        self._tick_fade_out()

    def _tick_fade_out(self):
        t = min(1.0, (time.perf_counter() - self._fadeo_start) / self._fadeo_dur)
        self.root.attributes("-alpha", 1.0 - t ** 3)
        if t < 1.0:
            self.root.after(16, self._tick_fade_out)
        else:
            self.root.destroy()

    # ── 入口 ──
    def run(self):
        """阻塞运行启动动画，动画结束后返回"""
        try:
            self.root.mainloop()
        except tk.TclError:
            pass
