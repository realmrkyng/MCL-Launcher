# -*- coding: utf-8 -*-
"""
MCL Launcher v1.2 — 主题系统 & 颜色常量
支持深色/浅色模式 + 用户自定义强调色
"""

# 内置强调色预设
ACCENT_PRESETS = {
    "orange": "#FF8C00",
    "blue":   "#2979FF",
    "green":  "#00C853",
    "purple": "#AA00FF",
    "pink":   "#F50057",
    "teal":   "#00BFA5",
}

DARK = {
    "bg":          "#141414",
    "sidebar":     "#1C1C1C",
    "card":        "#1E1E1E",
    "card2":       "#252525",
    "border":      "#2E2E2E",
    "text":        "#E0E0E0",
    "text_muted":  "#707070",
    "text_dim":    "#505050",
    "input_bg":    "#252525",
    "hover":       "#2A2A2A",
    "nav_active":  "#242424",
    "progress_bg": "#2A2A2A",
    "separator":   "#2A2A2A",
    "success":     "#4CAF50",
    "error":       "#FF5252",
    "warning":     "#FFB300",
}

LIGHT = {
    "bg":          "#F5F5F5",
    "sidebar":     "#FAFAFA",
    "card":        "#FFFFFF",
    "card2":       "#F8F8F8",
    "border":      "#E0E0E0",
    "text":        "#212121",
    "text_muted":  "#757575",
    "text_dim":    "#BDBDBD",
    "input_bg":    "#FFFFFF",
    "hover":       "#EEEEEE",
    "nav_active":  "#F0F0F0",
    "progress_bg": "#E0E0E0",
    "separator":   "#E8E8E8",
    "success":     "#2E7D32",
    "error":       "#C62828",
    "warning":     "#E65100",
}


class Theme:
    """运行时主题状态，单例"""
    _mode = "dark"
    _accent = ACCENT_PRESETS["orange"]
    _palette = DARK

    @classmethod
    def set_mode(cls, mode: str):
        cls._mode = mode
        cls._palette = DARK if mode == "dark" else LIGHT

    @classmethod
    def set_accent(cls, color: str):
        cls._accent = color

    @classmethod
    def c(cls, key: str) -> str:
        return cls._palette.get(key, "#FF0000")

    @classmethod
    def pair(cls, key: str) -> tuple:
        """CustomTkinter 颜色元组：(浅色模式下的颜色, 深色模式下的颜色)。

        必须用 LIGHT/DARK 各一份；勿写成 (Theme.c(k), Theme.c(k))，
        否则构建时两侧被固定成同一套色，切换外观后界面不会变。
        """
        return (LIGHT.get(key, "#000000"), DARK.get(key, "#FFFFFF"))

    @classmethod
    def accent(cls) -> str:
        return cls._accent

    @classmethod
    def is_dark(cls) -> bool:
        return cls._mode == "dark"
