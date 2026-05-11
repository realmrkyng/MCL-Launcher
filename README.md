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
├── src/               # 源代码
├── main.py            # 主程序入口
├── requirements.txt   # Python 依赖
├── README.md          # 项目说明
└── LICENSE            # MIT 许可证

# 技术栈
· Python 3.x
· PyInstaller（打包 exe）
· tkinter / customtkinter（界面）

#📄 开源协议
MIT License © 2026 MrKyng
