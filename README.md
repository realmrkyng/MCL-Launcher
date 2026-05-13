<h1 align="center">MCL Launcher</h1>

<p align="center">
  <strong>一个简洁、开源的 Minecraft 启动器</strong>
  <br>
  支持离线下载、自动 Java 检测、版本隔离、中英双语
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8%2B-blue" alt="Python 3.8+" />
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License" />
  <img src="https://img.shields.io/badge/platform-Windows-lightgrey" alt="Windows" />
</p>

---

## ✨ 功能

| 功能 | 说明 |
|------|------|
| 🚀 **一键下载 & 启动** | 自动下载 Minecraft，无需手动操作 |
| ☕ **Java 自动检测** | 找不到 Java 时自动下载安装包到桌面 |
| 📦 **版本隔离** | 不同版本互不干扰（可开关） |
| 💾 **内存自动分配** | 根据你的电脑内存智能分配 |
| 🔧 **模组加载器** | 支持 Forge / Fabric / OptiFine 一键安装 |
| 🎨 **黑白主题** | 纯白 / 纯黑，保护眼睛 |
| 🌐 **中英双语** | 自动适配系统语言 |
| 📥 **镜像下载** | BMCLAPI + TUNA 镜像加速 |
| 🔮 **联机预告** | 联机功能正在开发中 |

## 📸 截图

> [capture_20260513191434143.bmp](https://github.com/user-attachments/files/27707742/capture_20260513191434143.bmp)



## 🚀 快速开始

### 下载即用

从 [Releases](https://github.com/realmrkyng/MCL-Launcher/releases/latest) 下载最新版 exe，双击运行即可。

### 从源码运行

```bash
# 1. 克隆仓库
git clone https://github.com/realmrkyng/MCL-Launcher.git
cd MCL-Launcher

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行
python main.py
```

### 打包为 exe

```bash
build.bat
```

输出在 `dist/MCL-Launcher.exe`。

## 🏗️ 项目结构

```
MCL-Launcher/
├── main.py               # 入口
├── build.bat             # 打包脚本
├── requirements.txt      # 依赖
│
└── src/
    ├── constants.py      # 配置 & 常量
    ├── backend.py        # 后端核心逻辑
    ├── mod_loader.py     # 模组加载器管理
    ├── modrinth.py       # Modrinth API
    ├── i18n.py           # 双语
    └── ui/               # 用户界面
        ├── app.py        # 主窗口
        ├── pages.py      # 页面布局
        └── widgets.py    # UI 组件
```

> 完整结构见 [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)

## 🛠️ 技术栈

- **Python 3.x** — 核心语言
- **customtkinter** — 现代化 UI 框架
- **minecraft-launcher-lib** — Minecraft 启动库
- **PyInstaller** — 打包为 exe
- **Modrinth API / CurseForge API** — 模组搜索

## 📄 开源协议

MIT License © 2026 [MrKyng](https://github.com/realmrkyng)

---

<p align="center">
  <i>Minecraft 是一款值得购买的游戏，请支持正版。</i>
</p>
