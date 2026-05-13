@echo off
chcp 65001 >nul
echo ========================================
echo  MCL Launcher v1.2 - Build Script
echo ========================================
echo.

REM 检查 PyInstaller
where pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] PyInstaller not found. Installing...
    pip install pyinstaller
)

echo [1/3] Installing requirements...
pip install -r requirements.txt

echo.
echo [2/3] Building executable...
pyinstaller MCL-Launcher.spec --clean --noconfirm

echo.
echo [3/3] Build complete!
echo.
echo Output: dist\MCL-Launcher.exe
pause
