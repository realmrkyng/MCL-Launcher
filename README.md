# MCL-Launcher  
Minecraft 是一款值得购买的游戏，请支持正版。    
Minecraft启动器(MCL Launcher)  
本启动器仅供学习交流，游戏文件请通过官方启动器或正版账号获取。  
一个简洁、开源的 **Minecraft 启动器**，支持离线下载、自动 Java 检测、版本隔离、内存自动分配、中英双语、黑白主题。
 
## ✨ 特色功能

| 功能 | 说明 |
|------|------|
| 🚀 **离线下载与启动** | 无需正版账号，一键下载并启动 Minecraft |
| ☕ **Java 自动检测** | 找不到 Java 时自动提示官方下载链接 |
| 📦 **版本隔离** | 不同版本互不干扰（设置里可开关）|
| 💾 **内存自动分配** | 根据你的电脑内存智能分配，不卡顿 |
| 🎨 **黑白主题** | 纯白 / 纯黑，保护眼睛 |
| 🔮 **联机预告** | 创建房间 / 加入房间（功能开发中）|

---

## 📥 下载使用

### 方式一：直接下载 exe（推荐）
👉 [**下载 MCL Launcher v1.0**](https://github.com/realmrkyng/MCL-Launcher/releases/latest)

无需安装 Python，双击即可运行。

### 方式二：源码运行
```bash
git clone https://github.com/realmrkyng/MCL-Launcher.git
cd MCL-Launcher
pip install -r requirements.txt
python main.py

# 结构
MCL-Launcher/
│
├── main.py                      # 入口：from src.ui.app import LauncherGUI
├── requirements.txt             # minecraft-launcher-lib>=6.5, customtkinter>=5.2.0
├── build.bat                    # PyInstaller 打包脚本
├── .gitignore
├── README.md
├── LICENSE
│
└── src/
    │
    ├── __init__.py              # 包声明
    │
    ├── constants.py             # APP_NAME / v1.1 / AUTHOR / GitHub URL / 路径配置
    │
    ├── i18n.py                  # 中英文翻译字典（~70 keys，T["cn"] / T["en"]）
    │
    ├── backend.py               # LauncherBackend：版本列表 / 下载 / 安装 / Java检测 / 启动命令
    │
    ├── update_checker.py        # UpdateChecker：GitHub 异步检查更新
    │
    └── ui/
        │
        ├── __init__.py
        │
        ├── app.py               # LauncherGUI 主类：窗口 / 页面切换 / 启动流程 / 配置 / 主题 / 动画
        │
        ├── pages.py             # PageBuilder：5页 UI 构建器（启动 / 下载 / 联机 / 设置 / 关于）
        │
        └── widgets.py           # 侧边栏 / 横幅 / 悬浮动画 / 点击反馈

# 技术栈
· Python 3.x
· PyInstaller（打包 exe）
· tkinter / customtkinter（界面）

#📄 开源协议
MIT License © 2026 MrKyng
