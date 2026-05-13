# -*- coding: utf-8 -*-
"""
MCL Launcher v1.2 — 入口
"""
from src.ui.boot import BootSplash
from src.ui.app import LauncherGUI


def main():
    # 开机动画
    splash = BootSplash(app_name="MCL Launcher")
    splash.run()

    # 主窗口
    gui = LauncherGUI()
    gui.root.mainloop()


if __name__ == "__main__":
    main()
