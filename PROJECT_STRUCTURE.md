
📦 MCL-Launcher
├── 📄 main.py                  # 🚀 入口
├── 📄 build.bat                # 🏗️ 打包脚本
├── 📄 MCL-Launcher.spec        # 🔧 PyInstaller 配置
├── 📄 requirements.txt         # 📋 依赖
├── 📄 LICENSE                  # 📜 MIT 开源许可证（新加）
├── 📄 README.md                # 📖 说明文档（新加）
├── 📄 .gitignore               # 🙈 Git 忽略规则（新加）
│
└── 📁 src/                     # 核心代码
    ├── 📄 __init__.py
    ├── 📄 constants.py         #    全局配置
    ├── 📄 i18n.py              #    中英翻译
    ├── 📄 theme.py             #    主题管理
    ├── 📄 backend.py           # 🎮 后端（下载/启动/Java）
    ├── 📄 update_checker.py    # 🔄 更新检查
    ├── 📄 modrinth.py          # 🏔️ Modrinth API
    ├── 📄 curseforge.py        # 🔥 CurseForge API
    ├── 📄 mod_loader.py        # 🔧 模组加载器
    │
    └── 📁 ui/                  # 用户界面
        ├── 📄 __init__.py
        ├── 📄 boot.py          # 💫 启动动画
        ├── 📄 app.py           # 🖥️ 主窗口
        ├── 📄 pages.py         # 📐 页面布局
        └── 📄 widgets.py       # 🧩 UI 组件
