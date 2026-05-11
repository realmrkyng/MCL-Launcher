"""
MCL Launcher — 入口
    python -m src.main
如果使用单文件打包，可直接 python src/main.py
"""
from src.ui.app import LauncherGUI


def main():
    gui = LauncherGUI()
    gui.root.mainloop()


if __name__ == "__main__":
    main()
