@echo off
chcp 65001 >nul
echo ========================================
echo   MCL Launcher - 打包工具
echo ========================================
echo.

pyinstaller --onefile --windowed ^
    --name "MinecraftLauncher" ^
    --paths "src" ^
    --collect-data customtkinter ^
    --hidden-import minecraft_launcher_lib ^
    --hidden-import minecraft_launcher_lib.install ^
    --hidden-import minecraft_launcher_lib.command ^
    --hidden-import minecraft_launcher_lib.utils ^
    --hidden-import minecraft_launcher_lib.runtime ^
    --hidden-import src ^
    --hidden-import src.constants ^
    --hidden-import src.i18n ^
    --hidden-import src.backend ^
    --hidden-import src.update_checker ^
    --hidden-import src.ui ^
    --hidden-import src.ui.app ^
    --hidden-import src.ui.pages ^
    --hidden-import src.ui.widgets ^
    --clean --noconfirm ^
    main.py

echo.
echo ========================================
echo   完成！exe 在 dist 目录下
echo ========================================
pause
